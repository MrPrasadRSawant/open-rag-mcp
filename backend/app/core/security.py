import base64
import hashlib
import hmac
import json
from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt


class TokenError(ValueError):
    pass


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def create_access_token(
    *,
    subject: str,
    secret_key: str,
    expires_delta: timedelta,
) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": subject,
        "iat": int(now.timestamp()),
        "exp": int((now + expires_delta).timestamp()),
    }
    return _encode_jwt(payload, secret_key)


def decode_access_token(token: str, *, secret_key: str) -> dict[str, Any]:
    try:
        header_b64, payload_b64, signature_b64 = token.split(".")
    except ValueError as exc:
        raise TokenError("Invalid token format") from exc

    signing_input = f"{header_b64}.{payload_b64}".encode()
    expected_signature = _sign(signing_input, secret_key)
    actual_signature = _base64url_decode(signature_b64)
    if not hmac.compare_digest(actual_signature, expected_signature):
        raise TokenError("Invalid token signature")

    payload = json.loads(_base64url_decode(payload_b64))
    expires_at = payload.get("exp")
    if not isinstance(expires_at, int) or expires_at < int(datetime.now(UTC).timestamp()):
        raise TokenError("Token has expired")

    subject = payload.get("sub")
    if not isinstance(subject, str) or not subject:
        raise TokenError("Token subject is missing")

    return payload


def _encode_jwt(payload: dict[str, Any], secret_key: str) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    header_b64 = _base64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    payload_b64 = _base64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{header_b64}.{payload_b64}".encode()
    signature_b64 = _base64url_encode(_sign(signing_input, secret_key))
    return f"{header_b64}.{payload_b64}.{signature_b64}"


def _sign(signing_input: bytes, secret_key: str) -> bytes:
    return hmac.new(secret_key.encode("utf-8"), signing_input, hashlib.sha256).digest()


def _base64url_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("utf-8")


def _base64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)
