from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock

from expenses.models import Category, Expense
from expenses.external.sheets.writer import SheetWriter


def _make_sheet(rows: list[list]) -> SheetWriter:
    worksheet = MagicMock()
    worksheet.get_all_values.return_value = rows
    return SheetWriter(worksheet=worksheet)


def test_append_writes_correct_row(sample_expense):
    worksheet = MagicMock()
    sheet = SheetWriter(worksheet=worksheet)
    sheet.append(expense=sample_expense)

    worksheet.append_row.assert_called_once()
    values = worksheet.append_row.call_args.kwargs["values"]
    assert values[0] == "2026-06-12"
    assert values[1] == "Carulla"
    assert values[2] == "Mercado"
    assert values[3] == "45000"
    assert values[4] == "Daniela"


def test_append_no_category(sample_expense_no_category):
    worksheet = MagicMock()
    sheet = SheetWriter(worksheet=worksheet)
    sheet.append(expense=sample_expense_no_category)

    values = worksheet.append_row.call_args.kwargs["values"]
    assert values[2] == ""


def test_read_expenses_filters_by_date():
    rows = [
        ["Fecha", "Descripcion", "Categoria", "Valor", "Pagador"],
        ["2026-06-01", "Carulla", "Mercado", "45000", "Daniela"],
        ["2026-06-15", "Netflix", "Entretenimiento", "52900", "David"],
        ["2026-07-01", "Jumbo", "Mercado", "30000", "David"],
    ]
    sheet = _make_sheet(rows)
    result = sheet.read_expenses(since=date(2026, 6, 1), until=date(2026, 6, 30))

    assert len(result) == 2
    assert result[0].descripcion == "Carulla"
    assert result[1].descripcion == "Netflix"


def test_read_expenses_filters_by_pagador():
    rows = [
        ["Fecha", "Descripcion", "Categoria", "Valor", "Pagador"],
        ["2026-06-10", "Carulla", "Mercado", "45000", "Daniela"],
        ["2026-06-10", "Jumbo", "Mercado", "50000", "David"],
        ["2026-06-11", "Netflix", "Entretenimiento", "52900", "David"],
    ]
    sheet = _make_sheet(rows)
    result = sheet.read_expenses(since=date(2026, 6, 1), until=date(2026, 6, 30), pagador="David")

    assert len(result) == 2
    assert all(e.pagador == "David" for e in result)


def test_read_expenses_no_pagador_filter():
    rows = [
        ["Fecha", "Descripcion", "Categoria", "Valor", "Pagador"],
        ["2026-06-10", "Carulla", "Mercado", "45000", "Daniela"],
        ["2026-06-10", "Jumbo", "Mercado", "50000", "David"],
    ]
    sheet = _make_sheet(rows)
    result = sheet.read_expenses(since=date(2026, 6, 1), until=date(2026, 6, 30))

    assert len(result) == 2


def test_read_expenses_skips_invalid_rows():
    rows = [
        ["Fecha", "Descripcion", "Categoria", "Valor", "Pagador"],
        ["not-a-date", "Bad row", "", "0", "David"],
        ["2026-06-10", "Good row", "Mercado", "10000", "David"],
    ]
    sheet = _make_sheet(rows)
    result = sheet.read_expenses(since=date(2026, 6, 1), until=date(2026, 6, 30))

    assert len(result) == 1
    assert result[0].descripcion == "Good row"


def test_read_expenses_handles_missing_categoria():
    rows = [
        ["Fecha", "Descripcion", "Categoria", "Valor", "Pagador"],
        ["2026-06-10", "Gasolina", "", "80000", "David"],
    ]
    sheet = _make_sheet(rows)
    result = sheet.read_expenses(since=date(2026, 6, 1), until=date(2026, 6, 30))

    assert result[0].categoria is None
