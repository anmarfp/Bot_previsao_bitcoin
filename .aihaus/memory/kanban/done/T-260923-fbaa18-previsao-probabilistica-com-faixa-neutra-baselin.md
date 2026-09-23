---
id: T-260923-fbaa18-previsao-probabilistica-com-faixa-neutra-baselin
room: feature
created: 2026-09-23T01:03:18.586Z
---

# Goal

Previsão probabilística com faixa neutra, baselines e indicadores. O objetivo é tornar a qualidade das previsões mensurável e dar ao Gemini dados melhores: probabilidade com aviso de "sem convicção", faixa neutra de 0,3% na avaliação, comparação com baselines, Brier score, indicadores técnicos e de derivativos calculados em Python, e um histórico recente no prompt.

## Acceptance

- [x] Faixa neutra: Given preço da manhã e da noite When |variação| < 0,3% Then resultado "⚪ SEM VARIAÇÃO" e fora do placar; |variação| >= 0,3% conta como SUBIR/CAIR (teste unitário).
- [x] Probabilidade: o schema exige `probabilidade_subir` inteiro 0–100 coerente com a direção (>50 exige SUBIR, <50 exige CAIR, 50 aceita ambas); resposta incoerente ou fora do intervalo gera nova tentativa (teste unitário).
- [x] Amostragem: a manhã pede 3 amostras ao Gemini, usa a média das probabilidades, direção SUBIR se média > 50, CAIR se < 50 e, no empate, a maioria das amostras (persistindo o empate, a primeira); segue se pelo menos 1 amostra for válida e falha se nenhuma for (teste unitário com Gemini simulado).
- [x] Sem convicção: Given probabilidade final entre 45 e 55 inclusive When a mensagem da manhã é montada Then mostra a direção, a probabilidade dessa direção e o aviso "sem convicção"; a previsão continua contando no placar (teste unitário).
- [x] Mensagem da manhã mostra a probabilidade da direção prevista (ex.: "CAIR (62%)") (teste unitário).
- [x] Histórico: a nova entrada guarda probabilidade_subir, sem_conviccao, justificativa, baselines e um resumo dos indicadores; entradas antigas sem esses campos continuam lidas, avaliadas e contadas sem erro (teste unitário com o histórico atual do servidor).
- [x] Noite: salva variacao_pct, brier (só fora da faixa neutra) e o resultado de cada baseline; o prompt do aprendizado recebe justificativa, probabilidade e variação real; a mensagem mostra o placar do Gemini, o Brier médio e o placar das baselines nos mesmos dias (teste unitário).
- [x] Manhã: o prompt inclui indicadores de velas horárias (retornos 1/4/8/24/72h, RSI14, volatilidade 24h, posição na faixa 24h), derivativos (funding, variação do open interest 24h, long/short) e as últimas 10 previsões avaliadas; se velas ou derivativos falharem, a previsão segue com "n/d" (teste unitário).
- [x] `python -m py_compile robot_bitcoin.py` e `python -m unittest -v test_robot_bitcoin` passam sem rede nem Telegram; requirements.txt sem dependências novas.

## Context

- Decisões do dono (Marco, 2026-09-22, conversa): faixa neutra de 0,3%; quando sem convicção, avisar a falta de certeza mas ainda dizer SUBIR ou CAIR; mostrar a probabilidade.
- Regras afetadas: BR-C1 (avaliação) e BR-C2 (placar) em `.aihaus/memory/project/business-rules.md`. BR-C3 a BR-C6 ficam como estão.
- Evidência de pesquisa (backtest com velas horárias da Binance, 1.092 dias, 08h→22h BRT, até 2026-09-22): sempre SUBIR 52,0%; momentum 8h 52,4%; momentum 24h 49,5%; funding abaixo da mediana 52,7% (IC95 ±3pp). 19,4% dos dias variam menos de 0,3%.
- Produção em 2026-09-22 (leitura do servidor): 4 entradas e 2 avaliadas; o formato é o de `historico_bitcoin.json` na raiz mais uma entrada com `hora_previsao`.
- Endpoints verificados (HTTP 200) do PC e do servidor em 2026-09-22: `data-api.binance.vision/api/v3/klines`, `fapi.binance.com/fapi/v1/premiumIndex`, `fapi.binance.com/futures/data/openInterestHist`, `fapi.binance.com/futures/data/globalLongShortAccountRatio`.
- Servidor com Python 3.14.4; somente biblioteca padrão, sem numpy.
- Fonte: `robot_bitcoin.py` @ 5c122e1.

## Owned files

- robot_bitcoin.py
- test_robot_bitcoin.py (novo)

## Business-rule gaps

### Q-03ba78

Question: Como avaliar variações pequenas entre manhã e noite?

Answer: Faixa neutra de 0,3% (Marco, 2026-09-22)

Draft rule: Given preços da manhã e da noite When |variação| < 0,3% Then resultado SEM VARIAÇÃO, fora do placar

### Q-cae293

Question: O que fazer quando o modelo está sem convicção?

Answer: Avisar a falta de certeza, mas ainda dizer SUBIR ou CAIR, e mostrar a probabilidade (Marco, 2026-09-22)

Draft rule: Given probabilidade final entre 45% e 55% When a previsão da manhã é enviada Then mostra direção, probabilidade e aviso de sem convicção, e a previsão conta no placar

### Q-7442d8

Question: A mensagem da manhã mostra a probabilidade?

Answer: Sim (Marco, 2026-09-22)

Draft rule: Given uma previsão da manhã When a mensagem é enviada Then mostra a probabilidade da direção prevista

## Log

- 2026-09-22: tarefa criada pelo orquestrador. Implementação delegada ao Antigravity (agy) na worktree `../Bot_previsao_bitcoin-wt/probabilistica`, branch `feat/previsao-probabilistica`.
- 2026-09-22/23: rodada 1 do agy (5cd9dc4) rejeitada: histórico do prompt incompleto, âncora "60" no exemplo, comentário BR-C3 removido, testes faltando. Rodada 2 (91970f5) corrigiu. O orquestrador acrescentou o teste do Brier médio e corrigiu a formatação do funding (4 casas; antes aparecia +0.00%) e da volatilidade, achadas na execução com dados reais.
- Revisão adversarial independente: ship-with-changes. Achados médios: desempate pela média arredondada, placar das baselines em dias diferentes do Gemini, vela horária em curso usada como fecho. Achados baixos: 0,3% exato por ponto flutuante, int() truncando, formato da variação. A rodada 3 do agy (8ec44ac) corrigiu; o orquestrador corrigiu o formato da variação e o nome de variável e colocou dentro da classe um teste que tinha ficado após o `if __name__` e nunca rodava. Commit final: 5e3ba4a.
- Fora do escopo: preco_8h = 0 gera ZeroDivision na noite (comportamento que já existia; irrealista).
- Próximo: deploy manual no servidor somente com aprovação do dono (deployment.md).

## Evidence

Artifact: .aihaus/evidence/T-260923-fbaa18.json
