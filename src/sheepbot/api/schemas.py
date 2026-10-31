"""Request/response schemas. Money, kg and rates are strings; IDs are numbers."""

import re
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from sheepbot.api import texts
from sheepbot.domain.enums import PaymentMethod
from sheepbot.domain.formatting import today

CLIENT_NAME_MIN, CLIENT_NAME_MAX = 2, 100
PHONE_MAX = 32
NOTE_MAX = 500
AMOUNT_MAX_UZS = 10**12
_PHONE_RE = re.compile(r"^[0-9+()\- ]*$")


class InputModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class MeOut(BaseModel):
    id: int
    telegram_id: int
    full_name: str
    username: str | None
    status: str
    status_label: str
    permissions: list[str]


class OptionOut(BaseModel):
    value: str
    label: str


class ProductOut(BaseModel):
    code: str
    name: str
    category: str
    animal_type: str | None
    discount_per_head: str


class CatalogOut(BaseModel):
    products: list[ProductOut]
    animal_types: list[OptionOut]
    currencies: list[OptionOut]
    payment_methods: list[OptionOut]


class HealthOut(BaseModel):
    status: str


class ClientBalanceOut(BaseModel):
    id: int
    name: str
    shipped: str
    paid: str
    balance: str
    last_sale_date: date | None
    last_payment_date: date | None


class ClientPageOut(BaseModel):
    items: list[ClientBalanceOut]
    total: int


class ClientDetailOut(ClientBalanceOut):
    phone: str | None


def _check_phone(value: str | None) -> str | None:
    if value is not None and not _PHONE_RE.fullmatch(value):
        raise ValueError(texts.PHONE_INVALID)
    return value or None


class ClientCreateIn(InputModel):
    name: str = Field(min_length=CLIENT_NAME_MIN, max_length=CLIENT_NAME_MAX)
    phone: str | None = Field(default=None, max_length=PHONE_MAX)

    @field_validator("phone")
    @classmethod
    def _phone(cls, value: str | None) -> str | None:
        return _check_phone(value)


class ClientUpdateIn(InputModel):
    """Only the fields sent are changed; `phone: null` clears the phone."""

    name: str | None = Field(default=None, min_length=CLIENT_NAME_MIN, max_length=CLIENT_NAME_MAX)
    phone: str | None = Field(default=None, max_length=PHONE_MAX)

    @field_validator("phone")
    @classmethod
    def _phone(cls, value: str | None) -> str | None:
        return _check_phone(value)


class LedgerLineOut(BaseModel):
    date: date
    kind: str  # "shipment" | "payment"
    trip_number: int | None
    product: str | None
    heads: int | None
    net_kg: str | None
    price_uzs_per_kg: str | None
    amount_uzs: str
    payment_method: str | None
    note: str | None
    running_balance: str


class LedgerOut(BaseModel):
    client_id: int
    client_name: str
    date_from: date | None
    date_to: date | None
    opening_balance: str
    shipped: str
    paid: str
    closing_balance: str
    lines: list[LedgerLineOut]


class PaymentIn(InputModel):
    client_id: int
    amount_uzs: str
    method: PaymentMethod
    date: date
    note: str | None = Field(default=None, max_length=NOTE_MAX)

    @field_validator("amount_uzs")
    @classmethod
    def _amount(cls, value: str) -> str:
        digits = "".join(value.split())
        if not digits.isascii() or not digits.isdecimal() or int(digits) <= 0:
            raise ValueError(texts.AMOUNT_INVALID)
        if int(digits) > AMOUNT_MAX_UZS:
            raise ValueError(texts.AMOUNT_TOO_BIG)
        return digits

    @field_validator("date")
    @classmethod
    def _not_future(cls, value: date) -> date:
        if value > today():
            raise ValueError(texts.DATE_FUTURE)
        return value

    @field_validator("note")
    @classmethod
    def _empty_note(cls, value: str | None) -> str | None:
        return value or None


class PaymentOut(BaseModel):
    id: int
    client_id: int
    client_name: str
    amount_uzs: str
    method: str
    method_label: str
    date: date
    note: str | None
    entered_by: str
    created_at: datetime


class PaymentPageOut(BaseModel):
    items: list[PaymentOut]
    total: int


class PaymentResultOut(BaseModel):
    """A created or deleted payment and the client's balance after the change."""

    payment: PaymentOut
    balance: str
