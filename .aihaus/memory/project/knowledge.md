# Knowledge

## Verified facts

- Verified: the script runs one of three tasks based on its first argument: `manha` (morning prediction), `noite` (evening evaluation), and anything else or no argument (the two-hour price update, `preco`). Source: `robot_bitcoin.py` (reviewed e0bb956).
- Verified: all times shown to users are in Brasília time, using a fixed UTC-3 offset that does not depend on the server time zone. Source: `robot_bitcoin.py` (reviewed e0bb956).
- Verified: on startup the script loads a `.env` file from the script's own directory. It does not overwrite variables already set in the environment. Source: `robot_bitcoin.py` (reviewed e0bb956).
- Verified: the state files `historico_bitcoin.json` (prediction history) and `ultimo_preco.txt` (last notified price) use paths relative to the current working directory, not to the script's directory. Source: `robot_bitcoin.py` (reviewed e0bb956).
- Verified: each history entry holds `data`, `hora_previsao`, `preco_8h` and `direcao` after the morning run. The evening run adds `preco_noite`, `resultado` and `aprendizado`. Source: `robot_bitcoin.py` (reviewed e0bb956).
- Verified: Gemini calls request JSON output (the morning call also uses `SCHEMA_PREVISAO`). Each call is attempted up to 5 times with increasing waits on HTTP 429/500/502/503/504, network transport errors, or invalid/unparseable JSON. Source: `robot_bitcoin.py` (reviewed e0bb956).
- Verified: HTTP GETs use a 20s timeout and up to 3 attempts 10s apart. Fear & Greed is attempted once and may be missing. Source: `robot_bitcoin.py` (reviewed e0bb956).
- Verified: the morning task asks Gemini for 3 independent samples and aggregates them in `agregar_amostras`. The direction comes from the unrounded mean of `probabilidade_subir` (a tie at exactly 50 goes to the majority, then to the first sample); only valid samples count; it fails only if all 3 fail. Source: `robot_bitcoin.py` (reviewed 5e3ba4a).
- Verified: the morning prompt adds indicators computed from CLOSED hourly Binance candles (`data-api.binance.vision` klines; the candle still in progress is discarded by `close_time`), futures data from `fapi.binance.com` (funding, 24h open-interest change, long/short ratio), and the last 10 evaluated predictions. Each source is optional and shows "n/d" on failure. On 2026-09-22 all four endpoints returned HTTP 200 from the dev PC and from the server. Source: `robot_bitcoin.py` (reviewed 5e3ba4a).
- Verified: new history entries also store `probabilidade_subir`, `sem_conviccao`, `justificativa`, `baselines` (`sempre_subir`, `momentum_8h`) and `indicadores`; the evening adds `variacao_pct`, `brier` (non-neutral days only) and `resultados_baselines`. Old entries without these fields still work. Source: `robot_bitcoin.py` (reviewed 5e3ba4a).
- Historical: `python -m py_compile robot_bitcoin.py` exited 0 with the local `.venv` Python 3.14.7 on 2026-09-22. This is a syntax check only. Source: `robot_bitcoin.py` (reviewed e0bb956).

## Recurring gotchas

- Verified: a 3-year backtest (1,092 days, 08h→22h Brasília, Binance hourly candles, up to 2026-09-22) found no simple rule clearly above 50%: always SUBIR 52.0%, 8h momentum 52.4%, 24h momentum 49.5%, funding below median 52.7% (95% CI ±3pp). 19.4% of days move less than 0.3%. The average absolute move is 1.41%, so a 0.1%-per-side fee needs about 57% accuracy to break even; 8h momentum traded daily with that fee lost 75%. Source: orchestrator analysis on 2026-09-22 (script not versioned; `backtest.py` will reproduce it).
- Verified: floating point can put an exact 0.3% move under the band; `classificar_movimento` rounds the move to 10 decimal places before comparing. Source: `robot_bitcoin.py` (reviewed 5e3ba4a).

- Verified: Telegram messages are sent with `parse_mode: HTML`. The docstring requires every variable text to pass through `esc()` first, and a literal `&` in the template must be written as `&amp;`. Source: `robot_bitcoin.py` (reviewed e0bb956).
- Verified: the script imports `httpx` directly, so `requirements.txt` must keep listing it next to `google-genai` and `requests`. Sources: `requirements.txt`, `robot_bitcoin.py` (reviewed e0bb956).
- Accepted: the history in the repository has diverged from the server's history before (June 2026). Treat the server copy as the source of truth. Owner-confirmed on 2026-09-22 from earlier session notes; not re-verified on the server in this session.

## Useful code analogs

- Verified: `gerar_json(prompt, config, validar)` is the pattern for any new Gemini call: it takes a validator that raises `ValueError` to trigger a retry. Source: `robot_bitcoin.py` (reviewed e0bb956).
- Verified: `pedir(url, tentativas)` is the pattern for tolerant HTTP GETs that return `None` on failure. Source: `robot_bitcoin.py` (reviewed e0bb956).

Each entry should name its evidence and last review date. Transient research
belongs in the task that used it, not here.
