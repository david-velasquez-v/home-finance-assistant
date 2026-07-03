from expenses.telegram_processor import (
    DocumentMessage,
    PhotoMessage,
    TextMessage,
    classify_update,
)


def test_classify_text_from_david(david_text_update, settings):
    msg = classify_update(david_text_update, settings)
    assert isinstance(msg, TextMessage)
    assert msg.sender_name == "David"
    assert msg.text == "Carulla 45000"
    assert msg.chat_id == 111
    assert msg.message_id == 1


def test_classify_photo_from_daniela(daniela_photo_update, settings):
    msg = classify_update(daniela_photo_update, settings)
    assert isinstance(msg, PhotoMessage)
    assert msg.sender_name == "Daniela"
    assert msg.file_id == "large_id"  # largest photo selected
    assert msg.caption is None


def test_classify_photo_with_caption(daniela_photo_update, settings):
    daniela_photo_update["message"]["caption"] = "Pagó David"
    msg = classify_update(daniela_photo_update, settings)
    assert isinstance(msg, PhotoMessage)
    assert msg.caption == "Pagó David"


def test_classify_pdf_document(david_pdf_update, settings):
    msg = classify_update(david_pdf_update, settings)
    assert isinstance(msg, DocumentMessage)
    assert msg.file_id == "pdf_file_id"
    assert "pdf" in msg.mime_type


def test_unknown_sender_ignored(unknown_sender_update, settings):
    msg = classify_update(unknown_sender_update, settings)
    assert msg is None


def test_non_message_update_ignored(settings):
    update = {"update_id": 999, "edited_message": {"text": "edited"}}
    assert classify_update(update, settings) is None
