from app.core.security import create_access_token, decode_access_token, hash_password, verify_password


def test_password_hash_and_token_round_trip():
    hashed = hash_password("temporary-test-password")
    assert hashed != "temporary-test-password"
    assert verify_password("temporary-test-password", hashed)
    assert not verify_password("wrong", hashed)
    claims = decode_access_token(create_access_token("user-123", {"email": "person@example.test"}))
    assert claims["sub"] == "user-123"
    assert claims["email"] == "person@example.test"
