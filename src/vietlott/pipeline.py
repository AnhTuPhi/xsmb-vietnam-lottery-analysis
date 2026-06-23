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
        self._transformer.dump(merged, product, out_dir=self._store.data_dir)

        return PipelineReport(
            product_slug=product.slug,
            new_count=new_count,
            total_count=len(merged),
        )
