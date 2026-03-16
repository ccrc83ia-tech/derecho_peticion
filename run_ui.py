"""Entry point for Streamlit UI — run with:
    python -m streamlit run run_ui.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure project root is in sys.path for package resolution
_root = Path(__file__).resolve().parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

import streamlit as st

from src.infrastructure.adapters.input.ui.constants import (
    APP_ICON,
    APP_SUBTITLE,
    APP_TITLE,
    PAGES,
)
from src.infrastructure.adapters.input.ui.pages import company, generate, templates

st.set_page_config(page_title=APP_TITLE, page_icon=APP_ICON, layout="centered")

st.markdown(
    f"<h1 style='text-align:center;'>{APP_ICON} FuturoTech AI</h1>"
    f"<p style='text-align:center;color:gray;'>{APP_SUBTITLE}</p>",
    unsafe_allow_html=True,
)

tab_generate, tab_templates, tab_company = st.tabs(PAGES)

with tab_generate:
    generate.render()

with tab_templates:
    templates.render()

with tab_company:
    company.render()
