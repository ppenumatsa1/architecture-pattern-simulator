from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import json
import os
from typing import Any

from redis import Redis
from redis.exceptions import ConnectionError as RedisConnectionError
from redis.exceptions import TimeoutError as RedisTimeoutError

SUBMISSION_REQUESTS_STREAM = "submission_requests"
RISK_RESULTS_STREAM = "risk_results"
DOMAIN_EVENTS_STREAM = "domain_events"


@dataclass(frozen=True)
class RedisSettings:
    dsn: str


@lru_cache(maxsize=1)
def get_redis_settings() -> RedisSettings:
    dsn = os.getenv("REDIS_DSN")
    if dsn:
        return RedisSettings(dsn=dsn)

    host = os.getenv("REDIS_HOST", "redis")
    port = int(os.getenv("REDIS_PORT", "6379"))
    db = int(os.getenv("REDIS_DB", "0"))
    password = os.getenv("REDIS_PASSWORD")
    auth = f":{password}@" if password else ""
    return RedisSettings(dsn=f"redis://{auth}{host}:{port}/{db}")


@lru_cache(maxsize=1)
def get_redis_client() -> Redis:
    return Redis.from_url(get_redis_settings().dsn, decode_responses=True, socket_timeout=5)


class RedisStreams:
    def __init__(self, client: Redis | None = None) -> None:
        self._client = client or get_redis_client()

    def publish(self, stream: str, payload: dict[str, Any], *, maxlen: int = 10_000) -> str:
        _ensure_supported_stream(stream)
        return self._client.xadd(
            stream, {"payload": json.dumps(payload)}, maxlen=maxlen, approximate=True
        )

    def read(
        self,
        stream: str,
        *,
        last_id: str = "0-0",
        count: int = 50,
        block_ms: int | None = None,
    ) -> list[tuple[str, dict[str, Any]]]:
        _ensure_supported_stream(stream)
        try:
            response = self._client.xread({stream: last_id}, count=count, block=block_ms)
        except (RedisTimeoutError, RedisConnectionError):
            # Treat transient read timeouts/connectivity blips as empty polls for long-running workers.
            return []
        if not response:
            return []

        messages = response[0][1]
        return [
            (
                message_id,
                _decode_payload(message.get("payload", "{}")),
            )
            for message_id, message in messages
        ]

    def publish_submission_request(self, payload: dict[str, Any]) -> str:
        return self.publish(SUBMISSION_REQUESTS_STREAM, payload)

    def publish_risk_result(self, payload: dict[str, Any]) -> str:
        return self.publish(RISK_RESULTS_STREAM, payload)

    def publish_domain_event(self, payload: dict[str, Any]) -> str:
        return self.publish(DOMAIN_EVENTS_STREAM, payload)

    def read_submission_requests(
        self, *, last_id: str = "0-0", count: int = 50, block_ms: int | None = None
    ) -> list[tuple[str, dict[str, Any]]]:
        return self.read(
            SUBMISSION_REQUESTS_STREAM, last_id=last_id, count=count, block_ms=block_ms
        )

    def read_risk_results(
        self, *, last_id: str = "0-0", count: int = 50, block_ms: int | None = None
    ) -> list[tuple[str, dict[str, Any]]]:
        return self.read(RISK_RESULTS_STREAM, last_id=last_id, count=count, block_ms=block_ms)

    def read_domain_events(
        self, *, last_id: str = "0-0", count: int = 50, block_ms: int | None = None
    ) -> list[tuple[str, dict[str, Any]]]:
        return self.read(DOMAIN_EVENTS_STREAM, last_id=last_id, count=count, block_ms=block_ms)


def _decode_payload(raw_payload: str) -> dict[str, Any]:
    try:
        loaded = json.loads(raw_payload)
    except json.JSONDecodeError:
        return {"raw": raw_payload}
    return loaded if isinstance(loaded, dict) else {"value": loaded}


def _ensure_supported_stream(stream: str) -> None:
    if stream not in {
        SUBMISSION_REQUESTS_STREAM,
        RISK_RESULTS_STREAM,
        DOMAIN_EVENTS_STREAM,
    }:
        raise ValueError(f"Unsupported stream '{stream}'")
