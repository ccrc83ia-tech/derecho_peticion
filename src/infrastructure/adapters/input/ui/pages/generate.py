"""Page: Generate Document — form, AI generation, preview & download."""

from __future__ import annotations

import requests
import streamlit as st
import streamlit_antd_components as sac

from ..components import page_header, section_title, spacer, stat_card
from ..constants import (
    API_BASE,
    API_GENERATE_PATH,
    API_TIMEOUT_DOWNLOAD,
    API_TIMEOUT_GENERATE,
    DEFAULT_PRIMARY_COLOR,
    DOCX_MIME,
    FIELD_LABELS,
    MSG_API_OFFLINE,
    MSG_CONNECTION_ERROR,
    MSG_GENERATING,
    MSG_MISSING_FIELDS,
    MSG_NO_TEMPLATES,
    MSG_NO_TENANTS,
    MSG_SUCCESS,
    PAGE_COMPANY,
    PAGE_TEMPLATES,
    PDF_MIME,
    TEXT_AREA_FIELDS,
    TEXT_AREA_HEIGHT,
)
from ..state import get_template_documents, is_api_online, load_entities, load_templates, load_tenants
from src.infrastructure.adapters.output.doc_generator import DocxEngine


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _call_generate(
    tenant_id: str,
    template_id: str,
    metadata: dict,
    selected_rules: list[str] | None = None,
) -> dict:
    payload: dict = {"template_id": template_id, "metadata": metadata}
    if selected_rules is not None:
        payload["selected_rules"] = selected_rules
    resp = requests.post(
        f"{API_BASE}{API_GENERATE_PATH}",
        headers={"X-Tenant-ID": tenant_id, "Content-Type": "application/json"},
        json=payload,
        timeout=API_TIMEOUT_GENERATE,
    )
    resp.raise_for_status()
    return resp.json()


def _download(download_url: str) -> bytes:
    resp = requests.get(f"{API_BASE}{download_url}", timeout=API_TIMEOUT_DOWNLOAD)
    resp.raise_for_status()
    return resp.content


def _resolve_label(field: dict) -> str:
    return field.get("label") or FIELD_LABELS.get(
        field["key"], field["key"].replace("_", " ").title()
    )


# ---------------------------------------------------------------------------
# Render
# ---------------------------------------------------------------------------

