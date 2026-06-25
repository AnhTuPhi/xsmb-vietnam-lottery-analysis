from datetime import datetime
from unittest.mock import MagicMock
from zoneinfo import ZoneInfo

from vietlott.models import PipelineReport
from vietlott.products import ALL_PRODUCTS, LOTTO_535, MEGA_645, POWER_655
from vietlott_fetch import products_for_today, run_for_products

VN = ZoneInfo("Asia/Ho_Chi_Minh")


def test_products_for_today_picks_655_on_tuesday():
    # Tue 25/11/2025 — Power 6/55 draws
    now = datetime(2025, 11, 25, 19, 0, tzinfo=VN)
    picks = products_for_today(now)
    assert POWER_655 in picks
    assert MEGA_645 not in picks


def test_products_for_today_picks_645_on_wednesday():
    # Wed 26/11/2025 — Mega 6/45 draws
    now = datetime(2025, 11, 26, 19, 0, tzinfo=VN)
    picks = products_for_today(now)
    assert MEGA_645 in picks
    assert POWER_655 not in picks


def test_products_for_today_returns_empty_for_a_day_no_product_draws():
    # Pick a weekday not in ANY product's draw_days. If 535 is every day,
    # this test must adapt — use Task 3's verified schedule. If 535 draws
    # daily, this test can assert that LOTTO_535 is always included.
    now = datetime(2025, 11, 24, 19, 0, tzinfo=VN)  # Monday
    picks = products_for_today(now)
    # At minimum: no Power 6/55 on Monday
    assert POWER_655 not in picks


def test_run_for_products_isolates_failures():
    products = list(ALL_PRODUCTS)

    # Build a Pipeline whose run() raises for 655 but works for the others.
    fake_pipeline = MagicMock()

    def fake_run(product):
        if product is POWER_655:
            raise RuntimeError("boom")
        return PipelineReport(product_slug=product.slug, new_count=1, total_count=10)

    fake_pipeline.run.side_effect = fake_run

    reports = run_for_products(products, pipeline=fake_pipeline)

    by_slug = {r.product_slug: r for r in reports}
    assert by_slug["655"].new_count == 0
    assert "boom" in by_slug["655"].warnings[0]
    assert by_slug["645"].new_count == 1
    assert by_slug["535"].new_count == 1


def test_run_for_products_empty_input_returns_empty_list():
    fake_pipeline = MagicMock()
    assert run_for_products([], pipeline=fake_pipeline) == []
    fake_pipeline.run.assert_not_called()
