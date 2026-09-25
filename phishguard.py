#!/usr/bin/env python3
"""
PhishGuard — Cross-Platform CLI Entry Point
Works on: Kali Linux, Ubuntu, Debian, Arch, Windows CMD/PowerShell, macOS

Usage:
    python phishguard.py                  # Start server (default)
    python phishguard.py start            # Start server
    python phishguard.py setup            # First-time setup & dependency install
    python phishguard.py check            # System health check
    python phishguard.py --host 0.0.0.0   # Custom host
    python phishguard.py --port 9000      # Custom port
"""
import argparse
import os
import sys
import subprocess
import platform
import shutil
from pathlib import Path


# ── Cross-platform color & encoding support ───────────────────────────
if sys.platform == "win32":
    # Enable ANSI colors in Windows CMD
    os.system("")  # Triggers VT100 mode
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    if hasattr(sys.stderr, "reconfigure"):
        try:
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def _c(code, text):
    """Apply ANSI color. Falls back gracefully on old terminals."""
    return f"\033[{code}m{text}\033[0m"


def banner():
    print()
    try:
        print(_c("95", "  +======================================================+"))
        print(_c("95", "  |") + _c("1;96", "   [+] PhishGuard v2.0                                ") + _c("95", "|"))
        print(_c("95", "  |") + _c("37", "   Phishing Simulation & Security Analysis Platform  ") + _c("95", "|"))
        print(_c("95", "  |") + _c("90", f"   Platform: {platform.system()} {platform.release():<30s}     ") + _c("95", "|"))
        print(_c("95", "  |") + _c("90", f"   Python:   {platform.python_version():<30s}     ") + _c("95", "|"))
        print(_c("95", "  +======================================================+"))
    except Exception:
        print("  PhishGuard v2.0 - Phishing Simulation & Security Analysis Platform")
    print()


# ── Setup command ─────────────────────────────────────────────────────
def cmd_setup():
    """Install dependencies and verify the environment."""
    banner()
    print(_c("1;33", "  ⚙  Running first-time setup…\n"))

    # 1. Check Python version
    v = sys.version_info
    if v < (3, 9):
        print(_c("1;31", f"  ✗ Python {v.major}.{v.minor} detected — need 3.9+"))
        sys.exit(1)
    print(_c("32", f"  ✓ Python {v.major}.{v.minor}.{v.micro}"))

    # 2. Check pip
    pip = shutil.which("pip3") or shutil.which("pip")
    if not pip:
        print(_c("31", "  ✗ pip not found — install python3-pip"))
        sys.exit(1)
    print(_c("32", f"  ✓ pip found: {pip}"))

    # 3. Install requirements
    req_file = Path(__file__).parent / "requirements.txt"
    if req_file.exists():
        print(_c("36", "\n  📦 Installing dependencies…"))
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", str(req_file)],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            print(_c("31", "  ✗ pip install failed:"))
            print(result.stderr[-500:] if result.stderr else "Unknown error")
            sys.exit(1)
        print(_c("32", "  ✓ All dependencies installed"))
    else:
        print(_c("31", f"  ✗ {req_file} not found"))
        sys.exit(1)

    # 4. Verify imports
    print(_c("36", "\n  🔍 Verifying imports…"))
    try:
        import fastapi, uvicorn, sqlalchemy, jose, passlib, qrcode, rich, jinja2  # noqa
        print(_c("32", "  ✓ All core packages importable"))
    except ImportError as e:
        print(_c("31", f"  ✗ Import failed: {e}"))
        sys.exit(1)

    # 5. Create .env template if not exists
    env_file = Path(__file__).parent / ".env"
    if not env_file.exists():
        env_file.write_text(
            "# PhishGuard Environment Configuration\n"
            "# Rename this file to .env and fill in your values\n\n"
            "SECRET_KEY=\n"
            "BASE_URL=http://localhost:8000\n"
            "HOST=0.0.0.0\n"
            "PORT=8000\n\n"
            "# SMTP (optional — can also configure in dashboard)\n"
            "SMTP_HOST=\n"
            "SMTP_PORT=587\n"
            "SMTP_USERNAME=\n"
            "SMTP_PASSWORD=\n"
            "NOTIFICATION_FROM=\n",
            encoding="utf-8",
        )
        print(_c("32", "  ✓ .env template created"))

    print(_c("1;32", "\n  ✅ Setup complete! Run:  python phishguard.py start\n"))


