from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import jwt


def create_token(subject: str, secret_key: str, minutes: int, token_type: str = "access") -> str:
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": subject,
        "type": token_type,
        "iat": now,
        "exp": now + timedelta(minutes=minutes),
    }
    return jwt.encode(payload, secret_key, algorithm="HS256")


def decode_token(token: str, secret_key: str) -> dict[str, Any]:
    return jwt.decode(token, secret_key, algorithms=["HS256"])

