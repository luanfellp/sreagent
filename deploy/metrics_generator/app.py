from __future__ import annotations

import json
import os
import random
import threading
import time
from collections import deque
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask, Response, jsonify, request
from prometheus_client import CONTENT_TYPE_LATEST, CollectorRegistry, Counter, Gauge, Histogram, generate_latest

app = Flask(__name__)
registry = CollectorRegistry()

SERVICE = os.getenv("DEMO_SERVICE", "checkout")
ENVIRONMENT = os.getenv("DEMO_ENVIRONMENT", "prod")
COMPONENT = os.getenv("DEMO_COMPONENT", "api")
LOGGER_NAME = os.getenv("DEMO_LOGGER", f"{SERVICE}-{COMPONENT}")
LOG_PATH = Path(os.getenv("DEMO_LOG_PATH", f"/var/log/demo/{SERVICE}-app.log"))

REQUESTS = Counter(
    "http_requests_total",
    "Total requests",
    ["service", "environment", "code"],
    registry=registry,
)
LATENCY_SECONDS = Histogram(
    "http_request_duration_seconds",
    "Request latency in seconds",
    ["service", "environment"],
    buckets=(0.05, 0.1, 0.2, 0.3, 0.5, 1.0, 2.0, 5.0),
    registry=registry,
)
LATENCY_MS = Gauge(
    "http_request_duration_ms",
    "Request latency in ms",
    ["service", "environment"],
    registry=registry,
)
SCENARIO_ACTIVE = Gauge(
    "app_scenario_active",
    "Active scenario flag",
    ["service", "environment", "scenario"],
    registry=registry,
)
RECENT_DEPLOY = Gauge(
    "app_recent_deploy",
    "Recent deploy marker",
    ["service", "environment"],
    registry=registry,
)
RESTART_COUNT = Gauge(
    "app_restart_count",
    "Simulated restart count",
    ["service", "environment"],
    registry=registry,
)
CRASHLOOP_DETECTED = Gauge(
    "app_crashloop_detected",
    "CrashLoopBackOff simulated marker",
    ["service", "environment"],
    registry=registry,
)

SCENARIOS = {
    "normal": {
        "success_rate": 0.995,
        "latency_ms": (40, 160),
        "log_level": "info",
        "message": "Tráfego estável dentro do baseline.",
        "error_hint": None,
        "recent_deploy": False,
        "restart_count": 0,
        "crashloop": False,
    },
    "high5xx": {
        "success_rate": 0.35,
        "latency_ms": (250, 700),
        "log_level": "error",
        "message": "Erro 5xx recorrente ao processar checkout.",
        "error_hint": "http-5xx",
        "recent_deploy": False,
        "restart_count": 1,
        "crashloop": False,
    },
    "timeout": {
        "success_rate": 0.7,
        "latency_ms": (900, 1800),
        "log_level": "error",
        "message": "Timeout ao chamar dependência downstream payment-gateway.",
        "error_hint": "timeout",
        "recent_deploy": False,
        "restart_count": 1,
        "crashloop": False,
    },
    "crashloop": {
        "success_rate": 0.45,
        "latency_ms": (150, 500),
        "log_level": "critical",
        "message": "Pod entrando em CrashLoopBackOff após falha de inicialização.",
        "error_hint": "crashloopbackoff",
        "recent_deploy": False,
        "restart_count": 5,
        "crashloop": True,
    },
    "deploy_regression": {
        "success_rate": 0.82,
        "latency_ms": (450, 1200),
        "log_level": "warning",
        "message": "Latência elevada após deploy recente do serviço checkout.",
        "error_hint": "timeout",
        "recent_deploy": True,
        "restart_count": 2,
        "crashloop": False,
    },
}

state = {
    "scenario": "normal",
    "last_changed": time.time(),
    "events": deque(maxlen=25),
}
lock = threading.Lock()


def _ensure_log_dir() -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    LOG_PATH.touch(exist_ok=True)


def _write_log(level: str, message: str, **extra: object) -> None:
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "service": SERVICE,
        "environment": ENVIRONMENT,
        "component": COMPONENT,
        "logger": LOGGER_NAME,
        "log_source": "application",
        "level": level,
        "scenario": state["scenario"],
        "message": message,
        **extra,
    }
    line = json.dumps(entry, ensure_ascii=False)
    with LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")
    print(line, flush=True)
    state["events"].append(entry)


