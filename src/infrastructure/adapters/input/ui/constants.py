"""Centralised constants and configuration for the Streamlit UI layer."""

from __future__ import annotations

import os
import re

# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------
API_HOST: str = os.getenv("API_HOST", "localhost")
API_PORT: str = os.getenv("API_PORT", "8000")
API_BASE: str = os.getenv("API_BASE_URL", f"http://{API_HOST}:{API_PORT}")
API_GENERATE_PATH: str = "/api/v1/documents/generate"
API_HEALTH_PATH: str = "/docs"
API_TIMEOUT_GENERATE: int = int(os.getenv("API_TIMEOUT_GENERATE", "120"))
API_TIMEOUT_DOWNLOAD: int = int(os.getenv("API_TIMEOUT_DOWNLOAD", "30"))
API_TIMEOUT_HEALTH: int = int(os.getenv("API_TIMEOUT_HEALTH", "3"))

# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------
DB_PATH: str = os.getenv("DB_PATH", "legal_engine.db")
TENANTS_FILENAME: str = os.getenv("TENANT_DATASOURCE", "tenants.json")
TEMPLATES_FILENAME: str = os.getenv("TEMPLATES_DATASOURCE", "templates.json")
FILE_ENCODING: str = "utf-8"

# ---------------------------------------------------------------------------
# Page metadata
# ---------------------------------------------------------------------------
APP_TITLE: str = "FuturoTech AI — Legal Engine"
APP_ICON: str = "⚖️"
APP_SUBTITLE: str = "Generador Universal de Documentos Jurídicos"

PAGE_GENERATE: str = "📄 Generar Documento"
PAGE_TEMPLATES: str = "📋 Plantillas"
PAGE_COMPANY: str = "🏢 Configurar Empresa"

PAGES: tuple[str, ...] = (PAGE_GENERATE, PAGE_TEMPLATES, PAGE_COMPANY)

# ---------------------------------------------------------------------------
# Field rendering hints  (field_key → human label)
# Used as fallback when the template does not define a label for a field.
# ---------------------------------------------------------------------------
FIELD_LABELS: dict[str, str] = {
    "cliente_nombre": "Nombre del Cliente",
    "cedula": "Cédula de Ciudadanía",
    "entidad_demandada": "Entidad Demandada",
    "hechos_crudos": "Hechos del Caso",
    "client_name": "Client Name",
    "subject": "Subject",
    "body": "Body",
}

# Fields that should render as <textarea> instead of <input>
TEXT_AREA_FIELDS: set[str] = {"hechos_crudos", "body"}
TEXT_AREA_HEIGHT: int = 120

# ---------------------------------------------------------------------------
# Branding defaults & validation
# ---------------------------------------------------------------------------
DEFAULT_PRIMARY_COLOR: str = "#000000"
HEX_COLOR_PATTERN: re.Pattern[str] = re.compile(r"^#[0-9a-fA-F]{6}$")

# ---------------------------------------------------------------------------
# Preview
# ---------------------------------------------------------------------------
PREVIEW_MAX_HEIGHT: int = 500
PREVIEW_FONT_FAMILY: str = "'Georgia', serif"
PREVIEW_FONT_SIZE: str = "14px"

# ---------------------------------------------------------------------------
# UI messages
# ---------------------------------------------------------------------------
MSG_NO_TENANTS: str = "No hay empresas configuradas. Cree una en la pestaña «{page}»."
MSG_NO_TEMPLATES: str = "No hay plantillas configuradas. Cree una en la pestaña «{page}»."
MSG_NO_TEMPLATES_FOR_TENANT: str = "No hay plantillas con campos que coincidan con esta empresa."
MSG_MISSING_FIELDS: str = "Campos obligatorios vacíos: {fields}"
MSG_GENERATING: str = "Generando documento con IA…"
MSG_SUCCESS: str = "✅ Documento generado exitosamente"
MSG_CONNECTION_ERROR: str = (
    "No se pudo conectar con la API. "
    "Verifica que el servidor esté corriendo en {api_base}"
)
MSG_API_OFFLINE: str = (
    "⚠️ La API no está disponible en **{api_base}**. "
    "Inicia el servidor antes de generar documentos."
)
MSG_SAVED: str = "✅ Guardado correctamente"
MSG_DELETED: str = "🗑️ Eliminado correctamente"
MSG_CONFIRM_DELETE: str = "¿Está seguro de eliminar «{name}»?"
MSG_INVALID_COLOR: str = "Color inválido. Use formato hexadecimal (#RRGGBB)."

# ---------------------------------------------------------------------------
# DOCX MIME
# ---------------------------------------------------------------------------
DOCX_MIME: str = (
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
)
