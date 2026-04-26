from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

from app.integrations.models import KubernetesWorkloadStatus

DEFAULT_SERVICE_ACCOUNT_TOKEN = "/var/run/secrets/kubernetes.io/serviceaccount/token"
DEFAULT_SERVICE_ACCOUNT_CA = "/var/run/secrets/kubernetes.io/serviceaccount/ca.crt"


def _read_optional_file(path: str | None) -> str | None:
    if not path:
        return None

    try:
        value = Path(path).read_text(encoding="utf-8").strip()
    except OSError:
        return None
    return value or None


def _parse_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _minutes_ago(value: str | None, now: datetime) -> int | None:
    timestamp = _parse_timestamp(value)
    if timestamp is None:
        return None
    return max(0, int((now - timestamp).total_seconds() // 60))


def _unique_join(values: list[str]) -> str | None:
    unique = sorted({value for value in values if value})
    if not unique:
        return None
    return ", ".join(unique)


class KubernetesHTTPClient:
    def __init__(
        self,
        base_url: str,
        namespace: str | None = None,
        label_key: str = "app",
        token_file: str | None = None,
        ca_cert_file: str | None = None,
        timeout: float = 5.0,
        transport: httpx.BaseTransport | None = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.namespace = namespace
        self.label_key = label_key
        token = _read_optional_file(token_file or DEFAULT_SERVICE_ACCOUNT_TOKEN)
        headers = {"Authorization": f"Bearer {token}"} if token else None
        verify = ca_cert_file or DEFAULT_SERVICE_ACCOUNT_CA
        verify_config: bool | str = verify if Path(verify).exists() else True
        self._client = httpx.Client(
            headers=headers,
            timeout=timeout,
            verify=verify_config,
            transport=transport,
        )

    def close(self) -> None:
        self._client.close()

    def _namespace_for(self, environment: str) -> str:
        if self.namespace:
            return self.namespace
        if environment and environment != "unknown":
            return environment
        return "default"

    def _get_items(self, path: str, service: str) -> list[dict[str, Any]]:
        selector = f"{self.label_key}={service}"
        response = self._client.get(
            f"{self.base_url}{path}",
            params={"labelSelector": selector},
        )
        response.raise_for_status()
        return response.json().get("items", [])

    @staticmethod
    def _pod_status(pods: list[dict[str, Any]]) -> tuple[int, bool, str | None]:
        restart_count = 0
        crashloop_detected = False
        statuses: list[str] = []

        for pod in pods:
            phase = str(pod.get("status", {}).get("phase") or "")
            if phase:
                statuses.append(phase)

            for container in pod.get("status", {}).get("containerStatuses", []) or []:
                restart_count += int(container.get("restartCount") or 0)
                waiting = (container.get("state") or {}).get("waiting") or {}
                reason = str(waiting.get("reason") or "")
                if reason:
                    statuses.append(reason)
                if "crashloop" in reason.lower():
                    crashloop_detected = True

        return restart_count, crashloop_detected, _unique_join(statuses)

    @staticmethod
    def _deployment_status(
        deployments: list[dict[str, Any]], now: datetime
    ) -> tuple[bool, int | None, bool]:
        recent_deploy = False
        deploy_minutes_ago: int | None = None
        rollout_in_progress = False

        for deployment in deployments:
            metadata = deployment.get("metadata", {}) or {}
            status = deployment.get("status", {}) or {}
            spec = deployment.get("spec", {}) or {}
            desired_replicas = int(spec.get("replicas") or 0)
            updated_replicas = int(status.get("updatedReplicas") or 0)
            available_replicas = int(status.get("availableReplicas") or 0)
            generation = int(metadata.get("generation") or 0)
            observed_generation = int(status.get("observedGeneration") or 0)

            if (
                observed_generation < generation
                or updated_replicas < desired_replicas
                or available_replicas < desired_replicas
            ):
                rollout_in_progress = True

            timestamps = [
                metadata.get("creationTimestamp"),
                *[
                    condition.get("lastUpdateTime")
                    for condition in status.get("conditions", []) or []
                ],
            ]
            for timestamp in timestamps:
                minutes = _minutes_ago(timestamp, now)
                if minutes is None:
                    continue
                deploy_minutes_ago = (
                    minutes
                    if deploy_minutes_ago is None
                    else min(deploy_minutes_ago, minutes)
                )
                if minutes <= 30:
                    recent_deploy = True

        return recent_deploy, deploy_minutes_ago, rollout_in_progress

    def describe_workload(
        self, service: str, environment: str
    ) -> KubernetesWorkloadStatus:
        namespace = self._namespace_for(environment)
        try:
            pods = self._get_items(f"/api/v1/namespaces/{namespace}/pods", service)
            deployments = self._get_items(
                f"/apis/apps/v1/namespaces/{namespace}/deployments",
                service,
            )
        except Exception as exc:
            return KubernetesWorkloadStatus(
                service=service,
                environment=environment,
                summary=(
                    f"Falha ao consultar Kubernetes em modo somente leitura para "
                    f"{service} no namespace {namespace}: {exc}"
                ),
            )

        now = datetime.now(UTC)
        restart_count, crashloop_detected, pod_status = self._pod_status(pods)
        recent_deploy, deploy_minutes_ago, rollout_in_progress = (
            self._deployment_status(deployments, now)
        )

        if not pods and not deployments:
            summary = (
                f"Kubernetes consultado em modo somente leitura, mas nenhum pod ou "
                f"deployment com {self.label_key}={service} foi encontrado no namespace {namespace}."
            )
        else:
            summary = (
                f"Kubernetes consultado em modo somente leitura no namespace {namespace}: "
                f"{len(pods)} pod(s), {len(deployments)} deployment(s), "
                f"{restart_count} restart(s) observados."
            )

        return KubernetesWorkloadStatus(
            service=service,
            environment=environment,
            summary=summary,
            recent_deploy=recent_deploy,
            deploy_minutes_ago=deploy_minutes_ago,
            rollout_in_progress=rollout_in_progress,
            restart_count=restart_count,
            crashloop_detected=crashloop_detected,
            pod_status=pod_status,
        )
