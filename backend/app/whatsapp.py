"""WhatsApp Cloud API: webhook parsing and signature check, media download, message sending.

Written to Meta's documented webhook and Graph API shapes and tested against mock transports.
It has NOT been run against a live WhatsApp Business account from this repository.
"""
from __future__ import annotations

import hashlib
import hmac
import logging
from dataclasses import dataclass

import httpx

from .bot import Bot, Inbound, Outbound
from .config import Settings
from .i18n import t
from .store import Store

log = logging.getLogger("hunarqr.whatsapp")

MAX_TEXT = 4096
MAX_BUTTON_BODY = 1024
MAX_BUTTON_TITLE = 20


def verify_signature(app_secret: str, body: bytes, header: str | None) -> bool:
    """X-Hub-Signature-256 is 'sha256=' + hex HMAC-SHA256 of the raw request body with the app secret."""
    if not app_secret or not header or not header.startswith("sha256="):
        return False
    expected = hmac.new(app_secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, header[7:])


@dataclass
class WAMessage:
    id: str
    sender: str
    kind: str                 # text | button | image | audio | other
    text: str = ""
    button_id: str = ""
    media_id: str = ""
    mime: str = ""


def parse_webhook(payload: dict) -> list[WAMessage]:
    out: list[WAMessage] = []
    for entry in payload.get("entry", []) or []:
        for change in entry.get("changes", []) or []:
            for m in (change.get("value") or {}).get("messages", []) or []:   # 'statuses' are ignored
                mid, sender, typ = m.get("id", ""), m.get("from", ""), m.get("type", "")
                if not mid or not sender:
                    continue
                if typ == "text":
                    out.append(WAMessage(mid, sender, "text", text=(m.get("text") or {}).get("body", "")))
                elif typ == "interactive":
                    inter = m.get("interactive") or {}
                    rep = inter.get("button_reply") or inter.get("list_reply") or {}
                    out.append(WAMessage(mid, sender, "button", text=rep.get("title", ""), button_id=rep.get("id", "")))
                elif typ in ("image", "audio"):
                    media = m.get(typ) or {}
                    out.append(WAMessage(mid, sender, typ, media_id=media.get("id", ""), mime=media.get("mime_type", ""),
                                         text=media.get("caption", "") if typ == "image" else ""))
                else:
                    out.append(WAMessage(mid, sender, "other"))
    return out


class WhatsAppClient:
    def __init__(self, s: Settings, client: httpx.Client | None = None):
        self.s = s
        self.client = client or httpx.Client(timeout=30)
        self.base = f"{s.graph_api_base}/{s.graph_api_version}"
        self.auth = {"Authorization": f"Bearer {s.whatsapp_access_token}"}

    def _post_message(self, body: dict) -> None:
        r = self.client.post(f"{self.base}/{self.s.whatsapp_phone_number_id}/messages", headers=self.auth,
                             json={"messaging_product": "whatsapp", **body})
        r.raise_for_status()

    def download_media(self, media_id: str) -> tuple[bytes, str]:
        meta = self.client.get(f"{self.base}/{media_id}", headers=self.auth)
        meta.raise_for_status()
        info = meta.json()
        r = self.client.get(info["url"], headers=self.auth)
        r.raise_for_status()
        return r.content, info.get("mime_type", "")

    def upload_media(self, data: bytes, mime: str) -> str:
        r = self.client.post(f"{self.base}/{self.s.whatsapp_phone_number_id}/media", headers=self.auth,
                             data={"messaging_product": "whatsapp", "type": mime},
                             files={"file": ("file", data, mime)})
        r.raise_for_status()
        return r.json()["id"]

    def send(self, to: str, o: Outbound) -> None:
        if o.kind == "text":
            self._post_message({"to": to, "type": "text", "text": {"body": o.text[:MAX_TEXT]}})
        elif o.kind == "buttons":
            self._post_message({"to": to, "type": "interactive", "interactive": {
                "type": "button", "body": {"text": o.text[:MAX_BUTTON_BODY]},
                "action": {"buttons": [{"type": "reply", "reply": {"id": i, "title": title[:MAX_BUTTON_TITLE]}}
                                       for i, title in o.buttons[:3]]}}})
        elif o.kind == "image" and o.media:
            mid = self.upload_media(o.media, o.mime or "image/png")
            self._post_message({"to": to, "type": "image", "image": {"id": mid, "caption": o.text[:1024]}})
        elif o.kind == "audio" and o.media:
            mid = self.upload_media(o.media, o.mime or "audio/ogg")
            self._post_message({"to": to, "type": "audio", "audio": {"id": mid}})


def process_webhook(payload: dict, *, bot: Bot, client: WhatsAppClient, store: Store, hash_user) -> int:
    """Handle every message in a webhook delivery. Returns the number of messages handled."""
    handled = 0
    for wm in parse_webhook(payload):
        if not store.mark_seen(wm.id):
            continue   # Meta redelivered a message we already handled
        handled += 1
        try:
            if wm.kind == "other":
                inbound = Inbound("text", "")
            elif wm.kind in ("image", "audio"):
                data, mime = client.download_media(wm.media_id)
                inbound = Inbound(wm.kind, wm.text, media=data, mime=mime or wm.mime)
            else:
                inbound = Inbound(wm.kind, wm.text, button_id=wm.button_id)
            for o in bot.handle(hash_user(wm.sender), inbound, channel="whatsapp"):
                client.send(wm.sender, o)
        except Exception:   # noqa: BLE001 - never let one bad message break the delivery
            log.exception("failed to handle WhatsApp message %s", wm.id)
            try:
                client.send(wm.sender, Outbound("text", t("en", "error")))
            except Exception:   # noqa: BLE001
                log.exception("could not send the error reply")
    return handled
