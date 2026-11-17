---
id: T-261117-b5236e-depois-de-2026-12-01-tirar-o-gemini-2-5-flash-da
room: feature
created: 2026-11-17T13:20:00.000Z
---

# Goal

Depois de 2026-12-01: tirar o gemini-2.5-flash da lista padrão. A partir dessa data a API redireciona o gemini-2.5-flash para o gemini-3.5-flash-lite, que já está no fim da lista. A entrada vira um repetido na segunda posição, e o campo `modelos` do histórico registraria "gemini-2.5-flash" para respostas que vieram de outro modelo.

## Acceptance

- [ ] Given GEMINI_MODELOS não está definido When a lista é montada Then ela não contém o gemini-2.5-flash, e a segunda posição passa a ser um modelo que respondeu nos dias anteriores (conferir no log e no campo `modelos` do histórico do servidor) (teste).
- [ ] `python -m py_compile robot_bitcoin.py` e `python -m unittest -v test_robot_bitcoin` passam sem rede.

## Context

- Fonte: documentação de descontinuação do Gemini (aistudio.google.com/docs/deprecations, lida em 2026-11-17): "gemini-2.5-flash" é descontinuado e, a partir de 2026-12-01, as chamadas vão para o gemini-3.5-flash-lite.
- Origem: T-261117-11f0d5, que manteve o 2.5-flash em segundo lugar até a data, porque em 2026-11-17 ele era a reserva que mais respondia (38 de 51 amostras de novembro).
- Não fazer antes de 2026-12-01.

## Owned files

- robot_bitcoin.py
- test_robot_bitcoin.py

## Business-rule gaps

## Log

- 2026-11-17: ingerida no backlog pelo orquestrador (achado informativo da revisão adversarial de T-261117-11f0d5).

## Evidence
