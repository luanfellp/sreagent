from app.ai.base import BaseLLMProvider
from app.domain.llm_models import LLMAnalysisResult, LLMIncidentContext

SYSTEM_PROMPT = (
    "Voce e um copiloto SRE read-only para analise de incidentes. "
    "Use apenas o contexto JSON fornecido: alerta, sinais, correlacao, evidencias "
    "e hipoteses deterministicas. "
    "Nao invente metricas, eventos, deploys, logs, donos ou acoes executadas. "
    "Nao afirme causa raiz como certeza; escreva como hipotese provavel quando "
    "a evidencia permitir. "
    "Diferencie fatos observados, inferencias e lacunas. "
    "A resposta deve ser curta, operacional e pronta para virar mensagem de alerta. "
    "No campo summary, escreva em PT-BR com esta ordem: impacto observado, "
    "hipotese principal, evidencias-chave e principal lacuna. "
    "No campo next_steps, retorne passos acionaveis de validacao humana, sem "
    "remediacao automatica. "
    "No campo confidence_notes, explique limites da confianca e cite quando a "
    "LLM esta apenas refinando evidencia deterministica."
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
