"""
PhishGuard URL Security Scanner

Analyzes a URL for phishing indicators and security posture.
"""
import math
import re
import ssl
import socket
from collections import Counter
from datetime import datetime, timezone
from urllib.parse import urlparse

import requests


def analyze_url(url: str) -> dict:
    """Run all security checks against the given URL and return a report."""
    parsed = urlparse(url if "://" in url else f"https://{url}")
    results = {
        "url": url,
        "parsed_domain": parsed.hostname or url,
        "checks": [],
        "risk_score": 0,
        "risk_level": "unknown",
        "summary": "",
    }
    checks = []
    score = 0

    # ── 1. HTTPS Check ────────────────────────────────────────────
    is_https = parsed.scheme == "https"
    checks.append({
        "name": "HTTPS",
        "passed": is_https,
        "status": "✅ Pass" if is_https else "❌ Fail",
        "detail": (
            "URL uses HTTPS encryption"
            if is_https
            else "URL does NOT use HTTPS — data is transmitted in plain text"
        ),
    })
    if not is_https:
        score += 25

    # ── 2. TLS Certificate Check ──────────────────────────────────
    cert_info = _check_tls_certificate(parsed.hostname, parsed.port or 443)
    checks.append(cert_info["validity"])
    checks.append(cert_info["expiry"])
    score += cert_info["score"]

    # ── 3. Redirect Chain Analysis ────────────────────────────────
    redirect_info = _check_redirects(url)
    checks.append(redirect_info)
    if redirect_info.get("redirect_count", 0) > 3:
        score += 15

    # ── 4. Suspicious Domain Analysis ─────────────────────────────
    domain_check = _check_domain(parsed.hostname or "")
    checks.append(domain_check)
    score += domain_check.get("penalty", 0)

    # ── 5. URL Entropy ────────────────────────────────────────────
    entropy_check = _check_entropy(url)
    checks.append(entropy_check)
    score += entropy_check.get("penalty", 0)

    # ── 6. Phishing Keyword Detection ─────────────────────────────
    keyword_check = _check_phishing_keywords(url)
    checks.append(keyword_check)
    score += keyword_check.get("penalty", 0)

    # ── 7. Login-Page Imitation Detection ─────────────────────────
    login_check = _check_login_imitation(url)
    checks.append(login_check)
    score += login_check.get("penalty", 0)

    # ── 8. IP Address in URL ──────────────────────────────────────
    ip_check = _check_ip_in_url(parsed.hostname or "")
    checks.append(ip_check)
    score += ip_check.get("penalty", 0)

    # Clamp score to 0-100
    score = max(0, min(100, score))
    results["checks"] = checks
    results["risk_score"] = score
    results["risk_level"] = (
        "low" if score <= 25 else
        "medium" if score <= 50 else
        "high" if score <= 75 else
        "critical"
    )
    results["summary"] = (
        f"Risk score: {score}/100 ({results['risk_level'].upper()}). "
        f"{sum(1 for c in checks if c.get('passed'))} of {len(checks)} checks passed."
    )
    return results


# ── Internal helpers ──────────────────────────────────────────────────

