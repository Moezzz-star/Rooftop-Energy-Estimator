# ADR-0002: PostgreSQL as authoritative job state

Status: Accepted
Date: 2026-09-30

## Context
Analyses run as multi-stage async pipelines (§17). Job status, stage progress, retries,
cancellation, failure codes and cleanup status must be durable and queryable by the API.
Redis is present as the Celery broker/result backend but is volatile and transport-oriented.

## Decision
Persist authoritative job state in PostgreSQL via `ProcessingJob` and `JobStage` models.
Redis carries only broker messages and transient task results. Workers write stage
transitions transactionally to PostgreSQL. The API reads state exclusively from PostgreSQL.

## Consequences
+ Job state survives Redis restarts/flushes and worker crashes.
+ Rich querying, auditing, and reproducibility (DEC-09) come for free with relational data.
+ Cancellation and idempotency keys live next to the domain data they guard.
- Extra DB writes per stage transition; negligible at this scale and bounded by stage count.
- Slightly more code than "just use Celery result backend", justified by durability need.
