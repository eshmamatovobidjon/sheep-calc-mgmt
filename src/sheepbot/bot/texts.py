"""All Russian bot strings and button labels. Messages are sent with HTML parse mode."""

from sheepbot.domain.enums import UserStatus

# Main menu buttons (architecture section 9)
BTN_UPLOAD = "Загрузить рейс"
BTN_TEMPLATE = "Шаблон"
BTN_PAY = "Оплата"
BTN_PAYMENTS = "Последние оплаты"
BTN_CLIENTS = "Клиенты"
BTN_REPORTS = "Отчёты"
BTN_DEBTS = "Должники"
BTN_TRIPS = "Рейсы"
BTN_USERS = "Пользователи"
BTN_CANCEL = "Отмена"

# Bot commands: name -> description
COMMANDS: dict[str, str] = {
    "start": "Начать работу",
    "menu": "Главное меню",
    "template": "Скачать шаблон рейса",
    "pay": "Внести оплату клиента",
    "payments": BTN_PAYMENTS,
    "clients": BTN_CLIENTS,
    "report": BTN_REPORTS,
    "debts": BTN_DEBTS,
    "trips": BTN_TRIPS,
    "users": BTN_USERS,
    "cancel": "Отменить действие",
}

# General
GREETING = "Здравствуйте, {name}! Выберите действие в меню."
MAIN_MENU = "Главное меню."
CANCELLED = "Действие отменено."
IN_DEVELOPMENT = "Функция в разработке."
UNKNOWN_INPUT = "Не понял. Используйте меню."
NO_ACCESS = "Нет доступа к этой функции."
ERROR_GENERIC = "Произошла ошибка. Попробуйте ещё раз или обратитесь к администратору."
CALLBACK_EXPIRED = "Действие устарело."

# Template
TEMPLATE_CAPTION = "Заполните и отправьте файл в этот чат."

# Trip upload
UPLOAD_PROMPT = "Отправьте заполненный файл .xlsx (шаблон — кнопка «Шаблон»)."
UPLOAD_WRONG_TYPE = "Нужен Excel-файл в формате .xlsx — заполненный шаблон рейса."
UPLOAD_TOO_BIG = "Файл слишком большой: максимум {mb} МБ."
UPLOAD_REJECTED = "❌ <b>Файл отклонён.</b> Исправьте ошибки и отправьте файл снова:"
UPLOAD_ERRORS_MORE = "…и ещё {n} {word}"
UPLOAD_ERRORS_STOPPED = "Проверка остановлена после {n} ошибок."
UPLOAD_SAVED = "✅ Рейс №{number} сохранён."
UPLOAD_CANCELLED = "Загрузка отменена."
BTN_SAVE = "Сохранить"
BTN_UPLOAD_CANCEL = "Отмена"
ERROR_FORMS = ("ошибка", "ошибки", "ошибок")

PREVIEW_TITLE = "<b>Рейс №{number}</b>"
PREVIEW_REPLACES = " — <b>ЗАМЕНИТ существующий</b>"
PREVIEW_DEPARTURE = "Отправка: {date}"
PREVIEW_PURCHASE = (
    "Закуп: {heads} гол., {gross} кг брутто → {net} кг нетто\n    {kzt} KZT = {uzs} сум"
)
PREVIEW_EXPENSES = "Расходы: {uzs} сум"
PREVIEW_SALES = (
    "Продажи: {heads} гол., {net} кг нетто, {uzs} сум\n"
    "    {lines} {lines_word}, {clients} {clients_word}"
)
PREVIEW_PROFIT = "Прибыль: <b>{uzs} сум</b> ({pct}%)"
PREVIEW_NEW_CLIENTS = "Новые клиенты ({count}): {names}"
PREVIEW_MORE = " … и ещё {n}"
PREVIEW_CONFIRM = "Сохранить рейс?"
LINE_FORMS = ("строка", "строки", "строк")
CLIENT_FORMS = ("клиент", "клиента", "клиентов")

# Client picker
PICKER_PROMPT = "Введите часть имени клиента (минимум 2 буквы):"
PICKER_TOO_SHORT = "Введите минимум 2 буквы."
PICKER_NOT_FOUND = "Не найдено. Попробуйте другую часть имени."
PICKER_CHOOSE = "Выберите клиента:"
PICKER_CHOSEN = "Клиент: <b>{name}</b>"

# Balances
BALANCE_DEBT = "Долг: {amount} сум"
BALANCE_OVERPAID = "Переплата: {amount} сум"
BALANCE_ZERO = "Долг: 0 сум"
BALANCE_VALUE_OVERPAID = "переплата {amount}"

