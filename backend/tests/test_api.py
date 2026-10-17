import re
import time
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import cv2
import numpy as np
import pytest

from app import imaging
from app.credentials import canonical, unb64u

UPI = "upi://pay?pa=pmkaushal.fee@okdemo&pn=PM%20Kaushal%20Fee&am=99&cu=INR&tn=Processing%20fee"


def mint(client, **over):
    data = {"name": "Karthik M.", "trade": "electrical", "language": "ta", "use_sample_photo": "true", "use_sample_voice": "true"}
    data.update(over)
    return client.post("/api/passports", data=data)


def sig_of(rec):
    return rec["signature"]


# ------------------------------------------------------------------ basics
def test_health_meta_and_headers(client):
    assert client.get("/healthz").json()["ok"] is True
    m = client.get("/api/meta").json()
    assert m["providers"] == {"asr": "mock", "vision": "mock", "tts": "none"} and m["assurance"] == "demo"
    assert [t["id"] for t in m["trades"]][:3] == ["electrical", "tailoring", "solar"] and len(m["trades"]) == 12 and m["whatsapp_configured"] is True
    r = client.get("/healthz")
    assert r.headers["x-content-type-options"] == "nosniff" and r.headers["referrer-policy"] == "no-referrer"


def test_root_without_web_dir(client):
    assert client.get("/").json()["docs"] == "/docs"


def test_serves_web_dir(make_app, tmp_path):
    web = tmp_path / "web"
    web.mkdir()
    (web / "index.html").write_text("<h1>demo</h1>")
    with make_app(web_dir=str(web)) as c:
        assert "<h1>demo</h1>" in c.get("/").text
        assert c.get("/healthz").status_code == 200       # API routes still win over the static mount


# ------------------------------------------------------------------ scam shield
def test_analyze_danger_safe_empty(client):
    a = client.post("/api/analyze", json={"text": "Pay ₹99 processing fee at bit.ly/pm-kaushal-claim", "qr_text": UPI}).json()
    assert a["verdict"] == "danger" and a["upis"][0]["pa"] == "pmkaushal.fee@okdemo"
    assert client.post("/api/analyze", json={"text": "see https://scholarships.gov.in"}).json()["verdict"] == "safe"
    assert client.post("/api/analyze", json={"text": ""}).json()["verdict"] == "empty"


def test_analyze_validates_input(client):
    assert client.post("/api/analyze", json={"text": "x" * 9000}).status_code == 422
    assert client.post("/api/analyze", content=b"nope").status_code == 422


def test_analyze_image_reads_the_qr(client):
    r = client.post("/api/analyze-image", files={"image": ("q.png", imaging.qr_png(UPI), "image/png")}, data={"text": "scan to pay"})
    assert r.status_code == 200 and r.json()["qr_text"] == UPI and r.json()["verdict"] == "danger"
    r = client.post("/api/analyze-image", files={"image": ("p.png", imaging.sample_image("solar"), "image/png")})
    assert r.status_code == 422


def test_checks_are_counted_without_storing_text(client, settings):
    client.post("/api/analyze", json={"text": "Pay ₹99 processing fee now"})
    s = client.get("/api/stats").json()
    assert s["messages_checked"] == 1 and s["checks_by_verdict"] == {"warning": 1}
    db = (Path(settings.data_dir) / "hunar.db")
    assert b"processing fee now" not in db.read_bytes()


def test_rate_limit(make_app):
    with make_app(rate_analyze_per_min=3) as c:
        codes = [c.post("/api/analyze", json={"text": "hi"}).status_code for _ in range(5)]
    assert codes == [200, 200, 200, 429, 429]


def test_oversized_body_is_refused(make_app):
    with make_app(max_upload_bytes=1000) as c:
        r = c.post("/api/analyze", content=b"{}", headers={"content-length": "99999999", "content-type": "application/json"})
    assert r.status_code == 413


# ------------------------------------------------------------------ passports
def test_mint_passport(client):
    r = mint(client)
    assert r.status_code == 200, r.text
    rec = r.json()
    assert re.fullmatch(r"HQR-TN-\d\d-000001", rec["id"])
    c = rec["credential"]
    assert c["assurance"] == {"level": "demo", "asr": "mock", "vision": "mock"} and rec["assurance"] == "demo"
    s = c["credentialSubject"]
    assert s["name"] == "Karthik M." and s["practicalHours"] == 12 and s["ncrfCredits"] == 0.4 and s["linkedId"] is None
    assert s["mentor"]["endorsement"]["original"].startswith("இந்த மாணவர்") and s["mentor"]["endorsement"]["english"].startswith("This student")
    assert len(s["evidenceSha256"]) == 64 and len(unb64u(rec["signature"])) == 64
    assert rec["verify_url"] == f"http://testserver/v/{rec['id']}?s={rec['signature']}"
    assert [p["step"] for p in rec["pipeline"]] == ["recv", "asr", "live", "vlm", "ncrf", "sign", "qr"]
    assert mint(client).json()["id"].endswith("000002")


