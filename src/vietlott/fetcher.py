import os
from typing import Any

from cloudscraper import CloudScraper

from vietlott.errors import FetchError
from vietlott.products import VietlottProduct

# GitHub Actions runners use datacenter IPs that Vietlott's Cloudflare WAF
# blocks with a 403 regardless of headers. Setting VIETLOTT_PROXY to a VN
# (or residential) proxy URL routes requests through an allowed IP.
PROXY_ENV_VAR = "VIETLOTT_PROXY"

# Vietlott sits behind Cloudflare and rejects requests that don't look like a
# real browser. Sending a full set of browser headers (notably a Vietnamese
# Accept-Language and a same-origin Referer) reduces WAF 403s.
BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,"
        "image/avif,image/webp,*/*;q=0.8"
    ),
    "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
    "Referer": "https://vietlott.vn/",
    "Upgrade-Insecure-Requests": "1",
}


class Fetcher:
    def __init__(self, http: Any | None = None) -> None:
        if http is not None:
            self._http = http
        else:
            self._http = CloudScraper()
            self._http.headers.update(BROWSER_HEADERS)
            proxy = os.environ.get(PROXY_ENV_VAR)
            if proxy:
                self._http.proxies.update({"http": proxy, "https": proxy})

    def fetch_results_page(self, product: VietlottProduct) -> str:
        return self._get(product.result_url)

    def fetch_archive_page(self, product: VietlottProduct, page: int) -> str:
        return self._get(f"{product.result_url}?page={page}")

    def _get(self, url: str) -> str:
        resp = self._http.get(url)
        if resp.status_code != 200:
            raise FetchError(f"GET {url} returned status {resp.status_code}")
        return resp.text
