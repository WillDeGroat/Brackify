from __future__ import annotations

import json
import logging
import os
import time
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class BracketStore:
    """Interface for storing and retrieving bracket payloads."""

    def save(self, bracket_id: str, payload: Dict[str, Any], ttl_seconds: int) -> None:
        raise NotImplementedError

    def get(self, bracket_id: str) -> Optional[Dict[str, Any]]:
        raise NotImplementedError


class InMemoryBracketStore(BracketStore):
    """Simple TTL-aware in-memory store for development and tests."""

    def __init__(self) -> None:
        self._store: Dict[str, tuple[Dict[str, Any], float]] = {}

    def save(self, bracket_id: str, payload: Dict[str, Any], ttl_seconds: int) -> None:
        if ttl_seconds <= 0:
            self._store.pop(bracket_id, None)
            return

        expires_at = time.time() + ttl_seconds
        self._store[bracket_id] = (payload, expires_at)

    def get(self, bracket_id: str) -> Optional[Dict[str, Any]]:
        record = self._store.get(bracket_id)
        if not record:
            return None

        payload, expires_at = record
        if time.time() > expires_at:
            self._store.pop(bracket_id, None)
            return None

        return payload


class RedisBracketStore(BracketStore):
    """Redis-backed store using key expiry for TTL handling."""

    def __init__(self, url: str, key_prefix: str = "bracket:") -> None:
        try:
            import redis  # type: ignore
        except ImportError as exc:  # pragma: no cover - handled by dependency management
            raise RuntimeError("redis library is required for RedisBracketStore") from exc

        self._client = redis.Redis.from_url(url, decode_responses=False)
        self._key_prefix = key_prefix

        try:
            self._client.ping()
        except Exception as exc:  # pragma: no cover - network dependent
            logger.warning("Falling back to in-memory store because Redis is unavailable: %s", exc)
            raise

    def _key(self, bracket_id: str) -> str:
        return f"{self._key_prefix}{bracket_id}"

    def save(self, bracket_id: str, payload: Dict[str, Any], ttl_seconds: int) -> None:
        key = self._key(bracket_id)
        if ttl_seconds <= 0:
            self._client.delete(key)
            return

        self._client.set(key, json.dumps(payload), ex=max(1, ttl_seconds))

    def get(self, bracket_id: str) -> Optional[Dict[str, Any]]:
        raw = self._client.get(self._key(bracket_id))
        if raw is None:
            return None

        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            self._client.delete(self._key(bracket_id))
            return None


def create_store_from_env() -> BracketStore:
    """Create a store based on environment variables, falling back to memory."""

    backend = (os.getenv("BRACKET_STORE_BACKEND") or "").lower()
    redis_url = os.getenv("BRACKET_REDIS_URL") or os.getenv("REDIS_URL")

    if backend == "redis" or redis_url:
        url = redis_url or "redis://localhost:6379/0"
        try:
            return RedisBracketStore(url)
        except Exception:
            logger.info("Using InMemoryBracketStore due to Redis configuration issues.")

    return InMemoryBracketStore()
