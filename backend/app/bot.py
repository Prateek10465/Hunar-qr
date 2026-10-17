"""The Hunar-QR bot: one conversation engine used by WhatsApp and by the web demo chat.

Passport flow:  NAME > TRADE > MENTOR > HOURS > CONSENT > PHOTO > VOICE > passport.
Scam checks work at any time outside the passport flow: forward text, a link, a UPI request or a QR image.
"""
from __future__ import annotations

import hashlib
import logging
import random
import time
from dataclasses import dataclass, field
from pathlib import Path

from . import aadhaar, fraud, imaging
from .config import Settings
from .data import LANGS, LISTINGS, SECTOR_ORDER, SECTORS, TRADE_ORDER, TRADES
from .i18n import CANCEL_WORDS, GREETINGS, NO_WORDS, YES_WORDS, t
from .passports import PassportService, PhotoAssessment
from .providers import ProviderError, TTSProvider, clean_text
from .store import Store

log = logging.getLogger("hunarqr.bot")

PASSPORT_STATES = ("NAME", "AADHAAR", "AADHAAR_OTP", "SECTOR", "TRADE", "MENTOR", "HOURS", "CONSENT", "PHOTO", "VIDEO", "VOICE", "VIVA")


@dataclass
class Inbound:
    kind: str                      # text | button | image | audio
    text: str = ""
    button_id: str = ""
    media: bytes | None = None
    mime: str = ""


@dataclass
class Outbound:
    kind: str                      # text | buttons | image | audio
    text: str = ""
    buttons: list[tuple[str, str]] = field(default_factory=list)   # (id, title)
    media: bytes | None = None
    mime: str = ""
    meta: dict = field(default_factory=dict)


def _text(s: str) -> Outbound:
    return Outbound("text", s)


