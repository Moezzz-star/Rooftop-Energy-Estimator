# Code Architecture: Rooftop Energy Estimator

Buildable contract for implementation (Phase 2). Modular monolith: Django REST + Celery workers + PostGIS + Redis + storage abstraction. Domain logic lives in explicit **service classes** only — never in views, serializers, tasks, models, or React components. See `docs/decisions/CONTEXT.md` for canonical logic and decisions (DEC-01..09).

---

## 1. Backend layout (`backend/`)

```
backend/
  manage.py
  config/                     # project package (NOT an app)
    settings/{base,dev,prod,test}.py
    urls.py                   # /api/v1/ router include, spectacular views
    celery.py                 # Celery app + autodiscover
    asgi.py  wsgi.py
    logging.py                # structured JSON log config
  apps/
    accounts/  projects/  analyses/  geospatial/
    imagery/   solar/     ml_models/  jobs/  exports/
  common/                     # cross-cutting, NOT domain: base models, errors, pagination, permissions, storage, logging helpers
  tests/                      # integration + e2e-ish API tests
```

Per-app internal shape (only files that app needs):
```
apps/<app>/
  __init__.py  apps.py
  models.py            # persistence only (thin, with invariant methods)
  services.py          # domain services (service classes) — the app's core
  selectors.py         # read queries (optional; keeps services write-focused)
  serializers.py       # DRF (validation + shaping only)
  views.py             # DRF viewsets/APIViews (HTTP only -> call service)
  urls.py
  tasks.py             # Celery: THIN wrappers -> call services
  permissions.py       # object-level perms (where app-specific)
  filters.py           # django-filter FilterSets
  admin.py
  tests/
```

Rule: a Celery task deserializes ids/args, resolves objects, calls a service method, records stage status, and returns. No branching domain logic in tasks.

### App responsibilities

| App | Responsibility | Key models | Key services (class -> method) | Celery tasks |
|-----|----------------|-----------|-------------------------------|--------------|
| `accounts` | AuthN, current user, ownership root | `User` (custom) | `AccountService.register/authenticate` | — |
| `projects` | Project CRUD, ownership boundary (org-ready) | `Project` | `ProjectService.create/archive` | — |
| `analyses` | Analysis lifecycle, immutable snapshot, assumptions, idempotency | `Analysis`, `AnalysisArea`, `AnalysisAssumption` | `AnalysisService.create/submit/snapshot`, `AssumptionResolver.resolve` | — |
| `geospatial` | Geometry validation, area/centroid, vectorize repair, map-ready shaping, buildings/roofs | `Building`, `RoofGeometry` | `GeometryValidationService.validate`, `VectorizationService.mask_to_features`, `BuildingProjectionService` (bbox/simplify) | — |
| `imagery` | Provider registry, upload, metadata, checksum, storage refs | `ImageryAsset` | `ImageryService.register_upload/read_metadata`, `ImageryProviderRegistry` | `ingest_imagery` |
| `solar` | Versioned solar estimation (pvlib), validation | `SolarEstimate`, `CalculationMethodVersion` | `SolarEstimationService.estimate` (wraps `ml.inference.solar`) | — (called inside pipeline) |
| `ml_models` | Model registry metadata, versions, checksums, preproc config | `MLModelVersion` | `ModelRegistryService.active/get/verify_checksum` | — |
| `jobs` | Async orchestration, stage tracking, cancellation, provenance | `ProcessingJob`, `JobStage` | `JobOrchestrator.submit/advance/cancel`, `PipelineRunner.run` | `run_analysis_pipeline` (chains stages) |
| `exports` | GeoJSON/CSV/PDF artifacts, injection-safe CSV, disclaimer | `ExportArtifact` | `ExportService.build_geojson/build_csv/build_pdf` | `generate_export` |
| (audit, in `common` or `analyses`) | Immutable audit log | `AuditEvent` | `AuditService.record` | — |

`jobs.PipelineRunner` is the composition root that calls, in order, imagery -> ml inference -> geospatial vectorization -> geospatial persistence -> solar. It depends on services via constructor injection (testable, no hard singletons).

Dependency direction (no cycles): `accounts` <- `projects` <- `analyses` <- `jobs` -> {`imagery`, `geospatial`, `solar`, `ml_models`, `exports`}. `common` depended on by all; depends on none. `geospatial`/`solar` import pure logic from top-level `ml/`.

---

## 2. `ml/` package layout

Pure, framework-free Python (no Django import). Backend services call into it. Importable + CLI (`python -m ml.<cli>`).

