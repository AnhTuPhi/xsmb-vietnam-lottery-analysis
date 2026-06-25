# Vietlott Data Layer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a self-contained Python data layer that crawls, normalizes, dedupes, and publishes Power 6/55, Mega 6/45, and Lotto 5/35 results — replacing the current n8n ingestion.

**Architecture:** A2 from the spec — five components with single responsibilities (`Fetcher` for HTTP, `Parser` for HTML→model, `Store` for canonical JSON I/O + dedup, `Transformer` for DataFrames + dump, `Pipeline` to orchestrate). One `VietlottProduct` config per product flows through them. New `src/vietlott/` subpackage; existing XSMB code is not touched.

**Tech Stack:** Python 3.13 (CI), pydantic 2.11, cloudscraper, beautifulsoup4 + lxml, pandas 2.2, pyarrow, pytest, loguru, GitHub Actions.

**Companion spec:** `docs/superpowers/specs/2026-06-20-vietlott-data-layer-design.md` (commit `9998573`).

## Global Constraints

- Python: 3.13 in CI (`.github/workflows/fetch-and-analyze-data.yml` shows `python-version: '3.13'`); local dev must use ≥ 3.10 because of pydantic 2.11 / pandas 2.2 / numpy 2.2 floors.
- Dependency pins: do not change versions already in `requirements.txt`. Add new deps with pinned versions.
- Source code lives under `src/vietlott/` (new subpackage). Existing flat files under `src/` (`lottery.py`, `analyze.py`, `fetch.py`, `model.py`, `notification.py`, `telegram.py`) MUST NOT be touched in this plan.
- Data outputs land in `data/` using slugged names: `data/vietlott-{slug}.{csv,json,parquet}` and `data/vietlott-{slug}-sparse.{csv,json,parquet}`. Slugs are `655`, `645`, `535`.
- Timezone for draw scheduling: `Asia/Ho_Chi_Minh` (use `zoneinfo.ZoneInfo`, available stdlib on 3.9+).
- Primary key for a draw is `draw_id` (an int parsed from `"Kỳ quay thưởng #NNNNN"`); dedup prefers the existing record on conflict.
- Pipeline failures on one product MUST NOT abort the run for other products. Per-product try/except in the entrypoint.
- Commit message convention: `feat(vietlott): …` / `test(vietlott): …` / `chore(vietlott): …`. Every commit ends with the `Co-Authored-By` trailer used by the spec commit.
- Pre-existing files in `data/vietlott-*.json` are the n8n schema. The Store layer migrates them on first run; do not hand-edit them in any task.

---

## File Structure

**Created in this plan:**

```
src/vietlott/
  __init__.py
  products.py          # VietlottProduct dataclass + POWER_655 / MEGA_645 / LOTTO_535
  models.py            # DrawResult, DrawResultList, PipelineReport
  errors.py            # FetchError, ParseError
  fetcher.py           # Fetcher (HTTP)
  parser.py            # Parser (HTML → DrawResult)
  store.py             # Store + migrate_legacy_json
  transformer.py       # Transformer (DataFrames + dump)
  pipeline.py          # Pipeline orchestrator
src/vietlott_fetch.py  # GitHub Actions entry point

tests/
  __init__.py
  conftest.py          # shared fixtures (tmp data dir, sample DrawResults)
  vietlott/
    __init__.py
    test_products.py
    test_models.py
    test_fetcher.py
    test_parser.py
    test_store.py
    test_transformer.py
    test_pipeline.py
    test_entrypoint.py
  fixtures/vietlott/
    655-results.html   # captured live in Task 3
    645-results.html   # captured live in Task 3
    535-results.html   # captured live in Task 3
    655-legacy.json    # hand-built migration sample

scripts/
  capture_vietlott_fixtures.py   # one-off helper to fetch live HTML

.github/workflows/
  vietlott.yml         # cron + manual trigger

docs/
  vietlott-source-notes.md  # findings from Task 3 (URLs, DOM, schedules)

pyproject.toml         # pytest config (project doesn't have one yet)
```

**Modified in this plan:**

- `requirements.txt` — add `pytest==8.3.4`.
- `.gitignore` — already excludes `__pycache__`, `.pytest_cache`. No change needed.

**Not touched:** any file under `src/` other than the new subpackage and `src/vietlott_fetch.py`. The XSMB workflow file (`fetch-and-analyze-data.yml`) is left alone.

---

## Task Dependency Order

1. Test scaffold + `VietlottProduct` config (without `result_url`).
2. `DrawResult` / `DrawResultList` Pydantic models.
3. Source investigation: discover URLs, verify schedules, capture HTML fixtures, add `result_url`.
4. `Fetcher` (mocked HTTP in tests).
5. `Parser` (against captured fixtures).
6. `Store` + `migrate_legacy_json`.
7. `Transformer`.
8. `Pipeline` orchestrator.
9. Entry point script + GitHub Actions workflow.
10. End-to-end manual verification + n8n cutover.

Task 3 is the only manual investigation step and unblocks tasks 4 and 5. Everything else is straightforward TDD.

---

## Task 1: Test scaffold + `VietlottProduct` config

**Files:**
- Create: `pyproject.toml`
- Create: `src/vietlott/__init__.py` (empty)
- Create: `src/vietlott/products.py`
- Create: `tests/__init__.py` (empty)
- Create: `tests/conftest.py`
- Create: `tests/vietlott/__init__.py` (empty)
- Create: `tests/vietlott/test_products.py`
- Modify: `requirements.txt` — append `pytest==8.3.4`

**Interfaces:**
- Consumes: nothing (this is the foundation).
- Produces:
  - `vietlott.products.VietlottProduct` — frozen dataclass with fields: `slug: str`, `name: str`, `code: str`, `ball_count: int`, `ball_min: int`, `ball_max: int`, `has_special_ball: bool`, `special_ball_max: int | None`, `draw_days: tuple[int, ...]`, `draw_time_vn: tuple[int, int]`. (No `result_url` yet — added in Task 3.)
  - Module constants `POWER_655`, `MEGA_645`, `LOTTO_535`.
  - Helper `ALL_PRODUCTS: tuple[VietlottProduct, ...]`.

- [ ] **Step 1: Add pytest to requirements**

Append to `requirements.txt` (after the existing `loguru==0.7.3` line):

```
pytest==8.3.4
```

- [ ] **Step 2: Create `pyproject.toml` for pytest config**

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]
addopts = "-ra --strict-markers"
```

`pythonpath = ["src"]` lets tests `import vietlott` without an editable install.

- [ ] **Step 3: Create the test package skeleton**

Create empty files:
- `tests/__init__.py`
- `tests/vietlott/__init__.py`
- `src/vietlott/__init__.py`

And `tests/conftest.py` with a tmp-dir fixture used by later tasks:

```python
import pytest
from pathlib import Path

@pytest.fixture
def tmp_data_dir(tmp_path: Path) -> Path:
    d = tmp_path / "data"
    d.mkdir()
    return d