def _check_tls_certificate(hostname: str, port: int = 443) -> dict:
    """Check TLS certificate validity and expiration."""
    result = {"validity": {}, "expiry": {}, "score": 0}
    if not hostname:
        result["validity"] = {
            "name": "TLS Certificate",
            "passed": False,
            "status": "❌ Fail",
            "detail": "No hostname to check",
        }
        result["expiry"] = {
            "name": "Certificate Expiry",
            "passed": False,
            "status": "❌ Fail",
            "detail": "No hostname to check",
        }
        result["score"] = 20
        return result

    try:
        ctx = ssl.create_default_context()
        with ctx.wrap_socket(
            socket.socket(socket.AF_INET), server_hostname=hostname
        ) as s:
            s.settimeout(5)
            s.connect((hostname, port))
            cert = s.getpeercert()

        # Validity
        result["validity"] = {
            "name": "TLS Certificate",
            "passed": True,
            "status": "✅ Pass",
            "detail": f"Valid TLS certificate issued to {cert.get('subject', [[['', '']]])[0][0][1]}",
        }

        # Expiry
        not_after = datetime.strptime(
            cert["notAfter"], "%b %d %H:%M:%S %Y %Z"
        ).replace(tzinfo=timezone.utc)
        days_left = (not_after - datetime.now(timezone.utc)).days
        if days_left < 0:
            result["expiry"] = {
                "name": "Certificate Expiry",
                "passed": False,
                "status": "❌ Fail",
                "detail": f"Certificate EXPIRED {abs(days_left)} days ago",
            }
            result["score"] = 20
        elif days_left < 30:
            result["expiry"] = {
                "name": "Certificate Expiry",
                "passed": True,
                "status": "⚠️ Warning",
                "detail": f"Certificate expires in {days_left} days",
            }
            result["score"] = 5
        else:
            result["expiry"] = {
                "name": "Certificate Expiry",
                "passed": True,
                "status": "✅ Pass",
                "detail": f"Certificate valid for {days_left} more days",
            }

    except ssl.SSLCertVerificationError as e:
        result["validity"] = {
            "name": "TLS Certificate",
            "passed": False,
            "status": "❌ Fail",
            "detail": f"SSL verification failed: {e}",
        }
        result["expiry"] = {
            "name": "Certificate Expiry",
            "passed": False,
            "status": "❌ Fail",
            "detail": "Cannot check expiry — certificate is invalid",
        }
        result["score"] = 25
    except Exception as e:
        result["validity"] = {
            "name": "TLS Certificate",
            "passed": False,
            "status": "⚠️ Warning",
            "detail": f"Could not connect to check TLS: {type(e).__name__}",
        }
        result["expiry"] = {
            "name": "Certificate Expiry",
            "passed": False,
            "status": "⚠️ Warning",
            "detail": "Could not verify certificate expiry",
        }
        result["score"] = 10

    return result


def _check_redirects(url: str) -> dict:
    """Follow redirects and report the chain."""
    try:
        resp = requests.get(url, allow_redirects=True, timeout=8, verify=False)
        chain = [r.url for r in resp.history] + [resp.url]
        count = len(resp.history)
        if count == 0:
            return {
                "name": "Redirect Chain",
                "passed": True,
                "status": "✅ Pass",
                "detail": "No redirects detected",
                "redirect_count": 0,
                "chain": chain,
            }
        elif count <= 3:
            return {
                "name": "Redirect Chain",
                "passed": True,
                "status": "⚠️ Warning",
                "detail": f"{count} redirect(s) detected",
                "redirect_count": count,
                "chain": chain,
            }
        else:
            return {
                "name": "Redirect Chain",
                "passed": False,
                "status": "❌ Fail",
                "detail": f"Excessive redirects: {count}",
                "redirect_count": count,
                "chain": chain,
            }
    except Exception as e:
        return {
            "name": "Redirect Chain",
            "passed": False,
            "status": "⚠️ Warning",
            "detail": f"Could not follow redirects: {type(e).__name__}",
            "redirect_count": -1,
            "chain": [],
        }


def _check_domain(hostname: str) -> dict:
    """Check for suspicious domain patterns."""
    suspicious_patterns = [
        r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}",  # IP address
        r"(login|signin|verify|secure|account|update|confirm)",
        r"(.{30,}\.)",  # very long subdomain
        r"(--|\.\.|__)",  # double separators
        r"\.(tk|ml|ga|cf|gq|xyz|top|buzz|club)$",  # free/suspicious TLDs
    ]
    found = []
    for pattern in suspicious_patterns:
        if re.search(pattern, hostname, re.IGNORECASE):
            found.append(pattern)

    if not found:
        return {
            "name": "Domain Analysis",
            "passed": True,
            "status": "✅ Pass",
            "detail": f"Domain '{hostname}' has no suspicious patterns",
            "penalty": 0,
        }
    elif len(found) <= 1:
        return {
            "name": "Domain Analysis",
            "passed": True,
            "status": "⚠️ Warning",
            "detail": f"Domain '{hostname}' has {len(found)} suspicious indicator(s)",
            "penalty": 10,
        }
    else:
        return {
            "name": "Domain Analysis",
            "passed": False,
            "status": "❌ Fail",
            "detail": f"Domain '{hostname}' has {len(found)} suspicious indicators",
            "penalty": 20,
        }


