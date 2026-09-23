# Project

## Purpose

- Verified: a single Python script (`robot_bitcoin.py`) sends Bitcoin (BTC/USD) updates to a Telegram chat. It has three tasks: a price update every two hours, a daily morning SUBIR/CAIR ("up/down") prediction generated with Google Gemini, and an evening evaluation of that prediction. Source: `robot_bitcoin.py` (reviewed e0bb956).
- Verified: the evening evaluation asks Gemini for a short lesson (`aprendizado`). That lesson is stored and injected into the next morning's prompt as "Lição de ontem", so each prediction learns from the previous result. Source: `robot_bitcoin.py` (reviewed e0bb956).

## Users and outcomes

- Verified: messages go to one Telegram chat identified by the `TELEGRAM_CHAT_ID` environment variable. Messages and Gemini prompts are written in Portuguese. Source: `robot_bitcoin.py` (reviewed e0bb956).
- Verified: the evening message reports the running hit rate ("Placar geral") over all evaluated predictions. Source: `robot_bitcoin.py` (reviewed e0bb956).

## In scope

- Verified: the prediction horizon is from the moment of the morning run until 22:00 Brasília time the same day. The only outcomes are SUBIR or CAIR. Source: `robot_bitcoin.py` (reviewed e0bb956).
- Verified: prediction inputs are CoinGecko market data (price, 24h/7d change, 24h high/low, volume), the alternative.me Fear & Greed index (optional), and RSS headlines from the last 24 hours. Source: `robot_bitcoin.py` (reviewed e0bb956).

## Out of scope

- Unresolved: no repository document states what is out of scope. For example, it is not stated whether trading, multiple assets or multiple chats are excluded. Ask the owner.

## Definition of Done

- Unresolved: no Definition of Done is documented. The repository has no test suite, linter or CI check job. Source: `robot_bitcoin.py` (reviewed e0bb956).

## Current constraints

- Verified: a code comment says the news research uses RSS feeds because Google Search is unavailable on the Gemini 3.x free plan. Source: `robot_bitcoin.py` (reviewed e0bb956).
- Verified: the default model is `gemini-3.8-flash`, which the `GEMINI_MODEL` environment variable can override. Source: `robot_bitcoin.py` (reviewed e0bb956).
- Verified: Gemini text in Telegram messages is truncated to 1500 characters (500 for error text) to stay under Telegram's 4096-character limit. Source: `robot_bitcoin.py` (reviewed e0bb956).
- Accepted: production runs on an Oracle Cloud server scheduled by cron, and GitHub Actions is retired (ADR-001). Owner decision: Marco, stated in conversation on 2026-09-22.
