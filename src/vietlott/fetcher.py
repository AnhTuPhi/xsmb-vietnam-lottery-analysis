import os
import socket
from typing import Any

from cloudscraper import CloudScraper
from loguru import logger

from vietlott.errors import FetchError
from vietlott.products import VietlottProduct

TRACE_URL = "https://www.cloudflare.com/cdn-cgi/trace"
# Response headers that reveal why Cloudflare blocked a request.
_BLOCK_HEADERS = ("CF-Ray", "cf-mitigated", "Server", "CF-Cache-Status", "Content-Type")
# cdn-cgi/trace fields that reveal the egress IP and its location.
_TRACE_FIELDS = ("ip=", "loc=", "colo=", "warp=")

# GitHub Actions runners use datacenter IPs that Vietlott's Cloudflare WAF
# blocks with a 403 regardless of headers. Setting VIETLOTT_PROXY to a VN
# (or residential) proxy URL routes requests through an allowed IP.
PROXY_ENV_VAR = "VIETLOTT_PROXY"

# Cloudflare WARP on CI runners tunnels IPv6 only; IPv4 still egresses via the
# blocked datacenter IP. Setting VIETLOTT_FORCE_IPV6 makes the HTTP client
# resolve/connect over IPv6 so traffic goes through the WARP tunnel.
FORCE_IPV6_ENV_VAR = "VIETLOTT_FORCE_IPV6"


def _force_ipv6() -> None:
    import urllib3.util.connection as urllib3_conn

    urllib3_conn.allowed_gai_family = lambda: socket.AF_INET6

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
            if os.environ.get(FORCE_IPV6_ENV_VAR):
                _force_ipv6()
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
            self._log_block_details(url, resp)
            raise FetchError(f"GET {url} returned status {resp.status_code}")
        return resp.text

    def _log_block_details(self, url: str, resp: Any) -> None:
        headers = {k: resp.headers.get(k) for k in _BLOCK_HEADERS}
        logger.warning(
            "Blocked GET {} status={} headers={}", url, resp.status_code, headers
        )
        body = (resp.text or "")[:500].replace("\n", " ")
        logger.warning("Response body snippet: {}", body)
        try:
            trace = self._http.get(TRACE_URL, timeout=10)
            lines = [
                line
                for line in trace.text.splitlines()
                if line.startswith(_TRACE_FIELDS)
            ]
            logger.warning("Egress trace: {}", " ".join(lines))
        except Exception as exc:  # noqa: BLE001 — diagnostics must never mask FetchError
            logger.warning("Egress trace failed: {}", exc)
