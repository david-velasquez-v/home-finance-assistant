from collections.abc import Iterator
from pathlib import Path

import gspread
import instructor
import pytest

from expenses.config import Settings
from expenses.external.llm import build_client
from expenses.external.sheets.client import SheetsClient
from expenses.external.telegram import TelegramClient

_API_KEY_FIELDS = {
    "anthropic": "anthropic_api_key",
    "openai": "openai_api_key",
    "google": "gemini_api_key",
}


@pytest.fixture(scope="session")
def acceptance_settings() -> Settings:
    current_file_path = Path(__file__).resolve()
    two_folders_up = current_file_path.parents[2]
    env_path = two_folders_up / ".env.test"

    assert env_path.is_file(), f"File not found: {env_path}"

    settings = Settings(_env_file=env_path)  # ty: ignore -- reads from .env at runtime
    field: str | None = _API_KEY_FIELDS.get(settings.llm_provider)
    if field is None or not getattr(settings, field, ""):
        pytest.skip(f"no API key configured for provider {settings.llm_provider!r}")
    return settings


@pytest.fixture(scope="session")
def client(acceptance_settings: Settings) -> instructor.Instructor:
    return build_client(config=acceptance_settings)


@pytest.fixture(scope="session")
def sheets_client(acceptance_settings: Settings) -> SheetsClient:
    return SheetsClient(
        credentials_json=acceptance_settings.google_credentials_json,
        spreadsheet_id=acceptance_settings.google_spreadsheet_id,
    )


@pytest.fixture(scope="session")
def telegram_client(acceptance_settings: Settings) -> TelegramClient:
    return TelegramClient(token=acceptance_settings.telegram_bot_token)


def _delete_tab_if_exists(client: SheetsClient, title: str) -> None:
    spreadsheet = client._spreadsheet  # test-only reach-in
    try:
        ws = spreadsheet.worksheet(title)
    except gspread.WorksheetNotFound:
        return
    spreadsheet.del_worksheet(ws)


@pytest.fixture
def clean_state_tab(
    sheets_client: SheetsClient, acceptance_settings: Settings
) -> Iterator[None]:
    _delete_tab_if_exists(sheets_client, acceptance_settings.state_sheet_name)
    try:
        yield
    finally:
        _delete_tab_if_exists(sheets_client, acceptance_settings.state_sheet_name)


@pytest.fixture
def preserve_expenses_tail(
    sheets_client: SheetsClient, acceptance_settings: Settings
) -> Iterator[gspread.Worksheet]:
    """Snapshot the expenses tab row count; delete any rows appended during the test."""
    ws = sheets_client.get_or_create_worksheet(acceptance_settings.google_sheet_name)
    n_before = len(ws.get_all_values())
    try:
        yield ws
    finally:
        n_after = len(ws.get_all_values())
        if n_after > n_before:
            ws.delete_rows(n_before + 1, n_after)
