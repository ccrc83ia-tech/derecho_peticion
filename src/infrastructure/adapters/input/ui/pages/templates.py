"""Page: Templates — create, edit and delete document templates."""

from __future__ import annotations

import streamlit as st

from ..constants import MSG_CONFIRM_DELETE, MSG_DELETED, MSG_DOC_DELETED, MSG_DOC_EMPTY, MSG_DOC_ERROR, MSG_DOC_UPLOADED, MSG_SAVED, RAG_SUPPORTED_TYPES
from ..state import delete_document, delete_template, get_template_documents, ingest_document, load_templates, upsert_template


def _empty_template() -> dict:
    return {
        "template_id": "", "name": "", "description": "",
        "fields": [], "system_prompt": "", "legal_rules": [],
    }


def _populate_keys(tpl: dict) -> None:
    st.session_state["tpl_id"] = tpl.get("template_id", "")
    st.session_state["tpl_name"] = tpl.get("name", "")
    st.session_state["tpl_desc"] = tpl.get("description", "")
    st.session_state["tpl_prompt"] = tpl.get("system_prompt", "")
    st.session_state["tpl_fields"] = [f.copy() for f in tpl.get("fields", [])]
    st.session_state["tpl_rules"] = [
        {"text": r, "active": True} for r in tpl.get("legal_rules", [])
    ]
    for k in list(st.session_state.keys()):
        if k.startswith(("fk_", "fl_", "fr_", "fd_", "tr_")):
            del st.session_state[k]


# ---------------------------------------------------------------------------
# Render
# ---------------------------------------------------------------------------

