# Manual API Smoke Tests

Use this as a short runbook for manual verification across architecture modes.

## 1. Start services

```bash
cp .env.example .env
docker compose up --build -d
```

Use direct service ports for deterministic API smoke tests:

- Monolith: `http://localhost:8000`
- Microservices submission API: `http://localhost:8001`
- Microservices status API: `http://localhost:8002`
- Event-sourcing command API: `http://localhost:8003`
- Event-sourcing query API: `http://localhost:8004`

Use gateway (`http://localhost:8080`) for UI and integrated browsing.

## 2. Monolith

```bash
curl -sS -X POST http://localhost:8000/submissions \
  -H 'content-type: application/json' \
  -d '{"applicantId":"manual-mono","payload":{"income":75000,"age":35}}'
```

Expected: JSON with `submission_id` and `state`.

## 3. Microservices

```bash
curl -sS -X POST http://localhost:8001/submissions \
  -H 'content-type: application/json' \
  -d '{"applicant_id":"manual-micro","payload":{"income":55000,"age":40}}'
```

Expected: JSON with `status=accepted` and `submissionId`.

## 4. Event Sourcing + CQRS

```bash
curl -sS -X POST http://localhost:8003/commands/create-submission \
  -H 'content-type: application/json' \
  -d '{"applicantId":"manual-es","payload":{"income":90000,"age":28}}'
```

Expected: JSON with `status=accepted`, `submissionId`, and `eventId`.

Gateway spot-check example:

```bash
curl -sS http://localhost:8080/api/monolith/health
```

## 5. Optional async progression (full flow)

Docker Compose already starts all workers/processors/outbox publishers.

Run these locally in separate terminals only for debugging outside Compose:

```bash
./.venv/bin/python microservices/risk-service/worker.py
./.venv/bin/python microservices/persistence-service/worker.py
./.venv/bin/python microservices/outbox-publisher/worker.py
./.venv/bin/python event-sourcing-cqrs/processors/risk_processor.py
./.venv/bin/python event-sourcing-cqrs/processors/projection_processor.py
./.venv/bin/python event-sourcing-cqrs/processors/outbox_publisher.py
```

Then submit again in each mode and compare timeline + state in the UI.

## 6. Stop

```bash
docker compose down
```
