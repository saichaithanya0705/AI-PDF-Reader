"""NVIDIA-hosted reranking service for RAG retrieval candidates."""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Sequence

import requests

from .nvidia_api import NvidiaApiUnavailableError, create_nvidia_api_session, require_nvidia_api_key
from .nvidia_retrieval_config import (
    DEFAULT_RERANK_ENDPOINT,
    DEFAULT_RERANK_MODEL,
    load_nvidia_reranker_config,
)


MAX_PASSAGES = 512


class RerankerServiceUnavailableError(NvidiaApiUnavailableError):
    """Raised when NVIDIA reranking cannot return a validated result."""


@dataclass(frozen=True)
class RerankScore:
    index: int
    logit: float


class NvidiaRerankerService:
    """Rank retrieval candidates through NVIDIA without loading a local model."""

    def __init__(self, session: requests.Session | None = None):
        try:
            self.config = load_nvidia_reranker_config()
        except ValueError as exc:
            raise RerankerServiceUnavailableError(str(exc)) from exc
        self.model_name = self.config.model_name
        self.endpoint = self.config.endpoint
        self.timeout_seconds = self.config.timeout_seconds
        try:
            self.api_key = require_nvidia_api_key()
        except NvidiaApiUnavailableError as exc:
            raise RerankerServiceUnavailableError(str(exc)) from exc
        self.session = session or create_nvidia_api_session()

    def rerank(self, query: str, passages: Sequence[str]) -> list[RerankScore]:
        if not query or not query.strip():
            raise ValueError("query must not be empty")
        if not passages:
            return []
        if len(passages) > MAX_PASSAGES:
            raise ValueError(f"NVIDIA reranking accepts at most {MAX_PASSAGES} passages")
        if any(not passage or not passage.strip() for passage in passages):
            raise ValueError("passages must contain non-empty text")

        try:
            response = self.session.post(
                self.endpoint,
                headers={"Authorization": f"Bearer {self.api_key}", "Accept": "application/json"},
                json={
                    "model": self.model_name,
                    "query": {"text": query},
                    "passages": [{"text": passage} for passage in passages],
                    "truncate": "END",
                },
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise RerankerServiceUnavailableError("NVIDIA reranking API request failed") from exc

        try:
            payload: Any = response.json()
            rankings = payload["rankings"]
            scores = [RerankScore(index=item["index"], logit=item["logit"]) for item in rankings]
        except (KeyError, TypeError, ValueError) as exc:
            raise RerankerServiceUnavailableError(
                "NVIDIA reranking API returned an invalid response"
            ) from exc

        expected_indexes = set(range(len(passages)))
        if {score.index for score in scores} != expected_indexes or len(scores) != len(passages):
            raise RerankerServiceUnavailableError(
                "NVIDIA reranking API returned an unexpected set of rankings"
            )
        if not all(
            isinstance(score.index, int)
            and not isinstance(score.index, bool)
            and isinstance(score.logit, (int, float))
            and not isinstance(score.logit, bool)
            and math.isfinite(score.logit)
            for score in scores
        ):
            raise RerankerServiceUnavailableError(
                "NVIDIA reranking API returned invalid ranking values"
            )
        return sorted(scores, key=lambda score: score.logit, reverse=True)


_reranker_service_instance: NvidiaRerankerService | None = None


def get_reranker_service() -> NvidiaRerankerService:
    global _reranker_service_instance
    if _reranker_service_instance is None:
        _reranker_service_instance = NvidiaRerankerService()
    return _reranker_service_instance
