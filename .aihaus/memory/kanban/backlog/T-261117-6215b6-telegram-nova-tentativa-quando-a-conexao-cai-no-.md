---
id: T-261117-6215b6-telegram-nova-tentativa-quando-a-conexao-cai-no-
room: bugfix
created: 2026-11-17T13:05:00.000Z
---

# Goal

Telegram: nova tentativa quando a conexão cai no envio. Hoje uma única queda de conexão com o Telegram faz a mensagem se perder sem aviso.

## Acceptance

- [ ] Given o envio ao Telegram falha por erro de rede (conexão cortada ou recusada) When enviar_telegram é chamado Then tenta de novo algumas vezes, com espera curta, antes de desistir, e registra cada falha no log (teste de regressão que falha no código anterior).
- [ ] Given o Telegram responde com status diferente de 200 When enviar_telegram é chamado Then o comportamento atual se mantém, sem novas tentativas para erros de conteúdo (teste).
- [ ] `python -m py_compile robot_bitcoin.py` e `python -m unittest -v test_robot_bitcoin` passam sem rede.

## Context

- Fonte: `robot_bitcoin.py` @ bdc18a2, `enviar_telegram` (uma só chamada `requests.post` com timeout=15; qualquer exceção vira "Erro de conexão com o Telegram" e retorna False).
- Produção (somente leitura, `ssh oracle-bot`, logs/bot.log mais os 8 arquivos rotacionados, 2026-11-17): 6 mensagens perdidas em 726 execuções desde 2026-09-22, todas da tarefa `preco`: 2026-09-29 12:00 (Read timed out), 2026-11-02 12:00, 2026-11-06 10:00, 2026-11-08 14:00 e 2026-11-15 10:00 (ConnectionResetError 104), e 2026-11-09 10:00 (Read timed out). Cinco foram em novembro.
- Encontrado pelo orquestrador durante o diagnóstico da tarefa T-261117-11f0d5.

## Owned files

- robot_bitcoin.py
- test_robot_bitcoin.py

## Business-rule gaps

### Q-becc3f

Question: Em 'Read timed out' o Telegram pode já ter recebido a mensagem, e um novo envio pode duplicá-la. Nesse caso, o bot deve arriscar uma mensagem duplicada (tentar de novo) ou aceitar perder a mensagem (não tentar)?

Answer: pending

Draft rule: pending

## Log

- 2026-11-17: ingerida no backlog pelo orquestrador; ainda sem implementação.

## Evidence
