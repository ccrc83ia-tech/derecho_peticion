"""Centralised constants and configuration for the Streamlit UI layer."""

from __future__ import annotations

import os
import re
from pathlib import Path

# Project root (resolve relative paths from here)
_PROJECT_ROOT = Path(__file__).resolve().parents[5]

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
DB_PATH: str = str(_PROJECT_ROOT / os.getenv("DB_PATH", "legal_engine.db"))
TENANTS_FILENAME: str = os.getenv("TENANT_DATASOURCE", "tenants.json")
TEMPLATES_FILENAME: str = os.getenv("TEMPLATES_DATASOURCE", "templates.json")
FILE_ENCODING: str = "utf-8"

# ---------------------------------------------------------------------------
# Page metadata
# ---------------------------------------------------------------------------
APP_TITLE: str = "FuturoTech AI — Legal Engine"
APP_ICON: str = "⚖️"
APP_SUBTITLE: str = "Generador Universal de Documentos Jurídicos"

PAGE_GENERATE: str = "Generar Documento"
PAGE_TEMPLATES: str = "Plantillas"
PAGE_COMPANY: str = "Empresas"

NAV_ITEMS: list[dict[str, str]] = [
    {"icon": "📄", "label": PAGE_GENERATE, "key": "generate"},
    {"icon": "📋", "label": PAGE_TEMPLATES, "key": "templates"},
    {"icon": "🏢", "label": PAGE_COMPANY, "key": "company"},
]

# ---------------------------------------------------------------------------
# Field rendering hints
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

TEXT_AREA_FIELDS: set[str] = {"hechos_crudos", "body"}
TEXT_AREA_HEIGHT: int = 140

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
MSG_NO_TENANTS: str = "No hay empresas configuradas. Cree una en la sección «{page}»."
MSG_NO_TEMPLATES: str = "No hay plantillas configuradas. Cree una en la sección «{page}»."
MSG_NO_TEMPLATES_FOR_TENANT: str = "No hay plantillas compatibles con esta empresa."
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

# ---------------------------------------------------------------------------
# Theme
# ---------------------------------------------------------------------------
THEME_PRIMARY: str = os.getenv("THEME_PRIMARY", "#4F46E5")
THEME_BORDER: str = "#E2E8F0"
THEME_TEXT_MUTED: str = "#64748B"


def _build_css() -> str:
    """Build global CSS as a function to avoid f-string escaping issues."""
    return (
        "<style>"
        # Layout
        ".block-container { max-width: 1100px; padding-top: 1.5rem; }"
        # Sidebar
        'section[data-testid="stSidebar"] {'
        "  background: linear-gradient(180deg, #0F172A 0%, #1E293B 100%);"
        "}"
        'section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,'
        'section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] span {'
        "  color: #CBD5E1;"
        "}"
        'section[data-testid="stSidebar"] hr {'
        "  border-color: rgba(255,255,255,0.1);"
        "}"
        # Cards
        ".ui-card {"
        f"  border: 1px solid {THEME_BORDER};"
        "  border-radius: 12px;"
        "  padding: 1.25rem 1.5rem;"
        "  margin-bottom: 1rem;"
        "  background: #FFFFFF;"
        "  box-shadow: 0 1px 3px rgba(0,0,0,0.04), 0 1px 2px rgba(0,0,0,0.06);"
        "}"
        ".ui-card-muted {"
        "  border: 1px solid #F1F5F9;"
        "  border-radius: 10px;"
        "  padding: 1rem 1.25rem;"
        "  margin-bottom: 0.75rem;"
        "  background: #F8FAFC;"
        "}"
        # Section titles
        ".section-title {"
        "  font-size: 0.75rem;"
        "  font-weight: 700;"
        "  text-transform: uppercase;"
        "  letter-spacing: 0.08em;"
        f"  color: {THEME_TEXT_MUTED};"
        "  margin: 1.25rem 0 0.5rem 0;"
        "  padding-bottom: 0.35rem;"
        f"  border-bottom: 2px solid {THEME_PRIMARY};"
        "  display: inline-block;"
        "}"
        # Badges
        ".badge {"
        "  display: inline-block;"
        "  padding: 3px 12px;"
        "  border-radius: 999px;"
        "  font-size: 0.75rem;"
        "  font-weight: 600;"
        "}"
        ".badge-online  { background: #D1FAE5; color: #065F46; }"
        ".badge-offline { background: #FEE2E2; color: #991B1B; }"
        ".badge-count   { background: #EEF2FF; color: #4338CA; }"
        # Sidebar brand
        ".sidebar-brand { text-align: center; padding: 1.2rem 0.5rem 0.5rem; }"
        ".sidebar-brand-icon { font-size: 2.2rem; }"
        ".sidebar-brand-title {"
        "  color: #F8FAFC; font-size: 1.15rem; font-weight: 700; margin: 0.3rem 0 0;"
        "}"
        ".sidebar-brand-sub {"
        "  color: #94A3B8; font-size: 0.72rem; margin: 0;"
        "}"
        # Stat card
        ".stat-card {"
        "  text-align: center;"
        "  padding: 1rem;"
        f"  border: 1px solid {THEME_BORDER};"
        "  border-radius: 10px;"
        "  background: #FFFFFF;"
        "}"
        ".stat-card-value {"
        f"  font-size: 1.8rem; font-weight: 700; color: {THEME_PRIMARY};"
        "}"
        ".stat-card-label {"
        f"  font-size: 0.78rem; color: {THEME_TEXT_MUTED}; margin-top: 2px;"
        "}"
        # Page header
        ".page-header {"
        "  margin-bottom: 1.5rem;"
        "}"
        ".page-header h2 {"
        "  margin: 0 0 0.2rem 0; font-size: 1.5rem; color: #0F172A;"
        "}"
        ".page-header p {"
        f"  margin: 0; color: {THEME_TEXT_MUTED}; font-size: 0.9rem;"
        "}"
        # Rule row
        ".rule-row {"
        "  display: flex; align-items: center; gap: 0.5rem;"
        "  padding: 0.4rem 0;"
        "}"
        "</style>"
    )


GLOBAL_CSS: str = _build_css()
