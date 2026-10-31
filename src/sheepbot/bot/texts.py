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