# ── Health check command ──────────────────────────────────────────────
def cmd_check():
    """Run system health diagnostics."""
    banner()
    print(_c("1;33", "  🏥 System Health Check\n"))
    checks_passed = 0
    checks_total = 0

    def _check(label, condition, detail_ok="OK", detail_fail="FAIL"):
        nonlocal checks_passed, checks_total
        checks_total += 1
        if condition:
            checks_passed += 1
            print(f"  {_c('32', '✓')} {label}: {_c('32', detail_ok)}")
        else:
            print(f"  {_c('31', '✗')} {label}: {_c('31', detail_fail)}")

    # Python
    v = sys.version_info
    _check("Python ≥ 3.9", v >= (3, 9), f"{v.major}.{v.minor}.{v.micro}", f"{v.major}.{v.minor} — upgrade required")

    # OS
    _check("Operating System", True, f"{platform.system()} {platform.release()}")

    # Packages
    pkgs = ["fastapi", "uvicorn", "sqlalchemy", "jose", "passlib", "qrcode", "rich", "jinja2", "requests", "cryptography"]
    for pkg in pkgs:
        try:
            __import__(pkg)
            _check(f"Package: {pkg}", True, "installed")
        except ImportError:
            _check(f"Package: {pkg}", False, detail_fail="NOT installed")

    # Database file
    db_path = Path(__file__).parent / "phishguard.db"
    _check("Database", db_path.exists(), f"Found ({db_path.stat().st_size} bytes)" if db_path.exists() else "", "Not created yet (will be created on first run)")

    # Network
    import socket
    port = int(os.getenv("PORT", "8000"))
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex(("127.0.0.1", port))
        sock.close()
        if result == 0:
            _check(f"Port {port}", True, "Server is running")
        else:
            _check(f"Port {port}", True, "Available (server not running)")
    except Exception:
        _check(f"Port {port}", True, "Check skipped")

    print(f"\n  Result: {_c('1;32' if checks_passed == checks_total else '1;33', f'{checks_passed}/{checks_total}')} checks passed\n")


# ── Start server command ──────────────────────────────────────────────
def cmd_start(host: str, port: int, reload: bool):
    """Start the PhishGuard server."""
    banner()

    # Load .env if present
    env_file = Path(__file__).parent / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, val = line.partition("=")
                if val and key.strip() not in os.environ:
                    os.environ[key.strip()] = val.strip()

    # Override from CLI args
    os.environ["HOST"] = host
    os.environ["PORT"] = str(port)

    try:
        import uvicorn
    except ImportError:
        print(_c("31", "  ✗ uvicorn not installed. Run: python phishguard.py setup"))
        sys.exit(1)

    base_url = os.getenv("BASE_URL", f"http://{host}:{port}")
    print(_c("32", f"  🌐 Dashboard:  {base_url}"))
    print(_c("32", f"  📚 API Docs:   {base_url}/docs"))
    print(_c("32", f"  🖥️  Host:       {host}:{port}"))
    print(_c("90", f"  ⏹  Press Ctrl+C to stop\n"))

    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info",
    )


# ── Main ──────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        prog="phishguard",
        description="PhishGuard — Phishing Simulation & Security Analysis Platform",
    )
    sub = parser.add_subparsers(dest="command")

    # start
    start_p = sub.add_parser("start", help="Start the PhishGuard server")
    start_p.add_argument("--host", default=os.getenv("HOST", "0.0.0.0"), help="Bind host (default: 0.0.0.0)")
    start_p.add_argument("--port", type=int, default=int(os.getenv("PORT", "8000")), help="Bind port (default: 8000)")
    start_p.add_argument("--no-reload", action="store_true", help="Disable auto-reload")

    # setup
    sub.add_parser("setup", help="Install dependencies & verify environment")

    # check
    sub.add_parser("check", help="Run system health diagnostics")

    # Also support flags on root command for quick start
    parser.add_argument("--host", default=os.getenv("HOST", "0.0.0.0"), help="Bind host")
    parser.add_argument("--port", type=int, default=int(os.getenv("PORT", "8000")), help="Bind port")
    parser.add_argument("--no-reload", action="store_true", help="Disable auto-reload")

    args = parser.parse_args()

    if args.command == "setup":
        cmd_setup()
    elif args.command == "check":
        cmd_check()
    elif args.command == "start":
        cmd_start(args.host, args.port, not args.no_reload)
    else:
        # Default: start server
        cmd_start(args.host, args.port, not args.no_reload)


if __name__ == "__main__":
    main()
