"""The browser engine and the Python engine must agree. Skipped when node or web/index.html is missing."""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

from app import fraud
from test_fraud import SAMPLES, UPI

ROOT = Path(__file__).resolve().parents[2]
INDEX = ROOT / "web" / "index.html"

CORPUS = [s[0] for s in SAMPLES] + [
    "",
    "hello, how are you?",
    "Join now: www.skillindia-gov.com/register pay Rs. 250 registration fee",
    "Visit http://192.168.1.10/login for details",
    "https://аpple-support.com/login",
    "upi://collect?pa=abc@ybl&pn=Skill%20Grant&am=500&cu=INR",
    "please share your OTP to get the scholarship",
    "Check https://digilocker.gov.in and https://tinyurl.com/abc",
    "Email me at user@gmail.com",
    "Apply at nsdcindia.org/apply",
    "https://scholarships.gov.in.evil.com/x",
    "Congratulations you have been selected! Grant of ₹10000. Pay ₹100 processing fee. Urgent, expires within 2 hours.",
    "Visit https://example.nic.in/portal",
    "https://bit.ly/3abc?x=1",
    "download http://x.com/app.apk?v=2",
    "upi://pay?pa=pm.kisan@oksbi&pn=PM%20Kisan&am=10.5",
    "இந்த இணைப்பை பாருங்கள் https://jobs.xyz/a வேலை",
    "Hurry! limited seats https://jobs-tn.online/apply",
    "Pay ₹499 joining fee. " + UPI,
    "https://skillindiadigital.gov.in/home and https://scholarships.gov.in/x",
    "free laptop lottery prize claim at http://claim.win/now",
    "Send your PIN to confirm. Link: https://secure-bank.top/verify",
    "upi://pay?pa=shop@okhdfcbank&pn=Local%20Shop&am=250&tn=groceries",
]


@pytest.mark.skipif(shutil.which("node") is None or not INDEX.is_file(), reason="node or web/index.html not available")
def test_python_and_browser_engines_agree(tmp_path):
    corpus = tmp_path / "corpus.json"
    corpus.write_text(json.dumps(CORPUS), encoding="utf8")
    res = subprocess.run(["node", str(Path(__file__).parent / "parity.js"), str(INDEX), str(corpus)],
                         capture_output=True, text=True, encoding="utf-8", timeout=60)
    assert res.returncode == 0, res.stderr
    js = json.loads(res.stdout)
    assert len(js) == len(CORPUS)
    for text, j in zip(CORPUS, js):
        a = fraud.analyze(text)
        py = {"verdict": a["verdict"], "score": a["score"], "titles": [f["title"] for f in a["findings"]],
              "urls": [[u["host"], u["flagged"]] for u in a["urls"]],
              "upis": [[u["kind"], u["pa"], u["am"]] for u in a["upis"]]}
        assert py == j, f"engines disagree on: {text!r}"
