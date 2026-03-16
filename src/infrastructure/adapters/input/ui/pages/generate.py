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
    st.markdown(
        "<div class='page-header'>"
        "<h2>📄 Generar Documento</h2>"
        "<p>Seleccione empresa, plantilla y complete los datos para generar "
        "un documento jurídico con IA.</p>"
        "</div>",
        unsafe_allow_html=True,
    )

    if not is_api_online():
        st.error(MSG_API_OFFLINE.format(api_base=API_BASE))

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

    # ── Selectors (outside form so they update immediately) ────────────────
    st.markdown(
        "<div class='section-title'>Configuración</div>",
        unsafe_allow_html=True,
    )

    col_t, col_p = st.columns(2)
    with col_t:
        selected_name = st.selectbox(
            "Empresa", options=tenant_names, key="gen_tenant",
        )
    tenant = tenant_map[selected_name]

    # Compatible templates
    compatible = all_templates
    template_map = {t["template_id"]: t for t in compatible}
    with col_p:
        selected_template_id = st.selectbox(
            "Plantilla",
            options=list(template_map.keys()),
            format_func=lambda tid: f"{tid} — {template_map[tid].get('name', '')}",
            key="gen_template",
        )
    template = template_map[selected_template_id]

    if template.get("description"):
        st.caption(template["description"])

    # ── Legal rules ────────────────────────────────────────────────────────
    available_rules = template.get("legal_rules", []) or tenant.get("legal_rules", [])
    selected_rules: list[str] = []
    if available_rules:
        st.markdown(
            "<div class='section-title'>Reglas Jurídicas</div>",
            unsafe_allow_html=True,
        )
        rule_cols = st.columns(min(len(available_rules), 3))
        for i, rule in enumerate(available_rules):
            with rule_cols[i % len(rule_cols)]:
                if st.checkbox(rule, value=True, key=f"rule_{hash(rule)}"):
                    selected_rules.append(rule)

    # ── Form (ensures all widget values are submitted together) ────────────
    st.markdown(
        "<div class='section-title'>Datos del Documento</div>",
        unsafe_allow_html=True,
    )

    fields = template.get("fields", [])

    with st.form("generate_form", clear_on_submit=False):
        field_widgets: dict[str, str] = {}
        for field in fields:
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

    # Inject template prompt so the use case can use it
    tpl_prompt = template.get("system_prompt", "")
    if tpl_prompt:
        metadata["_system_prompt"] = tpl_prompt

    # Use template legal_rules as selected_rules if no tenant rules
    tpl_rules = template.get("legal_rules", [])
    if tpl_rules and not selected_rules:
        selected_rules = tpl_rules

    missing = [
        _resolve_label(f)
        for f in fields
        if f.get("required") and not metadata.get(f["key"], "")
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
    _show_last_result(tenant)


# ---------------------------------------------------------------------------
# Result preview
# ---------------------------------------------------------------------------

def _show_last_result(tenant: dict) -> None:
    if "last_result" not in st.session_state:
        return

    result = st.session_state["last_result"]
    branding = st.session_state.get("last_tenant", {}).get("branding", {})

    st.markdown(
        "<div class='section-title'>Resultado</div>", unsafe_allow_html=True,
    )

    col_s, col_id = st.columns([2, 3])
    col_s.markdown(
        f"<div class='stat-card'>"
        f"<div class='stat-card-value' style='font-size:1.2rem;'>✅</div>"
        f"<div class='stat-card-label'>{result['status']}</div></div>",
        unsafe_allow_html=True,
    )
    col_id.markdown(
        f"<div class='stat-card'>"
        f"<div class='stat-card-value' style='font-size:0.85rem;'>"
        f"{result['transaction_id'][:16]}</div>"
        f"<div class='stat-card-label'>Transaction ID</div></div>",
        unsafe_allow_html=True,
    )

    try:
        file_bytes = _download(result["download_url"])
        file_name = result["download_url"].split("/")[-1]
    except Exception:
        st.warning(f"Descarga manual: {API_BASE}{result['download_url']}")
        return

    # Extract text from DOCX for editable preview
    raw_text = _extract_text(file_bytes)
    if raw_text is None:
        st.info("No se pudo leer el documento.")
        return

    # Store original text on first load
    if "last_doc_text" not in st.session_state or st.session_state.get("_last_tx") != result["transaction_id"]:
        st.session_state["last_doc_text"] = raw_text
        st.session_state["_last_tx"] = result["transaction_id"]

    st.markdown(
        "<div class='section-title'>Editar Documento</div>",
        unsafe_allow_html=True,
    )
    st.caption("Puede editar el texto antes de descargar. Use **texto** para negrilla y *texto* para cursiva.")

    edited_text = st.text_area(
        "Contenido del documento",
        value=st.session_state["last_doc_text"],
        height=400,
        key="doc_editor",
        label_visibility="collapsed",
    )
    st.session_state["last_doc_text"] = edited_text

    # Rebuild DOCX from edited text
    edited_bytes = _rebuild_docx(edited_text, branding)

    col_dl, col_reset = st.columns([3, 1])
    with col_dl:
        st.download_button(
            label="📥 Descargar DOCX",
            data=edited_bytes,
            file_name=file_name,
            mime=DOCX_MIME,
            use_container_width=True,
            key="gen_download",
        )
    with col_reset:
        if st.button("🔄 Restaurar original", use_container_width=True, key="gen_reset"):
            st.session_state["last_doc_text"] = raw_text
            st.rerun()


# ---------------------------------------------------------------------------
# DOCX helpers
# ---------------------------------------------------------------------------

def _extract_text(file_bytes: bytes) -> str | None:
    """Extract plain text from DOCX, preserving bold/italic as markdown."""
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
    """Rebuild a DOCX from edited text with branding."""
    import io
    import re
    from docx import Document
    from docx.shared import Pt, RGBColor, Cm
    from docx.enum.text import WD_ALIGN_PARAGRAPH

    doc = Document()
    for section in doc.sections:
        section.top_margin = Cm(2)
        section.bottom_margin = Cm(2)
        section.left_margin = Cm(2.5)
        section.right_margin = Cm(2.5)

    primary_color = branding.get("primary_color", DEFAULT_PRIMARY_COLOR)
    try:
        h = primary_color.lstrip("#")
        rgb = RGBColor(int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))
    except (ValueError, IndexError):
        rgb = RGBColor(0, 0, 0)

    # Header
    header_text = branding.get("header_text", "")
    if header_text:
        hp = doc.add_paragraph()
        hp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        hr = hp.add_run(header_text)
        hr.bold = True
        hr.font.size = Pt(14)
        hr.font.color.rgb = rgb

        contact = [p for p in [
            branding.get("nit", ""), branding.get("address", ""),
            branding.get("phone", ""), branding.get("email", ""),
        ] if p]
        if contact:
            cp = doc.add_paragraph()
            cp.alignment = WD_ALIGN_PARAGRAPH.CENTER
            cr = cp.add_run(" · ".join(contact))
            cr.font.size = Pt(8)
            cr.font.color.rgb = RGBColor(120, 120, 120)

        doc.add_paragraph("─" * 60)

    # Body with markdown parsing
    pattern = re.compile(r"(\*\*\*(.+?)\*\*\*|\*\*(.+?)\*\*|\*(.+?)\*)")
    for line in text.split("\n"):
        stripped = line.strip()
        if not stripped:
            doc.add_paragraph("")
            continue
        para = doc.add_paragraph()
        last_end = 0
        for match in pattern.finditer(stripped):
            if match.start() > last_end:
                para.add_run(stripped[last_end:match.start()])
            if match.group(2):
                r = para.add_run(match.group(2))
                r.bold = True
                r.italic = True
            elif match.group(3):
                r = para.add_run(match.group(3))
                r.bold = True
            elif match.group(4):
                r = para.add_run(match.group(4))
                r.italic = True
            last_end = match.end()
        if last_end < len(stripped):
            para.add_run(stripped[last_end:])

    # Footer
    footer_text = branding.get("footer_text", "")
    if footer_text:
        doc.add_paragraph("")
        doc.add_paragraph("─" * 60)
        fp = doc.add_paragraph()
        fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        fr = fp.add_run(footer_text)
        fr.font.size = Pt(8)
        fr.italic = True
        fr.font.color.rgb = RGBColor(120, 120, 120)

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()
