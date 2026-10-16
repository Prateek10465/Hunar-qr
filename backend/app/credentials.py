"""Credential signing and verification (ECDSA P-256, SHA-256).

Signatures are stored as raw r||s (64 bytes, base64url). That is the format the browser's Web Crypto
API produces and accepts, so a verifier can check a credential offline with the issuer's public JWK.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import re
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature, encode_dss_signature

_B64U = re.compile(r"^[A-Za-z0-9_-]+$")


def b64u(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def unb64u(s: str) -> bytes:
    if not _B64U.match(s or ""):
        raise ValueError("not base64url")
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def _norm(o):
    if isinstance(o, float) and o.is_integer():
        return int(o)
    if isinstance(o, dict):
        return {k: _norm(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_norm(v) for v in o]
    return o


def canonical(obj) -> bytes:
    """Deterministic JSON bytes: sorted keys, no spaces, UTF-8."""
    return json.dumps(_norm(obj), sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def fingerprint(sig: bytes) -> str:
    h = hashlib.sha256(sig).hexdigest()[:16]
    return " ".join(h[i:i + 4] for i in range(0, 16, 4))


class Issuer:
    def __init__(self, private_key: ec.EllipticCurvePrivateKey, did: str):
        self._key = private_key
        self._pub = private_key.public_key()
        self.did = did

    @classmethod
    def load_or_create(cls, *, key_pem: str, key_path: Path, did: str) -> "Issuer":
        if key_pem:
            key = serialization.load_pem_private_key(key_pem.encode(), password=None)
        elif key_path.exists():
            key = serialization.load_pem_private_key(key_path.read_bytes(), password=None)
        else:
            key = ec.generate_private_key(ec.SECP256R1())
            pem = key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                    serialization.NoEncryption())
            fd = os.open(key_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "wb") as f:
                f.write(pem)
        if not isinstance(key, ec.EllipticCurvePrivateKey) or key.curve.name != "secp256r1":
            raise ValueError("issuer key must be an ECDSA P-256 key")
        return cls(key, did)

    def sign(self, credential: dict) -> bytes:
        der = self._key.sign(canonical(credential), ec.ECDSA(hashes.SHA256()))
        r, s = decode_dss_signature(der)
        return r.to_bytes(32, "big") + s.to_bytes(32, "big")

    def verify(self, credential: dict, sig: bytes) -> bool:
        if len(sig) != 64:
            return False
        der = encode_dss_signature(int.from_bytes(sig[:32], "big"), int.from_bytes(sig[32:], "big"))
        try:
            self._pub.verify(der, canonical(credential), ec.ECDSA(hashes.SHA256()))
            return True
        except (InvalidSignature, ValueError):
            return False

    def public_jwk(self) -> dict:
        n = self._pub.public_numbers()
        return {"kty": "EC", "crv": "P-256", "alg": "ES256",
                "x": b64u(n.x.to_bytes(32, "big")), "y": b64u(n.y.to_bytes(32, "big"))}

    def did_document(self) -> dict:
        kid = self.did + "#key-1"
        return {"@context": ["https://www.w3.org/ns/did/v1"], "id": self.did,
                "verificationMethod": [{"id": kid, "type": "JsonWebKey2020", "controller": self.did,
                                        "publicKeyJwk": self.public_jwk()}],
                "assertionMethod": [kid]}
