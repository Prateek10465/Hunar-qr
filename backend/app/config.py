"""Settings, read from environment variables (see .env.example)."""
from __future__ import annotations

import os
import secrets
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

_TRUE = {"1", "true", "yes", "on"}


def _bool(env: Mapping[str, str], key: str, default: bool) -> bool:
    v = env.get(key)
    return default if v is None else v.strip().lower() in _TRUE


def _int(env: Mapping[str, str], key: str, default: int) -> int:
    try:
        return int(env[key])
    except (KeyError, ValueError):
        return default


@dataclass(frozen=True)
class Settings:
    # Storage and identity
    data_dir: Path = Path("data")
    public_base_url: str = "http://localhost:8000"
    passport_id_prefix: str = "HQR-TN"
    issuer_did: str = "did:example:hunar-qr-demo-issuer"
    issuer_key_pem: str = ""          # optional: PEM private key (otherwise generated in data_dir)
    hash_secret: str = ""             # optional: HMAC key for hashing phone numbers

    # HTTP surface
    enable_demo_api: bool = True      # web demo endpoints (mint without WhatsApp). Turn off in production.
    cors_origins: tuple[str, ...] = ("*",)
    web_dir: str = ""                 # folder with index.html to serve at /
    trust_proxy: bool = False         # read client IP from X-Forwarded-For
    max_upload_bytes: int = 5_000_000
    rate_analyze_per_min: int = 60
    rate_mint_per_min: int = 10
    rate_chat_per_min: int = 90

    # Providers
    asr_provider: str = "mock"        # mock | http
    asr_url: str = ""
    asr_token: str = ""
    vision_provider: str = "mock"     # mock | claude
    anthropic_api_key: str = ""
    vision_model: str = "claude-sonnet-5-5"
    tts_provider: str = "none"        # none | http
    tts_url: str = ""
    tts_token: str = ""

    # WhatsApp Cloud API
    whatsapp_verify_token: str = ""
    whatsapp_app_secret: str = ""
    whatsapp_access_token: str = ""
    whatsapp_phone_number_id: str = ""
    graph_api_base: str = "https://graph.facebook.com"
    graph_api_version: str = "v21.0"
    allow_unsigned_webhook: bool = False

    @property
    def whatsapp_configured(self) -> bool:
        return bool(self.whatsapp_access_token and self.whatsapp_phone_number_id)

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> "Settings":
        e = os.environ if env is None else env
        d = cls()
        origins = tuple(o.strip() for o in e.get("CORS_ORIGINS", "*").split(",") if o.strip()) or ("*",)
        return cls(
            data_dir=Path(e.get("DATA_DIR", str(d.data_dir))),
            public_base_url=e.get("PUBLIC_BASE_URL", d.public_base_url).rstrip("/"),
            passport_id_prefix=e.get("PASSPORT_ID_PREFIX", d.passport_id_prefix),
            issuer_did=e.get("ISSUER_DID", d.issuer_did),
            issuer_key_pem=e.get("ISSUER_KEY_PEM", ""),
            hash_secret=e.get("HASH_SECRET", ""),
            enable_demo_api=_bool(e, "ENABLE_DEMO_API", d.enable_demo_api),
            cors_origins=origins,
            web_dir=e.get("WEB_DIR") or next((str(c) for c in (Path("../web"), Path("web"), Path(__file__).resolve().parent.parent.parent / "web") if (c / "index.html").is_file()), ""),
            trust_proxy=_bool(e, "TRUST_PROXY", False),
            max_upload_bytes=_int(e, "MAX_UPLOAD_BYTES", d.max_upload_bytes),
            rate_analyze_per_min=_int(e, "RATE_ANALYZE_PER_MIN", d.rate_analyze_per_min),
            rate_mint_per_min=_int(e, "RATE_MINT_PER_MIN", d.rate_mint_per_min),
            rate_chat_per_min=_int(e, "RATE_CHAT_PER_MIN", d.rate_chat_per_min),
            asr_provider=e.get("ASR_PROVIDER", d.asr_provider).lower(),
            asr_url=e.get("ASR_URL", ""),
            asr_token=e.get("ASR_TOKEN", ""),
            vision_provider=e.get("VISION_PROVIDER", d.vision_provider).lower(),
            anthropic_api_key=e.get("ANTHROPIC_API_KEY", ""),
            vision_model=e.get("VISION_MODEL", d.vision_model),
            tts_provider=e.get("TTS_PROVIDER", d.tts_provider).lower(),
            tts_url=e.get("TTS_URL", ""),
            tts_token=e.get("TTS_TOKEN", ""),
            whatsapp_verify_token=e.get("WHATSAPP_VERIFY_TOKEN", ""),
            whatsapp_app_secret=e.get("WHATSAPP_APP_SECRET", ""),
            whatsapp_access_token=e.get("WHATSAPP_ACCESS_TOKEN", ""),
            whatsapp_phone_number_id=e.get("WHATSAPP_PHONE_NUMBER_ID", ""),
            graph_api_base=e.get("GRAPH_API_BASE", d.graph_api_base).rstrip("/"),
            graph_api_version=e.get("GRAPH_API_VERSION", d.graph_api_version),
            allow_unsigned_webhook=_bool(e, "ALLOW_UNSIGNED_WEBHOOK", False),
        )


def load_or_create_secret(path: Path) -> str:
    """Random server-side secret kept in the data dir (used to hash phone numbers)."""
    if path.exists():
        return path.read_text().strip()
    value = secrets.token_hex(32)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as f:
        f.write(value)
    return value
