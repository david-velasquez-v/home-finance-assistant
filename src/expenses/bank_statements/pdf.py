import io

import pdfplumber


def extract_pdf_text(pdf_bytes: bytes) -> str:
    # KNOWN LIMITATION: PDFs whose embedded fonts lack a ToUnicode CMap (e.g. Wise
    # statements) come back as `(cid:XX)` gibberish. pdfminer/pymupdf hit the same
    # wall since the mapping isn't in the file. Planned fix: bypass text extraction
    # and send the PDF directly to a multimodal LLM as a document input (Claude,
    # OpenAI and Gemini all support this). Tracked as a follow-up — will live
    # alongside this function in the bank_statements module.
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        return "\n".join(page.extract_text() or "" for page in pdf.pages)
