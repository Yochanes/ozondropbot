from __future__ import annotations

import re
from dataclasses import dataclass


_OZON_ID_RE = re.compile(r"(?:/product/[^/]*-|/product/)(\d+)")


@dataclass(slots=True)
class ProductSnapshot:
    ozon_id: str
    url: str
    title: str
    current_price: float
    old_price: float | None = None
    promo: str | None = None


def extract_ozon_id(url: str) -> str | None:
    match = _OZON_ID_RE.search(url)
    return match.group(1) if match else None


class OzonParser:
    async def fetch_product(self, url: str) -> ProductSnapshot:
        ozon_id = extract_ozon_id(url)
        if not ozon_id:
            raise ValueError("Не удалось распознать артикул Ozon из ссылки")

        # Production note: integrate Playwright parser here.
        title = f"Ozon товар {ozon_id}"
        pseudo_price = float(int(ozon_id[-3:]) + 1000)
        return ProductSnapshot(
            ozon_id=ozon_id,
            url=f"https://www.ozon.ru/product/{ozon_id}",
            title=title,
            current_price=pseudo_price,
            old_price=pseudo_price * 1.03,
        )
