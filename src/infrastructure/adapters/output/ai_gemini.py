from google import genai
from google.genai.types import GenerateContentConfig, Content, Part

from src.domain.exceptions import DocumentGenerationException
from src.domain.models import LegalContext
from src.domain.ports.out_ports import AIServicePort


class GeminiAdapter(AIServicePort):

    def __init__(self, api_key: str, model_name: str = "gemini-2.5-flash") -> None:
        self._client = genai.Client(api_key=api_key) if api_key else None
        self._model_name = model_name

    async def generate(self, context: LegalContext) -> str:
        if self._client is None:
            raise DocumentGenerationException("GEMINI_API_KEY not configured")
        try:
            response = await self._client.aio.models.generate_content(
                model=self._model_name,
                contents=[
                    Content(role="user", parts=[Part(text=context.system_prompt)]),
                    Content(role="model", parts=[Part(text="Entendido. Seguiré estas instrucciones.")]),
                    Content(role="user", parts=[Part(text=context.user_prompt)]),
                ],
                config=GenerateContentConfig(
                    temperature=context.temperature,
                    max_output_tokens=context.max_output_tokens,
                ),
            )
            if not response.text:
                raise DocumentGenerationException("Empty response from AI provider")
            return response.text
        except DocumentGenerationException:
            raise
        except Exception as e:
            raise DocumentGenerationException(str(e)) from e
