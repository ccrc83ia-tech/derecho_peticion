"""API DTOs — request/response shapes for the HTTP layer.

These are intentionally separate from domain models (domain/models.py).
The controller maps DTOs ↔ domain objects; the domain never imports from here.
"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field


class GenerateDocumentRequestDTO(BaseModel):
    """HTTP request body for POST /api/v1/documents/generate."""
    template_id: str
    metadata: dict[str, str]
    selected_rules: list[str] | None = None


class GenerateDocumentResponseDTO(BaseModel):
    """HTTP response for document generation."""
    transaction_id: UUID
    status: str
    download_url: str | None = None


class HealthCheckDTO(BaseModel):
    status: str
    checks: dict[str, str] = Field(default_factory=dict)
