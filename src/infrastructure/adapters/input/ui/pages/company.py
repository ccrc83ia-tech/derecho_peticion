"""Page: Company — create/edit tenant, branding & legal rules."""

from __future__ import annotations

import streamlit as st

from ..constants import DEFAULT_PRIMARY_COLOR, HEX_COLOR_PATTERN, MSG_CONFIRM_DELETE, MSG_DELETED, MSG_INVALID_COLOR, MSG_SAVED
from ..state import delete_tenant, load_tenants, upsert_tenant


def _empty_tenant() -> dict:
    return {
        "tenant_id": "",
        "name": "",
        "system_prompt": "",
        "legal_rules": [],
        "branding": {
            "logo_url": "",
            "header_text": "",
            "footer_text": "",
            "primary_color": DEFAULT_PRIMARY_COLOR,
        },
        "required_fields": [],
        "active": True,
    }


def _populate_keys(tenant: dict) -> None:
    """Write tenant data into session_state BEFORE widgets render."""
    branding = tenant.get("branding", {})
    st.session_state["co_id"] = tenant.get("tenant_id", "")
    st.session_state["co_name"] = tenant.get("name", "")
    st.session_state["co_active"] = tenant.get("active", True)
    st.session_state["co_prompt"] = tenant.get("system_prompt", "")
    st.session_state["co_header"] = branding.get("header_text", "")
    st.session_state["co_footer"] = branding.get("footer_text", "")
    st.session_state["co_logo"] = branding.get("logo_url", "")
    st.session_state["co_color"] = branding.get("primary_color", DEFAULT_PRIMARY_COLOR)
    st.session_state["co_req_fields"] = ", ".join(tenant.get("required_fields", []))
    st.session_state["co_rules"] = [
        {"text": r, "active": True} for r in tenant.get("legal_rules", [])
    ]
    # Clear dynamic rule widget keys
    for k in list(st.session_state.keys()):
        if k.startswith("cr_"):
            del st.session_state[k]


# ---------------------------------------------------------------------------
# Render
# ---------------------------------------------------------------------------

