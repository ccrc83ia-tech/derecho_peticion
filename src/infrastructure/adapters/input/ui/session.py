"""Session persistence — server-side token store + URL query param.

Estrategia:
  - Al hacer login se genera un token HMAC firmado y se guarda en un dict
    en memoria del proceso (SESSION_STORE).  El token se pasa al browser
    via st.query_params["sid"].
  - En cada render (F5, navegación) se lee st.query_params["sid"], se
    verifica la firma y la expiración, y se restaura current_user desde
    el store en memoria.
  - Al cerrar sesión se elimina el token del store y del query param.

Ventajas frente a cookies de terceros:
  - 100 % síncrono — no hay ciclos de render "vacíos".
  - Sin dependencias externas.
  - El token nunca viaja en texto plano (solo el ID firmado en la URL).

Limitación conocida:
  - El store vive en el proceso uvicorn/streamlit.  Si el servidor se
    reinicia, las sesiones activas se pierden (el usuario vuelve a hacer
    login).  Para producción multi-proceso se puede reemplazar SESSION_STORE
    por Redis, pero para uso local/single-worker es suficiente.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import time
from typing import Any

import streamlit as st

_SECRET = os.getenv("SESSION_SECRET_KEY", "futurotech-legal-default-key").encode()
_SESSION_TTL = int(os.getenv("SESSION_TTL_SECONDS", str(8 * 3600)))  # 8 horas
_SID_PARAM = "sid"

# Server-side store: {token: {"user_id": str, "exp": float}}
SESSION_STORE: dict[str, dict] = {}


# ---------------------------------------------------------------------------
# Compatibilidad: _get_manager() ya no hace nada pero se mantiene para no
# romper la llamada en run_ui.py
# ---------------------------------------------------------------------------

def _get_manager():
    return None


# ---------------------------------------------------------------------------
# Token helpers
# ---------------------------------------------------------------------------

def _sign(payload: str) -> str:
    return hmac.new(_SECRET, payload.encode(), hashlib.sha256).hexdigest()


def _make_token(user_id: str) -> str:
    token = secrets.token_urlsafe(32)
    exp = time.time() + _SESSION_TTL
    sig = _sign(f"{token}:{user_id}:{exp}")
    SESSION_STORE[token] = {"user_id": user_id, "exp": exp, "sig": sig}
    return token


def _verify_token(token: str) -> str | None:
    """Devuelve user_id si el token es válido y no expiró."""
    entry = SESSION_STORE.get(token)
    if not entry:
        return None
    if time.time() > entry["exp"]:
        SESSION_STORE.pop(token, None)
        return None
    expected_sig = _sign(f"{token}:{entry['user_id']}:{entry['exp']}")
    if not hmac.compare_digest(entry["sig"], expected_sig):
        SESSION_STORE.pop(token, None)
        return None
    return entry["user_id"]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def save_session(user: dict[str, Any]) -> None:
    """Guarda la sesión tras login exitoso."""
    token = _make_token(user["user_id"])
    st.query_params[_SID_PARAM] = token


def clear_session() -> None:
    """Elimina la sesión al hacer logout."""
    token = st.query_params.get(_SID_PARAM)
    if token:
        SESSION_STORE.pop(token, None)
    try:
        st.query_params.clear()
    except Exception:
        pass


def restore_session() -> dict[str, Any] | None:
    """Restaura el usuario desde el query param en F5/navegación."""
    # Si ya está en memoria y el sid sigue siendo válido, reutilizar
    cached = st.session_state.get("current_user")
    token = st.query_params.get(_SID_PARAM)

    if not token:
        st.session_state.pop("current_user", None)
        return None

    user_id = _verify_token(token)
    if not user_id:
        st.session_state.pop("current_user", None)
        try:
            st.query_params.clear()
        except Exception:
            pass
        return None

    # Si el usuario en memoria coincide con el token, no ir a DB
    if cached and cached.get("user_id") == user_id:
        return cached

    # Fetch fresco desde DB
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
