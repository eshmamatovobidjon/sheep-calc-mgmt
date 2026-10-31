"""Generate fictional demo trip files in assets/demo/ through the template builder.

Deterministic: the same seed always produces the same data.
"""

import random
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from typing import Any

from sheepbot.domain.catalog import PRODUCT_CATALOG
from sheepbot.domain.enums import ANIMAL_TYPE_LABELS, CURRENCY_LABELS, AnimalType, Currency
from sheepbot.excel.template_builder import build_template
from sheepbot.excel.template_spec import SHEET_EXPENSES, SHEET_PURCHASES, SHEET_SALES

OUTPUT_DIR = Path(__file__).resolve().parents[1] / "assets" / "demo"
SEED = 20261031

# Fictional business names only.
CLIENTS = (
    "Кафе Чинар",
    "Ресторан Афсона",
    "Мясная лавка Юнусабад",
    "Магазин Чиланзар-Мясо",
    "Оптовик Сергели",
    "Кафе Бахор",
    "Чайхана Олтин",
    "Ресторан Лагман-Хаус",
    "Мясной двор Бектемир",
    "Кафе Самса-Центр",
    "Лавка Яккасарай",
    "Оптовик Мирабад",
    "Кафе Плов-Маркет",
    "Ресторан Шарк",
    "Мясная точка Алмазар",
)

KG = Decimal("0.1")
CENT = Decimal("0.01")
WHOLE = Decimal("1")
TARGET_AVG_PRICE = Decimal("115")  # thousand so'm/kg
MIN_PRICE, MAX_PRICE = Decimal("105"), Decimal("126")

# type -> (total heads range, purchase price range KZT/kg, sale price offset thousand so'm/kg)
TYPE_PLAN: dict[AnimalType, tuple[tuple[int, int], tuple[int, int], int]] = {
    AnimalType.SOVLIQ: ((230, 270), (3300, 3600), 0),
    AnimalType.QUCHQOR: ((110, 140), (3500, 3800), 2),
    AnimalType.QUZI: ((130, 160), (3800, 4100), 5),
    AnimalType.ECHKI: ((70, 90), (2400, 2700), -8),
}
ANIMAL_PRODUCTS = {p.animal_type: p for p in PRODUCT_CATALOG if p.animal_type}
BYPRODUCTS = [p for p in PRODUCT_CATALOG if p.animal_type is None]


@dataclass(frozen=True)
class TripPlan:
    number: int
    departure: date
    rate_kzt: Decimal
    rate_usd: Decimal
    sales_days: int
    clients: tuple[str, ...]

    @property
    def arrival(self) -> date:
        return self.departure + timedelta(days=3)


PLANS = (
    TripPlan(101, date(2026, 10, 5), Decimal("26.80"), Decimal("11900"), 3, CLIENTS[0:13]),
    TripPlan(102, date(2026, 10, 12), Decimal("26.95"), Decimal("11950"), 2, CLIENTS[2:15]),
)


def q(value: Decimal, step: Decimal) -> Decimal:
    return value.quantize(step, rounding=ROUND_HALF_UP)


def dec(value: float) -> Decimal:
    return Decimal(str(value))


def split(rng: random.Random, total: int, parts: int) -> list[int]:
    weights = [rng.uniform(0.7, 1.3) for _ in range(parts)]
    sizes = [max(1, round(total * w / sum(weights))) for w in weights[:-1]]
    return [*sizes, total - sum(sizes)]


@dataclass
class TripData:
    trip: dict[str, Any]
    purchases: list[dict[str, Any]]
    expenses: list[dict[str, Any]]
    sales: list[dict[str, Any]]
    cost_uzs: Decimal
    revenue_uzs: Decimal


