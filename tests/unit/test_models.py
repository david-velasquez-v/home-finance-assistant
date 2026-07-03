from datetime import date
from decimal import Decimal

import pytest

from expenses.models import Category, Expense, StatementTransaction


def test_expense_serialization(sample_expense):
    assert sample_expense.fecha == date(2026, 6, 12)
    assert sample_expense.descripcion == "Carulla"
    assert sample_expense.categoria == Category.MERCADO
    assert sample_expense.valor == Decimal("45000")
    assert sample_expense.pagador == "Daniela"


def test_expense_no_category(sample_expense_no_category):
    assert sample_expense_no_category.categoria is None


def test_expense_invalid_pagador():
    with pytest.raises(Exception):
        Expense(
            fecha=date(2026, 6, 12),
            descripcion="Test",
            valor=Decimal("1000"),
            pagador="Carlos",  # ty: ignore -- intentionally invalid; tests runtime validation
        )


def test_category_values():
    assert Category.MERCADO.value == "Mercado"
    assert Category.RANDOM_50_50.value == "Random 50/50"
    assert len(Category) == 11


def test_statement_transaction(sample_transaction):
    assert sample_transaction.fecha == date(2026, 6, 10)
    assert sample_transaction.valor == Decimal("123450")
