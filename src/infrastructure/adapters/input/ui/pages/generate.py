"""Page: Generate Document — form, AI generation, preview & download."""

from __future__ import annotations

import requests
import streamlit as st

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
    PREVIEW_FONT_FAMILY,
    PREVIEW_FONT_SIZE,
    PREVIEW_MAX_HEIGHT,
    TEXT_AREA_FIELDS,
    TEXT_AREA_HEIGHT,
)
from ..state import is_api_online, load_templates, load_tenants


# ---------------------------------------------------------------------------
# API helpers
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
    if field.get("label"):
        return field["label"]
    return FIELD_LABELS.get(field["key"], field["key"].replace("_", " ").title())


def _clear_form_keys() -> None:
    """Remove cached form widget values so fields reload correctly."""
    for k in list(st.session_state.keys()):
        if k.startswith(("gen_", "rule_")):
            del st.session_state[k]


# ---------------------------------------------------------------------------
# Render
# ---------------------------------------------------------------------------

def render() -> None:
    st.subheader("📄 Generar Documento")

    # --- API health ---
    if not is_api_online():
        st.error(MSG_API_OFFLINE.format(api_base=API_BASE))

    # --- Load data fresh every render ---
    tenants = load_tenants()
    active_tenants = [t for t in tenants if t.get("active", True)]
    if not active_tenants:
        st.warning(MSG_NO_TENANTS.format(page=PAGE_COMPANY))
        return

    all_templates = load_templates()
    if not all_templates:
        st.warning(MSG_NO_TEMPLATES.format(page=PAGE_TEMPLATES))
        return

    tenant_names = [t["name"] for t in active_tenants]
    tenant_map = {t["name"]: t for t in active_tenants}

    # --- Detect if available options changed (new tenant/template created) ---
    template_ids = sorted(t["template_id"] for t in all_templates)
    prev_tenant_names = st.session_state.get("_gen_tenant_names")
    prev_template_ids = st.session_state.get("_gen_template_ids")

    if prev_tenant_names != tenant_names or prev_template_ids != template_ids:
        _clear_form_keys()
        st.session_state["_gen_tenant_names"] = tenant_names
        st.session_state["_gen_template_ids"] = template_ids

    # --- Tenant selector ---
    selected_name = st.selectbox("Empresa", options=tenant_names, key="gen_tenant")
    tenant = tenant_map[selected_name]

    # --- Detect tenant switch → clear form fields ---
    if st.session_state.get("_gen_prev_tenant") != tenant["tenant_id"]:
        prev = st.session_state.get("_gen_prev_tenant")
        st.session_state["_gen_prev_tenant"] = tenant["tenant_id"]
        if prev is not None:
            _clear_form_keys()
            st.rerun()

    # --- Filter compatible templates ---
    tenant_fields = set(tenant.get("required_fields", []))
    compatible_templates = [
        t for t in all_templates
        if not tenant_fields or {f["key"] for f in t.get("fields", []) if f.get("required")} <= tenant_fields
    ]
    if not compatible_templates:
        compatible_templates = all_templates

    template_map = {t["template_id"]: t for t in compatible_templates}
    selected_template_id = st.selectbox(
        "Plantilla",
        options=list(template_map.keys()),
        format_func=lambda tid: f"{tid} — {template_map[tid].get('name', '')}",
        key="gen_template",
    )
    template = template_map[selected_template_id]

    # --- Detect template switch → clear form fields ---
    if st.session_state.get("_gen_prev_template") != selected_template_id:
        prev = st.session_state.get("_gen_prev_template")
        st.session_state["_gen_prev_template"] = selected_template_id
        if prev is not None:
            for k in list(st.session_state.keys()):
                if k.startswith("gen_") and k not in ("gen_tenant", "gen_template"):
                    del st.session_state[k]
            st.rerun()

    if template.get("description"):
        st.caption(template["description"])

    # --- Legal rules with checkboxes ---
    available_rules = tenant.get("legal_rules", [])
    selected_rules: list[str] = []
    if available_rules:
        st.markdown("**📜 Reglas jurídicas a aplicar:**")
        for rule in available_rules:
            if st.checkbox(rule, value=True, key=f"rule_{hash(rule)}"):
                selected_rules.append(rule)

    st.divider()

    # --- Dynamic fields from template ---
    st.markdown("**📝 Datos del documento**")
    metadata: dict[str, str] = {}
    for field in template.get("fields", []):
        field_key = field["key"]
        label = _resolve_label(field)
        required = field.get("required", False)
        display_label = f"{label} *" if required else label

        if field_key in TEXT_AREA_FIELDS:
            metadata[field_key] = st.text_area(display_label, height=TEXT_AREA_HEIGHT, key=f"gen_{field_key}")
        else:
            metadata[field_key] = st.text_input(display_label, key=f"gen_{field_key}")

    st.divider()

    # --- Generate ---
    if st.button("🚀 Generar Documento", type="primary", use_container_width=True, key="gen_btn"):
        missing = [
            _resolve_label(f)
            for f in template.get("fields", [])
            if f.get("required") and not metadata.get(f["key"], "").strip()
        ]

        if missing:
            st.error(MSG_MISSING_FIELDS.format(fields=", ".join(missing)))
            return

        with st.spinner(MSG_GENERATING):
            try:
                result = _call_generate(
                    tenant_id=tenant["tenant_id"],
                    template_id=selected_template_id,
                    metadata=metadata,
                    selected_rules=selected_rules if available_rules else None,
                )
                st.session_state["last_result"] = result
                st.session_state["last_tenant"] = tenant
            except requests.HTTPError as e:
                st.error(f"Error: {e.response.text}")
                return
            except requests.ConnectionError:
                st.error(MSG_CONNECTION_ERROR.format(api_base=API_BASE))
                return

        st.success(MSG_SUCCESS)

    # --- Preview & Download ---
    if "last_result" not in st.session_state:
        return

    result = st.session_state["last_result"]
    branding = st.session_state.get("last_tenant", {}).get("branding", {})

    st.divider()
    st.subheader("👁️ Previsualización")

    col1, col2 = st.columns(2)
    col1.metric("Estado", result["status"])
    col2.metric("ID", result["transaction_id"][:12] + "…")

    try:
        file_bytes = _download(result["download_url"])
        file_name = result["download_url"].split("/")[-1]
    except Exception:
        st.warning(f"Descarga manual: {API_BASE}{result['download_url']}")
        return

    header_text = branding.get("header_text", "")
    footer_text = branding.get("footer_text", "")
    primary_color = branding.get("primary_color", DEFAULT_PRIMARY_COLOR)

    _render_preview(file_bytes, header_text, footer_text, primary_color)

    st.download_button(
        label="📥 Descargar DOCX",
        data=file_bytes,
        file_name=file_name,
        mime=DOCX_MIME,
        use_container_width=True,
        key="gen_download",
    )


