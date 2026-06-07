# AGENTS Guide (Human + Agent Collaboration)

## Purpose

This repo is a side-by-side simulator for monolith, microservices, and event-sourcing/CQRS implementations of the same insurance flow. Changes should improve clarity/comparability across patterns.

## Working agreement

- Make focused, reversible changes.
- Explain assumptions in PR/commit notes when behavior is ambiguous.
- Keep terminology consistent across API payloads, DB schemas, and UI labels.

## Repo map

- `monolith/api`: single-service baseline
- `microservices/*`: split submission/risk/status flow
- `event-sourcing-cqrs/*`: command/query split with event store + processors
- `shared/python`: shared DB, Redis, model, risk helpers
- `infra/postgres/*.sql`: persistence contracts
- `ui/src`: React TS simulator frontend

## Conventions to follow

### Python

- Type-hinted functions, Pydantic validation, explicit HTTP errors.
- SQL in parameterized SQLAlchemy `text()` statements.
- UTC timestamps and deterministic event payloads.

### React/TypeScript

- Strict TS types; keep DTOs in `ui/src/types`.
- Keep network logic in `ui/src/api`; components render state.
- Preserve architecture-mode isolation via `modeConfig`.

## Eventing expectations

- Monolith/microservices timeline event names stay snake_case.
- Event-store domain events stay dotted and versioned.
- New event schema => increment top-level `schema_version` + add upcast path.
- Idempotency must remain intact (DB unique keys, offset tracking, causation guards).

## Quality gates for local dev

Run at minimum:

1. `docker compose config -q`
2. `cd ui && npm run build`

If Python code changes materially, also run:

- `python -m compileall monolith microservices event-sourcing-cqrs shared`

## Safe-change checklist

- [ ] No breaking drift between architecture modes for the same scenario.
- [ ] Event names/contracts remain backward compatible (or migrated).
- [ ] DB constraints and code enums/status values still match.
- [ ] README/instructions updated when behavior/contracts change.
- [ ] Local Docker-based developer flow still works from `.env.example`.
