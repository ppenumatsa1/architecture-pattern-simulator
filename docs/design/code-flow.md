# Code Flow

## 1) Monolith flow

1. `POST /api/monolith/submissions`
2. Monolith API validates payload.
3. In one DB transaction it:
   - inserts submission,
   - computes risk via shared rules,
   - writes risk result,
   - updates status,
   - appends timeline events.
4. UI opens SSE: `GET /api/monolith/submissions/{id}/events`.
5. API polls `monolith.timeline_events` and streams events/keep-alives.

## 2) Microservices flow

1. `POST /api/microservices/submissions` (micro-submission-api).
2. micro-submission-api stores initial submission + `submission_received` timeline event + outbox row in one DB transaction.
3. micro-outbox-publisher reads pending outbox rows and publishes to Redis `submission_requests`.
4. micro-risk-service consumes request, evaluates risk, writes `risk_scored`/`manual_review_requested` timeline events, and writes `risk_results` outbox rows.
5. micro-outbox-publisher publishes `risk_results` rows; micro-persistence-service consumes them, upserts risk summary, updates status/version, and writes final timeline event.
6. UI reads status and streams events from micro-status-api (`microservices.timeline_events`).

## 3) Event Sourcing + CQRS flow

1. `POST /api/event-sourcing/commands/create-submission` (cqrs-command-api).
2. cqrs-command-api appends `submission.created` to `event_store` and writes outbox rows in the same transaction.
3. cqrs-outbox-worker publishes pending outbox rows to Redis `domain_events`.
4. cqrs-risk-worker reads new events from `event_store` using processor offsets and appends derived domain events (`risk.scoring.started`, `risk.scored`, decision event) + outbox rows.
5. cqrs-outbox-worker publishes derived outbox rows to `domain_events`.
6. cqrs-projection-worker reads event store sequence and updates:
   - `submission_read_model`
   - `risk_summary_read_model`
   - `timeline_events`
7. cqrs-query-api serves read endpoints + SSE from projection tables.

## Gateway routing note

Nginx maps `/api/{mode}/...` routes to the correct backend service and disables buffering for SSE endpoints.

## Runtime note

`docker-compose.yml` starts UI, gateway, APIs, Postgres, Redis, worker/processors, and outbox publishers.  
Running workers manually is for debugging only when not using Compose.

## Related docs

- [Architecture](architecture.md)
- [User flow](user-flow.md)
- [Project structure](project-structure.md)
