---
id: T-260924-490102-gemini-sem-cota-trocar-de-modelo-em-vez-de-esper
room: bugfix
created: 2026-09-24T14:10:50.685Z
---

# Goal

Gemini sem cota: trocar de modelo em vez de esperar. Quando o modelo esgota a cota diária do plano gratuito ou fica sobrecarregado, gerar_json passa para o próximo modelo de uma lista, em vez de gastar a cota do mesmo modelo esperando.

## Acceptance

- [x] Given o modelo atual responde 429 de cota DIÁRIA (quotaId com "PerDay") When gerar_json é chamado Then o modelo é marcado como esgotado para o resto do processo e a próxima tentativa usa o próximo modelo da lista imediatamente, sem espera; chamadas seguintes no mesmo processo (as outras amostras e a noite) já começam pelo primeiro modelo não esgotado (teste de regressão que falha no código anterior).
- [x] Given o modelo atual falha com erro temporário (429 por minuto, 5xx, rede ou timeout) FALHAS_ANTES_DE_TROCAR vezes seguidas When gerar_json continua tentando Then passa para o próximo modelo, mantendo a espera crescente limitada a ESPERA_MAXIMA (e ESPERA_TIMEOUT após timeout), e percorre a lista em ciclo, sem limite de tentativas (teste).
- [x] Given todos os modelos estão com a cota diária esgotada When gerar_json continua tentando Then espera ESPERA_COTA, limpa a marcação e recomeça pelo primeiro modelo, sem desistir (teste).
- [x] A lista vem de GEMINI_MODELOS (separada por vírgula) ou, por padrão, [GEMINI_MODEL ou gemini-3.8-flash, gemini-3.7-flash, gemini-3.6-flash, gemini-3.5-flash], sem repetições; a entrada da manhã guarda "modelos" (o modelo de cada amostra válida) e o log registra o modelo em cada falha e na troca (teste).
- [x] A saída do bot é gravada linha a linha no log (stdout com line_buffering no início da execução), para o log mostrar as tentativas enquanto a tarefa ainda roda.
- [x] `python -m py_compile robot_bitcoin.py` e `python -m unittest -v test_robot_bitcoin` passam sem rede e sem esperas reais; requirements.txt sem dependências novas.

## Context

- Falha em produção em 2026-09-24: a `manha` das 08:00 ainda estava rodando às 11:07 (PID 22524, dormindo entre tentativas) e não publicou a previsão. O log estava mudo porque o stdout era redirecionado para arquivo com buffer.
- Diagnóstico (uma chamada, às 11:08): 429 RESOURCE_EXHAUSTED, quotaId `GenerateRequestsPerDayPerProjectPerModel-FreeTier`, quotaValue 20, model gemini-3.8-flash. A cota é por modelo.
- As respostas 503 também consomem a cota. Em 2026-09-23 a manhã fez 17 requisições (12 com 503) e a noite recebeu o primeiro 429 na 5ª tentativa (17 + 4 = 21). Sem retry_options, a biblioteca não repete as chamadas: cada "Tentativa N" do log é uma requisição.
- Modelos testados às 11:1x com uma chamada cada: gemini-3.7-flash respondeu 503; gemini-3.6-flash e gemini-3.5-flash responderam OK. `models.list()` também mostra 2.5-flash, 3.5-flash-lite, 3.1-flash-lite e outros.
- Regra do dono (2026-09-22): "tentar novamente e só parar quando conseguir êxito". Trocar de modelo cumpre essa regra sem queimar a cota de um só modelo. As regras de negócio BR-1 a BR-4 não mudam.
- A cota do plano gratuito zera à meia-noite do horário do Pacífico (cerca de 04:00 BRT).
- Fonte: `robot_bitcoin.py` @ 9c509ca.

## Owned files

- robot_bitcoin.py
- test_robot_bitcoin.py

## Business-rule gaps

## Log

- 2026-09-24: tarefa criada pelo orquestrador. Delegada ao Antigravity (agy) na worktree `../Bot_previsao_bitcoin-wt/modelos`, branch `fix/gemini-trocar-modelo`.

- 2026-09-24: a entrega do agy (cbc1328) foi revisada e aceita com os ajustes do orquestrador (a detecção de 'PerDay' restrita ao 429, o tratamento do 404, comentários restaurados, novo teste). Commit final: 76250d9. 27 testes.

## Evidence

Artifact: .aihaus/evidence/T-260924-490102.json