```
ml/
  configs/            # dataclass/YAML configs: preprocess, tiling, inference, training, solar
  preprocessing/
    normalize.py      # percentile_normalize(...)
    tiling.py         # Tiler
  inference/
    predictor.py      # UNetPredictor
    postprocess.py    # mask cleanup
    vectorize.py      # raster mask -> features
    pipeline.py       # InferencePipeline (orchestrates preprocessing->predict->postprocess->vectorize)
    solar.py          # SolarModel (pvlib port) — pure calc, versioned
  training/
    dataset.py  augment.py  train.py (CLI)  callbacks.py
  evaluation/
    metrics.py        # iou, dice, precision, recall, f1, object-level
    evaluate.py (CLI)
  model_registry/
    registry.py       # MLflow-backed load/register/promote; checksum
    interfaces.py     # StorageBackend, ImageryProvider protocols (shared abstractions)
  tests/              # fixtures use tiny CI model (DEC-05)
```

### Key signatures to port (canonical logic from CONTEXT.md)

```python
# ml/preprocessing/normalize.py
def percentile_normalize(
    img: np.ndarray, pmin: float = 2.0, pmax: float = 98.0,
    bands: tuple[int, ...] = (1, 2, 3), eps: float = 1e-6,
) -> np.ndarray: ...  # per-image per-band pctile -> clip[0,1]; guard hi-lo<eps ->0; nan_to_num

# ml/preprocessing/tiling.py
class Tiler:
    def __init__(self, tile: int = 256, stride: int = 128) -> None: ...
    def tiles(self, h: int, w: int) -> list[tuple[int, int]]: ...  # force last start=len-tile
    def stitch(self, preds: list[np.ndarray], coords, shape) -> np.ndarray: ...  # overlap-average

# ml/inference/predictor.py
class UNetPredictor:
    def __init__(self, model, tiler: Tiler, batch_size: int = 16) -> None: ...  # load compile=False
    def predict_prob(self, image: np.ndarray) -> np.ndarray: ...  # windowed, batched -> prob map

# ml/inference/postprocess.py
def cleanup_mask(prob: np.ndarray, threshold: float = 0.2,
                 min_object: int = 8, min_hole: int = 8) -> np.ndarray: ...

# ml/inference/vectorize.py
def mask_to_features(mask: np.ndarray, transform, crs,
                     simplify_tol_m: float, min_area_m2: float = 20.0) -> "gpd.GeoDataFrame": ...
    # rasterio.features.shapes -> shapely -> make_valid -> simplify -> UTM area -> drop<20m2 -> centroid4326

# ml/inference/solar.py  (pure; SolarEstimationService wraps it)
@dataclass(frozen=True)
class SolarInputs:
    roof_area_m2: float; latitude: float; longitude: float; timezone: str
    altitude: float; tilt_deg: float; azimuth_deg: float
    usable_roof_fraction: float; power_density_w_m2: float; system_losses: float; shading: float
class SolarModel:
    version: str
    def estimate(self, x: SolarInputs) -> "SolarResult": ...  # monthly[12]+annual_kwh, kwp, specific_yield
    def _validate(self, x: SolarInputs) -> None: ...  # §15 rules -> ValidationError
```

### Shared abstraction interfaces (`ml/model_registry/interfaces.py`, re-exported to backend `common`)

```python
class StorageBackend(Protocol):
    def save(self, key: str, data: BinaryIO) -> str: ...       # returns storage URI/ref
    def open(self, key: str) -> BinaryIO: ...
    def url(self, key: str, expires: int | None = None) -> str: ...
    def delete(self, key: str) -> None: ...
    def checksum(self, key: str) -> str: ...
# Impls: FilesystemStorage (default), MinioStorage/S3Storage (later) — swap via settings, no domain change.

class ImageryProvider(Protocol):
    name: str
    def read_metadata(self, ref: str) -> "ImageryMetadata": ...   # crs, bounds, res, bands, checksum
    def open_window(self, ref: str, window) -> np.ndarray: ...    # windowed read; never full raster
    def capabilities(self) -> "ProviderCapabilities": ...
# Impls: UploadedRasterProvider (default). Registry lists "available imagery sources" (§19).
```

---

## 3. Data model (15 entities)

SRIDs: all stored geometry in **EPSG:4326** (`geography=False`, `srid=4326`); metric ops via on-the-fly UTM reproject in services (matches `estimate_utm_crs` logic). `BaseModel` in `common`: `id: UUID pk`, `created_at`, `updated_at`.

**Ownership chain:** `User -> Project -> Analysis -> {AnalysisArea, ProcessingJob, Building, SolarEstimate, ExportArtifact}`.

