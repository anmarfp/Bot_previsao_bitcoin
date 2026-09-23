# Glossary

Meanings are taken from how the code uses each term. None of them is an owner-supplied definition.

| Term | Meaning | Source or owner |
|---|---|---|
| `manha` | Morning task: collect market data and news, then ask Gemini for a SUBIR/CAIR prediction until 22:00 Brasília time | `robot_bitcoin.py` (reviewed e0bb956) |
| `noite` | Evening task: compare the current price with `preco_8h`, score the prediction, and store an `aprendizado` | `robot_bitcoin.py` (reviewed e0bb956) |
| `preco` | Default task: two-hour price update with the change since the last notified price | `robot_bitcoin.py` (reviewed e0bb956) |
| SUBIR / CAIR | The only allowed prediction directions (up / down), enforced by `SCHEMA_PREVISAO` and `validar_previsao` | `robot_bitcoin.py` (reviewed e0bb956) |
| FICAR ESTÁVEL / SEM VARIAÇÃO | Evening outcome when the price equals the morning price; not counted in the hit rate | `robot_bitcoin.py` (reviewed e0bb956) |
| `preco_8h` | Price recorded at the morning prediction run (the actual run time depends on the schedule) | `robot_bitcoin.py` (reviewed e0bb956) |
| `aprendizado` | Gemini's self-assessment lesson, fed into the next morning prompt as "Lição de ontem" | `robot_bitcoin.py` (reviewed e0bb956) |
| Placar geral | Running hit rate: ACERTOU count over ACERTOU + ERROU count | `robot_bitcoin.py` (reviewed e0bb956) |
| BRT | Brasília time, fixed UTC-3 in the code | `robot_bitcoin.py` (reviewed e0bb956) |
