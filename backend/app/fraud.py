"""Fraud rules for forwarded messages, links, UPI payloads and QR content.

This is a port of the browser engine (`HQ.analyze` in web/index.html). The parity test
(tests/test_fraud_parity.py) runs both on the same messages so they stay in step.
Rules are heuristics: they flag common scam patterns, they do not prove a message is safe.
"""
from __future__ import annotations

import re
from urllib.parse import parse_qsl, urlsplit

SHORTENERS = ["bit.ly", "tinyurl.com", "cutt.ly", "t.co", "is.gd", "rb.gy", "shorturl.at",
              "goo.gl", "ow.ly", "tiny.cc", "s.id", "rebrand.ly"]
BAD_TLDS = ["xyz", "top", "click", "site", "online", "icu", "live", "cfd", "shop", "buzz",
            "monster", "work", "link", "vip", "win", "loan"]
OFFICIAL = ["digilocker.gov.in", "scholarships.gov.in", "skillindiadigital.gov.in",
            "apprenticeshipindia.gov.in", "india.gov.in", "myscheme.gov.in", "nsdcindia.org",
            "ncvet.gov.in"]
# Sample blocklist. Production syncs this with cybercrime-reported payee IDs.
BLOCKLIST = ["pmkaushal.fee@okdemo", "skill.grant99@ybl", "hr.recruit2026@paytm"]

_F = re.I | re.A
GOVISH = re.compile(r"(^|[^a-z])pm([^a-z]|kaushal|kisan|$)|kaushal|scholar|yojan|sarkar|govt|gov(?![a-z])"
                    r"|skillindia|nsdc|apaar|digilocker|mudhalvan", _F)
FEE = re.compile(r"\b(registration|processing|verification|security|joining|refundable|application|admission)"
                 r"\s*(fee|fees|charge|charges|deposit|amount)\b|\b(pay|send|transfer|deposit)\s*(rs\.?|₹|inr)\s*\d+", _F)
URGENT = re.compile(r"\b(urgent|urgently|today only|last date|limited seats?|hurry|expires?|"
                    r"within\s+\d+\s*(hours?|hrs?|minutes?|mins?))\b", _F)
LURE = re.compile(r"\b(congratulations|you (?:are|have been) (?:selected|shortlisted)|grant|free laptop|lottery|prize)\b", _F)
CONSUMER = re.compile(r"@(okdemo|okaxis|okhdfcbank|oksbi|okicici|ybl|ibl|axl|paytm|apl|fbl|upi)$", _F)
_OTP_A = re.compile(r"\b(otp|pin|cvv|password)\b", _F)
_OTP_B = re.compile(r"\b(share|send|enter|tell|give)\b", _F)

_UPI_RE = re.compile(r"upi://[^\s]+", _F)
_URL_RE = re.compile(
    r"(?:https?://|www\.)[^\s<>\"']+"
    r"|[a-z0-9-]+(?:\.[a-z0-9-]+)*\.(?:com|in|org|net|co|io|ly|gl|me|info|xyz|top|click|site|online|icu|live|"
    r"cfd|shop|buzz|link|vip|win|work|apk)(?:/[^\s<>\"']*)?", _F)
_TRAIL = re.compile(r"[.,;:!?)\]}'\"]+$")
_ODD_SPACE = re.compile("[   -     　﻿]")
_FLOAT = re.compile(r"^\s*[+-]?(\d+\.?\d*|\.\d+)([eE][+-]?\d+)?")

SEV_RANK = {"high": 0, "med": 1, "low": 2, "info": 3, "ok": 4}


def _clean(s: str) -> str:
    return _TRAIL.sub("", s)


def _in_domain(host: str, d: str) -> bool:
    return host == d or host.endswith("." + d)


def _num(x: float) -> str:
    return str(int(x)) if float(x).is_integer() else repr(x)


def _parse_float(s: str):
    m = _FLOAT.match(s or "")
    return float(m.group(0)) if m else None


def extract(text: str) -> tuple[list[str], list[str]]:
    """Return (urls, upi_strings) found in the text."""
    upis = [_clean(m.group(0)) for m in _UPI_RE.finditer(text)]
    rest = _UPI_RE.sub(" ", text)
    urls: list[str] = []
    for m in _URL_RE.finditer(rest):
        before = rest[m.start() - 1] if m.start() > 0 else ""
        if before == "@" or (before and re.match(r"[\w.-]", before, re.A)):
            continue
        u = _clean(m.group(0))
        if u and u not in urls:
            urls.append(u)
    return urls, upis


def parse_url(raw: str):
    has_scheme = bool(re.match(r"^https?://", raw, re.I))
    try:
        parts = urlsplit(raw if has_scheme else "http://" + raw)
        _ = parts.port  # raises ValueError on a bad port, like the browser URL parser
        host = parts.hostname or ""
    except ValueError:
        return None
    if not host:
        return None
    try:
        host = host.encode("idna").decode("ascii")
    except UnicodeError:
        pass
    host = re.sub(r"\.$", "", host.lower())
    path = ((parts.path or "/") + ("?" + parts.query if parts.query else "")).lower()
    return {"raw": raw, "host": host, "path": path,
            "scheme": parts.scheme if has_scheme else None,
            "unicode": any(ord(c) > 127 for c in raw)}


