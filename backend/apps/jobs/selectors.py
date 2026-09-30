"""Read queries for the jobs app (owner-scoped selectors).

Selectors keep read logic out of the write-focused services and views
(code-architecture §8). All queries enforce the ownership chain
(``job -> analysis -> project -> owner``) per DEC-08.
"""

from __future__ import annotations

from typing import Any

from common.errors import NotFoundError

from .models import ProcessingJob


def get_job_for_analysis(analysis_id: Any, user: Any) -> ProcessingJob:
    """Return the owner's job for ``analysis_id``.

    Args:
        analysis_id: Primary key of the owning analysis.
        user: The requesting user (ownership is resolved via the project).

    Returns:
        The matching :class:`ProcessingJob` with stages prefetched.

    Raises:
        NotFoundError: If no such job is visible to ``user``.
    """
    job = (
        ProcessingJob.objects.select_related("analysis__project")
        .prefetch_related("stages")
        .filter(analysis_id=analysis_id, analysis__project__owner=user)
        .first()
    )
    if job is None:
        raise NotFoundError("No processing job exists for this analysis.")
    return job
