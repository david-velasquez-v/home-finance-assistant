from datetime import date, datetime
from decimal import Decimal

import pytest

from expenses.config import Settings
from expenses.models import Category, Expense, StatementTransaction


@pytest.fixture
def settings() -> Settings:
    return Settings(
        telegram_bot_token="test_token",
        telegram_user_david=111,
        telegram_user_daniela=222,
        llm_provider="anthropic",
        llm_model="claude-haiku-4-5-20251001",
        anthropic_api_key="test_key",
        google_spreadsheet_id="test_spreadsheet_id",
    )


@pytest.fixture
def sample_expense() -> Expense:
    return Expense(
        fecha=date(2026, 6, 12),
        descripcion="Carulla",
        categoria=Category.MERCADO,
        valor=Decimal("45000"),
        pagador="Daniela",
    )


@pytest.fixture
def sample_expense_no_category() -> Expense:
    return Expense(
        fecha=date(2026, 6, 13),
        descripcion="Gasolina",
        categoria=None,
        valor=Decimal("80000"),
        pagador="David",
    )


@pytest.fixture
def sample_transaction() -> StatementTransaction:
    return StatementTransaction(
        fecha=date(2026, 6, 10),
        descripcion="ALMACENES EXITO SA",
        valor=Decimal("123450"),
    )


@pytest.fixture
def david_text_update() -> dict:
    return {
        "update_id": 100001,
        "message": {
            "message_id": 1,
            "from": {"id": 111, "first_name": "David"},
            "chat": {"id": 111},
            "date": int(datetime(2026, 6, 12, 14, 30).timestamp()),
            "text": "Carulla 45000",
        },
    }


@pytest.fixture
def daniela_photo_update() -> dict:
    return {
        "update_id": 100002,
        "message": {
            "message_id": 2,
            "from": {"id": 222, "first_name": "Daniela"},
            "chat": {"id": 222},
            "date": int(datetime(2026, 6, 12, 15, 0).timestamp()),
            "photo": [
                {"file_id": "small_id", "file_size": 1000, "width": 100, "height": 100},
                {"file_id": "large_id", "file_size": 50000, "width": 1280, "height": 960},
            ],
        },
    }


@pytest.fixture
def david_pdf_update() -> dict:
    return {
        "update_id": 100003,
        "message": {
            "message_id": 3,
            "from": {"id": 111, "first_name": "David"},
            "chat": {"id": 111},
            "date": int(datetime(2026, 6, 12, 16, 0).timestamp()),
            "document": {
                "file_id": "pdf_file_id",
                "file_name": "statement.pdf",
                "mime_type": "application/pdf",
            },
        },
    }


@pytest.fixture
def unknown_sender_update() -> dict:
    return {
        "update_id": 100004,
        "message": {
            "message_id": 4,
            "from": {"id": 999, "first_name": "Stranger"},
            "chat": {"id": 999},
            "date": int(datetime(2026, 6, 12, 17, 0).timestamp()),
            "text": "hello",
        },
    }
