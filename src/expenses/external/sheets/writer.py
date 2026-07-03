from datetime import date
from decimal import Decimal
from typing import cast

import gspread
from gspread.utils import ValueInputOption

from expenses.models import Category, Expense, Pagador


class SheetWriter:
    def __init__(self, worksheet: gspread.Worksheet) -> None:
        self._ws = worksheet

    def append(self, expense: Expense) -> None:
        self._ws.append_row(
            values=[
                expense.fecha.isoformat(),
                expense.descripcion,
                expense.categoria.value if expense.categoria else "",
                str(expense.valor),
                expense.pagador,
            ],
            value_input_option=ValueInputOption.user_entered,
        )

    def read_expenses(
        self,
        since: date,
        until: date,
        pagador: Pagador | None = None,
    ) -> list[Expense]:
        rows: list[list[str | int | float | bool | None]] = self._ws.get_all_values()
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
                categoria: Category | None = Category(categoria_str) if categoria_str else None
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
            except Exception:
                continue
        return expenses
