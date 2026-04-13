"""Gemini AI adapter — circuit breaker + exponential backoff retry.

Circuit breaker: after FAIL_MAX consecutive failures the breaker opens for
RESET_TIMEOUT seconds, rejecting calls immediately instead of hammering the API.
Tenacity handles per-call retries with exponential backoff before the breaker counts a failure.
"""

from __future__ import annotations

import pybreaker
from google import genai
from google.genai.types import GenerateContentConfig, HttpOptions
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential, retry_if_not_exception_type

from src.domain.exceptions import DocumentGenerationException
from src.domain.models import LegalContext
from src.domain.ports.out_ports import AIServicePort
from src.infrastructure.logging_config import get_logger

logger = get_logger(__name__)

_TIMEOUT_MS = 120_000
_MAX_RETRIES = 3
_FAIL_MAX = 5
_RESET_TIMEOUT = 60  # seconds

_breaker = pybreaker.CircuitBreaker(fail_max=_FAIL_MAX, reset_timeout=_RESET_TIMEOUT, name="gemini")


class GeminiAdapter(AIServicePort):

    def __init__(self, api_key: str, model_name: str = "gemini-2.5-flash") -> None:
        self._client = genai.Client(api_key=api_key) if api_key else None
        self._model_name = model_name

    async def generate(self, context: LegalContext) -> str:
        if self._client is None:
            raise DocumentGenerationException("GEMINI_API_KEY not configured")
        try:
            return await self._call_with_retry(context)
        except pybreaker.CircuitBreakerError as e:
            logger.error("Gemini circuit breaker OPEN: %s", e)
            raise DocumentGenerationException(
                "Servicio de IA no disponible temporalmente. Intente en unos minutos."
            ) from e

    @retry(
        retry=retry_if_not_exception_type((pybreaker.CircuitBreakerError, DocumentGenerationException)),
        stop=stop_after_attempt(_MAX_RETRIES),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        reraise=True,
    )
    async def _call_with_retry(self, context: LegalContext) -> str:
        try:
            response = await _breaker.call_async(self._call_api, context)
        except (pybreaker.CircuitBreakerError, DocumentGenerationException):
            raise
        except Exception as e:
            logger.warning("Gemini transient error (will retry): %s", e)
            raise
        if not response.text:
            raise DocumentGenerationException("Empty response from AI provider")
        return response.text

    async def _call_api(self, context: LegalContext):
        # Implement resource limits to prevent unbounded consumption
        max_tokens = min(context.max_output_tokens or 4000, 8000)  # Cap at 8K tokens
        temperature = max(0.0, min(context.temperature or 0.1, 1.0))  # Clamp temperature
        
        return await self._client.aio.models.generate_content(
            model=self._model_name,
            contents=context.user_prompt,
            config=GenerateContentConfig(
                system_instruction=context.system_prompt,
                temperature=temperature,
                max_output_tokens=max_tokens,
                http_options=HttpOptions(timeout=_TIMEOUT_MS),
            ),
        )

    @property
    def circuit_state(self) -> str:
        return _breaker.current_state
