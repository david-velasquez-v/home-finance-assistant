"""Reconciliation acceptance tests.

Hand-curated cases live in `_CASES` below. Each case references a PDF in
`fixtures/statements/` and lists what's already in the sheet. Reconciliation
must return ONLY the transactions in the statement that are not represented in
the sheet — accounting for commercial-vs-legal name differences, ±2 day fuzz,
and so on.

Add new cases by appending to `_CASES`. The PDF must already exist under
`fixtures/statements/`; the test skips cases whose PDF is missing.

**Expectations use (substring, valor) pairs** rather than substring-only, so
the same merchant appearing both matched and unmatched at different amounts
can be disambiguated (e.g. Rappi at $43.100 was recorded, Rappi at $66.300
wasn't).
"""
from __future__ import annotations

import unicodedata
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from pathlib import Path

import instructor
import pytest

from expenses.bank_statements import llm as bank_llm
from expenses.bank_statements.multimodal import extract_transactions
from expenses.models import Expense

pytestmark = pytest.mark.acceptance

_STATEMENTS_DIR = Path(__file__).parent / "fixtures" / "statements"


@dataclass(frozen=True)
class _Expectation:
    """One statement transaction identified by a lowercase substring + amount."""
    descripcion_substring: str
    valor: Decimal


@dataclass(frozen=True)
class _ReconcileCase:
    name: str
    pdf_filename: str  # under fixtures/statements/
    sender: str  # "David" or "Daniela"
    sheet_entries: list[Expense]
    # Transactions the LLM must have identified as matched (must NOT appear in
    # the returned unmatched list).
    expected_matched: list[_Expectation] = field(default_factory=list)
    # Transactions the LLM must have flagged as unmatched (MUST appear in the
    # returned unmatched list).
    expected_unmatched: list[_Expectation] = field(default_factory=list)


# --- BBVA May 2026 (David's savings account) ---
# Rich case: real David sheet entries drive real matches. Tests:
#   - payment-processor prefixes ("RAPPI COLOMBIA*DL" → "Almuerzo Jueves")
#   - PSE-to-legal-name ("PAGO POR PSE A ARAUJO Y SEGOVI" → "Arriendo")
#   - Bre-B transfers used to pay real expenses ("ENVIO POR BRE-B" 05-20 → "Cita Psicologia")
#   - same merchant appearing both matched and unmatched at different amounts (Rappi, Oxxo, Farmatodo)
# BBVA row #3087 ($3.884.691,02 to NU) is the credit-card payment and is expected UNMATCHED —
# it's an internal money-move, not a recorded expense in the sheet.
_bbva_sheet = [
    Expense(fecha=date(2026, 5, 2),  descripcion="Bebidas almuerzo",         valor=Decimal("4940"),    pagador="David"),
    Expense(fecha=date(2026, 5, 2),  descripcion="MT Cocina",                valor=Decimal("103000"),  pagador="David"),
    Expense(fecha=date(2026, 5, 2),  descripcion="Arriendo",                 valor=Decimal("1500000"), pagador="David"),
    Expense(fecha=date(2026, 5, 11), descripcion="Farmatodo - David",        valor=Decimal("77500"),   pagador="David"),
    Expense(fecha=date(2026, 5, 11), descripcion="Cena Lunes (BBC)",         valor=Decimal("49680"),   pagador="David"),
    Expense(fecha=date(2026, 5, 12), descripcion="D1 (Agua y Paquetico)",    valor=Decimal("8950"),    pagador="David"),
    Expense(fecha=date(2026, 5, 14), descripcion="Almuerzo Jueves",          valor=Decimal("43100"),   pagador="David"),
    Expense(fecha=date(2026, 5, 14), descripcion="Oxxo",                     valor=Decimal("2100"),    pagador="David"),
    Expense(fecha=date(2026, 5, 16), descripcion="Desayuno Sabado",          valor=Decimal("41200"),   pagador="David"),
    Expense(fecha=date(2026, 5, 16), descripcion="Cafe Nati",                valor=Decimal("67700"),   pagador="David"),
    Expense(fecha=date(2026, 5, 16), descripcion="Postresito Mama",          valor=Decimal("57900"),   pagador="David"),
    Expense(fecha=date(2026, 5, 18), descripcion="Afinia",                   valor=Decimal("268240"),  pagador="David"),
    Expense(fecha=date(2026, 5, 20), descripcion="Cita Individual Psicologia", valor=Decimal("180000"), pagador="David"),
    Expense(fecha=date(2026, 5, 20), descripcion="Perro Caliente",           valor=Decimal("33500"),   pagador="David"),
    Expense(fecha=date(2026, 5, 28), descripcion="Rappi (Corral)",           valor=Decimal("51400"),   pagador="David"),
]

