---
id: T-260923-d20893-gemini-indisponivel-tentar-ate-conseguir
room: bugfix
created: 2026-09-23T01:32:14.000Z
---

# Goal

Gemini indisponível: tentar até conseguir. Quando o Gemini estiver indisponível ou der timeout, as tarefas devem tentar de novo até ter êxito, e não desistir após 5 tentativas.

## Acceptance

- [ ] Indisponibilidade: Given o Gemini responde com um código temporário (429, 500, 502, 503 ou 504) mais vezes do que o antigo limite de 5 When gerar_json é chamado Then continua tentando, com espera crescente limitada a ESPERA_MAXIMA, até obter uma resposta válida (teste de regressão com 8 respostas 503 seguidas de sucesso; falha no código anterior).
- [ ] Timeout: Given a chamada ao Gemini estoura o timeout do cliente (httpx.TimeoutException) ou tem outra falha de rede (httpx.TransportError) When gerar_json é chamado Then espera alguns minutos (ESPERA_TIMEOUT) e tenta de novo, sem limite de tentativas; o cliente genai é criado com um timeout explícito (teste).
- [ ] Erros permanentes continuam falhando na hora: um código que não é temporário (ex.: 400, 401, 403) é relançado sem nova tentativa, e uma resposta com JSON inválido ou reprovada pelo validador continua limitada a 5 tentativas (teste).
- [ ] Sem perda de histórico durante esperas longas: Given uma tarefa (manhã ou noite) fica esperando o Gemini enquanto outra grava no historico_bitcoin.json When a primeira termina Then ela relê o histórico logo antes de alterar e salvar, e a entrada gravada pela outra tarefa é preservada; a noite avalia a mesma entrada que selecionou no início (mesma data e preco_8h) e continua usando o preço capturado antes de chamar o Gemini (teste que simula a gravação concorrente).
- [ ] `python -m py_compile robot_bitcoin.py` e `python -m unittest -v test_robot_bitcoin` passam sem rede e sem esperas reais (time.sleep simulado); requirements.txt sem dependências novas.

## Context

- Falha observada em produção em 2026-09-22 22:00 (logs/bot.log, leitura somente): 503 UNAVAILABLE "This model is currently experiencing high demand" nas 5 tentativas (esperas de 20, 40, 60 e 80 s) e depois `google.genai.errors.ServerError` e o alerta "⚠️ Falha na tarefa 'noite'". A previsão de 2026-09-22 ficou sem avaliação.
- Causa raiz: `gerar_json` (`robot_bitcoin.py`, antes da correção) tem max_tentativas=5 para TODOS os tipos de erro, e o `genai.Client()` é criado sem timeout.
- Pedido do dono (Marco, 2026-09-22, conversa): "Caso o serviço esteja indisponível, o comportamento esperado é tentar novamente e só parar quando conseguir êxito. Nesse caso, timeout é tentar novamente após alguns minutos."
- Risco criado pela correção: com esperas de horas, a noite pode salvar uma cópia antiga do histórico por cima da entrada que a manhã gravou (e vice-versa). Por isso a releitura antes de salvar faz parte do aceite.
- `google.genai.types.HttpOptions.timeout` é em milissegundos (verificado na .venv em 2026-09-23).
- Regras: BR-C4 (janela de avaliação) e BR-C6 (alerta de falha) continuam valendo. BR-1 a BR-4 não mudam.
- Fonte: `robot_bitcoin.py` @ b0f3625.

## Owned files

- robot_bitcoin.py
- test_robot_bitcoin.py

## Business-rule gaps

## Log

- 2026-09-23: tarefa criada pelo orquestrador. Delegada ao Antigravity (agy) na worktree `../Bot_previsao_bitcoin-wt/retentativas`, branch `fix/gemini-tentar-ate-conseguir`.

## Evidence
