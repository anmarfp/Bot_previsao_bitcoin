# Business rules

Markdown is authoritative; indexes only retrieve it.

## Accepted rules

- Historical: until e0bb956 no owner-accepted business rule was documented; the behaviors in "Inferred candidates" were implemented but not accepted.
- Accepted BR-1 (scoring with a neutral band, supersedes BR-C1): Given the morning price `preco_8h` When the evening price moves less than 0.3% in either direction Then the outcome is "FICAR ESTÁVEL" / "⚪ SEM VARIAÇÃO"; a move of 0.3% or more is SUBIR or CAIR and scores "✅ ACERTOU" or "❌ ERROU". The same band scores the baselines. Owner decision: Marco, stated in conversation on 2026-09-22 (task T-260923-fbaa18). Source: `robot_bitcoin.py` (reviewed 5e3ba4a).
- Accepted BR-2 (hit rate, supersedes BR-C2): Given the history When the scoreboard is shown Then only ACERTOU/ERROU entries count and neutral days are excluded. The comparison of Gemini against the baselines and the average Brier score uses only the same days (entries that have `resultados_baselines`). Owner decision: Marco, stated in conversation on 2026-09-22 (task T-260923-fbaa18). Source: `robot_bitcoin.py` (reviewed 5e3ba4a).
- Accepted BR-3 (no conviction): Given the final probability of rising is between 45% and 55% inclusive When the morning prediction is sent Then it still states SUBIR or CAIR, shows the probability and the "sem convicção" warning, and it counts in the scoreboard. Owner decision: Marco, stated in conversation on 2026-09-22 (task T-260923-fbaa18). Source: `robot_bitcoin.py` (reviewed 5e3ba4a).
- Accepted BR-4 (probability shown): Given a morning prediction When the message is sent Then it shows the probability of the predicted direction, e.g. "CAIR (62% de probabilidade)". Owner decision: Marco, stated in conversation on 2026-09-22 (task T-260923-fbaa18). Source: `robot_bitcoin.py` (reviewed 5e3ba4a).

## Conflicts and gaps

Record unresolved gaps here; an owner's answer becomes a rule.

### Inferred candidates (implemented, not accepted)

- Superseded by BR-1 — inferred candidate BR-C1 (scoring): Given the morning price stored as `preco_8h` When the evening price is higher, lower, or equal Then the real outcome is SUBIR, CAIR, or "FICAR ESTÁVEL", and the result is "✅ ACERTOU", "❌ ERROU", or "⚪ SEM VARIAÇÃO". Source: `robot_bitcoin.py` (reviewed e0bb956).
- Superseded by BR-2 — inferred candidate BR-C2 (hit rate): Given the history When the hit rate is calculated Then only ACERTOU/ERROU entries count, and SEM VARIAÇÃO and unevaluated entries are excluded. Source: `robot_bitcoin.py` (reviewed e0bb956).
- Inferred candidate BR-C3 (one prediction per day): Given today's prediction exists and has not been evaluated When the morning task runs again Then the new prediction replaces it instead of adding a second entry. Source: `robot_bitcoin.py` (reviewed e0bb956).
- Inferred candidate BR-C4 (evaluation window): Given the latest history entry When the evening task runs Then it evaluates a prediction from today or yesterday, fails if the latest entry is older, and does nothing if the entry is already evaluated. Source: `robot_bitcoin.py` (reviewed e0bb956).
- Inferred candidate BR-C5 (price update): Given a previously stored price When the two-hour task runs Then it reports the percentage change and previous price. If the price fetch fails it sends nothing and does not alert. Source: `robot_bitcoin.py` (reviewed e0bb956).
- Inferred candidate BR-C6 (failure alert): Given any task raises an exception When the script exits Then a Telegram failure alert is sent and the process exits non-zero. Source: `robot_bitcoin.py` (reviewed e0bb956).

### Gaps

- Gap: `historico_bitcoin.json` contains two entries dated 2026-06-16, and the first one was never evaluated. It is unknown whether an owner considers duplicate or unevaluated days acceptable. Source: `historico_bitcoin.json` (reviewed e0bb956).
