import dataclasses
import pytest

from vietlott.products import (
    ALL_PRODUCTS,
    LOTTO_535,
    MEGA_645,
    POWER_655,
    VietlottProduct,
)


def _sample() -> VietlottProduct:
    return VietlottProduct(
        slug="x",
        name="X",
        code="1/1",
        ball_count=1,
        ball_min=1,
        ball_max=1,
        has_special_ball=False,
        special_ball_max=None,
        draw_days=(0,),
        draw_time_vn=(18, 0),
        result_url="https://vietlott.vn/sample",
    )


def test_vietlott_product_is_frozen():
    p = _sample()
    with pytest.raises(dataclasses.FrozenInstanceError):
        p.slug = "y"  # type: ignore[misc]


def test_power_655_definition():
    assert POWER_655.slug == "655"
    assert POWER_655.code == "6/55"
    assert POWER_655.ball_count == 6
    assert POWER_655.ball_min == 1
    assert POWER_655.ball_max == 55
    assert POWER_655.has_special_ball is True
    assert POWER_655.special_ball_max == 55
    # Schedule: Tue / Thu / Sat (Python weekday: Mon=0..Sun=6)
    assert POWER_655.draw_days == (1, 3, 5)


def test_mega_645_definition():
    assert MEGA_645.slug == "645"
    assert MEGA_645.code == "6/45"
    assert MEGA_645.ball_count == 6
    assert MEGA_645.ball_max == 45
    assert MEGA_645.has_special_ball is False
    assert MEGA_645.special_ball_max is None
    # Schedule: Wed / Fri / Sun
    assert MEGA_645.draw_days == (2, 4, 6)


def test_lotto_535_definition():
    assert LOTTO_535.slug == "535"
    assert LOTTO_535.code == "5/35"
    assert LOTTO_535.ball_count == 5
    assert LOTTO_535.ball_max == 35
    assert LOTTO_535.has_special_ball is True
    assert LOTTO_535.special_ball_max == 35


def test_all_products_tuple_contains_three():
    assert set(ALL_PRODUCTS) == {POWER_655, MEGA_645, LOTTO_535}
    assert len(ALL_PRODUCTS) == 3


def test_draw_time_components_in_valid_range():
    for product in ALL_PRODUCTS:
        hh, mm = product.draw_time_vn
        assert 0 <= hh < 24
        assert 0 <= mm < 60


def test_each_product_has_a_result_url():
    for product in ALL_PRODUCTS:
        assert product.result_url.startswith("https://")
        assert "vietlott.vn" in product.result_url


def test_sample_constructor_includes_result_url():
    # Local helper from earlier needs updating
    p = VietlottProduct(
        slug="x", name="X", code="1/1",
        ball_count=1, ball_min=1, ball_max=1,
        has_special_ball=False, special_ball_max=None,
        draw_days=(0,), draw_time_vn=(18, 0),
        result_url="https://vietlott.vn/sample",
    )
    assert p.result_url == "https://vietlott.vn/sample"
