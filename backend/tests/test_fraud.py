import pytest

from app import fraud

UPI = "upi://pay?pa=pmkaushal.fee@okdemo&pn=PM%20Kaushal%20Fee&am=99&cu=INR&tn=Processing%20fee"

SAMPLES = [
    ("PM Kaushal Yojana ₹5,000 Grant: Click bit.ly/pm-kaushal-claim or scan this UPI QR to pay ₹99 processing fee.\nUPI QR content: " + UPI, "danger", 100),
    ("Congratulations! You are selected for a factory job, salary ₹18,000. Download your offer letter: http://tn-jobs-offer.xyz/offer-letter.apk and pay ₹499 verification fee within 2 hours to confirm joining.", "danger", 100),
    ("Last date today! Apply for the PM scholarship at https://scholarships-gov.in.apply-now.top/login and enter your Aadhaar number and OTP.", "danger", 95),
    ("Apprenticeship openings for electricians. Details and application form: https://jobs-chengalpattu.com/apply", "low", 10),
    ("Check your scholarship application status at https://scholarships.gov.in", "safe", 0),
]


@pytest.mark.parametrize("text,verdict,score", SAMPLES)
def test_sample_messages(text, verdict, score):
    a = fraud.analyze(text)
    assert (a["verdict"], a["score"]) == (verdict, score)


def titles(text):
    return [f["title"] for f in fraud.analyze(text)["findings"]]


def test_empty_and_chitchat():
    assert fraud.analyze("")["verdict"] == "empty"
    assert fraud.analyze("   ")["verdict"] == "empty"
    assert fraud.analyze("thanks, see you tomorrow")["verdict"] == "empty"


def test_shortener_and_scheme_name():
    t = titles("claim at https://bit.ly/pm-kaushal-grant")
    assert "Shortened link" in t and "Short link names a scheme" in t


def test_apk_download():
    assert "App file (.apk)" in titles("get it at https://files.example.com/job.apk?v=2")


def test_fake_gov_look_alike():
    a = fraud.analyze("https://scholarships.gov.in.evil-site.com/login")
    assert "Fake-looking .gov.in address" in [f["title"] for f in a["findings"]]
    assert a["verdict"] == "danger" or a["score"] >= 40


def test_real_gov_domain_is_not_flagged_as_fake():
    a = fraud.analyze("see https://scholarships.gov.in/apply")
    assert a["verdict"] == "safe" and a["urls"][0]["flagged"] is False
    sub = fraud.analyze("see https://login.digilocker.gov.in/x")
    assert sub["hasOfficial"] is True


def test_unlisted_gov_in_is_not_called_safe():
    a = fraud.analyze("https://example.nic.in/portal")
    assert a["verdict"] == "low" and a["unknown"] is True


def test_raw_ip_and_unusual_tld():
    t = titles("login at http://192.168.1.10/pay or https://claim-now.top/x")
    assert "Raw IP address" in t and "Unusual website ending (.top)" in t


def test_lookalike_characters():
    assert "Look-alike characters" in titles("https://аpple-support.com/login")   # Cyrillic a


def test_upi_collect_and_fee():
    a = fraud.analyze("approve: upi://collect?pa=abc@ybl&pn=Skill%20Grant&am=500&cu=INR")
    t = [f["title"] for f in a["findings"]]
    assert "UPI collect request" in t and "Fixed payment of ₹500" in t
    assert a["upis"][0]["pa"] == "abc@ybl" and a["upis"][0]["am"] == 500


def test_government_name_on_personal_upi_id():
    t = titles("upi://pay?pa=pm.kisan@oksbi&pn=PM%20Kisan&am=10.5")
    assert "Government name on a personal-style UPI ID" in t
    assert "Fixed payment of ₹10.5" in t


def test_blocklisted_payee():
    assert "UPI ID on the sample blocklist" in titles(UPI)


def test_fee_wording_without_links():
    a = fraud.analyze("Pay Rs. 250 registration fee to confirm your seat")
    assert a["verdict"] == "warning" and "Asks for money as a fee" in [f["title"] for f in a["findings"]]


def test_otp_request_needs_both_words():
    assert "Asks for OTP or PIN" in titles("please share your OTP to get the grant")
    assert "Asks for OTP or PIN" not in titles("your OTP is 123456")


def test_pressure_and_lure_alone_are_low_not_danger():
    a = fraud.analyze("Congratulations! Hurry, limited seats")
    assert a["verdict"] == "low" and a["urls"] == [] and a["upis"] == []


def test_email_address_is_not_a_link():
    assert fraud.analyze("write to user@gmail.com")["urls"] == []


def test_extract_dedupes_and_strips_punctuation():
    urls, upis = fraud.extract("go to https://a.example.com/x. Then https://a.example.com/x, or " + UPI + ".")
    assert urls == ["https://a.example.com/x"] and upis == [UPI]


def test_score_is_capped_and_findings_sorted():
    a = fraud.analyze(SAMPLES[0][0])
    assert a["score"] == 100
    ranks = [fraud.SEV_RANK[f["sev"]] for f in a["findings"]]
    assert ranks == sorted(ranks)


def test_non_string_and_none():
    assert fraud.analyze(None)["verdict"] == "empty"
