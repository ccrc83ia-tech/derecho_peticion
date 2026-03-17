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
)
from src.infrastructure.adapters.input.ui.pages import company, generate, templates
from src.infrastructure.adapters.input.ui.state import is_api_online, load_tenants


def _get_brand_name() -> str:
    tenants = load_tenants()
    active = [t for t in tenants if t.get("active", True)]
    return f"{active[0]['name']} AI" if active else "Legal Engine AI"


brand_name = _get_brand_name()

st.set_page_config(page_title=brand_name, page_icon=APP_ICON, layout="wide")
inject_css()

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    sidebar_brand(APP_ICON, brand_name, APP_SUBTITLE)
    st.divider()
    page_key = sidebar_nav()
    st.divider()
    sidebar_status(is_api_online(), API_BASE)

# ---------------------------------------------------------------------------
# Page routing
# ---------------------------------------------------------------------------
_PAGES = {
    "generate": generate.render,
    "templates": templates.render,
    "company": company.render,
}

_PAGES.get(page_key, generate.render)()