def _set_scenario(name: str) -> None:
    if name not in SCENARIOS:
        raise ValueError(f"cenário inválido: {name}")
    with lock:
        state["scenario"] = name
        state["last_changed"] = time.time()
    _write_log("info", f"Cenário alterado para {name}.", scenario_change=name)


def _scenario_payload() -> dict[str, object]:
    scenario = state["scenario"]
    config = SCENARIOS[scenario]
    seconds_since_change = int(time.time() - state["last_changed"])
    return {
        "service": SERVICE,
        "environment": ENVIRONMENT,
        "scenario": scenario,
        "seconds_since_change": seconds_since_change,
        "config": config,
        "recent_events": list(state["events"]),
        "available_scenarios": list(SCENARIOS),
        "log_path": str(LOG_PATH),
    }


def _apply_scenario_metrics(config: dict[str, object]) -> None:
    for name in SCENARIOS:
        SCENARIO_ACTIVE.labels(service=SERVICE, environment=ENVIRONMENT, scenario=name).set(
            1 if name == state["scenario"] else 0
        )
    RECENT_DEPLOY.labels(service=SERVICE, environment=ENVIRONMENT).set(
        1 if config["recent_deploy"] else 0
    )
    RESTART_COUNT.labels(service=SERVICE, environment=ENVIRONMENT).set(config["restart_count"])
    CRASHLOOP_DETECTED.labels(service=SERVICE, environment=ENVIRONMENT).set(
        1 if config["crashloop"] else 0
    )


def _simulate_traffic() -> None:
    _ensure_log_dir()
    while True:
        with lock:
            scenario = state["scenario"]
        config = SCENARIOS[scenario]
        _apply_scenario_metrics(config)

        success = random.random() <= float(config["success_rate"])
        code = "200" if success else random.choice(["500", "502", "503", "504"])
        latency_ms = random.uniform(*config["latency_ms"])
        latency_seconds = latency_ms / 1000.0

        REQUESTS.labels(service=SERVICE, environment=ENVIRONMENT, code=code).inc()
        LATENCY_SECONDS.labels(service=SERVICE, environment=ENVIRONMENT).observe(latency_seconds)
        LATENCY_MS.labels(service=SERVICE, environment=ENVIRONMENT).set(latency_ms)

        log_level = str(config["log_level"])
        message = str(config["message"])
        if success and scenario == "normal":
            _write_log(log_level, message, http_status=code, latency_ms=round(latency_ms, 2))
        elif success:
            _write_log(
                "warning",
                message,
                http_status=code,
                latency_ms=round(latency_ms, 2),
                dominant_error=config["error_hint"],
            )
        else:
            _write_log(
                log_level,
                message,
                http_status=code,
                latency_ms=round(latency_ms, 2),
                dominant_error=config["error_hint"],
            )

        time.sleep(0.5)


@app.route("/metrics")
def metrics() -> Response:
    data = generate_latest(registry)
    return Response(data, mimetype=CONTENT_TYPE_LATEST)


@app.route("/toggle_error", methods=["POST"])
def toggle_error() -> tuple[str, int]:
    enabled = request.args.get("on", "true").lower() in {"1", "true", "yes", "on"}
    _set_scenario("high5xx" if enabled else "normal")
    return ("", 204)


@app.route("/scenario", methods=["GET", "POST"])
def scenario() -> Response:
    if request.method == "GET":
        return jsonify(_scenario_payload())

    payload = request.get_json(silent=True) or {}
    name = payload.get("name") or request.args.get("name") or "normal"
    _set_scenario(str(name))
    return jsonify(_scenario_payload())


@app.route("/scenario/reset", methods=["POST"])
def scenario_reset() -> tuple[str, int]:
    _set_scenario("normal")
    return ("", 204)


@app.route("/health")
def health() -> Response:
    return jsonify({"status": "ok", **_scenario_payload()})


if __name__ == "__main__":
    worker = threading.Thread(target=_simulate_traffic, daemon=True)
    worker.start()
    app.run(host="0.0.0.0", port=8001)