```

- [ ] **Step 4: Write the failing test for `VietlottProduct` and the three constants**

Create `tests/vietlott/test_products.py`:

```python
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
```

- [ ] **Step 5: Run tests to verify they fail**

Run: `pytest tests/vietlott/test_products.py -v`
Expected: All tests FAIL with `ImportError: cannot import name 'VietlottProduct' from 'vietlott.products'`.

- [ ] **Step 6: Implement `VietlottProduct` and the three constants**

Create `src/vietlott/products.py`:

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class VietlottProduct:
    slug: str
    name: str
    code: str
    ball_count: int
    ball_min: int
    ball_max: int
    has_special_ball: bool
    special_ball_max: int | None
    draw_days: tuple[int, ...]
    draw_time_vn: tuple[int, int]


POWER_655 = VietlottProduct(
    slug="655",
    name="Power 6/55",
    code="6/55",
    ball_count=6,
    ball_min=1,
    ball_max=55,
    has_special_ball=True,
    special_ball_max=55,
    draw_days=(1, 3, 5),  # Tue, Thu, Sat
    draw_time_vn=(18, 30),
)

MEGA_645 = VietlottProduct(
    slug="645",
    name="Mega 6/45",
    code="6/45",
    ball_count=6,
    ball_min=1,
    ball_max=45,
    has_special_ball=False,
    special_ball_max=None,
    draw_days=(2, 4, 6),  # Wed, Fri, Sun
    draw_time_vn=(18, 30),
)

LOTTO_535 = VietlottProduct(
    slug="535",
    name="Lotto 5/35",
    code="5/35",
    ball_count=5,
    ball_min=1,
    ball_max=35,
    has_special_ball=True,
    special_ball_max=35,
    draw_days=(0, 1, 2, 3, 4, 5, 6),  # to be verified in Task 3
    draw_time_vn=(18, 0),
)

ALL_PRODUCTS: tuple[VietlottProduct, ...] = (POWER_655, MEGA_645, LOTTO_535)
```

- [ ] **Step 7: Run tests to verify they pass**

Run: `pytest tests/vietlott/test_products.py -v`
Expected: 6 passed.

- [ ] **Step 8: Commit**

```bash
git add pyproject.toml requirements.txt src/vietlott/__init__.py src/vietlott/products.py \
        tests/__init__.py tests/conftest.py tests/vietlott/__init__.py tests/vietlott/test_products.py
git commit -m "$(cat <<'EOF'
feat(vietlott): add VietlottProduct config and test scaffold

Introduces src/vietlott/ subpackage with frozen VietlottProduct dataclass
and POWER_655 / MEGA_645 / LOTTO_535 constants. Bootstraps pytest with
pyproject.toml and a tests/ tree under src-path import.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: `DrawResult` and `DrawResultList` Pydantic models

**Files:**
- Create: `src/vietlott/models.py`
- Create: `tests/vietlott/test_models.py`

**Interfaces:**
- Consumes: `vietlott.products.VietlottProduct` (Task 1) — for validation against product rules.
- Produces:
  - `vietlott.models.DrawResult` — pydantic `BaseModel` with fields: `draw_id: int`, `date: datetime.date`, `product_code: str`, `balls: list[int]` (sorted ascending), `special_ball: int | None`, `jackpot_vnd: int`.
  - `vietlott.models.DrawResultList` — `RootModel[list[DrawResult]]`.
  - `vietlott.models.PipelineReport` — pydantic `BaseModel` with fields: `product_slug: str`, `new_count: int`, `total_count: int`, `warnings: list[str]`. Defined here because it's shared by Pipeline (Task 8) and the entrypoint (Task 9).
  - Helper classmethod `DrawResult.validate_against_product(self, product) -> None` raising `ValueError` if shape doesn't match.

- [ ] **Step 1: Write the failing test**

Create `tests/vietlott/test_models.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/vietlott/test_models.py -v`
Expected: All FAIL with `ImportError`.

- [ ] **Step 3: Implement the models**

Create `src/vietlott/models.py`:

```python
from datetime import date as _date
from typing import Self

from pydantic import BaseModel, Field, RootModel, field_validator

from vietlott.products import VietlottProduct


class DrawResult(BaseModel):
    draw_id: int = Field(ge=1)
    date: _date
    product_code: str
    balls: list[int]
    special_ball: int | None = None
    jackpot_vnd: int = Field(ge=0)

    @field_validator("balls")
    @classmethod
    def _balls_sorted_ascending(cls, v: list[int]) -> list[int]:
        if v != sorted(v):
            raise ValueError("balls must be sorted ascending")
        return v

    def validate_against_product(self, product: VietlottProduct) -> None:
        if len(self.balls) != product.ball_count:
            raise ValueError(
                f"ball_count mismatch: got {len(self.balls)}, expected {product.ball_count}"
            )
        for b in self.balls:
            if not (product.ball_min <= b <= product.ball_max):
                raise ValueError(
                    f"ball {b} out of range [{product.ball_min}, {product.ball_max}]"
                )
        if product.has_special_ball:
            if self.special_ball is None:
                raise ValueError("special_ball required for this product")
            assert product.special_ball_max is not None  # type narrowing
            if not (product.ball_min <= self.special_ball <= product.special_ball_max):
                raise ValueError(
                    f"special_ball {self.special_ball} out of range"
                )
        else:
            if self.special_ball is not None:
                raise ValueError("special_ball not allowed for this product")


class DrawResultList(RootModel[list[DrawResult]]):
    pass


class PipelineReport(BaseModel):
    product_slug: str
    new_count: int
    total_count: int
    warnings: list[str] = Field(default_factory=list)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/vietlott/test_models.py -v`
Expected: 10 passed.

- [ ] **Step 5: Commit**

```bash
git add src/vietlott/models.py tests/vietlott/test_models.py
git commit -m "$(cat <<'EOF'
feat(vietlott): add DrawResult and DrawResultList pydantic models

DrawResult validates balls are sorted ascending at construction time;
validate_against_product checks ball_count, ball range, and special_ball
presence/range against a VietlottProduct config. PipelineReport carries
per-run counts and warnings for the orchestrator.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: Source investigation, schedule verification, fixture capture

**This is the one manual task in the plan.** It produces three artifacts that later tasks depend on:
1. `result_url` for each product, added to `VietlottProduct`.
2. Verified `draw_days` for Lotto 5/35 (other two products are confirmed from the existing JSON; 5/35 is set to "every day" as a placeholder in Task 1).
3. Captured live HTML fixtures used by Parser tests.

**Files:**
- Create: `docs/vietlott-source-notes.md` — findings written down
- Create: `scripts/__init__.py` (empty) — let pytest's pythonpath leave it alone; this is just a package marker so `scripts/` is importable if needed
- Create: `scripts/capture_vietlott_fixtures.py` — one-shot helper
- Create: `tests/fixtures/__init__.py` (empty marker — not strictly needed, but keeps the tree consistent)
- Create: `tests/fixtures/vietlott/655-results.html` (captured)
- Create: `tests/fixtures/vietlott/645-results.html` (captured)
- Create: `tests/fixtures/vietlott/535-results.html` (captured)
- Modify: `src/vietlott/products.py` — add `result_url: str` to dataclass and to all three constants
- Modify: `tests/vietlott/test_products.py` — assert `result_url` is set and non-empty for each product

