"""Reusable UI components for the Streamlit frontend.

Every visual pattern used across pages lives here.
Pages call these functions instead of writing raw st.markdown HTML.
"""

from __future__ import annotations

from pathlib import Path

import streamlit as st


# ---------------------------------------------------------------------------
# CSS loader — reads the .css file once and caches it
# ---------------------------------------------------------------------------

_CSS_PATH = Path(__file__).parent / "static" / "theme.css"


@st.cache_resource
def _load_css() -> str:
    css = _CSS_PATH.read_text(encoding='utf-8')
    return f"<style>{css}</style>"


_HIDE_STREAMLIT = """
<style>
header, header[data-testid="stHeader"], .stAppHeader,
[data-testid="stHeader"], [data-testid="stToolbar"],
[data-testid="stDecoration"], #MainMenu, footer,
.stDeployButton, [data-testid="manage-app-button"] {
    display: none !important;
    visibility: hidden !important;
    height: 0 !important;
}
</style>
"""


def inject_css() -> None:
    st.markdown(_load_css(), unsafe_allow_html=True)
    st.markdown(_HIDE_STREAMLIT, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Layout helpers
# ---------------------------------------------------------------------------

def page_header(icon: str, title: str, subtitle: str) -> None:
    st.markdown(
        f"<div class='page-header'>"
        f"<h2>{icon} {title}</h2>"
        f"<p>{subtitle}</p>"
        f"</div>",
        unsafe_allow_html=True,
    )


def section_title(text: str) -> None:
    st.markdown(
        f"<div class='section-title'>{text}</div>",
        unsafe_allow_html=True,
    )


def spacer(rem: float = 1.0) -> None:
    st.markdown(f"<div style='height:{rem}rem'></div>", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Cards
# ---------------------------------------------------------------------------

def stat_card(value: str, label: str, *, value_style: str = "") -> None:
    extra = f" style='{value_style}'" if value_style else ""
    st.markdown(
        f"<div class='stat-card'>"
        f"<div class='stat-card-value'{extra}>{value}</div>"
        f"<div class='stat-card-label'>{label}</div>"
        f"</div>",
        unsafe_allow_html=True,
    )


def card(content_html: str, *, style: str = "") -> None:
    extra = f" style='{style}'" if style else ""
    st.markdown(
        f"<div class='ui-card'{extra}>{content_html}</div>",
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Badges
# ---------------------------------------------------------------------------

def badge_html(text: str, variant: str = "count") -> str:
    """Return badge HTML string (for embedding inside other markdown)."""
    return f"<span class='badge badge-{variant}'>{text}</span>"


# ---------------------------------------------------------------------------
# Column headers (table-like grids)
# ---------------------------------------------------------------------------

def col_header(text: str) -> None:
    st.markdown(
        f"<span class='col-header'>{text}</span>",
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Empty state
# ---------------------------------------------------------------------------

def empty_state(icon: str, text: str, hint: str = "") -> None:
    hint_html = f"<div class='empty-state-hint'>{hint}</div>" if hint else ""
    st.markdown(
        f"<div class='empty-state'>"
        f"<div class='empty-state-icon'>{icon}</div>"
        f"<div class='empty-state-text'>{text}</div>"
        f"{hint_html}"
        f"</div>",
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Segmented control (replaces sac.segmented)
# ---------------------------------------------------------------------------

def segmented(options: list[str], *, key: str) -> str:
    """Two-button toggle styled as a button group. Returns selected label."""
    if f"{key}_val" not in st.session_state:
        st.session_state[f"{key}_val"] = options[0]

    st.markdown("<div class='segmented-wrap'>", unsafe_allow_html=True)
    cols = st.columns(len(options))
    for i, opt in enumerate(options):
        is_active = st.session_state[f"{key}_val"] == opt
        with cols[i]:
            if st.button(
                opt,
                key=f"{key}_{i}",
                type="primary" if is_active else "secondary",
            ):
                st.session_state[f"{key}_val"] = opt
                st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

    return st.session_state[f"{key}_val"]


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

_NAV_ITEMS = [
    {"key": "generate",  "icon": "📄", "label": "Generar Documento", "perm": "generate_document"},
    {"key": "templates", "icon": "📋", "label": "Plantillas",        "perm": "view_templates"},
    {"key": "entities",  "icon": "🏛️", "label": "Entidades",         "perm": "view_entities"},
    {"key": "company",   "icon": "🏢", "label": "Empresas",          "perm": "view_company"},
    {"key": "users",     "icon": "👥", "label": "Usuarios",          "perm": "manage_users"},
]


def sidebar_brand(icon: str, title: str, subtitle: str) -> None:
    st.markdown(
        f"<div class='sidebar-brand'>"
        f"<div class='sidebar-brand-icon'>{icon}</div>"
        f"<p class='sidebar-brand-title'>{title}</p>"
        f"<p class='sidebar-brand-sub'>{subtitle}</p>"
        f"</div>",
        unsafe_allow_html=True,
    )


def sidebar_nav(user_permissions: set[str] | None = None) -> str:
    """Render sidebar navigation using native radio, return page key."""
    if "nav_page" not in st.session_state:
        st.session_state["nav_page"] = "generate"

    visible = [
        item for item in _NAV_ITEMS
        if user_permissions is None or item.get("perm", "") in user_permissions
    ]
    if not visible:
        visible = [_NAV_ITEMS[0]]

    labels = [f"{item['icon']}  {item['label']}" for item in visible]
    keys = [item["key"] for item in visible]

    current_idx = keys.index(st.session_state["nav_page"]) if st.session_state["nav_page"] in keys else 0

    selected_label = st.radio(
        "Navegación",
        options=labels,
        index=current_idx,
        key="_sidebar_nav",
        label_visibility="collapsed",
    )

    selected_key = keys[labels.index(selected_label)] if selected_label in labels else "generate"
    st.session_state["nav_page"] = selected_key
    return selected_key


def sidebar_status(online: bool, api_base: str) -> None:
    badge_cls = "badge-online" if online else "badge-offline"
    badge_txt = "● Online" if online else "● Offline"
    st.markdown(
        f"<div class='sidebar-footer'>"
        f"<span class='badge {badge_cls}'>{badge_txt}</span>"
        f"<div class='sidebar-footer-version'>"
        f"API · {api_base}<br>v1.0.0 · Powered by Gemini"
        f"</div></div>",
        unsafe_allow_html=True,
    )
