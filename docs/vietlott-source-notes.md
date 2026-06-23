# Vietlott Source Notes

Captured during Task 3 (source investigation) on 2026-06-23.
Fixtures are **live HTML** fetched via `cloudscraper` from vietlott.vn.

---

## 1. Confirmed URLs per product

| Product | URL | How confirmed |
|---------|-----|---------------|
| Power 6/55 | `https://vietlott.vn/vi/trung-thuong/ket-qua-trung-thuong/655.html` | WebFetch of homepage revealed `.html` suffix navigation links; cloudscraper confirmed draw data present (41 KB, contains "Kỳ quay thưởng"). |
| Mega 6/45 | `https://vietlott.vn/vi/trung-thuong/ket-qua-trung-thuong/645.html` | Same method. |
| Lotto 5/35 | `https://vietlott.vn/vi/trung-thuong/ket-qua-trung-thuong/535.html` | Same method. Official slug is `535`, not `max-535`. |

**Important:** The shorter paths without `.html` (e.g. `/power-655`) return a
Cloudflare-blocked "Địa chỉ truy cập sai" (invalid address) error page. Always
use the `.html` suffix form.

---

## 2. DOM selectors for the Parser (Task 5)

All three products share the same HTML skeleton. Differences noted per-product below.

### 2a. Top-level container

```
div.chitietketqua
```

The class list always includes `chitietketqua` plus a product modifier
(`mega645` for both Power 6/55 and Mega 6/45; `lotto535` for Lotto 5/35).
There is exactly **one** such div per page — the page shows only the most
recent draw result. Navigation to other draws happens via a JavaScript AJAX
call (`ClientDrawResult(DrawId)`) that re-renders the same container.

```html
<div class="chitietketqua mega645">   <!-- 655 and 645 -->
<div class="chitietketqua lotto535">  <!-- 535 -->
```

**Important:** The `mega645` and `lotto535` modifier classes are vietlott.vn's CSS naming conventions, not product-discriminators. The Parser should always select on the generic `div.chitietketqua` and rely on the `product` argument passed to `parse()` to determine which product the draw rows belong to. Do not filter or discriminate based on the modifier class.

### 2b. Draw title — draw number and date

```
div.chitietketqua_title h5
```

The `h5` element contains the text "Kỳ quay thưởng", then a `<b>` with the
draw number (`#NNNNN`), the word "ngày", then a second `<b>` with the date
(`DD/MM/YYYY`).