def analyze(text: str) -> dict:
    t = _ODD_SPACE.sub(" ", str(text or "")).strip()
    out: dict = {"score": 0, "verdict": "empty", "findings": [], "urls": [], "upis": [],
                 "hasOfficial": False, "unknown": False}
    if not t:
        return out

    def add(sev: str, title: str, why: str, pts: int = 0) -> None:
        out["findings"].append({"sev": sev, "title": title, "why": why, "pts": pts})
        out["score"] += pts

    urls, upis = extract(t)

    for raw in urls:
        p = parse_url(raw)
        if not p:
            continue
        host = p["host"]
        info = {"raw": raw, "host": host, "flagged": False}
        out["urls"].append(info)
        if any(_in_domain(host, d) for d in OFFICIAL):
            out["hasOfficial"] = True
            add("ok", "Verified government address", f"{host} is on the verified list of portals.", 0)
            continue
        n0 = len(out["findings"])
        tld = host.split(".")[-1]
        gov_end = host.endswith(".gov.in") or host.endswith(".nic.in")
        looks_gov = bool(re.search(r"gov\.in|nic\.in", host)) and not gov_end
        is_short = any(_in_domain(host, d) for d in SHORTENERS)
        if is_short:
            add("med", "Shortened link", "A short link hides the real website. Government portals use their full .gov.in address.", 25)
            if GOVISH.search(p["path"]):
                add("med", "Short link names a scheme", 'Scam messages often hide a link behind a scheme name such as "pm-kaushal".', 10)
        if re.search(r"\.apk(\?|$)", p["path"]):
            add("high", "App file (.apk)", "An .apk installs an app outside the Play Store. Fake job apps can read your OTP messages.", 35)
        if looks_gov:
            add("high", "Fake-looking .gov.in address",
                f'The name contains "gov.in" but the address really ends with ".{tld}". Read an address from the right: the last part shows who owns it.', 40)
        elif not gov_end and not is_short and GOVISH.search(host):
            add("med", "Scheme name on a private website", "The address uses a government scheme name but is not a .gov.in or .nic.in site.", 20)
        if tld in BAD_TLDS:
            add("med", f"Unusual website ending (.{tld})", "Cheap endings like this are common on scam sites.", 15)
        if "xn--" in host or p["unicode"]:
            add("high", "Look-alike characters", "The address uses special characters that imitate normal letters.", 35)
        if re.match(r"^\d{1,3}(\.\d{1,3}){3}$", host):
            add("high", "Raw IP address", "Real portals use names, not number-only addresses.", 30)
        if p["scheme"] == "http":
            add("low", "Not a secure connection (http)", "The site does not use https.", 5)
        if gov_end:
            out["unknown"] = True
            add("info", "Ends in .gov.in", "This address is not on the prototype's short verified list. Open the portal by typing its address yourself.", 0)
        elif len(out["findings"]) == n0:
            out["unknown"] = True
            add("low", "Website not on the verified list", "Check this offer on skillindiadigital.gov.in or apprenticeshipindia.gov.in before sharing details.", 10)
        info["flagged"] = len(out["findings"]) > n0

    fee_flag = False
    for raw in upis:
        m = re.match(r"^upi://([a-z]+)\??(.*)$", raw, re.I | re.S)
        kind = m.group(1).lower() if m else "pay"
        q: dict[str, str] = {}
        for k, v in parse_qsl(m.group(2) if m else "", keep_blank_values=True):
            q.setdefault(k, v)
        pa = (q.get("pa") or "").lower()
        pn = q.get("pn") or ""
        tn = q.get("tn") or ""
        am = _parse_float(q.get("am") or "")
        amt = int(am) if am is not None and float(am).is_integer() else am
        out["upis"].append({"raw": raw, "kind": kind, "pa": pa, "pn": pn, "am": amt, "tn": tn})
        fee_words = bool(FEE.search(f"{pn} {tn} {t}"))
        if amt is not None and amt > 0 and fee_words:
            add("high", f"Asks you to pay ₹{_num(amt)}", "Real scholarships and job offers do not ask you to pay in order to receive them.", 35)
            fee_flag = True
        elif amt is not None and amt > 0:
            add("med", f"Fixed payment of ₹{_num(amt)}", "Check who you are paying before you approve any UPI request.", 15)
        if kind == "collect":
            add("high", "UPI collect request", "A collect request pulls money from your account when you approve it. A real payout never needs your approval.", 30)
        if GOVISH.search(pn) and CONSUMER.search(pa):
            add("high", "Government name on a personal-style UPI ID",
                f'The payee name says "{pn}" but the UPI ID {pa} looks like an ordinary personal account. Government payments do not go to IDs like this.', 40)
        if pa in BLOCKLIST:
            add("high", "UPI ID on the sample blocklist",
                f"{pa} matches a reported-fraud entry. In production this list syncs with cybercrime-reported IDs.", 50)

    if not fee_flag and FEE.search(t):
        add("high", "Asks for money as a fee", "Genuine scholarships and job offers do not ask for a registration, processing or verification fee.", 25)
    if URGENT.search(t):
        add("med", "Pressure to act fast", "Scammers use deadlines so you do not stop to check.", 10)
    if _OTP_A.search(t) and _OTP_B.search(t):
        add("high", "Asks for OTP or PIN", "Nobody who is helping you needs your OTP or PIN.", 30)
    if LURE.search(t):
        add("med", "Too-good-to-be-true wording", "Messages that say you were selected or won a grant without applying are a common trap.", 10)

    out["score"] = min(100, out["score"])
    out["findings"].sort(key=lambda f: SEV_RANK[f["sev"]])
    if out["score"] >= 60:
        out["verdict"] = "danger"
    elif out["score"] >= 25:
        out["verdict"] = "warning"
    elif out["hasOfficial"] and not out["unknown"] and out["score"] == 0:
        out["verdict"] = "safe"
    elif not out["urls"] and not out["upis"] and not out["findings"]:
        out["verdict"] = "empty"
    else:
        out["verdict"] = "low"
    return out
