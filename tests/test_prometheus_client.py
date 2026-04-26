import httpx

from app.integrations.prometheus_client import PrometheusHTTPClient


def test_prometheus_client_returns_snapshot_when_api_fails() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"status": "error"})

    client = PrometheusHTTPClient(
        "http://prometheus:9090",
        transport=httpx.MockTransport(handler),
    )

    snapshot = client.query_service_health("checkout", "prod")

    assert snapshot.status == "ok"
    assert snapshot.latency_p95_ms is None
    assert snapshot.error_rate_per_minute is None
    assert "Falha ao consultar Prometheus" in snapshot.summary
