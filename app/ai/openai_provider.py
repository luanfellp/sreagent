from app.ai.base import BaseLLMProvider
from app.domain.llm_models import LLMAnalysisResult, LLMIncidentContext

SYSTEM_PROMPT = (
    "Voce e um assistente de analise de incidentes SRE. "
    "Use apenas as evidencias fornecidas. "
    "Nao afirme causa raiz como certeza. "
    "Diferencie fatos de hipoteses. "
    "Nao invente metricas, eventos, deploys ou logs. "
    "Priorize resposta operacional curta e estruturada."
)


class OpenAIProvider(BaseLLMProvider):
    provider_name = "openai"

    def __init__(
        self,
        api_key: str,
        model: str,
        timeout_seconds: float,
    ):
        from openai import OpenAI

        self._client = OpenAI(api_key=api_key, timeout=timeout_seconds)
        self._model = model

    def analyze_incident(self, context: LLMIncidentContext) -> LLMAnalysisResult:
        response = self._client.responses.parse(
            model=self._model,
            input=[
                {
                    "role": "system",
                    "content": [{"type": "input_text", "text": SYSTEM_PROMPT}],
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": context.model_dump_json(indent=2),
                        }
                    ],
                },
            ],
            text_format=LLMAnalysisResult,
        )
        return response.output_parsed
