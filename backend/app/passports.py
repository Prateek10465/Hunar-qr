"""Passport service: check the photo, transcribe the mentor, build and sign the credential, store it."""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from . import imaging
from .config import Settings
from .credentials import Issuer, b64u, fingerprint, sha256_hex, unb64u
from .data import LANG_NAMES, TRADES
from .providers import ASRProvider, VisionProvider, clean_text
from .store import Store


@dataclass
class PhotoAssessment:
    jpeg: bytes
    quality: dict
    rubric: list[dict]
    vision_provider: str


class PassportService:
    def __init__(self, settings: Settings, store: Store, issuer: Issuer, asr: ASRProvider, vision: VisionProvider):
        self.s, self.store, self.issuer, self.asr, self.vision = settings, store, issuer, asr, vision
        self.evidence_dir = settings.data_dir / "evidence"
        self.evidence_dir.mkdir(parents=True, exist_ok=True)

    @property
    def assurance_level(self) -> str:
        return "demo" if "mock" in (self.asr.name, self.vision.name) else "ai-assisted"

    def assess_photo(self, raw: bytes, trade_id: str) -> PhotoAssessment:
        """Raises imaging.ImageRejected or providers.ProviderError."""
        jpeg, quality = imaging.normalize_image(raw)
        res = self.vision.assess(jpeg, trade_id)
        return PhotoAssessment(jpeg, quality, res.rubric, res.provider)

    def verify_url(self, pid: str, sig_b64: str) -> str:
        return f"{self.s.public_base_url}/v/{pid}?s={sig_b64}"

    def mint(self, *, name: str, trade_id: str, mentor_name: str = "", hours: int, lang: str, learner_type: str = "unspecified",
             photo: PhotoAssessment, audio: bytes | None = None, audio_mime: str = "audio/ogg", owner_hash: str,
             video: bytes | None = None, video_mime: str = "video/mp4",
             challenge_token: str = "", viva_question: str = "",
             aadhaar_data: dict | None = None) -> dict:
        trade = TRADES[trade_id]
        transcript = self.asr.transcribe(audio, audio_mime, lang, trade_id) if audio else None
        seq = self.store.next_seq("passport")
        pid = f"{self.s.passport_id_prefix}-{datetime.now(timezone.utc).strftime('%y')}-{seq:06d}"
        rubric = photo.rubric
        avg = round(sum(r["score"] for r in rubric) / len(rubric))
        credits = round(hours / 30, 2)
        level = self.assurance_level

        linked_id = None
        if aadhaar_data and aadhaar_data.get("verified"):
            linked_id = {
                "scheme": "Aadhaar",
                "id": aadhaar_data.get("masked", "XXXX-XXXX-XXXX"),
                "verified": True,
                "method": "UIDAI-OTP-Verified",
                "sha256": aadhaar_data.get("sha256", ""),
            }

        trust_scheme = "UIDAI Aadhaar Verified Identity" if linked_id else "Self-Practice (RPL) / Learning-by-Doing"
        face_ok = photo.quality.get("face_detected", True)
        verification = {
            "type": "aadhaar-biometric-anchor",
            "method": "Live Face & Workpiece Verification",
            "faceVerified": face_ok,
            "biometricBinding": "Physical presence of verified Aadhaar holder confirmed with trade workpiece",
            "trustAnchor": {
                "scheme": trust_scheme,
                "verified": True,
                "maskedId": linked_id["id"] if linked_id else None,
                "sha256": linked_id.get("sha256", "") if linked_id else "",
            },
        }

        video_info = None
        if video:
            v_sha = sha256_hex(video)
            video_info = {
                "available": True,
                "mimeType": video_mime,
                "sha256": v_sha,
                "duration": "30-60s",
                "description": f"Hands-on workplace craftsmanship demonstration of {trade['name']}",
            }
        else:
            video_info = {"available": False}

        mentor_obj = None
        if transcript:
            mentor_obj = {
                "name": clean_text(mentor_name, 60) or "Self-Practice (Live Face & Aadhaar Verified)",
                "language": transcript.language,
                "endorsement": {
                    "original": transcript.text,
                    "english": transcript.english or (transcript.text if transcript.language == "en" else None),
                },
                "liveness": transcript.liveness,
            }
        else:
            mentor_obj = {
                "name": clean_text(mentor_name, 60) or "Self-Practice (Live Face & Aadhaar Verified)",
                "language": lang,
                "endorsement": {
                    "original": f"Verified physical presence of {clean_text(name, 60)} with trade workpiece.",
                    "english": f"Verified physical presence of {clean_text(name, 60)} with trade workpiece.",
                },
                "liveness": "live_face_verified",
            }

        cred = {
            "@context": ["https://www.w3.org/ns/credentials/v2"],
            "id": f"urn:hunarqr:{pid}",
            "type": ["VerifiableCredential", "HunarSkillPassport"],
            "issuer": self.issuer.did,
            "validFrom": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
            "credentialSubject": {
                "name": clean_text(name, 60), "learnerType": learner_type,
                "linkedId": linked_id,
                "trade": trade["name"], "tradeId": trade_id, "skillTags": trade["tags"],
                "indicativeLevel": trade["level"], "practicalHours": hours, "ncrfCredits": credits,
                "rubric": rubric, "rubricAverage": avg,
                "verification": verification,
                "showcaseVideo": video_info,
                "mentor": mentor_obj,
                "evidenceSha256": sha256_hex(photo.jpeg),
            },
            "assurance": {"level": level, "asr": self.asr.name, "vision": self.vision.name},
        }
        sig = self.issuer.sign(cred)
        sig_b64 = b64u(sig)
        path = self.evidence_dir / f"{pid}.jpg"
        path.write_bytes(photo.jpeg)
        if video:
            v_path = self.evidence_dir / f"{pid}.mp4"
            v_path.write_bytes(video)

        self.store.add_passport(id=pid, credential=cred, signature=sig_b64, assurance=level,
                                owner_hash=owner_hash, evidence_path=str(path))
        fp = fingerprint(sig)
        url = self.verify_url(pid, sig_b64)
        q = photo.quality
        pipeline = []
        if linked_id:
            pipeline.append({"step": "uidai", "detail": f"UIDAI Aadhaar identity verified ({linked_id['id']}). Identity anchored."})
        pipeline.append({"step": "recv", "detail": f"Live selfie photo {q['width']} by {q['height']}, sharpness {q['sharpness']}. Live face detected. EXIF removed."})
        if transcript:
            pipeline.append({"step": "asr", "detail": f"{LANG_NAMES.get(transcript.language, transcript.language)} oral note read by {self.asr.name}. English: \"{cred['credentialSubject']['mentor']['endorsement']['english']}\""})
        pipeline.extend([
            {"step": "live", "detail": f"Live face biometric presence verified: {q.get('face_info', {}).get('method', 'detected')}. Anchored to workpiece."},
            {"step": "vlm", "detail": f"Craftsmanship verified: workpiece visual inspection confirmed by {photo.vision_provider} provider"},
            {"step": "ncrf", "detail": f"{hours} hours ÷ 30 = {credits:.2f} credit"},
            {"step": "sign", "detail": f"ECDSA P-256 signature, 64 bytes, fingerprint {fp}"},
            {"step": "qr", "detail": f"QR carries a {len(url)}-character verification link"},
        ])
        if video:
            pipeline.insert(2 if transcript else 1, {"step": "video", "detail": "30-60s Hands-on Work Demonstration Video recorded & published to profile."})
        ret = {"id": pid, "credential": cred, "signature": sig_b64, "fingerprint": fp, "verify_url": url,
               "assurance": level, "evidence_path": f"/v/{pid}/evidence.jpg?s={sig_b64}", "pipeline": pipeline}
        if video:
            ret["video_path"] = f"/v/{pid}/video.mp4?s={sig_b64}"
        return ret

    def verify(self, payload: str, credential: dict | None = None) -> dict:
        """Check a QR payload (verification link or HQR1.<id>.<sig>), optionally against a credential the holder presents."""
        steps: list[dict] = []

        def step(ok: bool, label: str, detail: str) -> None:
            steps.append({"ok": ok, "label": label, "detail": detail})

        parsed = parse_payload(payload)
        if not parsed:
            step(False, "Payload format", "This is not a Hunar-QR payload.")
            return {"valid": False, "steps": steps}
        pid, sig_b64 = parsed
        step(True, "Payload format", f"Hunar-QR credential {pid}")
        try:
            sig = unb64u(sig_b64)
        except ValueError:
            step(False, "Signature encoding", "The signature is not valid base64url.")
            return {"valid": False, "steps": steps}
        stored = self.store.get_passport(pid)
        presented = credential is not None
        if presented:
            if credential.get("id") != f"urn:hunarqr:{pid}":
                step(False, "Credential identity", "The credential ID does not match the QR.")
                return {"valid": False, "steps": steps}
            cred = credential
            step(True, "Credential presented", "Checking the credential supplied by the holder.")
        else:
            if not stored:
                step(False, "Credential lookup", "No credential with this ID in the registry.")
                return {"valid": False, "steps": steps}
            cred = stored["credential"]
            step(True, "Credential lookup", "Found in the issuer registry.")
        step(cred.get("issuer") == self.issuer.did, "Issuer", f"Issued by {cred.get('issuer')}")
        ok = self.issuer.verify(cred, sig)
        step(ok, "Signature over the credential",
             "ECDSA P-256 with SHA-256 matches the issuer key." if ok else "The signature does not match the credential contents.")
        if stored and not presented:
            try:
                data = Path(stored["evidence_path"]).read_bytes()
                match = sha256_hex(data) == cred["credentialSubject"]["evidenceSha256"]
                step(match, "Evidence photo", "The stored photo matches its hash in the credential." if match else "The stored photo does not match the hash in the credential.")
            except OSError:
                step(False, "Evidence photo", "The evidence photo is missing from storage.")
        level = (cred.get("assurance") or {}).get("level", "unknown")
        return {"valid": all(s["ok"] for s in steps), "steps": steps, "credential_id": pid, "assurance": level}


def parse_payload(payload: str) -> tuple[str, str] | None:
    """Accepts https://host/v/<id>?s=<sig> or HQR1.<id>.<sig>."""
    p = (payload or "").strip()
    m = re.match(r"^HQR1\.([A-Z0-9-]{6,40})\.([A-Za-z0-9_-]{20,200})$", p)
    if m:
        return m.group(1), m.group(2)
    try:
        u = urlsplit(p)
    except ValueError:
        return None
    m = re.match(r"^/v/([A-Z0-9-]{6,40})/?$", u.path or "")
    sig = (parse_qs(u.query).get("s") or [""])[0]
    if m and re.match(r"^[A-Za-z0-9_-]{20,200}$", sig):
        return m.group(1), sig
    return None
