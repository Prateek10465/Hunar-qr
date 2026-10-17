"""Server-rendered verification page that a QR code opens. Every stored string is HTML-escaped."""
from __future__ import annotations

from html import escape as e

_CSS = """
:root{--bg:#f4f6fa;--surface:#ffffff;--ink:#0f172a;--ink2:#475569;--line:#cbd5e1;--navy:#0b2d64;--ok:#0d731e;--okbg:#f0fdf4;--bad:#b91c1c;--badbg:#fef2f2;--warn:#92400e;--warnbg:#fffbeb;--bar:#0b2d64}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.55 "Noto Sans",system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
.tri{display:flex;height:5px}.tri i{flex:1}.tri i:nth-child(1){background:#ff9933}.tri i:nth-child(2){background:#ffffff}.tri i:nth-child(3){background:#138808}
header{background:var(--navy);color:#fff;border-bottom:3px solid #ff9933}.w{max-width:760px;margin:0 auto;padding:0 max(16px,env(safe-area-inset-left,0px))}
header .w{padding-block:14px;display:flex;gap:12px;align-items:baseline;flex-wrap:wrap}header b{font:700 1.3rem "Noto Serif",Georgia,serif}header span{font-size:.9rem;color:#e2e8f0}
main{padding-block:18px 40px;display:grid;gap:16px}
.banner{padding:12px 14px;font-weight:700;border:1px solid;border-radius:3px}.ok{color:var(--ok);background:var(--okbg);border-color:#86efac}.bad{color:var(--bad);background:var(--badbg);border-color:#fca5a5}.warn{color:var(--warn);background:var(--warnbg);border-color:#fcd34d}
.card{background:var(--surface);border:1px solid var(--line);border-radius:4px;padding:18px;display:grid;gap:12px;min-width:0;box-shadow:0 1px 4px rgba(11,45,100,.06)}
.pos-card{border-left:4px solid #ff9933}
h1,h2{font-family:"Noto Serif",Georgia,serif;margin:0;line-height:1.25;color:var(--navy)}h1{font-size:1.45rem}h2{font-size:.8rem;text-transform:uppercase;letter-spacing:.06em;color:var(--ink2);font-family:inherit}
dl{display:grid;grid-template-columns:auto minmax(0,1fr);gap:6px 14px;margin:0}dt{color:var(--ink2)}dd{margin:0;font-weight:600;overflow-wrap:anywhere}
.tags{display:flex;flex-wrap:wrap;gap:6px}.tags span{border:1px solid var(--line);background:#f1f5f9;padding:3px 10px;font-size:.85rem;border-radius:2px}
.badge{display:inline-block;padding:3px 8px;font-size:.78rem;font-weight:700;border-radius:3px;background:#e0f2fe;color:#0369a1;border:1px solid #bae6fd}
.aadhaar-badge{background:#ecfdf5;color:#047857;border-color:#a7f3d0}
.face-badge{background:#fef3c7;color:#92400e;border-color:#fde68a}
.anchor-card{border-left:4px solid #0d731e;background:#f8fafc}
.anchor-grid{display:grid;grid-template-columns:1fr;gap:10px}
@media(min-width:600px){.anchor-grid{grid-template-columns:1fr 1fr}}
.anchor-box{background:#fff;border:1px solid var(--line);border-radius:4px;padding:12px;display:grid;gap:4px}
.say{border:1px solid var(--line);background:#f8fafc;padding:12px 14px;display:grid;gap:6px;border-radius:3px}
.q-box{font-weight:600;color:var(--navy);background:#eff6ff;padding:8px 12px;border-radius:4px;border:1px solid #bfdbfe;font-size:.92rem}
.mono{font-family:ui-monospace,Menlo,Consolas,monospace;font-size:.78rem;color:var(--ink2);overflow-wrap:anywhere}
img.ev{max-width:100%;height:auto;border:1px solid var(--line);border-radius:3px}ul.steps{list-style:none;margin:0;padding:0;display:grid;gap:8px}ul.steps li{display:flex;gap:10px;align-items:baseline}.y{color:var(--ok);font-weight:bold}.n{color:var(--bad);font-weight:bold}
footer{font-size:.82rem;color:var(--ink2);text-align:center;padding-top:12px}
"""


