You are acting as a principal full-stack engineer, ML engineer, geospatial engineer, MLOps engineer, security engineer, DevOps engineer, and product designer.

Your task is to design and implement a complete portfolio project named:

Rooftop Energy Estimator

The application estimates how much photovoltaic energy building rooftops could generate from aerial or satellite imagery.

Treat this as a serious production-style portfolio project, but optimize the architecture for:

- zero mandatory cost,
- local execution,
- maintainability,
- reproducibility,
- demonstrability,
- security,
- testability,
- and efficient implementation.

Do not build a superficial prototype.

The final application must provide a complete working user journey using real local processing, deterministic sample data, and free open-source tools.

# 1. Core objective

Build a web application where a user can:

1. Create an account and sign in.
2. Create a solar-analysis project.
3. Search for a location or navigate an interactive map.
4. Select an analysis zone by:
   - drawing a polygon,
   - drawing a rectangle,
   - uploading GeoJSON,
   - or uploading a GeoTIFF.
5. Configure bounded solar-analysis assumptions.
6. Submit the analysis.
7. Monitor real backend processing progress.
8. View detected rooftop polygons on an interactive map.
9. Inspect solar estimates for the complete zone.
10. Select individual buildings and inspect their estimates.
11. View monthly and annual production charts.
12. Download a PDF report, CSV results, and GeoJSON polygons.
13. Reopen previous analyses.
14. Delete projects and associated artifacts.

The results must always be described as engineering estimates, not bankable photovoltaic yield studies.

# 2. Existing ML pipeline

The existing proof of concept uses the following pipeline:

satellite or aerial imagery
    ↓
optional super-resolution
    ↓
U-Net building segmentation
    ↓
building mask
    ↓
roof polygons
    ↓
roof area
    ↓
PV capacity
    ↓
monthly and annual energy estimates

The existing notebooks include:

- Run_Super_Resolution.ipynb
- building_segmentation_training_kaggle_full.ipynb
- segmentation_training_from_zip_kaggle.ipynb
- segmentation_inference_pv_estimation_kaggle.ipynb
- pv_estimation.ipynb

The existing model artifact is:

- unet_buildings.keras

The existing training configuration is:

- segmentation_training_config.json

Do not execute notebook files as part of the production application.

Extract reusable notebook logic into typed, importable, testable Python modules and command-line entry points.

Preserve correct existing logic where practical. Do not rewrite working components only for stylistic reasons.

# 3. Mandatory zero-cost constraint

This is a personal portfolio project.

The complete core application must:

- cost €0 to run locally,
- use only free and open-source software,
- require no payment details,
- require no cloud account,
- require no commercial API,
- require no paid geospatial or satellite imagery,
- require no hosted database,
- require no hosted object storage,
- require no commercial monitoring service,
- require no GPU,
- and remain demonstrable without internet access after setup.

External open-data integrations may be supported optionally, but they must not be required for the sample workflow, automated tests, or project demonstration.

Do not use or require:

- Google Maps,
- Google Earth Engine paid services,
- Mapbox paid services,
- commercial geocoding,
- commercial satellite imagery,
- AWS services,
- Azure services,
- Google Cloud services,
- Datadog,
- New Relic,
- Dynatrace SaaS,
- Splunk Cloud,
- Sentry SaaS,
- paid CI services,
- or paid security scanners.

Free cloud tiers may be documented as optional deployment alternatives, but the project must not depend on their availability.

Do not provision infrastructure that could generate charges.

# 4. Technology stack

Use the following stack unless an existing repository constraint makes an alternative necessary.

## Backend

- Python 3.12
- Django
- Django REST Framework
- GeoDjango
- PostgreSQL
- PostGIS
- Celery
- Redis
- django-filter
- drf-spectacular
- Gunicorn

## Frontend

- React
- TypeScript with strict mode
- Vite
- Material UI
- MapLibre GL JS
- TanStack Query
- React Hook Form
- Zod
- Recharts
- Vitest
- React Testing Library
- Playwright

## Machine learning

- TensorFlow and Keras
- NumPy
- Pandas
- scikit-learn
- scikit-image
- OpenCV

## Geospatial processing

- rasterio
- GeoPandas
- Shapely
- pyproj
- GDAL

## Solar modeling

- pvlib

## MLOps

- MLflow for local experiment tracking and model registration
- DVC for dataset and artifact versioning when it adds practical value
- Git for code versioning

## Storage

- filesystem storage as the simplest default, or
- MinIO when object-storage behavior is needed

All storage access must be implemented through an abstraction that can support S3-compatible storage later without changing domain logic.

## Observability

Use only self-hosted open-source components:

