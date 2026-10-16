import cv2
import numpy as np
import pytest

from app import imaging
from app.data import TRADES
from app.providers import MockASR, MockVision, ProviderError, Transcript, VisionResult

from conftest import Chat, all_text, build_bot

UPI = "upi://pay?pa=pmkaushal.fee@okdemo&pn=PM%20Kaushal%20Fee&am=99&cu=INR&tn=Processing%20fee"
SCAM = "PM Kaushal Yojana grant: pay ₹99 processing fee at bit.ly/pm-kaushal-claim"
PHOTO = imaging.sample_image("electrical")


def start(chat, lang="en"):
    chat.say("hello")
    chat.say(button=f"lang:{lang}")


def fill_until_photo(chat, lang="en", name="Karthik M.", hours="12"):
    start(chat, lang)
    chat.say(button="menu:passport")
    chat.say(name)
    chat.say(button="trade:electrical")
    chat.say(hours)
    out = chat.say(button="consent:yes")
    assert chat.state == "PHOTO"
    return out


def passports(bot):
    return bot.store.stats()["passports_issued"]


# ------------------------------------------------------------------ language and menu
def test_new_user_gets_language_buttons_then_menu(chat):
    out = chat.say("hello")
    assert out[0].kind == "buttons" and [b[0] for b in out[0].buttons] == ["lang:en", "lang:ta", "lang:hi"]
    out = chat.say(button="lang:ta")
    assert out[0].kind == "buttons" and "ஹுனர்" in out[0].text and chat.state == "MENU"
    assert [b[0] for b in out[0].buttons] == ["menu:passport", "menu:check"]


def test_language_can_be_chosen_by_typing(chat):
    chat.say("hi")
    assert "हुनर" in chat.say("3")[0].text


def test_greeting_returns_to_menu_and_menu_option_two(chat):
    start(chat)
    assert "Skill Passport" in chat.say("menu")[0].text
    assert "Forward me" in chat.say("2")[0].text
    assert chat.say("thanks!")[0].kind == "buttons"      # chit-chat just shows the menu


# ------------------------------------------------------------------ passport flow
def test_full_passport_flow_in_english(chat, bot, settings):
    fill_until_photo(chat)
    out = chat.say(image=PHOTO)
    assert chat.state == "VOICE" and "voice note" in out[0].text
    assert (settings.data_dir / "tmp" / f"{chat.key}.jpg").exists()
    out = chat.say(audio=b"voice-bytes")
    assert len(out) == 1 and out[0].kind == "image" and out[0].media[:4] == b"\x89PNG"
    assert "Verify link: http://testserver/v/HQR-TN-" in out[0].text and "DEMO credential" in out[0].text
    assert imaging.decode_qr(out[0].media) == out[0].meta["passport"]["verify_url"]
    assert passports(bot) == 1 and chat.state == "MENU"
    assert not (settings.data_dir / "tmp" / f"{chat.key}.jpg").exists()      # temp photo removed
    rec = bot.store.get_passport(out[0].meta["passport"]["id"])
    s = rec["credential"]["credentialSubject"]
    assert (s["name"], s["practicalHours"], s["tradeId"]) == ("Karthik M.", 12, "electrical")
    assert s["verification"]["type"] == "bharat-proof-of-skill"
    assert rec["owner_hash"] == chat.key


def test_full_passport_flow_in_tamil_uses_tamil_endorsement(chat, bot):
    fill_until_photo(chat, lang="ta")
    chat.say(image=PHOTO)
    out = chat.say(audio=b"v")
    assert "திறன் பாஸ்போர்ட்" in out[0].text
    cred = bot.store.get_passport(out[0].meta["passport"]["id"])["credential"]
    assert cred["credentialSubject"]["verification"]["type"] == "bharat-proof-of-skill"


def test_trade_can_be_picked_by_number_or_name(chat):
    start(chat)
    chat.say("1")
    chat.say("Anitha")
    assert "hours" in chat.say("tailoring")[0].text.lower() and chat.state == "HOURS"
    chat2 = Chat(chat.bot, key="user-2")
    chat2.say("hi"), chat2.say("1"), chat2.say("1"), chat2.say("Vignesh")
    # Step 1: select sector by number (1 = Tech & Repairs)
    assert chat2.say("1")[0].kind == "buttons"
    # Step 2: select trade by number from subcategory (1 = Electrical)
    assert "hours" in chat2.say("1")[0].text.lower() and chat2.state == "HOURS"


