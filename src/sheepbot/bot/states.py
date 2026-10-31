"""FSM state groups, one per feature."""

from aiogram.fsm.state import State, StatesGroup


class ClientPickerStates(StatesGroup):
    query = State()


class PaymentStates(StatesGroup):
    amount = State()
    method = State()
    date = State()
    custom_date = State()
    comment = State()
    confirm = State()


class ClientStates(StatesGroup):
    add_name = State()
    rename = State()


class ReportStates(StatesGroup):
    statement_period = State()
    statement_dates = State()
    statement_format = State()
