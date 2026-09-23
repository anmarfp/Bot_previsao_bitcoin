---
id: T-260923-1a9727-backtest-offline-com-operacao-simulada
room: feature
created: 2026-09-23T01:32:14.000Z
---

# Goal

Backtest offline com operação simulada. `backtest.py` mede, sem Telegram e sem Gemini, o acerto e o resultado de operar com base nas regras do bot e no histórico real de previsões. Serve para decidir quando ligar a compra e venda automática.

## Acceptance

- [x] Modo mercado: `python backtest.py mercado [--dias N]` baixa velas horárias BTCUSDT paginadas, simula a janela 11:00 UTC → 01:00 UTC do dia seguinte e, usando calcular_indicadores, calcular_baselines e classificar_movimento do bot, imprime o total de dias, a % de dias neutros, a % de altas e o acerto com n e IC95 de cada regra (baselines e regras de indicador), sem contar dias neutros nem dias sem sinal (testes com velas sintéticas).
- [x] Modo historico: `python backtest.py historico CAMINHO.json` mostra o placar do Gemini com IC95, o Brier médio comparado a 0,25, o acerto por faixa de confiança (50-55, 55-65, 65+ e n/d) e o placar das baselines nos mesmos dias; entradas antigas sem campos novos não quebram (testes).
- [x] Operação simulada: nos dois modos, cada regra (e o Gemini no modo historico) é simulada operando comprado em SUBIR e vendido em CAIR, com o retorno real menos 2 × taxa (`--taxa`, padrão 0,1% por lado), e são mostrados o retorno médio, o acumulado composto, o max drawdown e o acerto de equilíbrio; no modo historico também operando só com probabilidade da direção >= 55% (testes com números conhecidos).
- [x] `python -m py_compile backtest.py` e `python -m unittest -v test_backtest test_robot_bitcoin` passam sem rede; `python backtest.py mercado --dias 365` roda com a rede pública da Binance e sai com código 0; requirements.txt sem dependências novas.

## Context

- Objetivo do dono (Marco, 2026-09-22, conversa): esta é a fase de preparação; depois, o Gemini vai operar compra e venda automaticamente com base na previsão.
- Análise prévia do orquestrador (2026-09-22, 1.092 dias): nenhuma regra simples passa claramente de 50%. Com 0,1% por lado, o acerto de equilíbrio é cerca de 57%, e o momentum de 8h operado todo dia perdeu 75% (knowledge.md).
- Reutilizar as funções do bot (BR-1, faixa neutra) em vez de reimplementá-las. Fonte: `robot_bitcoin.py` @ b0f3625.
- Nenhuma ação de produção: só leitura de APIs públicas.

## Owned files

- backtest.py (novo)
- test_backtest.py (novo)

## Business-rule gaps

## Log

- 2026-09-23: tarefa criada pelo orquestrador. Delegada ao Antigravity (agy) na worktree `../Bot_previsao_bitcoin-wt/backtest`, branch `feat/backtest`.

- 2026-09-23: rodada 1 do agy (364c6bb) rejeitada. Problemas: modo historico comparando Gemini e baselines em dias diferentes (BR-2), paginação que falhava em silêncio, modo mercado saindo com código 0 sem velas, só 4 testes. A rodada 2 foi interrompida pelo sistema por falta de memória, sem WIP. A rodada 3 (70c2319) corrigiu tudo. Rebaseada sobre main (a314db6) como 15f3a71; 23 testes OK.
- Resultado com 3 anos (1.097 dias): nenhuma regra simples passa de 53% e todas perdem de 31% a 95% operando com 0,1% por lado. Acerto de equilíbrio de cerca de 57%.

## Evidence

Artifact: .aihaus/evidence/T-260923-1a9727.json
