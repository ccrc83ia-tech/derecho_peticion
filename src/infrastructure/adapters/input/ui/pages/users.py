"""Page: Users — manage user accounts and roles."""

from __future__ import annotations

import uuid

import streamlit as st
import streamlit_antd_components as sac

from ..components import page_header, section_title, segmented, spacer
from ..constants import ROLE_LABELS
from ..state import delete_user, has_permission, load_users, upsert_user
from src.application.services.auth_service import hash_password
from src.domain.models import Role as RoleEnum, ROLE_PERMISSIONS

ALL_PERMS = [
    "generate_document", "view_templates", "manage_templates",
    "view_entities", "manage_entities", "view_company",
    "manage_company", "manage_users",
]

PERM_LABELS = {
    "generate_document": "📄 Generar documentos",
    "view_templates": "📋 Ver plantillas",
    "manage_templates": "📋 Gestionar plantillas",
    "view_entities": "🏛️ Ver entidades",
    "manage_entities": "🏛️ Gestionar entidades",
    "view_company": "🏢 Ver empresa",
    "manage_company": "🏢 Gestionar empresa",
    "manage_users": "👥 Gestionar usuarios",
}


def _default_perms_for_role(role_str: str) -> set[str]:
    try:
        return {p.value for p in ROLE_PERMISSIONS.get(RoleEnum(role_str), set())}
    except ValueError:
        return set()


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

    # Inicializar widgets solo si aún no existen para este usuario
    _init_key = f"_usr_init_{sel_id}"
    if not st.session_state.get(_init_key):
        st.session_state[_init_key] = True
        for k in ["_usr_new_pass", "_usr_confirm_pass"]:
            st.session_state.pop(k, None)
        st.session_state[f"usr_username_{sel_id}"] = user.get("username", "")
        st.session_state[f"usr_fullname_{sel_id}"] = user.get("full_name", "")
        st.session_state[f"usr_email_{sel_id}"] = user.get("email", "")
        role_keys = list(ROLE_LABELS.keys())
        current_role = user.get("role", "pasante")
        st.session_state[f"usr_role_{sel_id}"] = current_role if current_role in role_keys else "pasante"
        st.session_state[f"usr_active_{sel_id}"] = user.get("active", True)
        # Permisos: custom guardados o defaults del rol
        saved_perms = user.get("permissions")
        if saved_perms is not None:
            perm_set = set(saved_perms)
        else:
            perm_set = _default_perms_for_role(current_role)
        for p in ALL_PERMS:
            st.session_state[f"usr_perm_{p}_{sel_id}"] = p in perm_set

    user_id = user["user_id"]

    # ── Form ──────────────────────────────────────────────────────────────
    tab_data, tab_security = st.tabs(["👤 Datos del Usuario", "🔒 Seguridad"])

    with tab_data:
        col_user, col_name = st.columns(2)
        with col_user:
            username = st.text_input(
                "Nombre de usuario *",
                key=f"usr_username_{sel_id}",
            )
        with col_name:
            full_name = st.text_input(
                "Nombre completo *",
                key=f"usr_fullname_{sel_id}",
            )

        col_email, col_role = st.columns(2)
        with col_email:
            email = st.text_input(
                "Email",
                key=f"usr_email_{sel_id}",
            )
        with col_role:
            role_keys = list(ROLE_LABELS.keys())
            role = st.selectbox(
                "Rol", options=role_keys,
                format_func=lambda r: ROLE_LABELS.get(r, r),
                key=f"usr_role_{sel_id}",
            )

        active = st.checkbox(
            "Usuario activo",
            key=f"usr_active_{sel_id}",
        )

    with tab_security:
        st.caption("Deje en blanco para mantener la contraseña actual (solo en edición).")
        new_password = st.text_input("Nueva contraseña", type="password", key="_usr_new_pass")
        confirm_password = st.text_input("Confirmar contraseña", type="password", key="_usr_confirm_pass")

        # Aplicar reset de permisos ANTES de renderizar los checkboxes
        if st.session_state.pop(f"_usr_do_reset_perms_{sel_id}", False):
            defaults = _default_perms_for_role(st.session_state.get(f"usr_role_{sel_id}", "pasante"))
            for p in ALL_PERMS:
                st.session_state[f"usr_perm_{p}_{sel_id}"] = p in defaults

        # Editable permission checkboxes
        section_title("Permisos del usuario")
        st.caption("Marque o desmarque para personalizar los permisos de este usuario.")
        for p, label in PERM_LABELS.items():
            st.checkbox(label, key=f"usr_perm_{p}_{sel_id}")

        # Botón para resetear permisos al default del rol
        if st.button("🔄 Restaurar permisos por defecto del rol", key=f"usr_reset_perms_{sel_id}"):
            st.session_state[f"_usr_do_reset_perms_{sel_id}"] = True
            st.rerun()

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

            # Recoger permisos seleccionados
            selected_perms = [
                p for p in ALL_PERMS
                if st.session_state.get(f"usr_perm_{p}_{sel_id}", False)
            ]

            upsert_user({
                "user_id": user_id,
                "username": username.strip(),
                "full_name": full_name.strip(),
                "email": email.strip(),
                "role": role,
                "active": active,
                "password_hash": pw_hash,
                "permissions": selected_perms,
            })
            sac.alert(label="Guardado", description="Usuario guardado correctamente.", color="success", icon=True)
            # Limpiar flags de inicialización para recargar datos frescos
            for k in list(st.session_state.keys()):
                if k.startswith("_usr_init_"):
                    del st.session_state[k]
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
            for k in list(st.session_state.keys()):
                if k.startswith("_usr_init_"):
                    del st.session_state[k]
            st.rerun()
        if c2.button("Cancelar", key="usr_no"):
            st.session_state["_usr_confirm_delete"] = False
            st.rerun()
