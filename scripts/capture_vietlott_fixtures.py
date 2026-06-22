"""One-shot helper: fetch live vietlott.vn pages and save HTML fixtures.

Run manually: `python scripts/capture_vietlott_fixtures.py`

Note: URLs use the .html suffix format discovered from the vietlott.vn
homepage navigation — the shorter slug-only paths (e.g. /power-655)
return a Cloudflare-protected "invalid address" error page.
"""
from pathlib import Path

import cloudscraper

URLS = {
    "655": "https://vietlott.vn/vi/trung-thuong/ket-qua-trung-thuong/655.html",
    "645": "https://vietlott.vn/vi/trung-thuong/ket-qua-trung-thuong/645.html",
    "535": "https://vietlott.vn/vi/trung-thuong/ket-qua-trung-thuong/535.html",
}

OUT_DIR = Path("tests/fixtures/vietlott")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    http = cloudscraper.create_scraper()
    for slug, url in URLS.items():
        resp = http.get(url, timeout=30)
        resp.raise_for_status()
        if "Kỳ quay thưởng" not in resp.text:
            raise RuntimeError(
                f"Response for {slug} does not contain draw data — "
                "may be a Cloudflare challenge page. "
                f"Status: {resp.status_code}, Length: {len(resp.text)}"
            )
        target = OUT_DIR / f"{slug}-results.html"
        target.write_text(resp.text, encoding="utf-8")
        print(f"Saved {target} ({len(resp.text)} bytes) from {url}")


if __name__ == "__main__":
    main()
