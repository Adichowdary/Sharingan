# 👁️ Sharingan v2.0

**Terminal-Based Cybersecurity Awareness & Simulation Platform**

An elite, interactive terminal security awareness training tool built for Kali Linux and Windows CMD/PowerShell. Designed for authorized red-team security drills and cybersecurity student training.

![Python](https://img.shields.io/badge/Python-3.9+-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green)
![License](https://img.shields.io/badge/License-MIT-purple)
![Platform](https://img.shields.io/badge/Platform-Kali%20|%20Windows%20|%20Linux%20|%20macOS-red)

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🎯 **Campaign Manager** | Create, manage, and track awareness training campaigns |
| 🔍 **URL Security Analyzer** | 8-point security analysis (HTTPS, TLS, redirects, entropy, phishing keywords, domain rep) |
| 📧 **Email Notifications** | Automated SMTP alerts on campaign events (immediate, batch, daily) |
| 📊 **Real-Time Dashboard** | Live event feed via Server-Sent Events (SSE) |
| 🗺️ **Location Visualization** | Consent-based location display on Leaflet/OpenStreetMap |
| 📱 **QR Code Generator** | Styled QR codes for campaign links |
| 🔐 **JWT Authentication** | Secure admin access with bcrypt password hashing |
| 🧾 **Audit Logs** | Complete action trail for compliance |
| 🚦 **Rate Limiting** | Per-IP request throttling |
| 🛡️ **Security Headers** | X-Frame-Options, X-XSS-Protection, CSP, HSTS |
| 📋 **Privacy Compliant** | Clear consent notices, no credential/cookie/keystroke collection |

---

## 📁 Project Structure

```
phishguard/
├── phishguard.py          # Cross-platform CLI entry point
├── run.py                 # Quick-start script
├── start.bat              # Windows double-click launcher
├── start.sh               # Kali / Linux launcher
├── requirements.txt       # Python dependencies
├── .gitignore
├── .env                   # Secrets (auto-generated, git-ignored)
│
├── app/
│   ├── __init__.py
│   ├── main.py            # FastAPI app + middleware + startup
│   ├── config.py          # Settings from environment variables
│   ├── database.py        # SQLite + SQLAlchemy setup
│   ├── models.py          # ORM models (User, Campaign, Event, EmailConfig, etc.)
│   ├── auth.py            # JWT auth + bcrypt
│   │
│   ├── routers/
│   │   ├── auth_router.py     # Login / Register / Profile
│   │   ├── campaigns.py       # Campaign CRUD + Targets + QR
│   │   ├── url_analyzer.py    # URL security scanning
│   │   ├── analytics.py       # Dashboard stats + campaign analytics
│   │   ├── landing.py         # Training landing pages (shown to targets)
│   │   ├── email_settings.py  # SMTP config CRUD + test
│   │   ├── notifications.py   # Notification log viewer
│   │   └── sse.py             # Server-Sent Events for live feed
│   │
│   ├── services/
│   │   ├── url_scanner.py         # 8-point URL analysis engine
│   │   ├── qr_generator.py        # QR code generation
│   │   ├── email_service.py       # SMTP sending + HTML templates
│   │   └── notification_queue.py  # Async queue + SSE bus + batch worker
│   │
│   └── static/
│       ├── index.html         # Dashboard SPA
│       ├── css/style.css      # Dark glassmorphism theme
│       └── js/app.js          # Dashboard logic
│
└── README.md
```

---

## 🚀 Quick Start

### 1️⃣ Clone the Repository

```bash
git clone https://github.com/<YOUR_USERNAME>/phishguard.git
cd phishguard
```

### 2️⃣ Setup (first time)

**Kali Linux / Ubuntu / Debian:**
```bash
chmod +x start.sh phishguard.py
./start.sh setup
```

**Windows CMD / PowerShell:**
```cmd
python phishguard.py setup
```

### 3️⃣ Start the Server

**Kali / Linux:**
```bash
./start.sh
# or
python3 phishguard.py start
# or with custom port
python3 phishguard.py start --port 9000
```

**Windows:**
```cmd
start.bat
REM or
python phishguard.py start
REM or with custom port
python phishguard.py start --port 9000
```

### 4️⃣ Open the Dashboard

Navigate to **http://localhost:8000** in your browser.

- First visit: create your admin account (username + password)
- All subsequent visits: login with your credentials

---

## 🖥️ Platform Compatibility

| Platform | Status | Notes |
|----------|--------|-------|
| Kali Linux 2024+ | ✅ Tested | `python3`, `pip3` pre-installed |
| Ubuntu 22.04+ | ✅ Tested | `sudo apt install python3 python3-pip python3-venv` |
| Debian 12+ | ✅ Tested | Same as Ubuntu |
| Arch Linux | ✅ Tested | `sudo pacman -S python python-pip` |
| Windows 10/11 | ✅ Tested | Python from python.org or Microsoft Store |
| Windows CMD | ✅ Tested | ANSI colors supported |
| PowerShell | ✅ Tested | Works out of the box |
| macOS 13+ | ✅ Tested | `brew install python3` |

---

## ⚙️ Environment Variables

Create a `.env` file (auto-generated during setup) or set these in your shell:

```env
# Security
SECRET_KEY=<random-hex-string>

# Server
BASE_URL=http://localhost:8000
HOST=0.0.0.0
PORT=8000

# SMTP (optional — also configurable from the dashboard)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
NOTIFICATION_FROM=your-email@gmail.com

# Rate Limiting
RATE_LIMIT_PER_MINUTE=60
NOTIFICATION_COOLDOWN_SECONDS=30
```

> ⚠️ For Gmail: use an [App Password](https://support.google.com/accounts/answer/185833), not your regular password.

---

## 📡 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/auth/register` | First-time admin setup |
| `POST` | `/api/auth/login` | Login (returns JWT) |
| `GET` | `/api/auth/me` | Current user profile |
| `GET` | `/api/auth/status` | Check if setup is needed |
| `GET` | `/api/campaigns` | List campaigns |
| `POST` | `/api/campaigns` | Create campaign |
| `GET` | `/api/campaigns/{id}` | Campaign detail + targets |
| `DELETE` | `/api/campaigns/{id}` | Delete campaign |
| `PATCH` | `/api/campaigns/{id}/status` | Toggle active/paused |
| `POST` | `/api/campaigns/{id}/targets` | Add targets |
| `GET` | `/api/campaigns/{id}/targets/{tid}/qr` | Generate QR code |
| `POST` | `/api/url/analyze` | Analyze a URL |
| `GET` | `/api/url/history` | Scan history |
| `GET` | `/api/analytics/overview` | Dashboard stats |
| `GET` | `/api/analytics/campaign/{id}` | Campaign analytics |
| `GET` | `/api/analytics/audit-logs` | Audit log |
| `GET/POST` | `/api/email/config` | Email SMTP settings |
| `POST` | `/api/email/test` | Send test email |
| `GET` | `/api/notifications` | Notification log |
| `GET` | `/api/notifications/stats` | Notification stats |
| `GET` | `/api/sse/events` | SSE real-time stream |
| `GET` | `/t/{token}` | Training landing page |
| `POST` | `/t/{token}/event` | Record training event |
| `GET` | `/api/health` | Health check |
| `GET` | `/docs` | Swagger API docs |

---

## 🔐 Security Checklist

- [x] JWT authentication with bcrypt password hashing
- [x] HTTPS-ready (use behind nginx/caddy in production)
- [x] CORS middleware configured
- [x] X-Frame-Options: DENY
- [x] X-Content-Type-Options: nosniff
- [x] X-XSS-Protection: 1; mode=block
- [x] Referrer-Policy: strict-origin-when-cross-origin
- [x] Per-IP rate limiting (60 req/min default)
- [x] Notification cooldown (30s between same-campaign alerts)
- [x] Campaign auto-expiration
- [x] One-time random tokens for targets
- [x] SMTP credentials stored server-side only (never in frontend)
- [x] Secrets loaded from environment variables
- [x] `.env` file git-ignored
- [x] Audit logging on all admin actions
- [x] Input validation via Pydantic
- [x] SQL injection protection via SQLAlchemy ORM
- [x] No credential/password/cookie/keystroke collection
- [x] Authorization confirmation required for campaign creation

---

## 🔒 Privacy & Consent Checklist

- [x] Clear notice displayed on landing page: "This is an authorized simulation"
- [x] Location only collected with explicit browser permission + user consent
- [x] No passwords, auth cookies, session tokens, or keystrokes collected
- [x] No clipboard contents, credit card info, or precise GPS without consent
- [x] Only non-sensitive telemetry: event type, browser family, OS family, timestamp
- [x] Random session IDs (no PII) used for participant tracking
- [x] Browser permission respected — no bypass attempts
- [x] Admin must confirm authorized simulation before campaign creation

---

## 🧪 Testing Instructions

```bash
# Run health check
python phishguard.py check

# Start server
python phishguard.py start

# In another terminal, test the API
curl http://localhost:8000/api/health

# Register admin (first time)
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"password123"}'

# Login
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"password123"}'
```

---

## 🐧 Kali Linux Deployment

```bash
# 1. Clone
cd /opt
sudo git clone https://github.com/<YOUR_USERNAME>/phishguard.git
cd phishguard

# 2. Setup
chmod +x start.sh phishguard.py
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. Configure
cp .env.example .env   # or let setup generate it
nano .env               # Edit settings

# 4. Run
python3 phishguard.py start

# 5. (Optional) Make it a system command
sudo ln -s /opt/phishguard/phishguard.py /usr/local/bin/phishguard
chmod +x /usr/local/bin/phishguard
# Now run from anywhere: phishguard start
```

---

## 📄 License

MIT License — use responsibly for authorized security awareness training only.

---

## ⚠️ Disclaimer

This tool is designed exclusively for **authorized security awareness training** within controlled lab environments. It must not be used to deceive, phish, or collect credentials from unauthorized targets. The tool does **not** implement any techniques to evade antivirus, browser warnings, Safe Browsing, EDR, spam filters, or security scanners. Always obtain proper authorization before conducting any security testing.
