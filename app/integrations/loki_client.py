import json
import time
import urllib.parse

import httpx

from app.integrations.models import LokiErrorSummary


class LokiHTTPClient:
    def __init__(self, base_url: str, timeout: float = 5.0):
        self.base_url = base_url.rstrip("/")
        self._client = httpx.Client(timeout=timeout)

    @staticmethod
    def _detect_dominant_error(lines: list[str]) -> str | None:
        joined = " ".join(line.lower() for line in lines)
        if "crashloop" in joined:
            return "crashloopbackoff"
        if "timeout" in joined:
            return "timeout"
        if "5xx" in joined or ' 500 ' in joined or ' 503 ' in joined or ' 504 ' in joined:
            return "http-5xx"
        if "exception" in joined:
            return "exception"
        return None

    @staticmethod
    def _format_example(line: str) -> str:
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            return line.strip()

        level = str(payload.get("level") or "log").lower()
        status = str(payload.get("http_status") or "-")
        latency = payload.get("latency_ms")
        latency_label = f" {latency}ms" if latency is not None else ""
        message = str(payload.get("message") or line).strip()
        return f"{level} {status}{latency_label} - {message}"

    def query_recent_errors(self, service: str, environment: str) -> LokiErrorSummary:
        now = int(time.time())
        start = (now - 300) * 1_000_000_000
        end = now * 1_000_000_000
        label_selector = (
            f'{{service="{service}",environment="{environment}",log_source="application",level=~"warning|error|critical"}}'
        )
        query = label_selector
        encoded = urllib.parse.quote_plus(query)
        url = (
            f"{self.base_url}/loki/api/v1/query_range?query={encoded}"
            f"&start={start}&end={end}&limit=200&direction=backward"
        )
        try:
            resp = self._client.get(url)
            resp.raise_for_status()
            data = resp.json()
            streams = data.get("data", {}).get("result", [])
            lines: list[str] = []
            for stream in streams:
                values = stream.get("values", [])
                for _, line in values:
                    lines.append(line)

            error_count = len(lines)
            examples = [self._format_example(line) for line in lines[:5]]
            dominant = self._detect_dominant_error(examples)
            if error_count == 0:
                summary = (
                    f"Loki não encontrou logs de aplicação relevantes para {service} em {environment} nos últimos 5 minutos."
                )
            else:
                summary = (
                    f"Loki acessou logs reais da aplicação {service} em {environment} e encontrou "
                    f"aproximadamente {error_count} eventos relevantes nos últimos 5 minutos. "
                    f"Exemplo recente: {examples[0]}"
                )
            return LokiErrorSummary(
                service=service,
                environment=environment,
                summary=summary,
                dominant_error=dominant,
                error_count=error_count,
                examples=examples,
            )
        except Exception as exc:
            return LokiErrorSummary(
                service=service,
                environment=environment,
                summary=f"Falha ao consultar logs da aplicação no Loki: {exc}",
                dominant_error=None,
                error_count=0,
                examples=[],
            )
