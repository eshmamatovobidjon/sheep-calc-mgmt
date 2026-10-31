from __future__ import annotations

import datetime as dt
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from sheepbot.db.base import Base, IdMixin, TimestampMixin, str_enum
from sheepbot.domain.enums import (
    AnimalType,
    Currency,
    PaymentMethod,
    ProductCategory,
    UploadStatus,
    UserStatus,
)

KG = Numeric(10, 1)
MONEY = Numeric(16, 2)
RATE = Numeric(14, 4)
DISCOUNT = Numeric(4, 1)

USER_FK = "bot_user.id"
TRIP_FK = "trip.id"
TRIP_CHILD_CASCADE = "all, delete-orphan"


class BotUser(IdMixin, TimestampMixin, Base):
    __tablename__ = "bot_user"

    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True)
    full_name: Mapped[str] = mapped_column(String(255))
    username: Mapped[str | None] = mapped_column(String(64))
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    can_upload: Mapped[bool] = mapped_column(Boolean, default=False)
    can_view: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[UserStatus] = mapped_column(str_enum(UserStatus), default=UserStatus.PENDING)


class Client(IdMixin, TimestampMixin, Base):
    __tablename__ = "client"

    name: Mapped[str] = mapped_column(String(255))
    name_key: Mapped[str] = mapped_column(String(255), unique=True)
    phone: Mapped[str | None] = mapped_column(String(32))
    created_by_id: Mapped[int | None] = mapped_column(ForeignKey(USER_FK))

    sales: Mapped[list[Sale]] = relationship(back_populates="client")
    payments: Mapped[list[Payment]] = relationship(back_populates="client")


class Product(IdMixin, TimestampMixin, Base):
    __tablename__ = "product"

    code: Mapped[str] = mapped_column(String(32), unique=True)
    name: Mapped[str] = mapped_column(String(64))
    category: Mapped[ProductCategory] = mapped_column(str_enum(ProductCategory))
    animal_type: Mapped[AnimalType | None] = mapped_column(str_enum(AnimalType))
    discount_per_head: Mapped[Decimal] = mapped_column(DISCOUNT, default=Decimal("0"))


class Upload(IdMixin, TimestampMixin, Base):
    __tablename__ = "upload"

    file_name: Mapped[str] = mapped_column(String(255))
    file_hash: Mapped[str] = mapped_column(String(64))
    stored_path: Mapped[str] = mapped_column(String(512))
    uploaded_by_id: Mapped[int] = mapped_column(ForeignKey(USER_FK))
    status: Mapped[UploadStatus] = mapped_column(
        str_enum(UploadStatus), default=UploadStatus.PENDING
    )
    trip_number: Mapped[int | None] = mapped_column(Integer)

    uploaded_by: Mapped[BotUser] = relationship()


class Trip(IdMixin, TimestampMixin, Base):
    __tablename__ = "trip"

    number: Mapped[int] = mapped_column(Integer, unique=True)
    departure_date: Mapped[dt.date] = mapped_column(Date)
    arrival_date: Mapped[dt.date | None] = mapped_column(Date)
    rate_kzt: Mapped[Decimal] = mapped_column(RATE)
    rate_usd: Mapped[Decimal] = mapped_column(RATE)
    note: Mapped[str | None] = mapped_column(String(1000))
    upload_id: Mapped[int] = mapped_column(ForeignKey("upload.id"))

    upload: Mapped[Upload] = relationship()
    purchases: Mapped[list[Purchase]] = relationship(
        back_populates="trip",
        cascade=TRIP_CHILD_CASCADE,
        passive_deletes=True,
        order_by="Purchase.row_no",
    )
    expenses: Mapped[list[Expense]] = relationship(
        back_populates="trip",
        cascade=TRIP_CHILD_CASCADE,
        passive_deletes=True,
        order_by="Expense.row_no",
    )
    sales: Mapped[list[Sale]] = relationship(
        back_populates="trip",
        cascade=TRIP_CHILD_CASCADE,
        passive_deletes=True,
        order_by="Sale.row_no",
    )


