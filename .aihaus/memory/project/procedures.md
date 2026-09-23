# Procedures

## Development closeout

1. Run affected checks. Verified: `python -m py_compile robot_bitcoin.py` and `python -m unittest -v test_robot_bitcoin` (13 tests with no network or Telegram, about 0.1 s) both exited 0 on 2026-09-23. In a worktree without its own `.venv`, use the main checkout's interpreter `C:/Users/Marco/Documents/Bot_previsao_bitcoin/.venv/Scripts/python.exe`. There is no linter. Source: `test_robot_bitcoin.py` (reviewed 5e3ba4a).
2. Run broader repository checks required by the Definition of Done. Unresolved: no Definition of Done is documented (see project.md).
3. Record commands, exit codes, and degraded checks.
4. Review the diff and update durable memory only when warranted.

## Operational procedures

- Verified: run a task manually from the repository root with `python robot_bitcoin.py preco`, `python robot_bitcoin.py manha` or `python robot_bitcoin.py noite`. Run it from the root because the state files are resolved from the working directory. Every task calls live external APIs, and all of them except a failed price fetch send a real Telegram message. Source: `robot_bitcoin.py` (reviewed e0bb956).
- Accepted: to update the bot, copy only `robot_bitcoin.py` to the server with `scp` and then check `logs/bot.log`. The server does not `git pull`. Owner-confirmed on 2026-09-22 from earlier session notes; not re-verified on the server in this session.
- Accepted: after changing the server time zone, restart cron with `sudo systemctl restart cron`. On 2026-09-22 this was skipped: the clock moved back 3h, cron suspended the fixed-time jobs, and the 20:00 update was missed. Owner-confirmed on 2026-09-22 from earlier session notes; not re-verified on the server in this session.
- Verified: rerunning `manha` on the same day replaces today's unevaluated prediction. Rerunning `noite` after an evaluation is a no-op. Source: `robot_bitcoin.py` (reviewed e0bb956).
- Verified: to measure prediction quality offline (no Telegram, no Gemini), run `python backtest.py mercado [--dias N] [--taxa 0.1]` (public Binance candles, about 30 s for 3 years) or `python backtest.py historico CAMINHO.json` on a copy of the server history, which you can read without changing anything using `ssh oracle-bot 'cat ~/bot_bitcoin/historico_bitcoin.json' > copia.json`. The "MESMOS DIAS" section is the fair comparison between Gemini and the baselines. Both modes exit with 0, or with 1 on error. Source: `backtest.py` (reviewed 15f3a71).
- Unresolved: no documented procedure exists for editing or repairing the server's `historico_bitcoin.json` or `ultimo_preco.txt`, or for stopping the bot.

Add repeatable, verified procedures with prerequisites, rollback, and stop
conditions. Do not copy one-off terminal history here.