def test_sector_to_subtrade_dynamic_flow(chat):
    start(chat)
    chat.say("1")
    chat.say("Ramesh")
    sec_prompt = chat.say(button="aadhaar:skip")[0]
    assert [b[0] for b in sec_prompt.buttons] == ["sector:technical", "sector:crafts", "sector:construction"]
    # Select Sector 1: Tech & Repairs
    out = chat.say(button="sector:technical")
    assert out[0].kind == "buttons"
    assert [b[0] for b in out[0].buttons] == ["trade:electrical", "trade:plumbing", "trade:hvac", "trade:automobile", "trade:solar"]
    # Select Sub-trade: Plumbing
    out = chat.say(button="trade:plumbing")
    assert "hours" in out[0].text.lower() and chat.state == "HOURS"



def test_name_and_trade_are_re_asked_when_invalid(chat):
    start(chat)
    chat.say("1")
    assert chat.say("A")[0].text == "What is the learner's name?"
    chat.say("Karthik")
    assert chat.say("9")[0].kind == "buttons"           # trade prompt again


@pytest.mark.parametrize("bad", ["abc", "0", "501", "-5", "12.5 hours", "1" * 9])
def test_hours_validation(chat, bad):
    start(chat)
    for step in ("1",):
        chat.say(step)
    chat.say("Karthik"), chat.say(button="trade:electrical")
    assert chat.say(bad)[0].text == "Please send a number between 1 and 500." and chat.state == "HOURS"
    assert chat.say("40")[0].kind == "buttons" and chat.state == "CONSENT"


def test_consent_no_stops_the_flow(chat, bot):
    start(chat)
    chat.say("1"), chat.say("Karthik"), chat.say(button="trade:electrical"), chat.say("12")
    assert chat.say("maybe")[0].kind == "buttons"          # asks again
    out = chat.say(button="consent:no")
    assert "Stopped" in out[0].text and chat.state == "MENU" and passports(bot) == 0


def test_yes_in_tamil_and_hindi_words(chat):
    start(chat, "hi")
    chat.say("1"), chat.say("Karthik"), chat.say(button="trade:solar"), chat.say("गुरु जी"), chat.say("20")
    chat.say("हाँ")
    assert chat.state == "PHOTO"


def test_cancel_in_the_middle(chat, bot, settings):
    fill_until_photo(chat)
    chat.say(image=PHOTO)
    out = chat.say("cancel")
    assert "Stopped" in out[0].text and chat.state == "MENU"
    assert not (settings.data_dir / "tmp" / f"{chat.key}.jpg").exists() and passports(bot) == 0


def test_text_where_a_photo_is_expected(chat):
    fill_until_photo(chat)
    assert chat.say("here it is")[0].text == "Please send a photo." and chat.state == "PHOTO"


def test_blurry_dark_and_fake_photos_are_refused_with_a_reason(chat):
    fill_until_photo(chat)
    img = cv2.imdecode(np.frombuffer(PHOTO, np.uint8), 1)
    blurry = cv2.imencode(".png", cv2.GaussianBlur(img, (0, 0), 6))[1].tobytes()
    dark = cv2.imencode(".png", (img * 0.1).astype(np.uint8))[1].tobytes()
    assert "it is blurry" in chat.say(image=blurry)[0].text
    assert "it is too dark" in chat.say(image=dark)[0].text
    assert "not an image I can read" in chat.say(image=b"junk")[0].text
    assert chat.state == "PHOTO"


def test_photo_reasons_are_translated(chat):
    fill_until_photo(chat, "hi")
    assert "धुंधली है" in chat.say(image=cv2.imencode(".png", cv2.GaussianBlur(cv2.imdecode(np.frombuffer(PHOTO, np.uint8), 1), (0, 0), 6))[1].tobytes())[0].text


def test_audio_where_a_photo_is_expected_and_photo_where_audio_is_expected(chat):
    fill_until_photo(chat)
    assert chat.say(audio=b"v")[0].text == "Please send a photo."
    chat.say(image=PHOTO)
    assert chat.say(image=PHOTO)[0].text == "Please send a voice note."


