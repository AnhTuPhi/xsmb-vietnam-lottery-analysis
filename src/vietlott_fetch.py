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