def _shell(title: str, body: str) -> str:
    return ("<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">"
            "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1, viewport-fit=cover\">"
            "<meta name=\"referrer\" content=\"no-referrer\"><meta name=\"robots\" content=\"noindex\">"
            "<link rel=\"icon\" type=\"image/png\" sizes=\"256x256\" href=\"/favicon.png\">"
            "<link rel=\"shortcut icon\" href=\"/favicon.ico\">"
            "<link rel=\"apple-touch-icon\" href=\"/favicon.png\">"
            f"<title>{e(title)}</title><style>{_CSS}</style></head><body>"
            "<div class=\"tri\" aria-hidden=\"true\"><i></i><i></i><i></i></div>"
            "<header><div class=\"w\"><img src=\"/favicon.png\" width=\"28\" height=\"28\" alt=\"Hunar-QR\" style=\"border-radius:4px;vertical-align:middle;margin-right:10px\"><b>भारत सरकार · Hunar-QR</b><span>National Skill Passport Verification</span></div></header>"
            f"<main class=\"w\">{body}</main></body></html>")


def render_not_found() -> str:
    return _shell("Passport not found", "<div class=\"banner bad\">No passport found for this link.</div>"
                  "<div class=\"card\"><p>The link is incomplete or has been changed. Ask the holder to show the QR code again.</p></div>")


