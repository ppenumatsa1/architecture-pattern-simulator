# Architecture

## Purpose

The simulator compares three implementation styles for the same insurance-submission workflow:

1. Monolith
2. Microservices
3. Event Sourcing + CQRS

The UI switches modes and hits mode-specific APIs through the Nginx gateway.

## Source-of-truth model by mode

| Mode                  | Write source of truth                                     | Read source of truth                                                   | Consistency profile               |
| --------------------- | --------------------------------------------------------- | ---------------------------------------------------------------------- | --------------------------------- |
| Monolith              | `monolith.submissions` + related tables                   | Same tables                                                            | Strong within a transaction       |
| Microservices         | `microservices.submissions` (+ async risk/result updates) | `microservices.submissions` + `microservices.risk_results`             | Eventual across worker boundaries |
| Event Sourcing + CQRS | `event_sourcing.event_store` (immutable events)           | Projection tables (`submission_read_model`, `risk_summary_read_model`) | Eventual between write/read sides |

## Pattern comparison (practical)

| Pattern               | Core shape                                                                 | Strengths                                                            | Trade-offs                                                                                | Best fit                                            |
| --------------------- | -------------------------------------------------------------------------- | -------------------------------------------------------------------- | ----------------------------------------------------------------------------------------- | --------------------------------------------------- |
| Monolith              | One API owns command + read + persistence                                  | Simple deploy/debug, single transaction boundary                     | Tighter coupling, lower service independence                                              | Small teams and low-ops scenarios                   |
| Microservices         | Split intake/compute/persistence/read services with Redis Streams handoffs | Service separation, async decoupling realism, selective scaling      | More moving parts, idempotency/retry complexity, higher ops coordination                  | Teams needing service autonomy and async boundaries |
| Event Sourcing + CQRS | Event store write model + projection-based query model                     | Full audit trail, replayable history, explicit write/read separation | Highest cognitive/operational cost, projection lag handling, schema versioning discipline | Auditability-first and replay-heavy domains         |

## Data & transport roles

- **Postgres**: persistent state for all modes (schemas: `monolith`, `microservices`, `event_sourcing`).
- **Outbox tables**: reliable handoff from DB transactions to async transport (microservices + CQRS).
- **Redis Streams**: async event transport for microservices (`submission_requests`, `risk_results`) and event-sourcing processors (`domain_events`).
- **SSE**: UI-facing live timeline channel from each mode’s read side.

## Microservices service ownership

- **Submission API**: command intake + initial persistence + enqueue.
- **Risk Service**: async risk computation + risk timeline events.
- **Persistence Service**: applies async risk outcomes to status/risk read tables.
- **Status API**: read + SSE interface only.
- **Outbox Publisher**: publishes pending outbox rows to Redis Streams and marks rows as sent.

## CQRS service ownership

- **CQRS Command API**: appends immutable events and writes outbox rows in the same transaction.
- **CQRS Risk Worker**: consumes stream events and appends derived risk/decision domain events.
- **CQRS Projection Worker**: projects event store sequence to read models.
- **CQRS Outbox Worker**: reliably publishes outbox rows to Redis `domain_events`.
- **CQRS Query API**: serves projections and SSE.

This ownership split is deliberate to demonstrate decoupled write workers versus read-serving API concerns.

## Healthcheck policy

- Postgres and Redis healthchecks are intentionally simple readiness gates.
- Service startup uses `depends_on: condition: service_healthy` to avoid boot races.
- This adds minimal complexity while reducing transient startup failures and noisy retries.

## SSE behavior

- **Monolith** and **Microservices status-api** poll timeline tables every 1s and emit:
  - domain events (`event: <type>`)
  - keep-alive comments (`: keep-alive`) when idle.
- **Event-sourcing query-api** streams timeline projection rows, sleeps between empty polls, then emits `event: done` after an idle window.

## Related docs

- [Code flow](code-flow.md)
- [User flow](user-flow.md)
- [Project structure](project-structure.md)
