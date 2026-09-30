# ADR-0004: Celery queue separation — orchestration vs cpu-heavy

Status: Accepted
Date: 2026-09-30

## Context
The pipeline mixes lightweight coordination with CPU-intensive raster/U-Net/pvlib work
(§17). Running everything on one queue lets heavy tasks starve coordination and makes memory
control hard. The default path must work on CPU with no GPU (§3, §17).

## Decision
Use two Celery queues: `orchestration` (fast, higher concurrency: sequencing, progress
aggregation, cleanup) and `cpu-heavy` (bounded concurrency: raster processing, U-Net
inference, vectorization, pvlib, exports). Reserve a `gpu` queue name for the future but keep
the default CPU-only. Apply per-task soft/hard time limits and memory-bounded batching.

## Consequences
+ Coordination stays responsive under heavy load; memory is capped per worker.
+ Clear scaling lever: add cpu-heavy workers independently.
+ GPU path can be added later without redesign.
- Two queues add a little config/ops surface; acceptable and documented in the Makefile/env.
