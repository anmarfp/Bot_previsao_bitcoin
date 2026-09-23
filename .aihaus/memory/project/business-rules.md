# Business rules

Markdown is authoritative; indexes only retrieve it.

## Accepted rules

- Verified: no owner-accepted business rule is documented in the repository. The behaviors below are implemented in code but have not been accepted by an owner, so they are recorded only as candidates. Source: `robot_bitcoin.py` (reviewed e0bb956).

## Conflicts and gaps

Record unresolved gaps here; an owner's answer becomes a rule.

### Inferred candidates (implemented, not accepted)

- Inferred candidate BR-C1 (scoring): Given the morning price stored as `preco_8h` When the evening price is higher, lower, or equal Then the real outcome is SUBIR, CAIR, or "FICAR ESTÁVEL", and the result is "✅ ACERTOU", "❌ ERROU", or "⚪ SEM VARIAÇÃO". Source: `robot_bitcoin.py` (reviewed e0bb956).
- Inferred candidate BR-C2 (hit rate): Given the history When the hit rate is calculated Then only ACERTOU/ERROU entries count, and SEM VARIAÇÃO and unevaluated entries are excluded. Source: `robot_bitcoin.py` (reviewed e0bb956).
- Inferred candidate BR-C3 (one prediction per day): Given today's prediction exists and has not been evaluated When the morning task runs again Then the new prediction replaces it instead of adding a second entry. Source: `robot_bitcoin.py` (reviewed e0bb956).
- Inferred candidate BR-C4 (evaluation window): Given the latest history entry When the evening task runs Then it evaluates a prediction from today or yesterday, fails if the latest entry is older, and does nothing if the entry is already evaluated. Source: `robot_bitcoin.py` (reviewed e0bb956).
- Inferred candidate BR-C5 (price update): Given a previously stored price When the two-hour task runs Then it reports the percentage change and previous price. If the price fetch fails it sends nothing and does not alert. Source: `robot_bitcoin.py` (reviewed e0bb956).
- Inferred candidate BR-C6 (failure alert): Given any task raises an exception When the script exits Then a Telegram failure alert is sent and the process exits non-zero. Source: `robot_bitcoin.py` (reviewed e0bb956).

### Gaps

- Gap: `historico_bitcoin.json` contains two entries dated 2026-06-16, and the first one was never evaluated. It is unknown whether an owner considers duplicate or unevaluated days acceptable. Source: `historico_bitcoin.json` (reviewed e0bb956).
