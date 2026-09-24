---
id: T-260924-5eca01-lista-padrao-de-modelos-com-outras-familias-do-g
room: bugfix
created: 2026-09-24T14:55:34.513Z
---

# Goal

Lista padrão de modelos com outras famílias do Gemini. Quando os modelos 3.x estão todos sobrecarregados, o bot ainda precisa de alternativas que respondam.

## Acceptance

- [ ] Given GEMINI_MODELOS não está definido When a lista é montada Then ela é [GEMINI_MODEL ou gemini-3.8-flash, gemini-2.5-flash, gemini-3-flash-preview, gemini-3.7-flash, gemini-3.6-flash, gemini-3.5-flash, gemini-3.5-flash-lite], alternando famílias para que uma sobrecarga da família 3.x não bloqueie todas as primeiras opções (teste).
- [ ] `python -m py_compile robot_bitcoin.py` e `python -m unittest -v test_robot_bitcoin` passam sem rede.

## Context

- Em 2026-09-24, das 11:19 às 11:53, gemini-3.7/3.6/3.5-flash responderam 503 em 14 tentativas seguidas; o 3.8 estava sem cota diária. A previsão só saiu às 11:54, rodada à mão com GEMINI_MODELOS ampliado, pelo gemini-2.5-flash.
- Teste de uma chamada por modelo às 11:52, com prompt de tamanho real e o SCHEMA_PREVISAO: gemini-2.5-flash OK em 3 s, gemini-3-flash-preview OK em 8 s, gemini-3.5-flash-lite OK em 49 s; gemini-flash-latest 429 diário (compartilha a cota), gemini-3.1-flash-lite 503, gemini-2.5-flash-lite 404.
- Tarefa pai: T-260924-490102 (troca de modelo). Fonte: `robot_bitcoin.py` @ 580d41a.
- Mudança de uma linha, feita pelo orquestrador (tarefa trivial).

## Owned files

- robot_bitcoin.py
- test_robot_bitcoin.py

## Business-rule gaps

## Log

- 2026-09-24: tarefa criada e implementada pelo orquestrador, na branch `fix/modelos-outras-familias`.

## Evidence
