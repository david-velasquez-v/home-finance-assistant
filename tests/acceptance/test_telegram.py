import pytest

from expenses.external.telegram import TelegramClient

pytestmark = pytest.mark.acceptance


def test_get_updates_returns_list(telegram_client: TelegramClient) -> None:
    result = telegram_client.get_updates()
    assert isinstance(result, list)