class FailingVision:
    name = "claude"

    def __init__(self, err):
        self.err = err

    def assess(self, jpeg, trade_id):
        raise self.err


def test_vision_failure_keeps_the_user_in_place(settings):
    bot = build_bot(settings, vision=FailingVision(ProviderError("down")))
    chat = Chat(bot)
    fill_until_photo(chat)
    assert "Something went wrong" in chat.say(image=PHOTO)[0].text and chat.state == "PHOTO"


def test_photo_without_trade_work(settings):
    bot = build_bot(settings, vision=FailingVision(ProviderError("no", code="no_work")))
    chat = Chat(bot)
    fill_until_photo(chat)
    assert "could not see the trade work" in chat.say(image=PHOTO)[0].text and chat.state == "PHOTO"


class FailingASR:
    name = "http"

    def transcribe(self, *a):
        raise ProviderError("asr down")


def test_speech_failure_lets_the_mentor_resend(settings):
    bot = build_bot(settings, asr=FailingASR())
    chat = Chat(bot)
    fill_until_photo(chat)
    chat.say(image=PHOTO)
    assert "Something went wrong" in chat.say(audio=b"v")[0].text
    assert chat.state == "VOICE" and (settings.data_dir / "tmp" / f"{chat.key}.jpg").exists() and passports(bot) == 0


class LiveASR:
    name = "http"

    def transcribe(self, audio, mime, lang, trade):
        return Transcript("mentor says well done", "mentor says well done", "en", "http", "passed")


def test_live_providers_give_ai_assisted_not_demo(settings):
    class LiveVision(MockVision):
        name = "claude"
    bot = build_bot(settings, asr=LiveASR(), vision=LiveVision())
    chat = Chat(bot)
    fill_until_photo(chat)
    chat.say(image=PHOTO)
    out = chat.say(audio=b"v")
    assert "DEMO" not in out[0].text
    cred = bot.store.get_passport(out[0].meta["passport"]["id"])["credential"]
    assert cred["assurance"]["level"] == "ai-assisted" and cred["credentialSubject"]["mentor"]["liveness"] == "passed"


def test_conversation_state_survives_a_restart(chat, settings):
    fill_until_photo(chat)
    again = Chat(build_bot(settings), key=chat.key)
    assert again.state == "PHOTO"
    assert "voice note" in again.say(image=PHOTO)[0].text


def test_users_do_not_share_state(bot):
    a, b = Chat(bot, "a"), Chat(bot, "b")
    fill_until_photo(a)
    assert b.say("hello")[0].kind == "buttons" and b.state == "LANG" and a.state == "PHOTO"


# ------------------------------------------------------------------ scam checks
def test_forwarded_scam_in_english(chat):
    start(chat)
    out = chat.say(SCAM)
    text = all_text(out)
    assert "Danger" in text and "Risk score: " in text and "• Asks for money as a fee" in text and "• Shortened link" in text
    assert "cybercrime.gov.in" in text and "1930" in text
    assert "zero-fee openings" in text and "sample listing" in text


@pytest.mark.parametrize("lang,word", [("ta", "ஆபத்து"), ("hi", "ख़तरा")])
def test_forwarded_scam_in_tamil_and_hindi(chat, lang, word):
    start(chat, lang)
    text = all_text(chat.say(SCAM))
    assert word in text and "• " not in text.split("1930")[0] and "1930" in text


def test_safe_link_gets_no_listings(chat):
    start(chat)
    out = chat.say("status: https://scholarships.gov.in")
    assert "verified government website" in out[0].text and len(out) == 1


def test_qr_image_with_a_scam_payment(chat):
    start(chat)
    out = chat.say(image=imaging.qr_png(UPI))
    assert "Danger" in out[0].text


def test_image_without_qr_in_menu(chat):
    start(chat)
    out = chat.say(image=imaging.sample_image("solar"))
    assert "could not find a QR code" in out[0].text and out[1].kind == "buttons"


def test_scam_forward_as_first_message(chat):
    out = chat.say(SCAM)
    assert "Danger" in out[0].text and out[-1].kind == "buttons" and out[-1].buttons[0][0] == "lang:en"
    assert chat.state == "LANG"


