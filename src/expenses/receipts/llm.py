import base64
from datetime import datetime

import instructor
from openai.types.chat import ChatCompletionMessageParam
from pydantic import ValidationError

from expenses.models import Expense, ParsedExpense
from expenses.prompts import RECEIPT_EXPENSE_SYSTEM


def parse_image(
    image_bytes: bytes,
    sender: str,
    sent_at: datetime,
    client: instructor.Instructor,
    caption: str | None = None,
) -> Expense | None:
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
        {"role": "system", "content": RECEIPT_EXPENSE_SYSTEM},
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
    try:
        result = client.chat.completions.create(
            response_model=ParsedExpense,
            messages=messages,
        )
    except ValidationError:
        return None
    return result.expense
