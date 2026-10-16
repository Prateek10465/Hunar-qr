"""Image handling: checks and clean-up of evidence photos, QR reading, QR drawing, sample images.

Evidence photos are decoded, size-checked, tested for darkness / blur, then re-encoded as JPEG.
Re-encoding drops EXIF data (including GPS position) before the photo is stored.
"""
from __future__ import annotations

import io
from functools import lru_cache

import cv2
import numpy as np
import segno
from PIL import Image, ImageDraw

MAX_PIXELS = 40_000_000
MIN_SIDE = 320
BLUR_MIN = 60.0       # variance of the Laplacian on an image at most 800 px wide
DARK_MAX = 35.0       # mean grey level
BRIGHT_MIN = 235.0


class ImageRejected(Exception):
    """The photo cannot be used. `code` is one of not_image, too_large, too_small, too_dark, too_bright, too_blurry."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def _decode(data: bytes):
    return cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)


def normalize_image(data: bytes, max_side: int = 1280) -> tuple[bytes, dict]:
    try:
        with Image.open(io.BytesIO(data)) as im:
            w, h = im.size
    except Image.DecompressionBombError:
        raise ImageRejected("too_large")
    except Exception:
        raise ImageRejected("not_image")
    if w * h > MAX_PIXELS:
        raise ImageRejected("too_large")
    img = _decode(data)
    if img is None:
        raise ImageRejected("not_image")
    h0, w0 = img.shape[:2]
    if min(h0, w0) < MIN_SIDE:
        raise ImageRejected("too_small")
    scale = min(1.0, max_side / max(h0, w0))
    if scale < 1.0:
        img = cv2.resize(img, (round(w0 * scale), round(h0 * scale)), interpolation=cv2.INTER_AREA)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    g = gray
    if gray.shape[1] > 800:
        g = cv2.resize(gray, (800, round(gray.shape[0] * 800 / gray.shape[1])), interpolation=cv2.INTER_AREA)
    sharp = float(cv2.Laplacian(g, cv2.CV_64F).var())
    mean = float(gray.mean())
    if mean < DARK_MAX:
        raise ImageRejected("too_dark")
    if mean > BRIGHT_MIN:
        raise ImageRejected("too_bright")
    if sharp < BLUR_MIN:
        raise ImageRejected("too_blurry")
    ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 88])
    if not ok:
        raise ImageRejected("not_image")
    return buf.tobytes(), {"width": int(img.shape[1]), "height": int(img.shape[0]),
                           "sharpness": round(sharp, 1), "brightness": round(mean, 1)}


def decode_qr(data: bytes) -> str | None:
    """Return the text of the first QR code found in the image, or None."""
    img = _decode(data)
    if img is None:
        return None
    padded = cv2.copyMakeBorder(img, 40, 40, 40, 40, cv2.BORDER_CONSTANT, value=(255, 255, 255))
    variants = [img, padded]
    if max(img.shape[:2]) < 700:
        variants.append(cv2.resize(padded, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC))
    detectors = []
    aruco = getattr(cv2, "QRCodeDetectorAruco", None)
    if aruco is not None:
        detectors.append(aruco)
    detectors.append(cv2.QRCodeDetector)
    for make in detectors:
        for v in variants:
            try:
                text, _, _ = make().detectAndDecode(v)
            except cv2.error:
                continue
            if text:
                return text
    return None


def qr_png(text: str, scale: int = 8) -> bytes:
    buf = io.BytesIO()
    segno.make(text, error="m").save(buf, kind="png", scale=scale, border=4)
    return buf.getvalue()


def qr_svg(text: str, scale: int = 6) -> str:
    buf = io.BytesIO()
    segno.make(text, error="m").save(buf, kind="svg", scale=scale, border=4, xmldecl=False, svgns=True)
    return buf.getvalue().decode("utf-8")


@lru_cache(maxsize=16)
def sample_image(trade_id: str) -> bytes:
    """A drawn stand-in for a work photo, used by the web demo and tests. Not a real photo."""
    color_map = {
        "electrical": (213, 219, 228), "tailoring": (234, 223, 202), "solar": (207, 230, 247),
        "plumbing": (210, 232, 248), "hvac": (215, 235, 245), "automobile": (235, 228, 220),
        "pottery": (235, 220, 205), "weaving": (240, 225, 235), "carpentry": (230, 220, 200),
        "masonry": (225, 225, 225), "welding": (215, 220, 230), "painting": (240, 235, 230),
    }
    base = color_map.get(trade_id, (220, 226, 234))
    img = Image.new("RGB", (800, 500), base)
    d = ImageDraw.Draw(img)
    if trade_id == "electrical":
        d.rectangle([40, 220, 760, 260], fill=(143, 155, 173))
        for x in (70, 240):
            d.rectangle([x, 90, x + 110, 340], fill=(244, 246, 249), outline=(143, 155, 173), width=3)
            d.rectangle([x + 18, 118, x + 92, 164], fill=(198, 40, 40))
        d.rectangle([420, 80, 590, 350], fill=(31, 79, 158))
        d.rectangle([446, 112, 564, 172], fill=(219, 231, 251))
        for i, c in enumerate([(198, 40, 40), (242, 184, 0), (21, 101, 192), (34, 34, 34)]):
            d.line([(130 + i * 50, 340), (300 + i * 70, 440), (470 + i * 30, 350)], fill=c, width=7)
    elif trade_id == "tailoring":
        d.polygon([(250, 70), (340, 40), (400, 110), (460, 40), (550, 70), (680, 170), (610, 240), (560, 200),
                   (560, 440), (240, 440), (240, 200), (190, 240), (120, 170)], fill=(168, 58, 98))
        d.line([(240, 200), (240, 440), (560, 440), (560, 200)], fill=(255, 255, 255), width=3)
        d.rectangle([30, 455, 770, 485], fill=(243, 201, 74))
        for x in range(40, 770, 40):
            d.line([(x, 455), (x, 470)], fill=(91, 67, 0), width=2)
    elif trade_id == "solar":
        d.rectangle([0, 360, 800, 500], fill=(185, 201, 168))
        d.ellipse([650, 40, 740, 130], fill=(255, 200, 61))
        d.polygon([(210, 120), (590, 100), (560, 330), (180, 340)], fill=(28, 63, 122), outline=(201, 211, 227))
        for i in range(1, 4):
            x = 210 + i * 95
            d.line([(x, 118 - i * 4), (x - 8 * i, 336)], fill=(111, 147, 209), width=3)
        d.line([(200, 230), (570, 215)], fill=(111, 147, 209), width=3)
        d.line([(300, 335), (270, 450)], fill=(107, 114, 128), width=12)
        d.line([(500, 325), (530, 450)], fill=(107, 114, 128), width=12)
        d.rectangle([640, 300, 740, 400], fill=(232, 236, 242), outline=(107, 114, 128), width=3)
    else:
        # Generic clean trade illustration stand-in with geometric work pieces and tools
        d.rectangle([80, 120, 720, 420], fill=(245, 248, 252), outline=(160, 174, 192), width=4)
        d.rectangle([120, 160, 420, 380], fill=(30, 64, 110))
        d.rectangle([460, 160, 680, 260], fill=(230, 126, 34))
        d.rectangle([460, 280, 680, 380], fill=(46, 125, 50))
        for i in range(5):
            d.line([(150 + i * 60, 180), (150 + i * 60, 360)], fill=(255, 255, 255), width=3)
        d.line([(100, 440), (700, 440)], fill=(100, 116, 139), width=8)
    rng = np.random.default_rng(7)
    arr = np.asarray(img).astype(np.int16)
    arr = np.clip(arr + rng.normal(0, 9, arr.shape).astype(np.int16), 0, 255).astype(np.uint8)
    out = io.BytesIO()
    Image.fromarray(arr).save(out, format="PNG")
    return out.getvalue()
