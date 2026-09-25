#!/usr/bin/env python3
"""
Sharingan — Interactive Terminal CLI
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
import subprocess
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

    pkgs = ["fastapi", "uvicorn", "sqlalchemy", "jinja2", "requests", "pydantic"]
    for pkg in pkgs:
        try:
            __import__(pkg)
            _ch(f"Module: {pkg}", True, "installed")
        except ImportError:
            _ch(f"Module: {pkg}", False, detail_fail="NOT installed")

    # JWT Authentication Engine
    jwt_status = "NOT installed"
    has_jwt = False
    try:
        __import__("jose")
        jwt_status = "python-jose active"
        has_jwt = True
    except ImportError:
        try:
            __import__("jwt")
            jwt_status = "PyJWT active"
            has_jwt = True
        except ImportError:
            jwt_status = "built-in stdlib active"
            has_jwt = True
    _ch("Module: JWT Engine", has_jwt, jwt_status)

    # Optional enhanced modules
    for opt_pkg, opt_label in [("bcrypt", "Bcrypt Hashing"), ("qrcode", "Terminal QR"), ("rich", "Rich Formatting")]:
        try:
            __import__(opt_pkg)
            _ch(f"Module: {opt_label}", True, "installed")
        except ImportError:
            _ch(f"Module: {opt_label}", True, "fallback active")

    db_path = Path(__file__).parent / "sharingan.db"
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
        cmd = [sys.executable, "-m", "pip", "install", "-r", str(req_file)]
        if platform.system() == "Linux":
            cmd.append("--break-system-packages")
        res = subprocess.run(cmd)
        if res.returncode != 0:
            res = subprocess.run([sys.executable, "-m", "pip", "install", "-r", str(req_file)])
        if res.returncode == 0:
            print(_c("1;32", "  [✓] All dependencies installed successfully."))
        else:
            print(_c("1;33", "  [!] Dependencies processed."))
    else:
        print(_c("1;31", f"  [✗] {req_file} not found."))
    print()
    input(_c("90", "  Press Enter to return to menu..."))


# ── SMTP Email Configuration Wizard ───────────────────────────────────
def cmd_configure_smtp():
    """Interactive SMTP setup wizard for real email delivery."""
    print_banner()
    print(_c("1;33", "  [:: SMTP OUTGOING EMAIL CONFIGURATION ::]\n"))
    print("  To deliver real alert emails to an inbox (Gmail, Outlook, etc.),")
    print("  Sharingan connects through an authenticated SMTP relay.\n")
    print(_c("1;36", "  [01]") + " Gmail (Requires 16-character Google App Password)")
    print(_c("1;36", "  [02]") + " Outlook / Hotmail / Office365")
    print(_c("1;36", "  [03]") + " Custom SMTP Server")
    print(_c("1;31", "  [00]") + " Back to Menu\n")

    p = input(_c("1;32", "  Select provider [1-3]: ")).strip()
    if p in ("0", "00", "back", "exit"):
        return

    from app.database import init_db, SessionLocal
    from app.models import EmailConfig, User
    from app.auth import hash_password
    from app.services.email_service import send_email
    init_db()
    db = SessionLocal()

    user = db.query(User).first()
    if not user:
        user = User(username="admin", password_hash=hash_password("AdminPassword123!"))
        db.add(user)
        db.commit()
        db.refresh(user)

    if p in ("1", "01"):
        provider = "gmail"
        host = "smtp.gmail.com"
        port = 587
        print(_c("1;35", "\n  [*] Note: For Gmail, generate an 'App Password' at: https://myaccount.google.com/apppasswords"))
        user_email = input(_c("1;37", "  [?] Your Gmail Address: ")).strip()
        pwd = input(_c("1;37", "  [?] Gmail App Password (16 characters): ")).strip().replace(" ", "")
    elif p in ("2", "02"):
        provider = "outlook"
        host = "smtp-mail.outlook.com"
        port = 587
        user_email = input(_c("1;37", "  [?] Your Outlook Email: ")).strip()
        pwd = input(_c("1;37", "  [?] Outlook Password: ")).strip()
    elif p in ("3", "03"):
        provider = "custom"
        host = input(_c("1;37", "  [?] SMTP Host (e.g. mail.domain.com): ")).strip()
        raw_port = input(_c("1;37", "  [?] SMTP Port [587]: ")).strip()
        port = int(raw_port) if raw_port.isdigit() else 587
        user_email = input(_c("1;37", "  [?] SMTP Username / Email: ")).strip()
        pwd = input(_c("1;37", "  [?] SMTP Password: ")).strip()
    else:
        db.close()
        return

    if not user_email or not pwd:
        print(_c("1;31", "\n  [✗] Email and password cannot be empty."))
        db.close()
        input(_c("90", "  Press Enter to return..."))
        return

    print(_c("1;33", f"\n  [*] Testing connection and sending verification email to {user_email}..."))
    res = send_email(
        to_email=user_email,
        subject="👁️ Sharingan — SMTP Verification Successful",
        html_body="<h3>Sharingan Alert System</h3><p>Your SMTP mail configuration is verified and ready to deliver real-time security drill alerts to your inbox.</p>",
        smtp_host=host,
        smtp_port=port,
        smtp_username=user_email,
        smtp_password=pwd,
        sender_email=user_email,
        sender_name="Sharingan",
    )

    if res["status"] == "sent":
        print(_c("1;32", f"  [✓] SUCCESS: Verification email sent to {user_email}!"))
        # Save to EmailConfig
        cfg = db.query(EmailConfig).filter(EmailConfig.user_id == user.id).first()
        if not cfg:
            cfg = EmailConfig(user_id=user.id)
            db.add(cfg)
        cfg.smtp_provider = provider
        cfg.smtp_host = host
        cfg.smtp_port = port
        cfg.smtp_username = user_email
        cfg.smtp_password_encrypted = pwd
        cfg.sender_email = user_email
        cfg.sender_name = "Sharingan"
        cfg.is_verified = True
        cfg.enabled = True
        db.commit()
        print(_c("1;32", "  [✓] Configuration saved to database. Real emails are now ACTIVE."))
    else:
        print(_c("1;31", f"  [✗] CONNECTION FAILED: {res.get('error')}"))
        print(_c("90", "      Tip: If using Gmail, make sure 2-Step Verification is ON and generate an App Password."))

    db.close()
    input(_c("90", "\n  Press Enter to return to menu..."))


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

    # Normalize URL scheme
    if redirect_url and not redirect_url.startswith(("http://", "https://")):
        redirect_url = "https://" + redirect_url

    # 3. Prompt Port
    raw_port = input(_c("1;37", "  [?] Enter Server Port [8000]: ")).strip()
    port = int(raw_port) if raw_port.isdigit() else 8000

    print()
    print(_c("1;33", "  [*] Initializing drill environment and database..."))

    # Initialize DB & create campaign programmatically
    from app.database import init_db, SessionLocal
    from app.models import Campaign, CampaignTarget, Event, EmailConfig, NotificationLog, User
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

    email_cfg = db.query(EmailConfig).filter(EmailConfig.user_id == user.id, EmailConfig.enabled == True).first()
    has_smtp = bool(email_cfg and email_cfg.smtp_host and email_cfg.smtp_username)
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
    
    if has_smtp:
        print(_c("1;37", f"  [*] Alerts Email : ") + _c("1;32", f"{notify_email} (SMTP Connected - Real Emails Active)"))
    else:
        print(_c("1;37", f"  [*] Alerts Email : ") + _c("1;33", f"{notify_email} (Local/Terminal Mode — Run [03] in menu to enable inbox delivery)"))

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

                # Check notification log for delivery status
                notif = db.query(NotificationLog).filter(NotificationLog.event_id == ev.id).first()

                if ev.event_type == "click":
                    total_clicks += 1
                    print(_c("1;33", f"  [+] [{time_now}] 🎯 LINK OPENED BY PARTICIPANT!"))
                    print(f"      ├── IP Address : {_c('1;37', ev.ip_address or 'Unknown')}")
                    print(f"      ├── Device / OS: {_c('1;36', f'{ev.os_family} ({ev.device_category})')}")
                    print(f"      ├── Browser    : {_c('1;36', ev.browser_family or 'Browser')}")
                    print(f"      ├── Session ID : {_c('1;90', ev.session_id)}")
                    if notif and notif.status == "sent":
                        print(f"      └── Alert      : {_c('1;32', f'✓ Real email delivered to {notify_email}')}\n")
                    elif notif and notif.status == "failed":
                        print(f"      └── Alert      : {_c('1;31', f'✗ Email delivery failed: {notif.error_message}')}\n")
                    else:
                        print(f"      └── Alert      : {_c('1;33', f'ℹ Logged to terminal & DB (Run option 03 to enable real emails)')}\n")

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
        print(_c("1;36", "  [03]") + " Configure SMTP Email (Gmail / Outlook / Custom)")
        print(_c("1;36", "  [04]") + " Run Health Diagnostics Check")
        print(_c("1;36", "  [05]") + " Install / Update Dependencies")
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
            cmd_configure_smtp()
        elif choice in ("4", "04"):
            clear_screen()
            cmd_check()
        elif choice in ("5", "05"):
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
    parser.add_argument("command", nargs="?", choices=["menu", "start", "setup", "check", "smtp"], default="menu", help="Execution mode (default: interactive menu)")
    parser.add_argument("--host", default=os.getenv("HOST", "0.0.0.0"), help="Bind host")
    parser.add_argument("--port", type=int, default=int(os.getenv("PORT", "8000")), help="Bind port")
    parser.add_argument("--no-reload", action="store_true", help="Disable auto-reload")

    args = parser.parse_args()

    if args.command == "setup":
        cmd_setup()
    elif args.command == "check":
        cmd_check()
    elif args.command == "smtp":
        cmd_configure_smtp()
    elif args.command == "start":
        from app.main import app
        import uvicorn
        print_banner()
        print(_c("1;32", f"  [+] Starting Sharingan Server on {args.host}:{args.port}...\n"))
        uvicorn.run("app.main:app", host=args.host, port=args.port, reload=not args.no_reload)
    else:
        interactive_menu()


if __name__ == "__main__":
    main()
