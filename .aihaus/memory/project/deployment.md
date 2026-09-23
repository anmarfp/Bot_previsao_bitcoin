# Deployment

## Environments

- Accepted: the production target is the Oracle Cloud server, reached with `ssh oracle-bot` using the key in the owner's `.ssh` folder (ADR-001). Owner decision: Marco, stated in conversation on 2026-09-22.
- Accepted: pushing to the repository does not deploy. The server does not run `git pull`, and the GitHub Actions workflows were removed (ADR-001). Owner-confirmed on 2026-09-22 from earlier session notes; not re-verified on the server in this session.

## Preconditions

- Accepted: you need SSH access through the `oracle-bot` alias. The credentials are in `/home/ubuntu/bot_bitcoin/.env` on the server; their values are never recorded here. Owner-confirmed on 2026-09-22 from earlier session notes; not re-verified on the server in this session.
- Historical: the GitHub Actions secrets that the retired workflows used can be deleted from the GitHub repository settings (ADR-001).

## Release procedure

- Accepted: deployment is manual. Copy `robot_bitcoin.py` to `/home/ubuntu/bot_bitcoin/` with `scp`, then check `logs/bot.log` after the next scheduled run. Owner-confirmed on 2026-09-22 from earlier session notes; not re-verified on the server in this session.
- Accepted: never copy the repository's `historico_bitcoin.json` or `ultimo_preco.txt` onto the server, because that would overwrite the live state. Owner-confirmed on 2026-09-22 from earlier session notes; not re-verified on the server in this session.
- Verified: the procedure below was run on 2026-09-22 at 23:30 Brasília time (02:30 UTC on 2026-09-23; deploy of 72508a4, owner approval in conversation). Every step exited with 0.
  1. Send the Git blob, not the Windows working copy: `git show HEAD:robot_bitcoin.py > f`. The checkout uses CRLF, so its hash differs from Git's and from the server's LF file.
  2. Pre-check in `/tmp/deploy-check` with the server `.venv`: `py_compile` and `python -m unittest test_robot_bitcoin` (the test file is copied only to /tmp). Then run a dry `previsao_manha` there with `gerar_json` and `enviar_telegram` patched, on a copy of the live history. This proves the Binance, CoinGecko and RSS sources from the server without sending anything.
  3. `scp` the file to `robot_bitcoin.py.new`, then in one ssh command with `set -e`, in order: abort if `pgrep -af "[p]ython robot_bitcoin[.]py"` finds a running task; abort unless the hashes of `.new` and of the active file are the expected ones; `cp -p robot_bitcoin.py robot_bitcoin.py.bak-<date>-<old commit>`; `mv -f robot_bitcoin.py.new robot_bitcoin.py`; `py_compile` plus a plain `import robot_bitcoin`.
  4. Confirm that the `historico_bitcoin.json` hash did not change.
- Verified gotcha: `pgrep -f robot_bitcoin.py`, and even `[r]obot_bitcoin.py`, matches the ssh command itself whenever that command mentions the file anywhere. Match the cron command line `[p]ython robot_bitcoin[.]py` instead.
- Verified: after the 2026-09-22 23:30 deploy the server runs `robot_bitcoin.py` sha256 `1ad3e9c326fc3f7f…` (Git 72508a4). The previous version is `robot_bitcoin.py.bak-20260923-e0bb956` (sha256 `f0940b1d96775278…`).

## Smoke checks

- Verified: the observable success signal is the log line "✅ Mensagem entregue ao Telegram com sucesso!" plus the Telegram message itself. On failure a "⚠️ Falha na tarefa" message is sent and the run exits non-zero. Source: `robot_bitcoin.py` (reviewed e0bb956).

## Rollback

- Verified procedure (backup confirmed present on 2026-09-22, not executed): `ssh oracle-bot 'cd ~/bot_bitcoin && cp -p robot_bitcoin.py.bak-20260923-e0bb956 robot_bitcoin.py'`. The state files are not touched. Older entries in history keep working with the old code, because the new fields are only additions.
- Historical: before a backup existed, the rollback candidate was copying the previous `robot_bitcoin.py` from Git history back with `scp`.

## Approval policy

- Unresolved: no approval policy is documented. A manual run sends real Telegram messages and uses the Gemini API quota. Source: `robot_bitcoin.py` (reviewed e0bb956).

Instructions are not containment. Name the external controls and credential
scope required for each environment.
