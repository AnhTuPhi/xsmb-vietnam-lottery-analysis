import json
from datetime import date
from pathlib import Path

import pytest

from vietlott.models import DrawResult
from vietlott.products import MEGA_645, POWER_655
from vietlott.store import Store, migrate_legacy_json

FIXTURE_DIR = Path(__file__).parent.parent / "fixtures" / "vietlott"


def _make(draw_id: int, balls: list[int], special: int | None = 14) -> DrawResult:
    return DrawResult(
        draw_id=draw_id, date=date(2025, 11, 22),
        product_code="6/55", balls=balls,
        special_ball=special, jackpot_vnd=10**9,
    )


def test_load_returns_empty_when_file_missing(tmp_data_dir):
    store = Store(data_dir=tmp_data_dir)
    assert store.load(POWER_655) == []


def test_save_then_load_roundtrips(tmp_data_dir):
    store = Store(data_dir=tmp_data_dir)
    results = [_make(1, [1, 2, 3, 4, 5, 6]), _make(2, [7, 8, 9, 10, 11, 12])]
    store.save(POWER_655, results)

    loaded = store.load(POWER_655)
    assert loaded == results


def test_save_writes_to_expected_path(tmp_data_dir):
    store = Store(data_dir=tmp_data_dir)
    store.save(POWER_655, [_make(1, [1, 2, 3, 4, 5, 6])])
    assert (tmp_data_dir / "vietlott-655.json").exists()


def test_merge_dedupes_by_draw_id_and_prefers_existing():
    store = Store(data_dir=Path("/unused"))
    existing = [_make(1, [1, 2, 3, 4, 5, 6])]
    new = [
        _make(1, [10, 11, 12, 13, 14, 15]),  # same draw_id, different balls
        _make(2, [7, 8, 9, 10, 11, 12]),
    ]

    merged = store.merge(existing, new)

    assert len(merged) == 2
    by_id = {r.draw_id: r for r in merged}
    assert by_id[1].balls == [1, 2, 3, 4, 5, 6]  # existing won
    assert by_id[2].balls == [7, 8, 9, 10, 11, 12]


def test_merge_sorts_ascending_by_draw_id():
    store = Store(data_dir=Path("/unused"))
    out = store.merge(
        existing=[_make(3, [1, 2, 3, 4, 5, 6])],
        new=[_make(1, [7, 8, 9, 10, 11, 12]), _make(2, [13, 14, 15, 16, 17, 18])],
    )
    assert [r.draw_id for r in out] == [1, 2, 3]


def test_load_migrates_legacy_n8n_schema(tmp_data_dir):
    # Copy the legacy fixture into the data dir
    legacy = (FIXTURE_DIR / "655-legacy.json").read_text(encoding="utf-8")
    (tmp_data_dir / "vietlott-655.json").write_text(legacy, encoding="utf-8")

    store = Store(data_dir=tmp_data_dir)
    loaded = store.load(POWER_655)

    # Three legacy records, but one is a duplicate of another -> two unique
    assert len(loaded) == 2
    assert {r.draw_id for r in loaded} == {1272, 1273}
    first = next(r for r in loaded if r.draw_id == 1272)
    assert first.balls == [8, 10, 19, 29, 34, 46]
    assert first.special_ball == 14
    assert first.jackpot_vnd == 71_484_993_300
    assert first.date == date(2025, 11, 22)


def test_migrate_legacy_json_omits_special_ball_for_645():
    legacy = [{
        "product-message": "...",
        "title": "Kỳ quay thưởng #01436 ngày 23/11/2025",
        "product": "6/45",
        "balls": ["04", "12", "19", "42", "43", "44"],
        "prize": "51.704.246.500",
    }]
    out = migrate_legacy_json(legacy, MEGA_645)
    assert len(out) == 1
    assert out[0].special_ball is None
    assert out[0].jackpot_vnd == 51_704_246_500


def test_save_after_load_writes_new_schema(tmp_data_dir):
    legacy = (FIXTURE_DIR / "655-legacy.json").read_text(encoding="utf-8")
    (tmp_data_dir / "vietlott-655.json").write_text(legacy, encoding="utf-8")
    store = Store(data_dir=tmp_data_dir)

    results = store.load(POWER_655)
    store.save(POWER_655, results)

    on_disk = json.loads((tmp_data_dir / "vietlott-655.json").read_text(encoding="utf-8"))
    assert isinstance(on_disk, list)
    # New schema: no "product-message" key, draw_id is int, date is ISO
    assert "product-message" not in on_disk[0]
    assert isinstance(on_disk[0]["draw_id"], int)
    assert on_disk[0]["date"] == "2025-11-22"