**Interfaces:**
- Consumes: `VietlottProduct` (Task 1).
- Produces:
  - `VietlottProduct.result_url: str`.
  - HTML fixtures at known paths used by Task 5.
  - `docs/vietlott-source-notes.md` documenting URL patterns, table/element selectors for each product, and verified draw schedules.

- [ ] **Step 1: Investigate vietlott.vn manually (no code yet)**

Open each product's results page in a browser. As of writing, the patterns are typically:

- Power 6/55: `https://vietlott.vn/vi/trung-thuong/ket-qua-trung-thuong/power-655`
- Mega 6/45: `https://vietlott.vn/vi/trung-thuong/ket-qua-trung-thuong/mega-645`
- Lotto 5/35: `https://vietlott.vn/vi/trung-thuong/ket-qua-trung-thuong/max-535` (verify the slug — the official product name has changed before).

Record in `docs/vietlott-source-notes.md`:
- Exact URL for each product.
- The CSS / element pattern that contains a single draw row (e.g. a table row containing the draw ID, date, balls, special ball, jackpot).
- How the draw date is formatted in the DOM (e.g. `dd/mm/yyyy`).
- How balls are presented (separate `<span>` per ball? comma-joined string?).
- How the jackpot value is formatted (dot-separated thousands, currency suffix?).
- The 5/35 draw schedule (which days does it actually draw? Update if the Task 1 placeholder of "every day" is wrong).

- [ ] **Step 2: Write `scripts/capture_vietlott_fixtures.py`**

This one-off script fetches each product page once and saves the HTML.

```python
"""One-shot helper: fetch live vietlott.vn pages and save HTML fixtures.

Run manually: `python scripts/capture_vietlott_fixtures.py`
"""
from pathlib import Path

from cloudscraper import CloudScraper

URLS = {
    "655": "https://vietlott.vn/vi/trung-thuong/ket-qua-trung-thuong/power-655",
    "645": "https://vietlott.vn/vi/trung-thuong/ket-qua-trung-thuong/mega-645",
    "535": "https://vietlott.vn/vi/trung-thuong/ket-qua-trung-thuong/max-535",
}

OUT_DIR = Path("tests/fixtures/vietlott")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    http = CloudScraper()
    for slug, url in URLS.items():
        resp = http.get(url)
        resp.raise_for_status()
        target = OUT_DIR / f"{slug}-results.html"
        target.write_text(resp.text, encoding="utf-8")
        print(f"Saved {target} ({len(resp.text)} bytes) from {url}")


if __name__ == "__main__":
    main()
```

Update the URLs above to whatever Step 1 confirmed.

- [ ] **Step 3: Run the capture script once**

Run: `python scripts/capture_vietlott_fixtures.py`
Expected: three files appear under `tests/fixtures/vietlott/`. Open each one and confirm it contains draw data (not a Cloudflare interstitial). If Cloudflare blocks the fetch, see the troubleshooting note at the end of this task.

- [ ] **Step 4: Add `result_url` to `VietlottProduct` and the three constants**

Edit `src/vietlott/products.py`:

```python
@dataclass(frozen=True)
class VietlottProduct:
    slug: str
    name: str
    code: str
    ball_count: int
    ball_min: int
    ball_max: int
    has_special_ball: bool
    special_ball_max: int | None
    draw_days: tuple[int, ...]
    draw_time_vn: tuple[int, int]
    result_url: str   # NEW
```

Add `result_url=...` to each of `POWER_655`, `MEGA_645`, `LOTTO_535` using the verified URLs from Step 1.

If the 5/35 schedule investigation in Step 1 turned up different `draw_days`, update them too.

- [ ] **Step 5: Extend the product test to cover `result_url`**

Append to `tests/vietlott/test_products.py`:

```python
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
```

Also update the existing `_sample()` helper at the top of `test_products.py` to include `result_url="https://vietlott.vn/sample"`.

- [ ] **Step 6: Run product tests to verify they still pass**

Run: `pytest tests/vietlott/test_products.py -v`
Expected: all pass (8 tests now).

- [ ] **Step 7: Write `docs/vietlott-source-notes.md`**

Capture findings from Step 1: URL per product, selector strategy for the Parser, sample of a single draw row from each fixture, draw schedule verification result for 5/35. This becomes the parser's specification.

- [ ] **Step 8: Commit**

```bash
git add docs/vietlott-source-notes.md scripts/capture_vietlott_fixtures.py \
        tests/fixtures/vietlott/ src/vietlott/products.py tests/vietlott/test_products.py
git commit -m "$(cat <<'EOF'
feat(vietlott): add source URLs, capture HTML fixtures, document selectors

Verified vietlott.vn URLs for Power 6/55, Mega 6/45, Lotto 5/35.
Captured live HTML to tests/fixtures/vietlott/ for parser tests.
Added result_url to VietlottProduct; documented DOM selectors and draw
schedules in docs/vietlott-source-notes.md.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

**Troubleshooting:** if `cloudscraper` returns a Cloudflare challenge page, try the same call from a normal `requests.Session` with a realistic User-Agent first, or open the page in your browser, save it as `tests/fixtures/vietlott/{slug}-results.html` manually, and skip the helper script. Either approach produces the same fixture file the parser needs.

---

## Task 4: `Fetcher` (HTTP layer)

**Files:**
- Create: `src/vietlott/errors.py`
- Create: `src/vietlott/fetcher.py`
- Create: `tests/vietlott/test_fetcher.py`

**Interfaces:**
- Consumes: `VietlottProduct.result_url` (added in Task 3).
- Produces:
  - `vietlott.errors.FetchError`, `vietlott.errors.ParseError` — `Exception` subclasses.
  - `vietlott.fetcher.Fetcher` with constructor `Fetcher(http=None)` and methods:
    - `fetch_results_page(product: VietlottProduct) -> str`
    - `fetch_archive_page(product: VietlottProduct, page: int) -> str` (constructs `f"{product.result_url}?page={page}"`).
  - Both methods raise `FetchError` on non-200, including status code in the message.

- [ ] **Step 1: Write the failing test**

Create `tests/vietlott/test_fetcher.py`:

```python
from unittest.mock import MagicMock

import pytest

from vietlott.errors import FetchError
from vietlott.fetcher import Fetcher
from vietlott.products import POWER_655


def _fake_http(status: int, text: str) -> MagicMock:
    response = MagicMock(status_code=status, text=text)
    http = MagicMock()
    http.get.return_value = response
    return http


def test_fetch_results_page_returns_html_on_200():
    http = _fake_http(200, "<html>ok</html>")
    fetcher = Fetcher(http=http)

    result = fetcher.fetch_results_page(POWER_655)

    assert result == "<html>ok</html>"
    http.get.assert_called_once_with(POWER_655.result_url)


