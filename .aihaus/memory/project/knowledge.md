# Knowledge

## Verified facts

- Verified: the script runs one of three tasks based on its first argument: `manha` (morning prediction), `noite` (evening evaluation), and anything else or no argument (the two-hour price update, `preco`). Source: `robot_bitcoin.py` (reviewed e0bb956).
- Verified: all times shown to users are in Brasília time, using a fixed UTC-3 offset that does not depend on the server time zone. Source: `robot_bitcoin.py` (reviewed e0bb956).
- Verified: on startup the script loads a `.env` file from the script's own directory. It does not overwrite variables already set in the environment. Source: `robot_bitcoin.py` (reviewed e0bb956).
- Verified: the state files `historico_bitcoin.json` (prediction history) and `ultimo_preco.txt` (last notified price) use paths relative to the current working directory, not to the script's directory. Source: `robot_bitcoin.py` (reviewed e0bb956).
- Verified: each history entry holds `data`, `hora_previsao`, `preco_8h` and `direcao` after the morning run. The evening run adds `preco_noite`, `resultado` and `aprendizado`. Source: `robot_bitcoin.py` (reviewed e0bb956).
- Verified: Gemini calls request JSON output (the morning call also uses `SCHEMA_PREVISAO`). Each call is attempted up to 5 times with increasing waits on HTTP 429/500/502/503/504, network transport errors, or invalid/unparseable JSON. Source: `robot_bitcoin.py` (reviewed e0bb956).
- Verified: HTTP GETs use a 20s timeout and up to 3 attempts 10s apart. Fear & Greed is attempted once and may be missing. Source: `robot_bitcoin.py` (reviewed e0bb956).
- Verified: `python -m py_compile robot_bitcoin.py` exited 0 with the local `.venv` Python 3.14.7 on 2026-09-22. This is a syntax check only. Source: `robot_bitcoin.py` (reviewed e0bb956).

## Recurring gotchas

- Verified: Telegram messages are sent with `parse_mode: HTML`. The docstring requires every variable text to pass through `esc()` first, and a literal `&` in the template must be written as `&amp;`. Source: `robot_bitcoin.py` (reviewed e0bb956).
- Verified: the script imports `httpx` directly, so `requirements.txt` must keep listing it next to `google-genai` and `requests`. Sources: `requirements.txt`, `robot_bitcoin.py` (reviewed e0bb956).
- Accepted: the history in the repository has diverged from the server's history before (June 2026). Treat the server copy as the source of truth. Owner-confirmed on 2026-09-22 from earlier session notes; not re-verified on the server in this session.

## Useful code analogs

- Verified: `gerar_json(prompt, config, validar)` is the pattern for any new Gemini call: it takes a validator that raises `ValueError` to trigger a retry. Source: `robot_bitcoin.py` (reviewed e0bb956).
- Verified: `pedir(url, tentativas)` is the pattern for tolerant HTTP GETs that return `None` on failure. Source: `robot_bitcoin.py` (reviewed e0bb956).

Each entry should name its evidence and last review date. Transient research
belongs in the task that used it, not here.
