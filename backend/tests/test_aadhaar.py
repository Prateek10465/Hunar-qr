from app import aadhaar


def test_verhoeff_valid_and_invalid():
    # Generate valid 12-digit Aadhaar using 11 digits + Verhoeff check digit
    prefix = "98425612341"
    chk = aadhaar.generate_verhoeff_check_digit(prefix)
    valid_aadhaar = prefix + chk
    assert len(valid_aadhaar) == 12
    assert aadhaar.validate_aadhaar(valid_aadhaar) is True
    assert aadhaar.validate_aadhaar(f"{valid_aadhaar[:4]} {valid_aadhaar[4:8]} {valid_aadhaar[8:]}") is True
    assert aadhaar.validate_aadhaar(f"{valid_aadhaar[:4]}-{valid_aadhaar[4:8]}-{valid_aadhaar[8:]}") is True

    # Tampered / invalid checksum
    wrong_chk = str((int(chk) + 1) % 10)
    invalid_aadhaar = prefix + wrong_chk
    assert aadhaar.validate_aadhaar(invalid_aadhaar) is False


def test_aadhaar_rejects_malformed_numbers():
    assert aadhaar.validate_aadhaar("") is False
    assert aadhaar.validate_aadhaar("1234") is False
    assert aadhaar.validate_aadhaar("abcdefghijkl") is False
    # Starting with 0 or 1
    assert aadhaar.validate_aadhaar("012345678901") is False
    assert aadhaar.validate_aadhaar("112345678901") is False
    # Identical repeated digits
    assert aadhaar.validate_aadhaar("222222222222") is False
    assert aadhaar.validate_aadhaar("999999999999") is False


def test_mask_aadhaar():
    assert aadhaar.mask_aadhaar("9842 5612 3414") == "XXXX-XXXX-3414"
    assert aadhaar.mask_aadhaar("984256123414") == "XXXX-XXXX-3414"
    assert aadhaar.mask_aadhaar("12") == "XXXX-XXXX-XXXX"


def test_hash_aadhaar():
    h1 = aadhaar.hash_aadhaar("9842 5612 3414")
    h2 = aadhaar.hash_aadhaar("984256123414")
    assert h1 == h2 and len(h1) == 64


def test_verify_aadhaar_otp():
    assert aadhaar.verify_aadhaar_otp("123456") is True
    assert aadhaar.verify_aadhaar_otp(" 123 456 ") is True
    assert aadhaar.verify_aadhaar_otp("000000") is False
