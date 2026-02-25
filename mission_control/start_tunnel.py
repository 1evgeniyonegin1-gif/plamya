"""
Mission Control — One-click launcher.
Starts backend + cloudflare tunnel + auto-updates Telegram menu button.

Usage:
    python -m mission_control.start_tunnel
"""

import os
import re
import sys
import time
import subprocess
import threading

import httpx

BOT_TOKEN = os.getenv(
    "MISSION_CONTROL_BOT_TOKEN",
    "8264259448:AAG81iJXxJPcUgywhM_z3a_jUki6kejHs-Q",
)
BACKEND_PORT = int(os.getenv("MISSION_CONTROL_API_PORT", "8006"))
TUNNEL_URL_RE = re.compile(r"(https://[a-z0-9-]+\.trycloudflare\.com)", re.IGNORECASE)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def start_backend():
    return subprocess.Popen(
        [sys.executable, "-m", "mission_control.backend.main"],
        cwd=PROJECT_ROOT,
        stdout=sys.stdout,
        stderr=sys.stderr,
    )


def wait_for_backend(timeout: int = 20) -> bool:
    url = f"http://localhost:{BACKEND_PORT}/health"
    for _ in range(timeout):
        try:
            r = httpx.get(url, timeout=2)
            if r.status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(1)
    return False


def start_cloudflared():
    url_holder: dict = {"url": None}
    url_event = threading.Event()

    proc = subprocess.Popen(
        ["cloudflared", "tunnel", "--url", f"http://localhost:{BACKEND_PORT}"],
        cwd=PROJECT_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    def _read_stderr():
        assert proc.stderr is not None
        for raw_line in proc.stderr:
            text = raw_line.decode("utf-8", errors="replace").strip()
            if text:
                print(f"  [cloudflared] {text}")
            m = TUNNEL_URL_RE.search(text)
            if m and not url_holder["url"]:
                url_holder["url"] = m.group(1)
                url_event.set()

    t = threading.Thread(target=_read_stderr, daemon=True)
    t.start()

    return proc, url_event, url_holder


def set_menu_button(tunnel_url: str) -> bool:
    api_url = f"https://api.telegram.org/bot{BOT_TOKEN}/setChatMenuButton"
    payload = {
        "menu_button": {
            "type": "web_app",
            "text": "Mission Control",
            "web_app": {"url": tunnel_url},
        }
    }
    try:
        r = httpx.post(api_url, json=payload, timeout=10)
        data = r.json()
        if data.get("ok"):
            return True
        print(f"  [!] Telegram API error: {data}")
        return False
    except Exception as e:
        print(f"  [!] Failed to set menu button: {e}")
        return False


def main():
    print()
    print("=" * 50)
    print("  Mission Control Launcher")
    print("=" * 50)
    print()

    # 1. Backend
    print("[1/3] Starting backend on port %d..." % BACKEND_PORT)
    backend = start_backend()
    if not wait_for_backend():
        print("[FAIL] Backend did not start. Check logs above.")
        backend.kill()
        sys.exit(1)
    print("[OK]  Backend is healthy")
    print()

    # 2. Tunnel
    print("[2/3] Starting cloudflare tunnel...")
    tunnel, url_event, url_holder = start_cloudflared()
    if not url_event.wait(timeout=30):
        print("[FAIL] Could not get tunnel URL within 30 seconds.")
        tunnel.kill()
        backend.kill()
        sys.exit(1)
    tunnel_url = url_holder["url"]
    print(f"[OK]  Tunnel URL: {tunnel_url}")
    print()

    # 3. Menu button
    print("[3/3] Setting Telegram menu button...")
    if set_menu_button(tunnel_url):
        print("[OK]  Menu button updated for @Alrton_bot")
    else:
        print("[WARN] Menu button update failed (app still works via direct URL)")

    print()
    print("=" * 50)
    print(f"  Mission Control is live!")
    print(f"  URL: {tunnel_url}")
    print(f"  Telegram: @Alrton_bot -> Menu button")
    print("=" * 50)
    print()
    print("Press Ctrl+C to stop.")
    print()

    # Monitor loop
    try:
        while True:
            if backend.poll() is not None:
                print(
                    "[!] Backend died (exit code %s), restarting..."
                    % backend.returncode
                )
                backend = start_backend()
                if not wait_for_backend():
                    print("[!] Backend restart failed")
            if tunnel.poll() is not None:
                print("[!] Tunnel died, restarting...")
                tunnel, url_event, url_holder = start_cloudflared()
                if url_event.wait(timeout=30):
                    new_url = url_holder["url"]
                    print(f"[OK] New tunnel URL: {new_url}")
                    if set_menu_button(new_url):
                        print("[OK] Menu button updated")
                    tunnel_url = new_url
                else:
                    print("[!] Tunnel restart failed — could not get URL")
            time.sleep(5)
    except KeyboardInterrupt:
        print()
        print("[Shutting down...]")
        tunnel.terminate()
        backend.terminate()
        for p in (tunnel, backend):
            try:
                p.wait(timeout=3)
            except subprocess.TimeoutExpired:
                p.kill()
        print("[Done]")


if __name__ == "__main__":
    main()
