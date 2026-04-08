"""Page: Users — manage user accounts and roles."""

from __future__ import annotations

import uuid

import streamlit as st
import streamlit_antd_components as sac

from ..components import page_header, section_title, segmented, spacer
from ..constants import ROLE_LABELS
from ..state import delete_user, has_permission, load_users, upsert_user
from src.application.services.auth_service import hash_password


def render() -> None:
    if not has_permission("manage_users"):
        sac.alert(
            label="Acceso denegado",
            description="No tiene permisos para gestionar usuarios.",
            color="error", icon=True,
        )
        return

    page_header("👥", "Gestión de Usuarios",
                "Administre las cuentas de usuario, roles y permisos del sistema.")

    users = load_users()
    user_map = {u["user_id"]: u for u in users}

    col_action, col_sel = st.columns([1, 2])
    with col_action:
        action = segmented(["➕ Crear nuevo", "✏️ Editar existente"], key="usr_action")

    is_edit = action == "✏️ Editar existente"

    if is_edit and not users:
        sac.alert(label="Sin usuarios", description="No hay usuarios. Cree uno primero.", color="info", icon=True)
        return

    # ── Selección de usuario a editar ─────────────────────────────────────
    if is_edit:
        with col_sel:
            sel_id = st.selectbox(
                "Seleccionar usuario",
                options=list(user_map.keys()),
                format_func=lambda uid: f"{user_map[uid]['full_name']} ({user_map[uid]['username']}) — {ROLE_LABELS.get(user_map[uid]['role'], user_map[uid]['role'])}",
                key="usr_sel",
            )
        user = user_map[sel_id].copy()
    else:
        sel_id = None
        user = {
            "user_id": str(uuid.uuid4()),
            "username": "", "full_name": "", "email": "",
            "role": "pasante", "active": True, "password_hash": "",
        }

    # Detectar cambio de usuario seleccionado para limpiar campos
    prev_sel = st.session_state.get("_usr_prev_sel")
    if prev_sel != sel_id:
        st.session_state["_usr_prev_sel"] = sel_id
        for k in ["_usr_new_pass", "_usr_confirm_pass"]:
            st.session_state.pop(k, None)

    user_id = user["user_id"]

    # ── Form ──────────────────────────────────────────────────────────────
    tab_data, tab_security = st.tabs(["👤 Datos del Usuario", "🔒 Seguridad"])

    with tab_data:
        col_user, col_name = st.columns(2)
        with col_user:
            username = st.text_input(
                "Nombre de usuario *",
                value=user.get("username", ""),
                key=f"usr_username_{sel_id}",
            )
        with col_name:
            full_name = st.text_input(
                "Nombre completo *",
                value=user.get("full_name", ""),
                key=f"usr_fullname_{sel_id}",
            )

        col_email, col_role = st.columns(2)
        with col_email:
            email = st.text_input(
                "Email",
                value=user.get("email", ""),
                key=f"usr_email_{sel_id}",
            )
        with col_role:
            role_keys = list(ROLE_LABELS.keys())
            current_role = user.get("role", "pasante")
            role_idx = role_keys.index(current_role) if current_role in role_keys else 3
            role = st.selectbox(
                "Rol", options=role_keys, index=role_idx,
                format_func=lambda r: ROLE_LABELS.get(r, r),
                key=f"usr_role_{sel_id}",
            )

        active = st.checkbox(
            "Usuario activo",
            value=user.get("active", True),
            key=f"usr_active_{sel_id}",
        )

    with tab_security:
        st.caption("Deje en blanco para mantener la contraseña actual (solo en edición).")
        new_password = st.text_input("Nueva contraseña", type="password", key="_usr_new_pass")
        confirm_password = st.text_input("Confirmar contraseña", type="password", key="_usr_confirm_pass")

        # Permission preview
        section_title("Permisos del rol")
        from src.domain.models import Role as RoleEnum, ROLE_PERMISSIONS
        try:
            role_enum = RoleEnum(role)
            perms = ROLE_PERMISSIONS.get(role_enum, set())
            perm_labels = {
                "generate_document": "📄 Generar documentos",
                "view_templates": "📋 Ver plantillas",
                "manage_templates": "📋 Gestionar plantillas",
                "view_entities": "🏛️ Ver entidades",
                "manage_entities": "🏛️ Gestionar entidades",
                "view_company": "🏢 Ver empresa",
                "manage_company": "🏢 Gestionar empresa",
                "manage_users": "👥 Gestionar usuarios",
            }
            for p in perm_labels:
                icon = "✅" if any(pp.value == p for pp in perms) else "❌"
                st.caption(f"{icon} {perm_labels[p]}")
        except ValueError:
            pass

    # ── Actions ────────────────────────────────────────────────────────────
    spacer()
    col_save, col_del = st.columns([3, 1])

    with col_save:
        if st.button("💾 Guardar usuario", type="primary", use_container_width=True, key="usr_save"):
            if not username.strip() or not full_name.strip():
                sac.alert(label="Error", description="Usuario y nombre completo son obligatorios.", color="error", icon=True)
                return

            if new_password:
                if new_password != confirm_password:
                    sac.alert(label="Error", description="Las contraseñas no coinciden.", color="error", icon=True)
                    return
                if len(new_password) < 6:
                    sac.alert(label="Error", description="La contraseña debe tener al menos 6 caracteres.", color="error", icon=True)
                    return

            pw_hash = user.get("password_hash", "")
            if new_password:
                pw_hash = hash_password(new_password)
            elif not is_edit:
                sac.alert(label="Error", description="Debe establecer una contraseña para el nuevo usuario.", color="error", icon=True)
                return

            upsert_user({
                "user_id": user_id,
                "username": username.strip(),
                "full_name": full_name.strip(),
                "email": email.strip(),
                "role": role,
                "active": active,
                "password_hash": pw_hash,
            })
            sac.alert(label="Guardado", description="Usuario guardado correctamente.", color="success", icon=True)
            st.session_state["_usr_prev_sel"] = None
            st.rerun()

    with col_del:
        if is_edit:
            if st.button("🗑️ Eliminar", use_container_width=True, key="usr_delete"):
                st.session_state["_usr_confirm_delete"] = True

    if st.session_state.get("_usr_confirm_delete"):
        sac.alert(
            label="Confirmar eliminación",
            description=f"¿Está seguro de eliminar «{full_name}»? Esta acción no se puede deshacer.",
            color="warning", icon=True,
        )
        c1, c2 = st.columns(2)
        if c1.button("Sí, eliminar", key="usr_yes"):
            delete_user(user_id)
            st.session_state["_usr_confirm_delete"] = False
            st.session_state["_usr_prev_sel"] = None
            st.rerun()
        if c2.button("Cancelar", key="usr_no"):
            st.session_state["_usr_confirm_delete"] = False
            st.rerun()
