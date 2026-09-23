# Decisions

- Verified: at commit e0bb956 the repository contained no ADR, decision log or accepted convention document. Source: `robot_bitcoin.py` (reviewed e0bb956).

## ADR-001 — Production runs on the Oracle server; GitHub Actions is retired

**Status:** accepted
**Date:** 2026-09-22
**Milestone:** none
**Amends:** supersedes ADR-C2

Related rules: none

### Context

- Accepted: at commit e0bb956 the repository contained three scheduled GitHub Actions workflows, which gave the impression that they were the production runtime.

### Decision

- Accepted: GitHub Actions is no longer used. The bot runs in production on an Oracle Cloud server. The server IP is deliberately not recorded in this public repository. Owner decision: Marco, stated in conversation on 2026-09-22.

### Consequences

- Accepted: the three workflow files were removed from the repository so they cannot run again and send duplicate Telegram messages. Owner decision: Marco, stated in conversation on 2026-09-22.
- Accepted: the state files are no longer committed by a bot. The live copies are on the server, and the repository copies are outdated snapshots. Owner-confirmed on 2026-09-22 from earlier session notes; not re-verified on the server in this session.

### Reversal or migration

- Unresolved: not documented.

## Inferred candidates (not accepted)

### ADR-C1 — Collect news from RSS instead of Gemini Google Search

**Status:** proposed (inferred from a code comment; no owner acceptance recorded)
**Date:** unknown (the code landed in e0bb956 on 2026-09-22)
**Milestone:** none
**Amends:** none

Related rules: none

- Context: a code comment says Google Search grounding is unavailable on the Gemini 3.x free plan. Source: `robot_bitcoin.py` (reviewed e0bb956).
- Decision (as implemented): the morning task fetches headlines from Google News, CoinDesk, Cointelegraph and Decrypt RSS feeds (15 per source, last 24h, de-duplicated) and passes them to Gemini in the prompt. Source: `robot_bitcoin.py` (reviewed e0bb956).
- Consequences (as implemented): if every feed fails the morning task stops with an error, while a single failing feed is skipped. Source: `robot_bitcoin.py` (reviewed e0bb956).
- Reversal or migration: unresolved; not documented.

### ADR-C2 — Commit run state back into the repository

**Status:** superseded by ADR-001 (GitHub Actions is no longer used; this described the retired workflows)
**Date:** unknown
**Milestone:** none
**Amends:** none

Related rules: none

- Decision (as implemented at commit e0bb956): each scheduled workflow committed its state file as `github-actions`, then ran `git pull --rebase` and pushed.
- Consequences: superseded by ADR-001.