- structured JSON logging,
- OpenTelemetry,
- Prometheus,
- Grafana,
- and optional Jaeger or Grafana Tempo.

Observability services should use optional Docker Compose profiles to reduce local resource usage.

## Security and quality

Use:

- Ruff
- mypy
- ESLint
- Prettier
- pytest
- pytest-django
- Bandit
- pip-audit
- npm audit
- Gitleaks
- Trivy
- OWASP ZAP where appropriate

# 5. Architecture principles

Build a modular monolith with asynchronous workers.

Do not create unnecessary microservices.

Use this high-level architecture:

React and MapLibre
        |
        v
Django REST API
        |
        +--- PostgreSQL and PostGIS
        |
        +--- Redis
        |
        +--- Celery workers
        |       |
        |       +--- image processing
        |       +--- U-Net inference
        |       +--- polygon extraction
        |       +--- pvlib calculation
        |       +--- report generation
        |
        +--- filesystem or MinIO
        |
        +--- MLflow
        |
        +--- Prometheus and Grafana

Separate these concerns:

- HTTP and API handling
- authentication and authorization
- domain logic
- database persistence
- imagery-provider integration
- raster processing
- model inference
- geospatial processing
- solar calculations
- asynchronous orchestration
- exports
- observability
- frontend presentation

Do not place domain logic directly inside:

- Django views,
- serializers,
- Celery task functions,
- React components,
- or database models.

Use explicit domain services and provider interfaces.

# 6. Repository structure

Use a monorepo with approximately this structure:

/
├── backend/
│   ├── config/
│   ├── apps/
│   │   ├── accounts/
│   │   ├── projects/
│   │   ├── analyses/
│   │   ├── geospatial/
│   │   ├── imagery/
│   │   ├── solar/
│   │   ├── ml_models/
│   │   ├── jobs/
│   │   └── exports/
│   ├── tests/
│   └── manage.py
├── frontend/
│   ├── src/
│   │   ├── api/
│   │   ├── components/
│   │   ├── features/
│   │   ├── pages/
│   │   ├── maps/
│   │   ├── hooks/
│   │   ├── schemas/
│   │   ├── theme/
│   │   └── types/
│   └── tests/
├── ml/
│   ├── training/
│   ├── inference/
│   ├── preprocessing/
│   ├── evaluation/
│   ├── model_registry/
│   ├── configs/
│   └── tests/
├── sample-data/
├── infrastructure/
│   ├── docker/
│   ├── kubernetes/
│   └── terraform-examples/
├── docs/
│   ├── architecture/
│   ├── methodology/
│   ├── security/
│   ├── operations/
│   └── decisions/
├── scripts/
├── .github/workflows/
├── docker-compose.yml
├── Makefile
├── README.md
├── CONTRIBUTING.md
├── SECURITY.md
├── COSTS.md
└── LICENSE

You may refine the structure after inspecting the repository.

Do not introduce directories that remain empty or exist only to make the repository appear complex.

# 7. Primary user workflow

Implement this complete flow:

1. The user registers or logs in.
2. The user creates a project.
3. The user opens the interactive map.
4. The user searches for a place or manually navigates.
5. The user defines an analysis area.
6. The frontend validates the geometry.
7. The user selects an imagery source or uploads a GeoTIFF.
8. The system validates the imagery and displays metadata.
9. The user reviews the calculation assumptions.
10. The user submits the analysis.
11. The API creates a durable processing job.
12. Celery processes the analysis asynchronously.
13. The frontend displays backend-derived stage progress.
14. The system stores all relevant artifacts and metadata.
15. The user views map overlays and calculated results.
16. The user selects individual buildings for details.
17. The user downloads reports and geospatial exports.
18. The user can return to the analysis later.

The core workflow must work with the included deterministic sample dataset without contacting external services.

# 8. User interface and experience

Create a polished renewable-energy and geospatial-analysis interface.

The design should communicate:

- scientific credibility,
- environmental value,
- trust,
- clarity,
- and technical quality.

Use:

- restrained green and blue colors,
- neutral backgrounds,
- a solar accent color,
- readable typography,
- clear spacing,
- consistent icons,
- clean cards,
- responsive layouts,
- and light, dark, and system themes.

Avoid:

- excessive gradients,
- unnecessary animation,
- crowded dashboards,
- decorative charts,
- fake real-time activity,
- or excessive technical terminology in user-facing screens.

Implement:

- responsive desktop design,
- usable tablet layouts,
- a functional mobile fallback,
- keyboard navigation,
- accessible contrast,
- visible focus states,
- loading skeletons,
- empty states,
- clear validation,
- actionable errors,
- confirmation dialogs,
- tooltips where necessary,
- and WCAG 2.1 AA practices where reasonably achievable.

