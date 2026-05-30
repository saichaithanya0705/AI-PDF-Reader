"""Resolve authenticated user id; optional dev-only client_id fallback."""
import os
from typing import Optional

from fastapi import HTTPException


def resolve_user_id(
    current_user: Optional[dict],
    client_id: Optional[str] = None,
) -> str:
    """Return the authenticated user id. Reject spoofed client_id in production."""
    if current_user and current_user.get("sub"):
        return current_user["sub"]

    allow_fallback = os.getenv("ALLOW_CLIENT_ID_FALLBACK", "false").lower() in (
        "1",
        "true",
        "yes",
    )
    if allow_fallback and client_id:
        return client_id

    raise HTTPException(
        status_code=401,
        detail="Authentication required. Sign in and send Authorization: Bearer <token>.",
    )