def test_fetch_results_page_raises_on_non_200():
    http = _fake_http(503, "boom")
    fetcher = Fetcher(http=http)

    with pytest.raises(FetchError, match="503"):
        fetcher.fetch_results_page(POWER_655)


def test_fetch_archive_page_appends_page_query_param():
    http = _fake_http(200, "<html>archive</html>")
    fetcher = Fetcher(http=http)

    result = fetcher.fetch_archive_page(POWER_655, page=3)

    assert result == "<html>archive</html>"
    http.get.assert_called_once_with(f"{POWER_655.result_url}?page=3")


def test_fetcher_default_constructs_a_cloudscraper():
    # No explicit http arg — defaults to a real CloudScraper instance.
    fetcher = Fetcher()
    # We don't make a real call, just check the attribute is set.
    assert fetcher._http is not None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/vietlott/test_fetcher.py -v`
Expected: ImportError.

- [ ] **Step 3: Implement `errors` and `Fetcher`**

Create `src/vietlott/errors.py`:

```python
class FetchError(Exception):
    """Raised when fetching a vietlott.vn page fails."""


class ParseError(Exception):
    """Raised when the fetched HTML can't be parsed into DrawResults."""
```

Create `src/vietlott/fetcher.py`:

```python
from typing import Any

from cloudscraper import CloudScraper

from vietlott.errors import FetchError
from vietlott.products import VietlottProduct


class Fetcher:
    def __init__(self, http: Any | None = None) -> None:
        self._http = http if http is not None else CloudScraper()

    def fetch_results_page(self, product: VietlottProduct) -> str:
        return self._get(product.result_url)

    def fetch_archive_page(self, product: VietlottProduct, page: int) -> str:
        return self._get(f"{product.result_url}?page={page}")

    def _get(self, url: str) -> str:
        resp = self._http.get(url)
        if resp.status_code != 200:
            raise FetchError(f"GET {url} returned status {resp.status_code}")
        return resp.text
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/vietlott/test_fetcher.py -v`
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add src/vietlott/errors.py src/vietlott/fetcher.py tests/vietlott/test_fetcher.py
git commit -m "$(cat <<'EOF'
feat(vietlott): add Fetcher with mocked HTTP tests

Fetcher wraps CloudScraper, raises FetchError on non-200 responses.
Exposes fetch_results_page and fetch_archive_page; the latter is for
the backfill sub-project but tested here for symmetry. Tests inject a
fake http client so no network is touched in CI.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 5: `Parser` (HTML → DrawResult)

**Files:**
- Create: `src/vietlott/parser.py`
- Create: `tests/vietlott/test_parser.py`

**Interfaces:**
- Consumes:
  - `VietlottProduct` (Task 1, extended in Task 3).
  - `DrawResult` (Task 2) and its `validate_against_product`.
  - `ParseError` (Task 4).
  - HTML fixtures under `tests/fixtures/vietlott/` (Task 3).
- Produces:
  - `vietlott.parser.Parser` with method `parse(html: str, product: VietlottProduct) -> list[DrawResult]`.
  - On unrecognized structure, raises `ParseError` with an HTML snippet (≤ 200 chars) for debugging.

The exact selectors depend on what Task 3's investigation found. The implementation strategy below is generic; substitute the real selectors documented in `docs/vietlott-source-notes.md`.

- [ ] **Step 1: Write the failing test against captured fixtures**

Create `tests/vietlott/test_parser.py`:

```python
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
    # ⬇️ Replace these with the actual values from the top of 655-results.html.
    # After running this test once you'll see the actual values printed on
    # failure; copy them into these assertions and re-run.
    expected_draw_id: int = ...  # noqa
    expected_balls: list[int] = ...  # noqa
    assert first.draw_id == expected_draw_id
    assert first.balls == expected_balls


def test_parse_raises_on_unrecognized_html():
    parser = Parser()
    with pytest.raises(ParseError):
        parser.parse("<html><body>nothing here</body></html>", POWER_655)
```

**Note on the spot-check test:** keep the `...` placeholders in place when first running the test. The test will FAIL with a TypeError on the `==` comparison, but more usefully you'll see the actual `first` value in the failure output. Copy the real values into the assertions, then re-run.

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/vietlott/test_parser.py -v`
Expected: ImportError on `Parser`.

- [ ] **Step 3: Implement the Parser**

Create `src/vietlott/parser.py`. The skeleton below follows the spec; replace the body of `_extract_rows` and `_parse_row` with the selectors documented in `docs/vietlott-source-notes.md`.

```python
import re
from datetime import datetime

from bs4 import BeautifulSoup, Tag

from vietlott.errors import ParseError
from vietlott.models import DrawResult
from vietlott.products import VietlottProduct

_DRAW_ID_RE = re.compile(r"#0*(\d+)")  # "Kỳ quay thưởng #01272" -> 1272
_DATE_RE = re.compile(r"(\d{2})/(\d{2})/(\d{4})")


class Parser:
    def parse(self, html: str, product: VietlottProduct) -> list[DrawResult]:
        soup = BeautifulSoup(html, "lxml")
        rows = self._extract_rows(soup, product)
        if not rows:
            snippet = html[:200].replace("\n", " ")
            raise ParseError(
                f"No draw rows found for {product.slug}. HTML snippet: {snippet!r}"
            )
        results: list[DrawResult] = []
        for row in rows:
            try:
                results.append(self._parse_row(row, product))
            except (ValueError, AttributeError) as exc:
                # Skip this row but record the warning indirectly by re-raising
                # only if we got zero usable results overall.
                snippet = str(row)[:200]
                raise ParseError(f"Failed to parse row: {exc}; snippet: {snippet!r}") from exc
        return results

    def _extract_rows(self, soup: BeautifulSoup, product: VietlottProduct) -> list[Tag]:
        # TODO(Task 5 implementer): replace with the selector documented in
        # docs/vietlott-source-notes.md, e.g.
        #   return soup.select("table.result-table tbody tr")
        raise NotImplementedError("populate selector from docs/vietlott-source-notes.md")

    def _parse_row(self, row: Tag, product: VietlottProduct) -> DrawResult:
        # TODO(Task 5 implementer): extract the per-row data from `row`
        # using the documented selectors. The helpers below cover the
        # generic transformation work once you have raw strings.
        raise NotImplementedError("populate field extraction from docs/vietlott-source-notes.md")

    # ----- Field-level helpers (selector-agnostic, ready to call) -----

    @staticmethod
    def _parse_draw_id(title_text: str) -> int:
        m = _DRAW_ID_RE.search(title_text)
        if not m:
            raise ValueError(f"draw_id not found in {title_text!r}")
        return int(m.group(1))

    @staticmethod
    def _parse_date(text: str):
        m = _DATE_RE.search(text)
        if not m:
            raise ValueError(f"date not found in {text!r}")
        day, month, year = map(int, m.groups())
        return datetime(year, month, day).date()

    @staticmethod
    def _parse_balls(raw_values: list[str]) -> list[int]:
        return sorted(int(v) for v in raw_values)

    @staticmethod
    def _parse_jackpot_vnd(text: str) -> int:
        digits = re.sub(r"[^\d]", "", text)
        if not digits:
            raise ValueError(f"jackpot value not found in {text!r}")
        return int(digits)
```