Do not show false precision.

Clearly display:

- units,
- assumptions,
- imagery source,
- imagery date when available,
- model version,
- methodology version,
- data-quality indicators,
- and limitations.

# 9. Required screens

Implement:

## Public landing page

Include:

- product description,
- methodology overview,
- feature summary,
- limitations,
- engineering-estimate disclaimer,
- and a clear start action.

## Authentication

Include:

- registration,
- login,
- logout,
- password reset,
- protected routes,
- and secure session handling.

## Project dashboard

Include:

- project list,
- analysis history,
- processing status,
- creation date,
- location,
- imagery source,
- model version,
- summary energy estimate,
- search,
- filters,
- sorting,
- pagination,
- rename,
- archive,
- and delete.

## New analysis wizard

Use these steps:

1. Select location
2. Define area
3. Choose or upload imagery
4. Validate imagery
5. Configure assumptions
6. Review submission
7. Start processing

Support:

- map drawing,
- polygon editing,
- rectangle selection,
- GeoJSON upload,
- GeoTIFF upload,
- geometry removal,
- and selection-area display.

## Processing screen

Show real backend stages:

- request validation,
- imagery acquisition or loading,
- raster validation,
- optional super-resolution,
- image tiling,
- segmentation,
- mask post-processing,
- polygon extraction,
- solar calculation,
- result persistence,
- and report preparation.

Do not simulate percentages.

Preserve status across browser refreshes.

Use polling initially. Add WebSockets only if they materially improve the architecture.

## Results workspace

Include:

- base map,
- source imagery,
- segmentation mask,
- building polygons,
- solar-potential thematic layer,
- layer controls,
- opacity controls,
- legend,
- scale,
- fit-to-analysis control,
- and building selection.

Zone-level results must include:

- selected area,
- number of buildings,
- total detected roof area,
- usable roof area,
- estimated installed capacity in kWp,
- monthly production,
- annual production in kWh,
- specific yield,
- assumed losses,
- data-quality indicator,
- model version,
- and methodology version.

Building-level results must include:

- building identifier,
- roof polygon area,
- usable roof area,
- capacity,
- monthly generation,
- annual generation,
- assumed tilt,
- assumed azimuth,
- shading factor when available,
- segmentation confidence,
- and warnings.

Add charts for:

- monthly energy generation,
- building potential distribution,
- capacity distribution,
- and data quality where meaningful.

## Settings

Allow bounded configuration of:

- usable roof fraction,
- PV power density,
- system losses,
- segmentation threshold,
- minimum building area,
- tilt,
- azimuth,
- and shading behavior.

Default assumptions:

- usable roof fraction: 70%
- PV power density: 200 W/m²
- system losses: 14%
- irradiance model: pvlib clear-sky

Every analysis must store an immutable snapshot of its assumptions.

## Model administration

Use Django Admin or a focused admin interface to:

- view model versions,
- inspect model metadata,
- inspect metrics,
- approve a production model,
- activate a model,
- deactivate a model,
- and roll back to a previous model.

Never promote a model automatically only because training completed.

# 10. Maps and geocoding

Use MapLibre GL JS.

Use OpenStreetMap-compatible map data only where licensing and provider usage policies allow it.

Do not bulk-download public tiles or violate public tile-provider policies.

Make the tile endpoint configurable.

For the offline sample demonstration:

- use local map fixtures where practical,
- or allow the application to operate without a base map while still showing analysis layers.

Implement geocoding behind a provider interface.

An optional Nominatim-compatible adapter may be included for light development use, but:

- it must not be required,
- it must be rate limited,
- it must identify the application appropriately,
- and automated tests must not call the public service.

# 11. Imagery handling

Implement an imagery-provider interface supporting:

- coverage lookup,
- imagery retrieval,
- provider metadata,
- acquisition date,
- spatial resolution,
- license information,
- attribution,
- and health checks.

The mandatory providers are:

1. User-uploaded GeoTIFF
2. Local sample-imagery provider
3. Local filesystem imagery provider

Optional adapters may support:

- public STAC catalogs,
- Sentinel-2,
- Landsat,
- municipal open aerial imagery,
- or national open-data imagery.

Do not claim that low-resolution public satellite imagery is always suitable for individual-rooftop segmentation.

For every imagery asset, record:

- source,
- provider,
- original filename,
- checksum,
- CRS,
- bounds,
- transform,
- width,
- height,
- band count,
- nodata value,
- pixel resolution,
- acquisition date when known,
- license,
- attribution,
- and processing lineage.

Treat uploaded imagery as untrusted.

Validate:

