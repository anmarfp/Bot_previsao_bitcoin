# Procedures

## Development closeout

1. Run affected checks. Verified: the repository has no automated tests or linter. The only check verified locally is `python -m py_compile robot_bitcoin.py` (a syntax check, exit 0 on 2026-09-22). Source: `robot_bitcoin.py` (reviewed e0bb956).
2. Run broader repository checks required by the Definition of Done. Unresolved: no Definition of Done is documented (see project.md).
3. Record commands, exit codes, and degraded checks.
4. Review the diff and update durable memory only when warranted.

## Operational procedures

- Verified: run a task manually from the repository root with `python robot_bitcoin.py preco`, `python robot_bitcoin.py manha` or `python robot_bitcoin.py noite`. Run it from the root because the state files are resolved from the working directory. Every task calls live external APIs, and all of them except a failed price fetch send a real Telegram message. Source: `robot_bitcoin.py` (reviewed e0bb956).
- Accepted: to update the bot, copy only `robot_bitcoin.py` to the server with `scp` and then check `logs/bot.log`. The server does not `git pull`. Owner-confirmed on 2026-09-22 from earlier session notes; not re-verified on the server in this session.
- Accepted: after changing the server time zone, restart cron with `sudo systemctl restart cron`. On 2026-09-22 this was skipped: the clock moved back 3h, cron suspended the fixed-time jobs, and the 20:00 update was missed. Owner-confirmed on 2026-09-22 from earlier session notes; not re-verified on the server in this session.
- Verified: rerunning `manha` on the same day replaces today's unevaluated prediction. Rerunning `noite` after an evaluation is a no-op. Source: `robot_bitcoin.py` (reviewed e0bb956).
- Unresolved: no documented procedure exists for editing or repairing the server's `historico_bitcoin.json` or `ultimo_preco.txt`, or for stopping the bot.

Add repeatable, verified procedures with prerequisites, rollback, and stop
conditions. Do not copy one-off terminal history here.