def render() -> None:
    page_header("📄", "Generar Documento",
                "Seleccione empresa, plantilla y complete los datos para generar un documento jurídico con IA.")

    if not is_api_online():
        sac.alert(
            label="API no disponible",
            description=f"Inicia el servidor en {API_BASE} antes de generar documentos.",
            color="error", icon=True, closable=True,
        )

    tenants = load_tenants()
    active_tenants = [t for t in tenants if t.get("active", True)]
    if not active_tenants:
        sac.alert(label="Sin empresas", description=MSG_NO_TENANTS.format(page=PAGE_COMPANY), color="warning", icon=True)
        return

    all_templates = load_templates()
    if not all_templates:
        sac.alert(label="Sin plantillas", description=MSG_NO_TEMPLATES.format(page=PAGE_TEMPLATES), color="warning", icon=True)
        return

    tenant_names = [t["name"] for t in active_tenants]
    tenant_map = {t["name"]: t for t in active_tenants}

    # ── Step 1: Configuration ──────────────────────────────────────────────
    section_title("① Configuración")

    col_t, col_p = st.columns(2)
    with col_t:
        selected_name = st.selectbox("Empresa", options=tenant_names, key="gen_tenant")
    tenant = tenant_map[selected_name]

    compatible = all_templates
    template_map = {t["template_id"]: t for t in compatible}
    with col_p:
        selected_template_id = st.selectbox(
            "Plantilla",
            options=list(template_map.keys()),
            format_func=lambda tid: f"{template_map[tid].get('name', '')}",
            key="gen_template",
        )
    template = template_map[selected_template_id]

    if template.get("description"):
        st.caption(template["description"])

    # ── Entity selection ───────────────────────────────────────────────────
    all_entities = load_entities()
    selected_entity: dict | None = None
    if all_entities:
        entity_map = {e["entity_id"]: e for e in all_entities}
        entity_options = [""] + list(entity_map.keys())

        def _fmt_entity(eid: str) -> str:
            if not eid:
                return "— Sin entidad destinataria —"
            e = entity_map[eid]
            t = f" ({e['entity_type']})" if e.get("entity_type") else ""
            return f"{e['name']}{t}"

        selected_eid = st.selectbox(
            "Entidad destinataria",
            options=entity_options,
            format_func=_fmt_entity,
            key="gen_entity",
        )
        if selected_eid:
            selected_entity = entity_map[selected_eid]

    # ── Step 2: Reference documents (RAG) ──────────────────────────────────
    rag_docs = get_template_documents(selected_template_id)
    available_rules = template.get("legal_rules", []) or tenant.get("legal_rules", [])
    selected_rules: list[str] = []
    has_sources = bool(rag_docs) or bool(available_rules)

    if has_sources:
        section_title("② Fuentes Jurídicas")

    if rag_docs:
        st.caption("Documentos de referencia cargados — la IA citará textualmente de estos.")
        doc_names = [d["doc_name"] for d in rag_docs]
        selected_doc_indices = sac.chip(
            items=[sac.ChipItem(label=name, icon="file-earmark-text") for name in doc_names],
            align="start",
            multiple=True,
            index=list(range(len(doc_names))),
            key="rag_doc_chips",
        )
        if selected_doc_indices is not None:
            for idx in selected_doc_indices:
                if isinstance(idx, int) and idx < len(doc_names):
                    selected_rules.append(doc_names[idx])
                elif isinstance(idx, str):
                    selected_rules.append(idx)

    if available_rules:
        st.caption("Reglas jurídicas configuradas en la plantilla.")
        rule_indices = sac.chip(
            items=[sac.ChipItem(label=rule, icon="book") for rule in available_rules],
            align="start",
            multiple=True,
            index=list(range(len(available_rules))),
            key="rule_chips",
        )
        if rule_indices is not None:
            for idx in rule_indices:
                if isinstance(idx, int) and idx < len(available_rules):
                    selected_rules.append(available_rules[idx])
                elif isinstance(idx, str):
                    selected_rules.append(idx)

    # ── Step 3: Form ──────────────────────────────────────────────────────
    step_num = "③" if has_sources else "②"
    section_title(f"{step_num} Datos del Documento")

    fields = template.get("fields", [])

    # Fields that the entity selection already covers
    _ENTITY_FIELD_KEYS = {"entidad_demandada", "entidad_nombre", "entidad_destino", "entidad"}

    with st.form("generate_form", clear_on_submit=False):
        field_widgets: dict[str, str] = {}
        for field in fields:
            # Skip entity fields when an entity is selected from the dropdown
            if selected_entity and field["key"] in _ENTITY_FIELD_KEYS:
                continue
            label = _resolve_label(field)
            display = f"{label} *" if field.get("required") else label
            if field["key"] in TEXT_AREA_FIELDS:
                field_widgets[field["key"]] = st.text_area(
                    display, height=TEXT_AREA_HEIGHT, key=f"gen_{field['key']}",
                )
            else:
                field_widgets[field["key"]] = st.text_input(
                    display, key=f"gen_{field['key']}",
                )

        submitted = st.form_submit_button(
            "🚀 Generar Documento",
            type="primary",
            use_container_width=True,
        )

    if not submitted:
        _show_last_result(tenant)
        return

    # ── Validate & generate ────────────────────────────────────────────────
    metadata = {k: v.strip() for k, v in field_widgets.items()}

    # Inject entity data into metadata
    if selected_entity:
        metadata["entidad_nombre"] = selected_entity.get("name", "")
        metadata["entidad_nit"] = selected_entity.get("nit", "")
        metadata["entidad_direccion"] = selected_entity.get("address", "")
        metadata["entidad_ciudad"] = selected_entity.get("city", "")
        metadata["entidad_telefono"] = selected_entity.get("phone", "")
        metadata["entidad_email"] = selected_entity.get("email", "")
        metadata["entidad_representante_legal"] = selected_entity.get("legal_rep", "")
        metadata["entidad_tipo"] = selected_entity.get("entity_type", "")

    tpl_prompt = template.get("system_prompt", "")
    if tpl_prompt:
        metadata["_system_prompt"] = tpl_prompt

    tpl_rules = template.get("legal_rules", [])
    if tpl_rules and not selected_rules:
        selected_rules = tpl_rules

    if rag_docs:
        metadata["_rag_sources"] = ",".join(selected_rules)

    # Pasar el modo estricto al backend
    metadata["_rag_strict"] = "1" if template.get("rag_strict", True) else "0"

    missing = [
        _resolve_label(f)
        for f in fields
        if f.get("required")
        and not metadata.get(f["key"], "")
        and not (selected_entity and f["key"] in _ENTITY_FIELD_KEYS)
    ]
    if missing:
        sac.alert(label="Campos faltantes", description=", ".join(missing), color="error", icon=True)
        return

    with st.spinner(MSG_GENERATING):
        try:
            result = _call_generate(
                tenant_id=tenant["tenant_id"],
                template_id=selected_template_id,
                metadata=metadata,
                selected_rules=selected_rules if has_sources else None,
            )
            st.session_state["last_result"] = result
            st.session_state["last_tenant"] = tenant
        except requests.HTTPError as e:
            st.error(f"Error: {e.response.text}")
            return
        except requests.ConnectionError:
            st.error(MSG_CONNECTION_ERROR.format(api_base=API_BASE))
            return

    sac.alert(label="Documento generado", description="El documento está listo para revisar y descargar.", color="success", icon=True)
    _show_last_result(tenant)