- actual file content,
- format,
- CRS,
- raster bounds,
- raster dimensions,
- number of bands,
- data type,
- pixel resolution,
- nodata values,
- file size,
- and decompressed resource requirements.

Reject malformed, oversized, or dangerous input safely.

# 12. Geospatial correctness

Never calculate area directly from unprojected longitude and latitude coordinates.

Use an appropriate projected CRS or equal-area method.

Document how the analysis CRS is selected.

Preserve:

- source CRS,
- analysis CRS,
- raster transform,
- original geometry,
- transformed geometry,
- and transformation metadata.

Handle:

- invalid polygons,
- self-intersections,
- multipolygons,
- empty geometries,
- geometry collections,
- antimeridian limitations,
- and unexpectedly large analysis zones.

Use PostGIS geometry types with explicit SRIDs.

# 13. Inference pipeline

Implement the inference pipeline as importable services and CLI commands.

Pipeline stages:

1. Validate request
2. Read imagery metadata
3. Normalize imagery
4. Apply optional super-resolution
5. Read raster using windows
6. Split imagery into overlapping tiles
7. Apply model-specific preprocessing
8. Run batched U-Net inference
9. Reassemble tile predictions
10. Threshold predictions
11. Apply morphological cleanup
12. Remove invalid or insignificant components
13. Vectorize the building mask
14. Repair invalid geometry
15. Simplify polygons with bounded tolerance
16. Calculate projected areas
17. Aggregate model confidence
18. Persist artifacts
19. Run solar estimation
20. Publish results

Do not silently resize imagery in ways that invalidate geospatial scale.

Do not load arbitrarily large rasters entirely into memory.

Use:

- windowed raster reading,
- configurable tile sizes,
- bounded batches,
- overlap handling,
- resource limits,
- temporary-file cleanup,
- and explicit failure handling.

Model preprocessing must be stored with the model metadata.

Each inference run must record:

- model name,
- model version,
- model checksum,
- training dataset version,
- preprocessing configuration,
- inference settings,
- code commit,
- input imagery checksum,
- assumptions,
- worker information,
- stage timings,
- output artifacts,
- and final status.

# 14. Training pipeline

Convert training notebooks into a reproducible command-line pipeline.

Implement:

- configuration-driven training,
- train, validation, and test separation,
- deterministic seeds where supported,
- data validation,
- augmentation,
- normalization,
- checkpointing,
- early stopping,
- learning-rate scheduling,
- evaluation,
- model export,
- and MLflow tracking.

Track:

- Intersection over Union,
- Dice coefficient,
- precision,
- recall,
- F1 score,
- pixel metrics,
- and object-level metrics where feasible.

Do not select the production model based only on training loss.

Log:

- dataset version,
- Git commit,
- training configuration,
- preprocessing configuration,
- dependency versions,
- input resolution,
- metrics,
- model signature,
- checksums,
- and example input/output metadata.

Implement this model lifecycle:

1. Train candidate
2. Evaluate candidate
3. Compare candidate with production model
4. Execute quality gates
5. Register candidate
6. Require explicit approval
7. Promote approved model
8. Preserve rollback capability

# 15. Solar calculations

Implement solar estimation as a separate, versioned domain service.

At minimum:

1. Calculate roof polygon area in square metres.
2. Calculate usable roof area:

   usable_area_m2 =
       roof_area_m2 × usable_roof_fraction

3. Calculate estimated PV capacity:

   capacity_kwp =
       usable_area_m2 × power_density_w_per_m2 / 1000

4. Use pvlib to calculate solar position and clear-sky irradiance.
5. Apply orientation, tilt, system losses, and shading assumptions.
6. Aggregate monthly and annual expected production.

Keep separate:

- measured input,
- inferred input,
- user-selected assumption,
- system default,
- and calculated result.

Validate:

- nonnegative area,
- nonnegative capacity,
- usable area not exceeding roof area,
- bounded system losses,
- valid latitude and longitude,
- valid tilt,
- valid azimuth,
- timezone availability,
- and required solar-model inputs.

Do not calculate financial savings or carbon reductions unless reliable, explicitly sourced inputs are provided.

If those features are added later, make them optional and display their source and effective date.

Version the solar methodology independently from the ML model.

# 16. Shading and uncertainty

Treat surrounding-building shading as an approximation.

Do not claim accurate physical obstruction modeling without reliable:

- building heights,
- LiDAR,
- digital surface models,
- roof orientation,
- or equivalent three-dimensional information.

Document shading assumptions and limitations clearly.

Create a transparent data-quality indicator using factors such as:

- imagery resolution,
- imagery age,
- obstruction or cloud quality,
- segmentation confidence,
- polygon validity,
- missing orientation,
- missing height information,
- and potential out-of-distribution inputs.

