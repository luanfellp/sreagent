# Security Notes

## Secrets and local credentials

- Never commit `.env`, `deploy/.env`, `deploy/secrets/*`, private URLs, API tokens, or bot credentials.
- Keep local secrets only under `deploy/secrets/` or in your shell environment.
- The distributable package excludes local secrets, caches, virtualenvs, workspace notes, and other machine-local artifacts.

## Telegram token exposure

If a Telegram Bot Token has ever been exposed in git history, screenshots, logs, or terminal recordings:

1. Rotate the token immediately with `@BotFather`.
2. Replace the local file in `deploy/secrets/telegram_bot_token.txt`.
3. Update any deployment secret store or CI secret that still references the old token.
4. Treat the previous token as compromised even if the repository is now clean.

## Read-only posture

SREAgent is intentionally read-only.

- It observes alerts and telemetry.
- It correlates evidence and drafts hypotheses.
- It suggests next steps.
- It does not execute remediation.

Notifications are optional outward delivery only; they are not remediation actions.