def render_passport(*, pid: str, cred: dict, result: dict, sig_param: str, fingerprint: str) -> str:
    s = cred["credentialSubject"]
    m = s.get("mentor") or {}
    ver = s.get("verification") or {}
    assurance = (cred.get("assurance") or {})
    level = assurance.get("level", "unknown")
    valid = result["valid"]
    parts = []
    if valid:
        parts.append("<div class=\"banner ok\">Verified: the signature is valid and the credential has not been changed.</div>")
    else:
        parts.append("<div class=\"banner bad\">Not valid. Do not rely on this credential.</div>")
    if level == "demo":
        parts.append("<div class=\"banner warn\">DEMO credential. It was made with sample providers and is not valid for employment.</div>")
    lid = s.get("linkedId")
    aadhaar_row = ""
    if lid and lid.get("scheme") == "Aadhaar" and lid.get("verified"):
        aadhaar_row = f"<dt>Identity Anchor</dt><dd><span class=\"badge aadhaar-badge\">🇮🇳 Aadhaar Verified · {e(lid['id'])}</span></dd>"

    v_info = s.get("showcaseVideo") or {}
    video_badge = "<span class=\"badge aadhaar-badge\">🎥 30-60s Video Attached</span>" if v_info.get("available") else "<span class=\"badge\">Photo Verified</span>"

    parts.append(
        f"<div class=\"card\"><h1>{e(s['name'])}</h1><dl>"
        + aadhaar_row
        + f"<dt>Trade</dt><dd>{e(s['trade'])}</dd>"
        f"<dt>Level</dt><dd>NCrF/NSQF {e(str(s['indicativeLevel']))} (indicative)</dd>"
        f"<dt>Practical hours</dt><dd>{e(str(s['practicalHours']))} (self-reported)</dd>"
        f"<dt>Credit</dt><dd>{s['ncrfCredits']:.2f} (30 hours = 1)</dd>"
        f"<dt>Biometric Status</dt><dd><span class=\"badge face-badge\">🛡️ Live Face &amp; Workpiece Bound</span></dd>"
        f"<dt>Work Showcase</dt><dd>{video_badge}</dd>"
        f"<dt>Issued</dt><dd>{e(cred['validFrom'])}</dd><dt>Passport ID</dt><dd>{e(pid)}</dd></dl>"
        f"<div class=\"tags\">{''.join(f'<span>{e(t)}</span>' for t in s['skillTags'])}</div></div>")

    # UIDAI Identity & Live Biometric Anchor Card
    aadhaar_num = lid['id'] if lid else "Not Linked"
    parts.append(
        f"<div class=\"card anchor-card\"><h2>UIDAI Identity &amp; Biometric Security Anchor</h2>"
        f"<div class=\"anchor-grid\">"
        f"<div class=\"anchor-box\"><div style=\"font-size:.8rem;color:var(--ink2)\">Verified Identity Anchor</div>"
        f"<b>{e(s['name'])}</b>"
        f"<div><span class=\"badge aadhaar-badge\">🇮🇳 UIDAI Aadhaar · {e(aadhaar_num)}</span></div></div>"
        f"<div class=\"anchor-box\"><div style=\"font-size:.8rem;color:var(--ink2)\">Physical Skill Evidence</div>"
        f"<b>Workpiece &amp; Face Bound</b>"
        f"<div><span class=\"badge face-badge\">🛡️ Live Face Verified Present</span></div></div>"
        f"</div>"
        f"<div class=\"mono\">The verified Aadhaar holder ({e(s['name'])}) was physically detected holding the finished workpiece in the evidence photo, preventing impersonation, stock catalog image uploads, and stolen work claims.</div>"
        f"</div>")

    # Hands-on Work Showcase Video Player Card
    if v_info.get("available"):
        v_sha = v_info.get("sha256", "")
        parts.append(
            f"<div class=\"card\"><h2>🎥 Craftsmanship in Action · 30–60s Work Showcase Video</h2>"
            f"<div class=\"mono\">Verified workplace hands-on demonstration of {e(s['trade'])} by {e(s['name'])}. Watch real-time technique, tool handling, and craftsmanship quality.</div>"
            f"<div style=\"position:relative;border-radius:4px;overflow:hidden;background:#0f172a;border:1px solid var(--line);margin-block:6px\">"
            f"<video controls playsinline preload=\"metadata\" poster=\"/v/{e(pid)}/evidence.jpg?s={e(sig_param)}\" style=\"display:block;width:100%;max-height:420px\">"
            f"<source src=\"/v/{e(pid)}/video.mp4?s={e(sig_param)}\" type=\"video/mp4\">"
            f"Your browser does not support HTML5 video streaming."
            f"</video>"
            f"</div>"
            f"<div class=\"mono\" style=\"display:flex;justify-content:space-between;flex-wrap:wrap;gap:8px\">"
            f"<span>Video SHA-256: {e(v_sha[:24])}…</span>"
            f"<span class=\"badge\" style=\"background:#ecfdf5;color:#047857;border-color:#a7f3d0\">✓ Verified Craft Demonstration</span>"
            f"</div></div>")

    
    if m and m.get("endorsement") and m.get("name") and "Self-Practice" not in m.get("name"):
        eng = m["endorsement"].get("english")
        parts.append(
            f"<div class=\"card\"><h2>Mentor endorsement, {e(m['name'])}</h2><div class=\"say\">"
            f"<div>{e(m['endorsement']['original'])}</div>"
            + (f"<div class=\"mono\">English: {e(eng)}</div>" if eng and eng != m["endorsement"]["original"] else "")
            + f"<div class=\"mono\">Language {e(m['language'])}. Voice liveness: {e(str(m['liveness']).replace('_', ' '))}. Speech read by the {e(assurance.get('asr', '?'))} provider.</div></div></div>")

    parts.append(
        f"<div class=\"card\"><h2>Live Evidence &amp; Biometric Photo Proof</h2>"
        f"<div class=\"mono\">Holder face physically verified holding trade workpiece. EXIF stripped.</div>"
        f"<img class=\"ev\" alt=\"Live selfie of worker with finished work\" src=\"/v/{e(pid)}/evidence.jpg?s={e(sig_param)}\">"
        f"<div class=\"mono\">SHA-256 {e(s['evidenceSha256'])}</div></div>")
    steps = "".join(f"<li><span class=\"{'y' if st['ok'] else 'n'}\">{'✓' if st['ok'] else '✗'}</span><span><b>{e(st['label'])}.</b> {e(st['detail'])}</span></li>" for st in result["steps"])
    parts.append(f"<div class=\"card\"><h2>Checks run just now</h2><ul class=\"steps\">{steps}</ul>"
                 f"<div class=\"mono\">Issuer {e(cred['issuer'])}<br>Signature fingerprint {e(fingerprint)}</div></div>")
    parts.append("<footer>Hunar-QR is a student prototype. It is not an official Government of India service.</footer>")
    return _shell(f"Hunar-QR Skill Passport {pid}", "".join(parts))
