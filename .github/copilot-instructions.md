# Copilot Instructions for `cqrs`

## Repository intent

This POC compares the same insurance-submission workflow across three styles:

- **Monolith** (`monolith/api`)
- **Microservices** (`microservices/*`)
- **Event Sourcing + CQRS** (`event-sourcing-cqrs/*`)

Use this repo to keep behavior comparable across modes, not to optimize one mode in isolation.

## Architecture patterns to preserve

- Python FastAPI services expose health + submission/event endpoints.
- PostgreSQL is the source of truth for persisted state and projections.
- Redis Streams carry async messages (`submission_requests`, `risk_results`, `domain_events`).
- UI (`ui/`) is React + TypeScript and routes through nginx gateway.

## Coding conventions

### Python (FastAPI/services)

- Keep route wiring in `main.py` + `routes.py`; business logic in service/worker modules.
- Use explicit typing, `from __future__ import annotations`, and snake_case.
- Validate request payloads with Pydantic models (`extra = "forbid"`).
- Use `session_scope()` + SQLAlchemy `text()` for DB access.
- Emit/compare timestamps in UTC ISO-8601.

### React + TypeScript (UI)

- Preserve strict typing (`ui/tsconfig.json` has `strict: true`).
- Prefer typed helpers in `ui/src/types` and `ui/src/api`; avoid `any`.
- Keep components functional and side effects in hooks.
- Keep architecture mode behavior centralized in `ui/src/api/modeConfig.ts`.

## Event rules (critical)

- **Monolith + microservices timeline events:** snake_case types (e.g., `submission_received`).
- **Event-sourcing domain events:** dotted types (e.g., `submission.created`, `risk.scored`).
- When introducing new event payload schema, bump `schema_version` and add upcasters in `event_store/upcasters.py`.
- Preserve aggregate event ordering/versioning (`aggregate_version` monotonic per aggregate).
- Preserve idempotency guarantees:
  - microservices timeline uses `(producer_service, idempotency_key)` unique index + `ON CONFLICT DO NOTHING`.
  - processors use `processor_offsets` and causation checks to avoid replay side effects.

## Validation commands (run before/after non-trivial changes)

- `docker compose config -q`
- `cd ui && npm run build`
- Optional Python syntax smoke check: `python -m compileall monolith microservices event-sourcing-cqrs shared`

## Safe-change checklist

- Keep all three architecture modes runnable and behaviorally comparable.
- Do not rename/remove existing event types without migration/upcaster updates.
- Keep DB constraints/checks aligned with code-level enums and statuses.
- Maintain SSE contract shape expected by UI normalization (`type/eventType/status` fields).
- Scope changes surgically; avoid unrelated refactors in this POC.

## Documentation expectations

When behavior/API/schema/event contracts change, update:

- `README.md` (high-level behavior and run instructions)
- this file and/or `AGENTS.md` if working conventions changed
- relevant SQL schema under `infra/postgres/` when persistence contracts change

## Local-dev constraints for this POC

- Assume **local Docker Compose** workflow first; no cloud deployment assumptions.
- Keep default ports and env contract from `.env.example`.
- Prefer reproducible local commands over external services.
- Avoid introducing dependencies that require managed infrastructure for basic runs.
