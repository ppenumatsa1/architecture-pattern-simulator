# Tech Stack

## Application

- **Frontend**: React 18, TypeScript, Vite.
- **API services/workers**: Python 3.12.
- **Web framework**: FastAPI + Uvicorn.
- **Validation/models**: Pydantic.
- **Data access**: SQLAlchemy + psycopg.

## Data & messaging

- **PostgreSQL 16**: persistent storage for monolith, microservices, and event-sourcing schemas.
- **Redis 7 (Streams)**: asynchronous transport (`submission_requests`, `risk_results`, `domain_events`).

## Edge/routing

- **Nginx** gateway: mode-aware API routing and SSE proxy settings (buffering disabled on event streams).

## Container/runtime

- **Docker Compose** orchestrates postgres, redis, APIs, UI, and gateway.

## Why this stack for the simulator

- FastAPI + SQLAlchemy keeps Python services simple and comparable.
- Redis Streams adds realistic async boundaries without heavy broker setup.
- Postgres supports both transactional tables and event-store/projection patterns.

## Related docs

- [Architecture](architecture.md)
- [Project structure](project-structure.md)
- [Code flow](code-flow.md)
