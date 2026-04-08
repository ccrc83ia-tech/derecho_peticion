"""Entry point for Streamlit UI — run with:
    python -m streamlit run run_ui.py
"""

from __future__ import annotations

import sys
from pathlib import Path

_root = Path(__file__).resolve().parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

import streamlit as st

from src.infrastructure.adapters.input.ui.components import (
    inject_css,
    sidebar_brand,
    sidebar_nav,
    sidebar_status,
)
from src.infrastructure.adapters.input.ui.constants import (
    API_BASE,
    APP_ICON,
    APP_SUBTITLE,
    ROLE_LABELS,
)
from src.infrastructure.adapters.input.ui.pages import (
    company, entities, generate, login, templates, users,
)
from src.infrastructure.adapters.input.ui.state import (
    current_user, ensure_admin_exists, is_api_online, load_tenants, logout,
)
from src.domain.models import ROLE_PERMISSIONS, Role, Permission


def _get_brand_name() -> str:
    tenants = load_tenants()
    active = [t for t in tenants if t.get("active", True)]
    return f"{active[0]['name']} AI" if active else "Legal Engine AI"


# Bootstrap
ensure_admin_exists()
brand_name = _get_brand_name()

st.set_page_config(page_title=brand_name, page_icon=APP_ICON, layout="wide")
inject_css()

# ---------------------------------------------------------------------------
# Login gate
# ---------------------------------------------------------------------------
user = current_user()
if not user:
    login.render()
    st.stop()

# ---------------------------------------------------------------------------
# Resolve permissions for current user
# ---------------------------------------------------------------------------
try:
    role_enum = Role(user.get("role", "consulta"))
    user_perms = {p.value for p in ROLE_PERMISSIONS.get(role_enum, set())}
except ValueError:
    user_perms = set()

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    sidebar_brand(APP_ICON, brand_name, APP_SUBTITLE)
    st.divider()

    # User info
    role_label = ROLE_LABELS.get(user.get("role", ""), user.get("role", ""))
    st.markdown(
        f"<div style='padding:0 1rem;font-size:0.85rem;'>"
        f"👤 <b>{user.get('full_name', '')}</b><br>"
        f"<span style='color:var(--text-secondary);font-size:0.75rem;'>{role_label}</span>"
        f"</div>",
        unsafe_allow_html=True,
    )
    if st.button("🚪 Cerrar sesión", use_container_width=True, key="logout_btn"):
        logout()
        st.rerun()

    st.divider()
    page_key = sidebar_nav(user_permissions=user_perms)
    st.divider()
    sidebar_status(is_api_online(), API_BASE)

# ---------------------------------------------------------------------------
# Page routing
# ---------------------------------------------------------------------------
_PAGES = {
    "generate": generate.render,
    "templates": templates.render,
    "entities": entities.render,
    "company": company.render,
    "users": users.render,
}

_PAGES.get(page_key, generate.render)()
