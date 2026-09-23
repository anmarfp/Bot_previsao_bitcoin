---
id: T-260923-c8efd6-preco-da-noite-binance-quando-o-coingecko-falhar
room: bugfix
created: 2026-09-23T02:52:29.563Z
---

# Goal

Preço da noite: Binance quando o CoinGecko falhar. Quando o CoinGecko estiver indisponível na hora da avaliação (22h) ou da atualização de 2 em 2 horas, o bot usa o preço da Binance em vez de falhar ou ficar em silêncio.

## Acceptance

- [x] Given o CoinGecko responde normalmente When obter_preco_bitcoin é chamado Then devolve o preço do CoinGecko e a Binance não é consultada (teste).
- [x] Given o CoinGecko falha (sem resposta após as tentativas do pedir, ou resposta sem o preço) When obter_preco_bitcoin é chamado Then devolve o preço de `data-api.binance.vision/api/v3/ticker/price?symbol=BTCUSDT` e registra no log que usou a Binance; se as duas fontes falharem, devolve None como hoje (teste).
- [x] Given o CoinGecko está fora às 22h When verificacao_noite roda Then a previsão é avaliada com o preço da Binance, em vez de levantar "Não foi possível obter o preço do BTC no CoinGecko" (teste de regressão que falha no código anterior).
- [x] `python -m py_compile robot_bitcoin.py` e `python -m unittest -v test_robot_bitcoin` passam sem rede e sem esperas reais; requirements.txt sem dependências novas.

## Context

- Pendência registrada em procedures.md (2026-09-23): se o CoinGecko estiver fora às 22h, a `noite` falha após as 3 tentativas do `pedir()`. Repetir por horas mudaria o preço avaliado. O orquestrador propôs usar a Binance como alternativa, e o dono (Marco, 2026-09-23) mandou prosseguir.
- Causa raiz: `obter_preco_bitcoin` (`robot_bitcoin.py`) tem uma única fonte. A noite levanta RuntimeError quando ela falha, e o relatório de 2h apenas não envia.
- O preço de BTCUSDT (Binance) e o de BTC/USD (CoinGecko) diferem pouco (0,02% em 2026-09-23: 86.477 contra 86.457). O endpoint `data-api.binance.vision/api/v3/ticker/price` respondeu HTTP 200 do PC e do servidor em 2026-09-23.
- A mesma escolha já foi usada na avaliação manual de 2026-09-22 (vela das 22h da Binance).
- Fora do escopo: `obter_mercado` (manhã) continua exigindo o CoinGecko (/coins/markets).
- Regras: BR-1 a BR-4, BR-C4, BR-C5 e BR-C6 não mudam. Fonte: `robot_bitcoin.py` @ 8de5c67.

## Owned files

- robot_bitcoin.py
- test_robot_bitcoin.py

## Business-rule gaps

## Log

- 2026-09-23: tarefa criada pelo orquestrador. Delegada ao Antigravity (agy) na worktree `../Bot_previsao_bitcoin-wt/preco-fallback`, branch `fix/preco-fallback-binance`.

- 2026-09-23: a entrega do agy (8f76970) foi aceita na primeira rodada. A revisão confirmou que os 23 testes definidos são os 23 que rodam (0,12 s) e que os testes novos falham no código anterior.

## Evidence

Artifact: .aihaus/evidence/T-260923-c8efd6.json