_bbva_case = _ReconcileCase(
    name="bbva_may_2026_david",
    pdf_filename="Extracto BBVA Mayo.pdf",
    sender="David",
    sheet_entries=_bbva_sheet,
    expected_matched=[
        _Expectation("euro nuestro",  Decimal("4940")),     # → Bebidas almuerzo
        _Expectation("bre-b",         Decimal("103000")),   # → MT Cocina (transfer for restaurant)
        _Expectation("araujo",        Decimal("1500000")),  # → Arriendo (landlord via PSE)
        _Expectation("farmatodo",     Decimal("77500")),    # → Farmatodo - David
        _Expectation("bbc",           Decimal("49680")),    # → Cena Lunes (BBC)
        _Expectation("d1",            Decimal("8950")),     # → D1 (Agua y Paquetico)
        _Expectation("rappi",         Decimal("43100")),    # → Almuerzo Jueves
        _Expectation("oxxo",          Decimal("2100")),     # → Oxxo (05-14, not the 05-06 $4.450 one)
        _Expectation("rappi",         Decimal("41200")),    # → Desayuno Sabado
        _Expectation("rappi",         Decimal("67700")),    # → Cafe Nati
        _Expectation("isabella",      Decimal("57900")),    # → Postresito Mama
        _Expectation("fideicomisos",  Decimal("268240")),   # → Afinia (utility via fiduciary)
        _Expectation("bre-b",         Decimal("180000")),   # → Cita Psicologia (transfer)
        _Expectation("bre-b",         Decimal("33500")),    # → Perro Caliente
        _Expectation("rappi",         Decimal("51400")),    # → Rappi (Corral)
    ],
    expected_unmatched=[
        _Expectation("tiendas ara",   Decimal("4320")),
        _Expectation("tomo",          Decimal("14300")),
        _Expectation("rappi",         Decimal("66300")),    # 05-04, not in sheet
        _Expectation("rappi",         Decimal("21800")),    # 05-04, not in sheet
        _Expectation("farmatodo",     Decimal("2450")),     # 05-05, not in sheet
        _Expectation("oxxo",          Decimal("4450")),     # 05-06, not in sheet
        _Expectation("primax",        Decimal("24077")),
        _Expectation("smart fit",     Decimal("109900")),
        _Expectation("compensar",     Decimal("855000")),
        _Expectation("nu",            Decimal("3884691.02")),  # credit-card payment — internal move
    ],
)


# --- NU May 2026 (David's credit card) ---
# NU has many small charges that in the real sheet were rolled up into the
# "Medellin" trip lump-sum. That would defeat a real-sheet reconciliation, so
# this case uses hand-crafted `sheet_entries` designed to test specific matcher
# behaviors:
#   - commercial↔legal-name matching ("Uber Rides" ↔ "Taxi Aeropuerto David")
#   - ±2 day fuzz  ("Compania de Medicina P" 05-06 ↔ "EPS Sura" 05-08)
#   - exact amount+date on a chain merchant ("Carulla Sao Paulo" 05-03 ↔ "Mercado Carulla" 05-03)
_nu_sheet = [
    # Should match Uber Rides $52.218 on 05-16 (commercial name in statement vs semantic label in sheet)
    Expense(fecha=date(2026, 5, 16), descripcion="Taxi Aeropuerto David",
            valor=Decimal("52218"), pagador="David"),
    # Should match Carulla Sao Paulo $67.300 on 05-03 (chain merchant, same date+amount)
    Expense(fecha=date(2026, 5, 3),  descripcion="Mercado Carulla",
            valor=Decimal("67300"), pagador="David"),
    # Should match Compania de Medicina P $483.420 on 05-06 within ±2 day fuzz
    Expense(fecha=date(2026, 5, 8),  descripcion="EPS Sura",
            valor=Decimal("483420"), pagador="David"),
]

