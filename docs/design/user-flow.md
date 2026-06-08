# User Flow

## Demo flow (end user)

1. Open simulator UI.
2. Select architecture mode: **Monolith**, **Microservices**, or **Event Sourcing + CQRS**.
3. Fill submission form (applicant, policy type, coverage, notes).
4. Submit request.
5. Observe:
   - accepted response with submission ID,
   - live timeline updates in Event Log (SSE),
   - connection state changes (connecting/connected/reconnecting).
6. Refresh Data View to inspect current persisted/projection state.
7. Switch mode and repeat with same business scenario for comparison.

## Contributor flow (quick validation)

1. Start stack (`docker compose up`).
2. Compose starts workers/processors/outbox publishers automatically.
3. (Optional, debug-only) run workers manually outside Compose:
   - `./.venv/bin/python microservices/risk-service/worker.py`
   - `./.venv/bin/python microservices/persistence-service/worker.py`
   - `./.venv/bin/python microservices/outbox-publisher/worker.py`
   - `./.venv/bin/python event-sourcing-cqrs/processors/risk_processor.py`
   - `./.venv/bin/python event-sourcing-cqrs/processors/projection_processor.py`
4. Submit one request per mode from UI.
5. Confirm expected timeline sequence:
   - submission received,
   - risk scored,
   - manual review requested or decision made.
6. Verify SSE remains alive during idle periods (keep-alive comments or done event behavior per mode).
7. Verify data endpoint output aligns with that mode’s source-of-truth model.

## Related docs

- [Architecture](architecture.md)
- [Code flow](code-flow.md)
- [Tech stack](tech-stack.md)
