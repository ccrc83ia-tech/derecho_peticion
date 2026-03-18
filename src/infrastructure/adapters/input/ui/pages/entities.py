"""Page: Entities — manage recipient organizations for documents."""

from __future__ import annotations

import uuid

import streamlit as st
import streamlit_antd_components as sac

from ..components import empty_state, page_header, section_title, segmented, spacer
from ..constants import ENTITY_TYPES
from ..state import delete_entity, load_entities, upsert_entity


def _empty_entity() -> dict:
    return {
        "entity_id": str(uuid.uuid4()),
        "name": "", "nit": "", "address": "", "city": "",
        "phone": "", "email": "", "legal_rep": "",
        "entity_type": "", "notes": "",
    }


def _populate_keys(ent: dict) -> None:
    st.session_state["ent_name"] = ent.get("name", "")
    st.session_state["ent_nit"] = ent.get("nit", "")
    st.session_state["ent_address"] = ent.get("address", "")
    st.session_state["ent_city"] = ent.get("city", "")
    st.session_state["ent_phone"] = ent.get("phone", "")
    st.session_state["ent_email"] = ent.get("email", "")
    st.session_state["ent_legal_rep"] = ent.get("legal_rep", "")
    st.session_state["ent_type"] = ent.get("entity_type", "")
    st.session_state["ent_notes"] = ent.get("notes", "")


# ---------------------------------------------------------------------------
# Render
# ---------------------------------------------------------------------------

def render() -> None:
    page_header("🏛️", "Entidades Destinatarias",
                "Registre las entidades a las que se dirigen los documentos (EPS, bancos, entidades públicas, etc.).")

    entities = load_entities()
    entity_map = {e["entity_id"]: e for e in entities}

    col_action, col_sel = st.columns([1, 2])
    with col_action:
        action = segmented(["➕ Crear nueva", "✏️ Editar existente"], key="ent_action")

    is_edit = action == "✏️ Editar existente"

    if is_edit and not entities:
        sac.alert(label="Sin entidades", description="No hay entidades registradas. Cree una primero.", color="info", icon=True)
        return

    if is_edit:
        with col_sel:
            sel_id = st.selectbox(
                "Seleccionar entidad",
                options=list(entity_map.keys()),
                format_func=lambda eid: f"{entity_map[eid]['name']}  ({entity_map[eid].get('entity_type', '')})",
                key="ent_sel",
            )
        entity = entity_map[sel_id].copy()
        context_key = f"edit_{sel_id}"
    else:
        entity = _empty_entity()
        context_key = "create_new"

    if st.session_state.get("_ent_context") != context_key:
        st.session_state["_ent_context"] = context_key
        st.session_state["_ent_id"] = entity["entity_id"]
        _populate_keys(entity)
        st.rerun()

    entity_id = st.session_state.get("_ent_id", entity["entity_id"])

    # ── Tabs ───────────────────────────────────────────────────────────────
    tab_data, tab_contact = st.tabs(["🏛️ Datos de la Entidad", "📞 Contacto y Notas"])

    with tab_data:
        col_name, col_type = st.columns(2)
        with col_name:
            name = st.text_input("Nombre de la entidad *", key="ent_name")
        with col_type:
            type_options = [""] + ENTITY_TYPES
            current_type = st.session_state.get("ent_type", "")
            type_idx = type_options.index(current_type) if current_type in type_options else 0
            entity_type = st.selectbox("Tipo de entidad", options=type_options, index=type_idx, key="ent_type")

        col_nit, col_city = st.columns(2)
        with col_nit:
            nit = st.text_input("NIT / Identificación", key="ent_nit")
        with col_city:
            city = st.text_input("Ciudad", key="ent_city")

        address = st.text_input("Dirección", key="ent_address")
        legal_rep = st.text_input("Representante legal", key="ent_legal_rep")

    with tab_contact:
        col_phone, col_email = st.columns(2)
        with col_phone:
            phone = st.text_input("Teléfono", key="ent_phone")
        with col_email:
            email = st.text_input("Email", key="ent_email")

        notes = st.text_area("Notas adicionales", height=100, key="ent_notes",
                             placeholder="Ej: Horario de atención, sede principal, dependencia específica…")

    # ── Actions ────────────────────────────────────────────────────────────
    spacer()
    col_save, col_del = st.columns([3, 1])

    with col_save:
        if st.button("💾 Guardar entidad", type="primary", use_container_width=True, key="ent_save"):
            if not name.strip():
                sac.alert(label="Error", description="El nombre de la entidad es obligatorio.", color="error", icon=True)
                return

            entity_data = {
                "entity_id": entity_id,
                "name": name.strip(),
                "nit": nit.strip(),
                "address": address.strip(),
                "city": city.strip(),
                "phone": phone.strip(),
                "email": email.strip(),
                "legal_rep": legal_rep.strip(),
                "entity_type": entity_type,
                "notes": notes.strip(),
            }
            upsert_entity(entity_data)
            sac.alert(label="Guardado", description="Entidad guardada correctamente.", color="success", icon=True)
            st.session_state["_ent_context"] = None
            st.rerun()

    with col_del:
        if is_edit:
            if st.button("🗑️ Eliminar", use_container_width=True, key="ent_delete"):
                st.session_state["_ent_confirm_delete"] = True

    if st.session_state.get("_ent_confirm_delete"):
        sac.alert(
            label="Confirmar eliminación",
            description=f"¿Está seguro de eliminar «{name}»? Esta acción no se puede deshacer.",
            color="warning", icon=True,
        )
        c1, c2 = st.columns(2)
        if c1.button("Sí, eliminar", key="ent_yes"):
            delete_entity(entity_id)
            st.session_state["_ent_confirm_delete"] = False
            st.session_state["_ent_context"] = None
            sac.alert(label="Eliminado", description="Entidad eliminada.", color="info", icon=True)
            st.rerun()
        if c2.button("Cancelar", key="ent_no"):
            st.session_state["_ent_confirm_delete"] = False
            st.rerun()

    # ── Directory preview ──────────────────────────────────────────────────
    if entities and len(entities) > 1:
        section_title(f"Directorio ({len(entities)} entidades)")
        for ent in entities:
            type_label = f" · {ent['entity_type']}" if ent.get("entity_type") else ""
            city_label = f" · {ent['city']}" if ent.get("city") else ""
            st.caption(f"🏛️ **{ent['name']}**{type_label}{city_label}")