class Bot:
    def __init__(self, settings: Settings, store: Store, passports: PassportService, tts: TTSProvider):
        self.s, self.store, self.passports, self.tts = settings, store, passports, tts
        self.tmp_dir = settings.data_dir / "tmp"
        self.tmp_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------ entry point
    def handle(self, user_key: str, msg: Inbound, channel: str = "whatsapp") -> list[Outbound]:
        conv = self.store.get_conversation(user_key) or {"state": "LANG", "lang": None, "data": {}}
        try:
            out = self._dispatch(user_key, conv, msg, channel)
        except Exception:   # noqa: BLE001 - the user must always get a reply
            log.exception("bot error")
            out = [_text(t(conv.get("lang"), "error"))]
        self.store.save_conversation(user_key, conv)
        return out

    # ------------------------------------------------------------------ routing
    def _dispatch(self, key: str, conv: dict, msg: Inbound, channel: str) -> list[Outbound]:
        text = (msg.text or "").strip()
        low = text.lower()
        state = conv["state"]
        lang = conv.get("lang")

        # Language button click directly switches language at any point
        if msg.button_id.startswith("lang:"):
            chosen = self._pick_lang(msg)
            if chosen:
                conv.update(lang=chosen)
                if state == "LANG":
                    conv["state"] = "MENU"
                return [self._menu(chosen)]

        if lang is None or state == "LANG":
            if msg.button_id.startswith("lang_page:"):
                try:
                    p = int(msg.button_id.split(":", 1)[1])
                except (ValueError, IndexError):
                    p = 1
                return [self._lang_prompt(page=p)]
            if low in ("more", "more languages", "next", "अगला", "அடுத்து", "other", "others"):
                return [self._lang_prompt(page=2)]
            if low in ("prev", "previous", "back", "पिछला", "முந்தைய"):
                return [self._lang_prompt(page=1)]
            chosen = self._pick_lang(msg)
            if chosen:
                conv.update(lang=chosen, state="MENU")
                return [self._menu(chosen)]
            checked = self._try_check(msg, "en", conv, channel)
            return (checked or []) + [self._lang_prompt()]

        if state in PASSPORT_STATES:
            if low in CANCEL_WORDS or msg.button_id == "menu:home":
                self._reset(key, conv)
                return [_text(t(lang, "stopped"))]
            return self._passport_step(key, conv, msg, text, low)

        # idle / menu
        if low in GREETINGS or msg.button_id == "menu:home":
            return [self._menu(lang)]
        if low in ("lang", "language", "भाषा", "மொழி", "மாற்று", "बदलें", "ಭಾಷೆ", "భాష", "ভাষা", "ભાષા", "ഭാഷ", "ਭਾਸ਼ਾ", "ଭାଷା"):
            conv["state"] = "LANG"
            return [self._lang_prompt()]
        if msg.button_id == "menu:passport" or low == "1" or any(w in low for w in (
            "passport", "skill", "पासपोर्ट", "பாஸ்போர்ட்", "పాస్‌పోర్ట్", "পাসপোর্ট",
            "પાસપોર્ટ", "ಪಾಸ್‌ಪೋರ್ಟ್", "പാസ്പോർട്ട്", "ਪਾਸਪੋਰਟ", "ପାସପୋର୍ଟ", "পাছপৰ্ট"
        )):
            conv["state"], conv["data"] = "NAME", {}
            return [_text(t(lang, "ask_name"))]
        if msg.button_id == "menu:check" or low == "2" or any(w in low for w in (
            "check", "scam", "fraud", "जाँच", "जांच", "சரிபார்", "తనిఖీ", "যাচাই", "ચકાસો", "ಪರಿಶೀಲಿಸಿ", "പരിಶോധിക്കുക", "ਜਾਂਚ", "ଯାଞ୍ଚ"
        )):
            return [_text(t(lang, "check_prompt"))]
        checked = self._try_check(msg, lang, conv, channel)
        if checked:
            return checked
        if msg.kind == "image":
            return [_text(t(lang, "no_qr")), self._menu(lang)]
        return [self._menu(lang)]

    # ------------------------------------------------------------------ language and menu
    @staticmethod
    def _pick_lang(msg: Inbound) -> str | None:
        if msg.button_id.startswith("lang:"):
            code = msg.button_id.split(":", 1)[1]
            return code if code in LANGS else None
        v = (msg.text or "").strip().lower()
        mapping = {
            # 1. English
            "1": "en", "english": "en", "en": "en",
            # 2. Tamil
            "2": "ta", "tamil": "ta", "தமிழ்": "ta", "ta": "ta",
            # 3. Hindi
            "3": "hi", "hindi": "hi", "हिन्दी": "hi", "हिंदी": "hi", "hi-in": "hi",
            # 4. Telugu
            "4": "te", "te": "te", "telugu": "te", "తెలుగు": "te",
            # 5. Bengali
            "5": "bn", "bn": "bn", "bengali": "bn", "bangla": "bn", "বাংলা": "bn",
            # 6. Marathi
            "6": "mr", "mr": "mr", "marathi": "mr", "मराठी": "mr",
            # 7. Gujarati
            "7": "gu", "gu": "gu", "gujarati": "gu", "ગુજરાતી": "gu",
            # 8. Kannada
            "8": "kn", "kn": "kn", "kannada": "kn", "ಕನ್ನಡ": "kn",
            # 9. Malayalam
            "9": "ml", "ml": "ml", "malayalam": "ml", "മലയാളം": "ml",
            # 10. Punjabi
            "10": "pa", "pa": "pa", "punjabi": "pa", "ਪੰਜਾਬੀ": "pa",
            # 11. Odia
            "11": "or", "or": "or", "odia": "or", "oriya": "or", "ଓଡ଼ିଆ": "or",
            # 12. Assamese
            "12": "as", "as": "as", "assamese": "as", "অসমীয়া": "as",
            # 13. Urdu
            "13": "ur", "ur": "ur", "urdu": "ur", "اردو": "ur",
            # 14. Sanskrit
            "14": "sa", "sa": "sa", "sanskrit": "sa", "संस्कृतम्": "sa", "संस्कृत": "sa",
            # 15. Nepali
            "15": "ne", "ne": "ne", "nepali": "ne", "नेपाली": "ne",
            # 16. Konkani
            "16": "kok", "kok": "kok", "konkani": "kok", "कोंकणी": "kok",
            # 17. Maithili
            "17": "mai", "mai": "mai", "maithili": "mai", "मैथिली": "mai",
            # 18. Sindhi
            "18": "sd", "sd": "sd", "sindhi": "sd", "सिंधी": "sd", "سنڌي": "sd",
            # 19. Kashmiri
            "19": "ks", "ks": "ks", "kashmiri": "ks", "कश्मीरी": "ks", "کٲشُر": "ks",
            # 20. Bodo
            "20": "brx", "brx": "brx", "bodo": "brx", "बर'": "brx",
            # 21. Dogri
            "21": "doi", "doi": "doi", "dogri": "doi", "डोगरी": "doi",
            # 22. Manipuri
            "22": "mni", "mni": "mni", "manipuri": "mni", "meitei": "mni", "মৈতৈলোন্": "mni",
            # 23. Santali
            "23": "sat", "sat": "sat", "santali": "sat", "ᱥᱟᱱᱛᱟᱲᱤ": "sat",
        }
        if v in mapping:
            return mapping[v]
        v_clean = v.strip(".# \t")
        if v_clean in mapping:
            return mapping[v_clean]
        digits = "".join(c for c in v if c.isdigit())
        if digits in mapping:
            return mapping[digits]
        return None

    @staticmethod
    def _lang_prompt(page: int = 1) -> Outbound:
        page1_rows = [
            ("lang:en", "English"),
            ("lang:ta", "தமிழ்"),
            ("lang:hi", "हिन्दी"),
            ("lang:te", "తెలుగు"),
            ("lang:bn", "বাংলা"),
            ("lang:mr", "मराठी"),
            ("lang:gu", "ગુજરાતી"),
            ("lang:kn", "ಕನ್ನಡ"),
            ("lang:ml", "മലയാളം"),
            ("lang_page:2", "More ➡️"),
        ]
        page2_rows = [
            ("lang:pa", "ਪੰਜਾਬੀ"),
            ("lang:or", "ଓଡ଼ିଆ"),
            ("lang:as", "অসমীয়া"),
            ("lang:ur", "اردو"),
            ("lang:sa", "संस्कृतम्"),
            ("lang:ne", "नेपाली"),
            ("lang:kok", "कोंकणी"),
            ("lang:mai", "मैथिली"),
            ("lang_page:3", "More ➡️"),
            ("lang_page:1", "⬅️ Prev"),
        ]
        page3_rows = [
            ("lang:sd", "سنڌي / सिंधी"),
            ("lang:ks", "کٲشُر / कश्मीरी"),
            ("lang:brx", "बर'"),
            ("lang:doi", "डोगरी"),
            ("lang:mni", "মৈতৈলোন্"),
            ("lang:sat", "ᱥᱟᱱᱛᱟᱲᱤ"),
            ("lang_page:2", "⬅️ Prev"),
        ]

        if page == 2:
            rows = page2_rows
            text = (
                "Choose language (Page 2 of 3) / भाषा सूची:\n\n"
                "10. ਪੰਜਾਬੀ (Punjabi)\n"
                "11. ଓଡ଼ିଆ (Odia)\n"
                "12. অসমীয়া (Assamese)\n"
                "13. اردو (Urdu)\n"
                "14. संस्कृतम् (Sanskrit)\n"
                "15. नेपाली (Nepali)\n"
                "16. कोंकणी (Konkani)\n"
                "17. मैथिली (Maithili)\n\n"
                "Tap 'Select Language' or reply with number (1-23) or name."
            )
        elif page == 3:
            rows = page3_rows
            text = (
                "Choose language (Page 3 of 3) / भाषा सूची:\n\n"
                "18. سنڌي / सिंधी (Sindhi)\n"
                "19. کٲشُر / कश्मीरी (Kashmiri)\n"
                "20. बर' (Bodo)\n"
                "21. डोगरी (Dogri)\n"
                "22. মৈতৈলোন্ (Manipuri)\n"
                "23. ᱥᱟᱱᱛᱟᱲᱤ (Santali)\n\n"
                "Tap 'Select Language' or reply with number (1-23) or name."
            )
        else:
            page = 1
            rows = page1_rows
            text = (
                "Choose your language / अपनी भाषा चुनें / உங்கள் மொழியைத் தேர்ந்தெடுக்கவும்:\n\n"
                "Reply with any language number (1-23), name, or tap 'Select Language':\n\n"
                " 1. English          13. اردو (Urdu)\n"
                " 2. தமிழ் (Tamil)    14. संस्कृतम् (Sanskrit)\n"
                " 3. हिन्दी (Hindi)    15. नेपाली (Nepali)\n"
                " 4. తెలుగు (Telugu)   16. कोंकणी (Konkani)\n"
                " 5. বাংলা (Bengali)   17. मैथिली (Maithili)\n"
                " 6. मराठी (Marathi)   18. سنڌي / सिंधी (Sindhi)\n"
                " 7. ગુજરાતી (Gujarati) 19. کٲشُر / कश्मीरी (Kashmiri)\n"
                " 8. ಕನ್ನಡ (Kannada)   20. बर' (Bodo)\n"
                " 9. മലയാളം (Malayalam) 21. डोगरी (Dogri)\n"
                "10. ਪੰਜਾਬੀ (Punjabi)   22. মৈতৈলোন্ (Manipuri)\n"
                "11. ଓଡ଼ିଆ (Odia)      23. ᱥᱟᱱᱛᱟᱲᱤ (Santali)\n"
                "12. অসমীয়া (Assamese)"
            )

        return Outbound("buttons", text, rows, meta={"type": "list", "button_label": "Select Language", "section_title": f"Languages (Pg {page})"})

    @staticmethod
    def _menu(lang: str) -> Outbound:
        return Outbound("buttons", t(lang, "menu"), [("menu:passport", t(lang, "btn_passport")), ("menu:check", t(lang, "btn_check"))])

    def _reset(self, key: str, conv: dict) -> None:
        self._drop_tmp(key)
        conv["state"], conv["data"] = "MENU", {}

    # ------------------------------------------------------------------ scam checks
    def _try_check(self, msg: Inbound, lang: str, conv: dict, channel: str) -> list[Outbound] | None:
        if msg.kind == "image" and msg.media:
            qr = imaging.decode_qr(msg.media)
            if not qr:
                return None
            body = "QR code content: " + qr
        elif msg.kind in ("text", "button") and (msg.text or "").strip():
            body = msg.text
        else:
            return None
        a = fraud.analyze(body)
        if a["verdict"] == "empty" or (a["verdict"] == "low" and not a["urls"] and not a["upis"]):
            return None
        self.store.log_check(channel, a["verdict"], a["score"], hashlib.sha256(body.encode()).hexdigest())
        return self._scam_reply(a, lang, conv)

    def _scam_reply(self, a: dict, lang: str, conv: dict) -> list[Outbound]:
        v = a["verdict"]
        lines = [t(lang, v), "", f"{t(lang, 'risk')}: {a['score']}/100"]
        if lang == "en":
            reasons = [f["title"] for f in a["findings"] if f["sev"] in ("high", "med")][:3]
            if reasons:
                lines += [f"{t(lang, 'why')}:"] + [f"• {r}" for r in reasons]
        if v in ("danger", "warning"):
            lines += ["", t(lang, "report")]
        out = [_text("\n".join(lines))]
        voice = self.tts.synthesize(t(lang, v), lang)
        if voice:
            out.append(Outbound("audio", media=voice[0], mime=voice[1]))
        if v in ("danger", "warning"):
            trade = conv.get("data", {}).get("last_trade") or "electrical"
            tag = f" ({t(lang, 'sample_tag')})" if "mock" in (self.passports.asr.name, self.passports.vision.name) else ""
            rows = [f"• {title}, {place}{tag}" for title, place, _ in LISTINGS[trade]]
            out.append(_text(t(lang, "route") + "\n" + "\n".join(rows)))
        return out

    # ------------------------------------------------------------------ passport flow
    def _passport_step(self, key: str, conv: dict, msg: Inbound, text: str, low: str) -> list[Outbound]:
        lang, state, data = conv["lang"], conv["state"], conv["data"]

        if state == "NAME":
            name = clean_text(text, 60)
            if msg.kind != "text" or len(name) < 2:
                return [_text(t(lang, "ask_name"))]
            data["name"], conv["state"] = name, "AADHAAR"
            return [Outbound("buttons", t(lang, "ask_aadhaar"), [("aadhaar:skip", t(lang, "btn_skip_aadhaar"))] + self._trade_prompt(lang).buttons)]

        if state == "AADHAAR":
            if msg.button_id == "aadhaar:skip" or low in ("skip", "தவிர்", "छोड़ें", "छोडे", "छोड़े", "none", "no"):
                data["aadhaar"] = None
                conv["state"] = "SECTOR"
                return [self._sector_prompt(lang)]
            trade = self._pick_trade(msg, low, lang)
            if trade and (msg.button_id.startswith("trade:") or low == trade or low in (n.lower() for n in TRADES[trade]["menu"].values())):
                data["trade"], conv["state"] = trade, "HOURS"
                return [_text(t(lang, "ask_hours"))]
            sector = self._pick_sector(msg, low)
            if sector:
                data["sector"], conv["state"] = sector, "TRADE"
                return [self._trade_prompt(lang, sector)]
            if not aadhaar.validate_aadhaar(text):
                return [Outbound("buttons", t(lang, "bad_aadhaar"), [("aadhaar:skip", t(lang, "btn_skip_aadhaar"))])]
            
            clean_num = aadhaar.clean_aadhaar(text)
            masked = aadhaar.mask_aadhaar(clean_num)
            last4 = clean_num[-4:]
            data["aadhaar_pending"] = {
                "masked": masked,
                "sha256": aadhaar.hash_aadhaar(clean_num),
                "last4": last4,
            }
            conv["state"] = "AADHAAR_OTP"
            return [Outbound("buttons", t(lang, "ask_aadhaar_otp", last4=last4), [("aadhaar:skip", t(lang, "btn_skip_aadhaar"))])]

        if state == "AADHAAR_OTP":
            if msg.button_id == "aadhaar:skip" or low in ("skip", "தவிர்", "छोड़ें", "छोडे", "छोड़े", "none", "no"):
                data["aadhaar"] = None
                data.pop("aadhaar_pending", None)
                conv["state"] = "SECTOR"
                return [self._sector_prompt(lang)]
            if aadhaar.verify_aadhaar_otp(text):
                info = data.pop("aadhaar_pending", {})
                info["verified"] = True
                data["aadhaar"] = info
                conv["state"] = "SECTOR"
                return [
                    _text(t(lang, "aadhaar_verified", name=data["name"], masked=info["masked"])),
                    self._sector_prompt(lang),
                ]
            return [Outbound("buttons", t(lang, "bad_otp"), [("aadhaar:skip", t(lang, "btn_skip_aadhaar"))])]

        if state == "SECTOR":
            trade = self._pick_trade(msg, low, lang)
            if trade and (msg.button_id.startswith("trade:") or low == trade or low in (n.lower() for n in TRADES[trade]["menu"].values())):
                data["trade"], conv["state"] = trade, "HOURS"
                return [_text(t(lang, "ask_hours"))]
            sector = self._pick_sector(msg, low)
            if sector:
                data["sector"], conv["state"] = sector, "TRADE"
                return [self._trade_prompt(lang, sector)]
            return [self._sector_prompt(lang)]

        if state == "TRADE":
            if msg.button_id.startswith("sector:") or low in ("back", "sectors", "sector", "துறை", "सेक्टर"):
                conv["state"] = "SECTOR"
                return [self._sector_prompt(lang)]
            trade = self._pick_trade(msg, low, lang, data.get("sector"))
            if not trade:
                return [self._trade_prompt(lang, data.get("sector"))]
            data["trade"], conv["state"] = trade, "HOURS"
            return [_text(t(lang, "ask_hours"))]

        if state == "MENTOR":
            conv["state"] = "HOURS"
            return [_text(t(lang, "ask_hours"))]

        if state == "HOURS":
            digits = "".join(ch for ch in low if ch.isdigit())
            hours = int(digits) if digits and len(digits) <= 3 and low.replace(" ", "").isdigit() else 0
            if not 1 <= hours <= 500:
                return [_text(t(lang, "bad_hours"))]
            data["hours"], conv["state"] = hours, "CONSENT"
            return [Outbound("buttons", t(lang, "consent"), [("consent:yes", t(lang, "btn_yes")), ("consent:no", t(lang, "btn_no"))])]

        if state == "CONSENT":
            if msg.button_id == "consent:yes" or low in YES_WORDS:
                conv["state"] = "PHOTO"
                return [_text(t(lang, "ask_photo"))]
            if msg.button_id == "consent:no" or low in NO_WORDS:
                self._reset(key, conv)
                return [_text(t(lang, "stopped"))]
            return [Outbound("buttons", t(lang, "consent"), [("consent:yes", t(lang, "btn_yes")), ("consent:no", t(lang, "btn_no"))])]

        if state == "PHOTO":
            if msg.kind != "image" or not msg.media:
                return [_text(t(lang, "need_photo"))]
            try:
                assessed = self.passports.assess_photo(msg.media, data["trade"])
            except imaging.ImageRejected as e:
                return [_text(t(lang, "bad_photo", reason=t(lang, f"r_{e.code}")))]
            except ProviderError as e:
                if e.code == "no_work":
                    return [_text(t(lang, "no_work"))]
                log.warning("vision provider failed: %s", e)
                return [_text(t(lang, "error"))]
            (self.tmp_dir / f"{key}.jpg").write_bytes(assessed.jpeg)
            data.update(rubric=assessed.rubric, quality=assessed.quality, vision=assessed.vision_provider)
            conv["state"] = "VIDEO"
            return [Outbound("buttons", t(lang, "ask_video"), [("video:skip", t(lang, "btn_skip_video"))])]

        # VIDEO / VOICE / VIVA
        if state in ("VIDEO", "VOICE", "VIVA"):
            wants_skip = msg.button_id in ("video:skip", "voice:finish", "passport:finish") or low in (
                "skip", "finish", "done", "qr", "தவிர்", "முடித்து", "முடி", "छोड़ें", "छोडे", "छोड़े", "पूरा", "बस", "ok", "okay"
            )
            is_video = msg.kind == "video" and msg.media
            is_audio = msg.kind == "audio" and msg.media
            if not wants_skip and not is_video and not is_audio:
                return [Outbound("buttons", t(lang, "need_video"), [("video:skip", t(lang, "btn_skip_video"))])]
            path = self.tmp_dir / f"{key}.jpg"
            try:
                jpeg = path.read_bytes()
            except OSError:
                conv["state"] = "PHOTO"
                return [_text(t(lang, "ask_photo"))]
            photo = PhotoAssessment(jpeg, data["quality"], data["rubric"], data["vision"])
            video_bytes = msg.media if is_video else None
            audio_bytes = msg.media if is_audio else None
            audio_mime = msg.mime if is_audio else "audio/ogg"
            try:
                rec = self.passports.mint(name=data["name"], trade_id=data["trade"], mentor_name=data.get("mentor", ""),
                                          hours=data["hours"], lang=lang, learner_type="unspecified", photo=photo,
                                          audio=audio_bytes, audio_mime=audio_mime, owner_hash=key,
                                          video=video_bytes,
                                          aadhaar_data=data.get("aadhaar"))
            except ProviderError as e:
                log.warning("mint provider failed: %s", e)
                return [_text(t(lang, "error"))]
            last_trade = data["trade"]
            self._reset(key, conv)
            conv["data"]["last_trade"] = last_trade
            caption = t(lang, "passport_ready", url=rec["verify_url"])
            if rec["assurance"] == "demo":
                caption += "\n\n" + t(lang, "demo_note")
            return [Outbound("image", caption, media=imaging.qr_png(rec["verify_url"]), mime="image/png",
                             meta={"passport": {"id": rec["id"], "signature": rec["signature"], "verify_url": rec["verify_url"]}})]

    # ------------------------------------------------------------------ helpers
    @staticmethod
    def _sector_prompt(lang: str) -> Outbound:
        buttons = [
            (f"sector:{sid}", SECTORS[sid]["menu"].get(lang) or SECTORS[sid]["menu"].get("hi" if lang not in ("en", "ta") else "en", SECTORS[sid]["short"]))
            for sid in SECTOR_ORDER
        ]
        return Outbound("buttons", t(lang, "ask_sector"), buttons)

    @staticmethod
    def _trade_prompt(lang: str, sector: str | None = None) -> Outbound:
        pool = SECTORS[sector]["trades"] if sector and sector in SECTORS else TRADE_ORDER
        buttons = [
            (f"trade:{tid}", TRADES[tid]["menu"].get(lang) or TRADES[tid]["menu"].get("hi" if lang not in ("en", "ta") else "en", TRADES[tid]["short"]))
            for tid in pool
        ]
        return Outbound("buttons", t(lang, "ask_trade"), buttons)

    @staticmethod
    def _pick_sector(msg: Inbound, low: str) -> str | None:
        if msg.button_id.startswith("sector:") and msg.button_id[7:] in SECTORS:
            return msg.button_id[7:]
        if low.isdigit() and 1 <= int(low) <= len(SECTOR_ORDER):
            return SECTOR_ORDER[int(low) - 1]
        for sid, sdata in SECTORS.items():
            if low and (low == sid or low in (n.lower() for n in sdata["menu"].values())):
                return sid
        if any(w in low for w in ("tech", "repair", "பழுது", "मरम्मत", "engineering")):
            return "technical"
        if any(w in low for w in ("craft", "art", "கலை", "கைவினை", "शिल्प", "हस्तकला")):
            return "crafts"
        if any(w in low for w in ("construction", "கட்டுமானம்", "भवन", "निर्माण", "infra")):
            return "construction"
        return None

    @staticmethod
    def _pick_trade(msg: Inbound, low: str, lang: str, sector: str | None = None) -> str | None:
        if msg.button_id.startswith("trade:") and msg.button_id[6:] in TRADES:
            return msg.button_id[6:]
        pool = SECTORS[sector]["trades"] if sector and sector in SECTORS else TRADE_ORDER
        if low.isdigit() and 1 <= int(low) <= len(pool):
            return pool[int(low) - 1]
        for tid, tr in TRADES.items():
            if low and (low == tid or low in (n.lower() for n in tr["menu"].values()) or low == tr["short"].lower()):
                return tid
        return None

    def _drop_tmp(self, key: str) -> None:
        try:
            (self.tmp_dir / f"{key}.jpg").unlink(missing_ok=True)
        except OSError:
            pass

    def purge(self) -> None:
        """Remove abandoned conversations and temp photos older than a day."""
        self.store.purge_stale(days=7)
        cutoff = time.time() - 86400
        for p in Path(self.tmp_dir).glob("*.jpg"):
            try:
                if p.stat().st_mtime < cutoff:
                    p.unlink()
            except OSError:
                pass
