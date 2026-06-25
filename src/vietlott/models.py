from datetime import date as _date
from typing import Self

from pydantic import BaseModel, Field, RootModel, field_validator

from vietlott.products import VietlottProduct


class DrawResult(BaseModel):
    draw_id: int = Field(ge=1)
    date: _date
    product_code: str
    balls: list[int]
    special_ball: int | None = None
    jackpot_vnd: int = Field(ge=0)

    @field_validator("balls")
    @classmethod
    def _balls_sorted_ascending(cls, v: list[int]) -> list[int]:
        if v != sorted(v):
            raise ValueError("balls must be sorted ascending")
        return v

    def validate_against_product(self, product: VietlottProduct) -> None:
        if len(self.balls) != product.ball_count:
            raise ValueError(
                f"ball_count mismatch: got {len(self.balls)}, expected {product.ball_count}"
            )
        for b in self.balls:
            if not (product.ball_min <= b <= product.ball_max):
                raise ValueError(
                    f"ball {b} out of range [{product.ball_min}, {product.ball_max}]"
                )
        if product.has_special_ball:
            if self.special_ball is None:
                raise ValueError("special_ball required for this product")
            assert product.special_ball_max is not None  # type narrowing
            if not (product.ball_min <= self.special_ball <= product.special_ball_max):
                raise ValueError(
                    f"special_ball {self.special_ball} out of range"
                )
        else:
            if self.special_ball is not None:
                raise ValueError("special_ball not allowed for this product")


class DrawResultList(RootModel[list[DrawResult]]):
    pass


class PipelineReport(BaseModel):
    product_slug: str
    new_count: int
    total_count: int
    warnings: list[str] = Field(default_factory=list)