def render() -> None:
    st.subheader("🏢 Configuración de Empresa")

    tenants = load_tenants()
    tenant_map = {t["tenant_id"]: t for t in tenants}

    action = st.radio(
        "Acción",
        ["Crear nueva", "Editar existente"],
        horizontal=True,
        key="co_action",
    )

    if action == "Editar existente" and not tenants:
        st.info("No hay empresas. Cree una primero.")
        return

    # --- Context switch detection ---
    if action == "Editar existente":
        sel_id = st.selectbox(
            "Seleccionar empresa",
            options=list(tenant_map.keys()),
            format_func=lambda tid: f"{tid} — {tenant_map[tid].get('name', '')}",
            key="co_sel",
        )
        tenant = tenant_map[sel_id].copy()
        context_key = f"edit_{sel_id}"
    else:
        tenant = _empty_tenant()
        context_key = "create_new"

    if st.session_state.get("_co_context") != context_key:
        st.session_state["_co_context"] = context_key
        _populate_keys(tenant)
        st.rerun()

    st.divider()

    # --- Basic info (widgets read from session_state via key, no value param) ---
    tenant["tenant_id"] = st.text_input(
        "ID de empresa *",
        disabled=action == "Editar existente",
        key="co_id",
    )
    tenant["name"] = st.text_input("Nombre *", key="co_name")
    tenant["active"] = st.checkbox("Activa", key="co_active")
    tenant["system_prompt"] = st.text_area(
        "System Prompt (instrucciones para la IA) *",
        height=120,
        key="co_prompt",
    )

    st.divider()

    # --- Branding ---
    st.markdown("**🎨 Branding**")

    b_col1, b_col2 = st.columns(2)
    header_text = b_col1.text_input("Texto encabezado", key="co_header")
    footer_text = b_col2.text_input("Texto pie de página", key="co_footer")

    b_col3, b_col4 = st.columns(2)
    logo_url = b_col3.text_input("URL del logo", key="co_logo")
    primary_color = b_col4.color_picker("Color primario", key="co_color")

    tenant["branding"] = {
        "header_text": header_text,
        "footer_text": footer_text,
        "logo_url": logo_url,
        "primary_color": primary_color,
    }

    # --- Preview branding ---
    if header_text:
        st.markdown(
            f"<div style='border:1px solid #ddd; border-radius:6px; padding:12px; "
            f"text-align:center; font-weight:bold; color:{primary_color};'>"
            f"{header_text}<br>"
            f"<span style='font-size:10px; font-style:italic; color:#888;'>"
            f"{footer_text}</span></div>",
            unsafe_allow_html=True,
        )

    st.divider()

    # --- Legal rules ---
    st.markdown("**📜 Reglas Jurídicas**")
    st.caption("Agregue reglas y marque las que desea que estén activas por defecto.")

    if "co_rules" not in st.session_state:
        st.session_state["co_rules"] = [
            {"text": r, "active": True} for r in tenant.get("legal_rules", [])
        ]

    rules_state: list[dict] = st.session_state["co_rules"]

    to_remove: int | None = None
    for i, rule in enumerate(rules_state):
        cols = st.columns([1, 8, 1])
        rule["active"] = cols[0].checkbox(
            "Activa", value=rule.get("active", True),
            key=f"cr_chk_{i}", label_visibility="collapsed",
        )
        rule["text"] = cols[1].text_input(
            "Regla", value=rule.get("text", ""),
            key=f"cr_txt_{i}", label_visibility="collapsed",
        )
        if cols[2].button("🗑️", key=f"cr_del_{i}"):
            to_remove = i

    if to_remove is not None:
        rules_state.pop(to_remove)
        st.session_state["co_rules"] = rules_state
        st.rerun()

    if st.button("➕ Agregar regla", key="co_add_rule"):
        rules_state.append({"text": "", "active": True})
        st.session_state["co_rules"] = rules_state
        st.rerun()

    st.divider()

    # --- Required fields ---
    st.markdown("**📋 Campos requeridos al generar**")
    st.caption("Lista de claves de campos que el usuario debe completar (separados por coma).")
    raw_fields = st.text_input("Campos requeridos", key="co_req_fields")
    tenant["required_fields"] = [f.strip() for f in raw_fields.split(",") if f.strip()]

    st.divider()

    # --- Save / Delete ---
    col_save, col_del = st.columns([3, 1])

    with col_save:
        if st.button("💾 Guardar empresa", type="primary", use_container_width=True, key="co_save"):
            if not tenant["tenant_id"].strip() or not tenant["name"].strip():
                st.error("ID y Nombre son obligatorios.")
                return
            if not HEX_COLOR_PATTERN.match(tenant["branding"].get("primary_color", DEFAULT_PRIMARY_COLOR)):
                st.error(MSG_INVALID_COLOR)
                return
            tenant["legal_rules"] = [
                r["text"] for r in rules_state if r.get("text", "").strip() and r.get("active", True)
            ]
            upsert_tenant(tenant)
            st.success(MSG_SAVED)
            # Force reload on next render
            st.session_state["_co_context"] = None
            st.rerun()

    with col_del:
        if action == "Editar existente":
            if st.button("🗑️ Eliminar", use_container_width=True, key="co_delete"):
                st.session_state["_co_confirm_delete"] = True

    if st.session_state.get("_co_confirm_delete"):
        st.warning(MSG_CONFIRM_DELETE.format(name=tenant["name"]))
        c1, c2 = st.columns(2)
        if c1.button("Sí, eliminar", key="co_yes"):
            delete_tenant(tenant["tenant_id"])
            st.session_state["_co_confirm_delete"] = False
            st.session_state["_co_context"] = None
            st.success(MSG_DELETED)
            st.rerun()
        if c2.button("Cancelar", key="co_no"):
            st.session_state["_co_confirm_delete"] = False
            st.rerun()
