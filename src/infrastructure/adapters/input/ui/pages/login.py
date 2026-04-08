"""Page: Login — user authentication."""

from __future__ import annotations

import streamlit as st

from ..components import page_header, spacer
from ..state import login


def render() -> None:
    spacer(3)
    col_l, col_c, col_r = st.columns([1, 2, 1])
    with col_c:
        page_header("🔐", "Iniciar Sesión", "Ingrese sus credenciales para acceder al sistema.")

        with st.form("login_form"):
            username = st.text_input("Usuario", key="login_user")
            password = st.text_input("Contraseña", type="password", key="login_pass")
            submitted = st.form_submit_button(
                "🔑 Ingresar", type="primary", use_container_width=True,
            )

        if submitted:
            if not username.strip() or not password.strip():
                st.error("Ingrese usuario y contraseña.")
                return
            user = login(username.strip(), password)
            if user:
                st.rerun()
            else:
                st.error("Credenciales inválidas o usuario inactivo.")
