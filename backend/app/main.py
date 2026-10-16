"""FastAPI application: web demo API, verification pages and the WhatsApp webhook."""
from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import logging
from pathlib import Path
from typing import Literal

from fastapi import BackgroundTasks, Depends, FastAPI, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, PlainTextResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import __version__, fraud, imaging
from .bot import Bot, Inbound, Outbound
from .config import Settings, load_or_create_secret
from .credentials import Issuer, fingerprint, unb64u
from .data import LANGS, LANG_NAMES, TRADE_ORDER, TRADES
from .i18n import t
from .pages import render_not_found, render_passport
from .passports import PassportService, parse_payload
from .providers import ProviderError, build_asr, build_tts, build_vision, clean_text
from .ratelimit import RateLimiter
from .store import Store
from .whatsapp import WhatsAppClient, process_webhook, verify_signature

log = logging.getLogger("hunarqr")


class AnalyzeIn(BaseModel):
    text: str = Field("", max_length=8000)
    qr_text: str = Field("", max_length=4000)


class VerifyIn(BaseModel):
    payload: str = Field(max_length=2000)
    credential: dict | None = None


class ChatIn(BaseModel):
    session_id: str = Field(pattern=r"^[A-Za-z0-9_-]{8,64}$")
    text: str = Field("", max_length=2000)
    button_id: str = Field("", max_length=64)
    image_b64: str = Field("", max_length=8_000_000)
    audio_b64: str = Field("", max_length=8_000_000)
    sample: Literal["", "photo", "voice"] = ""
    reset: bool = False


def _unb64(data: str, limit: int, what: str) -> bytes:
    try:
        raw = base64.b64decode(data, validate=True)
    except (binascii.Error, ValueError):
        raise HTTPException(400, f"{what} is not valid base64")
    if len(raw) > limit:
        raise HTTPException(413, f"{what} is too large")
    return raw


def _read_upload(f: UploadFile | None, limit: int, what: str) -> bytes | None:
    if f is None:
        return None
    raw = f.file.read(limit + 1)
    if len(raw) > limit:
        raise HTTPException(413, f"{what} is too large")
    return raw or None