**Implementer note:** the two `NotImplementedError` raises above must be replaced with real selector logic before the test passes. The expected pattern is:

```python
def _extract_rows(self, soup, product):
    return soup.select("...")  # selector from docs/vietlott-source-notes.md

def _parse_row(self, row, product):
    title_el = row.select_one("...")
    balls = [el.get_text(strip=True) for el in row.select("...")]
    special_el = row.select_one("...") if product.has_special_ball else None
    jackpot_el = row.select_one("...")
    return DrawResult(
        draw_id=self._parse_draw_id(title_el.get_text()),
        date=self._parse_date(title_el.get_text()),
        product_code=product.code,
        balls=self._parse_balls(balls),
        special_ball=int(special_el.get_text(strip=True)) if special_el else None,
        jackpot_vnd=self._parse_jackpot_vnd(jackpot_el.get_text()),
    )
```

- [ ] **Step 4: Run tests, then fill in the spot-check expected values from the failure output, then re-run**

Run: `pytest tests/vietlott/test_parser.py -v`
First run expectation: all three `parse_*_returns_nonempty_list` tests PASS, the spot-check FAILS showing actual values, the `parse_raises_on_unrecognized_html` test PASSES.

Update `expected_draw_id` and `expected_balls` in the spot-check test from the failure output. Re-run; all five tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/vietlott/parser.py tests/vietlott/test_parser.py
git commit -m "$(cat <<'EOF'
feat(vietlott): add Parser for Power 6/55, Mega 6/45, Lotto 5/35

Parses vietlott.vn results pages into DrawResult lists using the
selectors documented in docs/vietlott-source-notes.md. Validates each
row against its product's rules; raises ParseError with an HTML
snippet on unrecognized structure.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 6: `Store` (canonical JSON I/O + dedup + legacy migration)

**Files:**
- Create: `src/vietlott/store.py`
- Create: `tests/fixtures/vietlott/655-legacy.json` (small migration sample, hand-built)
- Create: `tests/vietlott/test_store.py`

**Interfaces:**
- Consumes: `DrawResult`, `DrawResultList` (Task 2); `VietlottProduct.slug` (Task 1).
- Produces:
  - `vietlott.store.Store(data_dir: Path = Path("data"))` with methods:
    - `load(product: VietlottProduct) -> list[DrawResult]`
    - `save(product: VietlottProduct, results: list[DrawResult]) -> None`
    - `merge(existing: list[DrawResult], new: list[DrawResult]) -> list[DrawResult]`
  - Module-level `migrate_legacy_json(legacy: list[dict], product: VietlottProduct) -> list[DrawResult]`.
  - `load` auto-detects legacy schema (presence of `product-message` key) and migrates on the fly. The first subsequent `save` writes the new schema, replacing the legacy file in place.

- [ ] **Step 1: Build a small legacy fixture**

Copy 3 records out of the existing `data/vietlott-655.json` (which still has the n8n schema) and save them as `tests/fixtures/vietlott/655-legacy.json`. Include at least one duplicate so the migration test covers dedup. Example contents (real prize values and draw IDs):

```json
[
  {"product-message":"Kết quả quay số mở thưởng POWER 6/55","title":"Kỳ quay thưởng #01272 ngày 22/11/2025","product":"6/55","balls":["08","10","19","29","34","46"],"special_ball":"14","prize_1":"71.484.993.300"},
  {"product-message":"Kết quả quay số mở thưởng POWER 6/55","title":"Kỳ quay thưởng #01272 ngày 22/11/2025","product":"6/55","balls":["08","10","19","29","34","46"],"special_ball":"14","prize_1":"71.484.993.300"},
  {"product-message":"Kết quả quay số mở thưởng POWER 6/55","title":"Kỳ quay thưởng #01273 ngày 25/11/2025","product":"6/55","balls":["23","31","32","42","46","48"],"special_ball":"04","prize_1":"74.915.017.950"}
]
```

- [ ] **Step 2: Write the failing test**

Create `tests/vietlott/test_store.py`:

```python
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
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `pytest tests/vietlott/test_store.py -v`
Expected: ImportError.

- [ ] **Step 4: Implement `Store` and `migrate_legacy_json`**

Create `src/vietlott/store.py`:

```python
import json
import re
from datetime import datetime
from pathlib import Path

from vietlott.models import DrawResult, DrawResultList
from vietlott.products import VietlottProduct

_DRAW_ID_RE = re.compile(r"#0*(\d+)")
_DATE_RE = re.compile(r"(\d{2})/(\d{2})/(\d{4})")


def _is_legacy_record(record: dict) -> bool:
    return "product-message" in record or "draw_id" not in record


def _parse_legacy_prize(record: dict) -> int:
    raw = record.get("prize") or record.get("prize_1") or "0"
    digits = re.sub(r"[^\d]", "", raw)
    return int(digits) if digits else 0


def migrate_legacy_json(legacy: list[dict], product: VietlottProduct) -> list[DrawResult]:
    seen: set[int] = set()
    out: list[DrawResult] = []
    for rec in legacy:
        title = rec.get("title", "")
        m_id = _DRAW_ID_RE.search(title)
        m_date = _DATE_RE.search(title)
        if not m_id or not m_date:
            continue
        draw_id = int(m_id.group(1))
        if draw_id in seen:
            continue
        seen.add(draw_id)
        day, month, year = map(int, m_date.groups())
        balls = sorted(int(b) for b in rec.get("balls", []))
        special_raw = rec.get("special_ball")
        special: int | None = int(special_raw) if (product.has_special_ball and special_raw) else None
        out.append(
            DrawResult(
                draw_id=draw_id,
                date=datetime(year, month, day).date(),
                product_code=product.code,
                balls=balls,
                special_ball=special,
                jackpot_vnd=_parse_legacy_prize(rec),
            )
        )
    out.sort(key=lambda r: r.draw_id)
    return out


