import instructor
from openai.types.chat import ChatCompletionMessageParam

from expenses.models import StatementTransaction, TransactionList

_STATEMENT_SYSTEM = """You are a helpful assistant that extracts transactions from a bank statement.

Extract ONLY outgoing charges — purchases, payments, transfers sent, cash withdrawals, and bank fees.
IGNORE incoming items: deposits, salary, credits, interest received, refunds, and reversals.

For each outgoing transaction extract:
- fecha: transaction date in YYYY-MM-DD format
- descripcion: merchant or description — clean up legal names into readable ones where possible (e.g. "ALMACENES EXITO SA" → "Éxito"). For transfers or bank fees, use a descriptive label (e.g. "Transferencia Bre-B", "Retiro cajero", "Cuota de manejo").
- valor: the amount as a positive number"""


def parse_statement(
    pdf_text: str, client: instructor.Instructor
) -> list[StatementTransaction]:
    user_content = f"""\
Extract all transactions from this bank statement:

{pdf_text}"""
    messages: list[ChatCompletionMessageParam] = [
        {"role": "system", "content": _STATEMENT_SYSTEM},
        {"role": "user", "content": user_content},
    ]
    result = client.chat.completions.create(
        response_model=TransactionList,
        messages=messages,
    )
    return result.transactions