Do not present this indicator as a calibrated statistical confidence interval unless calibration evidence exists.

# 17. Asynchronous orchestration

Use Celery and Redis.

Heavy image processing and model inference must never run inside HTTP request handlers.

Persist the authoritative job state in PostgreSQL, not Redis.

Jobs must support:

- stage-level status,
- durable progress,
- stage timestamps,
- correlation IDs,
- retry counts,
- cancellation state,
- failure codes,
- user-safe error messages,
- internal diagnostics,
- and cleanup status.

Tasks should be:

- idempotent where practical,
- safely retryable for transient failures,
- time limited,
- resource limited,
- observable,
- and resistant to duplicate execution.

Use separate queues when useful for:

- lightweight orchestration,
- CPU-intensive geospatial processing,
- and optional GPU inference.

The default path must work with CPU workers.

# 18. Database model

Implement normalized models for at least:

- User
- Project
- Analysis
- AnalysisArea
- ImageryAsset
- ProcessingJob
- JobStage
- MLModelVersion
- CalculationMethodVersion
- AnalysisAssumption
- Building
- RoofGeometry
- SolarEstimate
- ExportArtifact
- AuditEvent

Include an ownership boundary that can evolve into organization or workspace support later.

Every completed analysis must retain an immutable snapshot of:

- selected geometry,
- imagery metadata,
- assumptions,
- model version,
- calculation version,
- processing configuration,
- and code version.

Define cascade deletion and artifact cleanup explicitly.

# 19. REST API

Expose a versioned API under:

/api/v1/

Implement endpoints for:

- authentication,
- current user,
- projects,
- analyses,
- geometry validation,
- imagery upload,
- imagery metadata,
- available imagery sources,
- job submission,
- job status,
- job cancellation,
- result summary,
- paginated buildings,
- individual building details,
- map-ready geometry,
- exports,
- model metadata,
- and health checks.

Implement:

- input validation,
- object-level permission checks,
- pagination,
- filtering,
- ordering,
- rate limiting,
- idempotency keys for analysis submission,
- consistent errors,
- and OpenAPI documentation.

Avoid returning unbounded GeoJSON.

Use appropriate strategies such as:

- bounding-box queries,
- paginated features,
- zoom-dependent simplification,
- vector tiles,
- or downloadable files.

Generate a typed frontend API client from the OpenAPI specification where practical.

# 20. Reports and exports

Support:

- PDF summary report,
- CSV building results,
- GeoJSON roof polygons,
- and GeoPackage where practical.

The PDF report must contain:

- project information,
- location,
- analysis date,
- map visualization,
- imagery metadata,
- methodology,
- assumptions,
- model version,
- calculation version,
- total roof area,
- usable roof area,
- installed-capacity estimate,
- monthly generation chart,
- annual-generation estimate,
- principal limitations,
- and engineering-estimate disclaimer.

Use an open-source local PDF library such as WeasyPrint or ReportLab.

Generate expensive reports asynchronously.

Protect exported artifacts with authorization checks.

Do not expose internal storage paths.

Protect CSV exports from spreadsheet-formula injection.

# 21. Authentication and security

Implement secure authentication using Django-supported mechanisms.

Use secure defaults for:

- password hashing,
- session handling,
- CSRF protection,
- cookies,
- CORS,
- Content Security Policy,
- security headers,
- and object-level authorization.

Protect against:

- insecure direct object references,
- path traversal,
- malicious uploads,
- resource-exhaustion raster files,
- oversized geometries,
- decompression bombs,
- unauthorized artifact access,
- duplicate submissions,
- job spamming,
- cross-site scripting,
- SQL injection,
- and CSV formula injection.

Use:

- non-root containers,
- least-privilege filesystem permissions,
- dependency scanning,
- secret scanning,
- container scanning,
- and safe temporary directories.

Never store secrets in:

- source code,
- frontend bundles,
- Docker images,
- sample data,
- or log output.

Provide a safe .env.example.

Create SECURITY.md containing a threat model for:

- malicious files,
- unauthorized project access,
- sensitive-location disclosure,
- artifact tampering,
- model tampering,
- supply-chain compromise,
- denial of service,
- storage compromise,
- and accidental secret exposure.

# 22. Privacy and retention

Treat geographic selections and uploaded imagery as potentially sensitive.

Implement:

- strict ownership checks,
- tenant-ready database queries,
- configurable retention,
- artifact deletion,
- project deletion,
- minimal personal-data collection,
- and audit logging for sensitive operations.

Document:

- which data is stored,
- why it is stored,
- where it is stored,
- how long it is retained,
- and how the user deletes it.