def test_mint_with_uploaded_photo(client):
    r = client.post("/api/passports", data={"name": "Anitha R.", "trade": "tailoring", "language": "en", "hours": "40",
                                           "mentor_name": "Lakshmi Ammal", "use_sample_voice": "true"},
                    files={"photo": ("w.png", imaging.sample_image("tailoring"), "image/png")})
    assert r.status_code == 200, r.text
    s = r.json()["credential"]["credentialSubject"]
    assert s["practicalHours"] == 40 and s["ncrfCredits"] == 1.33 and s["mentor"]["name"] == "Lakshmi Ammal"


@pytest.mark.parametrize("over,code", [
    ({"trade": "unknown_trade"}, 422), ({"language": "fr"}, 422), ({"name": "A"}, 422), ({"hours": "0"}, 422),
    ({"hours": "501"}, 422), ({"learner_type": "alien"}, 422), ({"use_sample_photo": "false"}, 422)])
def test_mint_validation(client, over, code):
    assert mint(client, **over).status_code == code


def test_mint_with_showcase_video(client):
    r = client.post("/api/passports", data={"name": "Karthik M.", "trade": "electrical", "language": "en",
                                           "use_sample_photo": "true", "use_sample_video": "true"})
    assert r.status_code == 200, r.text
    rec = r.json()
    assert rec["credential"]["credentialSubject"]["showcaseVideo"]["available"] is True
    sig = rec["signature"]
    v_resp = client.get(f"/v/{rec['id']}/video.mp4?s={sig}")
    assert v_resp.status_code == 200
    assert v_resp.headers["content-type"] == "video/mp4"
    page_resp = client.get(f"/v/{rec['id']}?s={sig}")
    assert "<video" in page_resp.text
    assert "media-src 'self'" in page_resp.headers["content-security-policy"]


def test_mint_rejects_bad_photos(client):
    blurry = cv2.imencode(".png", cv2.GaussianBlur(cv2.imdecode(np.frombuffer(imaging.sample_image("electrical"), np.uint8), 1), (0, 0), 6))[1].tobytes()
    r = client.post("/api/passports", data={"name": "Karthik M.", "trade": "electrical", "use_sample_voice": "true"},
                    files={"photo": ("b.png", blurry, "image/png")})
    assert r.status_code == 422 and "blurry" in r.json()["detail"]
    r = client.post("/api/passports", data={"name": "Karthik M.", "trade": "electrical", "use_sample_voice": "true"},
                    files={"photo": ("b.txt", b"hello", "text/plain")})
    assert r.status_code == 422 and "not an image" in r.json()["detail"]


def test_mint_rejects_large_uploads(make_app):
    with make_app(max_upload_bytes=1000) as c:
        r = c.post("/api/passports", data={"name": "Karthik M.", "trade": "electrical", "use_sample_voice": "true"},
                   files={"photo": ("b.png", imaging.sample_image("electrical"), "image/png")})
    assert r.status_code == 413


def test_get_passport_needs_the_signature(client):
    rec = mint(client).json()
    pid, sig = rec["id"], sig_of(rec)
    assert client.get(f"/api/passports/{pid}", params={"s": sig}).json()["credential"] == rec["credential"]
    for params in ({}, {"s": "x" * 86}, {"s": sig[:-2] + "AA"}):
        assert client.get(f"/api/passports/{pid}", params=params).status_code == 404
    assert client.get("/api/passports/HQR-TN-26-999999", params={"s": sig}).status_code == 404


def test_demo_passport_is_created_once(client):
    a, b = client.get("/api/demo-passport").json(), client.get("/api/demo-passport").json()
    assert a["id"] == b["id"] and b["credential"]["credentialSubject"]["name"] == "Karthik M."
    assert client.get("/api/stats").json()["passports_issued"] == 1