class Store:
    def __init__(self, data_dir: Path = Path("data")) -> None:
        self._data_dir = data_dir

    def _path(self, product: VietlottProduct) -> Path:
        return self._data_dir / f"vietlott-{product.slug}.json"

    def load(self, product: VietlottProduct) -> list[DrawResult]:
        path = self._path(product)
        if not path.exists():
            return []
        raw = json.loads(path.read_text(encoding="utf-8"))
        if raw and _is_legacy_record(raw[0]):
            return migrate_legacy_json(raw, product)
        lst = DrawResultList.model_validate(raw)
        return lst.root

    def save(self, product: VietlottProduct, results: list[DrawResult]) -> None:
        path = self._path(product)
        path.parent.mkdir(parents=True, exist_ok=True)
        sorted_results = sorted(results, key=lambda r: r.draw_id)
        payload = DrawResultList(root=sorted_results).model_dump_json(indent=2)
        path.write_text(payload, encoding="utf-8")

    def merge(
        self,
        existing: list[DrawResult],
        new: list[DrawResult],
    ) -> list[DrawResult]:
        by_id: dict[int, DrawResult] = {r.draw_id: r for r in new}
        for r in existing:  # existing wins on conflict
            by_id[r.draw_id] = r
        return sorted(by_id.values(), key=lambda r: r.draw_id)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/vietlott/test_store.py -v`
Expected: 8 passed.

- [ ] **Step 6: Commit**

```bash
git add src/vietlott/store.py tests/fixtures/vietlott/655-legacy.json tests/vietlott/test_store.py
git commit -m "$(cat <<'EOF'
feat(vietlott): add Store with dedup and legacy n8n migration

Store owns the canonical data/vietlott-{slug}.json files. load() detects
the legacy n8n schema by the presence of "product-message" and converts
on the fly; the next save() persists the new schema. merge() dedupes
incoming results by draw_id, preferring existing records on conflict
(parser drift defence).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 7: `Transformer` (DataFrames + CSV/JSON/Parquet dump)

**Files:**
- Create: `src/vietlott/transformer.py`
- Create: `tests/vietlott/test_transformer.py`

**Interfaces:**
- Consumes: `DrawResult` (Task 2), `VietlottProduct` (Task 1).
- Produces:
  - `vietlott.transformer.Transformer` with methods:
    - `to_raw_dataframe(results: list[DrawResult], product: VietlottProduct) -> pd.DataFrame`
      - Columns: `draw_id`, `date`, `ball_1`..`ball_n`, `special_ball` (only if product has one), `jackpot_vnd`.
    - `to_sparse_dataframe(results, product) -> pd.DataFrame`
      - Columns: `draw_id`, `date`, `n_01`..`n_{ball_max:02d}`, plus `sp_01`..`sp_{special_ball_max:02d}` if the product has a special ball.
    - `dump(results, product, out_dir: Path = Path("data")) -> None`
      - Writes `vietlott-{slug}.{csv,json,parquet}` and `vietlott-{slug}-sparse.{csv,json,parquet}`.

- [ ] **Step 1: Write the failing test**

Create `tests/vietlott/test_transformer.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/vietlott/test_transformer.py -v`
Expected: ImportError.

- [ ] **Step 3: Implement the Transformer**

Create `src/vietlott/transformer.py`:

```python
from pathlib import Path

import pandas as pd

from vietlott.models import DrawResult
from vietlott.products import VietlottProduct


class Transformer:
    def to_raw_dataframe(
        self,
        results: list[DrawResult],
        product: VietlottProduct,
    ) -> pd.DataFrame:
        rows = []
        for r in results:
            row: dict = {"draw_id": r.draw_id, "date": r.date}
            for i, b in enumerate(r.balls, start=1):
                row[f"ball_{i}"] = b
            if product.has_special_ball:
                row["special_ball"] = r.special_ball
            row["jackpot_vnd"] = r.jackpot_vnd
            rows.append(row)
        df = pd.DataFrame(rows)
        df["date"] = pd.to_datetime(df["date"])
        return df

    def to_sparse_dataframe(
        self,
        results: list[DrawResult],
        product: VietlottProduct,
    ) -> pd.DataFrame:
        ball_cols = [f"n_{i:02d}" for i in range(product.ball_min, product.ball_max + 1)]
        sp_cols: list[str] = []
        if product.has_special_ball:
            assert product.special_ball_max is not None
            sp_cols = [f"sp_{i:02d}" for i in range(product.ball_min, product.special_ball_max + 1)]
        cols = ["draw_id", "date", *ball_cols, *sp_cols]
        rows = []
        for r in results:
            row = {c: 0 for c in cols}
            row["draw_id"] = r.draw_id
            row["date"] = r.date
            for b in r.balls:
                row[f"n_{b:02d}"] = 1
            if product.has_special_ball and r.special_ball is not None:
                row[f"sp_{r.special_ball:02d}"] = 1
            rows.append(row)
        df = pd.DataFrame(rows, columns=cols)
        df["date"] = pd.to_datetime(df["date"])
        return df

    def dump(
        self,
        results: list[DrawResult],
        product: VietlottProduct,
        out_dir: Path = Path("data"),
    ) -> None:
        out_dir.mkdir(parents=True, exist_ok=True)
        slug = product.slug
        raw = self.to_raw_dataframe(results, product)
        sparse = self.to_sparse_dataframe(results, product)
        for df, name in [(raw, f"vietlott-{slug}"), (sparse, f"vietlott-{slug}-sparse")]:
            df.to_csv(out_dir / f"{name}.csv", index=False)
            df.to_json(
                out_dir / f"{name}.json",
                orient="records", date_format="iso", indent=2, index=False,
            )
            df.to_parquet(out_dir / f"{name}.parquet", index=False)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/vietlott/test_transformer.py -v`
Expected: 7 passed.

- [ ] **Step 5: Commit**

```bash
git add src/vietlott/transformer.py tests/vietlott/test_transformer.py
git commit -m "$(cat <<'EOF'
feat(vietlott): add Transformer producing raw + sparse views

to_raw_dataframe yields one row per draw with ball_1..ball_n columns
(special_ball only when the product has one). to_sparse_dataframe
expands into one column per possible ball value (n_01..n_{ball_max})
and optional sp_01..sp_{special_max}. dump() writes CSV/JSON/Parquet
for both views following the XSMB delivery pattern.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 8: `Pipeline` (orchestrator)

**Files:**
- Create: `src/vietlott/pipeline.py`
- Create: `tests/vietlott/test_pipeline.py`

**Interfaces:**
- Consumes: `Fetcher` (Task 4), `Parser` (Task 5), `Store` (Task 6), `Transformer` (Task 7), `PipelineReport` (Task 2).
- Produces:
  - `vietlott.pipeline.Pipeline(fetcher, parser, store, transformer)` with method `run(product) -> PipelineReport`.
  - `run` flow: load existing → fetch HTML → parse → merge → save → dump → return `PipelineReport(product_slug, new_count, total_count)`.
  - `new_count` = number of draw_ids in the merged set that weren't in `existing`.

- [ ] **Step 1: Write the failing test**

Create `tests/vietlott/test_pipeline.py`:

```python
from datetime import date
from pathlib import Path

from vietlott.fetcher import Fetcher
from vietlott.models import DrawResult
from vietlott.parser import Parser
from vietlott.pipeline import Pipeline
from vietlott.products import POWER_655
from vietlott.store import Store
from vietlott.transformer import Transformer


class _StubFetcher:
    def __init__(self, html: str) -> None:
        self.html = html

    def fetch_results_page(self, product) -> str:
        return self.html


class _StubParser:
    def __init__(self, draws: list[DrawResult]) -> None:
        self.draws = draws

    def parse(self, html: str, product) -> list[DrawResult]:
        return list(self.draws)


