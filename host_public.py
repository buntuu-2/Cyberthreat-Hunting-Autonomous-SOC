#!/usr/bin/env python3
"""
AI Cyberthreat Hunting & Autonomous SOC - Public Host Launcher
Starts the FastAPI SOC server and creates a secure Cloudflare Tunnel
giving an instant, publicly accessible HTTPS URL.
"""

import os
import re
import sys
import time
import signal
import subprocess
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
CLOUDFLARED_BIN = ROOT_DIR / "bin" / "cloudflared"
PORT = int(os.environ.get("PORT", "8000"))
HOST = os.environ.get("HOST", "127.0.0.1")

LOG_DIR = ROOT_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
SERVER_LOG = LOG_DIR / "soc_server.log"
TUNNEL_LOG = LOG_DIR / "tunnel.log"

processes = []

def cleanup(sig=None, frame=None):
    print("\n[!] Shutting down public SOC host...")
    for p in processes:
        try:
            p.terminate()
            p.wait(timeout=3)
        except Exception:
            try:
                p.kill()
            except Exception:
                pass
    sys.exit(0)

signal.signal(signal.SIGINT, cleanup)
signal.signal(signal.SIGTERM, cleanup)

def main():
    if not CLOUDFLARED_BIN.exists():
        print(f"[ERROR] cloudflared not found at {CLOUDFLARED_BIN}")
        sys.exit(1)

    print("=" * 72)
    print("  🚀 STARTING AI CYBERTHREAT SOC PUBLIC HOST")
    print("=" * 72)
    print(f"[*] Starting local SOC Server on http://{HOST}:{PORT}...")

    # Start FastAPI server, writing output directly to log file
    server_log_fp = open(SERVER_LOG, "w", encoding="utf-8")
    server_cmd = [
        sys.executable,
        str(ROOT_DIR / "main.py"),
        "--serve",
        "--host", HOST,
        "--port", str(PORT)
    ]
    server_proc = subprocess.Popen(
        server_cmd,
        cwd=str(ROOT_DIR),
        stdout=server_log_fp,
        stderr=subprocess.STDOUT
    )
    processes.append(server_proc)

    # Wait 2 seconds for server to initialize
    time.sleep(2)

    # Check if server stayed alive
    if server_proc.poll() is not None:
        print("[ERROR] SOC Server failed to start! Check logs/soc_server.log:")
        if SERVER_LOG.exists():
            print(SERVER_LOG.read_text(encoding="utf-8"))
        cleanup()

    print(f"[*] Establishing secure Cloudflare Public Tunnel for port {PORT}...")
    tunnel_log_fp = open(TUNNEL_LOG, "w+", encoding="utf-8")
    tunnel_cmd = [
        str(CLOUDFLARED_BIN),
        "tunnel",
        "--url", f"http://{HOST}:{PORT}",
        "--no-autoupdate"
    ]
    tunnel_proc = subprocess.Popen(
        tunnel_cmd,
        cwd=str(ROOT_DIR),
        stdout=tunnel_log_fp,
        stderr=subprocess.STDOUT
    )
    processes.append(tunnel_proc)

    public_url = None
    url_regex = re.compile(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com")

    # Read tunnel log file until the public URL is printed
    start_time = time.time()
    read_pos = 0
    while time.time() - start_time < 30:
        time.sleep(0.5)
        if TUNNEL_LOG.exists():
            with open(TUNNEL_LOG, "r", encoding="utf-8") as f:
                f.seek(read_pos)
                new_text = f.read()
                read_pos = f.tell()
                match = url_regex.search(new_text)
                if match:
                    public_url = match.group(0)
                    break

        if tunnel_proc.poll() is not None:
            break

    if public_url:
        print("\n" + "=" * 72)
        print("  🎉 YOUR AI SOC COMMAND CENTER IS LIVE ON THE WEB!")
        print("=" * 72)
        print(f"  🌐 Public HTTPS URL:  {public_url}")
        print(f"  🏠 Local Dashboard:   http://{HOST}:{PORT}")
        print(f"  📖 API Documentation: {public_url}/docs")
        print("=" * 72)
        print("  Share this Public HTTPS URL with anyone! Anyone can open it")
        print("  in their browser from any device, phone, or computer to:")
        print("   - View the Live SOC Command Center & telemetry")
        print("   - Run interactive attack simulations (SSH, Port scan, Tor)")
        print("   - Test automated UFW containment & TTL auto-unblock")
        print("   - Inspect AI investigation narratives & MITRE ATT&CK mapping")
        print("   - View Viva defense preparation cheat sheets")
        print("=" * 72 + "\n")
        
        # Save URL to text file
        url_file = ROOT_DIR / "LIVE_PUBLIC_URL.txt"
        url_file.write_text(f"{public_url}\n", encoding="utf-8")
    else:
        print("[!] Could not detect public tunnel URL within 30 seconds.")
        if TUNNEL_LOG.exists():
            print(TUNNEL_LOG.read_text(encoding="utf-8"))

    # Keep running
    try:
        while True:
            time.sleep(1)
            if server_proc.poll() is not None:
                print("[!] Local server process exited.")
                break
            if tunnel_proc.poll() is not None:
                print("[!] Tunnel process exited.")
                break
    except KeyboardInterrupt:
        cleanup()

if __name__ == "__main__":
    main()