def test_demo_endpoints_can_be_switched_off(make_app):
    with make_app(enable_demo_api=False) as c:
        assert c.post("/api/passports", data={"name": "Karthik M.", "trade": "electrical"}).status_code == 404
        assert c.get("/api/demo-passport").status_code == 404
        assert c.post("/api/chat", json={"session_id": "abcdefgh12", "text": "hi"}).status_code == 404
        assert c.post("/api/analyze", json={"text": "hi"}).status_code == 200       # the scam shield stays available


# ------------------------------------------------------------------ hosted page, evidence, QR
def test_verification_page(client):
    rec = mint(client).json()
    r = client.get(f"/v/{rec['id']}", params={"s": sig_of(rec)})
    assert r.status_code == 200
    assert "Verified: the signature is valid" in r.text and "DEMO credential" in r.text and "Karthik M." in r.text
    assert "default-src 'none'" in r.headers["content-security-policy"] and r.headers["cache-control"] == "no-store"


def test_verification_page_escapes_user_text(client):
    rec = mint(client, name="<script>alert(1)</script>", mentor_name="<img src=x onerror=alert(2)>").json()
    html = client.get(f"/v/{rec['id']}", params={"s": sig_of(rec)}).text
    assert "<script>alert(1)" not in html and "&lt;script&gt;alert(1)" in html
    assert "<img src=x" not in html and "&lt;img src=x onerror=alert(2)&gt;" in html


def test_verification_page_without_the_secret_reveals_nothing(client):
    rec = mint(client).json()
    for params in ({}, {"s": "bad"}, {"s": "A" * 86}):
        r = client.get(f"/v/{rec['id']}", params=params)
        assert r.status_code == 404 and "Karthik" not in r.text and "No passport found" in r.text


def test_evidence_and_qr_endpoints(client):
    rec = mint(client).json()
    pid, sig = rec["id"], sig_of(rec)
    ev = client.get(f"/v/{pid}/evidence.jpg", params={"s": sig})
    assert ev.status_code == 200 and ev.content[:2] == b"\xff\xd8" and ev.headers["content-type"] == "image/jpeg"
    qr = client.get(f"/v/{pid}/qr.png", params={"s": sig})
    assert qr.status_code == 200 and qr.content[:8] == b"\x89PNG\r\n\x1a\n"
    assert imaging.decode_qr(qr.content) == rec["verify_url"]
    assert client.get(f"/v/{pid}/evidence.jpg").status_code == 404
    assert client.get(f"/v/{pid}/qr.png", params={"s": "nope"}).status_code == 404


def test_exif_gps_is_not_stored(client):
    from PIL import Image
    import io
    im = Image.open(io.BytesIO(imaging.sample_image("solar")))
    exif = Image.Exif()
    exif[0x010F] = "SecretPhoneMaker"
    buf = io.BytesIO()
    im.save(buf, format="JPEG", exif=exif.tobytes())
    r = client.post("/api/passports", data={"name": "Vignesh S.", "trade": "solar", "use_sample_voice": "true"},
                    files={"photo": ("p.jpg", buf.getvalue(), "image/jpeg")})
    rec = r.json()
    ev = client.get(f"/v/{rec['id']}/evidence.jpg", params={"s": rec["signature"]}).content
    assert b"SecretPhoneMaker" not in ev


# ------------------------------------------------------------------ verification API
def test_verify_by_link_and_by_short_payload(client):
    rec = mint(client).json()
    r = client.post("/api/verify", json={"payload": rec["verify_url"]}).json()
    assert r["valid"] is True and r["assurance"] == "demo" and r["credential_id"] == rec["id"]
    assert [s["label"] for s in r["steps"]] == ["Payload format", "Credential lookup", "Issuer", "Signature over the credential", "Evidence photo"]
    short = f"HQR1.{rec['id']}.{rec['signature']}"
    assert client.post("/api/verify", json={"payload": short}).json()["valid"] is True


def test_verify_detects_every_kind_of_tampering(client):
    rec = mint(client).json()
    pid, sig = rec["id"], rec["signature"]
    # holder presents an edited credential
    edited = {**rec["credential"], "credentialSubject": {**rec["credential"]["credentialSubject"], "practicalHours": 120}}
    r = client.post("/api/verify", json={"payload": rec["verify_url"], "credential": edited}).json()
    assert r["valid"] is False and not [s for s in r["steps"] if s["label"].startswith("Signature")][0]["ok"]
    # the presented credential, unedited, is accepted
    assert client.post("/api/verify", json={"payload": rec["verify_url"], "credential": rec["credential"]}).json()["valid"] is True
    # a credential for another ID
    other = {**rec["credential"], "id": "urn:hunarqr:HQR-TN-26-424242"}
    assert client.post("/api/verify", json={"payload": rec["verify_url"], "credential": other}).json()["valid"] is False
    # altered signature
    bad = sig[:-3] + ("AAA" if not sig.endswith("AAA") else "BBB")
    assert client.post("/api/verify", json={"payload": f"HQR1.{pid}.{bad}"}).json()["valid"] is False
    # unknown ID, garbage
    assert client.post("/api/verify", json={"payload": f"HQR1.HQR-TN-26-999999.{sig}"}).json()["valid"] is False
    for junk in ("hello", "", "http://x/v/%00?s=", "https://example.com/other?s=" + sig):
        assert client.post("/api/verify", json={"payload": junk}).json()["valid"] is False


