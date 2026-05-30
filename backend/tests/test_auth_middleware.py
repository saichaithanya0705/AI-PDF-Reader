import importlib
import sys

import pytest
from fastapi import HTTPException


def test_auth_middleware_never_uses_service_role_key_as_jwks_apikey(monkeypatch):
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "service-role-secret")
    monkeypatch.delenv("VITE_SUPABASE_ANON_KEY", raising=False)
    monkeypatch.delenv("SUPABASE_ANON_KEY", raising=False)
    sys.modules.pop("backend.app.auth_middleware", None)

    module = importlib.import_module("backend.app.auth_middleware")

    assert module.SUPABASE_API_KEY is None


def import_fresh_auth_middleware(monkeypatch):
    sys.modules.pop("backend.app.auth_config", None)
    sys.modules.pop("backend.app.auth_middleware", None)
    return importlib.import_module("backend.app.auth_middleware")


def test_development_auth_bypass_returns_configured_dev_account(monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("AUTH_BYPASS_ENABLED", "true")
    monkeypatch.setenv("DEV_AUTH_EMAIL", "ysaichaithu2005@gmail.com")
    monkeypatch.delenv("DEV_AUTH_USER_ID", raising=False)
    module = import_fresh_auth_middleware(monkeypatch)

    user = module.get_current_user(None)

    assert user["sub"] == "ysaichaithu2005@gmail.com"
    assert user["email"] == "ysaichaithu2005@gmail.com"
    assert user["role"] == "authenticated"
    assert user["auth_bypassed"] is True


def test_auth_bypass_is_never_allowed_in_production(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("AUTH_BYPASS_ENABLED", "true")
    monkeypatch.setenv("DEV_AUTH_EMAIL", "ysaichaithu2005@gmail.com")
    module = import_fresh_auth_middleware(monkeypatch)

    with pytest.raises(HTTPException) as exc_info:
        module.get_current_user(None)

    assert exc_info.value.status_code == 401


def test_optional_user_uses_dev_bypass_when_enabled(monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("AUTH_BYPASS_ENABLED", "true")
    monkeypatch.setenv("DEV_AUTH_EMAIL", "ysaichaithu2005@gmail.com")
    module = import_fresh_auth_middleware(monkeypatch)

    user = module.get_optional_user(None)

    assert user is not None
    assert user["sub"] == "ysaichaithu2005@gmail.com"
