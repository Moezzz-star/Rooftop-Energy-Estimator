# ADR-0007: Deterministic CPU sample path; super-resolution and orientation sweep optional

Status: Accepted
Date: 2026-09-30

## Context
The offline demo and tests must run at €0 on CPU without internet (§3). Two notebook features
are expensive or externally coupled: super-resolution (PyTorch OpenSR diffusion needs GPU +
network + telemetry, DEC-22-ref) and the solar orientation brute-force sweep (360 hourly-year
pvlib simulations, DEC-01 context).

## Decision
The default sample workflow is deterministic and CPU-only: fixed default tilt/azimuth for
solar (skip brute-force sweep) and no super-resolution. Both are feature-flagged and
optional: the orientation sweep is available as a coarse opt-in flag; super-resolution is
skipped entirely on the offline CPU path.

## Consequences
+ Reproducible, fast, network-free demo and tests (reproducibility + zero-cost drivers).
+ No GPU or external telemetry dependency in the required path.
- Default solar estimate is not orientation-optimized; documented as an indicative estimate
  (DEC-02 disclaimer) with the sweep available for deeper analysis.
- Super-resolution quality gains are unavailable offline; acceptable for portfolio scope.
