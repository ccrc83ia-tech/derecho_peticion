"""Page: Templates — create, edit and delete document templates."""

from __future__ import annotations

import streamlit as st

from ..constants import MSG_CONFIRM_DELETE, MSG_DELETED, MSG_SAVED
from ..state import delete_template, load_templates, upsert_template


def _empty_template() -> dict:
    return {"template_id": "", "name": "", "description": "", "fields": []}


def _populate_keys(tpl: dict) -> None:
    """Write template data into session_state BEFORE widgets render."""
    st.session_state["tpl_id"] = tpl.get("template_id", "")
    st.session_state["tpl_name"] = tpl.get("name", "")
    st.session_state["tpl_desc"] = tpl.get("description", "")
    st.session_state["tpl_fields"] = [f.copy() for f in tpl.get("fields", [])]
    # Clear dynamic field widget keys
    for k in list(st.session_state.keys()):
        if k.startswith(("fk_", "fl_", "fr_", "fd_")):
            del st.session_state[k]


# ---------------------------------------------------------------------------
# Render
# ---------------------------------------------------------------------------

def render() -> None:
    st.subheader("📋 Gestión de Plantillas")

    templates = load_templates()
    template_map = {t["template_id"]: t for t in templates}

    action = st.radio(
        "Acción",
        ["Crear nueva", "Editar existente"],
        horizontal=True,
        key="tpl_action",
    )

    if action == "Editar existente" and not templates:
        st.info("No hay plantillas. Cree una primero.")
        return

    # --- Context switch detection ---
    if action == "Editar existente":
        sel_id = st.selectbox(
            "Seleccionar plantilla",
            options=list(template_map.keys()),
            format_func=lambda tid: f"{tid} — {template_map[tid].get('name', '')}",
            key="tpl_sel",
        )
        tpl = template_map[sel_id].copy()
        context_key = f"edit_{sel_id}"
    else:
        tpl = _empty_template()
        context_key = "create_new"

    if st.session_state.get("_tpl_context") != context_key:
        st.session_state["_tpl_context"] = context_key
        _populate_keys(tpl)
        st.rerun()

    st.divider()

    # --- Basic info (widgets read from session_state via key, no value param) ---
    tpl["template_id"] = st.text_input(
        "ID de plantilla *",
        disabled=action == "Editar existente",
        key="tpl_id",
    )
    tpl["name"] = st.text_input("Nombre *", key="tpl_name")
    tpl["description"] = st.text_area("Descripción", height=80, key="tpl_desc")

    st.divider()

    # --- Dynamic fields ---
    st.markdown("**📝 Campos del formulario**")
    st.caption("Defina los campos que el usuario debe completar al generar un documento con esta plantilla.")

    if "tpl_fields" not in st.session_state:
        st.session_state["tpl_fields"] = [f.copy() for f in tpl.get("fields", [])]

    current_fields: list[dict] = st.session_state["tpl_fields"]

    to_remove: int | None = None
    for i, field in enumerate(current_fields):
        with st.container():
            cols = st.columns([3, 3, 1, 1])
            field["key"] = cols[0].text_input("Clave", value=field.get("key", ""), key=f"fk_{i}")
            field["label"] = cols[1].text_input("Etiqueta", value=field.get("label", ""), key=f"fl_{i}")
            field["required"] = cols[2].checkbox("Req.", value=field.get("required", False), key=f"fr_{i}")
            if cols[3].button("🗑️", key=f"fd_{i}"):
                to_remove = i

    if to_remove is not None:
        current_fields.pop(to_remove)
        st.session_state["tpl_fields"] = current_fields
        st.rerun()

    if st.button("➕ Agregar campo", key="tpl_add_field"):
        current_fields.append({"key": "", "label": "", "required": False})
        st.session_state["tpl_fields"] = current_fields
        st.rerun()

    st.divider()

    # --- Save ---
    col_save, col_del = st.columns([3, 1])

    with col_save:
        if st.button("💾 Guardar plantilla", type="primary", use_container_width=True, key="tpl_save"):
            if not tpl["template_id"].strip() or not tpl["name"].strip():
                st.error("ID y Nombre son obligatorios.")
                return
            tpl["fields"] = [f for f in current_fields if f.get("key", "").strip()]
            upsert_template(tpl)
            st.success(MSG_SAVED)
            st.session_state["_tpl_context"] = None
            st.rerun()

    with col_del:
        if action == "Editar existente":
            if st.button("🗑️ Eliminar", use_container_width=True, key="tpl_delete"):
                st.session_state["_tpl_confirm_delete"] = True

    if st.session_state.get("_tpl_confirm_delete"):
        st.warning(MSG_CONFIRM_DELETE.format(name=tpl["template_id"]))
        c1, c2 = st.columns(2)
        if c1.button("Sí, eliminar", key="tpl_yes"):
            delete_template(tpl["template_id"])
            st.session_state["_tpl_confirm_delete"] = False
            st.session_state["_tpl_context"] = None
            st.success(MSG_DELETED)
            st.rerun()
        if c2.button("Cancelar", key="tpl_no"):
            st.session_state["_tpl_confirm_delete"] = False
            st.rerun()