def build_trip(plan: TripPlan) -> TripData:
    rng = random.Random(SEED + plan.number)

    # Purchases
    purchases: list[dict[str, Any]] = []
    heads_by_type: dict[AnimalType, int] = {}
    net_by_type: dict[AnimalType, Decimal] = {}
    purchase_uzs = Decimal(0)
    for animal, (heads_range, price_range, _) in TYPE_PLAN.items():
        total_heads = rng.randint(*heads_range)
        heads_by_type[animal] = total_heads
        net_by_type[animal] = Decimal(0)
        for heads in split(rng, total_heads, rng.randint(2, 3)):
            gross = q(dec(heads * rng.uniform(30, 40)), KG)
            discount = q(gross * dec(rng.uniform(0.06, 0.08)), KG)
            price = Decimal(rng.randrange(price_range[0], price_range[1] + 1, 10))
            net = gross - discount
            net_by_type[animal] += net
            purchase_uzs += q(q(net * price, CENT) * plan.rate_kzt, WHOLE)
            purchases.append(
                {
                    "date": plan.departure - timedelta(days=rng.randint(0, 1)),
                    "animal_type": ANIMAL_TYPE_LABELS[animal],
                    "heads": heads,
                    "gross_kg": gross,
                    "discount_kg": discount,
                    "price_kzt": price,
                }
            )
    purchases.sort(key=lambda r: r["date"])
    total_heads = sum(heads_by_type.values())

    # Expenses
    kzt, usd, uzs = (CURRENCY_LABELS[c] for c in (Currency.KZT, Currency.USD, Currency.UZS))
    expenses: list[dict[str, Any]] = [
        {"item": "Мясник", "qty": total_heads, "unit_price": 1200, "currency": kzt},
        {"item": "Грузчики", "unit_price": rng.randrange(120_000, 180_001, 5_000), "currency": kzt},
        {"item": "Документы", "unit_price": rng.randrange(700, 901, 50), "currency": usd},
        {"item": "Водитель", "unit_price": rng.randrange(1400, 1701, 50), "currency": usd},
        {"item": "Арава", "qty": total_heads, "unit_price": 7000, "currency": uzs},
        {
            "item": "Прочее",
            "unit_price": rng.randrange(2_000_000, 3_500_001, 100_000),
            "currency": uzs,
            "note": "Мелкие расходы в пути",
        },
    ]
    rates = {kzt: plan.rate_kzt, usd: plan.rate_usd, uzs: Decimal(1)}
    expense_uzs = sum(
        q(
            q(Decimal(e.get("qty", 1)) * Decimal(e["unit_price"]), CENT) * rates[e["currency"]],
            WHOLE,
        )
        for e in expenses
    )
    cost_uzs = purchase_uzs + expense_uzs

    def sale_day() -> int:
        return rng.choices(range(1, plan.sales_days + 1), weights=[5, 3, 2][: plan.sales_days])[0]

    # By-product sales
    sales: list[dict[str, Any]] = []
    byproduct_uzs = Decimal(0)
    for _ in range(rng.randint(4, 6)):
        gross = q(dec(rng.uniform(20, 150)), KG)
        price = Decimal(rng.randint(34, 90)) / 2
        byproduct_uzs += q(gross * price * 1000, WHOLE)
        sales.append(
            {
                "day": sale_day(),
                "client": rng.choice(plan.clients),
                "product": rng.choice(BYPRODUCTS).code,
                "gross_kg": gross,
                "price_thousand_uzs": price,
            }
        )

    # Animal sales: sell every purchased head; size kg and prices for a plausible margin.
    margin = dec(rng.uniform(0.06, 0.09))
    needed_net_kg = (cost_uzs * (1 + margin) - byproduct_uzs) / (TARGET_AVG_PRICE * 1000)
    shrink = needed_net_kg / sum(net_by_type.values())
    weighted_offset = sum(net_by_type[t] * TYPE_PLAN[t][2] for t in TYPE_PLAN) / sum(
        net_by_type.values()
    )
    center = TARGET_AVG_PRICE - weighted_offset

    clients_queue = list(plan.clients)
    rng.shuffle(clients_queue)
    for animal, heads in heads_by_type.items():
        product = ANIMAL_PRODUCTS[animal]
        net_per_head = net_by_type[animal] / heads
        lines = max(3, round(heads / rng.uniform(10, 16)))
        for line_heads in split(rng, heads, lines):
            per_head = net_per_head * shrink * dec(rng.uniform(0.97, 1.03))
            gross = q(line_heads * (per_head + product.discount_per_head), KG)
            price = center + TYPE_PLAN[animal][2] + dec(rng.uniform(-1.5, 1.5))
            price = min(MAX_PRICE, max(MIN_PRICE, q(price * 2, WHOLE) / 2))
            client = clients_queue.pop() if clients_queue else rng.choice(plan.clients)
            sales.append(
                {
                    "day": sale_day(),
                    "client": client,
                    "product": product.code,
                    "heads": line_heads,
                    "gross_kg": gross,
                    "price_thousand_uzs": price,
                }
            )

    sales.sort(key=lambda r: r["day"])
    discounts = {p.code: p.discount_per_head for p in PRODUCT_CATALOG}
    revenue_uzs = Decimal(0)
    for sale in sales:
        sale["date"] = plan.arrival + timedelta(days=sale["day"] - 1)
        net = sale["gross_kg"] - sale.get("heads", 0) * discounts[sale["product"]]
        revenue_uzs += q(net * q(sale["price_thousand_uzs"] * 1000, WHOLE), WHOLE)

    trip = {
        "number": plan.number,
        "departure_date": plan.departure,
        "arrival_date": plan.arrival,
        "rate_kzt": plan.rate_kzt,
        "rate_usd": plan.rate_usd,
        "note": "Демо-рейс, вымышленные данные",
    }
    return TripData(trip, purchases, expenses, sales, cost_uzs, revenue_uzs)


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for plan in PLANS:
        data = build_trip(plan)
        path = OUTPUT_DIR / f"demo_trip_{plan.number}.xlsx"
        path.write_bytes(
            build_template(
                data.trip,
                {
                    SHEET_PURCHASES: data.purchases,
                    SHEET_EXPENSES: data.expenses,
                    SHEET_SALES: data.sales,
                },
            )
        )

        profit = data.revenue_uzs - data.cost_uzs
        margin = profit / data.cost_uzs * 100
        heads = sum(r["heads"] for r in data.purchases)
        gross = sum(r["gross_kg"] for r in data.purchases)
        sold_heads = sum(r.get("heads", 0) for r in data.sales)
        clients = len({r["client"] for r in data.sales})
        print(
            f"{path.name}: purchase {heads} heads / {gross} kg gross; "
            f"sales {len(data.sales)} lines, {clients} clients, {sold_heads} heads; "
            f"cost {data.cost_uzs:,.0f}, revenue {data.revenue_uzs:,.0f}, "
            f"profit {profit:,.0f} ({margin:.1f}%)"
        )
        assert 5 <= margin <= 10, "demo margin out of the 5-10% range"
        assert 40 <= len(data.sales) <= 70, "demo sale line count out of range"
        assert sold_heads == heads


if __name__ == "__main__":
    main()
