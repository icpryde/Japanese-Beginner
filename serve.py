#!/usr/bin/env python3
"""
Akamonkai Japanese — Local Server with Progress Sync

Serves the offline site and provides a progress sync API
for cross-device usage (Mac, iPad, iPhone on same WiFi).
"""
import http.server
import json
import os
import socket
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

PROJECT_ROOT = Path(__file__).parent
SITE_DIR = PROJECT_ROOT / "site"
PROGRESS_FILE = PROJECT_ROOT / "progress.json"
SYNC_META_FILE = PROJECT_ROOT / "sync-meta.json"
PORT = 8080
MAX_OP_HISTORY = 5000


def get_local_ip():
    """Get the Mac's local network IP address."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "localhost"


def load_progress() -> dict:
    if PROGRESS_FILE.exists():
        try:
            return json.loads(PROGRESS_FILE.read_text())
        except (json.JSONDecodeError, IOError):
            pass
    return {}


def save_progress(data: dict):
    PROGRESS_FILE.write_text(json.dumps(data, indent=2))


def load_sync_meta() -> dict:
    if SYNC_META_FILE.exists():
        try:
            data = json.loads(SYNC_META_FILE.read_text())
            if isinstance(data, dict) and isinstance(data.get("applied_ops"), dict):
                return data
        except (json.JSONDecodeError, IOError):
            pass
    return {"applied_ops": {}, "last_updated": ""}


def save_sync_meta(meta: dict):
    SYNC_META_FILE.write_text(json.dumps(meta, indent=2))


def prune_applied_ops(applied_ops: dict) -> dict:
    if len(applied_ops) <= MAX_OP_HISTORY:
        return applied_ops
    # Keep newest operation IDs by timestamp.
    ordered = sorted(applied_ops.items(), key=lambda item: item[1], reverse=True)
    return dict(ordered[:MAX_OP_HISTORY])


def merge_progress(server_data: dict, client_data: dict) -> dict:
    """Merge progress: latest timestamp wins per lesson."""
    merged = dict(server_data)
    for lid, cv in client_data.items():
        sv = merged.get(lid, {})
        if (cv.get("timestamp", 0) or 0) > (sv.get("timestamp", 0) or 0):
            merged[lid] = cv
    return merged


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(SITE_DIR), **kwargs)

    def end_headers(self):
        # CORS headers for cross-device access
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, X-Operation-Id')
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == '/api/progress':
            data = load_progress()
            body = json.dumps(data).encode()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif parsed.path == '/api/sync-status':
            meta = load_sync_meta()
            body = json.dumps({
                "applied_operation_ids": len(meta.get("applied_ops", {})),
                "last_updated": meta.get("last_updated", ""),
            }).encode()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == '/api/progress':
            length = int(self.headers.get('Content-Length', 0))
            if length > 1_000_000:  # 1MB limit
                self.send_response(413)
                self.end_headers()
                return
            try:
                body = self.rfile.read(length)
                client_data = json.loads(body)
                if not isinstance(client_data, dict):
                    raise ValueError("Expected dict")
            except (json.JSONDecodeError, ValueError):
                self.send_response(400)
                self.end_headers()
                return

            operation_id = (self.headers.get('X-Operation-Id') or '').strip()
            if not operation_id:
                self.send_response(400)
                self.end_headers()
                return

            meta = load_sync_meta()
            applied_ops = meta.get("applied_ops", {})
            if operation_id in applied_ops:
                resp = json.dumps({"status": "duplicate", "count": len(load_progress())}).encode()
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(resp)))
                self.end_headers()
                self.wfile.write(resp)
                return

            server_data = load_progress()
            merged = merge_progress(server_data, client_data)
            save_progress(merged)

            applied_ops[operation_id] = int(time.time())
            meta["applied_ops"] = prune_applied_ops(applied_ops)
            meta["last_updated"] = time.strftime("%Y-%m-%d %H:%M:%S")
            save_sync_meta(meta)

            resp = json.dumps({"status": "ok", "count": len(merged)}).encode()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(resp)))
            self.end_headers()
            self.wfile.write(resp)
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        # Quieter logging
        if '/api/' in str(args[0]) if args else False:
            return
        super().log_message(format, *args)


def print_warmup_guidance(url: str):
    """Print first-run cache warmup instructions based on build audit."""
    report_path = SITE_DIR / "offline-asset-report.json"
    if not report_path.exists():
        return

    try:
        report = json.loads(report_path.read_text())
    except (json.JSONDecodeError, OSError):
        return

    summary = report.get("summary", {})
    readiness = summary.get("offline_readiness_percent", 0)
    coverage_by_kind = summary.get("coverage_by_kind", {})
    build_id = report.get("build_id", "unknown")

    print("  ── Offline Status ──────────────────────────────")
    print(f"  Build: {build_id}")
    print(f"  Overall readiness: {readiness:.1f}%")
    if coverage_by_kind:
        for kind, pct in sorted(coverage_by_kind.items()):
            flag = "✓" if pct == 100.0 else "!"
            print(f"    {flag} {kind}: {pct:.1f}%")
    print()

    precache_path = SITE_DIR / "precache-manifest.json"
    lesson_count = 0
    if precache_path.exists():
        try:
            manifest = json.loads(precache_path.read_text())
            lesson_count = sum(
                1 for u in manifest.get("urls", []) if "/lessons/" in u
            )
        except (json.JSONDecodeError, OSError):
            pass

    print("  ── First-Run Warmup (cache all lessons) ────────")
    print("  The PWA service worker caches pages as you visit them.")
    print("  To fully warm up the cache on a new device:")
    print()
    print(f"    1. Open {url} in Safari")
    print("    2. Tap Share → Add to Home Screen → Open from Home Screen")
    print("    3. Visit the Dashboard — this triggers the install event")
    print("       which pre-caches all lesson pages + media automatically")
    if lesson_count:
        print(f"       ({lesson_count} lesson pages + required media will be cached)")
    print()
    print("  ── Sync Across Devices ─────────────────────────")
    print("  Progress syncs automatically when both devices are online.")
    print("  Offline changes queue locally and flush on reconnect.")
    print()


def main():
    if not SITE_DIR.exists():
        print(f"Error: Site directory not found at {SITE_DIR}")
        print("Run build_site.py first!")
        sys.exit(1)

    ip = get_local_ip()
    url = f"http://{ip}:{PORT}"

    print("=" * 50)
    print("  Akamonkai Japanese — Local Server")
    print("=" * 50)
    print()
    print(f"  Local:   http://localhost:{PORT}")
    print(f"  Network: {url}")
    print()

    print_warmup_guidance(url)

    # Generate QR code
    try:
        import qrcode
        qr = qrcode.QRCode(box_size=1, border=1)
        qr.add_data(url)
        qr.make()
        print("  Scan this QR code on iPad/iPhone:")
        print()
        qr.print_ascii(invert=True)
        print()
    except ImportError:
        print("  (Install 'qrcode' package for QR code display)")
        print()

    print("  On iPad/iPhone:")
    print("    1. Connect to same WiFi as this Mac")
    print(f"    2. Open Safari → {url}")
    print("    3. Tap Share → Add to Home Screen")
    print()
    print("  Press Ctrl+C to stop.")
    print("=" * 50)

    server = http.server.HTTPServer(('0.0.0.0', PORT), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
        server.server_close()


if __name__ == "__main__":
    main()