_nu_case = _ReconcileCase(
    name="nu_may_2026_david_curated",
    pdf_filename="Extracto NU Mayo.pdf",
    sender="David",
    sheet_entries=_nu_sheet,
    expected_matched=[
        _Expectation("uber",     Decimal("52218")),
        _Expectation("carulla",  Decimal("67300")),
        _Expectation("medicina", Decimal("483420")),
    ],
    expected_unmatched=[
        _Expectation("apple",   Decimal("3900")),    # Apple.com/Bill 05-11
        _Expectation("renting", Decimal("20000")),   # Renting Colombia 05-09
        _Expectation("uber",    Decimal("16846")),   # a small Uber ride not in sheet
        _Expectation("carulla", Decimal("14500")),   # Carulla $14.500 on 05-03 (different from the $67.300 match)
        _Expectation("carulla", Decimal("20800")),   # Carulla $20.800 on 05-06
    ],
)


# --- Wise May 2026 (David's USD account, COP card purchases) ---
# Exercises the multimodal extraction path (pdfplumber can't read this PDF) end
# to end through reconciliation. `sheet_entries` are hand-crafted to hit:
#   - exact date+amount match on a distinctive merchant ("Alambique" 05-09)
#   - commercial-name match ("Café Juan Valdez" in sheet ↔ "Juan Valdez" 05-15)
#   - ±2 day fuzz ("Medipiel" recorded 05-04 ↔ statement 05-03)
# The amounts are the ORIGINAL COP amounts shown in each transaction line, not
# the USD settlement — the USD-only rows (transfers, fees, subscriptions) are
# dropped at extraction and never reach reconciliation.
_wise_sheet = [
    Expense(fecha=date(2026, 5, 9),  descripcion="Alambique",          valor=Decimal("452333"), pagador="David"),
    Expense(fecha=date(2026, 5, 10), descripcion="Frisby",             valor=Decimal("91400"),  pagador="David"),
    Expense(fecha=date(2026, 5, 15), descripcion="Café Juan Valdez",   valor=Decimal("25000"),  pagador="David"),
    Expense(fecha=date(2026, 5, 29), descripcion="Éxito",              valor=Decimal("8750"),   pagador="David"),
    Expense(fecha=date(2026, 5, 4),  descripcion="Medipiel",           valor=Decimal("259430"), pagador="David"),
]

_wise_case = _ReconcileCase(
    name="wise_may_2026_david_curated",
    pdf_filename="Extracto Wise Mayo.pdf",
    sender="David",
    sheet_entries=_wise_sheet,
    expected_matched=[
        _Expectation("alambique",     Decimal("452333")),
        _Expectation("frisby",        Decimal("91400")),
        _Expectation("juan valdez",   Decimal("25000")),
        _Expectation("exito",         Decimal("8750")),
        _Expectation("medipiel viva", Decimal("259430")),
    ],
    expected_unmatched=[
        _Expectation("mamasita",      Decimal("260037")),
        _Expectation("cabeza y cola", Decimal("136401")),
        _Expectation("alto bistro",   Decimal("156103")),
        _Expectation("market pasteur", Decimal("425")),
    ],
)


_CASES: list[_ReconcileCase] = [_bbva_case, _nu_case, _wise_case]


def _norm(text: str) -> str:
    """Comparison key ignoring case, accents, whitespace and punctuation.

    Same rationale as in test_prompts_statement.py: merchant matching ignores
    capitalization/diacritics/spacing but an objectively wrong name still fails.
    """
    decomposed = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in decomposed if c.isalnum())


def _find_match(exp: _Expectation, unmatched_pairs: list[tuple[str, Decimal]]) -> bool:
    needle = _norm(exp.descripcion_substring)
    return any(
        exp.valor == valor and needle in desc for desc, valor in unmatched_pairs
    )


@pytest.mark.parametrize("case", _CASES, ids=lambda c: c.name)
def test_reconcile(case: _ReconcileCase, client: instructor.Instructor) -> None:
    pdf_path = _STATEMENTS_DIR / case.pdf_filename
    if not pdf_path.exists():
        pytest.skip(f"missing statement PDF {case.pdf_filename}")

    txns = extract_transactions(pdf_bytes=pdf_path.read_bytes(), client=client)
    unmatched = bank_llm.reconcile(
        txns=txns,
        sheet_entries=case.sheet_entries,
        client=client,
    )

    unmatched_pairs = [(_norm(t.descripcion), t.valor) for t in unmatched]

    for exp in case.expected_matched:
        assert not _find_match(exp, unmatched_pairs), (
            f"{exp} should have been matched but appears in unmatched: {unmatched_pairs}"
        )

    for exp in case.expected_unmatched:
        assert _find_match(exp, unmatched_pairs), (
            f"expected unmatched {exp} not found in unmatched: {unmatched_pairs}"
        )