def render() -> None:
    st.markdown(
        "<div class='page-header'>"
        "<h2>📋 Gestión de Plantillas</h2>"
        "<p>Cree y administre las plantillas de documentos con sus campos dinámicos.</p>"
        "</div>",
        unsafe_allow_html=True,
    )

    templates = load_templates()
    template_map = {t["template_id"]: t for t in templates}

    # Action selector
    col_action, col_sel = st.columns([1, 2])
    with col_action:
        action = st.radio(
            "Acción",
            ["➕ Crear nueva", "✏️ Editar existente"],
            horizontal=True,
            key="tpl_action",
        )

    is_edit = action.startswith("✏️")

    if is_edit and not templates:
        st.info("No hay plantillas. Cree una primero.")
        return

    if is_edit:
        with col_sel:
            sel_id = st.selectbox(
                "Seleccionar plantilla",
                options=list(template_map.keys()),
                format_func=lambda tid: f"{template_map[tid].get('name', '')}  ({tid})",
                key="tpl_sel",
            )
        tpl = template_map[sel_id].copy()
        context_key = f"edit_{sel_id}"
    else:
        tpl = _empty_template()
        context_key = "create_new"

    if st.session_state.get("_tpl_context") != context_key:
        st.session_state["_tpl_context"] = context_key
        _populate_keys(tpl)
        st.rerun()

    # ── Información básica ─────────────────────────────────────────────────
    st.markdown("<div class='section-title'>Información General</div>", unsafe_allow_html=True)

    col_id, col_name = st.columns(2)
    with col_id:
        tpl["template_id"] = st.text_input("ID de plantilla *", disabled=is_edit, key="tpl_id")
    with col_name:
        tpl["name"] = st.text_input("Nombre *", key="tpl_name")

    tpl["description"] = st.text_area("Descripción", height=80, key="tpl_desc")

    # ── Instrucciones para la IA ─────────────────────────────────────────
    st.markdown("<div class='section-title'>Instrucciones para la IA</div>", unsafe_allow_html=True)
    st.caption("Defina cómo debe redactar la IA los documentos de esta plantilla.")
    tpl["system_prompt"] = st.text_area(
        "System Prompt", height=120, key="tpl_prompt",
        placeholder="Ej: Eres un abogado experto en derecho administrativo colombiano. Genera documentos formales...",
    )

    # ── Reglas jurídicas ───────────────────────────────────────────────
    st.markdown("<div class='section-title'>Reglas Jurídicas</div>", unsafe_allow_html=True)
    st.caption("Leyes y normas que la IA debe aplicar al generar documentos.")

    if "tpl_rules" not in st.session_state:
        st.session_state["tpl_rules"] = [
            {"text": r, "active": True} for r in tpl.get("legal_rules", [])
        ]

    rules_state: list[dict] = st.session_state["tpl_rules"]
    rule_to_remove: int | None = None
    for i, rule in enumerate(rules_state):
        cols_r = st.columns([8, 0.5])
        rule["text"] = cols_r[0].text_input(
            "Regla", value=rule.get("text", ""),
            key=f"tr_txt_{i}", label_visibility="collapsed",
        )
        if cols_r[1].button("✕", key=f"tr_del_{i}"):
            rule_to_remove = i

    if rule_to_remove is not None:
        rules_state.pop(rule_to_remove)
        st.session_state["tpl_rules"] = rules_state
        st.rerun()

    if st.button("➕ Agregar regla", key="tpl_add_rule"):
        rules_state.append({"text": "", "active": True})
        st.session_state["tpl_rules"] = rules_state
        st.rerun()

    # ── Campos dinámicos ───────────────────────────────────────────────────
    st.markdown("<div class='section-title'>Campos del Formulario</div>", unsafe_allow_html=True)
    st.caption("Defina los campos que el usuario completará al generar un documento.")

    if "tpl_fields" not in st.session_state:
        st.session_state["tpl_fields"] = [f.copy() for f in tpl.get("fields", [])]

    current_fields: list[dict] = st.session_state["tpl_fields"]

    # Header row
    if current_fields:
        hdr = st.columns([3, 3, 1, 0.5])
        hdr[0].markdown(
            "<span style='font-size:0.78rem; color:#64748B; font-weight:600;'>CLAVE</span>",
            unsafe_allow_html=True,
        )
        hdr[1].markdown(
            "<span style='font-size:0.78rem; color:#64748B; font-weight:600;'>ETIQUETA</span>",
            unsafe_allow_html=True,
        )
        hdr[2].markdown(
            "<span style='font-size:0.78rem; color:#64748B; font-weight:600;'>REQ.</span>",
            unsafe_allow_html=True,
        )

    to_remove: int | None = None
    for i, field in enumerate(current_fields):
        cols = st.columns([3, 3, 1, 0.5])
        field["key"] = cols[0].text_input(
            "Clave", value=field.get("key", ""), key=f"fk_{i}", label_visibility="collapsed",
        )
        field["label"] = cols[1].text_input(
            "Etiqueta", value=field.get("label", ""), key=f"fl_{i}", label_visibility="collapsed",
        )
        field["required"] = cols[2].checkbox(
            "Req.", value=field.get("required", False), key=f"fr_{i}", label_visibility="collapsed",
        )
        if cols[3].button("✕", key=f"fd_{i}"):
            to_remove = i

    if to_remove is not None:
        current_fields.pop(to_remove)
        st.session_state["tpl_fields"] = current_fields
        st.rerun()

    if st.button("➕ Agregar campo", key="tpl_add_field"):
        current_fields.append({"key": "", "label": "", "required": False})
        st.session_state["tpl_fields"] = current_fields
        st.rerun()

    # ── Documentos de referencia (RAG) ─────────────────────────────────────
    if is_edit and tpl["template_id"].strip():
        st.markdown("<div class='section-title'>Documentos de Referencia (RAG)</div>", unsafe_allow_html=True)
        st.caption(
            "Suba leyes, normas o documentos legales en PDF, TXT o DOCX. "
            "La IA usará el texto literal de estos documentos al generar."
        )

        uploaded = st.file_uploader(
            "Subir documento",
            type=RAG_SUPPORTED_TYPES,
            accept_multiple_files=True,
            key="tpl_doc_upload",
        )
        if uploaded:
            # Track already-processed files to avoid re-ingesting on every render
            processed: set = st.session_state.get("_rag_processed", set())
            for f in uploaded:
                fkey = f"{tpl['template_id']}::{f.name}::{f.size}"
                if fkey in processed:
                    continue
                with st.spinner(f"Procesando {f.name}…"):
                    try:
                        chunks = ingest_document(tpl["template_id"], f.name, f.getvalue(), f.type)
                        if chunks > 0:
                            st.success(MSG_DOC_UPLOADED.format(name=f.name, chunks=chunks))
                        else:
                            st.warning(MSG_DOC_EMPTY.format(name=f.name))
                    except Exception as e:
                        st.error(MSG_DOC_ERROR.format(name=f.name, error=e))
                processed.add(fkey)
            st.session_state["_rag_processed"] = processed

        docs = get_template_documents(tpl["template_id"])
        if docs:
            for doc in docs:
                cols_doc = st.columns([5, 2, 1])
                cols_doc[0].markdown(f"📄 **{doc['doc_name']}**")
                cols_doc[1].caption(f"{doc['chunks_count']} fragmentos")
                if cols_doc[2].button("✕", key=f"doc_del_{doc['doc_name']}"):
                    delete_document(tpl["template_id"], doc["doc_name"])
                    st.success(MSG_DOC_DELETED.format(name=doc["doc_name"]))
                    st.rerun()

    # ── Actions ────────────────────────────────────────────────────────────
    st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)

    col_save, col_del = st.columns([3, 1])

    with col_save:
        if st.button("💾 Guardar plantilla", type="primary", use_container_width=True, key="tpl_save"):
            if not tpl["template_id"].strip() or not tpl["name"].strip():
                st.error("ID y Nombre son obligatorios.")
                return
            tpl["fields"] = [f for f in current_fields if f.get("key", "").strip()]
            tpl["system_prompt"] = st.session_state.get("tpl_prompt", "")
            tpl["legal_rules"] = [
                r["text"] for r in rules_state if r.get("text", "").strip()
            ]
            upsert_template(tpl)
            st.success(MSG_SAVED)
            st.session_state["_tpl_context"] = None
            st.rerun()

    with col_del:
        if is_edit:
            if st.button("🗑️ Eliminar", use_container_width=True, key="tpl_delete"):
                st.session_state["_tpl_confirm_delete"] = True

    if st.session_state.get("_tpl_confirm_delete"):
        st.warning(MSG_CONFIRM_DELETE.format(name=tpl["template_id"]))
        c1, c2 = st.columns(2)
        if c1.button("Sí, eliminar", key="tpl_yes"):
            delete_template(tpl["template_id"])
            st.session_state["_tpl_confirm_delete"] = False
            st.session_state["_tpl_context"] = None
            st.success(MSG_DELETED)
            st.rerun()
        if c2.button("Cancelar", key="tpl_no"):
            st.session_state["_tpl_confirm_delete"] = False
            st.rerun()
