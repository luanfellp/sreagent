import urllib.parse
from typing import Optional

import httpx

from app.core.query_safety import build_label_matchers
from app.integrations.models import PrometheusSnapshot


class PrometheusHTTPClient:
    def __init__(self, base_url: str, p95_metric: Optional[str] = None, timeout: float = 5.0):
        self.base_url = base_url.rstrip("/")
        self.p95_metric = p95_metric
        self._client = httpx.Client(timeout=timeout)

    def close(self) -> None:
        self._client.close()

    def _query(self, expr: str) -> float:
        encoded = urllib.parse.quote_plus(expr)
        url = f"{self.base_url}/api/v1/query?query={encoded}"
        resp = self._client.get(url)
        resp.raise_for_status()
        data = resp.json()
        try:
            return float(data.get("data", {}).get("result", [])[0].get("value", [None, 0])[1])
        except Exception:
            return 0.0

    def query_service_health(self, service: str, environment: str) -> PrometheusSnapshot:
        labels = build_label_matchers(
            {"service": service, "environment": environment}
        )
        err_expr = f'sum(rate(http_requests_total{{{labels},code=~"5.."}}[5m]))'
        tot_expr = f'sum(rate(http_requests_total{{{labels}}}[5m]))'

        err = self._query(err_expr)
        tot = self._query(tot_expr)
        error_rate_per_min = None
        percent = 0.0
        if tot > 0:
            percent = (err / tot) * 100.0
            error_rate_per_min = int(err * 60)

        status = "ok"
        if percent >= 10.0:
            status = "critical"
        elif percent >= 5.0:
            status = "degraded"

        latency_p95 = None
        metric_name = self.p95_metric or "http_request_duration_seconds"
        try:
            p95_expr = (
                f'histogram_quantile(0.95, sum(rate({metric_name}_bucket{{{labels}}}[5m])) by (le))'
            )
            p95_seconds = self._query(p95_expr)
            latency_p95 = int(p95_seconds * 1000) if p95_seconds else None
        except Exception:
            latency_p95 = None

        summary = (
            f"Prometheus indica taxa de erro aproximada de {percent:.2f}% para {service} em {environment} "
            f"(thresholds 5%/10%), com status {status}."
        )

        return PrometheusSnapshot(
            service=service,
            environment=environment,
            metric_name=metric_name,
            status=status,
            summary=summary,
            latency_p95_ms=latency_p95,
            error_rate_per_min=error_rate_per_min,
        )
