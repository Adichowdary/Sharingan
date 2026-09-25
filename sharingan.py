#!/usr/bin/env python3
"""
PhishGuard — Interactive Terminal CLI
A professional, terminal-based cybersecurity awareness and simulation tool
inspired by classic security utilities (XPHISHER / Social Engineering Toolkit).
Works on: Kali Linux, Ubuntu, Debian, Windows CMD / PowerShell, macOS
"""
import argparse
import os
import sys
import time
import socket
import platform
import shutil
import threading
from datetime import datetime, timezone, timedelta
from pathlib import Path


# ── Cross-platform color & encoding support ───────────────────────────
if sys.platform == "win32":
    os.system("")  # Enable ANSI colors in Windows CMD
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


def _c(code: str, text: str) -> str:
    """Apply ANSI color escape sequence."""
    return f"\033[{code}m{text}\033[0m"


def clear_screen():
    """Clear terminal screen cross-platform."""
    os.system("cls" if os.name == "nt" else "clear")


def get_local_ip() -> str:
    """Detect the local LAN IP for network sharing."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def print_banner():
    """Display the Sharingan cybersecurity terminal banner."""
    print(_c("1;31", r"""
  ███████╗██╗  ██╗ █████╗ ██████╗ ██╗███╗   ██╗ ██████╗  █████╗ ███╗   ██╗
  ██╔════╝██║  ██║██╔══██╗██╔══██╗██║████╗  ██║██╔════╝ ██╔══██╗████╗  ██║
  ███████╗███████║███████║██████╔╝██║██╔██╗ ██║██║  ███╗███████║██╔██╗ ██║
  ╚════██║██╔══██║██╔══██║██╔══██╗██║██║╚██╗██║██║   ██║██╔══██║██║╚██╗██║
  ███████║██║  ██║██║  ██║██║  ██║██║██║ ╚████║╚██████╔╝██║  ██║██║ ╚████║
  ╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝╚═╝  ╚═══╝ ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═══╝
