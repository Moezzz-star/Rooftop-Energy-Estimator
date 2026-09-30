# ADR-0006: Model artifact distributed outside git

Status: Accepted
Date: 2026-09-30

## Context
`unet_buildings.keras` is 90MB (DEC-05, DEC-06). Committing large binaries bloats the repo
and git history and is poor practice for a public portfolio. Tests and CI must still run
without the real model and without network dependence on the sample path (§3).

## Decision
Do not commit the model. Provide a checksummed download script in `scripts/` that fetches
`unet_buildings.keras` from a free host into a git-ignored location, with a clear error when
the model is missing. Ship a tiny randomly-initialized CI test U-Net with the identical
`(256,256,3) -> sigmoid` contract so tests and CI run fast and offline.

## Consequences
+ Small, clean repository; fast clones; no LFS billing concerns.
+ CI runs CPU-only with a tiny model (free-tier friendly, §27).
- New developers must run the download step once (documented in README/Makefile `setup`).
- Download host availability is a setup-time dependency, not a runtime one (offline demo OK).