def create_app(settings: Settings | None = None, *, asr=None, vision=None, tts=None, wa_client=None) -> FastAPI:
    s = settings or Settings.from_env()
    s.data_dir.mkdir(parents=True, exist_ok=True)
    store = Store(s.data_dir / "hunar.db")
    secret = (s.hash_secret or load_or_create_secret(s.data_dir / "secret.key")).encode()
    issuer = Issuer.load_or_create(key_pem=s.issuer_key_pem, key_path=s.data_dir / "issuer_key.pem", did=s.issuer_did)
    asr = asr or build_asr(s)
    vision = vision or build_vision(s)
    tts = tts or build_tts(s)
    svc = PassportService(s, store, issuer, asr, vision)
    bot = Bot(s, store, svc, tts)
    wa = wa_client or (WhatsAppClient(s) if s.whatsapp_configured else None)
    bot.purge()

    def hash_user(user_id: str) -> str:
        return hmac.new(secret, user_id.encode(), hashlib.sha256).hexdigest()

    limits = {"analyze": RateLimiter(s.rate_analyze_per_min), "mint": RateLimiter(s.rate_mint_per_min),
              "chat": RateLimiter(s.rate_chat_per_min)}

    def client_ip(request: Request) -> str:
        if s.trust_proxy:
            fwd = request.headers.get("x-forwarded-for", "")
            if fwd:
                return fwd.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    def limited(name: str):
        def dep(request: Request):
            if not limits[name].allow(client_ip(request)):
                raise HTTPException(429, "Too many requests. Try again in a minute.", headers={"Retry-After": "60"})
        return dep

    def need_demo():
        if not s.enable_demo_api:
            raise HTTPException(404, "Not found")

    app = FastAPI(title="Hunar-QR API", version=__version__,
                  description="Skill Passport issuing, fraud checks and the WhatsApp bot. Prototype.")
    app.state.settings, app.state.store, app.state.issuer, app.state.bot, app.state.passports = s, store, issuer, bot, svc

    app.add_middleware(CORSMiddleware, allow_origins=list(s.cors_origins), allow_methods=["GET", "POST"],
                       allow_headers=["*"], max_age=600)

    @app.middleware("http")
    async def guard(request: Request, call_next):
        cl = request.headers.get("content-length")
        if cl and cl.isdigit() and int(cl) > s.max_upload_bytes * 2 + 100_000:
            return JSONResponse({"detail": "Request body too large"}, status_code=413)
        resp = await call_next(request)
        resp.headers.setdefault("X-Content-Type-Options", "nosniff")
        resp.headers.setdefault("Referrer-Policy", "no-referrer")
        if request.url.path.startswith(("/v/", "/api/passports")):
            resp.headers["Cache-Control"] = "no-store"
        return resp

    # ------------------------------------------------------------------ basics
    @app.get("/healthz")
    def healthz():
        return {"ok": True, "version": __version__}

    @app.get("/api/meta")
    def meta():
        return {"name": "Hunar-QR API", "version": __version__, "demo_api": s.enable_demo_api,
                "providers": {"asr": asr.name, "vision": vision.name, "tts": tts.name},
                "assurance": svc.assurance_level, "whatsapp_configured": s.whatsapp_configured,
                "issuer_did": issuer.did, "languages": [{"id": k, "name": LANG_NAMES[k]} for k in LANGS],
                "trades": [{"id": k, "name": TRADES[k]["name"], "short": TRADES[k]["short"],
                            "sample_learner": TRADES[k]["sample_learner"], "sample_mentor": TRADES[k]["sample_mentor"],
                            "sample_hours": TRADES[k]["sample_hours"]} for k in TRADE_ORDER]}

    @app.get("/api/stats")
    def stats():
        return store.stats()

    @app.get("/.well-known/did.json")
    def did_doc():
        return issuer.did_document()

    # ------------------------------------------------------------------ scam shield
    @app.post("/api/analyze", dependencies=[Depends(limited("analyze"))])
    def analyze(body: AnalyzeIn):
        text = "\n".join(x for x in (body.text.strip(), f"QR code content: {body.qr_text.strip()}" if body.qr_text.strip() else "") if x)
        a = fraud.analyze(text)
        if a["verdict"] != "empty":
            store.log_check("web", a["verdict"], a["score"], hashlib.sha256(text.encode()).hexdigest())
        return a

    @app.post("/api/analyze-image", dependencies=[Depends(limited("analyze"))])
    def analyze_image(image: UploadFile = File(...), text: str = Form("")):
        raw = _read_upload(image, s.max_upload_bytes, "image")
        qr = imaging.decode_qr(raw) if raw else None
        if not qr:
            raise HTTPException(422, "No QR code could be read in that image.")
        a = fraud.analyze("\n".join(x for x in (clean_text(text, 2000), f"QR code content: {qr}") if x))
        store.log_check("web", a["verdict"], a["score"], hashlib.sha256(qr.encode()).hexdigest())
        a["qr_text"] = qr
        return a

    # ------------------------------------------------------------------ passports
    @app.post("/api/passports", dependencies=[Depends(limited("mint")), Depends(need_demo)])
    def create_passport(name: str = Form(...), trade: str = Form(...), language: str = Form("en"),
                        mentor_name: str = Form(""), hours: int | None = Form(None),
                        learner_type: str = Form("unspecified"), use_sample_photo: bool = Form(False),
                        use_sample_voice: bool = Form(False), demo_seed: bool = Form(False),
                        photo: UploadFile | None = File(None), audio: UploadFile | None = File(None)):
        """Web-demo minting. The WhatsApp bot is the real channel; this lets a browser demo the same pipeline."""
        if trade not in TRADES:
            raise HTTPException(422, "Unknown trade")
        if language not in LANGS:
            raise HTTPException(422, "Unknown language")
        if learner_type not in ("school", "apprentice", "unspecified"):
            raise HTTPException(422, "Unknown learner type")
        name = clean_text(name, 60)
        if len(name) < 2:
            raise HTTPException(422, "Name is too short")
        hours = TRADES[trade]["sample_hours"] if hours is None else hours
        if not 1 <= hours <= 500:
            raise HTTPException(422, "Hours must be between 1 and 500")
        mentor = clean_text(mentor_name, 60) or TRADES[trade]["sample_mentor"]
        raw_photo = _read_upload(photo, s.max_upload_bytes, "photo")
        if raw_photo is None:
            if not use_sample_photo:
                raise HTTPException(422, "Send a photo or set use_sample_photo")
            raw_photo = imaging.sample_image(trade)
        raw_audio = _read_upload(audio, s.max_upload_bytes, "audio")
        if raw_audio is None:
            if not use_sample_voice or asr.name != "mock":
                raise HTTPException(422, "Send a voice note" + ("" if asr.name == "mock" else " (sample voice is only available with the mock speech provider)"))
            raw_audio = b"sample-voice-note"
        try:
            assessed = svc.assess_photo(raw_photo, trade)
            rec = svc.mint(name=name, trade_id=trade, mentor_name=mentor, hours=hours, lang=language,
                           learner_type=learner_type, photo=assessed, audio=raw_audio,
                           audio_mime=audio.content_type if audio else "audio/ogg",
                           owner_hash="demo" if demo_seed else "web")
        except imaging.ImageRejected as e:
            raise HTTPException(422, t("en", "bad_photo", reason=t("en", f"r_{e.code}")))
        except ProviderError as e:
            raise HTTPException(422 if e.code == "no_work" else 502, str(e))
        return rec

    def _owned(pid: str, sig: str) -> dict:
        rec = store.get_passport(pid)
        if not rec or not sig or not hmac.compare_digest(rec["signature"], sig):
            raise HTTPException(404, "Passport not found")
        return rec

    @app.get("/api/demo-passport", dependencies=[Depends(need_demo)])
    def demo_passport():
        """A ready-made passport for the demo's verify tab, created once."""
        rec = store.get_demo_passport()
        if rec is None:
            tr = TRADES["electrical"]
            assessed = svc.assess_photo(imaging.sample_image("electrical"), "electrical")
            made = svc.mint(name=tr["sample_learner"], trade_id="electrical", mentor_name=tr["sample_mentor"],
                            hours=tr["sample_hours"], lang="ta", learner_type="school", photo=assessed,
                            audio=b"sample-voice-note", audio_mime="audio/ogg", owner_hash="demo")
            return made
        sig = rec["signature"]
        return {"id": rec["id"], "credential": rec["credential"], "signature": sig,
                "fingerprint": fingerprint(unb64u(sig)), "verify_url": svc.verify_url(rec["id"], sig),
                "assurance": rec["assurance"], "evidence_path": f"/v/{rec['id']}/evidence.jpg?s={sig}"}

    @app.get("/api/passports/{pid}")
    def get_passport(pid: str, sig: str = Query("", alias="s")):
        rec = _owned(pid, sig)
        return {"id": pid, "credential": rec["credential"], "signature": rec["signature"],
                "assurance": rec["assurance"], "verify_url": svc.verify_url(pid, rec["signature"])}

    @app.post("/api/verify", dependencies=[Depends(limited("analyze"))])
    def verify(body: VerifyIn):
        return svc.verify(body.payload, body.credential)

    # ------------------------------------------------------------------ hosted verification page
    @app.get("/v/{pid}", response_class=HTMLResponse)
    def passport_page(pid: str, sig: str = Query("", alias="s")):
        try:
            rec = _owned(pid, sig)
        except HTTPException:
            return HTMLResponse(render_not_found(), status_code=404)
        res = svc.verify(svc.verify_url(pid, rec["signature"]))
        return HTMLResponse(render_passport(pid=pid, cred=rec["credential"], result=res, sig_param=rec["signature"],
                                            fingerprint=fingerprint(unb64u(rec["signature"]))),
                            headers={"Content-Security-Policy": "default-src 'none'; img-src 'self'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'"})

    @app.get("/v/{pid}/evidence.jpg")
    def evidence(pid: str, sig: str = Query("", alias="s")):
        rec = _owned(pid, sig)
        p = Path(rec["evidence_path"])
        if not p.is_file():
            raise HTTPException(404, "Evidence not found")
        return FileResponse(p, media_type="image/jpeg")

    @app.get("/v/{pid}/qr.png")
    def qr_image(pid: str, sig: str = Query("", alias="s")):
        rec = _owned(pid, sig)
        return Response(imaging.qr_png(svc.verify_url(pid, rec["signature"])), media_type="image/png")

    # ------------------------------------------------------------------ web demo chat (same bot as WhatsApp)
    def _serialize(o: Outbound) -> dict:
        d: dict = {"kind": o.kind, "text": o.text}
        if o.buttons:
            d["buttons"] = [{"id": i, "title": ti} for i, ti in o.buttons]
        if o.media:
            d["media"] = f"data:{o.mime};base64,{base64.b64encode(o.media).decode()}"
        if o.meta:
            d["meta"] = o.meta
        return d

    @app.post("/api/chat", dependencies=[Depends(limited("chat")), Depends(need_demo)])
    def chat(body: ChatIn):
        key = hash_user("web:" + body.session_id)
        if body.reset:
            store.delete_conversation(key)
        conv = store.get_conversation(key) or {}
        if body.sample == "photo":
            trade = (conv.get("data") or {}).get("trade") or "electrical"
            msg = Inbound("image", media=imaging.sample_image(trade), mime="image/png")
        elif body.sample == "voice":
            if asr.name != "mock":
                raise HTTPException(422, "Sample voice is only available with the mock speech provider")
            msg = Inbound("audio", media=b"sample-voice-note", mime="audio/ogg")
        elif body.image_b64:
            msg = Inbound("image", media=_unb64(body.image_b64, s.max_upload_bytes, "image"), mime="image/jpeg")
        elif body.audio_b64:
            msg = Inbound("audio", media=_unb64(body.audio_b64, s.max_upload_bytes, "audio"), mime="audio/ogg")
        elif body.button_id:
            msg = Inbound("button", text=body.text, button_id=body.button_id)
        else:
            msg = Inbound("text", text=body.text)
        out = bot.handle(key, msg, channel="web")
        conv = store.get_conversation(key) or {}
        return {"messages": [_serialize(o) for o in out], "state": conv.get("state"), "lang": conv.get("lang")}

    # ------------------------------------------------------------------ WhatsApp webhook
    @app.get("/webhook/whatsapp")
    def wa_verify(request: Request):
        q = request.query_params
        if q.get("hub.mode") == "subscribe" and s.whatsapp_verify_token and hmac.compare_digest(
                q.get("hub.verify_token", ""), s.whatsapp_verify_token):
            return PlainTextResponse(q.get("hub.challenge", ""))
        raise HTTPException(403, "Verification failed")

    @app.post("/webhook/whatsapp")
    async def wa_receive(request: Request, background: BackgroundTasks):
        raw = await request.body()
        if s.whatsapp_app_secret:
            if not verify_signature(s.whatsapp_app_secret, raw, request.headers.get("x-hub-signature-256")):
                raise HTTPException(403, "Bad signature")
        elif not s.allow_unsigned_webhook:
            raise HTTPException(403, "WHATSAPP_APP_SECRET is not set; refusing unsigned webhook")
        if wa is None:
            raise HTTPException(503, "WhatsApp is not configured")
        try:
            payload = await request.json()
        except ValueError:
            raise HTTPException(400, "Invalid JSON")
        background.add_task(process_webhook, payload, bot=bot, client=wa, store=store, hash_user=hash_user)
        return {"status": "ok"}

    # ------------------------------------------------------------------ static web demo (last, so API routes win)
    web = Path(s.web_dir) if s.web_dir else None
    if web and (web / "index.html").is_file():
        app.mount("/", StaticFiles(directory=web, html=True), name="web")
    else:
        @app.get("/")
        def root():
            return {"name": "Hunar-QR API", "docs": "/docs"}

    return app

