# Secrets for local demo

Keep real secrets in this directory, but do not commit them.
Never commit Telegram tokens, private URLs, or copied `.env` files.

Expected local file:
- `telegram_bot_token.txt`

Example setup:
```bash
cp deploy/.env.example deploy/.env
printf '123456:telegram-bot-token' > deploy/secrets/telegram_bot_token.txt
```

If you do not want Telegram delivery, leave `SREAGENT_TELEGRAM_CHAT_ID` empty and skip the token file.

If a Telegram Bot Token was ever exposed in git history, logs, screenshots, or demos, rotate it immediately with `@BotFather` before reusing this project publicly.
