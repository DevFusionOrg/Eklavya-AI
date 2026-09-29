from httpx import AsyncClient

from app.core.encryption import decrypt_value, encrypt_value
from app.core.logging import scrub_pii


def test_scrub_pii_redacts_sensitive_keys_and_aadhaar_values() -> None:
    result = scrub_pii(
        {
            "email": "asha@example.test",
            "nested": {"phone": "9999999999", "note": "Aadhaar 123456789012"},
        }
    )
    assert result["email"] == "[REDACTED]"
    assert result["nested"]["phone"] == "[REDACTED]"
    assert "123456789012" not in result["nested"]["note"]


def test_sensitive_values_are_authenticated_and_encrypted() -> None:
    ciphertext = encrypt_value("9999999999")
    assert ciphertext != "9999999999"
    assert decrypt_value(ciphertext) == "9999999999"


async def test_security_headers_are_present(client: AsyncClient) -> None:
    response = await client.get("/health")
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["content-security-policy"].startswith("default-src")


async def test_cookie_authenticated_mutation_requires_csrf(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/auth/logout",
        cookies={"eklavya_session": "session"},
        json={"refresh_token": "not-a-token"},
    )
    assert response.status_code == 403
