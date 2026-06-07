from __future__ import annotations

from typing import Any, Callable

Upcaster = Callable[[dict[str, Any]], dict[str, Any]]


_UPCASTERS: dict[tuple[str, int], Upcaster] = {}


def register_upcaster(event_type: str, from_version: int, handler: Upcaster) -> None:
    _UPCASTERS[(event_type, from_version)] = handler


def upcast(event: dict[str, Any], target_version: int | None = None) -> dict[str, Any]:
    current = dict(event)
    event_type = str(current.get("event_type", ""))
    version = int(
        current.get("schema_version") or current.get("metadata", {}).get("schema_version") or 1
    )
    current["schema_version"] = version

    if target_version is None or version >= target_version:
        return current

    while version < target_version:
        handler = _UPCASTERS.get((event_type, version))
        if handler is None:
            version += 1
            current["schema_version"] = version
            continue

        current = handler(current)
        version = int(current.get("schema_version", version + 1))
        current["schema_version"] = version

    return current
