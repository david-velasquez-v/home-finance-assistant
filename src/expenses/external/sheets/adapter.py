from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import cast

import gspread
from gspread.utils import DateTimeOption, ValueInputOption, ValueRenderOption

from expenses.external.sheets.client import SheetsClient
from expenses.models import Category, Expense, Pagador, LastUpdatedState

_EXPENSE_HEADERS = ["Fecha", "Descripcion", "Categoria", "Valor", "Pagador"]


class SheetAdapter:
    def __init__(
        self,
        expenses: gspread.Worksheet,
        state: gspread.Worksheet,
    ) -> None:
        self._expenses = expenses
        self._state = state

    @classmethod
    def open(
        cls,
        client: SheetsClient,
        expenses_sheet_name: str,
        state_sheet_name: str,
    ) -> "SheetAdapter":
        expenses = client.get_or_create_worksheet(expenses_sheet_name)
        state = client.get_or_create_worksheet(state_sheet_name)
        adapter = cls(expenses=expenses, state=state)
        adapter._ensure_expense_headers()
        return adapter

    def _ensure_expense_headers(self) -> None:
        if not self._expenses.get_all_values():
            self._expenses.append_row(
                values=_EXPENSE_HEADERS,
                value_input_option=ValueInputOption.user_entered,
            )

    def append(self, expense: Expense) -> None:
        # Target the first row where column A (Fecha) is empty
        next_row = len(self._expenses.col_values(1)) + 1
        self._expenses.update(
            range_name=f"A{next_row}:E{next_row}",
            values=[[
                expense.fecha.isoformat(),
                expense.descripcion,
                expense.categoria.value if expense.categoria else "",
                str(expense.valor),
                expense.pagador,
            ]],
            value_input_option=ValueInputOption.user_entered,
        )

    def read_expenses(
        self,
        since: date,
        until: date,
        pagador: Pagador | None = None,
    ) -> list[Expense]:
        rows: list[list[str | int | float | bool | None]] = (
            self._expenses.get_all_values(
                value_render_option=ValueRenderOption.unformatted,
                date_time_render_option=DateTimeOption.formatted_string,
            )
        )
        expenses: list[Expense] = []
        for row in rows[1:]:  # skip header
            if len(row) < 4:
                continue
            try:
                row_date = date.fromisoformat(str(row[0]))
            except (ValueError, IndexError):
                continue
            if not (since <= row_date <= until):
                continue

            row_pagador = str(row[4]) if len(row) > 4 else ""
            if row_pagador not in ("David", "Daniela"):
                continue
            if pagador is not None and row_pagador != pagador:
                continue

            categoria_str = str(row[2]) if len(row) > 2 else ""
            try:
                categoria: Category | None = (
                    Category(categoria_str) if categoria_str else None
                )
            except ValueError:
                categoria = None

            try:
                expenses.append(
                    Expense(
                        fecha=row_date,
                        descripcion=str(row[1]) if len(row) > 1 else "",
                        categoria=categoria,
                        valor=Decimal(str(row[3])) if len(row) > 3 else Decimal(0),
                        pagador=cast(Pagador, row_pagador),
                    )
                )
            except (ValueError, InvalidOperation):
                continue
        return expenses

    def load_state(self) -> LastUpdatedState:
        rows = self._state.get_all_values()
        data = {row[0]: row[1] for row in rows if len(row) >= 2}
        last_run_raw = data.get("last_run", "")
        return LastUpdatedState(
            last_update_id=int(data.get("last_update_id") or 0),
            last_run=datetime.fromisoformat(last_run_raw) if last_run_raw else None,
        )

    def save_state(self, state: LastUpdatedState) -> None:
        self._state.update(
            range_name="A1:B2",
            values=[
                ["last_update_id", str(state.last_update_id)],
                ["last_run", state.last_run.isoformat() if state.last_run else ""],
            ],
        )
