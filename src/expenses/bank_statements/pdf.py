import io

import pdfplumber

# Above this many `(cid:XX)` tokens the extracted text is treated as gibberish
# and the caller should fall back to the multimodal path. Started life as the
# inline heuristic in tests/acceptance/test_prompts_statement.py.
CID_GIBBERISH_THRESHOLD = 20


def extract_pdf_text(pdf_bytes: bytes) -> str:
    # KNOWN LIMITATION: PDFs whose embedded fonts lack a ToUnicode CMap (e.g. Wise
    # statements) come back as `(cid:XX)` gibberish. pdfminer/pymupdf hit the same
    # wall since the mapping isn't in the file. When that happens, callers should
    # fall back to the multimodal path (see bank_statements/multimodal.py), which
    # sends the PDF straight to a multimodal LLM as a document input. Use
    # `text_is_unusable` below to detect the condition.
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        return "\n".join(page.extract_text() or "" for page in pdf.pages)


def text_is_unusable(pdf_text: str) -> bool:
    """True when extracted text is empty or dominated by `(cid:XX)` gibberish.

    Statements whose embedded fonts lack a ToUnicode CMap (e.g. Wise) extract as
    `(cid:XX)` tokens instead of readable characters; those must be parsed via
    the multimodal path instead of `parse_statement`.
    """
    return (
        not pdf_text.strip()
        or pdf_text.count("(cid:") > CID_GIBBERISH_THRESHOLD
    )