Sample (Power 6/55, draw #01361, 20/06/2026):
```html
<div class="chitietketqua_title">
  <h5>
    Kỳ quay thưởng
    <b>#01361</b>
    ngày
    <b>20/06/2026</b>
  </h5>
</div>
```

**Parsing recipe:**
```python
h5 = soup.select_one("div.chitietketqua_title h5")
b_tags = h5.find_all("b")
draw_number = b_tags[0].get_text(strip=True).lstrip("#")   # "01361"
draw_date   = b_tags[1].get_text(strip=True)               # "20/06/2026"
```

### 2c. Ball values (regular balls)

```
div.day_so_ket_qua_v2 span.bong_tron:not(.active)
```

Regular balls are `<span class="bong_tron ...">` elements **without** the
`active` class. The `active` class marks the special/power ball.

Sample (Power 6/55):
```html
<div class="day_so_ket_qua_v2">
  <span class="bong_tron small">16</span>
  <span class="bong_tron small">23</span>
  <span class="bong_tron small">26</span>
  <span class="bong_tron small">30</span>
  <span class="bong_tron small">52</span>
  <span class="bong_tron small">53</span>
  <i>|</i>
  <span class="bong_tron small no-margin-right active">46</span>
</div>
```

Note for Mega 6/45: ball spans use `class="bong_tron"` (no `small` suffix) and
there is no special ball, so no `active` span. The last ball has
`class="bong_tron no-margin-right"` — no `active` class.

**Parsing recipe:**
```python
ball_div = soup.select_one("div.day_so_ket_qua_v2")
all_balls = ball_div.find_all("span", class_="bong_tron")
regular_balls = [int(b.get_text(strip=True)) for b in all_balls
                 if "active" not in b.get("class", [])]
```

### 2d. Special ball (Power 6/55 and Lotto 5/35 only)

```
div.day_so_ket_qua_v2 span.bong_tron.active
```

The special ball is the single `<span class="bong_tron ... active">` element.

**Parsing recipe:**
```python
special_span = ball_div.find("span", class_="active")
special_ball = int(special_span.get_text(strip=True)) if special_span else None
```

Mega 6/45 has `has_special_ball=False`, so `special_ball` will always be
`None` for that product.

### 2e. Jackpot value

The jackpot location differs by product:

#### Power 6/55 and Mega 6/45

```
div.gt_jackpot div.so_tien h3
```

For Power 6/55, there are two `.so_tien` divs (Jackpot 1 and Jackpot 2).
For Mega 6/45, there is one `.so_tien` div (Jackpot).
Use the **first** `.so_tien h3` as the primary jackpot value.

Sample (Power 6/55):
```html
<div class="gt_jackpot">
  <div class="row">
    <div class="col-md-5"><h5>Giá trị Jackpot 1</h5></div>
    <div class="col-md-7">
      <div class="so_tien">
        <h3>56.004.290.850</h3>
        <p>VNĐ</p>
      </div>
    </div>
    <div class="col-md-5"><h5>Giá trị Jackpot 2</h5></div>
    <div class="col-md-7">
      <div class="so_tien">
        <h3>5.290.303.100</h3>
        <p>VNĐ</p>
      </div>
    </div>
  </div>
</div>
```

**Parsing recipe (655 / 645):**
```python
jackpot_h3 = soup.select_one("div.gt_jackpot div.so_tien h3")
jackpot_raw = jackpot_h3.get_text(strip=True)  # "56.004.290.850"
```

#### Lotto 5/35

The jackpot appears in the `<thead>` of the prize table, **not** in a
`div.gt_jackpot`. The first `<tr>` in `<thead>` has four `<th>` cells; the
fourth cell (index 3) holds the jackpot value followed by " VND".

```html
<thead>
  <tr style="background-color:#ed1b2f;color:white;font-weight:bold">
    <th colspan="3">Giải Độc Đắc</th>
    <th class="text-right">7.030.567.500 VND</th>
  </tr>
  ...
</thead>
```

**Parsing recipe (535):**
```python
thead_rows = soup.select("table.table thead tr")
jackpot_raw = thead_rows[0].find_all("th")[-1].get_text(strip=True)
# "7.030.567.500 VND" — strip " VND" suffix
jackpot_raw = jackpot_raw.replace(" VND", "")
```

### 2f. Jackpot formatting

All jackpot values use **dot-separated thousands** with no decimal part,
e.g. `56.004.290.850`. To convert to an integer:

```python
jackpot_int = int(jackpot_raw.replace(".", ""))
```

### 2g. Date formatting

Draw dates appear as `DD/MM/YYYY` (e.g. `20/06/2026`).

```python
from datetime import date
draw_date = date(int(dd[6:]), int(dd[3:5]), int(dd[:2]))
# or: datetime.strptime(dd, "%d/%m/%Y").date()
```

---

## 3. Lotto 5/35 draw schedule

**Confirmed: every day (Mon–Sun), twice per day.**

Evidence from two sources:

1. **Live page footer text** (`div.box_kqtt_nd_chinh`):
   > "Lotto 5/35 được phát hành hàng ngày từ thứ Hai đến Chủ Nhật với tần
   > suất quay sổ mở thưởng **2 lần / ngày**"
   > (Lotto 5/35 is issued every day from Monday to Sunday with a draw
   > frequency of **2 times per day**)

2. **Existing n8n data** (`data/vietlott-535.json`, 310 draws): weekday
   analysis across 50 draws shows all seven days represented roughly equally.
   Many dates have 2 draws on the same date (115 out of 194 unique dates).

**Conclusion:** `draw_days=(0, 1, 2, 3, 4, 5, 6)` in `LOTTO_535` is correct.
The `draw_time_vn=(18, 0)` is a reasonable placeholder for the first draw;
the second draw time is not documented on the page (the page shows only the
most recent draw).

---

## 4. Fixture provenance

| Fixture | Source | Confirmed by |
|---------|--------|--------------|
| `tests/fixtures/vietlott/655-results.html` | **Live HTML** fetched via `cloudscraper` on 2026-06-23 | Contains "Kỳ quay thưởng #01361 ngày 20/06/2026" |
| `tests/fixtures/vietlott/645-results.html` | **Live HTML** fetched via `cloudscraper` on 2026-06-23 | Contains "Kỳ quay thưởng #01526 ngày 21/06/2026" |
| `tests/fixtures/vietlott/535-results.html` | **Live HTML** fetched via `cloudscraper` on 2026-06-23 | Contains "Kỳ quay thưởng #00718 ngày 22/06/2026" |

Helper script: `scripts/capture_vietlott_fixtures.py`

---

## 5. Notes for the Parser (Task 5)

- The page shows **only one draw** (the most recent). Navigation between draws
  uses a JavaScript AJAX call: `ClientDrawResult('NNNNN')`. The Fetcher
  (Task 4) will need to issue follow-up requests to fetch older draws.
  The AJAX endpoint appears to be a server-side rendered WebPart specific
  to each product:
  - Power 6/55: `Vietlott.PlugIn.WebParts.Game655ResultDetailWebPart.ServerSideDrawResult(...)`
  - Mega 6/45: `Vietlott.PlugIn.WebParts.Game645ResultDetailWebPart.ServerSideDrawResult(...)`
  - Lotto 5/35: `Vietlott.PlugIn.WebParts.Game535ResultDetailWebPart.ServerSideDrawResult(...)`

- The HTML fixtures are sufficient for **one** `DrawResult` per product.
  Task 5 parser tests should parse these fixtures and assert exactly one
  valid `DrawResult` per fixture.

- For Mega 6/45, `special_ball` must be `None` in the parsed `DrawResult`
  (the fixture confirms no `active` span in the ball container).

- Jackpot values are in VND (Vietnamese Dong), dot-separated thousands,
  no decimal. Strip dots and cast to `int`.

- The `div.chitietketqua` top-level div is the parser's entry point.
  The Parser should `soup.select_one("div.chitietketqua")` and then apply
  the sub-selectors described above.

## Verification log

- **Manual end-to-end run on 2026-06-24** (`run_for_products(ALL_PRODUCTS)`,
  live fetch from vietlott.vn): all three products fetched cleanly, no
  Cloudflare block, no warnings.
  - 655: +1 new (total 89) — new draw `#1362` (2026-06-23)
  - 645: +1 new (total 88) — new draw `#1526`
  - 535: +1 new (total 305) — new draw `#720`
- **Diff against legacy n8n output (draw_id sets):** no missing draws for
  any product (`missing=[]`). The legacy n8n files contained duplicate
  rows (655: 90 records / 88 unique ids; 645: 89/87; 535: 305/304); the
  Store dedup collapses them, which accounts for the unique-count delta.
- **Canonical round-trip confirmed:** after a run, `Store.load` re-reads
  `data/vietlott-{slug}.json` and returns the same draws — fixed by the
  Transformer/Store filename-collision fix (commit `f4f97de`), where the
  raw view previously overwrote the canonical JSON.
- **Migration is automatic:** the first CI run (or first manual run on
  master) detects the legacy schema and rewrites each file in place; the
  branch intentionally does not commit migrated data while the n8n flow is
  still active.

### Remaining cutover steps (operator)

- [ ] Merge the PR to `master`, then trigger the workflow once via
  `workflow_dispatch` to confirm it runs green and commits new-schema data.
- [ ] Once the GitHub Actions workflow has run cleanly at least once,
  **disable the n8n Vietlott ingestion** that writes `data/vietlott-*.json`
  (the n8n XSMB workflow is separate and unaffected). Running both at once
  would race on the same files.
- [ ] Record the first green CI run date and the n8n-disabled date here.