# ---------------------------------------------------------------------------
# Result preview
# ---------------------------------------------------------------------------

def _show_last_result(tenant: dict) -> None:
    if "last_result" not in st.session_state:
        return

    result = st.session_state["last_result"]
    branding = st.session_state.get("last_tenant", {}).get("branding", {})

    section_title("Resultado")

    col_s, col_id = st.columns([2, 3])
    with col_s:
        stat_card("✅", result["status"], value_style="font-size:1.4rem;")
    with col_id:
        stat_card(
            f"{result['transaction_id'][:16]}…",
            "Transaction ID",
            value_style="font-size:0.8rem; font-family:monospace;",
        )

    try:
        file_bytes = _download(result["download_url"])
        file_name = result["download_url"].split("/")[-1]
    except Exception:
        st.warning(f"Descarga manual: {API_BASE}{result['download_url']}")
        return

    raw_text = _extract_text(file_bytes)
    if raw_text is None:
        st.info("No se pudo leer el documento.")
        return

    if "last_doc_text" not in st.session_state or st.session_state.get("_last_tx") != result["transaction_id"]:
        st.session_state["last_doc_text"] = raw_text
        st.session_state["_last_tx"] = result["transaction_id"]

    section_title("Editar Documento")
    st.caption("Puede editar el texto antes de descargar. Use **texto** para negrilla y *texto* para cursiva.")

    edited_text = st.text_area(
        "Contenido del documento",
        value=st.session_state["last_doc_text"],
        height=400,
        key="doc_editor",
        label_visibility="collapsed",
    )
    st.session_state["last_doc_text"] = edited_text

    edited_bytes = _rebuild_docx(edited_text, branding)
    pdf_bytes = _rebuild_pdf(edited_text, branding)
    file_name_base = file_name.rsplit(".", 1)[0]

    col_dl_docx, col_dl_pdf, col_reset = st.columns([2, 2, 1])
    with col_dl_docx:
        st.download_button(
            label="📥 Descargar DOCX",
            data=edited_bytes,
            file_name=file_name,
            mime=DOCX_MIME,
            use_container_width=True,
            key="gen_download",
        )
    with col_dl_pdf:
        st.download_button(
            label="📥 Descargar PDF",
            data=pdf_bytes,
            file_name=f"{file_name_base}.pdf",
            mime=PDF_MIME,
            use_container_width=True,
            key="gen_download_pdf",
        )
    with col_reset:
        if st.button("🔄 Restaurar", use_container_width=True, key="gen_reset"):
            st.session_state["last_doc_text"] = raw_text
            st.rerun()


# ---------------------------------------------------------------------------
# DOCX helpers
# ---------------------------------------------------------------------------

def _extract_text(file_bytes: bytes) -> str | None:
    try:
        import io
        from docx import Document

        doc = Document(io.BytesIO(file_bytes))
        lines: list[str] = []
        for para in doc.paragraphs:
            if not para.text.strip():
                lines.append("")
                continue
            parts: list[str] = []
            for run in para.runs:
                text = run.text
                if not text:
                    continue
                if run.bold and run.italic:
                    text = f"***{text}***"
                elif run.bold:
                    text = f"**{text}**"
                elif run.italic:
                    text = f"*{text}*"
                parts.append(text)
            lines.append("".join(parts))
        return "\n".join(lines)
    except Exception:
        return None


def _rebuild_docx(text: str, branding: dict) -> bytes:
    return DocxEngine.build_bytes(text, branding)


def _rebuild_pdf(text: str, branding: dict) -> bytes:
    return DocxEngine.build_pdf_bytes(text, branding)
