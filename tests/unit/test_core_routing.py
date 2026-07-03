from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch

from expenses.core import process_update
from expenses.models import Expense


def test_unknown_sender_ignored(unknown_sender_update, settings):
    telegram, client, sheet = MagicMock(), MagicMock(), MagicMock()

    process_update(
        unknown_sender_update,
        telegram=telegram,
        client=client,
        sheet=sheet,
        config=settings,
    )

    sheet.append.assert_not_called()
    telegram.send_message.assert_not_called()


def test_dispatch_by_message_type(
    david_text_update, daniela_photo_update, david_pdf_update, settings
):
    text_expense = Expense(
        fecha=date(2026, 6, 12), descripcion="X", valor=Decimal("1"), pagador="David"
    )
    photo_expense = Expense(
        fecha=date(2026, 6, 12), descripcion="Y", valor=Decimal("2"), pagador="Daniela"
    )

    # text path → parse_text
    with patch("expenses.core.parse_text", return_value=text_expense) as parse_text:
        telegram, client, sheet = MagicMock(), MagicMock(), MagicMock()
        process_update(
            david_text_update, telegram=telegram, client=client, sheet=sheet, config=settings
        )
        parse_text.assert_called_once()

    # photo path → parse_image, telegram.download_file
    with patch("expenses.core.parse_image", return_value=photo_expense) as parse_image:
        telegram, client, sheet = MagicMock(), MagicMock(), MagicMock()
        telegram.download_file.return_value = b"bytes"
        process_update(
            daniela_photo_update, telegram=telegram, client=client, sheet=sheet, config=settings
        )
        parse_image.assert_called_once()
        telegram.download_file.assert_called_once()

    # pdf path → reconcile_statement
    with patch(
        "expenses.core.reconcile_statement", return_value=[]
    ) as reconcile_statement:
        telegram, client, sheet = MagicMock(), MagicMock(), MagicMock()
        telegram.download_file.return_value = b"pdf"
        process_update(
            david_pdf_update, telegram=telegram, client=client, sheet=sheet, config=settings
        )
        reconcile_statement.assert_called_once()
