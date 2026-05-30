"""Authentication environment policy.

This module is the single place that decides whether local development may
replace Supabase JWT authentication with a deterministic test user.
"""
from __future__ import annotations

import os
from typing import Dict


DEV_AUTH_EMAIL_DEFAULT = "ysaichaithu2005@gmail.com"
_TRUTHY = {"1", "true", "yes", "on"}
_DEVELOPMENT_ENVS = {"development", "dev", "local", "test"}


def current_environment() -> str:
    return (os.getenv("APP_ENV") or os.getenv("ENVIRONMENT") or "production").strip().lower()


def auth_bypass_enabled() -> bool:
    if current_environment() not in _DEVELOPMENT_ENVS:
        return False
    return (os.getenv("AUTH_BYPASS_ENABLED") or "").strip().lower() in _TRUTHY


def development_user() -> Dict[str, object]:
    email = (os.getenv("DEV_AUTH_EMAIL") or DEV_AUTH_EMAIL_DEFAULT).strip()
    user_id = (os.getenv("DEV_AUTH_USER_ID") or email).strip()
    return {
        "sub": user_id,
        "user_id": user_id,
        "email": email,
        "role": "authenticated",
        "authenticated": True,
        "auth_bypassed": True,
    }
