from aiogram.fsm.state import State, StatesGroup


class LanguageState(StatesGroup):
    choosing = State()


class KPState(StatesGroup):
    q1_company = State()
    q2_client = State()
    q3_product = State()
    q4_price = State()
    q5_deadline = State()
    q6_phone = State()
    confirm = State()


class ContractState(StatesGroup):
    q1_company = State()
    q2_client = State()
    q3_subject = State()
    q4_amount = State()
    q5_deadline = State()
    q6_city = State()
    confirm = State()


class InvoiceState(StatesGroup):
    q1_company = State()
    q2_client = State()
    q3_product = State()
    q4_quantity = State()
    q5_price = State()
    q6_bank = State()
    confirm = State()