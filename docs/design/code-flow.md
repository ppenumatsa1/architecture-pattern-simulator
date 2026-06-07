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

1. `POST /api/microservices/submissions` (submission-api).
2. submission-api stores initial submission + `submission_received` timeline event in Postgres.
3. submission-api publishes message to Redis `submission_requests`.
4. risk-service consumes request, evaluates risk, writes `risk_scored`/`manual_review_requested` timeline events, publishes to `risk_results`.
5. persistence-service consumes `risk_results`, upserts risk summary, updates submission status/version, writes final timeline event.
6. UI reads status and streams events from status-api (`microservices.timeline_events`).

## 3) Event Sourcing + CQRS flow

1. `POST /api/event-sourcing/commands/create-submission` (command-api).
2. command-api appends `submission.created` to `event_store` (optimistic concurrency) and publishes to Redis `domain_events`.
3. risk processor consumes domain event, emits derived events (`risk.scoring.started`, `risk.scored`, decision event) back to event store + Redis.
4. projection processor reads event store sequence and updates:
   - `submission_read_model`
   - `risk_summary_read_model`
   - `timeline_events`
5. query-api serves read endpoints + SSE from projection tables.

## Gateway routing note

Nginx maps `/api/{mode}/...` routes to the correct backend service and disables buffering for SSE endpoints.

## Runtime note

`docker-compose.yml` starts UI, gateway, APIs, Postgres, and Redis.  
Async workers (`microservices/risk-service`, `microservices/persistence-service`) and CQRS processors (`event-sourcing-cqrs/processors`) are available in-repo and can be started separately for full end-to-end async progression.

## Related docs

- [Architecture](architecture.md)
- [User flow](user-flow.md)
- [Project structure](project-structure.md)
