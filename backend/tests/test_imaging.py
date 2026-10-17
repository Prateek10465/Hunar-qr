import cv2
import numpy as np
import pytest

from app import imaging
from app.imaging import ImageRejected

UPI = "upi://pay?pa=pmkaushal.fee@okdemo&pn=PM%20Kaushal%20Fee&am=99&cu=INR&tn=Processing%20fee"


def _img(trade="electrical"):
    return cv2.imdecode(np.frombuffer(imaging.sample_image(trade), np.uint8), cv2.IMREAD_COLOR)


def _png(a):
    return cv2.imencode(".png", a)[1].tobytes()


@pytest.mark.parametrize("trade", ["electrical", "tailoring", "solar"])
def test_sample_images_pass(trade):
    jpeg, q = imaging.normalize_image(imaging.sample_image(trade))
    assert jpeg[:2] == b"\xff\xd8" and q["width"] == 800 and q["sharpness"] > imaging.BLUR_MIN


@pytest.mark.parametrize("label,make,code", [
    ("blur", lambda a: cv2.GaussianBlur(a, (0, 0), 6), "too_blurry"),
    ("dark", lambda a: (a * 0.1).astype(np.uint8), "too_dark"),
    ("bright", lambda a: np.clip(a.astype(int) + 200, 0, 255).astype(np.uint8), "too_bright"),
    ("small", lambda a: cv2.resize(a, (200, 120)), "too_small"),
])
def test_bad_photos_are_rejected(label, make, code):
    with pytest.raises(ImageRejected) as e:
        imaging.normalize_image(_png(make(_img())))
    assert e.value.code == code


@pytest.mark.parametrize("data", [b"", b"garbage", b"<svg xmlns='http://www.w3.org/2000/svg'/>", b"\x89PNG\r\n\x1a\ntruncated"])
def test_non_images_are_rejected(data):
    with pytest.raises(ImageRejected) as e:
        imaging.normalize_image(data)
    assert e.value.code == "not_image"


def test_too_many_pixels_rejected(monkeypatch):
    monkeypatch.setattr(imaging, "MAX_PIXELS", 1000)
    with pytest.raises(ImageRejected) as e:
        imaging.normalize_image(imaging.sample_image("solar"))
    assert e.value.code == "too_large"


def test_large_photos_are_downscaled():
    big = cv2.resize(_img(), (2400, 1500), interpolation=cv2.INTER_CUBIC)
    noise = np.random.default_rng(1).integers(-12, 12, big.shape).astype(np.int16)
    big = np.clip(big.astype(np.int16) + noise, 0, 255).astype(np.uint8)
    jpeg, q = imaging.normalize_image(_png(big))
    assert max(q["width"], q["height"]) == 1280


def test_reencoding_drops_exif():
    from PIL import Image
    import io
    im = Image.open(io.BytesIO(imaging.sample_image("electrical")))
    exif = Image.Exif()
    exif[0x010F] = "SecretPhoneMaker"
    buf = io.BytesIO()
    im.save(buf, format="JPEG", exif=exif.tobytes())
    assert b"SecretPhoneMaker" in buf.getvalue()
    jpeg, _ = imaging.normalize_image(buf.getvalue())
    assert b"SecretPhoneMaker" not in jpeg and b"Exif" not in jpeg


def test_qr_roundtrip():
    assert imaging.decode_qr(imaging.qr_png(UPI)) == UPI
    assert imaging.decode_qr(imaging.qr_png("https://example.com/v/HQR-1?s=abc")) == "https://example.com/v/HQR-1?s=abc"


def test_qr_inside_a_larger_photo():
    qr = cv2.imdecode(np.frombuffer(imaging.qr_png(UPI, scale=6), np.uint8), cv2.IMREAD_COLOR)
    canvas = _img("solar")
    canvas[40:40 + qr.shape[0], 40:40 + qr.shape[1]] = qr
    assert imaging.decode_qr(_png(canvas)) == UPI


def test_no_qr_returns_none():
    assert imaging.decode_qr(imaging.sample_image("tailoring")) is None
    assert imaging.decode_qr(b"not an image") is None


def test_qr_svg_is_svg():
    assert imaging.qr_svg("hello").lstrip().startswith("<svg")


def test_photo_without_face_is_rejected():
    img = np.zeros((400, 400, 3), dtype=np.uint8) + 120
    cv2.rectangle(img, (50, 50), (350, 350), (20, 20, 20), 4)
    with pytest.raises(ImageRejected) as e:
        imaging.normalize_image(_png(img))
    assert e.value.code == "no_face"
