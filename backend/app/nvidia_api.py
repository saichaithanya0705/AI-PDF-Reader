"""Shared authenticated HTTP primitives for NVIDIA hosted retrieval APIs."""
from __future__ import annotations

import os

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class NvidiaApiUnavailableError(RuntimeError):
    """Raised when a hosted NVIDIA API cannot be invoked safely."""


def require_nvidia_api_key() -> str:
    api_key = (os.getenv("NVIDIA_API_KEY") or "").strip()
    if not api_key:
        raise NvidiaApiUnavailableError("NVIDIA_API_KEY is required for hosted retrieval")
    return api_key


def create_nvidia_api_session() -> requests.Session:
    """Retry transient provider failures without switching to a local model."""
    retry_policy = Retry(
        total=2,
        connect=2,
        read=2,
        status=2,
        backoff_factor=0.25,
        status_forcelist=(408, 429, 500, 502, 503, 504),
        allowed_methods=frozenset({"POST"}),
        raise_on_status=False,
    )
    session = requests.Session()
    session.mount("https://", HTTPAdapter(max_retries=retry_policy))
    return session
