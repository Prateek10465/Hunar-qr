import hashlib
import hmac
import json
import sqlite3
from dataclasses import replace
from pathlib import Path

import httpx
from fastapi.testclient import TestClient

from app import imaging
from app.main import create_app
from app.whatsapp import WhatsAppClient, parse_webhook, verify_signature

from conftest import PHONE

SECRET = "appsecret"


def sign(body: bytes, secret=SECRET) -> str:
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def payload(*messages, statuses=None):
    value = {"messaging_product": "whatsapp", "metadata": {"phone_number_id": "123"}}
    if messages:
        value["messages"] = list(messages)
    if statuses:
        value["statuses"] = statuses
    return {"object": "whatsapp_business_account", "entry": [{"id": "WABA", "changes": [{"field": "messages", "value": value}]}]}


def text(mid, body, sender=PHONE):
    return {"id": mid, "from": sender, "type": "text", "text": {"body": body}}


def button(mid, bid, title="x", sender=PHONE):
    return {"id": mid, "from": sender, "type": "interactive", "interactive": {"type": "button_reply", "button_reply": {"id": bid, "title": title}}}


def media(mid, kind, media_id, mime, sender=PHONE):
    return {"id": mid, "from": sender, "type": kind, kind: {"id": media_id, "mime_type": mime}}


def post(client, pl, secret=SECRET):
    body = json.dumps(pl).encode()
    headers = {"content-type": "application/json"}
    if secret is not None:
        headers["x-hub-signature-256"] = sign(body, secret)
    return client.post("/webhook/whatsapp", content=body, headers=headers)


# ------------------------------------------------------------------ signature and parsing
def test_signature_check():
    body = b'{"a":1}'
    assert verify_signature(SECRET, body, sign(body))
    assert not verify_signature(SECRET, body, sign(body, "other"))
    assert not verify_signature(SECRET, body, None)
    assert not verify_signature(SECRET, body, "sha1=" + "0" * 40)
    assert not verify_signature(SECRET, body + b" ", sign(body))
    assert not verify_signature("", body, sign(body, ""))


def test_parse_webhook_handles_each_message_type_and_ignores_statuses():
    msgs = parse_webhook(payload(text("m1", "hello"), button("m2", "lang:ta", "தமிழ்"), media("m3", "image", "IMG1", "image/jpeg"),
                                 media("m4", "audio", "AUD1", "audio/ogg; codecs=opus"),
                                 {"id": "m5", "from": PHONE, "type": "sticker", "sticker": {}}))
    assert [(m.kind, m.text, m.button_id, m.media_id) for m in msgs] == [
        ("text", "hello", "", ""), ("button", "தமிழ்", "lang:ta", ""), ("image", "", "", "IMG1"),
        ("audio", "", "", "AUD1"), ("other", "", "", "")]
    assert parse_webhook(payload(statuses=[{"id": "x", "status": "delivered"}])) == []
    assert parse_webhook({}) == [] and parse_webhook({"entry": [{"changes": [{}]}]}) == []


# ------------------------------------------------------------------ endpoint security
def test_webhook_handshake(client):
    ok = client.get("/webhook/whatsapp", params={"hub.mode": "subscribe", "hub.verify_token": "verify-me", "hub.challenge": "12345"})
    assert ok.status_code == 200 and ok.text == "12345"
    for params in ({"hub.mode": "subscribe", "hub.verify_token": "wrong", "hub.challenge": "1"},
                   {"hub.mode": "unsubscribe", "hub.verify_token": "verify-me", "hub.challenge": "1"}, {}):
        assert client.get("/webhook/whatsapp", params=params).status_code == 403


def test_handshake_refused_when_no_token_is_configured(make_app):
    with make_app(whatsapp_verify_token="") as c:
        assert c.get("/webhook/whatsapp", params={"hub.mode": "subscribe", "hub.verify_token": "", "hub.challenge": "1"}).status_code == 403


def test_unsigned_or_badly_signed_posts_are_refused(client, wa_mock):
    pl = payload(text("m1", "hello"))
    assert post(client, pl, secret=None).status_code == 403
    assert post(client, pl, secret="wrong").status_code == 403
    assert wa_mock.requests == []


def test_posts_are_refused_without_an_app_secret_unless_explicitly_allowed(make_app, wa_mock):
    pl = payload(text("m1", "hello"))
    with make_app(whatsapp_app_secret="") as c:
        assert c.post("/webhook/whatsapp", json=pl).status_code == 403
    with make_app(whatsapp_app_secret="", allow_unsigned_webhook=True, whatsapp_access_token="") as c:
        assert c.post("/webhook/whatsapp", json=pl).status_code == 503       # allowed, but WhatsApp itself is not configured


def test_invalid_json_with_a_valid_signature(client):
    body = b"{not json"
    r = client.post("/webhook/whatsapp", content=body, headers={"x-hub-signature-256": sign(body)})
    assert r.status_code == 400


