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
