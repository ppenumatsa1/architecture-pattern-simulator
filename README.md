# Architecture Pattern Simulator (Insurance Submission POC)

Compare the same insurance-submission business flow across:

1. **Monolith**
2. **Microservices**
3. **Event Sourcing + CQRS**

The simulator is designed for demos, architecture discussions, and hands-on learning of trade-offs in data ownership, event flow, and consistency.

## Project goals

- Run one business scenario in three architecture styles.
- Observe timeline updates via SSE.
- Inspect persisted/read-model state for each style.
- Keep implementations comparable so trade-offs are explicit.

## Insurance flow (high-level)

This simulator runs the same insurance submission journey in all three architecture modes:

1. A user submits an application with applicant details and underwriting signals.
2. The system records intake and emits timeline/progress events.
3. Risk scoring evaluates the submission using deterministic rules.
4. A decision is derived from risk level:

- low risk: approved
- medium risk: under_review (manual review path)
- high/critical risk: rejected (mode-specific mapping)

5. The latest decision and risk summary are persisted in each mode's read path.
6. The UI polls/streams updates and shows the evolving timeline and current state.

For detailed behavior and sequence-by-sequence flow, see:

- [User flow](docs/design/user-flow.md)
- [Code flow](docs/design/code-flow.md)
- [Architecture](docs/design/architecture.md)
- [Docs index](docs/README.md)

## Architecture pattern comparison (summary)

| Pattern               | Core shape                                                                                                   | Strengths                                                                                    | Trade-offs                                                                            | Best fit                                                                          |
| --------------------- | ------------------------------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------- |
| Monolith              | One API owns command + read + persistence in one deployable                                                  | Simple deploy/debug, single transaction boundary, straightforward local dev                  | Tight coupling, lower service independence, harder independent scaling                | Small teams, early-stage products, low operational overhead goals                 |
| Microservices         | Submission intake, risk processing, persistence, and status reads split by service with Redis async handoffs | Clear service boundaries, realistic async decoupling, independent deploy/scale opportunities | More moving parts, idempotency/retry complexity, operational coordination cost        | Teams needing service autonomy and explicit async processing boundaries           |
| Event Sourcing + CQRS | Commands append immutable events; processors build read models; query side serves projections                | Immutable audit trail, replay-friendly history, explicit write/read separation               | Highest cognitive load, projection lag handling, event/versioning discipline required | Domains needing strong auditability, temporal debugging, and evolution via replay |

## Prerequisites

- Docker + Docker Compose
- Python 3.12 with local venv at `./.venv` (used by `make`)
- Node.js 20+ (for local UI lint/test)

Optional local Python bootstrap (if `./.venv` is missing):

```bash
python3.12 -m venv .venv
./.venv/bin/pip install -U pip
./.venv/bin/pip install ruff pytest fastapi uvicorn pydantic sqlalchemy "psycopg[binary]" redis
```

## Quick start (Docker Compose)

```bash
cp .env.example .env
docker compose up --build -d
```

Open the simulator through the gateway:

- UI + routed APIs: `http://localhost:8080`

Useful direct service ports are defined in `.env.example`.

Stop everything:

```bash
docker compose down
```

`docker compose down` keeps named volumes so Postgres/Redis data persists.
To reset all data intentionally, use:

```bash
docker compose down -v
```

## Demo walkthrough

1. Start stack:

```bash
docker compose up --build
```

2. Open `http://localhost:8080`.
3. Run quick API smoke checks (per-mode payloads and `curl` commands):

- see [docs/manual-testing.md](docs/manual-testing.md)

4. For **Microservices** and **Event Sourcing + CQRS**, start workers/processors if you want full async progression:

```bash
./.venv/bin/python microservices/risk-service/worker.py
./.venv/bin/python microservices/persistence-service/worker.py
./.venv/bin/python event-sourcing-cqrs/processors/risk_processor.py
./.venv/bin/python event-sourcing-cqrs/processors/projection_processor.py
```

5. Re-run submissions in each mode and compare timelines + final state in the UI.

