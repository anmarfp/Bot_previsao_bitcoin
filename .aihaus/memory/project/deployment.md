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

## Smoke checks

- Verified: the observable success signal is the log line "✅ Mensagem entregue ao Telegram com sucesso!" plus the Telegram message itself. On failure a "⚠️ Falha na tarefa" message is sent and the run exits non-zero. Source: `robot_bitcoin.py` (reviewed e0bb956).

## Rollback

- Inferred candidate: to roll back, copy the previous `robot_bitcoin.py` from Git history back to the server with `scp`, without touching the state files. Not yet verified or accepted by the owner.

## Approval policy

- Unresolved: no approval policy is documented. A manual run sends real Telegram messages and uses the Gemini API quota. Source: `robot_bitcoin.py` (reviewed e0bb956).

Instructions are not containment. Name the external controls and credential
scope required for each environment.
