from datetime import datetime

import instructor
from openai.types.chat import ChatCompletionMessageParam
from pydantic import ValidationError

from expenses.models import Expense, ParsedExpense
from expenses.prompts import TEXT_EXPENSE_SYSTEM


def parse_text(
    text: str,
    sender: str,
    sent_at: datetime,
    client: instructor.Instructor,
) -> Expense | None:
    user_content = f"""\
Message date: {sent_at.date().isoformat()}
Sender: {sender}
Message: {text}"""
    messages: list[ChatCompletionMessageParam] = [
        {"role": "system", "content": TEXT_EXPENSE_SYSTEM},
        {"role": "user", "content": user_content},
    ]
    try:
        result = client.chat.completions.create(
            response_model=ParsedExpense,
            messages=messages,
        )
    except ValidationError:
        return None
    return result.expense