Do not include analytics or tracking by default.

# 23. Observability

Implement structured logs with:

- timestamp,
- log level,
- service,
- request ID,
- job ID,
- analysis ID,
- stage,
- model version,
- and error code.

Do not log:

- passwords,
- tokens,
- secrets,
- complete sensitive geometry unless required,
- private storage URLs,
- or uploaded file contents.

Add metrics for:

- API latency,
- API errors,
- queue depth,
- job duration,
- stage duration,
- job success rate,
- failure rate,
- model-inference time,
- raster-processing time,
- database errors,
- object-storage errors,
- and worker resource consumption where practical.

Provide:

- liveness endpoint,
- readiness endpoint,
- database health check,
- Redis health check,
- storage health check,
- and model-availability check.

Include at least one Grafana dashboard definition.

Keep observability optional through a Docker Compose profile.

# 24. Testing

Never claim that a test passed unless it was executed.

## Backend tests

Implement tests for:

- domain services,
- authentication,
- authorization,
- project ownership,
- solar formulas,
- CRS transformations,
- area calculations,
- raster validation,
- upload security,
- polygon extraction,
- API behavior,
- Celery tasks,
- retries,
- idempotency,
- cancellation,
- exports,
- model metadata,
- and database integration.

## ML tests

Implement tests for:

- preprocessing contracts,
- expected tensor shapes,
- deterministic fixture inference,
- tile overlap,
- tile stitching,
- thresholding,
- post-processing,
- polygon conversion,
- model loading failure,
- output schemas,
- and known sample outputs.

The default test suite must run without a GPU.

## Frontend tests

Implement tests for:

- form validation,
- authentication state,
- protected routes,
- API behavior,
- analysis wizard,
- loading states,
- error states,
- result rendering,
- map interactions where practical,
- and accessibility.

## End-to-end tests

Implement at least one complete deterministic flow:

1. Register or log in.
2. Create a project.
3. Select the included sample area.
4. Select the sample imagery provider.
5. Submit an analysis.
6. Wait for real background processing.
7. Verify roof polygons exist.
8. Verify solar results exist.
9. Open a building.
10. Generate an export.
11. Verify unauthorized users cannot access the project.

Do not call external APIs from the standard automated test suite.

# 25. Sample demonstration

Include one small, legally reusable geospatial sample.

The repository or setup process must include:

- one small GeoTIFF,
- one analysis boundary,
- one lightweight inference model,
- one configuration,
- documented source and license,
- checksums,
- and expected output ranges.

The model used in the demonstration must perform real inference.

Do not return hardcoded polygons or solar estimates.

If the full model is too large for Git:

- provide a documented download script,
- use a free and legally permitted artifact host,
- verify the checksum,
- display a clear missing-model error,
- and include a lightweight test model for CI.

The offline demonstration must perform:

1. Raster loading
2. Preprocessing
3. Real model inference
4. Mask processing
5. Polygon extraction
6. Area calculation
7. PV calculation
8. Result storage
9. Map display
10. Export generation

# 26. Local development

The basic platform must start with:

docker compose up --build

Provide optional profiles:

docker compose --profile mlops up --build

docker compose --profile observability up --build

The basic profile should contain only what is required for the core workflow:

- Django API,
- React frontend,
- PostgreSQL with PostGIS,
- Redis,
- Celery worker,
- and local or MinIO storage.

Optional profiles may add:

- MLflow,
- Prometheus,
- Grafana,
- and tracing.

Provide a Makefile with:

make setup
make dev
make stop
make test
make test-backend
make test-frontend
make test-e2e
make lint
make typecheck
make migrate
make seed
make train-sample
make infer-sample
make build
make security
make clean

A new developer must be able to follow the README without undocumented manual database or filesystem steps.

# 27. CI/CD

Use GitHub Actions and remain within reasonable free-tier limits for a public portfolio repository.

Implement workflows for:

- Python linting,
- Python formatting validation,
- mypy,
- backend tests,
- frontend linting,
- TypeScript checking,
- frontend tests,
- frontend production build,
- integration tests,
- end-to-end tests,
- migration validation,
- Docker image builds,
- dependency auditing,
- secret scanning,
- and container scanning.

Optimize CI:

- cache dependencies,
- use small fixtures,
- avoid unnecessary build matrices,
- run CPU-only ML tests,
- cancel superseded workflow runs,
- and avoid building the same container repeatedly.

Do not require paid GitHub features.

Do not deploy untrusted pull-request code.

# 28. Deployment

The mandatory supported deployment is local Docker Compose.

Also provide:

- production Dockerfiles,
- a production Docker Compose example,
- optional Kubernetes manifests or a Helm chart,
- and optional Terraform examples.

