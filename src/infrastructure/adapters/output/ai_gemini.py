import asyncio

from google import genai
from google.genai.types import GenerateContentConfig, HttpOptions

from src.domain.exceptions import DocumentGenerationException
from src.domain.models import LegalContext
from src.domain.ports.out_ports import AIServicePort
from src.infrastructure.logging_config import get_logger

logger = get_logger(__name__)

_DEFAULT_TIMEOUT_MS = 120_000
_MAX_RETRIES = 3
_RETRY_BACKOFF_BASE = 2


class GeminiAdapter(AIServicePort):

    def __init__(self, api_key: str, model_name: str = "gemini-2.5-flash") -> None:
        self._client = genai.Client(api_key=api_key) if api_key else None
        self._model_name = model_name

    async def generate(self, context: LegalContext) -> str:
        if self._client is None:
            raise DocumentGenerationException("GEMINI_API_KEY not configured")

        last_error: Exception | None = None
        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                response = await self._client.aio.models.generate_content(
                    model=self._model_name,
                    contents=context.user_prompt,
                    config=GenerateContentConfig(
                        system_instruction=context.system_prompt,
                        temperature=context.temperature,
                        max_output_tokens=context.max_output_tokens,
                        http_options=HttpOptions(timeout=_DEFAULT_TIMEOUT_MS),
                    ),
                )
                if not response.text:
                    raise DocumentGenerationException("Empty response from AI provider")
                return response.text
            except DocumentGenerationException:
                raise
            except Exception as e:
                last_error = e
                if attempt < _MAX_RETRIES:
                    wait = _RETRY_BACKOFF_BASE ** attempt
                    logger.warning("Gemini attempt %d/%d failed: %s — retrying in %ds", attempt, _MAX_RETRIES, e, wait)
                    await asyncio.sleep(wait)

        raise DocumentGenerationException(str(last_error)) from last_error
