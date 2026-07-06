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


def test_fetcher_applies_proxy_from_env(monkeypatch):
    monkeypatch.setenv("VIETLOTT_PROXY", "http://user:pass@vn-proxy:8080")

    fetcher = Fetcher()

    assert fetcher._http.proxies["http"] == "http://user:pass@vn-proxy:8080"
    assert fetcher._http.proxies["https"] == "http://user:pass@vn-proxy:8080"


def test_fetcher_no_proxy_when_env_unset(monkeypatch):
    monkeypatch.delenv("VIETLOTT_PROXY", raising=False)

    fetcher = Fetcher()

    assert "http" not in fetcher._http.proxies


def test_fetcher_forces_ipv6_when_env_set(monkeypatch):
    import socket

    import urllib3.util.connection as urllib3_conn

    original = urllib3_conn.allowed_gai_family
    monkeypatch.setattr(urllib3_conn, "allowed_gai_family", original)
    monkeypatch.setenv("VIETLOTT_FORCE_IPV6", "1")

    Fetcher()

    assert urllib3_conn.allowed_gai_family() == socket.AF_INET6
