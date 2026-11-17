---
id: T-261117-11f0d5-gemini-4-hydrogen-como-modelo-principal-e-lista-
room: feature
created: 2026-11-17T12:42:17.853Z
---

# Goal

Gemini 4 Hydrogen como modelo principal e lista de modelos atualizada. O dono pediu, em 2026-11-17, para modernizar o agente com os modelos novos do Gemini. O bot deve usar o modelo mais novo disponível no plano gratuito, sem perder tempo nem cota repetindo a cada amostra um modelo sobrecarregado.

## Acceptance

- [ ] Given GEMINI_MODEL e GEMINI_MODELOS não estão definidos When a lista é montada Then ela é [gemini-4-hydrogen, gemini-2.5-flash, gemini-3.6-flash, gemini-3.8-flash, gemini-3.1-flash-lite, gemini-3-flash-preview, gemini-3.5-flash-lite], sem o gemini-3.7-flash e o gemini-3.5-flash, que a API já redireciona para o 3.8 e o 3.6 (teste).
- [ ] Given um modelo falhou FALHAS_ANTES_DE_TROCAR vezes seguidas com erro temporário e o seguinte respondeu When gerar_json é chamado de novo no mesmo processo (as outras amostras da manhã) Then a nova chamada começa pelo modelo que respondeu, sem repetir o sobrecarregado; a cota diária e o 404 continuam como antes (teste de regressão que falha no código anterior).
- [ ] Given a chave do bot no servidor When a API lista os modelos e o prompt real da manhã é enviado com o SCHEMA_PREVISAO (sem gravar o histórico nem enviar ao Telegram) Then o gemini-4-hydrogen e todos os modelos da lista padrão aparecem com generateContent, e pelo menos um modelo de reserva devolve um JSON aceito por validar_previsao.
- [ ] `python -m py_compile robot_bitcoin.py` e `python -m unittest -v test_robot_bitcoin` passam sem rede.

## Context

- Pedido do dono (Marco), 2026-11-17: "Saíram novos modelos do gemini, verifique se você consegue atualizar o bot para modernizar o agente".
- Fonte: `robot_bitcoin.py` @ bdc18a2 (`MODELO_GEMINI`, `MODELOS_PADRAO`, `gerar_json`). Não há regra de negócio aceita sobre a ordem dos modelos; a lista foi tratada como mecânica técnica em T-260924-5eca01 e T-260924-490102. Conhecimento relacionado: `.aihaus/memory/project/knowledge.md` (entradas sobre `gerar_json` e a cota de 20 requisições por dia por modelo).
- Produção (somente leitura, `ssh oracle-bot`, 2026-11-17): GEMINI_MODEL e GEMINI_MODELOS não estão definidos no servidor, então vale a lista padrão. Desde 2026-09-22, 726 execuções no log. Todas as manhãs e noites de novembro, o gemini-3.8-flash respondeu 503/504 duas vezes em CADA amostra antes de o bot trocar para o gemini-2.5-flash. Amostras no histórico: 2.5-flash 102, 3.8-flash 49, 3-flash-preview 9, 3.5-flash 1, 3.6-flash 1; em novembro, 38 de 51 vieram do 2.5-flash.
- `models.list` com a chave do bot (2026-11-17 09:30 BRT): aparecem gemini-4-hydrogen, gemini-4-argon, gemini-4-carbon, gemini-3.1-flash-lite, além dos modelos já usados. SDK no servidor: google-genai 2.25.0 (tem `thinking_level`).
- Documentação oficial (aistudio.google.com/docs: models, pricing, deprecations, whats-new-gemini-4-hydrogen; lida em 2026-11-17): o Hydrogen (GA em 2026-11-12) é o sucessor indicado do 3.8-flash e o único Gemini 4 com plano gratuito; o Argon e o Carbon não têm plano gratuito. O gemini-2.5-flash foi descontinuado: a partir de 2026-12-01 as chamadas a ele vão para o gemini-3.5-flash-lite. O 3.7-flash já vai para o 3.8-flash, e o 3.5-flash vai para o 3.6-flash. O Hydrogen ignora temperature, recusa thinking_budget (400) e usa thinking_level, que por padrão é HIGH. O bot não envia nenhum desses parâmetros.
- Teste no servidor com o prompt real da manhã (17,6 mil caracteres) e o SCHEMA_PREVISAO, 09:34–09:45 BRT: gemini-4-hydrogen falhou nas 5 tentativas, com 504 DEADLINE_EXCEEDED aos 119 s (thinking padrão e LOW) e 503. O gemini-3.8-flash e o gemini-3.5-flash-lite deram 503. O gemini-3.6-flash respondeu em 52 s e o gemini-3.1-flash-lite em 3 s, ambos com JSON válido. O histórico de produção não mudou (sha256 conferido).
- Decisão técnica: o Hydrogen vira o principal, porque é o modelo novo e a sobrecarga de lançamento deve passar. Para isso não custar 3 vezes por manhã, o modelo que respondeu passa a ser o primeiro das chamadas seguintes no mesmo processo. A ordem das reservas alterna famílias e prioriza os modelos que responderam (2.5-flash até 2026-12-01, depois redirecionado; 3.6-flash; 3.1-flash-lite). A configuração das chamadas não muda: thinking_level não é enviado, porque o 2.5-flash não o aceita.
- Fora do escopo: atualizar o SDK (a chamada chegou ao modelo com 2.25.0), o aviso de AFC no log e a perda de mensagens quando o Telegram corta a conexão (tarefa própria no backlog).

## Owned files

- robot_bitcoin.py
- test_robot_bitcoin.py
- .aihaus/memory/kanban/ (este arquivo)
- .aihaus/evidence/T-261117-11f0d5.json
- .aihaus/memory/project/knowledge.md

## Business-rule gaps

## Log

- 2026-11-17: tarefa criada pelo orquestrador na branch `feat/gemini-4-hydrogen` (worktree principal), depois do diagnóstico de produção em modo leitura e dos testes de modelo descritos em Context.

## Evidence