| Entity | Key fields | Geometry (SRID 4326) | FKs | Cascade / cleanup |
|--------|-----------|----------------------|-----|-------------------|
| **User** | `email` unq, `is_active`, `date_joined` | — | — | protect if owns projects |
| **Project** | `name`, `description`, `is_archived` | — | `owner->User` | User delete -> CASCADE |
| **Analysis** | `name`, `status`(draft/queued/running/completed/failed/cancelled), `idempotency_key` unq/user, `submitted_at`, `completed_at` + **snapshot FKs below** | — | `project->Project` | Project delete -> CASCADE; on delete signal -> `ExportService`/storage cleanup |
| **AnalysisArea** | `label` | `area: PolygonField/MultiPolygon` | `analysis` | CASCADE |
| **AnalysisAssumption** | classified inputs: `source`(measured/inferred/user/default/calculated), `usable_roof_fraction`, `power_density_w_m2`, `system_losses`, `module_eff`, `tilt_deg`, `azimuth_deg`, `shading`, `temp_air`, `wind` | — | `analysis` (1:1, frozen) | CASCADE; immutable after submit |
| **ImageryAsset** | `provider`, `storage_key`, `checksum`, `crs`, `resolution_m`, `bounds`, `bands`, `acquired_at` | `footprint: PolygonField` | `analysis` | CASCADE; delete signal -> storage.delete(storage_key) |
| **MLModelVersion** | `name`, `version`, `checksum`, `training_dataset_version`, `preprocess_config`(JSON), `input_resolution`, `signature`(JSON), `metrics`(JSON), `status`(candidate/registered/production/rolled_back), `mlflow_run_id` | — | — | PROTECT (referenced by snapshots; never hard-delete) |
| **CalculationMethodVersion** | `name`(solar), `version`, `parameters`(JSON), `description`, `effective_date` | — | — | PROTECT |
| **ProcessingJob** | `status`, `celery_task_id`, `worker_info`(JSON), `provenance`(JSON: code_commit, imagery_checksum, model_checksum, preproc, inference settings), `queued_at`, `started_at`, `finished_at`, `error`(JSON) | — | `analysis` (1:1) | CASCADE |
| **JobStage** | `name`(enum §7), `sequence`, `status`(pending/running/succeeded/failed/skipped), `started_at`, `finished_at`, `duration_ms`, `detail`(JSON) | — | `job` | CASCADE |
| **Building** | `confidence`, `area_m2`, `index` | `geometry: PolygonField`, `centroid: PointField` | `analysis` | CASCADE (bulk) |
| **RoofGeometry** | `tilt_deg`, `azimuth_deg`, `usable_area_m2`, `source` | `geometry: PolygonField` | `building` (1:1) | CASCADE |
| **SolarEstimate** | `capacity_kwp`, `annual_kwh`, `monthly_kwh`(JSON[12]), `specific_yield`, `usable_area_m2`, `inputs`(JSON classified), `disclaimer` | — | `building`, `calculation_version->CalculationMethodVersion(PROTECT)` | CASCADE from building |
| **ExportArtifact** | `kind`(geojson/csv/pdf), `storage_key`, `checksum`, `bytes`, `status` | — | `analysis` | CASCADE; delete signal -> storage.delete |
| **AuditEvent** | `action`, `actor_email`(denormalized), `target_type`, `target_id`, `metadata`(JSON), `at` | — | `actor->User (SET_NULL)` | **retained independently** (DEC-03); not cascade-deleted with project |

**Immutable snapshot (Analysis, DEC-09):** on `submit`, `AnalysisService.snapshot()` freezes FKs `model_version`, `calculation_version`, 1:1 `AnalysisAssumption`, and `snapshot`(JSON: code_commit, imagery metadata, processing config). These fields become read-only; re-open reproduces identical numbers. Snapshot references use `PROTECT` so versions can't be deleted out from under a completed analysis.

---

## 4. REST API (`/api/v1/`)

DRF, JWT auth, all endpoints require auth except health + auth/login/register. Object-level permission `IsOwner` (via project/analysis ownership) on every resource. django-filter for filtering/ordering; cursor or page-number pagination (page size default 25, max 200). drf-spectacular generates OpenAPI -> typed frontend client (§19). Consistent error envelope (§6). Unbounded GeoJSON avoided (see notes).

