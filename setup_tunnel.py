"""PlanetariumAI - Cloudflare Tunnel Setup & Remote Exposure Script.

Implements Specification 08 (Global Remote Access):
1. Verifies or downloads the official `cloudflared` executable.
2. Checks that the local FastAPI Host Server is active on port 8000.
3. Initializes a secure Cloudflare Tunnel mapping localhost:8000 to the public internet.
4. Extracts and displays the public HTTPS URL for global access from any browser or phone.
"""

import argparse
import os
import platform
import re
import shutil
import subprocess
import sys
import time
import urllib.request
from typing import Optional


# Official Cloudflare download URLs by OS and Architecture
CLOUDFLARED_DOWNLOAD_URLS = {
    "windows_amd64": "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe",
    "linux_amd64": "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64",
    "linux_arm64": "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64",
    "darwin_amd64": "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-darwin-amd64",
    "darwin_arm64": "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-darwin-arm64",
}


def get_platform_key() -> str:
    """Return platform key for downloading cloudflared."""
    sys_name = platform.system().lower()
    machine = platform.machine().lower()

    is_arm = "arm" in machine or "aarch" in machine
    arch = "arm64" if is_arm else "amd64"

    if sys_name == "windows":
        return "windows_amd64"
    elif sys_name == "darwin":
        return f"darwin_{arch}"
    elif sys_name == "linux":
        return f"linux_{arch}"
    return "linux_amd64"


def find_or_download_cloudflared(bin_dir: Optional[str] = None) -> str:
    """Locate existing cloudflared binary or download it if missing."""
    # 1. Check system PATH
    system_path = shutil.which("cloudflared")
    if system_path:
        print(f"[Tunnel] Found system cloudflared at: {system_path}")
        return system_path

    # 2. Check local tools/bin directory
    root_dir = os.path.dirname(os.path.abspath(__file__))
    target_dir = bin_dir or os.path.join(root_dir, "tools", "bin")
    os.makedirs(target_dir, exist_ok=True)

    exe_name = "cloudflared.exe" if platform.system() == "Windows" else "cloudflared"
    local_path = os.path.join(target_dir, exe_name)

    if os.path.exists(local_path):
        print(f"[Tunnel] Found local cloudflared at: {local_path}")
        return local_path

    # 3. Download cloudflared binary
    plat_key = get_platform_key()
    url = CLOUDFLARED_DOWNLOAD_URLS.get(plat_key, CLOUDFLARED_DOWNLOAD_URLS["linux_amd64"])
    print(f"[Tunnel] cloudflared not found on PATH. Downloading from {url}...")

    def reporthook(block_num, block_size, total_size):
        if total_size > 0:
            downloaded = block_num * block_size
            pct = min(100.0, (downloaded / total_size) * 100.0)
            sys.stdout.write(f"\r[Tunnel] Downloading cloudflared: {pct:.1f}% ({downloaded // (1024*1024)}MB / {total_size // (1024*1024)}MB)")
            sys.stdout.flush()

    try:
        urllib.request.urlretrieve(url, local_path, reporthook)
        print()
        if platform.system() != "Windows":
            os.chmod(local_path, 0o755)
        print(f"[Tunnel] cloudflared downloaded successfully to: {local_path}")
        return local_path
    except Exception as e:
        raise RuntimeError(f"Failed to download cloudflared from {url}: {e}")


def is_local_server_running(port: int = 8000) -> bool:
    """Check if the local FastAPI server is accepting HTTP connections."""
    url = f"http://localhost:{port}/"
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=1.5) as resp:
            return resp.status in (200, 301, 302, 307, 308, 404)
    except Exception:
        # Try GET if HEAD is not supported
        try:
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=1.5) as resp:
                return resp.status in (200, 301, 302, 307, 308, 404)
        except Exception:
            return False


