import base64
from datetime import datetime

import instructor
from openai.types.chat import ChatCompletionMessageParam

from expenses.models import CATEGORY_DESCRIPTIONS, Category, Expense

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
