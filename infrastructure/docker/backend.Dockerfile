# =============================================================================
# backend.Dockerfile — shared image for `api`, `worker`, and `beat`.
# Base: python:3.12-slim (Debian bookworm) + GDAL/GEOS/PROJ for
# rasterio / geopandas / shapely. Non-root user `app` (uid 1000).
#
# Multi-stage is optional here; a single stage keeps the geospatial + TF-CPU
# toolchain simple. Build once, reuse across api/worker/beat (arch §2).
# =============================================================================
FROM python:3.12-slim AS runtime

# --- OS packages: geospatial native libs + build + curl (healthcheck) + procps
# (procps provides pgrep, used by the celery-beat healthcheck in compose).
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        gdal-bin \
        libgdal-dev \
        libgeos-dev \
        libproj-dev \
        build-essential \
        curl \
        procps \
    && rm -rf /var/lib/apt/lists/*

# --- Python runtime behaviour ------------------------------------------------
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    # Repo root (for `ml`) + backend/ (for `config`, `apps`, `common`).
    PYTHONPATH=/app:/app/backend

WORKDIR /app

# --- Non-root user -----------------------------------------------------------
RUN groupadd --gid 1000 app \
    && useradd --uid 1000 --gid 1000 --create-home --shell /bin/bash app

# --- Python dependencies -----------------------------------------------------
# The backend/ package (pyproject.toml, authored by the backend engineer) lists
# all runtime deps incl. tensorflow-cpu, rasterio, geopandas, pvlib, celery.
# We install it editable so `config`/`common`/`apps` resolve; in dev the source
# is bind-mounted over /app, keeping the editable install valid.
COPY backend/ /app/backend/
RUN pip install --upgrade pip
# Install the heavy geospatial stack from prebuilt wheels only. This avoids
# fragile source (sdist) builds — notably rasterio, whose sdist setup.py imports
# the now-removed `pkg_resources` and fails under modern setuptools. TensorFlow
# is resolved by the editable install below via platform markers in pyproject
# (tensorflow-cpu on x86_64, tensorflow on aarch64).
RUN pip install --only-binary=:all: \
        "numpy>=1.26,<2.0" \
        "rasterio>=1.4,<1.6" \
        "geopandas>=0.14,<1.1" \
        "shapely>=2.0,<3.0" \
        "scikit-image>=0.23,<0.25" \
        "pvlib>=0.11,<0.12"
# Then install the project (editable) + remaining deps incl. TensorFlow (wheel).
RUN pip install -e "/app/backend[dev]"

# --- Entrypoint --------------------------------------------------------------
COPY infrastructure/docker/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh \
    && mkdir -p /app/media /app/beat \
    && chown -R app:app /app

USER app

# Default healthcheck targets the API service; worker/beat override it in
# docker-compose.yml (celery inspect ping / process check).
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD curl -fsS http://localhost:8000/api/health/ || exit 1

ENTRYPOINT ["entrypoint.sh"]
# Default command = API dev server (compose overrides per service/env).
CMD ["python", "backend/manage.py", "runserver", "0.0.0.0:8000"]