def test_verify_detects_a_swapped_evidence_photo(client, settings):
    rec = mint(client).json()
    Path(settings.data_dir, "evidence", f"{rec['id']}.jpg").write_bytes(b"\xff\xd8swapped")
    r = client.post("/api/verify", json={"payload": rec["verify_url"]}).json()
    assert r["valid"] is False and [s for s in r["steps"] if s["label"] == "Evidence photo"][0]["ok"] is False


def test_verify_detects_a_changed_database_row(client, settings):
    import json, sqlite3
    rec = mint(client).json()
    db = sqlite3.connect(Path(settings.data_dir) / "hunar.db")
    cred = dict(rec["credential"])
    cred["credentialSubject"] = {**cred["credentialSubject"], "name": "Someone Else"}
    db.execute("UPDATE passports SET credential = ? WHERE id = ?", (json.dumps(cred), rec["id"]))
    db.commit()
    db.close()
    assert client.post("/api/verify", json={"payload": rec["verify_url"]}).json()["valid"] is False
    page = client.get(f"/v/{rec['id']}", params={"s": rec["signature"]}).text
    assert "Not valid" in page


def test_did_document_verifies_issued_credentials(client):
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.hazmat.primitives.asymmetric.utils import encode_dss_signature
    rec = mint(client).json()
    jwk = client.get("/.well-known/did.json").json()["verificationMethod"][0]["publicKeyJwk"]
    pub = ec.EllipticCurvePublicNumbers(int.from_bytes(unb64u(jwk["x"]), "big"), int.from_bytes(unb64u(jwk["y"]), "big"), ec.SECP256R1()).public_key()
    sig = unb64u(rec["signature"])
    pub.verify(encode_dss_signature(int.from_bytes(sig[:32], "big"), int.from_bytes(sig[32:], "big")),
               canonical(rec["credential"]), ec.ECDSA(hashes.SHA256()))


def test_stats_count_passports(client):
    mint(client)
    mint(client)
    s = client.get("/api/stats").json()
    assert s["passports_issued"] == 2 and s["demo_passports"] == 2


# ------------------------------------------------------------------ web demo chat uses the same bot
def test_chat_endpoint_runs_the_full_passport_flow(client):
    sid = "session-abc123"

    def say(**kw):
        r = client.post("/api/chat", json={"session_id": sid, **kw})
        assert r.status_code == 200, r.text
        return r.json()

    assert say(text="hello")["messages"][0]["buttons"][0]["id"] == "lang:en"
    say(button_id="lang:en")
    say(button_id="menu:passport")
    say(text="Karthik M.")
    say(button_id="trade:electrical")
    say(text="S. Karuppasamy")
    say(text="12")
    say(button_id="consent:yes")
    r = say(sample="photo")
    assert r["state"] == "VIDEO"
    r = say(sample="video")
    img = r["messages"][0]
    assert img["kind"] == "image" and img["media"].startswith("data:image/png;base64,")
    pid = img["meta"]["passport"]["id"]
    assert client.get(f"/v/{pid}", params={"s": img["meta"]["passport"]["signature"]}).status_code == 200
    assert say(text="hi")["state"] == "MENU"


def test_chat_validation_and_reset(client):
    assert client.post("/api/chat", json={"session_id": "short", "text": "hi"}).status_code == 422
    assert client.post("/api/chat", json={"session_id": "abcdefgh12", "image_b64": "!!!"}).status_code == 400
    sid = "session-reset1"
    client.post("/api/chat", json={"session_id": sid, "button_id": "lang:ta"})
    r = client.post("/api/chat", json={"session_id": sid, "reset": True, "text": "hello"}).json()
    assert r["lang"] is None and r["messages"][0]["buttons"][2]["id"] == "lang:hi"
