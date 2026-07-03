from _pytest.mark.structures import MarkDecorator
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

import instructor
import pytest

from expenses.models import Category, Pagador
from expenses.text_messages.llm import parse_text

pytestmark: MarkDecorator = pytest.mark.acceptance


@dataclass(frozen=True)
class _TextCase:
    text: str
    sender: Pagador
    expected_valor: Decimal
    expected_descripcion_substring: str
    acceptable_categorias: tuple[Category | None, ...]  # empty tuple = don't assert
    sent_at: datetime = datetime(2026, 6, 12, 14, 30)


_CASES = [
    _TextCase(
        text="Carulla 45000",
        sender="Daniela",
        expected_valor=Decimal("45000"),
        expected_descripcion_substring="carulla",
        acceptable_categorias=(Category.MERCADO,),
    ),
    _TextCase(
        text="Gasolina 80000",
        sender="David",
        expected_valor=Decimal("80000"),
        expected_descripcion_substring="gasolina",
        acceptable_categorias=(Category.CARRO,),
    ),
    _TextCase(
        text="Netflix 35900",
        sender="David",
        expected_valor=Decimal("35900"),
        expected_descripcion_substring="netflix",
        acceptable_categorias=(Category.ENTRETENIMIENTO,),
    ),
    _TextCase(
        text="Pagué arriendo 2500000",
        sender="David",
        expected_valor=Decimal("2500000"),
        expected_descripcion_substring="arriendo",
        acceptable_categorias=(Category.CASA,),
    ),
    _TextCase(
        text="Almuerzo con compañeros 42000",
        sender="Daniela",
        expected_valor=Decimal("42000"),
        expected_descripcion_substring="almuerzo",
        acceptable_categorias=(),  # ambiguous — Entretenimiento or Random both defensible; don't pin.
    ),
    _TextCase(
        text="Personal 5000",
        sender="David",
        expected_valor=Decimal("5000"),
        expected_descripcion_substring="personal",
        acceptable_categorias=(Category.RANDOM_DAVID,),
    ),
    _TextCase(
        text="Peaje 13200",
        sender="David",
        expected_valor=Decimal("13200"),
        expected_descripcion_substring="peaje",
        # After narrowing Carro to fixed car-ownership costs, the LLM should either
        # place a toll under Viajes or leave it uncategorized. Carro would be wrong.
        acceptable_categorias=(Category.VIAJES, None),
    ),
]


@pytest.mark.parametrize("case", _CASES, ids=lambda c: c.text)
def test_parse_text(case: _TextCase, client: instructor.Instructor) -> None:
    result = parse_text(
        text=case.text,
        sender=case.sender,
        sent_at=case.sent_at,
        client=client,
    )

    assert result is not None, f"expected an expense, got None for {case.text!r}"
    assert result.valor == case.expected_valor
    assert result.pagador == case.sender
    assert result.fecha == case.sent_at.date()
    assert case.expected_descripcion_substring in result.descripcion.lower()
    if case.acceptable_categorias:
        assert result.categoria in case.acceptable_categorias, (
            f"expected one of {case.acceptable_categorias}, got {result.categoria}"
        )


_NOT_EXPENSE_CASES: list[tuple[str, Pagador]] = [
    ("This is a test", "Daniela"),
    ("Hola, cómo estás?", "David"),
    ("¿Cuánto gasté esta semana?", "Daniela"),
]


@pytest.mark.parametrize("text,sender", _NOT_EXPENSE_CASES)
def test_parse_text_not_an_expense(
    text: str, sender: Pagador, client: instructor.Instructor
) -> None:
    result = parse_text(
        text=text,
        sender=sender,
        sent_at=datetime(2026, 6, 12, 14, 30),
        client=client,
    )
    assert result is None, f"expected None, got {result!r} for {text!r}"