## Endpoint matrix (gateway-facing)

All endpoints below are available through `http://localhost:8080`.

| Mode                  | Submit                                                | Read current state                                         | SSE timeline                                                | Health                                                                      |
| --------------------- | ----------------------------------------------------- | ---------------------------------------------------------- | ----------------------------------------------------------- | --------------------------------------------------------------------------- |
| Monolith              | `POST /api/monolith/submissions`                      | `GET /api/monolith/submissions/{submissionId}`             | `GET /api/monolith/submissions/{submissionId}/events`       | `GET /api/monolith/health`                                                  |
| Microservices         | `POST /api/microservices/submissions`                 | `GET /api/microservices/submissions/{submissionId}/status` | `GET /api/microservices/submissions/{submissionId}/events`  | `GET /api/microservices/health` (submission API)                            |
| Event Sourcing + CQRS | `POST /api/event-sourcing/commands/create-submission` | `GET /api/event-sourcing/projections/{submissionId}`       | `GET /api/event-sourcing/submissions/{submissionId}/events` | `GET /api/event-sourcing/commands/health`, `GET /api/event-sourcing/health` |

### Request payload note (current implementation)

- Monolith submit expects `applicantId` + `payload`.
- Microservices submit expects `applicant_id` + `payload`.
- Event-sourcing command submit expects `applicantId` + `payload` (optional `correlationId`).

## Source of truth by mode

- **Monolith:** operational tables in `monolith.*` (`submissions`, `risk_results`, `timeline_events`).
- **Microservices:** operational status in `microservices.submissions`, risk summary in `microservices.risk_results`, timeline in `microservices.timeline_events`.
- **Event Sourcing + CQRS:** immutable write source in `event_sourcing.event_store`; query source in projection tables (`submission_read_model`, `risk_summary_read_model`, `timeline_events`).

See schema SQL in `infra/postgres/*.sql`.

## Microservices role split (why multiple services exist)

- **Submission API**: accepts requests, writes initial submission row, emits `submission_received`, and publishes to Redis `submission_requests`.
- **Risk Service**: consumes `submission_requests`, runs risk rules, emits risk timeline events, and publishes normalized outcomes to Redis `risk_results`.
- **Persistence Service**: consumes `risk_results`, updates submission status/version, upserts risk summary, and writes final timeline decisions.
- **Status API**: read-only facade for dashboard/status/SSE against `microservices.*` tables.

This split is intentional: write-side async workers handle transitions, while Status API stays focused on read + stream concerns.

## SSE timeline behavior

- **Monolith** and **Microservices** SSE endpoints poll every second and emit:
  - event frames for newly persisted timeline events
  - `: keep-alive` comments when no new events are available
- **Event Sourcing + CQRS** query SSE also polls every second, but ends with `event: done` after ~30 idle cycles.

UI event normalization accepts `type`, `eventType`, or `status` fields from stream payloads.

## Quality commands

From repository root:

```bash
make lint
make format
make test
```

These run:

- Python: Ruff + pytest
- UI: ESLint + Vitest

## Troubleshooting

- **`make lint` / `make test` fails with missing `./.venv/bin/python`:**
  create `.venv` and install dependencies (see prerequisites).
- **UI mode appears accepted but state/events do not progress in async modes:**
  run microservice workers + CQRS processors locally (commands above).
- **SSE appears idle:** keep-alive comments are expected in monolith/microservices when no new rows exist.
- **Event-sourcing stream closes:** expected after idle timeout (`event: done`), reconnect to resume.
- **Route mismatch issues:** always use gateway paths (`/api/...`) instead of direct container hostnames.
- **When debugging route behavior:** verify service behavior directly on ports `8000`-`8004` and then retest through gateway `:8080`.

## Additional docs and agent guidance

- Design docs index: [`docs/README.md`](docs/README.md)
- Human/agent collaboration guide: [`AGENTS.md`](AGENTS.md)
- Copilot repository instructions: [`.github/copilot-instructions.md`](.github/copilot-instructions.md)
