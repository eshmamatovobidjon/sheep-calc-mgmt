"""Product catalog: used by the seed, the template and the parser."""

from dataclasses import dataclass
from decimal import Decimal

from sheepbot.domain.enums import AnimalType, ProductCategory


@dataclass(frozen=True, slots=True)
class ProductDef:
    code: str
    name: str
    category: ProductCategory
    animal_type: AnimalType | None
    discount_per_head: Decimal


PRODUCT_CATALOG: tuple[ProductDef, ...] = (
    ProductDef("SOV (-1KG)", "Совлик", ProductCategory.ANIMAL, AnimalType.SOVLIQ, Decimal("1.0")),
    ProductDef(
        "QO'CH (-1KG)", "Кучкор", ProductCategory.ANIMAL, AnimalType.QUCHQOR, Decimal("1.0")
    ),
    ProductDef("QO'Z (-0,5KG)", "Кузи", ProductCategory.ANIMAL, AnimalType.QUZI, Decimal("0.5")),
    ProductDef("ECHKI (-0,5KG)", "Эчки", ProductCategory.ANIMAL, AnimalType.ECHKI, Decimal("0.5")),
    ProductDef("DUMBA", "Думба", ProductCategory.BYPRODUCT, None, Decimal("0")),
    ProductDef("JIGAR", "Жигар", ProductCategory.BYPRODUCT, None, Decimal("0")),
    ProductDef("LAXAT", "Лахат", ProductCategory.BYPRODUCT, None, Decimal("0")),
    ProductDef("CHARVI", "Чарви", ProductCategory.BYPRODUCT, None, Decimal("0")),
    ProductDef("UPKA", "Упка", ProductCategory.BYPRODUCT, None, Decimal("0")),
)

PRODUCT_CODES: tuple[str, ...] = tuple(p.code for p in PRODUCT_CATALOG)
