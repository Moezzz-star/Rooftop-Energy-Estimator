# Rooftop Energy Estimator — Project Context (Phase 1)

Shared memory for all agents. Keep tight and factual. Update via Context Manager.

## 1. Canonical Reusable Logic (Assessment Digest)

### ML Segmentation
- **Model:** `unet_buildings.keras` (90MB, NOT in git). Keras functional U-Net. Input `(256,256,3)` float32 in `[0,1]`, single-channel sigmoid output. Load with `compile=False`.
- **Preprocessing (canonical):** per-image per-band percentile normalize `pmin=2, pmax=98` -> clip `[0,1]`; guard `hi-lo < 1e-6` -> 0; `nan_to_num`. Bands `(1,2,3)`=R,G,B (B04/B03/B02). Percentiles over whole image -> **two-pass needed for windowed reads**.
- **Tiling:** `tile=256`, `stride=128`, force final edge start = `length-tile`, reflect-pad if smaller than tile. Overlap-average stitching (`prob_sum/weight_sum`), crop to original.
- **Threshold:** `0.2`. Mask post: skimage `remove_small_objects(min_size=8)`, `remove_small_holes(area_threshold=8)`. Drop polygons with `area_m2 < 20`.

### Vectorization & Geo
- **Vectorize:** `rasterio.features.shapes` -> `shapely.shape` -> `GeoDataFrame(crs=src.crs)`; validity filter `notnull & ~is_empty & is_valid`. **MUST ADD** `make_valid`/`buffer(0)` + bounded simplify (absent in notebook).
- **Area:** `gdf.estimate_utm_crs()` -> `to_crs` -> `geometry.area` (m2). Centroid computed in UTM then reproject to EPSG:4326. Geospatially sound. **Risk:** `estimate_utm_crs` single-zone; fails if raster lacks CRS.

### Solar (pvlib — port to versioned service)
- `Location(lat,lon,tz,alt)`; `get_clearsky(model="ineichen")`; `get_solarposition`; `irradiance.get_total_irradiance(model="haydavies", dni_extra=get_extra_radiation)`; `temperature.sapm_cell(temp_air=20, wind=1, open_rack_glass_glass)`; `pvsystem.pvwatts_dc(pdc0, gamma_pdc=-0.0035)`; `inverter.pvwatts(eta_inv_nom=0.96)`. Hourly full year (`freq=1h`).
- `usable = roof_area*0.70`; `pdc0_w = usable*200`; `kwp = pdc0_w/1000`; `poa_eff = poa_diffuse + poa_direct*shading`; `pac_net = pac*(1-0.14)`; `annual_kwh = pac_net.sum()/1000`; `specific_yield = annual_kwh/kwp`.
- **Orientation sweep** (tilt 0-45 step5 × azi 0-360 step10 = 360 hourly-year sims) is EXPENSIVE. **DECISION:** deterministic CPU sample path uses fixed default tilt/azimuth (skip brute-force sweep); sweep is optional/coarse behind a flag.
- **Shading:** custom parametric height-from-area model; OPTIONAL, deferred (not P0).
- **Super-resolution:** PyTorch OpenSR diffusion (GPU + network deps + telemetry POST). **DECISION:** OPTIONAL, feature-flagged, SKIPPED on offline CPU sample path.

## 2. Decision Log (DEC)

- **DEC-01 Solar defaults:** `usable_roof_fraction=0.70`, `power_density=200 W/m2`, `system_losses=0.14`, `module_eff=0.20`, irradiance=pvlib clear-sky Ineichen, `gamma_pdc=-0.0035`, inverter `eta=0.96`, `temp_air=20C`, `wind=1 m/s`.
- **DEC-02 Disclaimer text** (all UI/PDF/CSV/GeoJSON): "These are engineering estimates for indicative purposes only and are not a bankable photovoltaic yield study."
- **DEC-03 Retention:** configurable; default keep until user deletes project/analysis; audit events retained separately. No analytics/tracking by default.
- **DEC-04 Licensing:** training labels from OpenStreetMap = ODbL 1.0 -> ship attribution "© OpenStreetMap contributors, ODbL" with model + derived outputs; document in model card. pvlib BSD-3. Keep all open-data/imagery integrations OPTIONAL (not required for sample/tests).
- **DEC-05 Model distribution:** 90MB `unet_buildings.keras` NOT in git -> documented checksummed download script (`scripts/`) to a free host; clear missing-model error; ship a tiny randomly-initialized CI test U-Net with identical `(256,256,3)->sigmoid` contract for tests.
- **DEC-06 Do NOT commit large files:** `unet_buildings.keras` (90MB), `sr_training_30.zip` (51MB), `notebook final segmentation.ipynb` (22MB) -> `.gitignore`.
- **DEC-07 Architecture:** modular monolith (Django) + Celery async workers; no microservices/Kafka/k8s in default path (§33). Storage behind an abstraction (filesystem default, MinIO/S3 later).
- **DEC-08 Ownership:** User -> Project -> Analysis; strict per-user object-level authorization; tenant-ready queries.
- **DEC-09 Immutable snapshot:** each Analysis freezes AnalysisAssumption + MLModelVersion + CalculationMethodVersion + code commit + imagery metadata; reopen reproduces identical numbers. Solar methodology versioned independently from ML model.

## 3. MUST-ADD (not present in notebooks)

- Windowed rasterio reads; bounded batched inference.
- Geometry repair (`make_valid`/`buffer(0)`) + bounded simplify.
- §15 solar input validation: nonneg area/capacity, `usable <= roof`, bounded losses, valid lat/lon/tilt/azimuth, tz availability.
- Inference provenance record: model name/version/checksum, dataset version, preproc config, code commit, imagery checksum, stage timings, status.
- Remove Kaggle paths + pip installs + Google-Form telemetry.
- CSV formula-injection protection.
- Model download+checksum script + CI test model.

## 4. Domain Model (15 entities, §18)

`User`, `Project`, `Analysis`, `AnalysisArea`, `ImageryAsset`, `ProcessingJob`, `JobStage`, `MLModelVersion`, `CalculationMethodVersion`, `AnalysisAssumption`, `Building`, `RoofGeometry`, `SolarEstimate`, `ExportArtifact`, `AuditEvent`.

PostGIS geometry types with explicit SRIDs.
