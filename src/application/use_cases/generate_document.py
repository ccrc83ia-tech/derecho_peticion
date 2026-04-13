from uuid import uuid4

from src.domain.exceptions import (
    DocumentGenerationException,
    TenantNotFoundException,
)
from src.domain.models import (
    DocumentGenerationRequest,
    DocumentGenerationResponse,
    DocumentStatus,
    LegalContext,
    TenantConfig,
)
from src.domain.ports.in_ports import GenerateDocumentPort
from src.domain.ports.out_ports import AIServicePort, FileExporterPort, KnowledgeBasePort, TenantRepositoryPort

import logging

logger = logging.getLogger(__name__)


class GenerateDocumentUseCase(GenerateDocumentPort):
    """Orchestrator: Tenant config → Prompt composition → AI call → Docx export."""

    def __init__(
        self,
        tenant_repository: TenantRepositoryPort,
        ai_service: AIServicePort,
        file_exporter: FileExporterPort,
        knowledge_base: KnowledgeBasePort | None = None,
    ) -> None:
        self._tenant_repo = tenant_repository
        self._ai_service = ai_service
        self._file_exporter = file_exporter
        self._knowledge_base = knowledge_base

    async def execute(
        self, request: DocumentGenerationRequest, tenant_id: str
    ) -> DocumentGenerationResponse:
        transaction_id = uuid4()
        logger.info("[%s] Starting generation — tenant=%s template=%s", transaction_id, tenant_id, request.template_id)

        tenant = await self._resolve_tenant(tenant_id)
        logger.debug("[%s] Tenant resolved: %s (rules=%d)", transaction_id, tenant.name, len(tenant.legal_rules))

        context = self._compose_prompt(tenant, request, self._knowledge_base)
        logger.debug("[%s] Prompt composed — system_prompt length=%d", transaction_id, len(context.system_prompt))

        try:
            raw_text = await self._ai_service.generate(context)
            logger.info("[%s] AI generation complete — %d chars", transaction_id, len(raw_text))
        except Exception as e:
            logger.error("[%s] AI generation failed: %s", transaction_id, e)
            raise DocumentGenerationException(str(e)) from e

        file_name = f"{transaction_id}_{request.template_id}.docx"
        file_path = await self._file_exporter.export(
            content=raw_text,
            branding=tenant.branding,
            file_name=file_name,
        )
        logger.info("[%s] Document exported: %s", transaction_id, file_path)

        return DocumentGenerationResponse(
            transaction_id=transaction_id,
            status=DocumentStatus.COMPLETED,
            download_url=f"/files/{file_path}",
        )

    async def _resolve_tenant(self, tenant_id: str) -> TenantConfig:
        tenant = await self._tenant_repo.get_by_id(tenant_id)
        if tenant is None:
            logger.error("Tenant not found in DB: '%s'", tenant_id)
            raise TenantNotFoundException(tenant_id)
        return tenant

    @staticmethod
    def _compose_prompt(
        tenant: TenantConfig, request: DocumentGenerationRequest,
        knowledge_base: KnowledgeBasePort | None = None,
    ) -> LegalContext:
        # Use selected_rules from request, fallback to tenant rules
        rules = request.selected_rules if request.selected_rules is not None else tenant.legal_rules
        rules_block = "\n".join(f"- {r}" for r in rules) if rules else ""

        # Use template system_prompt if provided, fallback to tenant
        base_prompt = (
            request.metadata.get("_system_prompt", "")
            or tenant.system_prompt
            or "Eres un abogado experto. Genera documentos jurídicos formales con lenguaje preciso y respetuoso."
        )

        system_prompt = (
            f"{base_prompt}\n\nReglas jurídicas aplicables:\n{rules_block}"
            if rules_block
            else base_prompt
        )

        # RAG: retrieve relevant legal context from knowledge base
        rag_strict = request.metadata.get("_rag_strict", "1") == "1"
        rag_context = ""
        has_indexed_docs = knowledge_base is not None and knowledge_base.has_documents(request.template_id)

        if has_indexed_docs:
            clean_metadata = {k: v for k, v in request.metadata.items() if not k.startswith("_")}
            query_parts = [request.template_id] + list(rules)
            for v in clean_metadata.values():
                if v and len(v) > 20:
                    query_parts.append(v)
            chunks = knowledge_base.search(request.template_id, " ".join(query_parts), n_results=10)
            if chunks:
                rag_context = "\n\n---\n\n".join(chunks)
                logger.info("RAG: injected %d chunks (%d chars)", len(chunks), len(rag_context))

        if rag_strict:
            if rag_context:
                system_prompt += (
                    "\n\n=== FUENTES NORMATIVAS AUTORIZADAS ===\n"
                    "INSTRUCCIÓN ABSOLUTA: El documento SOLO puede contener citas, artículos, "
                    "decretos, leyes y jurisprudencia que aparezcan TEXTUALMENTE en los fragmentos "
                    "de abajo. Queda PROHIBIDO usar conocimiento propio, inventar contenido normativo "
                    "o citar cualquier norma que no esté en estas fuentes. Si un argumento no tiene "
                    "respaldo en los fragmentos, NO lo incluyas.\n\n"
                    f"{rag_context}\n"
                    "=== FIN DE FUENTES AUTORIZADAS ==="
                )
            else:
                # Modo estricto pero sin chunks recuperables: bloqueo total de citas
                system_prompt += (
                    "\n\nINSTRUCCIÓN ABSOLUTA — MODO ESTRICTO: "
                    + ("Los documentos de referencia no contienen fragmentos relevantes para este caso. "
                       if has_indexed_docs else
                       "No hay documentos de referencia cargados para esta plantilla. ")
                    + "Queda PROHIBIDO citar, transcribir o mencionar el contenido de cualquier "
                    "artículo, ley, decreto o sentencia. Puedes mencionar los nombres de las normas "
                    "listadas en las reglas jurídicas, pero NUNCA su texto. Donde iría una cita "
                    "textual escribe exactamente: [texto no disponible en fuentes autorizadas]."
                )
        else:
            if rag_context:
                system_prompt += (
                    "\n\nDocumentos de referencia (prioriza estas fuentes, puedes complementar "
                    "con tu conocimiento jurídico):\n\n"
                    f"{rag_context}"
                )

        # Remove internal keys from metadata
        clean_metadata = {k: v for k, v in request.metadata.items() if not k.startswith("_")}

        user_prompt = (
            f"Genera el documento con plantilla '{request.template_id}' "
            f"usando estos datos del caso:\n{clean_metadata}"
        )
        return LegalContext(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            metadata=clean_metadata,
        )
