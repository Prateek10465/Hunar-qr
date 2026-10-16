"""Aadhaar (UIDAI) Identity Verification utility for Hunar-QR.

Implements:
1. The mathematical Verhoeff algorithm checksum validation (as mandated by UIDAI specifications).
2. Privacy-compliant Aadhaar masking (XXXX-XXXX-1234) under Section 29 of the Aadhaar Act.
3. Cryptographic SHA-256 identity binding.
4. Instant OTP verification simulator for live demonstrations.
"""
from __future__ import annotations

import hashlib
import re

# ----------------------------------------------------------------------
# Verhoeff algorithm lookup tables
# ----------------------------------------------------------------------
# Multiplication table d
_D = (
    (0, 1, 2, 3, 4, 5, 6, 7, 8, 9),
    (1, 2, 3, 4, 0, 6, 7, 8, 9, 5),
    (2, 3, 4, 0, 1, 7, 8, 9, 5, 6),
    (3, 4, 0, 1, 2, 8, 9, 5, 6, 7),
    (4, 0, 1, 2, 3, 9, 5, 6, 7, 8),
    (5, 9, 8, 7, 6, 0, 4, 3, 2, 1),
    (6, 5, 9, 8, 7, 1, 0, 4, 3, 2),
    (7, 6, 5, 9, 8, 2, 1, 0, 4, 3),
    (8, 7, 6, 5, 9, 3, 2, 1, 0, 4),
    (9, 8, 7, 6, 5, 4, 3, 2, 1, 0),
)

# Permutation table p
_P = (
    (0, 1, 2, 3, 4, 5, 6, 7, 8, 9),
    (1, 5, 7, 6, 2, 8, 3, 0, 9, 4),
    (5, 8, 0, 3, 7, 9, 6, 1, 4, 2),
    (8, 9, 1, 6, 0, 4, 3, 5, 2, 7),
    (9, 4, 5, 3, 1, 2, 6, 8, 7, 0),
    (4, 2, 8, 6, 5, 7, 3, 9, 0, 1),
    (2, 7, 9, 3, 8, 0, 6, 4, 1, 5),
    (7, 0, 4, 6, 9, 1, 3, 2, 5, 8),
)

# Inverse table inv
_INV = (0, 4, 3, 2, 1, 5, 6, 7, 8, 9)


def verhoeff_checksum(num_str: str) -> bool:
    """Validate a numeric string against the Verhoeff algorithm."""
    c = 0
    # Process digits in reverse order
    for i, ch in enumerate(reversed(num_str)):
        if not ch.isdigit():
            return False
        c = _D[c][_P[i % 8][int(ch)]]
    return c == 0


def generate_verhoeff_check_digit(num_str: str) -> str:
    """Generate the Verhoeff check digit for an 11-digit number."""
    c = 0
    for i, ch in enumerate(reversed(num_str)):
        c = _D[c][_P[(i + 1) % 8][int(ch)]]
    return str(_INV[c])


def clean_aadhaar(raw: str) -> str:
    """Strip spaces, hyphens, and formatting from an input string."""
    return re.sub(r"[\s\-]", "", str(raw or "").strip())


def validate_aadhaar(raw: str) -> bool:
    """Validate that raw is a valid 12-digit Aadhaar number with correct Verhoeff checksum.

    Rejects:
    - Non-numeric or wrong length (< 12 or > 12)
    - Starting with '0' or '1' (Aadhaar numbers do not start with 0 or 1)
    - Repeated identical digits (e.g., 000000000000, 222222222222)
    - Invalid Verhoeff check digit
    """
    cleaned = clean_aadhaar(raw)
    if not (len(cleaned) == 12 and cleaned.isdigit()):
        return False
    if cleaned[0] in ("0", "1"):
        return False
    if len(set(cleaned)) == 1:
        # All digits are identical
        return False
    return verhoeff_checksum(cleaned)


def mask_aadhaar(raw: str) -> str:
    """Return UIDAI-compliant masked Aadhaar string (XXXX-XXXX-1234)."""
    cleaned = clean_aadhaar(raw)
    if len(cleaned) < 4:
        return "XXXX-XXXX-XXXX"
    last4 = cleaned[-4:]
    return f"XXXX-XXXX-{last4}"


def hash_aadhaar(raw: str, salt: str = "hunarqr-aadhaar-salt") -> str:
    """Return irreversible SHA-256 hash for database deduplication without storing plaintext."""
    cleaned = clean_aadhaar(raw)
    return hashlib.sha256(f"{salt}:{cleaned}".encode("utf-8")).hexdigest()


DEMO_OTP = "123456"


def verify_aadhaar_otp(entered_otp: str, expected_otp: str = DEMO_OTP) -> bool:
    """Verify 6-digit OTP (accepts simulated demo OTP '123456' or live generated OTP)."""
    code = clean_aadhaar(entered_otp)
    return code == expected_otp or code == DEMO_OTP
