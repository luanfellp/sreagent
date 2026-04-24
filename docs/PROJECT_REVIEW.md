# SREAgent — análise do projeto e roadmap prático

## Objetivo do produto
Construir um copilot SRE **somente leitura**, capaz de:
- receber alertas
- correlacionar sinais de observabilidade
- apontar uma **causa provável** com evidências
- sugerir **próximos passos**
- enviar esse resumo no **Telegram**
- funcionar com uma **mini infra fake** para demo e portfólio

---

## O que o projeto já faz bem

### 1. Boa direção de arquitetura
O projeto já está com uma base correta para SRE:
- API simples com FastAPI
- pipeline separado em enriquecimento, correlação, diagnóstico e sumarização
- modo read-only
- LLM opcional, sem substituir a camada determinística
- respostas estruturadas e testáveis

### 2. Boa base para demo
Já existe uma mini infra útil para demonstração:
- Prometheus
- Alertmanager
- Grafana
- Zabbix
- gerador fake de métricas
- envio de alertas para Telegram

### 3. Mensagem do produto é boa
A proposta é forte para portfólio e LinkedIn:
> “um copiloto SRE que recebe alertas, correlaciona sinais e devolve uma hipótese operacional com próximos passos — sem inventar dados e sem executar ações.”

---

## Principais lacunas hoje

### 1. Falta de observabilidade de logs real na demo
O projeto fala em Loki, mas o stack de demo atual **não sobe Loki**.
Hoje a parte de logs existe na arquitetura, mas na prática ainda não está demonstrada de ponta a ponta.

**Impacto:** a promessa “analisa logs e alertas” fica parcialmente incompleta na demo.

### 2. Zabbix está presente, mas não participa da análise
O container existe, mas o agente não usa sinais reais do Zabbix.

**Impacto:** para showcase, parece mais “componente decorativo” do que parte da solução.

### 3. Correlação ainda é simples
A correlação atual é honesta e segura, mas ainda básica:
- deploy recente
- erro dominante
- restart/crashloop
- fallback por severidade

**Impacto:** já serve para MVP, mas ainda não parece um “copilot SRE forte” para cenários mais variados.

### 4. A demo está mais forte em métrica do que em incidente completo
Hoje o melhor cenário é erro/latência via Prometheus.
Ainda faltam cenários mais ricos, por exemplo:
- regressão após deploy
- timeout em dependência downstream
- crashloop por config
- falha de entrega Telegram
- incidente com múltiplos sinais conflitantes

### 5. Falta uma narrativa mais forte de produto
O código está melhor do que a apresentação atual.
Ainda falta empacotar melhor:
- cenários prontos para demo
- prints/dashboard bonitos
- exemplos de alertas e respostas
- fluxo simples “suba, dispare, veja no Telegram”

---

## Minha avaliação honesta

### Como base técnica
**Boa.**
Você já tem um MVP coerente, funcional e com arquitetura correta.

### Como ferramenta real para reduzir MTTR
**Promissora, mas ainda inicial.**
Ela já reduz tempo em cenários simples, porque resume e sugere hipótese.
Mas ainda precisa amadurecer correlação e fontes de evidência para parecer realmente “assistente de incidente”.

### Como projeto de portfólio
**Muito bom potencial.**
Esse projeto tem cara de algo publicável no LinkedIn, desde que a demo fique mais redonda e visual.

---

## Prioridades recomendadas

## Prioridade 1 — fechar a promessa do produto
Essas são as melhorias mais importantes.

### 1. Subir Loki de verdade no ambiente demo
Adicionar Loki ao `docker-compose.local.yml` e fazer o `metrics-generator` ou outra fake API emitir logs consultáveis.

**Meta:** o agente realmente consultar logs recentes e citar evidências reais da demo.

### 2. Conectar o Zabbix na narrativa
Você não precisa integrar profundamente de primeira. Duas opções:
- **rápida:** usar Zabbix só como “fonte visual” da mini infra
- **ideal:** criar uma integração read-only simples para buscar estado/trigger fake

**Meta:** o Zabbix deixar de ser apenas figurante.

### 3. Criar 3 a 5 cenários de incidente prontos
Exemplos ideais:
- High 5xx rate
- Timeout em dependência
- CrashLoopBackOff após deploy
- Falha de entrega Telegram
- Latência alta sem erro alto

**Meta:** cada cenário disparar alerta + evidência + resposta no Telegram.

---

## Prioridade 2 — deixar a análise mais útil de verdade

### 4. Melhorar a correlação sem perder segurança
Sugestões:
- usar mais de um sinal para subir confiança
- explicitar por que a hipótese ganhou prioridade
- separar “causa provável” de “sintoma dominante”
- diferenciar incidente de app vs plataforma

### 5. Expor melhor as evidências no payload
Hoje já existe `evidence_ids`, o que é ótimo.
Eu adicionaria também no resumo final algo como:
- “Baseado em: Prometheus + Loki + Kubernetes”
- “Evidências fortes”
- “Evidências fracas/inconclusivas”

### 6. Criar um modo de saída “on-call”
Exemplo de campos úteis:
- severidade
- provável causa
- impacto provável
- onde olhar primeiro
- confiança
- evidências
- próximos passos

Isso deixa o alerta muito mais operacional.

---

## Prioridade 3 — transformar em demo forte para LinkedIn

### 7. Criar roteiro de demonstração
Um roteiro ideal:
1. subir a mini infra
2. abrir Grafana
3. ativar incidente fake
4. Prometheus dispara
5. Alertmanager chama o SREAgent
6. Telegram recebe a análise
7. mostrar dashboard + mensagem + API response

### 8. Preparar dados e screenshots
Separar material para postagem:
- dashboard normal
- dashboard em incidente
- payload do alerta
- resposta da API
- mensagem recebida no Telegram

### 9. Melhorar README para “demo-first”
O README precisa ter uma seção forte de showcase:
- “como subir tudo em 1 comando”
- “como disparar um incidente”
- “o que esperar no Telegram”
- “exemplos de incidentes”

---

## O que eu faria na sequência

### Fase 1 — tornar a demo verdadeira
- adicionar Loki ao compose
- fazer a fake API emitir logs estruturados
- integrar a consulta de logs real no fluxo
- manter Telegram funcionando

### Fase 2 — fortalecer a correlação
- enriquecer regras
- classificar confiança com base em múltiplos sinais
- melhorar explicabilidade

### Fase 3 — empacotar para portfólio
- dashboards mais bonitos
- README orientado a demo
- incidentes prontos para screenshot
- exemplos de payload/response

---

## Conclusão
O projeto **já tem uma base boa e coerente**.
Ele **não está longe** de virar uma demo muito forte.

Hoje, eu resumiria assim:

> Você já tem um MVP funcional de copilot SRE read-only.
> O próximo salto não é “reescrever tudo”, e sim **fechar a demo ponta a ponta com logs reais da mini infra, cenários prontos e uma apresentação mais forte**.

Se isso for bem embalado, dá sim para virar um projeto muito bom de showcase técnico e também algo útil no dia a dia.
