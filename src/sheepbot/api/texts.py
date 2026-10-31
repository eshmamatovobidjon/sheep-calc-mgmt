"""Russian messages returned by the API."""

AUTH_MISSING = "Откройте приложение из Telegram."
AUTH_INVALID = "Неверные данные авторизации Telegram. Откройте приложение заново."
AUTH_EXPIRED = "Сессия устарела. Закройте и откройте приложение заново."
NO_ACCESS = "Нет доступа. Откройте бота и нажмите /start, затем дождитесь одобрения администратора."
FORBIDDEN = "Нет доступа к этой функции."
NOT_FOUND = "Не найдено."
CLIENT_NOT_FOUND = "Клиент не найден."
CLIENT_EXISTS = "Клиент «{name}» уже есть."
PAYMENT_NOT_FOUND = "Оплата не найдена или уже удалена."
AMOUNT_INVALID = "Введите сумму целым числом сум, больше 0."
AMOUNT_TOO_BIG = "Слишком большая сумма."
DATE_FUTURE = "Дата не может быть в будущем."
DATE_RANGE = "Дата «с» позже даты «по»."
PHONE_INVALID = "Телефон: только цифры, пробелы и символы + - ( )."

# Pydantic error type -> message (value errors carry their own message).
VALIDATION_MESSAGES = {
    "missing": "Обязательное поле.",
    "string_too_short": "Слишком коротко (минимум {min_length}).",
    "string_too_long": "Слишком длинно (максимум {max_length}).",
    "enum": "Недопустимое значение.",
    "extra_forbidden": "Неизвестное поле.",
}
VALIDATION_DEFAULT = "Неверное значение."
INVALID_INPUT = "Проверьте введённые данные."
SERVER_ERROR = "Внутренняя ошибка. Попробуйте позже."
DB_UNAVAILABLE = "База данных недоступна."