# ---------------------------------------------------------------------------
# DOCX preview with formatting
# ---------------------------------------------------------------------------

def _render_preview(
    file_bytes: bytes,
    header_text: str,
    footer_text: str,
    primary_color: str,
) -> None:
    try:
        import io
        from docx import Document

        doc = Document(io.BytesIO(file_bytes))
        paragraphs_html = _extract_paragraphs_html(doc)
    except Exception:
        st.info("No se pudo generar la previsualización.")
        return

    body_html = "\n".join(paragraphs_html)

    preview_html = f"""
    <div style="
        border:1px solid #ddd; border-radius:8px; padding:24px;
        max-height:{PREVIEW_MAX_HEIGHT}px; overflow-y:auto; background:#fff; color:#222;
        font-family:{PREVIEW_FONT_FAMILY}; font-size:{PREVIEW_FONT_SIZE}; line-height:1.6;
    ">
        <div style="text-align:center; font-weight:bold; font-size:16px;
                    color:{primary_color}; margin-bottom:12px;">
            {header_text}
        </div>
        {body_html}
        <hr style="margin-top:20px;">
        <div style="text-align:center; font-size:10px; color:#888; font-style:italic;">
            {footer_text}
        </div>
    </div>
    """
    st.markdown(preview_html, unsafe_allow_html=True)


def _extract_paragraphs_html(doc) -> list[str]:
    result: list[str] = []
    for para in doc.paragraphs:
        if not para.text.strip():
            result.append("<br>")
            continue
        runs_html = ""
        for run in para.runs:
            text = run.text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            if run.bold and run.italic:
                text = f"<b><i>{text}</i></b>"
            elif run.bold:
                text = f"<b>{text}</b>"
            elif run.italic:
                text = f"<i>{text}</i>"
            runs_html += text
        if runs_html.strip():
            result.append(f"<p style='margin:4px 0;'>{runs_html}</p>")
    return result
