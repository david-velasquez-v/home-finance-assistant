import base64

import instructor
from instructor.processing.multimodal import PDF

from expenses.bank_statements.llm import parse_statement
from expenses.bank_statements.pdf import extract_pdf_text, text_is_unusable
from expenses.models import StatementTransaction, TransactionList
from expenses.prompts import STATEMENT_SYSTEM

_MULTIMODAL_USER_PROMPT = """\
Extract all transactions from the attached bank statement PDF."""


def parse_statement_pdf(
    pdf_bytes: bytes, client: instructor.Instructor
) -> list[StatementTransaction]:
    """Parse a statement by sending the raw PDF to a multimodal LLM.

    Fallback for PDFs (e.g. Wise) whose embedded fonts lack a ToUnicode CMap, so
    pdfplumber returns `(cid:XX)` gibberish instead of readable text. instructor's
    `PDF` primitive renders the document into the provider-specific shape
    (Anthropic `document`, OpenAI `file`, Gemini `Part`) automatically, so this
    works with whatever provider `LLM_PROVIDER` selects — no code change needed.
    """
    data = base64.b64encode(pdf_bytes).decode("ascii")
    document = PDF(source="statement.pdf", data=data)
    messages = [
        {"role": "system", "content": STATEMENT_SYSTEM},
        {
            "role": "user",
            "content": [
                {"type": "text", "text": _MULTIMODAL_USER_PROMPT},
                document,
            ],
        },
    ]
    # `create_fn` is instructor's internal `Callable[..., Any]`; going through it
    # (rather than `chat.completions.create`) avoids the typed create overloads
    # rejecting a `PDF` object inside message content. `handle_kwargs` injects the
    # provider/model bound by `from_provider`, which `create_fn` doesn't add on
    # its own.
    call_kwargs = client.handle_kwargs(
        {"response_model": TransactionList, "messages": messages}
    )
    result: TransactionList = client.create_fn(**call_kwargs)
    return result.transactions


def extract_transactions(
    pdf_bytes: bytes, client: instructor.Instructor
) -> list[StatementTransaction]:
    """Extract statement transactions, choosing the extraction path automatically.

    Tries pdfplumber text extraction first; if the text is empty or `(cid:XX)`
    gibberish (see `text_is_unusable`), falls back to the multimodal path. The
    choice is made from the extracted text alone — a readable statement that the
    LLM turns into zero transactions is surfaced as-is, not silently retried
    through the multimodal path.
    """
    pdf_text = extract_pdf_text(pdf_bytes=pdf_bytes)
    if text_is_unusable(pdf_text):
        return parse_statement_pdf(pdf_bytes=pdf_bytes, client=client)
    return parse_statement(pdf_text=pdf_text, client=client)
