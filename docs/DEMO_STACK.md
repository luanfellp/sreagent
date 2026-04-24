# Demo stack local

## O que sobe
- **SREAgent** em `http://localhost:8002`
- **Grafana** em `http://localhost:3000`
- **Prometheus** em `http://localhost:9091`
- **Alertmanager** em `http://localhost:9093`
- **Loki** em `http://localhost:3100`
- **Fake API / metrics generator** em `http://localhost:8001`
- **Zabbix** em `http://localhost:8080`

## Subir a stack
Antes do primeiro `up`, copie o arquivo de exemplo:
```bash
cp deploy/.env.example deploy/.env
```

Depois suba a stack:
```bash
docker compose -f deploy/docker-compose.local.yml up -d --build
```

## Cenários disponíveis
O fake service suporta estes cenários:
- `normal`
- `high5xx`
- `timeout`
- `crashloop`
- `deploy_regression`

## Ativar um cenário manualmente
```bash
curl -X POST 'http://localhost:8001/scenario?name=timeout'
```

## Resetar para normal
```bash
curl -X POST 'http://localhost:8001/scenario/reset'
```

## Rodar um incidente de demonstração
```bash
bash deploy/test_incident.sh timeout
```

## Rodar a bateria de cenários
```bash
bash deploy/run_demo_scenarios.sh
```

## Fluxo da análise inicial
1. O fake service escreve **logs reais da aplicação** em `/var/log/demo/checkout-app.log`.
2. O Promtail coleta esses logs e envia para o Loki com labels como `service`, `environment` e `log_source=application`.
3. O Prometheus avalia as regras de erro, latência, restart e deploy.
4. O Alertmanager envia o webhook para o SREAgent.
5. O SREAgent consulta **Prometheus + Loki** antes de montar a análise inicial.
6. O resumo final inclui um bloco explícito de **logs da aplicação** com evidência recente.
7. O resumo é enviado para o Telegram configurado.

## Dashboard sugerido
No Grafana, abra:
- **Incident Workbench**

Esse dashboard mostra:
- taxa de erro
- latência p95
- restart count
- cenário ativo
- logs recentes no Loki

## Observações
- O projeto continua em **modo somente leitura**.
- O Zabbix está incluído como parte da mini infra visual da demo.
- A análise inicial usa evidências reais da demo para Prometheus e **logs da aplicação no Loki**.
- Os segredos locais ficam em `deploy/secrets/` e não devem ir para o Git.
- Sem provider real de Kubernetes, o agente usa apenas metadados do alerta para sinais de workload.
