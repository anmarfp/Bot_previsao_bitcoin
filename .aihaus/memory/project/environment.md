# Environment

## Local

- Verified: the script loads credentials from a `.env` file next to itself. Its contents were not read. Source: `robot_bitcoin.py` (reviewed e0bb956).
- Verified: `.env` is ignored by Git. `git check-ignore -v .env` matched line 1 of the ignore file on 2026-09-22, and that line was already present at commit e0bb956.
- Verified: the script reads `TELEGRAM_TOKEN`, `TELEGRAM_CHAT_ID` and the optional `GEMINI_MODEL`, and creates `genai.Client()` without an explicit key. The google-genai client therefore takes its key from the environment (`GEMINI_API_KEY`). Source: `robot_bitcoin.py` (reviewed e0bb956).
- Verified: `requirements.txt` lists `google-genai`, `httpx` and `requests`. Source: `requirements.txt` (reviewed e0bb956).

## CI

- Accepted: the repository has no CI. The scheduled GitHub Actions workflows were removed per ADR-001, and there never was a test job. Owner decision: Marco, stated in conversation on 2026-09-22.

## Staging or homolog

- Unresolved: no staging environment is documented.

## Production

- Accepted: production is an Oracle Cloud server; GitHub Actions is not used (ADR-001). The IP is kept out of this public repository and is reached through the owner's SSH alias `oracle-bot`. Owner decision: Marco, stated in conversation on 2026-09-22.
- Accepted: the SSH private key for that server is in the owner's `.ssh` folder on their PC (`~/.ssh/oracle_bot`, referenced by the `oracle-bot` alias in `~/.ssh/config`), outside this repository. The key contents are not recorded here. Owner decision: Marco, stated in conversation on 2026-09-22.
- Accepted: the instance is Ubuntu 26.04 on VM.Standard.E2.1.Micro in region sa-saopaulo-1, and the login user is `ubuntu`. Owner-confirmed on 2026-09-22 from earlier session notes; not re-verified on the server in this session.
- Accepted: the bot lives in `/home/ubuntu/bot_bitcoin`, with its own `.venv`, a `.env` file with mode 600 holding the credentials, and `logs/bot.log` rotated weekly by logrotate. The server's `historico_bitcoin.json` and `ultimo_preco.txt` are the live state files. Owner-confirmed on 2026-09-22 from earlier session notes; not re-verified on the server in this session.
- Accepted: the server time zone is America/Sao_Paulo. The crontab runs the price update at `0 0-20/2`, the morning prediction at `0 8` and the evening evaluation at `0 22` (Brasília time). Owner-confirmed on 2026-09-22 from earlier session notes; not re-verified on the server in this session.
- Accepted: the older Oracle instance, which could no longer be reached over SSH, has been deleted, so it can no longer send duplicate messages. Owner decision: Marco, stated in conversation on 2026-09-22.

### Retired: GitHub Actions (superseded by ADR-001)

- Historical: until 2026-09-22 the repository had three scheduled GitHub Actions workflows: the price update every 2h (03:00–23:00 UTC), the morning prediction at 09:00 UTC (06:00 Brasília) and the evening evaluation at 01:00 UTC. They ran on `ubuntu-latest` with Python 3.10, read the Gemini and Telegram credentials from GitHub Actions secrets, and committed the state files back to the repository. They were removed per ADR-001; their last version is in Git history at commit e0bb956.

### Resolved conflicts

- Resolved: the name `preco_8h` versus a 06:00 Brasília run. The mismatch existed only in the retired morning workflow. The server runs the morning prediction at 08:00 Brasília time, which matches the name. Owner-confirmed on 2026-09-22 from earlier session notes; not re-verified on the server in this session.
- Resolved: which runtime is live. The owner confirmed that production is the Oracle server and that GitHub Actions is not used (ADR-001). Owner decision: Marco, stated in conversation on 2026-09-22.

## External dependencies

- Verified: CoinGecko public API (`/simple/price`, `/coins/markets`), alternative.me Fear & Greed API, RSS feeds from Google News (two queries), CoinDesk, Cointelegraph and Decrypt, the Google Gemini API through `google-genai`, and the Telegram Bot API `sendMessage`. Source: `robot_bitcoin.py` (reviewed e0bb956).

Describe topology and access expectations. Never store credentials or secret
values in this file.
