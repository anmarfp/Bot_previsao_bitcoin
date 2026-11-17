---
id: T-261117-c26b66-prazo-de-240-s-por-chamada-ao-gemini-e-deploy
room: feature
created: 2026-11-17T13:00:40.000Z
---

# Goal

Prazo de 240 s por chamada ao Gemini e deploy. O Hydrogen, na fila de lançamento, leva perto de 120 s até para um prompt curto e então recebe 504; com mais prazo ele responde mais vezes. Depois, colocar no servidor o código de T-261117-11f0d5 junto com este prazo.

## Acceptance

- [ ] Given uma chamada ao Gemini demora mais de 120 s When gerar_json cria o cliente Then o prazo de cada requisição é de 240 s (TIMEOUT_GEMINI_MS = 240_000) (teste).
- [ ] `python -m py_compile robot_bitcoin.py` e `python -m unittest -v test_robot_bitcoin` passam sem rede.
- [ ] Given a aprovação do dono em 2026-11-17 When o deploy manual roda pelo runbook Then o servidor roda o robot_bitcoin.py do commit integrado na main (sha256 conferido), há backup da versão anterior, py_compile e import passam no servidor, e o sha256 do historico_bitcoin.json não muda.
- [ ] Given o código novo no servidor When roda a próxima tarefa agendada Then o log registra "✅ Mensagem entregue ao Telegram com sucesso!" sem erro novo.

## Context

- Pedido do dono (Marco), 2026-11-17: "Mude o prazo de resposta e realize o deploy". A opção de 240 s, com atraso de até ~9 min quando o Hydrogen estiver saturado, foi apresentada na mesma conversa.
- Fonte: `robot_bitcoin.py` @ 53be82b (`TIMEOUT_GEMINI_MS`, usado só em `gerar_json` via `types.HttpOptions(timeout=...)`; `ESPERA_TIMEOUT` = 180 s continua sendo a espera depois de um timeout de rede).
- Medição (T-261117-11f0d5): o Hydrogen devolveu 504 DEADLINE_EXCEEDED aos ~119 s, o que coincide com o prazo de 120 s, e respondeu 200 em 116,6 s num prompt curto.
- Custo aceito: com 240 s e FALHAS_ANTES_DE_TROCAR = 2, um modelo que esgota o prazo duas vezes atrasa a troca em até 2 × 240 + 20 + 40 = 540 s; numa falha de rede por timeout, até 2 × (240 + 180) = 840 s. Como as chamadas seguintes começam pelo último modelo que respondeu, isso acontece no máximo uma vez por execução.
- Deploy (produção; aprovação explícita do dono nesta conversa), conforme `.aihaus/memory/project/deployment.md` e ADR-001:
  - Contenção e credenciais: só `ssh oracle-bot` (chave do dono); o `.env` do servidor não é lido nem copiado; nenhuma mensagem real é enviada no pré-teste (Telegram bloqueado no processo).
  - Pré-teste: `git show <main>:robot_bitcoin.py` (LF); em /tmp/deploy-check com a .venv do servidor: py_compile, `python -m unittest test_robot_bitcoin` (o arquivo de teste vai só para /tmp) e um ensaio de `previsao_manha` sobre uma cópia do histórico, com `enviar_telegram` bloqueado.
  - Troca: script em /tmp (não usar pgrep/kill na linha do ssh), com `set -e`: abortar se `pgrep -af "[p]ython robot_bitcoin[.]py"` achar tarefa rodando; abortar se o sha256 do `.new` ou do ativo não for o esperado (ativo esperado: e1970e4fbb8a4504…, Git ab86f7e); `cp -p robot_bitcoin.py robot_bitcoin.py.bak-20261117-ab86f7e`; `mv -f robot_bitcoin.py.new robot_bitcoin.py`; py_compile e `import robot_bitcoin`; conferir que o sha256 do histórico não mudou.
  - Condições de parada: qualquer etapa com saída diferente de 0, hash inesperado ou tarefa do cron rodando.
  - Rollback: `cp -p robot_bitcoin.py.bak-20261117-ab86f7e robot_bitcoin.py` em ~/bot_bitcoin; os arquivos de estado não são tocados.
  - Smoke: a próxima execução do cron (preço a cada 2 h) registra "✅ Mensagem entregue"; a primeira execução com Gemini é a noite das 22:00.

## Owned files

- robot_bitcoin.py
- test_robot_bitcoin.py
- .aihaus/memory/kanban/ (este arquivo)
- .aihaus/evidence/T-261117-c26b66.json
- .aihaus/memory/project/knowledge.md
- .aihaus/memory/project/deployment.md

## Business-rule gaps

## Log

- 2026-11-17 10:00: tarefa criada pelo orquestrador na branch `feat/prazo-gemini-240s`.

## Evidence