| # | Method | Path | Auth | Notes |
|---|--------|------|------|-------|
| 1 | POST | `/auth/login/` | public | JWT obtain |
| 2 | POST | `/auth/refresh/` | public | JWT refresh |
| 3 | POST | `/auth/register/` | public | create user |
| 4 | GET | `/me/` | user | current user |
| 5 | GET/POST | `/projects/` | owner | list(filter name,archived; order created)/create |
| 6 | GET/PATCH/DELETE | `/projects/{id}/` | owner | DELETE cascades + cleanup |
| 7 | GET/POST | `/projects/{id}/analyses/` | owner | list/create (draft) |
| 8 | GET/PATCH/DELETE | `/analyses/{id}/` | owner | detail/edit-draft/delete |
| 9 | POST | `/analyses/{id}/submit/` | owner | **Idempotency-Key header required**; enqueues job; returns 202 + job |
| 10 | POST | `/geometry/validate/` | user | validate GeoJSON polygon(s); returns validity/area/repairs |
| 11 | POST | `/analyses/{id}/imagery/` | owner | multipart upload -> ImageryAsset |
| 12 | GET | `/imagery/{id}/` | owner | imagery metadata |
| 13 | GET | `/imagery/sources/` | user | available imagery providers + capabilities |
| 14 | GET | `/analyses/{id}/job/` | owner | job status + stages (progress) |
| 15 | POST | `/analyses/{id}/job/cancel/` | owner | cancel running job |
| 16 | GET | `/analyses/{id}/results/` | owner | result summary (counts, totals, disclaimer) |
| 17 | GET | `/analyses/{id}/buildings/` | owner | **paginated**; filter bbox, min_area, confidence; order area; geometry omitted or simplified |
| 18 | GET | `/buildings/{id}/` | owner | full building + roof + solar estimate |
| 19 | GET | `/analyses/{id}/features/` | owner | **map-ready GeoJSON, bounded**: required `bbox` + zoom-dependent `simplify`, capped feature count, else 400 |
| 20 | GET/POST | `/analyses/{id}/exports/` | owner | list / request export (kind) -> async artifact |
| 21 | GET | `/exports/{id}/` | owner | status + signed download URL |
| 22 | GET | `/models/` | user | list MLModelVersion metadata (production/active) |
| 23 | GET | `/models/{id}/` | user | model card / metadata |
| 24 | GET | `/health/` | public | liveness |
| 25 | GET | `/health/ready/` | public | readiness (db, redis, storage, model present) |

**Endpoint count: 25** (distinct method+path routes; some share a path).

**Bounding unbounded GeoJSON:** (a) `/buildings/` returns tabular paginated rows with geometry excluded by default (`?geometry=simplified` opt-in, still paginated); (b) `/features/` requires a `bbox` and applies zoom-dependent `ST_SimplifyPreserveTopology`, hard cap N features per response (paged by bbox tiles); (c) full dataset only via downloadable `ExportArtifact` (GeoJSON/CSV file). Vector tiles are a future option, not P0.

---

## 5. Frontend layout (`frontend/src/`)

```
api/        # generated OpenAPI client + typed hooks wrappers (TanStack Query)
schemas/    # Zod schemas (mirror DTOs); single source for RHF validation
types/      # shared TS types (many re-exported from generated client)
components/ # dumb/presentational reusable UI (MUI)
features/   # feature slices: auth, projects, analyses, wizard, map, results, exports
  <feature>/{components,hooks,api.ts,routes.tsx}
pages/      # route-level page composition
maps/       # MapLibre GL setup, layers, draw controls, style, bbox/zoom helpers
hooks/      # cross-cutting hooks (useAuth, usePolling)
theme/      # MUI theme
```

State approach: **TanStack Query** owns all server state (queries + mutations, cache keyed by resource id, polling for job status via `/analyses/{id}/job/`). **React Hook Form + Zod** for all forms (project create, analysis wizard, assumption editing) with `zodResolver`. No global client-state library beyond React context for auth/session. Zod schemas are the validation contract; keep aligned with backend serializers (ideally generated). Maps hold ephemeral local state only.

---

## 6. Coding conventions

**Python:** 3.12, full type hints. Ruff (lint+format) and mypy `strict` on `backend/` and `ml/`. No logic in views/serializers/tasks/models (§5) — services only. Services are classes with dependencies injected via `__init__` (testability). Pure geo/ML logic in `ml/` (no Django import). Naming: modules `snake_case`, classes `PascalCase`, service methods verbs (`create`, `estimate`, `run`). One public service class per concern; narrow public methods; private helpers `_prefixed`.

**TypeScript:** strict mode, ESLint + Prettier, no `any` (use generated types/Zod inferred). Components `PascalCase`, hooks `useX`, files match default export. Presentational components in `components/`, data-fetching only in feature hooks/`api`.

