import json

import httpx

from app.integrations.kubernetes_client import KubernetesHTTPClient


def test_kubernetes_client_collects_read_only_workload_status() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["labelSelector"] == "app=checkout"

        if request.url.path.endswith("/pods"):
            return httpx.Response(
                200,
                json={
                    "items": [
                        {
                            "status": {
                                "phase": "Running",
                                "containerStatuses": [
                                    {
                                        "restartCount": 3,
                                        "state": {
                                            "waiting": {
                                                "reason": "CrashLoopBackOff",
                                            }
                                        },
                                    }
                                ],
                            }
                        }
                    ]
                },
            )

        if request.url.path.endswith("/deployments"):
            return httpx.Response(
                200,
                json={
                    "items": [
                        {
                            "metadata": {
                                "generation": 2,
                                "creationTimestamp": "2026-04-26T11:00:00Z",
                            },
                            "spec": {"replicas": 2},
                            "status": {
                                "observedGeneration": 1,
                                "updatedReplicas": 1,
                                "availableReplicas": 1,
                                "conditions": [
                                    {
                                        "lastUpdateTime": "2026-04-26T11:10:00Z",
                                    }
                                ],
                            },
                        }
                    ]
                },
            )

        return httpx.Response(404, content=json.dumps({"error": "not found"}))

    client = KubernetesHTTPClient(
        "https://kubernetes.default.svc",
        namespace="prod",
        transport=httpx.MockTransport(handler),
    )

    status = client.describe_workload("checkout", "prod")

    assert status.service == "checkout"
    assert status.environment == "prod"
    assert status.restart_count == 3
    assert status.crashloop_detected is True
    assert status.rollout_in_progress is True
    assert status.pod_status == "CrashLoopBackOff, Running"
    assert "modo somente leitura" in status.summary


def test_kubernetes_client_returns_evidence_gap_when_api_fails() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, json={"message": "forbidden"})

    client = KubernetesHTTPClient(
        "https://kubernetes.default.svc",
        namespace="prod",
        transport=httpx.MockTransport(handler),
    )

    status = client.describe_workload("checkout", "prod")

    assert status.restart_count == 0
    assert status.crashloop_detected is False
    assert "Falha ao consultar Kubernetes" in status.summary
