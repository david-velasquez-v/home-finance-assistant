"""Bank-statement PDF acceptance tests.

For every `*.pdf` in `fixtures/statements/`, expect a companion
`<name>.expected.json` with this shape:

    {
        "expected_count": 12,                     # int (exact) OR [min, max] range
        "period_start": "2026-05-01",
        "period_end":   "2026-05-31",
        "expected_transactions": [
            {"descripcion_substring": "araujo",   "valor": "1500000"},
            {"descripcion_substring": "farmatodo", "valor": "77500"}
        ]
    }

Each entry in `expected_transactions` asserts that the LLM's output contains a
transaction whose `descripcion` contains the substring (case-insensitive) AND
whose `valor` matches exactly. This mirrors the (substring, valor) shape used
by `test_reconciliation.py`.

`expected_count` accepts a range because statement extraction may include or
exclude edge cases (small bank fees, borderline reversals) run-to-run.

Extraction goes through `extract_transactions`, which uses pdfplumber text when
it's readable and falls back to the multimodal LLM path for PDFs whose embedded
fonts produce `(cid:XX)` gibberish (e.g. Wise). A fixture is skipped only when
it has no `.expected.json` sidecar yet.
"""
from __future__ import annotations

import json
import unicodedata
from datetime import date
from decimal import Decimal
from pathlib import Path

import instructor
import pytest

from expenses.bank_statements.multimodal import extract_transactions
from expenses.models import StatementTransaction

pytestmark = pytest.mark.acceptance

_FIXTURES_DIR = Path(__file__).parent / "fixtures" / "statements"


def _discover() -> list[Path]:
    if not _FIXTURES_DIR.exists():
        return []
    return sorted(_FIXTURES_DIR.glob("*.pdf"))


_STATEMENTS = _discover()


def _norm(text: str) -> str:
    """Comparison key ignoring case, accents, whitespace and punctuation.

    Merchant-name matching should not care about capitalization, diacritics, or
    spacing/punctuation (e.g. "Éxito" vs "Exito", "Torre Alta 903" vs
    "Torrealta 903", "Café San Alberto" vs "cafe san alberto casa"). Only the
    letters and digits matter — so an objectively wrong name (e.g. "Cabaña y
    Cola" vs "Cabeza y Cola") still fails to match.
    """
    decomposed = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in decomposed if c.isalnum())


def _contains(txns: list[StatementTransaction], substring: str, valor: Decimal) -> bool:
    needle = _norm(substring)
    return any(needle in _norm(t.descripcion) and t.valor == valor for t in txns)


@pytest.mark.skipif(not _STATEMENTS, reason="no statement fixtures in fixtures/statements/")
@pytest.mark.parametrize("pdf_path", _STATEMENTS, ids=lambda p: p.name)
def test_parse_statement(pdf_path: Path, client: instructor.Instructor) -> None:
    expected_path = pdf_path.with_name(pdf_path.stem + ".expected.json")
    if not expected_path.exists():
        pytest.skip(f"no expectation file for {pdf_path.name}")

    expected = json.loads(expected_path.read_text())

    txns = extract_transactions(pdf_bytes=pdf_path.read_bytes(), client=client)

    expected_count = expected["expected_count"]
    if isinstance(expected_count, list):
        assert expected_count[0] <= len(txns) <= expected_count[1], (
            f"txn count {len(txns)} outside expected range {expected_count}"
        )
    else:
        assert len(txns) == expected_count

    for entry in expected["expected_transactions"]:
        substring = entry["descripcion_substring"]
        valor = Decimal(str(entry["valor"]))
        assert _contains(txns, substring, valor), (
            f"expected ({substring!r}, {valor}) not found in "
            f"{[(t.descripcion, t.valor) for t in txns]}"
        )

    period_start = date.fromisoformat(expected["period_start"])
    period_end = date.fromisoformat(expected["period_end"])
    for t in txns:
        assert period_start <= t.fecha <= period_end, (
            f"transaction {t} falls outside period {period_start}..{period_end}"
        )
