from ozondropbot.services.drops import drop_percent
from ozondropbot.services.ozon import extract_ozon_id


def test_extract_ozon_id_variants() -> None:
    assert extract_ozon_id("https://www.ozon.ru/product/noutbuk-123456789/") == "123456789"
    assert extract_ozon_id("https://www.ozon.ru/product/123456789/?oos_search=false") == "123456789"


def test_drop_percent() -> None:
    assert round(drop_percent(1000, 930), 2) == 7.0
    assert drop_percent(0, 100) == 0.0
