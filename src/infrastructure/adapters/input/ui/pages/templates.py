"""Page: Templates — create, edit and delete document templates."""

from __future__ import annotations

import streamlit as st
import streamlit_antd_components as sac

from ..components import (
    badge_html,
    col_header,
    empty_state,
    page_header,
    section_title,
    segmented,
    spacer,
)
from ..constants import (
    MSG_CONFIRM_DELETE,
    MSG_DELETED,
    MSG_DOC_DELETED,
    MSG_DOC_EMPTY,
    MSG_DOC_ERROR,
    MSG_DOC_UPLOADED,
    MSG_SAVED,
    RAG_SUPPORTED_TYPES,
)
from ..state import (
    delete_document,
    delete_template,
    get_template_documents,
    has_permission,
    ingest_document,
    load_templates,
    upsert_template,
)


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
    page_header("📋", "Gestión de Plantillas",
                "Cree y administre las plantillas de documentos con sus campos dinámicos.")

    can_manage = has_permission("manage_templates")

    templates = load_templates()
    template_map = {t["template_id"]: t for t in templates}

    col_action, col_sel = st.columns([1, 2])
    with col_action:
        if can_manage:
            action = segmented(["➕ Crear nueva", "✏️ Editar existente"], key="tpl_action")
        else:
            action = "✏️ Editar existente"

    is_edit = action == "✏️ Editar existente"

    if is_edit and not templates:
        sac.alert(label="Sin plantillas", description="No hay plantillas. Cree una primero.", color="info", icon=True)
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

    # ── Tabs ───────────────────────────────────────────────────────────────
    tab_labels = ["📝 General", "🤖 IA & Reglas", "📋 Campos"]
    if is_edit and tpl["template_id"].strip():
        tab_labels.append("📚 Documentos RAG")

    tabs = st.tabs(tab_labels)

    # ── Tab 1: General ─────────────────────────────────────────────────────
    with tabs[0]:
        col_id, col_name = st.columns(2)
        with col_id:
            tpl["template_id"] = st.text_input("ID de plantilla *", disabled=is_edit, key="tpl_id")
        with col_name:
            tpl["name"] = st.text_input("Nombre *", key="tpl_name")

        tpl["description"] = st.text_area("Descripción", height=80, key="tpl_desc")

    # ── Tab 2: IA & Rules ──────────────────────────────────────────────────
    with tabs[1]:
        section_title("Instrucciones para la IA")
        st.caption("Defina cómo debe redactar la IA los documentos de esta plantilla.")
        tpl["system_prompt"] = st.text_area(
            "System Prompt", height=150, key="tpl_prompt",
            placeholder="Ej: Eres un abogado experto en derecho administrativo colombiano…",
        )

        section_title("Reglas Jurídicas")
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

    # ── Tab 3: Fields ──────────────────────────────────────────────────────
    with tabs[2]:
        st.caption("Defina los campos que el usuario completará al generar un documento.")

        if "tpl_fields" not in st.session_state:
            st.session_state["tpl_fields"] = [f.copy() for f in tpl.get("fields", [])]

        current_fields: list[dict] = st.session_state["tpl_fields"]

        if current_fields:
            hdr = st.columns([3, 3, 1, 0.5])
            hdr[0].markdown("<span class='col-header'>CLAVE</span>", unsafe_allow_html=True)
            hdr[1].markdown("<span class='col-header'>ETIQUETA</span>", unsafe_allow_html=True)
            hdr[2].markdown("<span class='col-header'>REQ.</span>", unsafe_allow_html=True)

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

    # ── Tab 4: RAG Documents ───────────────────────────────────────────────
    if is_edit and tpl["template_id"].strip() and len(tabs) > 3:
        with tabs[3]:
            st.caption(
                "Suba leyes, normas o documentos legales en PDF, TXT o DOCX. "
                "La IA usará el texto literal de estos documentos al generar."
            )

            rag_strict = st.toggle(
                "🔒 Modo estricto — usar SOLO los documentos adjuntos como fuente",
                value=tpl.get("rag_strict", True),
                key=f"tpl_rag_strict_{tpl['template_id']}",
                help=(
                    "Activado: la IA solo puede citar los documentos adjuntos. "
                    "Desactivado: puede complementar con su conocimiento propio."
                ),
            )
            tpl["rag_strict"] = rag_strict
            if rag_strict:
                sac.alert(
                    label="Modo estricto activo",
                    description="La IA solo usará los documentos adjuntos. No citará leyes ni jurisprudencia de su conocimiento propio.",
                    color="info", icon=True,
                )
            else:
                sac.alert(
                    label="Modo libre activo",
                    description="La IA usará los documentos adjuntos como referencia principal, pero puede complementar con su conocimiento.",
                    color="warning", icon=True,
                )

            uploaded = st.file_uploader(
                "Subir documento",
                type=RAG_SUPPORTED_TYPES,
                accept_multiple_files=True,
                key="tpl_doc_upload",
            )
            if uploaded:
                processed: set = st.session_state.get("_rag_processed", set())
                for f in uploaded:
                    fkey = f"{tpl['template_id']}::{f.name}::{f.size}"
                    if fkey in processed:
                        continue
                    with st.status(f"Procesando **{f.name}**…", expanded=True) as status:
                        bar = st.progress(0.0)
                        label_slot = st.empty()

                        def _on_progress(pct: float, lbl: str, _bar=bar, _slot=label_slot) -> None:
                            _bar.progress(min(pct, 1.0))
                            _slot.caption(lbl)

                        try:
                            chunks = ingest_document(
                                tpl["template_id"], f.name, f.getvalue(), f.type,
                                on_progress=_on_progress,
                            )
                            if chunks > 0:
                                status.update(
                                    label=f"✅ {f.name} — {chunks} fragmentos indexados",
                                    state="complete", expanded=False,
                                )
                            else:
                                status.update(
                                    label=f"⚠️ {f.name} — No se extrajo texto",
                                    state="error", expanded=False,
                                )
                        except Exception as e:
                            status.update(
                                label=f"❌ {f.name} — {e}",
                                state="error", expanded=False,
                            )
                    processed.add(fkey)
                st.session_state["_rag_processed"] = processed

            docs = get_template_documents(tpl["template_id"])
            if docs:
                section_title(f"Documentos indexados ({len(docs)})")
                for doc in docs:
                    cols_doc = st.columns([5, 2, 1])
                    cols_doc[0].markdown(
                        f"📄 **{doc['doc_name']}**",
                    )
                    cols_doc[1].markdown(
                        badge_html(f"{doc['chunks_count']} fragmentos"),
                        unsafe_allow_html=True,
                    )
                    if cols_doc[2].button("✕", key=f"doc_del_{doc['doc_name']}"):
                        delete_document(tpl["template_id"], doc["doc_name"])
                        sac.alert(label="Eliminado", description=doc["doc_name"], color="info", icon=True, closable=True)
                        st.rerun()
            elif not uploaded:
                empty_state(
                    "📚",
                    "No hay documentos de referencia.",
                    "Suba PDFs de leyes para que la IA cite textualmente.",
                )

    # ── Actions ────────────────────────────────────────────────────────────
    spacer()
    if not can_manage:
        return

    col_save, col_del = st.columns([3, 1])

    with col_save:
        if st.button("💾 Guardar plantilla", type="primary", use_container_width=True, key="tpl_save"):
            if not tpl["template_id"].strip() or not tpl["name"].strip():
                sac.alert(label="Error", description="ID y Nombre son obligatorios.", color="error", icon=True)
                return
            tpl["fields"] = [f for f in current_fields if f.get("key", "").strip()]
            tpl["system_prompt"] = st.session_state.get("tpl_prompt", "")
            tpl["legal_rules"] = [
                r["text"] for r in rules_state if r.get("text", "").strip()
            ]
            tpl["rag_strict"] = st.session_state.get(
                f"tpl_rag_strict_{tpl['template_id']}", tpl.get("rag_strict", True)
            )
            upsert_template(tpl)
            sac.alert(label="Guardado", description="Plantilla guardada correctamente.", color="success", icon=True)
            st.session_state["_tpl_context"] = None
            st.rerun()

    with col_del:
        if is_edit:
            if st.button("🗑️ Eliminar", use_container_width=True, key="tpl_delete"):
                st.session_state["_tpl_confirm_delete"] = True

    if st.session_state.get("_tpl_confirm_delete"):
        sac.alert(
            label="Confirmar eliminación",
            description=f"¿Está seguro de eliminar «{tpl['template_id']}»? Esta acción no se puede deshacer.",
            color="warning", icon=True,
        )
        c1, c2 = st.columns(2)
        if c1.button("Sí, eliminar", key="tpl_yes"):
            delete_template(tpl["template_id"])
            st.session_state["_tpl_confirm_delete"] = False
            st.session_state["_tpl_context"] = None
            sac.alert(label="Eliminado", description="Plantilla eliminada.", color="info", icon=True)
            st.rerun()
        if c2.button("Cancelar", key="tpl_no"):
            st.session_state["_tpl_confirm_delete"] = False
            st.rerun()
