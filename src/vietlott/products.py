from dataclasses import dataclass


@dataclass(frozen=True)
class VietlottProduct:
    slug: str
    name: str
    code: str
    ball_count: int
    ball_min: int
    ball_max: int
    has_special_ball: bool
    special_ball_max: int | None
    draw_days: tuple[int, ...]
    draw_time_vn: tuple[int, int]


POWER_655 = VietlottProduct(
    slug="655",
    name="Power 6/55",
    code="6/55",
    ball_count=6,
    ball_min=1,
    ball_max=55,
    has_special_ball=True,
    special_ball_max=55,
    draw_days=(1, 3, 5),  # Tue, Thu, Sat
    draw_time_vn=(18, 30),
)

MEGA_645 = VietlottProduct(
    slug="645",
    name="Mega 6/45",
    code="6/45",
    ball_count=6,
    ball_min=1,
    ball_max=45,
    has_special_ball=False,
    special_ball_max=None,
    draw_days=(2, 4, 6),  # Wed, Fri, Sun
    draw_time_vn=(18, 30),
)

LOTTO_535 = VietlottProduct(
    slug="535",
    name="Lotto 5/35",
    code="5/35",
    ball_count=5,
    ball_min=1,
    ball_max=35,
    has_special_ball=True,
    special_ball_max=35,
    draw_days=(0, 1, 2, 3, 4, 5, 6),  # to be verified in Task 3
    draw_time_vn=(18, 0),
)

ALL_PRODUCTS: tuple[VietlottProduct, ...] = (POWER_655, MEGA_645, LOTTO_535)