def _r(draw_id: int) -> DrawResult:
    return DrawResult(
        draw_id=draw_id, date=date(2025, 11, 22),
        product_code="6/55", balls=[1, 2, 3, 4, 5, 6],
        special_ball=7, jackpot_vnd=10**9,
    )


def test_pipeline_reports_new_and_total_counts(tmp_data_dir):
    store = Store(data_dir=tmp_data_dir)
    store.save(POWER_655, [_r(1), _r(2)])

    pipeline = Pipeline(
        fetcher=_StubFetcher("<html/>"),
        parser=_StubParser([_r(2), _r(3), _r(4)]),  # 1 dup + 2 new
        store=store,
        transformer=Transformer(),
    )

    report = pipeline.run(POWER_655)

    assert report.product_slug == "655"
    assert report.new_count == 2  # draws 3 and 4
    assert report.total_count == 4  # 1, 2, 3, 4


def test_pipeline_writes_transformer_outputs(tmp_data_dir):
    pipeline = Pipeline(
        fetcher=_StubFetcher("<html/>"),
        parser=_StubParser([_r(1)]),
        store=Store(data_dir=tmp_data_dir),
        transformer=Transformer(),
    )

    pipeline.run(POWER_655)

    assert (tmp_data_dir / "vietlott-655.json").exists()
    assert (tmp_data_dir / "vietlott-655.csv").exists()
    assert (tmp_data_dir / "vietlott-655.parquet").exists()
    assert (tmp_data_dir / "vietlott-655-sparse.csv").exists()


def test_pipeline_handles_zero_new_results(tmp_data_dir):
    store = Store(data_dir=tmp_data_dir)
    store.save(POWER_655, [_r(1)])

    pipeline = Pipeline(
        fetcher=_StubFetcher("<html/>"),
        parser=_StubParser([_r(1)]),  # no new
        store=store,
        transformer=Transformer(),
    )

    report = pipeline.run(POWER_655)

    assert report.new_count == 0
    assert report.total_count == 1


def test_pipeline_accepts_real_components_for_type_compatibility():
    # Smoke check that Pipeline.__init__ accepts the real classes.
    Pipeline(
        fetcher=Fetcher(http=object()),
        parser=Parser(),
        store=Store(data_dir=Path("/unused")),
        transformer=Transformer(),
    )
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/vietlott/test_pipeline.py -v`
Expected: ImportError on `Pipeline`.

- [ ] **Step 3: Implement the Pipeline**

Create `src/vietlott/pipeline.py`:

```python
from typing import Protocol

from vietlott.models import DrawResult, PipelineReport
from vietlott.products import VietlottProduct


class _FetcherLike(Protocol):
    def fetch_results_page(self, product: VietlottProduct) -> str: ...


class _ParserLike(Protocol):
    def parse(self, html: str, product: VietlottProduct) -> list[DrawResult]: ...


