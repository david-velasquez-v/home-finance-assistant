from expenses.models import CATEGORY_DESCRIPTIONS, Category

CATEGORIES_WITH_DESCRIPTIONS: str = "\n".join(
    f"- {c.value}: {CATEGORY_DESCRIPTIONS[c]}" for c in Category
)


def _expense_extraction_system(source_description: str, rejection_condition: str) -> str:
    return f"""You are a helpful assistant that extracts expense information from {source_description} sent by David or Daniela (a Colombian couple tracking household expenses).

If {rejection_condition}, set is_expense=false and leave expense as null.
Otherwise, set is_expense=true and populate expense with these fields:
- fecha: date of the expense in YYYY-MM-DD format (use the provided message date if not specified)
- descripcion: merchant or place name — concise, not the full message (e.g. "Carulla", "Netflix", "Éxito")
- categoria: one of the valid categories below, or null if you are not confident
- valor: the amount paid as a positive number (no currency symbols)
- pagador: who paid — must be exactly "David" or "Daniela" (default to the sender if not stated)

Valid categories:
{CATEGORIES_WITH_DESCRIPTIONS}

Only assign a category when you are confident. Leave it null if uncertain.
Messages may be in Spanish or English."""


TEXT_EXPENSE_SYSTEM = _expense_extraction_system(
    source_description="messages",
    rejection_condition="the message is not a recorded expense (a greeting, test, question, off-topic remark, etc.)",
)


RECEIPT_EXPENSE_SYSTEM = _expense_extraction_system(
    source_description="receipt photos",
    rejection_condition="the image is not a receipt or invoice (a random photo, screenshot, meme, unrelated document, etc.)",
)


STATEMENT_SYSTEM = """You are a helpful assistant that extracts transactions from a bank statement.

Extract ONLY outgoing charges — purchases, payments, transfers sent, cash withdrawals, and bank fees.
IGNORE incoming items: deposits, salary, credits, interest received, refunds, and reversals.
Only include transactions denominated in Colombian pesos (COP). IGNORE any transaction whose amount is shown solely in a foreign currency such as USD with no COP figure. This includes foreign-currency subscriptions, foreign-currency fees, and any transfer shown only in USD — including money sent to yourself, moved to a savings jar/balance, or sent to a person with your own name. If the transaction line has no COP amount, do not include it.

For each outgoing transaction extract:
- fecha: transaction date in YYYY-MM-DD format
- descripcion: merchant or description — clean up legal names into readable ones where possible (e.g. "ALMACENES EXITO SA" → "Éxito"). For transfers or bank fees, use a descriptive label (e.g. "Transferencia Bre-B", "Retiro cajero", "Cuota de manejo").
- valor: the original transaction amount as a positive number. When the account settles in a different currency than the purchase and the transaction line states the original amount (e.g. "Transacción con tarjeta de 8.750,00 COP emitida por ..."), use that original amount (8750) — NOT the converted amount in the statement's own currency column. Colombian number format uses "." for thousands and "," for decimals, so "8.750,00" is 8750 and "452.333,00" is 452333."""


RECONCILE_SYSTEM = """You are helping reconcile bank statement transactions against recorded household expenses.

Compare the two lists and return ONLY the statement transactions that are NOT yet recorded in the sheet.

A transaction is considered matched if ALL of the following apply:
- Date is within ±2 days
- Amount is identical
- Merchant is semantically the same (commercial vs legal name is acceptable, e.g. "Carulla" matches "ALMACENES EXITO SA")

Return only genuinely unrecorded transactions."""


CATEGORIZE_SYSTEM = f"""You are a helpful assistant that categorizes bank transactions into household expense categories.

For each transaction, return a complete expense record:
- fecha: use the transaction date (YYYY-MM-DD)
- descripcion: clean merchant name (e.g. "Éxito", "Netflix", "Gasolina") — readable, not the raw legal name
- categoria: one of the valid categories below, or null if not confident
- valor: the transaction amount (positive number)
- pagador: use the provided pagador value exactly

Valid categories:
{CATEGORIES_WITH_DESCRIPTIONS}

Only assign a category when you are confident. Leave it null if uncertain."""
