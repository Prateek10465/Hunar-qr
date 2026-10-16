import sys
from dataclasses import replace
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.bot import Bot                      # noqa: E402
from app.config import Settings              # noqa: E402
from app.credentials import Issuer           # noqa: E402
from app.main import create_app              # noqa: E402
from app.passports import PassportService    # noqa: E402
from app.providers import MockASR, MockVision, NullTTS  # noqa: E402
from app.store import Store                  # noqa: E402
from app.whatsapp import WhatsAppClient      # noqa: E402

PHONE = "919876543210"


@pytest.fixture
def settings(tmp_path):
    return Settings(data_dir=tmp_path / "data", public_base_url="http://testserver",
                    rate_analyze_per_min=0, rate_mint_per_min=0, rate_chat_per_min=0,
                    whatsapp_verify_token="verify-me", whatsapp_app_secret="appsecret",
                    whatsapp_access_token="TOKEN", whatsapp_phone_number_id="123", hash_secret="test-secret")


class WAMock:
    """Records every request the WhatsApp client makes and answers like the Graph API."""

    def __init__(self):
        self.requests: list[httpx.Request] = []
        self.media: dict[str, tuple[bytes, str]] = {}     # media id -> (bytes, mime)
        self.fail_messages = False

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        path = request.url.path
        if request.method == "POST" and path.endswith("/messages"):
            return httpx.Response(500, json={"error": "boom"}) if self.fail_messages else httpx.Response(200, json={"messages": [{"id": "wamid.OUT"}]})
        if request.method == "POST" and path.endswith("/media"):
            return httpx.Response(200, json={"id": "MEDIA-OUT"})
        if request.url.host == "lookaside.example":
            data, _ = self.media[path.rsplit("/", 1)[1]]
            return httpx.Response(200, content=data)
        if request.method == "GET":
            mid = path.rsplit("/", 1)[1]
            return httpx.Response(200, json={"url": f"https://lookaside.example/m/{mid}", "mime_type": self.media[mid][1]})
        return httpx.Response(404)

    def sent(self) -> list[dict]:
        import json
        return [json.loads(r.content) for r in self.requests if r.method == "POST" and r.url.path.endswith("/messages")]


@pytest.fixture
def wa_mock():
    return WAMock()


@pytest.fixture
def client(settings, wa_mock):
    wa = WhatsAppClient(settings, httpx.Client(transport=httpx.MockTransport(wa_mock.handler)))
    app = create_app(settings, wa_client=wa)
    with TestClient(app) as c:
        c.app_state = app.state
        yield c


@pytest.fixture
def make_app(settings):
    def _make(**over):
        return TestClient(create_app(replace(settings, **over)))
    return _make


class Chat:
    """Drives a Bot like one WhatsApp user."""

    def __init__(self, bot: Bot, key="user-1", channel="web"):
        from app.bot import Inbound
        self.bot, self.key, self.channel, self.Inbound = bot, key, channel, Inbound

    def say(self, text="", *, button="", image=None, audio=None):
        if image is not None:
            m = self.Inbound("image", media=image, mime="image/png")
        elif audio is not None:
            m = self.Inbound("audio", media=audio, mime="audio/ogg")
        elif button:
            m = self.Inbound("button", text=text, button_id=button)
        else:
            m = self.Inbound("text", text=text)
        return self.bot.handle(self.key, m, channel=self.channel)

    @property
    def state(self):
        return (self.bot.store.get_conversation(self.key) or {}).get("state")


def build_bot(settings, *, asr=None, vision=None, tts=None):
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    store = Store(settings.data_dir / "hunar.db")
    issuer = Issuer.load_or_create(key_pem="", key_path=settings.data_dir / "issuer_key.pem", did=settings.issuer_did)
    svc = PassportService(settings, store, issuer, asr or MockASR(), vision or MockVision())
    return Bot(settings, store, svc, tts or NullTTS())


@pytest.fixture
def bot(settings):
    return build_bot(settings)


@pytest.fixture
def chat(bot):
    return Chat(bot)


def all_text(out) -> str:
    return "\n".join(o.text for o in out)
