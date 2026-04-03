# Cloud Sync Setup (Mac + iPad)

This enables real cross-device progress sync for your hosted app.

## 1. Create Worker + KV

1. Install Wrangler (if needed):
   - npm install -g wrangler
2. Login:
   - wrangler login
3. Create KV namespace:
   - wrangler kv namespace create "PROGRESS_KV"
4. Create preview namespace:
   - wrangler kv namespace create "PROGRESS_KV" --preview
5. Copy both IDs into `cloudflare_sync/wrangler.toml` replacing:
   - `REPLACE_WITH_KV_NAMESPACE_ID`
   - `REPLACE_WITH_PREVIEW_KV_NAMESPACE_ID`

## 2. Deploy Worker

Run from repo root:

```bash
cd cloudflare_sync
wrangler deploy
```

After deploy, copy the worker URL, for example:
- `https://akamonkai-progress-sync.<your-subdomain>.workers.dev`

## 3. Configure Sync In The App

On both Mac and iPad:

1. Open the app URL.
2. Tap/click the top-right status badge.
3. Enter worker URL when asked (without `/api/progress` is fine).
4. Enter the same sync key on both devices (example: `akamonkai2026`).

If configured correctly, status becomes:
- `Status: Sync connected` or `Status: Synced`

## 4. Verify

1. Mark a lesson complete on Mac.
2. Open app on iPad while online.
3. Confirm completion state appears.
4. Toggle a lesson on iPad offline, reconnect, and verify it syncs.

## Notes

- Sync key must match on both devices.
- Allowed origin is set in `wrangler.toml` as `ALLOWED_ORIGIN`.
- If your GitHub Pages URL changes, update `ALLOWED_ORIGIN` and redeploy.
