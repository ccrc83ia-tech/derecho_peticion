import json
from pathlib import Path

import requests
import streamlit as st

API_BASE = "http://localhost:8000"


def _find_tenants_file() -> Path:
    current = Path(__file__).resolve().parent
    while current != current.parent:
        candidate = current / "tenants.json"
        if candidate.exists():
            return candidate
        current = current.parent
    return Path("tenants.json")


TENANTS_PATH = _find_tenants_file()

# --- Helpers ---

@st.cache_data(ttl=60)
def load_tenants() -> list[dict]:
    with TENANTS_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def generate_document(tenant_id: str, template_id: str, metadata: dict) -> dict:
    resp = requests.post(
        f"{API_BASE}/api/v1/documents/generate",
        headers={"X-Tenant-ID": tenant_id, "Content-Type": "application/json"},
        json={"template_id": template_id, "metadata": metadata},
        timeout=120,
    )
    resp.raise_for_status()
    return resp.json()


def download_file(download_url: str) -> bytes:
    resp = requests.get(f"{API_BASE}{download_url}", timeout=30)
    resp.raise_for_status()
    return resp.content


# --- Labels legibles para campos ---

FIELD_LABELS = {
    "cliente_nombre": "Nombre del Cliente",
    "cedula": "Cédula de Ciudadanía",
    "entidad_demandada": "Entidad Demandada",
    "hechos_crudos": "Hechos del Caso",
    "client_name": "Client Name",
    "subject": "Subject",
    "body": "Body",
}

TEXT_AREA_FIELDS = {"hechos_crudos", "body"}

# --- UI ---

st.set_page_config(page_title="FuturoTech AI — Legal Engine", page_icon="⚖️", layout="centered")

st.markdown(
    "<h1 style='text-align:center;'>⚖️ FuturoTech AI</h1>"
    "<p style='text-align:center;color:gray;'>Generador Universal de Documentos Jurídicos</p>",
    unsafe_allow_html=True,
)

st.divider()

tenants = load_tenants()
tenant_map = {t["name"]: t for t in tenants if t.get("active", True)}

# --- Sidebar ---

with st.sidebar:
    st.header("⚙️ Configuración")
    selected_name = st.selectbox("Firma / Tenant", options=list(tenant_map.keys()))
    tenant = tenant_map[selected_name]

    st.markdown(f"**ID:** `{tenant['tenant_id']}`")
    if tenant.get("branding", {}).get("footer_text"):
        st.caption(tenant["branding"]["footer_text"])

    st.divider()
    st.subheader("📜 Reglas Jurídicas")
    for rule in tenant.get("legal_rules", []):
        st.markdown(f"- {rule}")

# --- Formulario ---

st.subheader("📝 Datos del Documento")

template_id = st.text_input("Plantilla (template_id)", value="REQ-PENSIONAL-V1")

metadata = {}
for field in tenant.get("required_fields", []):
    label = FIELD_LABELS.get(field, field)
    if field in TEXT_AREA_FIELDS:
        metadata[field] = st.text_area(label, height=120)
    else:
        metadata[field] = st.text_input(label)

st.divider()

# --- Generación ---

if st.button("🚀 Generar Documento", type="primary", use_container_width=True):
    missing = [FIELD_LABELS.get(f, f) for f in tenant.get("required_fields", []) if not metadata.get(f)]
    if missing:
        st.error(f"Campos obligatorios vacíos: {', '.join(missing)}")
    else:
        with st.spinner("Generando documento con IA..."):
            try:
                result = generate_document(tenant["tenant_id"], template_id, metadata)
                st.session_state["last_result"] = result
                st.success("✅ Documento generado exitosamente")
            except requests.HTTPError as e:
                st.error(f"Error del servidor: {e.response.text}")
            except requests.ConnectionError:
                st.error("No se pudo conectar con la API. Verifica que el servidor esté corriendo en http://localhost:8000")

# --- Resultado ---

if "last_result" in st.session_state:
    result = st.session_state["last_result"]

    st.divider()
    st.subheader("📄 Resultado")

    col1, col2 = st.columns(2)
    col1.metric("Estado", result["status"])
    col2.metric("Transaction ID", result["transaction_id"][:8] + "...")

    try:
        file_bytes = download_file(result["download_url"])
        file_name = result["download_url"].split("/")[-1]
        st.download_button(
            label="📥 Descargar Documento DOCX",
            data=file_bytes,
            file_name=file_name,
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            use_container_width=True,
        )
    except Exception:
        st.warning(f"Descarga manual: {API_BASE}{result['download_url']}")
