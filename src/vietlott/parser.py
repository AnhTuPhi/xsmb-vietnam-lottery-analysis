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
        # Section 2a of docs/vietlott-source-notes.md:
        # Use generic div.chitietketqua — do NOT filter on modifier class.
        return soup.select("div.chitietketqua")

    def _parse_row(self, row: Tag, product: VietlottProduct) -> DrawResult:
        # Section 2b: draw number and date from div.chitietketqua_title h5
        h5 = row.select_one("div.chitietketqua_title h5")
        if h5 is None:
            raise ValueError("No div.chitietketqua_title h5 element found in row")
        title_text = h5.get_text()

        # Section 2c: regular balls (bong_tron without active class)
        ball_div = row.select_one("div.day_so_ket_qua_v2")
        if ball_div is None:
            raise ValueError("No div.day_so_ket_qua_v2 element found in row")
        all_ball_spans = ball_div.find_all("span", class_="bong_tron")
        raw_balls = [
            b.get_text(strip=True)
            for b in all_ball_spans
            if "active" not in b.get("class", [])
        ]

        # Section 2d: special ball (active class), gated on product.has_special_ball
        special_ball: int | None = None
        if product.has_special_ball:
            special_span = ball_div.find("span", class_="active")
            if special_span is not None:
                special_ball = int(special_span.get_text(strip=True))

        # Section 2e: jackpot value — differs by product
        if product.slug == "535":
            # Section 2e (Lotto 5/35): jackpot is in thead of prize table
            thead_rows = row.select("table.table thead tr")
            if not thead_rows:
                raise ValueError("No table.table thead tr found for 535 jackpot")
            jackpot_raw = thead_rows[0].find_all("th")[-1].get_text(strip=True)
            jackpot_raw = jackpot_raw.replace(" VND", "")
        else:
            # Section 2e (Power 6/55 and Mega 6/45): jackpot in div.gt_jackpot div.so_tien h3
            jackpot_h3 = row.select_one("div.gt_jackpot div.so_tien h3")
            if jackpot_h3 is None:
                raise ValueError("No div.gt_jackpot div.so_tien h3 element found in row")
            jackpot_raw = jackpot_h3.get_text(strip=True)

        return DrawResult(
            draw_id=self._parse_draw_id(title_text),
            date=self._parse_date(title_text),
            product_code=product.code,
            balls=self._parse_balls(raw_balls),
            special_ball=special_ball,
            jackpot_vnd=self._parse_jackpot_vnd(jackpot_raw),
        )

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
