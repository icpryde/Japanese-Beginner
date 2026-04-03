const MAX_BODY_BYTES = 1_000_000;
const OPERATION_TTL_SECONDS = 60 * 60 * 24 * 30; // 30 days

function corsHeaders(origin) {
  return {
    'Access-Control-Allow-Origin': origin,
    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type, X-Operation-Id',
    'Access-Control-Max-Age': '86400',
    'Vary': 'Origin',
  };
}

function jsonResponse(payload, status, origin) {
  return new Response(JSON.stringify(payload), {
    status,
    headers: {
      'Content-Type': 'application/json',
      ...corsHeaders(origin),
    },
  });
}

function normalizeAllowedOrigin(env) {
  const raw = (env.ALLOWED_ORIGIN || '*').trim();
  return raw || '*';
}

function getRequestOrigin(request) {
  return request.headers.get('Origin') || '*';
}

function getCorsOrigin(request, env) {
  const configured = normalizeAllowedOrigin(env);
  if (configured === '*') return '*';
  const reqOrigin = getRequestOrigin(request);
  if (reqOrigin === configured) return configured;
  return configured;
}

function sanitizeSyncKey(key) {
  if (!key) return '';
  const trimmed = key.trim();
  if (!/^[A-Za-z0-9_-]{6,128}$/.test(trimmed)) return '';
  return trimmed;
}

function mergeProgress(serverData, clientData) {
  const merged = { ...(serverData || {}) };

  for (const [lessonId, incoming] of Object.entries(clientData || {})) {
    const current = merged[lessonId] || {};
    const incomingTs = Number(incoming?.timestamp || 0);
    const currentTs = Number(current?.timestamp || 0);
    if (incomingTs >= currentTs) {
      merged[lessonId] = incoming;
    }
  }

  return merged;
}

function progressStorageKey(syncKey) {
  return `progress:${syncKey}`;
}

function operationStorageKey(syncKey, operationId) {
  return `op:${syncKey}:${operationId}`;
}

async function getStoredProgress(env, syncKey) {
  const raw = await env.PROGRESS_KV.get(progressStorageKey(syncKey));
  if (!raw) return {};
  try {
    const parsed = JSON.parse(raw);
    return parsed && typeof parsed === 'object' ? parsed : {};
  } catch {
    return {};
  }
}

async function handleGetProgress(request, env, syncKey) {
  const origin = getCorsOrigin(request, env);
  const data = await getStoredProgress(env, syncKey);
  return jsonResponse(data, 200, origin);
}

async function handlePostProgress(request, env, syncKey) {
  const origin = getCorsOrigin(request, env);

  const operationId = (request.headers.get('X-Operation-Id') || '').trim();
  if (!operationId) {
    return jsonResponse({ error: 'missing_operation_id' }, 400, origin);
  }

  const opKey = operationStorageKey(syncKey, operationId);
  const alreadyApplied = await env.PROGRESS_KV.get(opKey);
  if (alreadyApplied) {
    return jsonResponse({ status: 'duplicate' }, 200, origin);
  }

  const bodyText = await request.text();
  if (bodyText.length > MAX_BODY_BYTES) {
    return jsonResponse({ error: 'payload_too_large' }, 413, origin);
  }

  let clientData;
  try {
    clientData = JSON.parse(bodyText);
  } catch {
    return jsonResponse({ error: 'invalid_json' }, 400, origin);
  }

  if (!clientData || typeof clientData !== 'object' || Array.isArray(clientData)) {
    return jsonResponse({ error: 'invalid_payload' }, 400, origin);
  }

  const serverData = await getStoredProgress(env, syncKey);
  const merged = mergeProgress(serverData, clientData);

  await env.PROGRESS_KV.put(progressStorageKey(syncKey), JSON.stringify(merged));
  await env.PROGRESS_KV.put(opKey, '1', { expirationTtl: OPERATION_TTL_SECONDS });

  return jsonResponse({ status: 'ok', count: Object.keys(merged).length }, 200, origin);
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const origin = getCorsOrigin(request, env);

    if (request.method === 'OPTIONS') {
      return new Response(null, {
        status: 204,
        headers: corsHeaders(origin),
      });
    }

    if (url.pathname !== '/api/progress') {
      return jsonResponse({ error: 'not_found' }, 404, origin);
    }

    const syncKey = sanitizeSyncKey(url.searchParams.get('sync_key'));
    if (!syncKey) {
      return jsonResponse({ error: 'invalid_sync_key' }, 400, origin);
    }

    if (request.method === 'GET') {
      return handleGetProgress(request, env, syncKey);
    }

    if (request.method === 'POST') {
      return handlePostProgress(request, env, syncKey);
    }

    return jsonResponse({ error: 'method_not_allowed' }, 405, origin);
  },
};
