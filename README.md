# home-finance-assistant

Telegram bot that logs family expenses to Google Sheets and reconciles bank-statement PDFs against them.

## Running tests

Two test tiers, opt into them explicitly:

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
