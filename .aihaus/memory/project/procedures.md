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
- Open (2026-09-23): the 2026-09-22 prediction has no evaluation on the server (the 22:00 run failed with 503 before saving). Recovering it would edit the production history, for example with the 22:00 BRT Binance candle, and needs the owner's approval.
- Open (2026-09-23): if CoinGecko is unavailable at 22:00, `noite` still fails after 3 `pedir()` attempts. Retrying for hours would change the evaluated price. A fallback such as the Binance 22:00 candle needs an owner decision.

## Orchestration runbook (verified 2026-09-22/23)

- Integration branch is `main` on `anmarfp/Bot_previsao_bitcoin`. Worktrees go in `../Bot_previsao_bitcoin-wt/<name>`. The flow is: task committed on main → worktree/branch → one implementation commit → the orchestrator's bookkeeping commit (evidence, task moved to done, memory) on the same branch → `gh pr create` + `gh pr merge --merge` → `git merge --ff-only origin/main` → remove the worktree, the local branch and the remote branch. There is no CI and nothing runs after merge. Merging does not deploy (see deployment.md).
- Worktrees have no `.venv`. Use `C:/Users/Marco/Documents/Bot_previsao_bitcoin/.venv/Scripts/python.exe`. Git does not track empty kanban folders, so run `mkdir -p .aihaus/memory/kanban/{backlog,todo,doing,review,done}` in a new worktree before `task.mjs move`.
- `task.mjs move` appends to the end of the file. Put log lines under `## Log`, not after `## Evidence`. Store evidence as `.aihaus/evidence/<task-id-prefix>.json` and check it with `node .aihaus/tools/evidence-validate.mjs`.
- `scope-check.mjs` only sees uncommitted changes, so run it before `git commit --amend`.
- "Antigravity" subagents are the Google `agy` CLI: `agy -p "<briefing>" --model gemini-3.1-pro-high --effort high --dangerously-skip-permissions --output-format json` run inside the worktree in the background. For corrections, continue with `--conversation <id>` (the id comes from the JSON output). A round takes about 5–50 minutes. Monitor it through `git status/log` in the worktree and `tasklist | grep agy`. One `agy` process started by the owner may already be running; leave it alone.
- Observed `agy` failure modes, so always recheck: tests written after `if __name__ == '__main__':` never run (compare the `def test_` count with "Ran N tests"); tests that call real CoinGecko/RSS because `obter_mercado`/`obter_noticias` were not patched (a suite much slower than about 0.1 s is the sign); claims that tests passed without running them; a prompt example value (`60`) that anchors the model; dropped comments. Put those checks in the briefing and still verify them independently. Also run the regression test against the previous commit.
- For consequential changes, an independent read-only reviewer (Claude general-purpose + `contracts/adversarial-review.md`) found real defects that the author and the orchestrator missed: tie-break on a rounded mean, scoreboards on different day sets, a still-open hourly candle.
- Live dry-run pattern: import `robot_bitcoin` from a scratch directory that holds a copy of the history, patch `gerar_json` and `enviar_telegram`, and run `previsao_manha()`. It exercises every real data source without sending anything or spending Gemini quota.

Add repeatable, verified procedures with prerequisites, rollback, and stop
conditions. Do not copy one-off terminal history here.