Kubernetes and Terraform are included only as portfolio demonstrations.

They must not be required for the core application.

Never execute Terraform automatically.

Clearly warn that optional cloud infrastructure could generate charges.

Include:

- environment-variable reference,
- migration procedure,
- backup guidance,
- restoration guidance,
- deployment runbook,
- rollback runbook,
- and upgrade procedure.

# 29. Documentation

Create:

- README.md
- CONTRIBUTING.md
- SECURITY.md
- COSTS.md
- architecture documentation
- development guide
- deployment guide
- API guide
- MLOps lifecycle guide
- model card
- dataset card
- solar methodology
- geospatial accuracy guide
- threat model
- privacy and retention guide
- operational runbook
- troubleshooting guide
- release process
- architecture decision records

Add Mermaid diagrams for:

- system context,
- application components,
- analysis sequence,
- job lifecycle,
- data lineage,
- model promotion,
- and deployment topology.

COSTS.md must state that the default local cost is:

€0, excluding the user’s existing computer, electricity, and internet access.

Document all important limitations:

- imagery availability,
- imagery licensing,
- image resolution,
- segmentation uncertainty,
- super-resolution limitations,
- roof-slope uncertainty,
- orientation uncertainty,
- missing height data,
- shading limitations,
- clear-sky assumptions,
- and weather-data limitations.

# 30. Performance

Use configurable and documented limits.

Implement:

- asynchronous heavy processing,
- windowed raster reads,
- batched inference,
- paginated API responses,
- bounded uploads,
- bounded geometry size,
- efficient spatial queries,
- database indexes,
- avoidance of N+1 queries,
- simplified map geometry,
- streamed downloads,
- and background exports.

Do not state performance guarantees without measured benchmarks.

Add simple benchmark or performance tests for:

- geometry validation,
- raster tiling,
- model inference,
- polygon extraction,
- building-result queries,
- and result serialization.

# 31. Efficient implementation plan

Implement this project in vertical phases.

A phase is complete only when its functionality works, relevant tests pass, and documentation is updated.

## Phase 1: Repository assessment

- Inspect the complete repository.
- Inspect the notebooks.
- Identify reusable implementation.
- Identify missing artifacts.
- Identify dataset and model licensing.
- Record technical risks.
- Create a concise implementation plan.
- Add architecture decision records for major choices.

Do not begin by rewriting the complete repository.

## Phase 2: Minimal foundation

- Create the monorepo structure.
- Configure Django.
- Configure React.
- Configure PostGIS.
- Configure Redis and Celery.
- Add Docker Compose.
- Add authentication.
- Add projects and analyses.
- Add the basic design system.
- Add quality tooling.

## Phase 3: Thin working vertical slice

Build the smallest complete real workflow:

- create project,
- use sample area,
- load sample GeoTIFF,
- run lightweight real inference,
- extract polygons,
- calculate solar estimates,
- save results,
- and display them on a map.

Complete this vertical slice before adding advanced features.

## Phase 4: User input workflow

Add:

- map drawing,
- polygon editing,
- GeoJSON upload,
- GeoTIFF upload,
- validation,
- imagery metadata,
- and analysis assumptions.

## Phase 5: Scalable processing

Add:

- windowed raster processing,
- image tiling,
- tile overlap,
- batched inference,
- durable job stages,
- retries,
- cancellation,
- resource limits,
- and cleanup.

## Phase 6: Complete results experience

Add:

- map layers,
- building selection,
- zone summary,
- building summary,
- charts,
- legends,
- filters,
- warnings,
- and methodology display.

## Phase 7: MLOps

Add:

- reproducible training,
- MLflow,
- dataset versioning,
- model evaluation,
- model registration,
- approval,
- promotion,
- and rollback.

## Phase 8: Exports

Add:

- PDF,
- CSV,
- GeoJSON,
- and GeoPackage where practical.

## Phase 9: Hardening

Complete:

- security review,
- accessibility checks,
- privacy controls,
- observability,
- performance profiling,
- CI/CD,
- deployment examples,
- and operational documentation.

At the end of every phase:

1. Format code.
2. Run linting.
3. Run type checking.
4. Run relevant tests.
5. Run builds.
6. Correct failures before continuing.
7. Commit or summarize the phase cleanly.
8. State exact commands and results.
9. Record remaining risks.
10. Continue to the next phase unless genuinely blocked.

# 32. Scope prioritization

Use these priorities.

## P0: Mandatory

