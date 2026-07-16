# src/aegis/api/schemas/errors.py
"""
Shared API error response schema.

FastAPI's default ``HTTPException`` handling already serializes every
error raised by the routers as ``{"detail": <str>}``; ``ErrorResponse``
exists only so that shape is declared in the OpenAPI schema via each
route's ``responses=`` mapping, instead of being an accurate-but-
undocumented convention. It is never raised or constructed directly --
routers keep raising ``HTTPException``, and the global handler in
``aegis.api.main`` keeps returning a plain dict with the same shape.
"""

from __future__ import annotations

from pydantic import BaseModel


class ErrorResponse(BaseModel):
    """Stable external error envelope: ``{"detail": "<safe message>"}``."""

    detail: str
