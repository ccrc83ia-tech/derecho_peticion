"""Page: Company — create/edit tenant with professional branding."""

from __future__ import annotations

import uuid

import streamlit as st
import streamlit_antd_components as sac

from ..components import card, col_header, page_header, section_title, segmented, spacer
from ..constants import (
    DEFAULT_PRIMARY_COLOR,
    HEX_COLOR_PATTERN,
    MSG_CONFIRM_DELETE,
    MSG_DELETED,
    MSG_INVALID_COLOR,
    MSG_SAVED,
)
from ..state import delete_tenant, load_tenants, upsert_tenant


def _empty_tenant() -> dict:
    return {
        "tenant_id": str(uuid.uuid4()),
        "name": "",
        "active": True,
        "system_prompt": "",
        "legal_rules": [],
        "required_fields": [],
        "branding": {
            "logo_url": "",
            "header_text": "",
            "footer_text": "",
            "primary_color": DEFAULT_PRIMARY_COLOR,
            "nit": "",
            "address": "",
            "phone": "",
            "email": "",
            "website": "",
        },
    }


def _populate_keys(tenant: dict) -> None:
    branding = tenant.get("branding", {})
    color = branding.get("primary_color", DEFAULT_PRIMARY_COLOR)
    st.session_state["co_name"] = tenant.get("name", "")
    st.session_state["co_active"] = tenant.get("active", True)
    st.session_state["co_nit"] = branding.get("nit", "")
    st.session_state["co_address"] = branding.get("address", "")
    st.session_state["co_phone"] = branding.get("phone", "")
    st.session_state["co_email"] = branding.get("email", "")
    st.session_state["co_website"] = branding.get("website", "")
    st.session_state["co_logo"] = branding.get("logo_url", "")
    st.session_state["co_header"] = branding.get("header_text", "")
    st.session_state["co_footer"] = branding.get("footer_text", "")
    st.session_state["co_color"] = color
    st.session_state["co_color_hex"] = color


def _on_picker_change() -> None:
    st.session_state["co_color_hex"] = st.session_state["co_color"]


def _on_hex_change() -> None:
    val = st.session_state["co_color_hex"]
    if HEX_COLOR_PATTERN.match(val):
        st.session_state["co_color"] = val


# ---------------------------------------------------------------------------
# Render
# ---------------------------------------------------------------------------