**Error handling:** domain errors in `common/errors.py`: `DomainError` -> `ValidationError`, `NotFoundError`, `ConflictError`, `PermissionDeniedError`, `InfrastructureError`. Services raise domain errors; a DRF exception handler maps them to a **consistent envelope** `{ "error": { "code", "message", "details" } }` with proper HTTP status. Map infra/library errors (rasterio, pvlib, storage) to `InfrastructureError` at the boundary. Never swallow errors; log with context before re-raise. Pipeline stage failures recorded on `JobStage` with `detail`, job -> `failed`, temp files cleaned in `finally`.

**Logging:** structured JSON (`config/logging.py`), OpenTelemetry-friendly. Required fields: `timestamp, level, logger, message, trace_id, analysis_id?/job_id?, stage?`. Levels: DEBUG dev-only detail; INFO lifecycle transitions (submit, stage start/finish, promote); WARNING recoverable (missing optional imagery source, fallback path); ERROR handled failures with context; no PII beyond user email in audit. Metrics via Prometheus (job durations, stage timings) behind optional compose profile.

**Testing:** pytest + pytest-django. Unit: services + `ml/` pure functions (mock `StorageBackend`/`ImageryProvider`/model via tiny CI U-Net, DEC-05). Integration: API endpoints (auth, permissions, pagination, idempotency), DB + PostGIS. E2E: Playwright critical path (create project -> draw area -> upload -> submit -> poll -> results -> export). Coverage target 80% backend/ml, meaningful over exhaustive. Frontend: Vitest + RTL for hooks/components; Zod schema tests.

---

## 7. Processing pipeline stages -> `JobStage` names

`PipelineRunner.run` executes these in order; each maps to a `JobStage.name` (shared enum used by backend and frontend progress UI). Names are the machine keys; timings recorded per stage.

```
VALIDATE_REQUEST        (§13.1)
READ_IMAGERY_METADATA   (§13.2)
NORMALIZE_IMAGERY       (§13.3)  percentile_normalize (two-pass for windows)
SUPER_RESOLUTION        (§13.4)  optional, feature-flagged, skipped on sample path
READ_RASTER_WINDOWS     (§13.5)  windowed reads, no full-raster load
TILE_IMAGERY            (§13.6)  Tiler tile=256 stride=128
PREPROCESS_TILES        (§13.7)  model-specific preproc from model metadata
RUN_INFERENCE           (§13.8)  batched UNetPredictor
REASSEMBLE_PREDICTIONS  (§13.9)  overlap-average stitch
THRESHOLD               (§13.10) 0.2
MORPHOLOGY_CLEANUP      (§13.11) remove_small_objects/holes
FILTER_COMPONENTS       (§13.12) drop area<20m2
VECTORIZE               (§13.13) shapes -> shapely -> gdf
REPAIR_GEOMETRY         (§13.14) make_valid/buffer(0)
SIMPLIFY_POLYGONS       (§13.15) bounded tolerance
CALCULATE_AREAS         (§13.16) UTM reproject
AGGREGATE_CONFIDENCE    (§13.17)
PERSIST_ARTIFACTS       (§13.18) Buildings/RoofGeometry + imagery/mask artifacts
RUN_SOLAR_ESTIMATION    (§13.19) SolarEstimationService per building (fixed tilt/azimuth default)
PUBLISH_RESULTS         (§13.20) mark analysis completed + snapshot finalized
```

Frontend `features/analyses` maps these keys to labels + a progress bar driven by polling `/analyses/{id}/job/`.

---

## 8. Design patterns & rationale

| Concern | Pattern | Why |
|--------|---------|-----|
| Domain logic isolation | Service layer | §5 mandate; keeps views/tasks thin, testable |
| Storage / imagery | Strategy + Registry behind Protocol | swap filesystem<->MinIO/S3 and add providers without touching domain (§4 storage) |
| Read queries | Selectors | separate reads from write services; cleaner services |
| Pipeline | Pipeline/Chain via `PipelineRunner` + stage records | explicit stages, per-stage timing/failure, resumable reasoning |
| Model access | Registry (MLflow-backed) | versioning, checksum, promotion/rollback (§14) |
| Snapshot | Memento (frozen FKs+JSON) | immutable, reproducible analyses (DEC-09) |
| Idempotency | Idempotency-Key + unique constraint | safe analysis re-submit (§19) |
| Errors | Domain error hierarchy + boundary mapping | consistent API envelope, no infra leakage |

Anti-patterns avoided: no domain logic in views/serializers/tasks/models/components; no God pipeline service (composition via injected services); no interface explosion (Protocols only for storage/imagery/provider — the things that actually vary); no empty scaffolding dirs (DEC/§6).
