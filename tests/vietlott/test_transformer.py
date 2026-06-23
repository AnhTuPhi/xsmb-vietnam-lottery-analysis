from datetime import date
from pathlib import Path

import pandas as pd

from vietlott.models import DrawResult
from vietlott.products import LOTTO_535, MEGA_645, POWER_655
from vietlott.transformer import Transformer


def _655(draw_id: int, balls: list[int], special: int) -> DrawResult:
    return DrawResult(
        draw_id=draw_id, date=date(2025, 11, 22),
        product_code="6/55", balls=balls,
        special_ball=special, jackpot_vnd=10**9,
    )


def _645(draw_id: int, balls: list[int]) -> DrawResult:
    return DrawResult(
        draw_id=draw_id, date=date(2025, 11, 23),
        product_code="6/45", balls=balls,
        special_ball=None, jackpot_vnd=10**9,
    )


def test_raw_dataframe_655_has_expected_columns():
    t = Transformer()
    df = t.to_raw_dataframe([_655(1, [1, 2, 3, 4, 5, 6], special=7)], POWER_655)
    assert list(df.columns) == [
        "draw_id", "date",
        "ball_1", "ball_2", "ball_3", "ball_4", "ball_5", "ball_6",
        "special_ball", "jackpot_vnd",
    ]
    assert df.loc[0, "ball_1"] == 1
    assert df.loc[0, "special_ball"] == 7


def test_raw_dataframe_645_omits_special_ball_column():
    t = Transformer()
    df = t.to_raw_dataframe([_645(1, [1, 2, 3, 4, 5, 6])], MEGA_645)
    assert "special_ball" not in df.columns
    assert df.shape == (1, 9)  # draw_id, date, ball_1..6, jackpot_vnd


def test_sparse_dataframe_655_marks_drawn_balls_with_one():
    t = Transformer()
    df = t.to_sparse_dataframe([_655(1, [1, 5, 10, 20, 30, 55], special=42)], POWER_655)
    # 1 for drawn balls, 0 otherwise
    assert df.loc[0, "n_01"] == 1
    assert df.loc[0, "n_02"] == 0
    assert df.loc[0, "n_55"] == 1
    assert df.loc[0, "sp_42"] == 1
    assert df.loc[0, "sp_01"] == 0


def test_sparse_dataframe_645_has_no_sp_columns():
    t = Transformer()
    df = t.to_sparse_dataframe([_645(1, [1, 2, 3, 4, 5, 6])], MEGA_645)
    assert not any(c.startswith("sp_") for c in df.columns)
    assert "n_45" in df.columns


def test_sparse_dataframe_535_has_correct_sp_range():
    t = Transformer()
    r = DrawResult(
        draw_id=1, date=date(2025, 11, 24),
        product_code="5/35", balls=[5, 20, 24, 32, 33],
        special_ball=5, jackpot_vnd=1,
    )
    df = t.to_sparse_dataframe([r], LOTTO_535)
    assert "sp_35" in df.columns
    assert "sp_36" not in df.columns


def test_dump_writes_all_six_files(tmp_data_dir: Path):
    t = Transformer()
    t.dump([_655(1, [1, 2, 3, 4, 5, 6], special=7)], POWER_655, out_dir=tmp_data_dir)
    expected = {
        "vietlott-655.csv", "vietlott-655.json", "vietlott-655.parquet",
        "vietlott-655-sparse.csv", "vietlott-655-sparse.json", "vietlott-655-sparse.parquet",
    }
    assert {p.name for p in tmp_data_dir.iterdir()} >= expected


def test_dump_645_does_not_write_sp_columns_into_parquet(tmp_data_dir: Path):
    t = Transformer()
    t.dump([_645(1, [1, 2, 3, 4, 5, 6])], MEGA_645, out_dir=tmp_data_dir)
    sparse = pd.read_parquet(tmp_data_dir / "vietlott-645-sparse.parquet")
    assert not any(c.startswith("sp_") for c in sparse.columns)
