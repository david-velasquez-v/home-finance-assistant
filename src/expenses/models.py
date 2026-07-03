from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Literal

from pydantic import BaseModel

Pagador = Literal["David", "Daniela"]


@dataclass
class LastUpdatedState:
    last_update_id: int = 0
    last_run: datetime | None = None


class Category(str, Enum):
    CASA = "Casa"
    MERCADO = "Mercado"
    VIAJES = "Viajes"
    ENTRETENIMIENTO = "Entretenimiento"
    FAMILIA_DANIELA = "Familia Daniela"
    FAMILIA_DAVID = "Familia David"
    CARRO = "Carro"
    IMPREVISTOS = "Imprevistos"
    RANDOM_50_50 = "Random 50/50"
    RANDOM_DANIELA = "Random Daniela"
    RANDOM_DAVID = "Random David"


CATEGORY_DESCRIPTIONS: dict[Category, str] = {
    Category.CASA: "Rent, utilities, home maintenance, furniture, cleaning supplies, home repairs",
    Category.MERCADO: "Groceries, supermarket, food market, bakery, butcher, produce",
    Category.VIAJES: "Flights, hotels, Airbnb, vacation activities, travel insurance",
    Category.ENTRETENIMIENTO: "Restaurants, bars, movies, concerts, streaming services, games, leisure activities",
    Category.FAMILIA_DANIELA: "Gifts, financial support, or events for Daniela's family",
    Category.FAMILIA_DAVID: "Gifts, financial support, or events for David's family",
    Category.CARRO: "Fixed expenses of owning and using our car: gas, maintenance and repairs, car insurance. Tolls and parking do NOT belong here — those are travel or entertainment depending on the trip.",
    Category.IMPREVISTOS: "Unexpected or emergency expenses, medical bills, unplanned repairs",
    Category.RANDOM_50_50: "Personal shared expenses split equally between David and Daniela",
    Category.RANDOM_DANIELA: "Daniela's personal expenses — clothing, personal care, hobbies",
    Category.RANDOM_DAVID: "David's personal expenses — clothing, personal care, hobbies",
}


class Expense(BaseModel):
    fecha: date
    descripcion: str
    categoria: Category | None = None
    valor: Decimal
    pagador: Pagador


class ExpenseList(BaseModel):
    expenses: list[Expense]


class StatementTransaction(BaseModel):
    fecha: date
    descripcion: str
    valor: Decimal


class UnmatchedList(BaseModel):
    unmatched: list[StatementTransaction]


class TransactionList(BaseModel):
    transactions: list[StatementTransaction]
