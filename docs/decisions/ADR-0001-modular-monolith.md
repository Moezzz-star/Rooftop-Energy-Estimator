# ADR-0001: Modular monolith over microservices

Status: Accepted
Date: 2026-09-30

## Context
Zero-cost, single-developer portfolio project (§3) that must run offline on one machine.
The requirements (§5, DEC-07) call for clear separation of concerns but explicitly forbid
unnecessary microservices, Kafka, or required Kubernetes.

## Decision
Build one Django deployable (the "modular monolith") with internal module boundaries per
domain (accounts, projects, analyses, geospatial, imagery, solar, ml_models, jobs, exports)
and offload heavy work to Celery workers. Boundaries are enforced by app/package structure
and explicit domain services + provider interfaces, not by network splits.

## Consequences
+ Simple local startup, one codebase, one CI pipeline, cheap to run and reason about.
+ Domain seams already drawn, so extraction to services later is possible if ever needed.
- Shared process/deploy: a bad dependency can affect the whole app; mitigated by module
  discipline and async isolation of heavy tasks.
- Horizontal scale is coarse-grained (scale workers/API replicas), acceptable for the
  stated scope (no hypothetical future scale — anti-pattern avoided).
