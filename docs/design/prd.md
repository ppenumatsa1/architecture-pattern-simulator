# Product Requirements (PRD)

## Product

**Architecture Pattern Simulator** for insurance submissions.

## Problem

Teams discuss architecture trade-offs abstractly. This simulator provides one business flow implemented three ways so users can compare behavior, complexity, and data movement.

## Primary users

- Engineers learning architecture patterns.
- Contributors extending simulator services/UI.
- Demo facilitators explaining trade-offs.

## Goals

1. Submit one form and run it through monolith, microservices, or event-sourcing mode.
2. Show near-real-time timeline updates via SSE.
3. Display final data snapshot per mode.
4. Make service boundaries and data ownership explicit.

## Functional requirements

- Mode selector in UI (monolith, microservices, event-sourcing).
- Submission endpoint per mode.
- Streaming timeline endpoint per mode.
- Read/data endpoint per mode.
- Redis-backed async pipelines for microservices and event processors.
- Postgres persistence for operational and projection data.

## Non-goals

- Production-grade auth/multi-tenant controls.
- Full workflow engine.
- Perfect feature parity across patterns beyond core comparison flow.

## Success criteria (demo)

- A user can complete the end-to-end flow in each mode from one UI session.
- Event log visibly updates from SSE in each mode.
- Contributors can map a UI action to backend tables/streams quickly.

## Related docs

- [Architecture](architecture.md)
- [User flow](user-flow.md)
- [Code flow](code-flow.md)