- Authentication
- Project management
- Map area selection
- GeoTIFF validation
- Real model inference
- Roof polygon extraction
- Geospatially correct area calculation
- Solar estimation
- Asynchronous processing
- Results map
- Building details
- PDF, CSV, and GeoJSON export
- Tests
- Docker Compose
- Documentation
- Zero-cost local demonstration

## P1: Important

- MLflow experiment tracking
- Model registry
- Data-quality score
- Advanced results filtering
- Prometheus and Grafana
- GeoPackage export
- Optional open-data imagery adapter

## P2: Optional

- Kubernetes
- Helm
- Terraform examples
- WebSocket progress
- GPU execution
- Advanced 3D shading
- Multiple organizations
- Social login
- Financial savings
- Carbon calculations

Do not implement P2 features before all P0 requirements work.

# 33. Anti-overengineering rules

Do not:

- create microservices,
- add Kafka,
- add Kubernetes to the default development path,
- introduce separate databases per domain,
- create abstractions without a current use case,
- create generic frameworks inside the project,
- generate hundreds of empty files,
- add advanced shading without reliable data,
- implement financial estimates without sourced inputs,
- optimize for hypothetical internet-scale traffic,
- or add features only to increase apparent complexity.

Prefer a clean modular monolith and one complete working workflow.

# 34. Definition of done

The project is complete only when a reviewer can:

1. Clone the repository.
2. Follow the documented setup.
3. Start the system with Docker Compose.
4. Register and log in.
5. Create a project.
6. Select the sample zone.
7. Submit an analysis.
8. Observe real processing stages.
9. Execute real CPU-based inference.
10. View resulting roof polygons.
11. Inspect zone and building solar estimates.
12. Download PDF, CSV, and GeoJSON exports.
13. Reopen the historical analysis.
14. Delete the project and its artifacts.
15. Run the complete automated test suite.

Additionally:

- migrations must succeed,
- backend tests must pass,
- frontend tests must pass,
- end-to-end tests must pass,
- production builds must succeed,
- Docker images must build,
- OpenAPI documentation must generate,
- required controls must be functional,
- required paths must not contain placeholders,
- secrets must not be committed,
- and no core workflow may require a paid tool or service.

# 35. Coding-agent operating instructions

Before writing code:

1. Inspect the repository.
2. Read the existing notebooks and configuration.
3. Identify reusable functions.
4. Identify missing inputs and artifacts.
5. Check data and model licenses.
6. Create a short ordered plan.
7. Begin with the thin vertical slice.

Ask questions only when missing information makes correct implementation impossible.

Otherwise, choose conservative defaults and document them.

Do not pause after every small decision.

Do not ask for confirmation between phases unless a genuine blocker exists.

Do not:

- fabricate datasets,
- fabricate model metrics,
- fabricate test output,
- fabricate benchmark results,
- fabricate deployment success,
- return hardcoded analysis results,
- leave TODO implementations in mandatory functionality,
- create fake APIs,
- or claim software is production-ready without verification.

If a resource is unavailable:

- explain the exact dependency,
- implement its interface,
- provide a deterministic local alternative,
- add setup validation,
- and continue with all unblocked work.

# 36. Token and execution efficiency

Optimize context and token usage.

Follow these rules:

- Do not repeat this specification.
- Do not explain standard framework concepts.
- Do not print complete lockfiles.
- Do not print generated migration files unless needed.
- Do not print large JSON, raster, model, or generated artifacts.
- Read only files relevant to the current phase.
- Search the repository before opening many files.
- Patch working files instead of regenerating them.
- Reuse shared types and constants.
- Keep progress updates concise.
- Reference changed files by path.
- Group related changes.
- Maintain a short decision log.
- Maintain a short risk log.
- Run targeted tests during implementation.
- Run the full suite at meaningful milestones.
- Prioritize implementation and validation over lengthy explanations.

For each progress report, use this format:

Completed:
- concise list

Changed files:
- paths only

Validation:
- commands executed
- passed and failed counts
- relevant errors

Decisions:
- only material decisions

Risks or blockers:
- only actual risks

Next:
- immediate next implementation step

# 37. Required final report

At completion, provide:

1. Architecture summary
2. Repository structure
3. Implemented user journeys
4. ML pipeline summary
5. Solar methodology summary
6. MLOps lifecycle
7. Geospatial correctness measures
8. Security controls
9. Testing summary
10. Exact commands executed
11. Exact test and build results
12. Local startup instructions
13. Sample demonstration instructions
14. Deployment options
15. Known limitations
16. Optional future improvements

Do not call the project complete or production-ready if any P0 requirement remains unimplemented or unverified.

Start now by inspecting the repository and existing notebook implementation. Produce a concise repository assessment and implementation plan, then immediately begin Phase 2 and the thin vertical slice unless a genuine blocker prevents progress.