def start_quick_tunnel(cloudflared_path: str, port: int = 8000):
    """Start a TryCloudflare quick tunnel and extract the public HTTPS URL."""
    import tempfile
    
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(line_buffering=True)

    print("=" * 70, flush=True)
    print("          PLANETARIUMAI - GLOBAL CLOUDFLARE TUNNEL INITIALIZER", flush=True)
    print("=" * 70, flush=True)

    # Health check local server
    if not is_local_server_running(port):
        print(f"[Warning] FastAPI backend does not appear to be running on http://localhost:{port}/.", flush=True)
        print("          Start the server using: python -m uvicorn main:app --port 8000 (inside /core)", flush=True)
        print("          Continuing tunnel initialization anyway...\n", flush=True)
    else:
        print(f"[Health] Local FastAPI Host Server verified running on http://localhost:{port}/\n", flush=True)

    temp_log = os.path.join(tempfile.gettempdir(), f"cloudflared_{os.getpid()}.log")
    if os.path.exists(temp_log):
        try:
            os.remove(temp_log)
        except OSError:
            pass

    cmd = [
        cloudflared_path,
        "tunnel",
        "--url",
        f"http://localhost:{port}",
        "--logfile",
        temp_log
    ]

    print(f"[Tunnel] Launching command: {' '.join(cmd)}", flush=True)
    print("[Tunnel] Negotiating secure tunnel with Cloudflare Edge Network...\n", flush=True)

    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

    url_pattern = re.compile(r"https://[a-zA-Z0-9\-]+\.trycloudflare\.com")
    assigned_url = None
    last_pos = 0

    try:
        # Poll the logfile for the assigned quick tunnel URL
        while proc.poll() is None:
            if os.path.exists(temp_log):
                with open(temp_log, "r", encoding="utf-8", errors="ignore") as f:
                    f.seek(last_pos)
                    new_data = f.read()
                    last_pos = f.tell()

                if new_data:
                    for line in new_data.splitlines():
                        match = url_pattern.search(line)
                        if match and not assigned_url:
                            assigned_url = match.group(0)
                            print("\n" + "#" * 70, flush=True)
                            print("                     SECURE GLOBAL REMOTE ACCESS READY", flush=True)
                            print("#" * 70, flush=True)
                            print(f"\n  PUBLIC WEB APP URL:  {assigned_url}", flush=True)
                            print(f"  LOCAL SERVER:        http://localhost:{port}", flush=True)
                            print(f"  WEBSOCKET ENDPOINT:  {assigned_url.replace('https://', 'wss://')}/ws/audio\n", flush=True)
                            print("  Share this URL to access your PlanetariumAI kiosk from any device", flush=True)
                            print("  (phone, tablet, laptop) anywhere in the world without port-forwarding!", flush=True)
                            print("\n" + "#" * 70 + "\n", flush=True)
                            print("[Tunnel] Tunnel is active. Press CTRL+C to close the tunnel.\n", flush=True)

                        if "ERR" in line or "error" in line.lower():
                            print(f"[Cloudflare Log] {line.strip()}", flush=True)
                        elif "Registered tunnel connection" in line:
                            print(f"[Cloudflare Log] {line.strip()}", flush=True)

            time.sleep(0.5)

        proc.wait()
    except KeyboardInterrupt:
        print("\n[Tunnel] Shutting down Cloudflare Tunnel...", flush=True)
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()
        print("[Tunnel] Tunnel closed. Remote access disabled.", flush=True)
    finally:
        if os.path.exists(temp_log):
            try:
                os.remove(temp_log)
            except OSError:
                pass


def setup_named_tunnel(cloudflared_path: str, tunnel_name: str, domain: Optional[str] = None):
    """Guide user through Cloudflare Zero Trust named tunnel configuration."""
    print("=" * 70)
    print("        CLOUDFLARE ZERO TRUST / NAMED TUNNEL CONFIGURATION")
    print("=" * 70)
    print("\n1. Step 1: Authenticate with Cloudflare...")
    subprocess.run([cloudflared_path, "tunnel", "login"])

    print(f"\n2. Step 2: Creating named tunnel '{tunnel_name}'...")
    subprocess.run([cloudflared_path, "tunnel", "create", tunnel_name])

    if domain:
        print(f"\n3. Step 3: Routing DNS for '{domain}' to '{tunnel_name}'...")
        subprocess.run([cloudflared_path, "tunnel", "route", "dns", tunnel_name, domain])

    print("\nNamed tunnel setup complete. Run with: cloudflared tunnel run", tunnel_name)


def main():
    parser = argparse.ArgumentParser(description="PlanetariumAI Cloudflare Tunnel Initializer")
    parser.add_argument("--port", type=int, default=8000, help="Local port to expose (default: 8000)")
    parser.add_argument("--check-only", action="store_true", help="Verify cloudflared and local server health without starting tunnel")
    parser.add_argument("--named", type=str, default=None, help="Name for a Cloudflare Zero Trust named tunnel")
    parser.add_argument("--domain", type=str, default=None, help="Custom domain for the named tunnel")
    parser.add_argument("--bin-dir", type=str, default=None, help="Custom directory for cloudflared binary")
    args = parser.parse_args()

    cloudflared_path = find_or_download_cloudflared(args.bin_dir)

    if args.check_only:
        server_ok = is_local_server_running(args.port)
        print(f"[Check] cloudflared binary: {cloudflared_path}")
        print(f"[Check] Local server port {args.port}: {'RUNNING' if server_ok else 'STOPPED'}")
        sys.exit(0 if server_ok else 1)

    if args.named:
        setup_named_tunnel(cloudflared_path, args.named, args.domain)
    else:
        start_quick_tunnel(cloudflared_path, port=args.port)


if __name__ == "__main__":
    main()
