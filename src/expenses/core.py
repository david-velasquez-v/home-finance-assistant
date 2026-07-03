from typing import Any

import instructor

from expenses.bank_statements import llm as bank_llm
from expenses.bank_statements import multimodal as bank_multimodal
from expenses.config import Settings
from expenses.external.telegram import TelegramClient
from expenses.models import Expense, Pagador, StatementTransaction
from expenses.receipts.llm import parse_image
from expenses.external.sheets.adapter import SheetAdapter
from expenses.telegram_processor import (
    DocumentMessage,
    PhotoMessage,
    TextMessage,
    classify_update,
)
from expenses.text_messages.llm import parse_text

_NOT_AN_EXPENSE = "🤔 No pude detectar un gasto"


def reconcile_statement(
    pdf_bytes: bytes,
    sheet: SheetAdapter,
    client: instructor.Instructor,
    sender: Pagador,
) -> list[StatementTransaction]:
    txns = bank_multimodal.extract_transactions(pdf_bytes=pdf_bytes, client=client)
    if not txns:
        return []
    sheet_entries = sheet.read_expenses(
        since=min(t.fecha for t in txns),
        until=max(t.fecha for t in txns),
        pagador=sender,
    )
    return bank_llm.reconcile(
        txns=txns, sheet_entries=sheet_entries, client=client
    )


def format_confirmation(expense: Expense) -> str:
    category = expense.categoria.value if expense.categoria else "[sin categoría]"
    return f"""\
✅ Registrado
{expense.descripcion} — ${expense.valor:,.0f} — {category} — {expense.pagador} — {expense.fecha}"""


def format_reconcile_added(expenses: list[Expense]) -> str:
    if not expenses:
        return "✅ Todo registrado. No hay transacciones pendientes."
    lines = [f"📋 Reconciliación: {len(expenses)} transacciones agregadas\n"]
    for expense in expenses:
        category = expense.categoria.value if expense.categoria else "[sin categoría]"
        lines.append(
            f"• {expense.descripcion} — ${expense.valor:,.0f} — {category} — {expense.fecha}"
        )
    return "\n".join(lines)


def process_update(
    update: dict[str, Any],
    *,
    telegram: TelegramClient,
    client: instructor.Instructor,
    sheet: SheetAdapter,
    config: Settings,
) -> None:
    msg = classify_update(update=update, config=config)
    if msg is None:
        return

    try:
        match msg:
            case TextMessage():
                expense = parse_text(
                    text=msg.text,
                    sender=msg.sender_name,
                    sent_at=msg.sent_at,
                    client=client,
                )
                if expense is None:
                    telegram.send_message(
                        chat_id=msg.chat_id,
                        text=_NOT_AN_EXPENSE,
                        reply_to_message_id=msg.message_id,
                    )
                    return
                sheet.append(expense=expense)
                telegram.send_message(
                    chat_id=msg.chat_id,
                    text=format_confirmation(expense=expense),
                    reply_to_message_id=msg.message_id,
                )

            case PhotoMessage():
                image = telegram.download_file(file_id=msg.file_id)
                expense = parse_image(
                    image_bytes=image,
                    sender=msg.sender_name,
                    sent_at=msg.sent_at,
                    client=client,
                    caption=msg.caption,
                )
                if expense is None:
                    telegram.send_message(
                        chat_id=msg.chat_id,
                        text=_NOT_AN_EXPENSE,
                        reply_to_message_id=msg.message_id,
                    )
                    return
                sheet.append(expense=expense)
                telegram.send_message(
                    chat_id=msg.chat_id,
                    text=format_confirmation(expense=expense),
                    reply_to_message_id=msg.message_id,
                )

            case DocumentMessage():
                pdf_bytes = telegram.download_file(file_id=msg.file_id)
                unmatched = reconcile_statement(
                    pdf_bytes=pdf_bytes,
                    sheet=sheet,
                    client=client,
                    sender=msg.sender_name,
                )
                if not unmatched:
                    telegram.send_message(
                        chat_id=msg.chat_id,
                        text="✅ Todo registrado. No hay transacciones pendientes.",
                        reply_to_message_id=msg.message_id,
                    )
                else:
                    expenses = bank_llm.categorize_transactions(
                        txns=unmatched,
                        pagador=msg.sender_name,
                        client=client,
                    )
                    for expense in expenses:
                        sheet.append(expense=expense)
                    telegram.send_message(
                        chat_id=msg.chat_id,
                        text=format_reconcile_added(expenses=expenses),
                        reply_to_message_id=msg.message_id,
                    )

    except Exception as exc:
        telegram.send_message(
            chat_id=msg.chat_id,
            text=f"❌ Error procesando mensaje: {exc}",
            reply_to_message_id=msg.message_id,
        )
        raise