"""))
    print(_c("1;31", "  [:: 👁️  SHARINGAN — Cybersecurity Awareness & Simulation Platform ::]"))
    print(_c("1;90", f"  [:: Version: 2.0.0 | Platform: Kali Linux / Windows CMD ::]"))
    print()


# ── System Diagnostics ────────────────────────────────────────────────
def cmd_check():
    """Run full system health diagnostics in terminal."""
    print_banner()
    print(_c("1;33", "  [*] Running System Health Diagnostics...\n"))
    passed, total = 0, 0

    def _ch(label, cond, detail_ok="OK", detail_fail="FAIL"):
        nonlocal passed, total
        total += 1
        if cond:
            passed += 1
            print(f"  {_c('1;32', '[✓]')} {label:<24}: {_c('32', detail_ok)}")
        else:
            print(f"  {_c('1;31', '[✗]')} {label:<24}: {_c('31', detail_fail)}")

    v = sys.version_info
    _ch("Python Runtime", v >= (3, 9), f"{v.major}.{v.minor}.{v.micro}", "Upgrade to Python 3.9+ required")
    _ch("Operating System", True, f"{platform.system()} ({platform.machine()})")

    pkgs = ["fastapi", "uvicorn", "sqlalchemy", "jose", "bcrypt", "qrcode", "rich", "jinja2", "requests", "cryptography"]
    for pkg in pkgs:
        try:
            __import__(pkg)
            _ch(f"Module: {pkg}", True, "installed")
        except ImportError:
            _ch(f"Module: {pkg}", False, detail_fail="NOT installed")

    db_path = Path(__file__).parent / "phishguard.db"
    _ch("Database Storage", db_path.exists(), f"Found ({db_path.stat().st_size} bytes)" if db_path.exists() else "", "Will be initialized on first run")

    print(f"\n  Result: {_c('1;32' if passed == total else '1;33', f'{passed}/{total}')} checks passed.\n")
    input(_c("90", "  Press Enter to return to menu..."))


# ── Setup ─────────────────────────────────────────────────────────────
def cmd_setup():
    """Install dependencies and verify environment."""
    print_banner()
    print(_c("1;33", "  [*] Running Environment Setup...\n"))
    req_file = Path(__file__).parent / "requirements.txt"
    if req_file.exists():
        print(_c("36", "  [+] Installing python dependencies..."))
        res = subprocess.run([sys.executable, "-m", "pip", "install", "-r", str(req_file)])
        if res.returncode == 0:
            print(_c("1;32", "  [✓] All dependencies installed successfully."))
        else:
            print(_c("1;31", "  [✗] pip install encountered an error."))
    else:
        print(_c("1;31", f"  [✗] {req_file} not found."))
    print()
    input(_c("90", "  Press Enter to return to menu..."))


# ── Interactive Drill Runner ──────────────────────────────────────────
def run_interactive_drill(default_redirect: str = "", drill_type_label: str = "Drill"):
    """Run an interactive simulation drill entirely from the terminal."""
    print_banner()
    print(_c("1;35", f"  [+] Configure Simulation: {drill_type_label}\n"))

    # 1. Prompt Email
    default_email = "admin@lab.local"
    raw_email = input(_c("1;37", f"  [?] Enter Notification Email [{default_email}]: ")).strip()
    notify_email = raw_email if raw_email else default_email

    # 2. Prompt Redirect URL
    if default_redirect:
        raw_redirect = input(_c("1;37", f"  [?] Enter Target Redirect URL [{default_redirect}]: ")).strip()
        redirect_url = raw_redirect if raw_redirect else default_redirect
    else:
        redirect_url = input(_c("1;37", "  [?] Enter Educational Redirect URL (e.g., YouTube link): ")).strip()
        if not redirect_url:
            redirect_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

    # 3. Prompt Port
    raw_port = input(_c("1;37", "  [?] Enter Server Port [8000]: ")).strip()
    port = int(raw_port) if raw_port.isdigit() else 8000

    print()
    print(_c("1;33", "  [*] Initializing drill environment and database..."))

    # Initialize DB & create campaign programmatically
    from app.database import init_db, SessionLocal
    from app.models import Campaign, CampaignTarget, Event, User
    from app.auth import hash_password

    init_db()
    db = SessionLocal()

    user = db.query(User).first()
    if not user:
        user = User(username="admin", password_hash=hash_password("AdminPassword123!"))
        db.add(user)
        db.commit()
        db.refresh(user)

    now_str = datetime.now(timezone.utc).strftime("%b %d, %H:%M")
    campaign = Campaign(
        name=f"Terminal Drill ({now_str})",
        description=f"Interactive terminal drill -> {redirect_url}",
        campaign_type="terminal_drill",
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        user_id=user.id,
        notification_email=notify_email,
        notification_frequency="immediate",
        notifications_enabled=True,
        authorized_simulation=True,
        redirect_url=redirect_url,
    )
    db.add(campaign)
    db.commit()
    db.refresh(campaign)

    target = CampaignTarget(
        campaign_id=campaign.id,
        name="Participant",
        email="",
    )
    db.add(target)
    db.commit()
    db.refresh(target)

    cid = campaign.id
    token = target.token
    db.close()

    # Start background uvicorn server quietly
    import uvicorn
    from app.main import app

    server_config = uvicorn.Config(
        app=app,
        host="0.0.0.0",
        port=port,
        log_level="error",
        access_log=False,
    )
    server = uvicorn.Server(server_config)
    server_thread = threading.Thread(target=server.run, daemon=True)
    server_thread.start()

    time.sleep(1.0)  # Allow server to bind

    local_ip = get_local_ip()
    local_url = f"http://127.0.0.1:{port}/t/{token}"
    lan_url = f"http://{local_ip}:{port}/t/{token}"

    clear_screen()
    print_banner()

    print(_c("1;32", "  [✓] Simulation Server Started Successfully!\n"))
    print(_c("1;37", f"  [*] Local Link   : ") + _c("1;36", local_url))
    print(_c("1;37", f"  [*] Network Link : ") + _c("1;36", lan_url))
    print(_c("1;37", f"  [*] Alerts Email : ") + _c("1;33", notify_email))
    print(_c("1;37", f"  [*] Destination  : ") + _c("1;35", redirect_url))
    print()

    # Print terminal ASCII QR Code
    try:
        import qrcode
        print(_c("1;37", "  [*] Terminal QR Code (Scan with Mobile Camera):"))
        qr = qrcode.QRCode(border=1)
        qr.add_data(lan_url)
        qr.print_ascii(invert=True)
        print()
    except Exception:
        pass

    print(_c("1;34", "  " + "=" * 70))
    print(_c("1;32", "  [LIVE TELEMETRY MONITOR] — Listening for participant activity..."))
    print(_c("1;90", "  (Press Ctrl+C to stop the simulation session)"))
    print(_c("1;34", "  " + "=" * 70 + "\n"))

    # Live telemetry monitor loop
    last_event_id = 0
    total_clicks = 0
    total_completed = 0

    try:
        while True:
            time.sleep(1.2)
            db = SessionLocal()
            new_events = (
                db.query(Event)
                .filter(Event.campaign_id == cid, Event.id > last_event_id)
                .order_by(Event.id.asc())
                .all()
            )

            for ev in new_events:
                last_event_id = ev.id
                time_now = datetime.now().strftime("%H:%M:%S")

                if ev.event_type == "click":
                    total_clicks += 1
                    print(_c("1;33", f"  [+] [{time_now}] 🎯 LINK OPENED BY PARTICIPANT!"))
                    print(f"      ├── IP Address : {_c('1;37', ev.ip_address or 'Unknown')}")
                    print(f"      ├── Device / OS: {_c('1;36', f'{ev.os_family} ({ev.device_category})')}")
                    print(f"      ├── Browser    : {_c('1;36', ev.browser_family or 'Browser')}")
                    print(f"      ├── Session ID : {_c('1;90', ev.session_id)}")
                    print(f"      └── Alert      : {_c('32', f'Notification sent -> {notify_email}')}\n")

                elif ev.event_type in ("submit", "training_completed"):
                    total_completed += 1
                    print(_c("1;32", f"  [+] [{time_now}] 🚀 DRILL COMPLETED & ACKNOWLEDGED!"))
                    print(f"      ├── Session ID : {_c('1;90', ev.session_id)}")
                    print(f"      └── Action     : {_c('1;35', f'Forwarded to educational URL -> {redirect_url}')}\n")

            db.close()

    except KeyboardInterrupt:
        print()
        print(_c("1;31", "\n  [!] Stopping simulation session..."))
        server.should_exit = True
        time.sleep(0.5)
        print(_c("1;33", "  ────────────────────────────────────────────────────────"))
        print(_c("1;37", "  📊 SESSION SUMMARY:"))
        print(f"     • Total Participant Clicks    : {_c('1;33', str(total_clicks))}")
        print(f"     • Total Completions Verified : {_c('1;32', str(total_completed))}")
        print(f"     • Notification Email Target   : {_c('1;36', notify_email)}")
        print(_c("1;33", "  ────────────────────────────────────────────────────────\n"))
        input(_c("90", "  Press Enter to return to main menu..."))


# ── Interactive Menu Loop ─────────────────────────────────────────────
def interactive_menu():
    """Main terminal menu matching classic security CLI tools."""
    while True:
        clear_screen()
        print_banner()

        print(_c("1;37", "  [:: SELECT AN OPTION ::]\n"))
        print(_c("1;36", "  [01]") + " YouTube Security Awareness Drill")
        print(_c("1;36", "  [02]") + " Custom Educational Redirect Drill")
        print(_c("1;36", "  [03]") + " Run Health Diagnostics Check")
        print(_c("1;36", "  [04]") + " Install / Update Dependencies")
        print(_c("1;31", "  [00]") + " Exit\n")

        choice = input(_c("1;31", "  sharingan > ")).strip()

        if choice in ("1", "01"):
            run_interactive_drill(
                default_redirect="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                drill_type_label="YouTube Security Awareness Drill",
            )
        elif choice in ("2", "02"):
            run_interactive_drill(
                default_redirect="",
                drill_type_label="Custom Educational Redirect Drill",
            )
        elif choice in ("3", "03"):
            clear_screen()
            cmd_check()
        elif choice in ("4", "04"):
            clear_screen()
            cmd_setup()
        elif choice in ("0", "00", "exit", "quit"):
            print(_c("1;31", "\n  [!] Exiting Sharingan. Stay secure!\n"))
            sys.exit(0)


# ── Main Entrypoint ───────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        prog="sharingan",
        description="Sharingan — Terminal-Based Cybersecurity Awareness & Simulation Platform",
    )
    parser.add_argument("command", nargs="?", choices=["menu", "start", "setup", "check"], default="menu", help="Execution mode (default: interactive menu)")
    parser.add_argument("--host", default=os.getenv("HOST", "0.0.0.0"), help="Bind host")
    parser.add_argument("--port", type=int, default=int(os.getenv("PORT", "8000")), help="Bind port")
    parser.add_argument("--no-reload", action="store_true", help="Disable auto-reload")

    args = parser.parse_args()

    if args.command == "setup":
        cmd_setup()
    elif args.command == "check":
        cmd_check()
    elif args.command == "start":
        # Direct server start without menu
        from app.main import app
        import uvicorn
        print_banner()
        print(_c("1;32", f"  [+] Starting PhishGuard Server on {args.host}:{args.port}...\n"))
        uvicorn.run("app.main:app", host=args.host, port=args.port, reload=not args.no_reload)
    else:
        # Default: Interactive Terminal CLI
        interactive_menu()


if __name__ == "__main__":
    main()