def render() -> None:
    page_header("🏢", "Configuración de Empresa",
                "Registre los datos de la empresa para generar documentos con membrete profesional.")

    tenants = load_tenants()
    tenant_map = {t["tenant_id"]: t for t in tenants}

    col_action, col_sel = st.columns([1, 2])
    with col_action:
        action = segmented(["➕ Crear nueva", "✏️ Editar existente"], key="co_action")

    is_edit = action == "✏️ Editar existente"

    if is_edit and not tenants:
        sac.alert(label="Sin empresas", description="No hay empresas. Cree una primero.", color="info", icon=True)
        return

    if is_edit:
        with col_sel:
            sel_id = st.selectbox(
                "Seleccionar empresa",
                options=list(tenant_map.keys()),
                format_func=lambda tid: f"{tenant_map[tid].get('name', '')}  ({tid[:8]}…)",
                key="co_sel",
            )
        tenant = tenant_map[sel_id].copy()
        context_key = f"edit_{sel_id}"
    else:
        tenant = _empty_tenant()
        context_key = "create_new"

    if st.session_state.get("_co_context") != context_key:
        st.session_state["_co_context"] = context_key
        st.session_state["_co_tenant_id"] = tenant["tenant_id"]
        _populate_keys(tenant)
        st.rerun()

    tenant_id = st.session_state.get("_co_tenant_id", tenant["tenant_id"])

    # ── Tabs ───────────────────────────────────────────────────────────────
    tab_data, tab_brand = st.tabs(["🏢 Datos de la Empresa", "🎨 Membrete y Branding"])

    with tab_data:
        col_name, col_nit = st.columns(2)
        with col_name:
            name = st.text_input("Nombre de la empresa *", key="co_name")
        with col_nit:
            nit = st.text_input("NIT / Identificación fiscal", key="co_nit")

        col_addr, col_phone = st.columns(2)
        with col_addr:
            address = st.text_input("Dirección", key="co_address")
        with col_phone:
            phone = st.text_input("Teléfono", key="co_phone")

        col_email, col_web = st.columns(2)
        with col_email:
            email = st.text_input("Email", key="co_email")
        with col_web:
            website = st.text_input("Sitio web", key="co_website")

        active = st.checkbox(
            "Empresa activa", key="co_active",
            help="Solo una empresa puede estar activa. Al activar esta, las demás se desactivarán.",
        )

    with tab_brand:
        col_h, col_f = st.columns(2)
        with col_h:
            header_text = st.text_input("Texto de encabezado", key="co_header")
        with col_f:
            footer_text = st.text_input("Texto de pie de página", key="co_footer")

        col_logo, col_color_pick, col_color_txt = st.columns([2, 1, 1])
        with col_logo:
            logo_url = st.text_input("URL del logo", key="co_logo")
        with col_color_pick:
            st.color_picker("Color primario", key="co_color", on_change=_on_picker_change)
        with col_color_txt:
            st.text_input("Código hex", key="co_color_hex", on_change=_on_hex_change)

        primary_color = st.session_state.get("co_color", DEFAULT_PRIMARY_COLOR)

        # Preview
        if header_text or logo_url:
            section_title("Vista previa del membrete")
            logo_html = (
                f"<img src='{logo_url}' style='max-height:40px; margin-bottom:8px;' /><br>"
                if logo_url else ""
            )
            contact_parts = [p for p in [address, phone, email] if p]
            contact_line = "  ·  ".join(contact_parts)
            card(
                f"{logo_html}"
                f"<span style='font-weight:700; color:{primary_color}; font-size:1.1rem;'>"
                f"{header_text}</span><br>"
                f"<span style='font-size:0.72rem; color:var(--text-secondary);'>{contact_line}</span><br>"
                f"<div style='border-top:1px solid var(--border-subtle); margin:0.8rem 0;'></div>"
                f"<span style='font-size:0.7rem; color:var(--text-secondary); font-style:italic;'>"
                f"{footer_text}</span>",
                style="text-align:center;",
            )

    # ── Actions ────────────────────────────────────────────────────────────
    spacer()
    col_save, col_del = st.columns([3, 1])

    with col_save:
        if st.button("💾 Guardar empresa", type="primary", use_container_width=True, key="co_save"):
            if not name.strip():
                sac.alert(label="Error", description="El nombre de la empresa es obligatorio.", color="error", icon=True)
                return
            if not HEX_COLOR_PATTERN.match(primary_color):
                sac.alert(label="Error", description=MSG_INVALID_COLOR, color="error", icon=True)
                return

            tenant_data = {
                "tenant_id": tenant_id,
                "name": name.strip(),
                "active": active,
                "system_prompt": "",
                "legal_rules": [],
                "required_fields": [],
                "branding": {
                    "logo_url": logo_url.strip(),
                    "header_text": header_text.strip(),
                    "footer_text": footer_text.strip(),
                    "primary_color": primary_color,
                    "nit": nit.strip(),
                    "address": address.strip(),
                    "phone": phone.strip(),
                    "email": email.strip(),
                    "website": website.strip(),
                },
            }
            upsert_tenant(tenant_data)
            sac.alert(label="Guardado", description="Empresa guardada correctamente.", color="success", icon=True)
            st.session_state["_co_context"] = None
            st.rerun()

    with col_del:
        if is_edit:
            if st.button("🗑️ Eliminar", use_container_width=True, key="co_delete"):
                st.session_state["_co_confirm_delete"] = True

    if st.session_state.get("_co_confirm_delete"):
        sac.alert(
            label="Confirmar eliminación",
            description=f"¿Está seguro de eliminar «{name}»? Esta acción no se puede deshacer.",
            color="warning", icon=True,
        )
        c1, c2 = st.columns(2)
        if c1.button("Sí, eliminar", key="co_yes"):
            delete_tenant(tenant_id)
            st.session_state["_co_confirm_delete"] = False
            st.session_state["_co_context"] = None
            sac.alert(label="Eliminado", description="Empresa eliminada.", color="info", icon=True)
            st.rerun()
        if c2.button("Cancelar", key="co_no"):
            st.session_state["_co_confirm_delete"] = False
            st.rerun()
