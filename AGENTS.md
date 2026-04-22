# AGENTS.md

Objetivo:
Construir um copilot de incidente SRE em modo read-only.

Diretrizes:
- Usar Python com FastAPI.
- Não executar ações destrutivas.
- Não alterar ambientes reais.
- Separar coleta, correlação e resposta.
- Preferir código simples, modular e testável.
- Toda hipótese deve vir acompanhada de evidências.

Escopo inicial:
- Receber alertas HTTP.
- Normalizar payload.
- Gerar resumo estruturado.
- Expor endpoint de healthcheck.
- Usar mocks para integrações externas.

Definition of done:
- Projeto roda localmente.
- Há README com setup.
- Há pelo menos 1 teste.
- Estrutura pronta para integrar Prometheus, Loki, Kubernetes, Slack e Zabbix.
