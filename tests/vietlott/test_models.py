from datetime import date

import pytest
from pydantic import ValidationError

from vietlott.models import DrawResult, DrawResultList, PipelineReport
from vietlott.products import LOTTO_535, MEGA_645, POWER_655


def _ok_655_kwargs() -> dict:
    return dict(
        draw_id=1272,
        date=date(2025, 11, 22),
        product_code="6/55",
        balls=[8, 10, 19, 29, 34, 46],
        special_ball=14,
        jackpot_vnd=71_484_993_300,
    )


def test_draw_result_constructs_from_valid_kwargs():
    r = DrawResult(**_ok_655_kwargs())
    assert r.draw_id == 1272
    assert r.balls == [8, 10, 19, 29, 34, 46]
    assert r.jackpot_vnd == 71_484_993_300


def test_draw_result_rejects_unsorted_balls():
    kw = _ok_655_kwargs()
    kw["balls"] = [10, 8, 19, 29, 34, 46]
    with pytest.raises(ValidationError):
        DrawResult(**kw)


def test_validate_against_product_passes_for_matching_655():
    r = DrawResult(**_ok_655_kwargs())
    r.validate_against_product(POWER_655)  # no raise


def test_validate_against_product_rejects_wrong_ball_count():
    kw = _ok_655_kwargs()
    kw["balls"] = [8, 10, 19, 29, 34]  # 5 balls for a 6-ball game
    r = DrawResult.model_construct(**kw)
    with pytest.raises(ValueError, match="ball_count"):
        r.validate_against_product(POWER_655)


def test_validate_against_product_rejects_out_of_range_ball():
    kw = _ok_655_kwargs()
    kw["balls"] = [8, 10, 19, 29, 34, 60]  # 60 > 55
    r = DrawResult.model_construct(**kw)
    with pytest.raises(ValueError, match="range"):
        r.validate_against_product(POWER_655)


def test_validate_against_product_rejects_special_ball_when_disallowed():
    # 6/45 has no special ball
    r = DrawResult.model_construct(
        draw_id=1, date=date(2025, 11, 23), product_code="6/45",
        balls=[4, 12, 19, 42, 43, 44], special_ball=5, jackpot_vnd=1,
    )
    with pytest.raises(ValueError, match="special_ball"):
        r.validate_against_product(MEGA_645)


def test_validate_against_product_rejects_missing_special_ball_when_required():
    r = DrawResult.model_construct(
        draw_id=1, date=date(2025, 11, 24), product_code="5/35",
        balls=[5, 20, 24, 32, 33], special_ball=None, jackpot_vnd=1,
    )
    with pytest.raises(ValueError, match="special_ball"):
        r.validate_against_product(LOTTO_535)


def test_draw_result_list_roundtrip_json():
    r = DrawResult(**_ok_655_kwargs())
    lst = DrawResultList(root=[r])
    payload = lst.model_dump_json()
    restored = DrawResultList.model_validate_json(payload)
    assert restored.root == [r]


def test_draw_result_date_round_trips_as_iso():
    r = DrawResult(**_ok_655_kwargs())
    payload = r.model_dump_json()
    assert "\"2025-11-22\"" in payload


def test_pipeline_report_defaults():
    rep = PipelineReport(product_slug="655", new_count=0, total_count=10)
    assert rep.warnings == []
