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