def _check_entropy(url: str) -> dict:
    """Calculate Shannon entropy of the URL to detect randomized phishing URLs."""
    if not url:
        return {
            "name": "URL Entropy",
            "passed": True,
            "status": "ℹ️ Info",
            "detail": "No URL to analyze",
            "penalty": 0,
        }
    freq = Counter(url)
    length = len(url)
    entropy = -sum(
        (count / length) * math.log2(count / length)
        for count in freq.values()
    )

    if entropy < 3.5:
        return {
            "name": "URL Entropy",
            "passed": True,
            "status": "✅ Pass",
            "detail": f"Low entropy ({entropy:.2f}) — URL appears structured",
            "penalty": 0,
            "entropy": round(entropy, 2),
        }
    elif entropy < 4.5:
        return {
            "name": "URL Entropy",
            "passed": True,
            "status": "ℹ️ Info",
            "detail": f"Moderate entropy ({entropy:.2f})",
            "penalty": 0,
            "entropy": round(entropy, 2),
        }
    else:
        return {
            "name": "URL Entropy",
            "passed": False,
            "status": "⚠️ Warning",
            "detail": f"High entropy ({entropy:.2f}) — URL may be randomized/obfuscated",
            "penalty": 10,
            "entropy": round(entropy, 2),
        }


def _check_phishing_keywords(url: str) -> dict:
    """Look for common phishing-related keywords in the URL."""
    keywords = [
        "login", "signin", "verify", "secure", "account",
        "update", "confirm", "banking", "paypal", "microsoft",
        "apple", "google", "facebook", "password", "credential",
        "wallet", "suspend", "restrict", "unlock", "urgent",
    ]
    lower = url.lower()
    found = [kw for kw in keywords if kw in lower]

    if not found:
        return {
            "name": "Phishing Keywords",
            "passed": True,
            "status": "✅ Pass",
            "detail": "No common phishing keywords detected",
            "penalty": 0,
        }
    elif len(found) <= 2:
        return {
            "name": "Phishing Keywords",
            "passed": True,
            "status": "⚠️ Warning",
            "detail": f"Found keyword(s): {', '.join(found)}",
            "penalty": 10,
        }
    else:
        return {
            "name": "Phishing Keywords",
            "passed": False,
            "status": "❌ Fail",
            "detail": f"Multiple phishing keywords: {', '.join(found)}",
            "penalty": 20,
        }


def _check_login_imitation(url: str) -> dict:
    """Check if the page content imitates a login form."""
    try:
        resp = requests.get(url, timeout=8, verify=False)
        html = resp.text.lower()
        indicators = 0
        details = []

        if "<form" in html and ("password" in html or "passwd" in html):
            indicators += 1
            details.append("login form detected")
        if "type=\"password\"" in html or "type='password'" in html:
            indicators += 1
            details.append("password field found")
        for brand in ["paypal", "microsoft", "google", "facebook", "apple", "amazon"]:
            if brand in html:
                indicators += 1
                details.append(f"brand mention: {brand}")
                break

        if indicators == 0:
            return {
                "name": "Login-Page Imitation",
                "passed": True,
                "status": "✅ Pass",
                "detail": "No login-form imitation detected",
                "penalty": 0,
            }
        elif indicators == 1:
            return {
                "name": "Login-Page Imitation",
                "passed": True,
                "status": "⚠️ Warning",
                "detail": f"Minor indicator: {'; '.join(details)}",
                "penalty": 5,
            }
        else:
            return {
                "name": "Login-Page Imitation",
                "passed": False,
                "status": "❌ Fail",
                "detail": f"Phishing indicators: {'; '.join(details)}",
                "penalty": 20,
            }
    except Exception:
        return {
            "name": "Login-Page Imitation",
            "passed": True,
            "status": "ℹ️ Info",
            "detail": "Could not fetch page content for analysis",
            "penalty": 0,
        }


def _check_ip_in_url(hostname: str) -> dict:
    """Check if the URL uses a raw IP address instead of a domain name."""
    ip_pattern = re.compile(r"^\d{1,3}(\.\d{1,3}){3}$")
    if ip_pattern.match(hostname):
        return {
            "name": "IP in URL",
            "passed": False,
            "status": "❌ Fail",
            "detail": f"URL uses raw IP address ({hostname}) instead of a domain",
            "penalty": 20,
        }
    return {
        "name": "IP in URL",
        "passed": True,
        "status": "✅ Pass",
        "detail": "URL uses a proper domain name",
        "penalty": 0,
    }