# Payment dialog
PAY_ASK_AMOUNT = "{balance}\n\nВведите сумму оплаты в сумах, например: 20 000 000"
PAY_AMOUNT_INVALID = "Введите сумму цифрами, больше 0. Например: 20 000 000"
PAY_ASK_METHOD = "Способ оплаты?"
PAY_ASK_DATE = "Дата оплаты?"
PAY_ASK_CUSTOM_DATE = "Введите дату в формате ДД.ММ.ГГГГ:"
PAY_DATE_INVALID = "Неверная дата. Формат: ДД.ММ.ГГГГ, например 31.10.2026"
PAY_DATE_FUTURE = "Дата не может быть в будущем."
PAY_ASK_COMMENT = "Комментарий? Напишите текст или нажмите «Пропустить»."
PAY_COMMENT_TOO_LONG = "Комментарий слишком длинный (максимум {limit} символов)."
PAY_CARD = (
    "<b>Оплата</b>\n"
    "Клиент: {client}\n"
    "Сумма: {amount} сум\n"
    "Способ: {method}\n"
    "Дата: {date}\n"
    "Комментарий: {note}\n"
    "Долг: {before} → {after}"
)
PAY_SAVED = "✅ Оплата сохранена."
PAY_CANCELLED = "Оплата отменена."
BTN_TODAY = "Сегодня"
BTN_YESTERDAY = "Вчера"
BTN_OTHER_DATE = "Другая"
BTN_SKIP = "Пропустить"
BTN_PAY_SAVE = "Сохранить"
BTN_PAY_CANCEL = "Отмена"
NO_VALUE = "—"

# Recent payments
PAYMENTS_TITLE = "<b>Последние оплаты</b>"
PAYMENTS_EMPTY = "Оплат пока нет."
PAYMENT_LINE = "{n}. {date} · {client} · {amount} · {method} · {author}"
BTN_DELETE_N = "Удалить {n}"
PAYMENT_DELETE_CONFIRM = "Удалить оплату?\n{date} · {client} · {amount} сум · {method}"
PAYMENT_DELETED = "🗑 Оплата удалена: {date} · {client} · {amount} сум"
PAYMENT_DELETE_KEPT = "Удаление отменено."
BTN_YES = "Да"
BTN_NO = "Нет"

# Clients
CLIENTS_MENU = "<b>Клиенты</b>"
BTN_CLIENT_FIND = "Найти"
BTN_CLIENT_ADD = "Добавить"
BTN_CLIENT_ALL = "Все клиенты"
CLIENTS_PAGE_TITLE = "<b>Клиенты</b> (стр. {page} из {pages})"
CLIENTS_EMPTY = "Клиентов пока нет."
CLIENT_LINE = "{name} — {balance}"
BTN_PREV = "←"
BTN_NEXT = "→"
CLIENT_CARD = (
    "<b>{name}</b>\n"
    "{balance}\n"
    "Отгружено: {shipped} сум\n"
    "Оплачено: {paid} сум\n"
    "Последняя продажа: {last_sale}\n"
    "Последняя оплата: {last_payment}"
)
BTN_CLIENT_RENAME = "Переименовать"
BTN_CLIENT_PAY = "Внести оплату"
CLIENT_ASK_NAME = "Введите имя нового клиента:"
CLIENT_ASK_NEW_NAME = "Введите новое имя для «{name}»:"
CLIENT_NAME_INVALID = "Имя должно содержать от 2 до {limit} символов."
CLIENT_EXISTS = "Клиент «{name}» уже есть."
CLIENT_ADDED = "✅ Клиент «{name}» добавлен."
CLIENT_RENAMED = "✅ Клиент переименован: «{name}»."
CLIENT_NOT_FOUND = "Клиент не найден."

# Access
REQUEST_SENT = "Запрос отправлен администратору. Вы получите сообщение, когда доступ откроют."
REQUEST_PENDING = "Ваш запрос на рассмотрении."
ACCESS_CLOSED = "Доступ закрыт."
NOT_REGISTERED = "Отправьте /start, чтобы запросить доступ."
ACCESS_GRANTED = "Доступ открыт: {perms}."

PERM_UPLOAD = "Загрузка"
PERM_VIEW = BTN_REPORTS
NO_PERMS = "нет"

# Access request card (to the admin)
REQUEST_CARD = (
    "<b>Запрос доступа</b>\n\nИмя: {name}\nUsername: {username}\nTelegram ID: <code>{tg_id}</code>"
)
REQUEST_GRANTED = "✅ Выдан доступ: {perms}"
REQUEST_REJECTED = "❌ Отклонено"
BTN_REQ_UPLOAD = PERM_UPLOAD
BTN_REQ_VIEW = PERM_VIEW
BTN_REQ_BOTH = "Оба"
BTN_REQ_REJECT = "Отклонить"

# User management
USERS_TITLE = (
    "<b>Пользователи</b>\n\nОжидают: {pending}\nАктивны: {active}\nЗаблокированы: {blocked}"
)
USERS_EMPTY = "Пользователей пока нет."
USER_CARD = (
    "<b>{name}</b>\nUsername: {username}\nTelegram ID: <code>{tg_id}</code>\n"
    "Статус: {status}\nПрава: {perms}"
)
USER_NOT_FOUND = "Пользователь не найден."
CANNOT_CHANGE_ADMIN = "Нельзя изменить администратора."
BTN_TOGGLE_UPLOAD = "Загрузка {mark}"
BTN_TOGGLE_VIEW = "Отчёты {mark}"
BTN_BLOCK = "Заблокировать"
BTN_UNBLOCK = "Разблокировать"
BTN_BACK = "Назад"
MARK_ON = "✓"
MARK_OFF = "✗"
STATUS_ICONS: dict[UserStatus, str] = {
    UserStatus.PENDING: "⏳",
    UserStatus.ACTIVE: "✅",
    UserStatus.BLOCKED: "⛔",
}
