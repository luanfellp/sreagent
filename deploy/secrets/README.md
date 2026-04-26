# Secrets for local demo

Keep real secrets in this directory, but do not commit them.
Never commit Telegram tokens, WhatsApp access tokens, private URLs, or copied `.env` files.

Expected local files:
- `telegram_bot_token.txt`
- `whatsapp_access_token.txt`

Example setup:
```bash
cp deploy/.env.example deploy/.env
printf '123456:telegram-bot-token' > deploy/secrets/telegram_bot_token.txt
printf 'EAAG...' > deploy/secrets/whatsapp_access_token.txt
```

If you do not want outbound delivery, leave the destination variables empty and skip the token files.

If a Telegram Bot Token was ever exposed in git history, logs, screenshots, or demos, rotate it immediately with `@BotFather` before reusing this project publicly.
If a WhatsApp Cloud API token was exposed, revoke it in Meta Business Manager and generate a new one.
