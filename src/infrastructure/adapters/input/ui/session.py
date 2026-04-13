"""Session persistence via signed cookies.

On login   → serializes user_id + expiry into a HMAC-SHA256 signed token
              and stores it in a browser cookie (max_age = SESSION_TTL_SECONDS).
On F5/reload → reads the cookie, verifies the signature, fetches the user
               from DB and restores st.session_state["current_user"].
On logout  → clears the cookie and session_state.

No plaintext credentials or password hashes are ever stored in the cookie.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
from typing import Any

import streamlit as st

_SECRET = os.getenv("SESSION_SECRET_KEY", "futurotech-legal-default-key").encode()
_COOKIE_NAME = "legal_session"
_SESSION_TTL = int(os.getenv("SESSION_TTL_SECONDS", str(8 * 3600)))  # 8 hours


# ---------------------------------------------------------------------------
# Singleton CookieManager — must be created ONCE per app session
# ---------------------------------------------------------------------------

def _get_manager():
    """Get or create CookieManager instance without caching."""
    if "cookie_manager" not in st.session_state:
        import extra_streamlit_components as stx
        st.session_state["cookie_manager"] = stx.CookieManager()
    return st.session_state["cookie_manager"]


# ---------------------------------------------------------------------------
# Token helpers
# ---------------------------------------------------------------------------

def _sign(payload: str) -> str:
    return hmac.new(_SECRET, payload.encode(), hashlib.sha256).hexdigest()


def _make_token(user_id: str) -> str:
    import base64
    data = json.dumps({"uid": user_id, "exp": int(time.time()) + _SESSION_TTL})
    return base64.urlsafe_b64encode(f"{data}||{_sign(data)}".encode()).decode()


def _verify_token(token: str) -> str | None:
    """Return user_id if token is valid and not expired, else None."""
    try:
        import base64
        raw = base64.urlsafe_b64decode(token.encode()).decode()
        data, sig = raw.rsplit("||", 1)
        if not hmac.compare_digest(_sign(data), sig):
            return None
        payload = json.loads(data)
        if time.time() > payload["exp"]:
            return None
        return payload["uid"]
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def save_session(user: dict[str, Any]) -> None:
    """Write signed cookie after successful login."""
    token = _make_token(user["user_id"])
    _get_manager().set(_COOKIE_NAME, token, max_age=_SESSION_TTL)


def clear_session() -> None:
    """Delete cookie on logout."""
    try:
        _get_manager().delete(_COOKIE_NAME)
    except Exception:
        pass


def restore_session() -> dict[str, Any] | None:
    """Try to restore user from cookie on F5/reload. Returns user dict or None."""
    if st.session_state.get("current_user"):
        return st.session_state["current_user"]

    token = _get_manager().get(_COOKIE_NAME)
    if not token:
        return None

    user_id = _verify_token(token)
    if not user_id:
        clear_session()
        return None

    # Fetch fresh user data from DB to ensure still active
    from src.infrastructure.adapters.input.ui.state import _get_repo
    user = next(
        (u for u in _get_repo().get_all_users()
         if u["user_id"] == user_id and u.get("active", False)),
        None,
    )
    if not user:
        clear_session()
        return None

    st.session_state["current_user"] = user
    return user
