from datetime import date, datetime
from unittest.mock import MagicMock

from expenses.external.sheets.adapter import SheetAdapter
from expenses.models import LastUpdatedState


def _make_adapter(
    expenses_rows: list[list] | None = None,
    state_rows: list[list] | None = None,
) -> tuple[SheetAdapter, MagicMock, MagicMock]:
    expenses = MagicMock()
    expenses.get_all_values.return_value = expenses_rows or []
    state = MagicMock()
    state.get_all_values.return_value = state_rows or []
    return SheetAdapter(expenses=expenses, state=state), expenses, state


def test_append_writes_correct_row(sample_expense):
    adapter, expenses, _ = _make_adapter()
    # Simulate a sheet with header + 3 data rows in column A → next row is 5.
    expenses.col_values.return_value = ["Fecha", "d1", "d2", "d3"]
    adapter.append(expense=sample_expense)

    expenses.update.assert_called_once()
    kwargs = expenses.update.call_args.kwargs
    assert kwargs["range_name"] == "A5:E5"
    values = kwargs["values"][0]
    assert values[0] == "2026-06-12"
    assert values[1] == "Carulla"
    assert values[2] == "Mercado"
    assert values[3] == "45000"
    assert values[4] == "Daniela"


def test_append_no_category(sample_expense_no_category):
    adapter, expenses, _ = _make_adapter()
    expenses.col_values.return_value = ["Fecha"]  # only the header → next row is 2
    adapter.append(expense=sample_expense_no_category)

    kwargs = expenses.update.call_args.kwargs
    assert kwargs["range_name"] == "A2:E2"
    values = kwargs["values"][0]
    assert values[2] == ""


def test_read_expenses_filters_by_date():
    rows = [
        ["Fecha", "Descripcion", "Categoria", "Valor", "Pagador"],
        ["2026-06-01", "Carulla", "Mercado", "45000", "Daniela"],
        ["2026-06-15", "Netflix", "Entretenimiento", "52900", "David"],
        ["2026-07-01", "Jumbo", "Mercado", "30000", "David"],
    ]
    adapter, _, _ = _make_adapter(expenses_rows=rows)
    result = adapter.read_expenses(since=date(2026, 6, 1), until=date(2026, 6, 30))

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
    adapter, _, _ = _make_adapter(expenses_rows=rows)
    result = adapter.read_expenses(
        since=date(2026, 6, 1), until=date(2026, 6, 30), pagador="David"
    )

    assert len(result) == 2
    assert all(e.pagador == "David" for e in result)


def test_read_expenses_no_pagador_filter():
    rows = [
        ["Fecha", "Descripcion", "Categoria", "Valor", "Pagador"],
        ["2026-06-10", "Carulla", "Mercado", "45000", "Daniela"],
        ["2026-06-10", "Jumbo", "Mercado", "50000", "David"],
    ]
    adapter, _, _ = _make_adapter(expenses_rows=rows)
    result = adapter.read_expenses(since=date(2026, 6, 1), until=date(2026, 6, 30))

    assert len(result) == 2


def test_read_expenses_skips_invalid_rows():
    rows = [
        ["Fecha", "Descripcion", "Categoria", "Valor", "Pagador"],
        ["not-a-date", "Bad row", "", "0", "David"],
        ["2026-06-10", "Good row", "Mercado", "10000", "David"],
    ]
    adapter, _, _ = _make_adapter(expenses_rows=rows)
    result = adapter.read_expenses(since=date(2026, 6, 1), until=date(2026, 6, 30))

    assert len(result) == 1
    assert result[0].descripcion == "Good row"


def test_read_expenses_handles_missing_categoria():
    rows = [
        ["Fecha", "Descripcion", "Categoria", "Valor", "Pagador"],
        ["2026-06-10", "Gasolina", "", "80000", "David"],
    ]
    adapter, _, _ = _make_adapter(expenses_rows=rows)
    result = adapter.read_expenses(since=date(2026, 6, 1), until=date(2026, 6, 30))

    assert result[0].categoria is None


def test_load_state_empty_returns_defaults():
    adapter, _, _ = _make_adapter()
    state = adapter.load_state()
    assert state.last_update_id == 0
    assert state.last_run is None


def test_load_state_reads_values():
    rows = [
        ["last_update_id", "12345"],
        ["last_run", "2026-07-03T10:00:00"],
    ]
    adapter, _, _ = _make_adapter(state_rows=rows)
    state = adapter.load_state()
    assert state.last_update_id == 12345
    assert state.last_run == datetime(2026, 7, 3, 10, 0, 0)


def test_save_state_writes_range():
    adapter, _, state_ws = _make_adapter()
    adapter.save_state(
        state=LastUpdatedState(
            last_update_id=99, last_run=datetime(2026, 7, 3, 10, 0, 0)
        )
    )

    state_ws.update.assert_called_once()
    kwargs = state_ws.update.call_args.kwargs
    assert kwargs["range_name"] == "A1:B2"
    assert kwargs["values"] == [
        ["last_update_id", "99"],
        ["last_run", "2026-07-03T10:00:00"],
    ]


def test_save_state_null_last_run():
    adapter, _, state_ws = _make_adapter()
    adapter.save_state(state=LastUpdatedState(last_update_id=1, last_run=None))

    values = state_ws.update.call_args.kwargs["values"]
    assert values[1] == ["last_run", ""]
