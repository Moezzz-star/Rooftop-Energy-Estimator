# ADR-0005: Optional Docker Compose profiles for MLOps and observability

Status: Accepted
Date: 2026-09-30

## Context
MLflow, Prometheus, Grafana, and tracing add real value but also RAM/CPU cost. The base
platform must start with `docker compose up --build` and stay light for a laptop (§4, §26),
while the extras remain available for a fuller portfolio demonstration.

## Decision
Keep the BASE profile to the six core services (frontend, api, worker, db, redis, storage).
Put MLflow behind `--profile mlops` and Prometheus/Grafana/OTel/Tempo behind
`--profile observability`. Optional S3 (MinIO) behind `--profile storage-s3`. None are
required for the core workflow, automated tests, or the demo.

## Consequences
+ Minimal default footprint; fast, cheap local startup (zero-cost driver).
+ Reviewers can opt into observability/MLOps with a single flag.
- Two ways to run the stack must be documented (README/Makefile) and kept in sync.
- Observability of the base run relies on structured JSON logs until a profile is enabled.
