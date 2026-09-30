"""Celery tasks for the geospatial app.

Per the app responsibility table (code-architecture §1), geospatial exposes no
Celery tasks of its own: vectorization and persistence are invoked *inside* the
jobs pipeline via injected services (:class:`VectorizationService`,
:class:`BuildingPersistenceService`). This module exists so
``CELERY_TASK_ROUTES`` (``apps.geospatial.tasks.*`` -> ``cpu-heavy``) has a
concrete target namespace and autodiscovery finds a valid module.
"""

from __future__ import annotations
