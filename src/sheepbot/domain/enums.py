"""Domain enums. Values are stored in the DB; labels are shown to users."""

from enum import StrEnum


class AnimalType(StrEnum):
    SOVLIQ = "sovliq"
    QUCHQOR = "quchqor"
    QUZI = "quzi"
    ECHKI = "echki"


class ProductCategory(StrEnum):
    ANIMAL = "animal"
    BYPRODUCT = "byproduct"


class Currency(StrEnum):
    KZT = "KZT"
    USD = "USD"
    UZS = "UZS"


class PaymentMethod(StrEnum):
    BANK = "bank"
    CARD = "card"
    CASH = "cash"


class UserStatus(StrEnum):
    PENDING = "pending"
    ACTIVE = "active"
    BLOCKED = "blocked"


class UploadStatus(StrEnum):
    PENDING = "pending"
    SAVED = "saved"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


class Perm(StrEnum):
    UPLOAD = "upload"
    VIEW = "view"
    ADMIN = "admin"


ANIMAL_TYPE_LABELS: dict[AnimalType, str] = {
    AnimalType.SOVLIQ: "Совлик",
    AnimalType.QUCHQOR: "Кучкор",
    AnimalType.QUZI: "Кузи",
    AnimalType.ECHKI: "Эчки",
}

PRODUCT_CATEGORY_LABELS: dict[ProductCategory, str] = {
    ProductCategory.ANIMAL: "Туша",
    ProductCategory.BYPRODUCT: "Субпродукт",
}

CURRENCY_LABELS: dict[Currency, str] = {
    Currency.KZT: "KZT",
    Currency.USD: "USD",
    Currency.UZS: "UZS",
}

PAYMENT_METHOD_LABELS: dict[PaymentMethod, str] = {
    PaymentMethod.BANK: "Банк",
    PaymentMethod.CARD: "Карта",
    PaymentMethod.CASH: "Наличные",
}

USER_STATUS_LABELS: dict[UserStatus, str] = {
    UserStatus.PENDING: "Ожидает",
    UserStatus.ACTIVE: "Активен",
    UserStatus.BLOCKED: "Заблокирован",
}


def _label_key(text: str) -> str:
    return " ".join(text.split()).casefold().replace("ё", "е")


def enum_from_label[E: StrEnum](labels: dict[E, str], text: str) -> E | None:
    """Reverse lookup: label -> enum member (trimmed, case-insensitive); None if unknown."""
    key = _label_key(text)
    for member, label in labels.items():
        if _label_key(label) == key:
            return member
    return None


def animal_type_from_label(text: str) -> AnimalType | None:
    return enum_from_label(ANIMAL_TYPE_LABELS, text)


def product_category_from_label(text: str) -> ProductCategory | None:
    return enum_from_label(PRODUCT_CATEGORY_LABELS, text)


def currency_from_label(text: str) -> Currency | None:
    return enum_from_label(CURRENCY_LABELS, text)


def payment_method_from_label(text: str) -> PaymentMethod | None:
    return enum_from_label(PAYMENT_METHOD_LABELS, text)


def user_status_from_label(text: str) -> UserStatus | None:
    return enum_from_label(USER_STATUS_LABELS, text)
