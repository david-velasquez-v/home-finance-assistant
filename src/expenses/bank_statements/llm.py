import instructor
from openai.types.chat import ChatCompletionMessageParam

from expenses.models import (
    Expense,
    ExpenseList,
    Pagador,
    StatementTransaction,
    TransactionList,
    UnmatchedList,
)
from expenses.prompts import CATEGORIZE_SYSTEM, RECONCILE_SYSTEM, STATEMENT_SYSTEM


def transactions_to_text(txns: list[StatementTransaction]) -> str:
    return "\n".join(f"- {t.fecha}  {t.descripcion}  ${t.valor}" for t in txns)


def sheet_entries_to_text(sheet_entries: list[Expense]) -> str:
    return (
        "\n".join(
            f"- {e.fecha}  {e.descripcion}  ${e.valor}  {e.pagador}"
            for e in sheet_entries
        )
        or "(none)"
    )


def parse_user_content(pdf_text: str) -> str:
    return f"""\
Extract all transactions from this bank statement:

{pdf_text}"""


def reconcile_user_content(txn_context: str, sheet_context: str) -> str:
    return f"""\
BANK STATEMENT TRANSACTIONS:
{txn_context}

ALREADY RECORDED IN SHEET:
{sheet_context}

Which bank statement transactions are NOT already recorded in the sheet?"""


def categorize_user_content(txns_text: str, pagador: Pagador) -> str:
    return f"""\
Pagador: {pagador}

Categorize each of these transactions and return a complete expense record for each.

Transactions:
{txns_text}"""


# Parser functions -----------------------------------------------------


def parse_statement(
    pdf_text: str, client: instructor.Instructor
) -> list[StatementTransaction]:
    messages: list[ChatCompletionMessageParam] = [
        {"role": "system", "content": STATEMENT_SYSTEM},
        {"role": "user", "content": parse_user_content(pdf_text)},
    ]
    result = client.chat.completions.create(
        response_model=TransactionList,
        messages=messages,
    )
    return result.transactions


def reconcile(
    txns: list[StatementTransaction],
    sheet_entries: list[Expense],
    client: instructor.Instructor,
) -> list[StatementTransaction]:
    txns_text: str = transactions_to_text(txns)
    sheet_text: str = sheet_entries_to_text(sheet_entries)
    user_content = reconcile_user_content(txns_text, sheet_text)

    messages: list[ChatCompletionMessageParam] = [
        {"role": "system", "content": RECONCILE_SYSTEM},
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
    txns_text = transactions_to_text(txns)
    user_content = categorize_user_content(txns_text, pagador)

    messages: list[ChatCompletionMessageParam] = [
        {"role": "system", "content": CATEGORIZE_SYSTEM},
        {"role": "user", "content": user_content},
    ]
    result = client.chat.completions.create(
        response_model=ExpenseList,
        messages=messages,
    )
    return result.expenses
