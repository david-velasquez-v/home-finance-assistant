import instructor
from openai.types.chat import ChatCompletionMessageParam

from expenses.models import (
    CATEGORY_DESCRIPTIONS,
    Category,
    Expense,
    ExpenseList,
    Pagador,
    StatementTransaction,
    TransactionList,
    UnmatchedList,
)

# Prompts --------------------------------------------------------------

_CATEGORIES_WITH_DESCRIPTIONS = "\n".join(
    f"- {c.value}: {CATEGORY_DESCRIPTIONS[c]}" for c in Category
)

_STATEMENT_SYSTEM = """You are a helpful assistant that extracts transactions from a bank statement.

Extract ONLY outgoing charges — purchases, payments, transfers sent, cash withdrawals, and bank fees.
IGNORE incoming items: deposits, salary, credits, interest received, refunds, and reversals.
Only include transactions denominated in Colombian pesos (COP). IGNORE any transaction whose amount is shown solely in a foreign currency such as USD with no COP figure. This includes foreign-currency subscriptions, foreign-currency fees, and any transfer shown only in USD — including money sent to yourself, moved to a savings jar/balance, or sent to a person with your own name. If the transaction line has no COP amount, do not include it.

For each outgoing transaction extract:
- fecha: transaction date in YYYY-MM-DD format
- descripcion: merchant or description — clean up legal names into readable ones where possible (e.g. "ALMACENES EXITO SA" → "Éxito"). For transfers or bank fees, use a descriptive label (e.g. "Transferencia Bre-B", "Retiro cajero", "Cuota de manejo").
- valor: the original transaction amount as a positive number. When the account settles in a different currency than the purchase and the transaction line states the original amount (e.g. "Transacción con tarjeta de 8.750,00 COP emitida por ..."), use that original amount (8750) — NOT the converted amount in the statement's own currency column. Colombian number format uses "." for thousands and "," for decimals, so "8.750,00" is 8750 and "452.333,00" is 452333."""

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
        {"role": "system", "content": _STATEMENT_SYSTEM},
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
    txns_text = transactions_to_text(txns)
    user_content = categorize_user_content(txns_text, pagador)

    messages: list[ChatCompletionMessageParam] = [
        {"role": "system", "content": _CATEGORIZE_SYSTEM},
        {"role": "user", "content": user_content},
    ]
    result = client.chat.completions.create(
        response_model=ExpenseList,
        messages=messages,
    )
    return result.expenses
