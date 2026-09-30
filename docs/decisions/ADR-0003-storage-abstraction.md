# ADR-0003: Storage abstraction — filesystem default, S3-compatible later

Status: Accepted
Date: 2026-09-30

## Context
Rasters, masks, and export artifacts must be stored. The zero-cost/offline constraint (§3)
favors the filesystem, but §4 and DEC-07 require the ability to move to S3-compatible object
storage (MinIO/S3) later without changing domain logic.

## Decision
Define an `ObjectStorage` interface (save/open/read_bytes/exists/delete/url/list/copy) using
opaque logical keys. Provide `FilesystemStorage` (default, `MEDIA_ROOT`) and `S3Storage`
(boto3, works with MinIO or any S3-compatible endpoint). Backend selected via
`STORAGE_BACKEND` env. Domain services depend only on the interface.

## Consequences
+ Core workflow runs at €0 on the filesystem; no object-store dependency for demo/tests.
+ Switching to MinIO/S3 is a config + adapter change, zero domain edits.
+ Presigned-URL semantics abstracted behind `url()` so the frontend contract is stable.
- Filesystem adapter must emulate a flat key space over directories; minor complexity.
- Some S3-only features (versioning, lifecycle) are not exposed by the common interface.