def test_checks_are_counted_by_channel_and_verdict(chat, bot):
    start(chat)
    chat.say(SCAM)
    chat.say("status: https://scholarships.gov.in")
    s = bot.store.stats()
    assert s["messages_checked"] == 2 and s["checks_by_verdict"] == {"danger": 1, "safe": 1}


def test_listings_follow_the_last_trade_the_user_picked(chat):
    fill_until_photo(chat)
    chat.say(image=PHOTO)
    chat.say(audio=b"v")
    text = all_text(chat.say(SCAM))
    assert "wireman" in text.lower() or "electrician" in text.lower()


class FakeTTS:
    name = "fake"

    def synthesize(self, text, lang):
        return b"OGGDATA", "audio/ogg"


def test_voice_warning_is_sent_when_tts_is_available(settings):
    chat = Chat(build_bot(settings, tts=FakeTTS()))
    start(chat)
    out = chat.say(SCAM)
    assert [o.kind for o in out][:2] == ["text", "audio"] and out[1].media == b"OGGDATA"


def test_bot_never_goes_silent_on_internal_errors(settings, monkeypatch):
    bot = build_bot(settings)
    chat = Chat(bot)
    start(chat)
    monkeypatch.setattr("app.bot.fraud.analyze", lambda t: 1 / 0)
    out = chat.say(SCAM)
    assert "Something went wrong" in out[0].text


def test_bharat_pos_verification_flow_with_dynamic_challenge_token_and_viva(chat, bot):
    start(chat)
    chat.say("1")
    chat.say("Suresh Kumar")
    chat.say(button="trade:plumbing")
    chat.say("45")    # Directly asks hours (learning-by-doing, no mentor)
    out = chat.say(button="consent:yes")
    # Step 1: dynamic token check
    assert "token #" in out[0].text.lower()
    token = "".join(ch for ch in out[0].text if ch.isdigit())
    assert len(token) == 3
    # Step 2: photo upload generates practical troubleshooting viva question
    out = chat.say(image=PHOTO)
    assert "viva" in out[0].text.lower() and ("suction" in out[0].text.lower() or "pump" in out[0].text.lower())
    # Step 3: worker answers oral viva with troubleshooting voice note
    out = chat.say(audio=b"plumber-troubleshooting-voice")
    assert "Verify link:" in out[0].text
    rec = bot.store.get_passport(out[0].meta["passport"]["id"])
    ver = rec["credential"]["credentialSubject"]["verification"]
    assert ver["type"] == "bharat-proof-of-skill"
    assert ver["challengeToken"] == token
    assert "pump" in ver["viva"]["question"].lower() or "suction" in ver["viva"]["question"].lower()
    assert ver["trustAnchor"]["verified"] is True


def test_trade_directly_asks_hours_without_mentor(chat):
    start(chat)
    chat.say("1")
    chat.say("Priya R.")
    out = chat.say(button="trade:tailoring")
    assert "hours" in out[0].text.lower() and chat.state == "HOURS"
    out = chat.say("30")
    assert out[0].kind == "buttons" and "consent" in out[0].buttons[0][0]


def test_bot_aadhaar_verification_with_otp(chat, bot):
    start(chat)
    chat.say("1")
    out = chat.say("Manoj Kumar")
    assert "aadhaar" in out[0].text.lower() and chat.state == "AADHAAR"
    
    # Enter valid Aadhaar number (e.g. 984256123414)
    out = chat.say("9842 5612 3414")
    assert "otp" in out[0].text.lower() and chat.state == "AADHAAR_OTP"
    
    # Enter demo OTP
    out = chat.say("123456")
    assert len(out) == 2
    assert "verified" in out[0].text.lower() and "3414" in out[0].text
    assert out[1].kind == "buttons" and chat.state == "SECTOR"


def test_bot_aadhaar_invalid_checksum_and_skip(chat):
    start(chat)
    chat.say("1")
    chat.say("Kavitha S.")
    # Enter invalid Aadhaar number with bad checksum
    out = chat.say("9842 5612 3419")
    assert "checksum" in out[0].text.lower() and chat.state == "AADHAAR"
    
    # User skips
    out = chat.say(button="aadhaar:skip")
    assert out[0].kind == "buttons" and chat.state == "SECTOR"

