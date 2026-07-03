import uuid
from datetime import date, datetime
from decimal import Decimal

import gspread
import pytest

from expenses.config import Settings
from expenses.external.sheets.adapter import SheetAdapter
from expenses.external.sheets.client import SheetsClient
from expenses.models import Category, Expense, LastUpdatedState

pytestmark = pytest.mark.acceptance


_WIDE_SINCE = date(2000, 1, 1)
_WIDE_UNTIL = date(2100, 1, 1)


def _build_adapter(client: SheetsClient, settings: Settings) -> SheetAdapter:
    return SheetAdapter.open(
        client=client,
        expenses_sheet_name=settings.google_sheet_name,
        state_sheet_name=settings.state_sheet_name,
    )


def _unique_descripcion() -> str:
    return f"acceptance-test-{uuid.uuid4().hex[:12]}"


# -------- reads against seeded data --------

def test_reads_return_typed_and_filtered_data(
    sheets_client: SheetsClient,
    acceptance_settings: Settings,
    clean_state_tab: None,
) -> None:
    adapter = _build_adapter(sheets_client, acceptance_settings)
    all_ = adapter.read_expenses(since=_WIDE_SINCE, until=_WIDE_UNTIL)
    david = adapter.read_expenses(since=_WIDE_SINCE, until=_WIDE_UNTIL, pagador="David")
    daniela = adapter.read_expenses(since=_WIDE_SINCE, until=_WIDE_UNTIL, pagador="Daniela")

    assert all_, "expected the test sheet to have at least one seeded row"

    # typed shape on every row
    for e in all_:
        assert isinstance(e.fecha, date)
        assert isinstance(e.valor, Decimal)
        assert e.valor > 0
        assert e.pagador in ("David", "Daniela")
        assert e.categoria is None or isinstance(e.categoria, Category)

    # pagador filter is a subset and partitions the whole
    assert all(e.pagador == "David" for e in david)
    assert all(e.pagador == "Daniela" for e in daniela)
    assert len(david) + len(daniela) == len(all_)

    # date filter is a subset within bounds
    min_date = min(e.fecha for e in all_)
    max_date = max(e.fecha for e in all_)
    narrow = adapter.read_expenses(since=min_date, until=max_date)
    assert len(narrow) <= len(all_)
    for e in narrow:
        assert min_date <= e.fecha <= max_date


# -------- append behavior --------

def test_append_writes_correct_columns(
    sheets_client: SheetsClient,
    acceptance_settings: Settings,
    clean_state_tab: None,
    preserve_expenses_tail: gspread.Worksheet,
) -> None:
    adapter = _build_adapter(sheets_client, acceptance_settings)
    tag = _unique_descripcion()
    expected = Expense(
        fecha=date(2026, 6, 12),
        descripcion=tag,
        categoria=Category.MERCADO,
        valor=Decimal("12345"),
        pagador="David",
    )

    adapter.append(expense=expected)
    rows = adapter.read_expenses(since=_WIDE_SINCE, until=_WIDE_UNTIL, pagador="David")
    matches = [e for e in rows if e.descripcion == tag]

    assert len(matches) == 1
    got = matches[0]
    assert got.fecha == expected.fecha
    assert got.descripcion == expected.descripcion
    assert got.categoria == expected.categoria
    assert got.valor == expected.valor
    assert got.pagador == expected.pagador


def test_append_preserves_existing_rows(
    sheets_client: SheetsClient,
    acceptance_settings: Settings,
    clean_state_tab: None,
    preserve_expenses_tail: gspread.Worksheet,
) -> None:
    ws = preserve_expenses_tail
    n_before = len(ws.col_values(1))
    block_before = ws.get(f"A1:E{n_before}")

    adapter = _build_adapter(sheets_client, acceptance_settings)
    tag_a = _unique_descripcion()
    tag_b = _unique_descripcion()
    adapter.append(expense=Expense(
        fecha=date(2026, 1, 1), descripcion=tag_a, valor=Decimal("1"), pagador="David",
    ))
    adapter.append(expense=Expense(
        fecha=date(2026, 1, 2), descripcion=tag_b, valor=Decimal("2"), pagador="Daniela",
    ))

    n_after = len(ws.col_values(1))
    assert n_after == n_before + 2, "column A should have grown by exactly 2 rows"

    block_after = ws.get(f"A1:E{n_before}")
    assert block_after == block_before, "existing A:E block must not shift or mutate"

    new_rows = ws.get(f"A{n_before + 1}:E{n_after}")
    assert [r[1] for r in new_rows] == [tag_a, tag_b], "new rows must land immediately below existing data"


# -------- client provisioning --------

def test_get_or_create_returns_existing_entradas(
    sheets_client: SheetsClient,
    acceptance_settings: Settings,
) -> None:
    ws1 = sheets_client.get_or_create_worksheet(acceptance_settings.google_sheet_name)
    tabs_before = {w.id for w in sheets_client._spreadsheet.worksheets()}
    ws2 = sheets_client.get_or_create_worksheet(acceptance_settings.google_sheet_name)
    tabs_after = {w.id for w in sheets_client._spreadsheet.worksheets()}

    assert ws1.id == ws2.id
    assert tabs_before == tabs_after


# -------- state tab lifecycle --------

def test_open_creates_state_tab_and_round_trip(
    sheets_client: SheetsClient,
    acceptance_settings: Settings,
    clean_state_tab: None,
) -> None:
    # precondition: fixture guarantees _state is absent
    with pytest.raises(gspread.WorksheetNotFound):
        sheets_client._spreadsheet.worksheet(acceptance_settings.state_sheet_name)

    adapter = _build_adapter(sheets_client, acceptance_settings)

    # tab was auto-created and starts with defaults
    sheets_client._spreadsheet.worksheet(acceptance_settings.state_sheet_name)
    defaults = adapter.load_state()
    assert defaults.last_update_id == 0
    assert defaults.last_run is None

    # round-trip: save then load matches
    written = LastUpdatedState(
        last_update_id=999_999_999,
        last_run=datetime(2026, 7, 3, 15, 42, 7),
    )
    adapter.save_state(state=written)
    read = adapter.load_state()
    assert read.last_update_id == written.last_update_id
    assert read.last_run == written.last_run


def test_open_uses_existing_state_tab(
    sheets_client: SheetsClient,
    acceptance_settings: Settings,
    clean_state_tab: None,
) -> None:
    state_ws = sheets_client.get_or_create_worksheet(acceptance_settings.state_sheet_name)
    state_ws.update(
        range_name="A1:B2",
        values=[
            ["last_update_id", "12345"],
            ["last_run", "2026-07-03T10:00:00"],
        ],
    )
    tabs_after_seed = {w.id for w in sheets_client._spreadsheet.worksheets()}

    adapter = _build_adapter(sheets_client, acceptance_settings)
    tabs_after_open = {w.id for w in sheets_client._spreadsheet.worksheets()}

    assert tabs_after_open == tabs_after_seed, "no duplicate state tab should be created"
    state = adapter.load_state()
    assert state.last_update_id == 12345
    assert state.last_run == datetime(2026, 7, 3, 10, 0, 0)
