# TODO: Refactor this module a bit so its more human-readable

import base64
from datetime import datetime

import instructor
from openai.types.chat import ChatCompletionMessageParam

from expenses.models import (
    CATEGORY_DESCRIPTIONS,
    Category,
    Expense,
    ExpenseList,
    Pagador,
    StatementTransaction,
    UnmatchedList,
)

_CATEGORIES_WITH_DESCRIPTIONS = "\n".join(
    f"- {c.value}: {CATEGORY_DESCRIPTIONS[c]}" for c in Category
)

_EXPENSE_SYSTEM = f"""You are a helpful assistant that extracts expense information from messages sent by David or Daniela (a Colombian couple tracking household expenses).

Extract a single expense with these fields:
- fecha: date of the expense in YYYY-MM-DD format (use the provided message date if not specified)
- descripcion: merchant or place name — concise, not the full message (e.g. "Carulla", "Netflix", "Éxito")
- categoria: one of the valid categories below, or null if you are not confident
- valor: the amount paid as a positive number (no currency symbols)
- pagador: who paid — must be exactly "David" or "Daniela" (default to the sender if not stated)

Valid categories:
{_CATEGORIES_WITH_DESCRIPTIONS}

Only assign a category when you are confident. Leave it null if uncertain.
Messages may be in Spanish or English."""

_RECONCILE_SYSTEM = """You are helping reconcile bank statement transactions against recorded household expenses.

Compare the two lists and return ONLY the statement transactions that are NOT yet recorded in the sheet.

A transaction is considered matched if ALL of the following apply:
- Date is within ±2 days
- Amount is identical
- Merchant is semantically the same (commercial vs legal name is acceptable, e.g. "Carulla" matches "ALMACENES EXITO SA")

Return only genuinely unrecorded transactions."""

_CATEGORIZE_SYSTEM = f"""You are a helpful assistant that categorizes bank transactions into household expense categories.

For each transaction, return a complete expense record:
- fecha: use the transaction date (YYYY-MM-DD)
- descripcion: clean merchant name (e.g. "Éxito", "Netflix", "Gasolina") — readable, not the raw legal name
- categoria: one of the valid categories below, or null if not confident
- valor: the transaction amount (positive number)
- pagador: use the provided pagador value exactly

Valid categories:
{_CATEGORIES_WITH_DESCRIPTIONS}

Only assign a category when you are confident. Leave it null if uncertain."""


def parse_text(
    text: str,
    sender: str,
    sent_at: datetime,
    client: instructor.Instructor,
) -> Expense:
    user_content = f"""\
Message date: {sent_at.date().isoformat()}
Sender: {sender}
Message: {text}"""
    messages: list[ChatCompletionMessageParam] = [
        {"role": "system", "content": _EXPENSE_SYSTEM},
        {"role": "user", "content": user_content},
    ]
    return client.chat.completions.create(
        response_model=Expense,
        messages=messages,
    )


def parse_image(
    image_bytes: bytes,
    sender: str,
    sent_at: datetime,
    client: instructor.Instructor,
    caption: str | None = None,
) -> Expense:
    b64 = base64.b64encode(image_bytes).decode()
    caption_hint = (
        f"\nSender's caption: {caption}"
        f"\nIf the caption states who paid or specifies a category, respect it."
        if caption
        else ""
    )
    user_text = f"""\
Message date: {sent_at.date().isoformat()}
Sender: {sender}{caption_hint}
This is a photo of a receipt. Extract the expense details."""
    messages: list[ChatCompletionMessageParam] = [
        {"role": "system", "content": _EXPENSE_SYSTEM},
        {
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{b64}"},
                },
                {"type": "text", "text": user_text},
            ],
        },
    ]
    return client.chat.completions.create(
        response_model=Expense,
        messages=messages,
    )


def reconcile(
    txns: list[StatementTransaction],
    sheet_entries: list[Expense],
    client: instructor.Instructor,
) -> list[StatementTransaction]:
    txns_text = "\n".join(f"- {t.fecha}  {t.descripcion}  ${t.valor}" for t in txns)
    sheet_text = (
        "\n".join(
            f"- {e.fecha}  {e.descripcion}  ${e.valor}  {e.pagador}"
            for e in sheet_entries
        )
        or "(none)"
    )

    user_content = f"""\
BANK STATEMENT TRANSACTIONS:
{txns_text}

ALREADY RECORDED IN SHEET:
{sheet_text}

Which bank statement transactions are NOT already recorded in the sheet?"""
    messages: list[ChatCompletionMessageParam] = [
        {"role": "system", "content": _RECONCILE_SYSTEM},
        {"role": "user", "content": user_content},
    ]
    result = client.chat.completions.create(
        response_model=UnmatchedList,
        messages=messages,
    )
    return result.unmatched


def categorize_transactions(
    txns: list[StatementTransaction],
    pagador: Pagador,
    client: instructor.Instructor,
) -> list[Expense]:
    txns_text = "\n".join(
        f"- fecha={t.fecha}  descripcion={t.descripcion}  valor={t.valor}" for t in txns
    )
    user_content = f"""\
Pagador: {pagador}

Categorize each of these transactions and return a complete expense record for each.

Transactions:
{txns_text}"""
    messages: list[ChatCompletionMessageParam] = [
        {"role": "system", "content": _CATEGORIZE_SYSTEM},
        {"role": "user", "content": user_content},
    ]
    result = client.chat.completions.create(
        response_model=ExpenseList,
        messages=messages,
    )
    return result.expenses
