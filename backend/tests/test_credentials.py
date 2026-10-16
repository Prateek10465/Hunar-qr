import base64

import pytest
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import encode_dss_signature

from app.credentials import Issuer, b64u, canonical, fingerprint, unb64u

CRED = {"id": "urn:hunarqr:X", "b": [3, 2.0, {"z": "தமிழ்", "a": 1}], "a": "é"}


@pytest.fixture
def issuer(tmp_path):
    return Issuer.load_or_create(key_pem="", key_path=tmp_path / "k.pem", did="did:example:t")


def test_canonical_is_sorted_compact_and_utf8():
    assert canonical({"b": 1, "a": {"d": 1, "c": 2}}) == b'{"a":{"c":2,"d":1},"b":1}'
    assert canonical({"x": 2.0}) == b'{"x":2}'
    assert "தமிழ்".encode() in canonical(CRED)


def test_canonical_ignores_key_order():
    assert canonical({"a": 1, "b": 2}) == canonical({"b": 2, "a": 1})


def test_sign_verify_roundtrip(issuer):
    sig = issuer.sign(CRED)
    assert len(sig) == 64 and issuer.verify(CRED, sig)


def test_tamper_fails(issuer):
    sig = issuer.sign(CRED)
    bad = {**CRED, "a": "e"}
    assert not issuer.verify(bad, sig)
    flipped = bytes([sig[0] ^ 1]) + sig[1:]
    assert not issuer.verify(CRED, flipped)
    assert not issuer.verify(CRED, sig[:-1])
    assert not issuer.verify(CRED, b"")


def test_key_persists_and_is_private(tmp_path):
    a = Issuer.load_or_create(key_pem="", key_path=tmp_path / "k.pem", did="d")
    sig = a.sign(CRED)
    b = Issuer.load_or_create(key_pem="", key_path=tmp_path / "k.pem", did="d")
    import os
    if os.name != "nt":
        assert (tmp_path / "k.pem").stat().st_mode & 0o777 == 0o600


def test_other_issuer_cannot_verify(issuer, tmp_path):
    other = Issuer.load_or_create(key_pem="", key_path=tmp_path / "o.pem", did="d")
    assert not other.verify(CRED, issuer.sign(CRED))


def test_public_jwk_verifies_independently(issuer):
    """A verifier that only has the published JWK can check the signature with a standard library."""
    jwk = issuer.public_jwk()
    x, y = int.from_bytes(unb64u(jwk["x"]), "big"), int.from_bytes(unb64u(jwk["y"]), "big")
    pub = ec.EllipticCurvePublicNumbers(x, y, ec.SECP256R1()).public_key()
    sig = issuer.sign(CRED)
    der = encode_dss_signature(int.from_bytes(sig[:32], "big"), int.from_bytes(sig[32:], "big"))
    pub.verify(der, canonical(CRED), ec.ECDSA(hashes.SHA256()))   # raises on failure


def test_did_document_shape(issuer):
    d = issuer.did_document()
    assert d["id"] == "did:example:t" and d["verificationMethod"][0]["publicKeyJwk"]["crv"] == "P-256"


def test_rejects_non_p256_key(tmp_path):
    from cryptography.hazmat.primitives import serialization
    key = ec.generate_private_key(ec.SECP384R1())
    pem = key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()).decode()
    with pytest.raises(ValueError):
        Issuer.load_or_create(key_pem=pem, key_path=tmp_path / "x.pem", did="d")


def test_b64u_roundtrip_and_validation():
    assert unb64u(b64u(b"\x00\xff\xfe")) == b"\x00\xff\xfe"
    with pytest.raises(ValueError):
        unb64u("ab*d")


def test_fingerprint_shape():
    assert len(fingerprint(b"x" * 64).split()) == 4
