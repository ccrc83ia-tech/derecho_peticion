from enum import Enum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


# --- Tenant Configuration ---

class Branding(BaseModel):
    logo_url: str | None = None
    header_text: str | None = None
    footer_text: str | None = None
    primary_color: str = "#000000"
    nit: str | None = None
    address: str | None = None
    phone: str | None = None
    email: str | None = None
    website: str | None = None


class TenantConfig(BaseModel):
    tenant_id: str
    name: str
    system_prompt: str
    legal_rules: list[str] = Field(default_factory=list)
    branding: Branding = Field(default_factory=Branding)
    active: bool = True


class Entity(BaseModel):
    entity_id: str
    name: str
    nit: str = ""
    address: str = ""
    city: str = ""
    phone: str = ""
    email: str = ""
    legal_rep: str = ""
    entity_type: str = ""
    notes: str = ""


# --- Request / Response (aligned to OpenAPI contract) ---

class DocumentGenerationRequest(BaseModel):
    template_id: str
    metadata: dict[str, str]
    selected_rules: list[str] | None = None


class DocumentStatus(str, Enum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class DocumentGenerationResponse(BaseModel):
    transaction_id: UUID = Field(default_factory=uuid4)
    status: DocumentStatus = DocumentStatus.COMPLETED
    download_url: str | None = None


# --- Internal Domain Objects ---

class LegalContext(BaseModel):
    """Agnostic context assembled by the Use Case, consumed by any AI provider."""
    system_prompt: str
    user_prompt: str
    metadata: dict[str, str] = Field(default_factory=dict)
    temperature: float = 0.3
    max_output_tokens: int = 4096
