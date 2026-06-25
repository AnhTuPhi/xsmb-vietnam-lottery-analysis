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
