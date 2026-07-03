from dataclasses import dataclass
from datetime import datetime
from typing import Any

from expenses.config import Settings
from expenses.models import Pagador


@dataclass
class TextMessage:
    chat_id: int
    message_id: int
    sender_name: Pagador
    sent_at: datetime
    text: str


@dataclass
class PhotoMessage:
    chat_id: int
    message_id: int
    sender_name: Pagador
    sent_at: datetime
    file_id: str
    caption: str | None = None


@dataclass
class DocumentMessage:
    chat_id: int
    message_id: int
    sender_name: Pagador
    sent_at: datetime
    file_id: str
    mime_type: str


type IncomingMessage = TextMessage | PhotoMessage | DocumentMessage


def classify_update(update: dict[str, Any], config: Settings) -> IncomingMessage | None:
    msg = update.get("message")
    if not msg:
        return None

    sender_id: int = msg["from"]["id"]
    sender_name: Pagador
    if sender_id == config.telegram_user_david:
        sender_name = "David"
    elif sender_id == config.telegram_user_daniela:
        sender_name = "Daniela"
    else:
        return None

    chat_id: int = msg["chat"]["id"]
    message_id: int = msg["message_id"]
    sent_at = datetime.fromtimestamp(msg["date"])

    if "text" in msg:
        return TextMessage(
            chat_id=chat_id,
            message_id=message_id,
            sender_name=sender_name,
            sent_at=sent_at,
            text=msg["text"],
        )

    if "photo" in msg:
        largest = max(msg["photo"], key=lambda p: p.get("file_size", 0))
        return PhotoMessage(
            chat_id=chat_id,
            message_id=message_id,
            sender_name=sender_name,
            sent_at=sent_at,
            file_id=largest["file_id"],
            caption=msg.get("caption"),
        )

    if "document" in msg:
        doc = msg["document"]
        mime = doc.get("mime_type", "")
        if "pdf" in mime:
            return DocumentMessage(
                chat_id=chat_id,
                message_id=message_id,
                sender_name=sender_name,
                sent_at=sent_at,
                file_id=doc["file_id"],
                mime_type=mime,
            )

    return None
