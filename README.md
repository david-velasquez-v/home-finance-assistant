# home-finance-assistant

Telegram bot that logs family expenses to Google Sheets and reconciles bank-statement PDFs against them.

Each run polls Telegram for new messages, sends them through an LLM to structure them into `(fecha, descripcion, categoria, valor, pagador)`, and appends them to a Google Sheet. Text messages, photo receipts, and PDF bank statements are all supported. Designed to run periodically as a scheduled job (GitHub Actions cron or Lambda + EventBridge).

## Getting started (local)

Requires [uv](https://docs.astral.sh/uv/) and Python 3.12+.

### 1. Install dependencies

```bash
uv sync --extra dev
```

### 2. Create a Telegram bot

- Open Telegram, message [@BotFather](https://t.me/BotFather), run `/newbot`, follow the prompts.
- Save the bot token BotFather gives you → goes in `TELEGRAM_BOT_TOKEN`.
- Message your new bot from your own account, then open `https://api.telegram.org/bot<TOKEN>/getUpdates` in a browser. Find `message.from.id` in the JSON — that's your Telegram user ID. Repeat for the other user.
- Set `TELEGRAM_USER_DAVID` and `TELEGRAM_USER_DANIELA` to those numeric IDs. Messages from any other sender are silently ignored.

### 3. Google service account

- In the [Google Cloud Console](https://console.cloud.google.com/), pick or create a project.
- Enable both **Google Sheets API** and **Google Drive API** for the project.
- **IAM & Admin → Service Accounts** → create a service account (any name; no project-level roles required).
- On that service account: **Keys → Add key → JSON**. Download the file.
- Minify it to a single line and paste the whole thing as the value of `GOOGLE_CREDENTIALS_JSON` in `.env`:
  ```bash
  jq -c . ~/Downloads/your-service-account.json
  ```
- Don't commit the JSON file. `.env` is already gitignored.

### 4. Google Sheet

- Create a new empty Google Sheet.
- Copy its ID from the URL (the long token between `/d/` and `/edit`) into `GOOGLE_SPREADSHEET_ID`.
- **Share** the sheet with the service account's email (looks like `something@your-project.iam.gserviceaccount.com`) with **Editor** access — otherwise the bot can't write.
- The `Gastos` tab (or whatever `GOOGLE_SHEET_NAME` you set) and the `_state` tab are created automatically on first run.

### 5. LLM provider

Pick one and set the matching key in `.env`:

| `LLM_PROVIDER` | Key env var         | Console                                                   |
|----------------|---------------------|-----------------------------------------------------------|
| `anthropic`    | `ANTHROPIC_API_KEY` | [console.anthropic.com](https://console.anthropic.com/)   |
| `openai`       | `OPENAI_API_KEY`    | [platform.openai.com](https://platform.openai.com/)       |
| `google`       | `GEMINI_API_KEY`    | [aistudio.google.com](https://aistudio.google.com/apikey) |

Also set `LLM_MODEL` to a specific model id for that provider (see `.env.example` for the default).

### 6. Fill in `.env`

Copy the template and fill in the values collected above:

```bash
cp .env.example .env
```

## Running

```bash
uv run python -m expenses
```

Each invocation fetches all pending Telegram updates, processes them, and stamps `last_update_id` + `last_run` into the `_state` tab. Safe to re-run — already-processed messages aren't re-processed.

## Tests

```bash
# Unit tests only — fast, no network, no API keys required.
uv run pytest -m "not acceptance"

# Acceptance suite — calls the real LLM configured in .env. Slow (~1 min) and
# costs a few cents per full run. Requires an API key for the provider set in
# .env (skips gracefully if unset).
uv run pytest -m acceptance

# Everything (unit + acceptance).
uv run pytest
```

Individual tests can be run via VSCode's test runner or `pytest` directly with the file/node path.

## Type checking

```bash
uv run ty check src/
```
