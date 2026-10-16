import base64
import json

import httpx
import pytest

from app.config import Settings
from app.data import TRADES
from app.providers import (ClaudeVision, HttpASR, HttpTTS, MockASR, MockVision, NullTTS, ProviderError,
                           build_asr, build_tts, build_vision, clean_text)


def client(handler):
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_mock_asr_returns_sample_in_requested_language():
    t = MockASR().transcribe(b"x", "audio/ogg", "ta", "electrical")
    assert t.text == TRADES["electrical"]["say"]["ta"] and t.english == TRADES["electrical"]["say"]["en"]
    assert t.provider == "mock" and t.liveness == "not_checked"
    assert MockASR().transcribe(b"x", "", "zz", "solar").language == "en"


def test_mock_vision_matches_rubric():
    r = MockVision().assess(b"x", "tailoring")
    assert [x["item"] for x in r.rubric] == [i for i, _, _ in TRADES["tailoring"]["rubric"]] and r.provider == "mock"


# ---- HTTP ASR
def test_http_asr_success():
    seen = {}

    def h(req: httpx.Request):
        seen["auth"] = req.headers.get("authorization")
        seen["ct"] = req.headers["content-type"]
        seen["body"] = req.content
        return httpx.Response(200, json={"text": "  வணக்கம் ", "english": "Hello", "language": "ta", "liveness": "passed"})

    t = HttpASR("http://asr.test/x", token="T", client=client(h)).transcribe(b"AUDIOBYTES", "audio/ogg", "ta", "solar")
    assert (t.text, t.english, t.language, t.liveness) == ("வணக்கம்", "Hello", "ta", "passed")
    assert seen["auth"] == "Bearer T" and seen["ct"].startswith("multipart/form-data") and b"AUDIOBYTES" in seen["body"]


@pytest.mark.parametrize("resp", [httpx.Response(500), httpx.Response(200, text="not json"), httpx.Response(200, json={"text": ""}),
                                  httpx.Response(200, json=["list"])])
def test_http_asr_failures_become_provider_errors(resp):
    with pytest.raises(ProviderError):
        HttpASR("http://asr.test/x", client=client(lambda r: resp)).transcribe(b"a", "audio/ogg", "en", "solar")


def test_http_asr_ignores_bad_optional_fields():
    t = HttpASR("http://asr.test/x", client=client(lambda r: httpx.Response(200, json={"text": "ok", "language": "xx", "liveness": "maybe"}))).transcribe(b"a", "", "hi", "solar")
    assert t.language == "hi" and t.liveness == "not_checked" and t.english is None


# ---- Claude vision
def vision_reply(scores, shows=True, wrap=""):
    body = json.dumps({"shows_trade_work": shows, "scores": scores})
    return httpx.Response(200, json={"content": [{"type": "text", "text": wrap + body + wrap}]})


def test_claude_vision_happy_path_and_request_shape():
    seen = {}

    def h(req: httpx.Request):
        seen["headers"], seen["body"] = req.headers, json.loads(req.content)
        return vision_reply([{"score": 91.4, "note": "neat"}, {"score": 120, "note": None}, {"score": -5}, {"score": "70"}, {"score": 55, "note": "<b>x</b>\n" * 100}], wrap="```json\n")

    v = ClaudeVision("KEY", "model-x", client=client(h))
    res = v.assess(b"\xff\xd8JPEG", "electrical")
    assert [r["score"] for r in res.rubric] == [91, 100, 0, 70, 55]
    assert res.provider == "claude" and res.rubric[0]["note"] == "neat"
    assert len(res.rubric[4]["note"]) <= 120
    assert [r["item"] for r in res.rubric] == [i for i, _, _ in TRADES["electrical"]["rubric"]]   # our names, not the model's
    assert seen["headers"]["x-api-key"] == "KEY" and seen["headers"]["anthropic-version"] == "2023-06-01"
    b = seen["body"]
    assert b["model"] == "model-x"
    img = b["messages"][0]["content"][0]
    assert img["type"] == "image" and base64.b64decode(img["source"]["data"]) == b"\xff\xd8JPEG"
    prompt = b["messages"][0]["content"][1]["text"]
    assert "untrusted" in prompt and "Safe isolation" in prompt


def test_claude_vision_photo_without_trade_work():
    v = ClaudeVision("K", "m", client=client(lambda r: vision_reply([{"score": 5}] * 5, shows=False)))
    with pytest.raises(ProviderError) as e:
        v.assess(b"x", "electrical")
    assert e.value.code == "no_work"


@pytest.mark.parametrize("resp", [
    httpx.Response(401, json={"error": "bad key"}),
    httpx.Response(200, json={"content": [{"type": "text", "text": "I cannot help"}]}),
    vision_reply([{"score": 1}] * 3),                       # wrong number of items
    vision_reply([{"score": "high"}] * 5),                   # not a number
    httpx.Response(200, json={"content": [{"type": "text", "text": "{not json}"}]}),
])
def test_claude_vision_bad_replies_fail_loudly(resp):
    with pytest.raises(ProviderError):
        ClaudeVision("K", "m", client=client(lambda r: resp)).assess(b"x", "electrical")


# ---- TTS
def test_tts_providers():
    assert NullTTS().synthesize("x", "en") is None
    ok = HttpTTS("http://tts.test", client=client(lambda r: httpx.Response(200, content=b"OGG", headers={"content-type": "audio/ogg; codecs=opus"})))
    assert ok.synthesize("hello", "ta") == (b"OGG", "audio/ogg")
    down = HttpTTS("http://tts.test", client=client(lambda r: httpx.Response(503)))
    assert down.synthesize("hello", "ta") is None     # a missing voice note must not block the text warning


# ---- factories
def test_factories(tmp_path):
    s = Settings(data_dir=tmp_path)
    assert build_asr(s).name == "mock" and build_vision(s).name == "mock" and build_tts(s).name == "none"
    with pytest.raises(ValueError):
        build_asr(Settings(asr_provider="http"))
    with pytest.raises(ValueError):
        build_vision(Settings(vision_provider="claude"))
    with pytest.raises(ValueError):
        build_tts(Settings(tts_provider="http"))
    with pytest.raises(ValueError):
        build_vision(Settings(vision_provider="nope"))
    assert build_vision(Settings(vision_provider="claude", anthropic_api_key="k")).name == "claude"


def test_clean_text():
    assert clean_text("  a\n\tb\x00c  ", 10) == "a b c"
    assert clean_text("x" * 50, 5) == "xxxxx" and clean_text(None, 5) == ""