class Purchase(IdMixin, TimestampMixin, Base):
    __tablename__ = "purchase"

    trip_id: Mapped[int] = mapped_column(ForeignKey(TRIP_FK, ondelete="CASCADE"), index=True)
    row_no: Mapped[int] = mapped_column(Integer)
    date: Mapped[dt.date] = mapped_column(Date)
    animal_type: Mapped[AnimalType] = mapped_column(str_enum(AnimalType))
    heads: Mapped[int] = mapped_column(Integer)
    gross_kg: Mapped[Decimal] = mapped_column(KG)
    discount_kg: Mapped[Decimal] = mapped_column(KG)
    net_kg: Mapped[Decimal] = mapped_column(KG)
    price_kzt: Mapped[Decimal] = mapped_column(MONEY)
    amount_kzt: Mapped[Decimal] = mapped_column(MONEY)
    amount_uzs: Mapped[int] = mapped_column(BigInteger)
    note: Mapped[str | None] = mapped_column(String(1000))

    trip: Mapped[Trip] = relationship(back_populates="purchases")


class Expense(IdMixin, TimestampMixin, Base):
    __tablename__ = "expense"

    trip_id: Mapped[int] = mapped_column(ForeignKey(TRIP_FK, ondelete="CASCADE"), index=True)
    row_no: Mapped[int] = mapped_column(Integer)
    item: Mapped[str] = mapped_column(String(255))
    qty: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    unit_price: Mapped[Decimal] = mapped_column(MONEY)
    currency: Mapped[Currency] = mapped_column(str_enum(Currency))
    amount: Mapped[Decimal] = mapped_column(MONEY)
    amount_uzs: Mapped[int] = mapped_column(BigInteger)
    note: Mapped[str | None] = mapped_column(String(1000))

    trip: Mapped[Trip] = relationship(back_populates="expenses")


class Sale(IdMixin, TimestampMixin, Base):
    __tablename__ = "sale"

    trip_id: Mapped[int] = mapped_column(ForeignKey(TRIP_FK, ondelete="CASCADE"), index=True)
    row_no: Mapped[int] = mapped_column(Integer)
    day: Mapped[int] = mapped_column(Integer)
    date: Mapped[dt.date] = mapped_column(Date)
    client_id: Mapped[int] = mapped_column(ForeignKey("client.id"), index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("product.id"))
    heads: Mapped[int | None] = mapped_column(Integer)
    gross_kg: Mapped[Decimal] = mapped_column(KG)
    discount_per_head: Mapped[Decimal] = mapped_column(DISCOUNT)
    net_kg: Mapped[Decimal] = mapped_column(KG)
    price_uzs_per_kg: Mapped[int] = mapped_column(BigInteger)
    amount_uzs: Mapped[int] = mapped_column(BigInteger)
    note: Mapped[str | None] = mapped_column(String(1000))

    trip: Mapped[Trip] = relationship(back_populates="sales")
    client: Mapped[Client] = relationship(back_populates="sales")
    product: Mapped[Product] = relationship()


class Payment(IdMixin, TimestampMixin, Base):
    __tablename__ = "payment"
    __table_args__ = (CheckConstraint("amount_uzs > 0", name="amount_positive"),)

    client_id: Mapped[int] = mapped_column(ForeignKey("client.id"), index=True)
    date: Mapped[dt.date] = mapped_column(Date)
    amount_uzs: Mapped[int] = mapped_column(BigInteger)
    method: Mapped[PaymentMethod] = mapped_column(str_enum(PaymentMethod))
    note: Mapped[str | None] = mapped_column(String(1000))
    entered_by_id: Mapped[int] = mapped_column(ForeignKey(USER_FK))
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    deleted_by_id: Mapped[int | None] = mapped_column(ForeignKey(USER_FK))
    deleted_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))

    client: Mapped[Client] = relationship(back_populates="payments")
    entered_by: Mapped[BotUser] = relationship(foreign_keys=[entered_by_id])
