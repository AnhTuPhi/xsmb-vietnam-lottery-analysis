from pathlib import Path

import pytest

from vietlott.errors import ParseError
from vietlott.parser import Parser
from vietlott.products import LOTTO_535, MEGA_645, POWER_655

FIXTURE_DIR = Path(__file__).parent.parent / "fixtures" / "vietlott"


def _load(slug: str) -> str:
    return (FIXTURE_DIR / f"{slug}-results.html").read_text(encoding="utf-8")


def test_parse_655_returns_nonempty_list_of_draw_results():
    parser = Parser()
    results = parser.parse(_load("655"), POWER_655)
    assert len(results) > 0
    for r in results:
        r.validate_against_product(POWER_655)
        assert r.product_code == "6/55"


def test_parse_645_returns_nonempty_list_of_draw_results():
    parser = Parser()
    results = parser.parse(_load("645"), MEGA_645)
    assert len(results) > 0
    for r in results:
        r.validate_against_product(MEGA_645)
        assert r.product_code == "6/45"
        assert r.special_ball is None


def test_parse_535_returns_nonempty_list_of_draw_results():
    parser = Parser()
    results = parser.parse(_load("535"), LOTTO_535)
    assert len(results) > 0
    for r in results:
        r.validate_against_product(LOTTO_535)
        assert r.product_code == "5/35"


def test_parse_655_first_row_matches_top_of_fixture():
    """Spot-check: the first parsed draw should match the topmost draw
    visible on the page. Replace `expected_*` values below with whatever
    the captured fixture actually shows on its first row.
    """
    parser = Parser()
    results = parser.parse(_load("655"), POWER_655)
    first = results[0]
    # Values from the top of 655-results.html (draw #01361, 20/06/2026)
    expected_draw_id: int = 1361
    expected_balls: list[int] = [16, 23, 26, 30, 52, 53]
    assert first.draw_id == expected_draw_id
    assert first.balls == expected_balls


def test_parse_raises_on_unrecognized_html():
    parser = Parser()
    with pytest.raises(ParseError):
        parser.parse("<html><body>nothing here</body></html>", POWER_655)
