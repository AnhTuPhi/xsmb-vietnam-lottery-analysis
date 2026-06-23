from pathlib import Path

import pandas as pd

from vietlott.models import DrawResult
from vietlott.products import VietlottProduct


class Transformer:
    def to_raw_dataframe(
        self,
        results: list[DrawResult],
        product: VietlottProduct,
    ) -> pd.DataFrame:
        rows = []
        for r in results:
            row: dict = {"draw_id": r.draw_id, "date": r.date}
            for i, b in enumerate(r.balls, start=1):
                row[f"ball_{i}"] = b
            if product.has_special_ball:
                row["special_ball"] = r.special_ball
            row["jackpot_vnd"] = r.jackpot_vnd
            rows.append(row)
        df = pd.DataFrame(rows)
        df["date"] = pd.to_datetime(df["date"])
        return df

    def to_sparse_dataframe(
        self,
        results: list[DrawResult],
        product: VietlottProduct,
    ) -> pd.DataFrame:
        ball_cols = [f"n_{i:02d}" for i in range(product.ball_min, product.ball_max + 1)]
        sp_cols: list[str] = []
        if product.has_special_ball:
            assert product.special_ball_max is not None
            sp_cols = [f"sp_{i:02d}" for i in range(product.ball_min, product.special_ball_max + 1)]
        cols = ["draw_id", "date", *ball_cols, *sp_cols]
        rows = []
        for r in results:
            row = {c: 0 for c in cols}
            row["draw_id"] = r.draw_id
            row["date"] = r.date
            for b in r.balls:
                row[f"n_{b:02d}"] = 1
            if product.has_special_ball and r.special_ball is not None:
                row[f"sp_{r.special_ball:02d}"] = 1
            rows.append(row)
        df = pd.DataFrame(rows, columns=cols)
        df["date"] = pd.to_datetime(df["date"])
        return df

    def dump(
        self,
        results: list[DrawResult],
        product: VietlottProduct,
        out_dir: Path = Path("data"),
    ) -> None:
        out_dir.mkdir(parents=True, exist_ok=True)
        slug = product.slug
        raw = self.to_raw_dataframe(results, product)
        sparse = self.to_sparse_dataframe(results, product)
        for df, name in [(raw, f"vietlott-{slug}"), (sparse, f"vietlott-{slug}-sparse")]:
            df.to_csv(out_dir / f"{name}.csv", index=False)
            df.to_json(
                out_dir / f"{name}.json",
                orient="records", date_format="iso", indent=2, index=False,
            )
            df.to_parquet(out_dir / f"{name}.parquet", index=False)
