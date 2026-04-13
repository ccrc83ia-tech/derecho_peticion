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


# --- RBAC ---

class Permission(str, Enum):
    GENERATE_DOCUMENT = "generate_document"
    VIEW_TEMPLATES = "view_templates"
    MANAGE_TEMPLATES = "manage_templates"
    VIEW_ENTITIES = "view_entities"
    MANAGE_ENTITIES = "manage_entities"
    VIEW_COMPANY = "view_company"
    MANAGE_COMPANY = "manage_company"
    MANAGE_USERS = "manage_users"


class Role(str, Enum):
    ADMIN = "admin"
    ABOGADO = "abogado"
    PASANTE = "pasante"
    CONSULTA = "consulta"


ROLE_PERMISSIONS: dict[Role, set[Permission]] = {
    Role.ADMIN: set(Permission),
    Role.ABOGADO: {
        Permission.GENERATE_DOCUMENT,
        Permission.VIEW_TEMPLATES,
        Permission.VIEW_ENTITIES,
        Permission.MANAGE_ENTITIES,
        Permission.VIEW_COMPANY,
    },
    Role.PASANTE: {
        Permission.GENERATE_DOCUMENT,
        Permission.VIEW_TEMPLATES,
        Permission.VIEW_ENTITIES,
    },
    Role.CONSULTA: {
        Permission.VIEW_TEMPLATES,
        Permission.VIEW_ENTITIES,
        Permission.VIEW_COMPANY,
    },
}


class User(BaseModel):
    user_id: str
    username: str
    full_name: str
    email: str = ""
    role: Role = Role.PASANTE
    active: bool = True
    password_hash: str = ""
    permissions: list[str] | None = None

    def has_permission(self, perm: Permission) -> bool:
        if self.permissions is not None:
            return perm.value in self.permissions
        return perm in ROLE_PERMISSIONS.get(self.role, set())


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
    max_output_tokens: int | None = None
