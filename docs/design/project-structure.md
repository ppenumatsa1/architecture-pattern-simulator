# Project Structure

```text
cqrs/
├─ monolith/
│  └─ api/                         # single-service implementation
├─ microservices/
│  ├─ submission-api/              # command intake + enqueue
│  ├─ risk-service/                # risk worker (Redis consumer)
│  ├─ persistence-service/         # result consumer + status updater
│  └─ status-api/                  # read + SSE endpoint
├─ event-sourcing-cqrs/
│  ├─ command-api/                 # writes immutable domain events
│  ├─ event_store/                 # event contracts/repository
│  ├─ processors/                  # risk + projection processors
│  └─ query-api/                   # projection reads + SSE
├─ shared/python/                  # DB, Redis, models, risk rules, timeline helpers
├─ infra/postgres/                 # schema bootstrap SQL
├─ gateway/                        # nginx routing and SSE proxy config
├─ ui/                             # React + Vite simulator UI
└─ docs/                           # design and contributor docs
```

## Key ownership boundaries

- **UI** owns mode selection, submission, SSE subscription, and data refresh UX.
- **Monolith** owns end-to-end transaction for its mode.
- **Microservices** split intake, compute, and read concerns with Redis async handoffs.
- **Event-sourcing** separates command writes (event store) from projection reads.
- **Shared** keeps common contracts/utilities consistent across services.

## Compose runtime mapping

- Included in `docker-compose.yml`: `postgres`, `redis`, mode APIs, `ui`, and `gateway`.
- Compose also starts worker/processor services for full async behavior during normal runs.
- Worker/processor code exists in:
  - `microservices/risk-service`
  - `microservices/persistence-service`
  - `event-sourcing-cqrs/processors`
    and can be run manually only when debugging outside Compose.

## Related docs

- [Architecture](architecture.md)
- [Code flow](code-flow.md)
- [Tech stack](tech-stack.md)
