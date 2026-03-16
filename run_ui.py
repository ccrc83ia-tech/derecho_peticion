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

from src.infrastructure.adapters.input.ui.constants import (
    API_BASE,
    APP_ICON,
    APP_SUBTITLE,
    GLOBAL_CSS,
    NAV_ITEMS,
)
from src.infrastructure.adapters.input.ui.pages import company, generate, templates
from src.infrastructure.adapters.input.ui.state import is_api_online, load_tenants


def _get_brand_name() -> str:
    """Return the brand name from the first active tenant, or fallback."""
    tenants = load_tenants()
    active = [t for t in tenants if t.get("active", True)]
    if active:
        return f"{active[0]['name']} AI"
    return "Legal Engine AI"


brand_name = _get_brand_name()

st.set_page_config(page_title=brand_name, page_icon=APP_ICON, layout="wide")
st.markdown(GLOBAL_CSS, unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown(
        "<div class='sidebar-brand'>"
        f"<div class='sidebar-brand-icon'>{APP_ICON}</div>"
        f"<p class='sidebar-brand-title'>{brand_name}</p>"
        f"<p class='sidebar-brand-sub'>{APP_SUBTITLE}</p>"
        "</div>",
        unsafe_allow_html=True,
    )
    st.divider()

    nav_labels = [f"{item['icon']}  {item['label']}" for item in NAV_ITEMS]
    selected = st.radio(
        "Navegación", nav_labels, label_visibility="collapsed", key="nav",
    )
    selected_key = NAV_ITEMS[nav_labels.index(selected)]["key"]

    st.divider()

    online = is_api_online()
    badge_cls = "badge-online" if online else "badge-offline"
    badge_txt = "● Online" if online else "● Offline"
    st.markdown(
        f"<div style='text-align:center;'>"
        f"<span class='badge {badge_cls}'>{badge_txt}</span>"
        f"<div style='color:#94A3B8; font-size:0.7rem; margin-top:4px;'>"
        f"API · {API_BASE}</div></div>",
        unsafe_allow_html=True,
    )

# ---------------------------------------------------------------------------
# Page routing
# ---------------------------------------------------------------------------
_pages = {
    "generate": generate.render,
    "templates": templates.render,
    "company": company.render,
}
_pages[selected_key]()