class Pipeline:
    def __init__(
        self,
        fetcher: _FetcherLike,
        parser: _ParserLike,
        store,
        transformer,
    ) -> None:
        self._fetcher = fetcher
        self._parser = parser
        self._store = store
        self._transformer = transformer

    def run(self, product: VietlottProduct) -> PipelineReport:
        existing = self._store.load(product)
        existing_ids = {r.draw_id for r in existing}

        html = self._fetcher.fetch_results_page(product)
        new_results = self._parser.parse(html, product)

        merged = self._store.merge(existing, new_results)
        new_count = sum(1 for r in merged if r.draw_id not in existing_ids)

        self._store.save(product, merged)
        self._transformer.dump(merged, product)

        return PipelineReport(
            product_slug=product.slug,
            new_count=new_count,
            total_count=len(merged),
        )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/vietlott/test_pipeline.py -v`
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add src/vietlott/pipeline.py tests/vietlott/test_pipeline.py
git commit -m "$(cat <<'EOF'
feat(vietlott): add Pipeline orchestrating fetch/parse/store/transform

Pipeline.run loads existing data, fetches and parses the latest page,
merges with dedup, saves the canonical JSON, and dumps CSV/JSON/Parquet
artifacts. Returns a PipelineReport with new_count vs total_count so the
entrypoint can log per-product results.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 9: Entry point script + GitHub Actions workflow

**Files:**
- Create: `src/vietlott_fetch.py`
- Create: `tests/vietlott/test_entrypoint.py`
- Create: `.github/workflows/vietlott.yml`

**Interfaces:**
- Consumes: all earlier components.
- Produces:
  - Function `vietlott_fetch.products_for_today(now: datetime, products: tuple[VietlottProduct, ...] = ALL_PRODUCTS) -> list[VietlottProduct]` — filters by `weekday() in product.draw_days` using Asia/Ho_Chi_Minh time.
  - Function `vietlott_fetch.run_for_products(products: list[VietlottProduct]) -> list[PipelineReport]` — runs each in its own try/except so one failure doesn't block the others. On failure, logs and appends a `PipelineReport` with `new_count=0`, `total_count=0`, and the exception summary in `warnings`.
  - `__main__` block: instantiate real components, call `products_for_today(datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")))`, then `run_for_products`. Exit 0 unless every product failed; exit 1 if all failed.
  - GitHub Actions workflow `.github/workflows/vietlott.yml` with a cron that covers all three products' draw days.

- [ ] **Step 1: Write the failing test**

Create `tests/vietlott/test_entrypoint.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/vietlott/test_entrypoint.py -v`
Expected: ImportError on `vietlott_fetch`.

- [ ] **Step 3: Implement the entry point**

Create `src/vietlott_fetch.py`:

```python
"""GitHub Actions entry point for the Vietlott data pipeline."""
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

from loguru import logger

from vietlott.fetcher import Fetcher
from vietlott.models import PipelineReport
from vietlott.parser import Parser
from vietlott.pipeline import Pipeline
from vietlott.products import ALL_PRODUCTS, VietlottProduct
from vietlott.store import Store
from vietlott.transformer import Transformer

_VN = ZoneInfo("Asia/Ho_Chi_Minh")


def products_for_today(
    now: datetime,
    products: tuple[VietlottProduct, ...] = ALL_PRODUCTS,
) -> list[VietlottProduct]:
    today_weekday = now.astimezone(_VN).weekday()
    return [p for p in products if today_weekday in p.draw_days]


def run_for_products(
    products: list[VietlottProduct],
    pipeline: Pipeline | None = None,
) -> list[PipelineReport]:
    if pipeline is None:
        pipeline = Pipeline(
            fetcher=Fetcher(),
            parser=Parser(),
            store=Store(),
            transformer=Transformer(),
        )
    reports: list[PipelineReport] = []
    for product in products:
        try:
            report = pipeline.run(product)
            logger.info(
                "Vietlott {}: +{} new (total {})",
                product.slug, report.new_count, report.total_count,
            )
            reports.append(report)
        except Exception as exc:  # noqa: BLE001 — boundary, want everything
            logger.exception("Pipeline failed for {}", product.slug)
            reports.append(
                PipelineReport(
                    product_slug=product.slug,
                    new_count=0,
                    total_count=0,
                    warnings=[f"{type(exc).__name__}: {exc}"],
                )
            )
    return reports


def main() -> int:
    now = datetime.now(_VN)
    picks = products_for_today(now)
    if not picks:
        logger.info("No Vietlott products scheduled for {}", now.date())
        return 0
    reports = run_for_products(picks)
    all_failed = all(r.warnings for r in reports)
    return 1 if all_failed else 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/vietlott/test_entrypoint.py -v`
Expected: 5 passed.

- [ ] **Step 5: Write the GitHub Actions workflow**

Create `.github/workflows/vietlott.yml`:

```yaml
name: Vietlott Fetch

on:
  schedule:
    # Vietnam is UTC+7. Draws complete by ~18:30 VN = 11:30 UTC.
    # We schedule for 12:00 UTC = 19:00 VN to be safe.
    # Power 6/55: Tue / Thu / Sat   (weekdays 2,4,6 in cron — Sunday=0)
    # Mega 6/45 : Wed / Fri / Sun   (weekdays 3,5,0)
    # Lotto 5/35: per Task 3's verified schedule (assume daily here)
    - cron: "0 12 * * *"
  workflow_dispatch:

jobs:
  fetch:
    runs-on: ubuntu-24.04
    environment: secrets
    steps:
      - name: checkout repo content
        uses: actions/checkout@v4

      - name: setup python
        uses: actions/setup-python@v5
        with:
          python-version: "3.13"
          cache: pip
          cache-dependency-path: requirements.txt

      - name: install python packages
        run: pip install -r requirements.txt

      - name: run vietlott pipeline
        run: python src/vietlott_fetch.py

      - name: get current date
        run: echo "date=$(date +'%Y-%m-%d')" >> $GITHUB_ENV

      - name: push changes
        uses: actions-x/commit@v6
        with:
          token: ${{ secrets.MY_GITHUB_TOKEN }}
          message: "Vietlott ${{ env.date }}"
          email: action@github.com
          name: GitHub Action
          files: data/vietlott-*.json data/vietlott-*.csv data/vietlott-*.parquet
```

If Task 3 verified that Lotto 5/35 does NOT draw daily, you can split this into two crons (one for Tue/Thu/Sat + 5/35-days, one for Wed/Fri/Sun + 5/35-days) — but running the script every day at 12:00 UTC and letting `products_for_today` filter is simpler and cheaper. Keep the single cron.

- [ ] **Step 6: Run the full test suite**

Run: `pytest -v`
Expected: every test from Tasks 1-9 passes.

- [ ] **Step 7: Commit**

```bash
git add src/vietlott_fetch.py tests/vietlott/test_entrypoint.py .github/workflows/vietlott.yml
git commit -m "$(cat <<'EOF'
feat(vietlott): add daily entry point and GitHub Actions workflow

vietlott_fetch.py picks the products whose draw_days include today
(Asia/Ho_Chi_Minh), runs the Pipeline for each in isolation, and exits
0 unless every product failed. The workflow runs daily at 12:00 UTC
(19:00 VN), installs requirements, runs the script, and commits any
changed data/vietlott-* files.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 10: End-to-end manual verification + n8n cutover

This is a verification gate, not new code. **Read each step and confirm before proceeding.** The spec calls this out explicitly: do NOT delete the n8n flow until step 4 of this task passes.

**Files:**
- Modify: `docs/vietlott-source-notes.md` — append a "Verification log" section
- Optionally modify: external n8n workflow (outside this repo) to disable Vietlott ingestion

**Interfaces:**
- Consumes: a fully-built and pushed branch with everything from Tasks 1-9.
- Produces: confirmation that the new pipeline produces equivalent results to the n8n flow, and the n8n flow is retired.

- [ ] **Step 1: Run the new pipeline locally end-to-end**

```bash
python src/vietlott_fetch.py
```

Confirm:
- `data/vietlott-{655,645,535}.json` are in the new schema (int `draw_id`, ISO `date`, single `jackpot_vnd`, no `product-message`).
- `data/vietlott-{655,645,535}.csv` / `.parquet` and `-sparse.*` exist.
- The set of `draw_id`s in the new JSON ≥ the set of unique `draw_id`s parsed from the previous n8n JSON (we should never lose draws).

- [ ] **Step 2: Compare against the legacy n8n output**

Quick diff script (run in the shell):

```python
import json, re
from pathlib import Path

for slug in ["655", "645", "535"]:
    # The legacy file was already overwritten by the migration on first run,
    # so use a backup. Take a backup BEFORE first run if you haven't:
    legacy = json.loads(Path(f"data/vietlott-{slug}.json.backup").read_text())
    legacy_ids = set()
    for rec in legacy:
        m = re.search(r"#0*(\d+)", rec.get("title", ""))
        if m:
            legacy_ids.add(int(m.group(1)))
    new = json.loads(Path(f"data/vietlott-{slug}.json").read_text())
    new_ids = {r["draw_id"] for r in new}
    missing = legacy_ids - new_ids
    extra = new_ids - legacy_ids
    print(f"{slug}: legacy={len(legacy_ids)} new={len(new_ids)} missing={sorted(missing)} extra={sorted(extra)}")
```

`missing` should be empty (we didn't drop any draws). `extra` is allowed (the new fetcher may have pulled draws the n8n flow hadn't yet captured).

If `missing` is non-empty, investigate **before** proceeding. The most likely cause is a legacy title pattern the Parser doesn't recognize.

- [ ] **Step 3: Open a PR, get the workflow file reviewed, merge to master**

The workflow won't run on the branch — it has to be on `master`. Once merged, trigger it once manually via `workflow_dispatch` to confirm green.

- [ ] **Step 4: Disable the n8n Vietlott ingestion**

Once the GitHub Actions workflow has run cleanly at least once on its cron schedule and committed updates, disable the n8n flow that was writing `data/vietlott-*.json`. The n8n XSMB workflow (separate) is unaffected.

- [ ] **Step 5: Document the verification result**

Append to `docs/vietlott-source-notes.md`:

```markdown
## Verification log

- Manual run on YYYY-MM-DD: 655 +N draws / 645 +N / 535 +N
- Diff against legacy n8n output: no missing draws
- First scheduled CI run on YYYY-MM-DD HH:MM UTC: green
- n8n vietlott flow disabled on YYYY-MM-DD
```

- [ ] **Step 6: Commit the verification log and close the loop**

```bash
git add docs/vietlott-source-notes.md
git commit -m "$(cat <<'EOF'
docs(vietlott): record verification log + n8n cutover

Captures the manual diff against the legacy n8n output (no missing
draws), the first green CI run, and the date the n8n flow was retired.
Marks sub-project A as complete.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

Sub-project A is now done. Sub-project B (analysis + visualization) can begin in a fresh brainstorming session — it consumes the cleaned datasets and adds no requirements to this layer.
