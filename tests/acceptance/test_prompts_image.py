"""Receipt-image acceptance tests.

Fixture filename convention: `{descripcion_substring}_{valor}_{category_slug}.{ext}`
e.g. `exito_16200_mercado.jpeg`, `peaje_13200_viajes.jpeg`. `category_slug` matches
`Category.value` case-insensitively (single-word categories only for now).

For each receipt we exercise three scenarios:
    A. Sent by David, no caption
       → pagador defaults to David; categoria must be the filename category OR None
         (the LLM is allowed to say "I don't know" rather than guess).
    B. Sent by David, caption "Pagó Daniela"
       → pagador must be Daniela — the caption overrides the sender.
    C. Sent by Daniela, caption forcing a specific category
       → categoria must match the caption, not the filename.
"""
from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path

import instructor
import pytest

from expenses.models import Category, Pagador
from expenses.receipts.llm import parse_image


def _fold(text: str) -> str:
    """Strip accents and lowercase, so 'Éxito' matches 'exito' from a filename slug."""
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii").lower()

pytestmark = pytest.mark.acceptance

_FIXTURES_DIR = Path(__file__).parent / "fixtures" / "receipts"
_RECEIPT_GLOBS = ("*.jpg", "*.jpeg", "*.png")


def _discover() -> list[Path]:
    if not _FIXTURES_DIR.exists():
        return []
    return sorted(p for pattern in _RECEIPT_GLOBS for p in _FIXTURES_DIR.glob(pattern))


_RECEIPTS = _discover()


@dataclass(frozen=True)
class _Expected:
    descripcion_substring: str
    valor: Decimal
    filename_categoria: Category | None


def _parse_filename(receipt: Path) -> _Expected:
    parts = receipt.stem.split("_", 2)
    assert len(parts) == 3, f"unexpected filename shape: {receipt.name}"
    substring, valor_str, slug = parts
    categoria = next(
        (c for c in Category if c.value.lower() == slug.lower()), None
    )
    return _Expected(substring, Decimal(valor_str), categoria)


@dataclass(frozen=True)
class _Scenario:
    scenario_id: str
    sender: Pagador
    caption: str | None
    expected_pagador: Pagador
    expected_categoria_override: Category | None


_SCENARIOS: list[_Scenario] = [
    _Scenario(
        scenario_id="sender-david-no-caption",
        sender="David",
        caption=None,
        expected_pagador="David",
        expected_categoria_override=None,
    ),
    _Scenario(
        scenario_id="sender-david-caption-daniela-paid",
        sender="David",
        caption="Pagó Daniela",
        expected_pagador="Daniela",
        expected_categoria_override=None,
    ),
    _Scenario(
        scenario_id="sender-daniela-caption-forces-entretenimiento",
        sender="Daniela",
        caption="Categoriza esto como Entretenimiento",
        expected_pagador="Daniela",
        expected_categoria_override=Category.ENTRETENIMIENTO,
    ),
]


def _cases() -> list[tuple[Path, _Scenario]]:
    return [(r, s) for r in _RECEIPTS for s in _SCENARIOS]


def _case_id(value: object) -> str:
    if isinstance(value, Path):
        return value.name
    if isinstance(value, _Scenario):
        return value.scenario_id
    return str(value)


@pytest.mark.skipif(not _RECEIPTS, reason="no receipt fixtures in fixtures/receipts/")
@pytest.mark.parametrize("receipt_path,scenario", _cases(), ids=_case_id)
def test_parse_image(
    receipt_path: Path, scenario: _Scenario, client: instructor.Instructor
) -> None:
    expected = _parse_filename(receipt_path)
    sent_at = datetime(2026, 6, 12, 12, 0)

    result = parse_image(
        image_bytes=receipt_path.read_bytes(),
        sender=scenario.sender,
        sent_at=sent_at,
        client=client,
        caption=scenario.caption,
    )

    assert result is not None, f"expected an expense, got None for {receipt_path.name}"
    assert result.valor == expected.valor
    assert result.pagador == scenario.expected_pagador
    assert _fold(expected.descripcion_substring) in _fold(result.descripcion)

    if scenario.expected_categoria_override is not None:
        assert result.categoria == scenario.expected_categoria_override
    else:
        assert result.categoria in (expected.filename_categoria, None), (
            f"expected {expected.filename_categoria} or None, got {result.categoria}"
        )