# ------------------------------------------------------------------ message handling
def test_first_message_gets_language_buttons(client, wa_mock):
    assert post(client, payload(text("m1", "hi"))).json() == {"status": "ok"}
    sent = wa_mock.sent()
    assert len(sent) == 1
    m = sent[0]
    assert m["messaging_product"] == "whatsapp" and m["to"] == PHONE and m["type"] == "interactive"
    buttons = m["interactive"]["action"]["buttons"]
    assert [b["reply"]["id"] for b in buttons] == ["lang:en", "lang:ta", "lang:hi"] and all(len(b["reply"]["title"]) <= 20 for b in buttons)
    req = [r for r in wa_mock.requests if r.url.path.endswith("/messages")][0]
    assert req.url.path == "/v21.0/123/messages" and req.headers["authorization"] == "Bearer TOKEN"


def test_redelivered_messages_are_handled_once(client, wa_mock):
    pl = payload(text("same-id", "hi"))
    post(client, pl)
    post(client, pl)
    assert len(wa_mock.sent()) == 1


def test_one_failing_message_does_not_block_the_rest(client, wa_mock):
    wa_mock.fail_messages = True
    assert post(client, payload(text("m1", "hi"), text("m2", "hello"))).status_code == 200
    assert len(wa_mock.requests) >= 2       # both were attempted, plus the error replies


def test_scam_forward_over_whatsapp(client, wa_mock):
    post(client, payload(button("m1", "lang:en", "English")))
    wa_mock.requests.clear()
    post(client, payload(text("m2", "Pay ₹99 processing fee at bit.ly/pm-kaushal-claim now")))
    bodies = [m["text"]["body"] for m in wa_mock.sent() if m["type"] == "text"]
    assert "Danger" in bodies[0] and "zero-fee openings" in bodies[1]


def test_full_passport_over_whatsapp_with_media(client, wa_mock, settings):
    wa_mock.media["IMG1"] = (imaging.sample_image("electrical"), "image/png")
    wa_mock.media["AUD1"] = (b"OPUSBYTES", "audio/ogg; codecs=opus")
    i = iter(range(1, 100))
    step = lambda m: post(client, payload(m(f"w{next(i)}")))
    step(lambda n: button(n, "lang:en"))
    step(lambda n: button(n, "menu:passport"))
    step(lambda n: text(n, "Karthik M."))
    step(lambda n: button(n, "trade:electrical"))
    step(lambda n: text(n, "S. Karuppasamy"))
    step(lambda n: text(n, "12"))
    step(lambda n: button(n, "consent:yes"))
    step(lambda n: media(n, "image", "IMG1", "image/png"))
    wa_mock.requests.clear()
    step(lambda n: media(n, "audio", "AUD1", "audio/ogg"))
    # the media was fetched in two steps: the Graph lookup, then the file URL
    gets = [r for r in wa_mock.requests if r.method == "GET"]
    assert gets[0].url.path == "/v21.0/AUD1" and gets[1].url.host == "lookaside.example" and gets[1].headers["authorization"] == "Bearer TOKEN"
    # the passport QR was uploaded, then sent as an image message that references the upload
    up = [r for r in wa_mock.requests if r.url.path == "/v21.0/123/media"]
    assert len(up) == 1 and b"image/png" in up[0].content
    last = wa_mock.sent()[-1]
    assert last["type"] == "image" and last["image"]["id"] == "MEDIA-OUT" and "/v/HQR-TN-" in last["image"]["caption"]
    assert client.app_state.store.stats()["passports_issued"] == 1


def test_phone_numbers_are_never_stored(client, settings):
    post(client, payload(text("m1", "hi")))
    post(client, payload(button("m2", "lang:en")))
    post(client, payload(button("m3", "menu:passport")))
    post(client, payload(text("m4", "Karthik M.")))
    db = sqlite3.connect(Path(settings.data_dir) / "hunar.db")
    rows = db.execute("SELECT user_hash FROM conversations").fetchall()
    assert len(rows) == 1 and PHONE not in rows[0][0] and len(rows[0][0]) == 64
    dump = "\n".join(db.iterdump())
    assert PHONE not in dump
    db.close()


def test_other_message_types_get_the_menu_not_a_crash(client, wa_mock):
    post(client, payload(button("m1", "lang:en")))
    wa_mock.requests.clear()
    post(client, payload({"id": "m2", "from": PHONE, "type": "sticker", "sticker": {"id": "s"}}))
    assert wa_mock.sent()[0]["type"] == "interactive"


def test_whatsapp_client_truncates_long_text_and_titles(settings):
    sent = []
    c = WhatsAppClient(settings, httpx.Client(transport=httpx.MockTransport(lambda r: (sent.append(json.loads(r.content)), httpx.Response(200, json={}))[1])))
    from app.bot import Outbound
    c.send("1", Outbound("text", "x" * 9000))
    c.send("1", Outbound("buttons", "y" * 2000, [("a", "T" * 50)] * 5))
    assert len(sent[0]["text"]["body"]) == 4096
    assert len(sent[1]["interactive"]["body"]["text"]) == 1024 and len(sent[1]["interactive"]["action"]["buttons"]) == 3
    assert len(sent[1]["interactive"]["action"]["buttons"][0]["reply"]["title"]) == 20
