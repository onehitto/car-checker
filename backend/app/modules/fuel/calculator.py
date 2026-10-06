"""Fuel consumption (full-tank method) and fuel statistics. Pure functions.

See docs/05-domain-logic.md, section 16. Between two consecutive *full* fill-ups, the fuel
burnt is the sum of every fill-up after the first one (partial top-ups included) up to and
including the second one. A fill-up flagged `missed_previous` breaks the chain.
"""

import uuid
from collections import defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from app.core.dates import month_key

PRICE_TOLERANCE = Decimal("0.05")


@dataclass(frozen=True, slots=True)
class FillUp:
    id: uuid.UUID
    fill_date: date
    mileage: int
    liters: Decimal
    total_price: Decimal | None
    full_tank: bool
    missed_previous: bool


@dataclass(frozen=True, slots=True)
class FillUpMetrics:
    distance_since_previous: int | None
    consumption_l_100km: float | None


@dataclass(frozen=True, slots=True)
class Segment:
    """Distance between two full tanks and the fuel used over it."""

    start_mileage: int
    end_mileage: int
    end_date: date
    liters: Decimal
    cost: Decimal | None  # None when a fill-up of the segment has no price

    @property
    def distance(self) -> int:
        return self.end_mileage - self.start_mileage

    @property
    def consumption(self) -> float:
        return float(self.liters) / self.distance * 100


@dataclass(frozen=True, slots=True)
class MonthlyFuel:
    month: str
    liters: Decimal
    cost: Decimal


@dataclass(frozen=True, slots=True)
class FuelStatistics:
    fill_up_count: int
    total_liters: Decimal
    total_cost: Decimal
    distance_tracked: int
    average_consumption_l_100km: float | None
    last_consumption_l_100km: float | None
    cost_per_km: float | None
    average_price_per_liter: float | None
    monthly: list[MonthlyFuel]


def _ordered(fill_ups: Iterable[FillUp]) -> list[FillUp]:
    return sorted(fill_ups, key=lambda f: (f.mileage, f.fill_date, f.id))


def analyze(fill_ups: Iterable[FillUp]) -> tuple[dict[uuid.UUID, FillUpMetrics], list[Segment]]:
    """Per fill-up metrics and the measurable segments, in mileage order."""
    metrics: dict[uuid.UUID, FillUpMetrics] = {}
    segments: list[Segment] = []
    previous: FillUp | None = None
    anchor: FillUp | None = None  # last full tank of an unbroken chain
    liters = Decimal(0)
    cost: Decimal | None = Decimal(0)

    for fill_up in _ordered(fill_ups):
        distance = fill_up.mileage - previous.mileage if previous else None
        consumption = None
        if fill_up.missed_previous:
            anchor = None
        if anchor is not None:
            liters += fill_up.liters
            cost = (
                None if cost is None or fill_up.total_price is None else cost + fill_up.total_price
            )
            if fill_up.full_tank and fill_up.mileage > anchor.mileage:
                segment = Segment(anchor.mileage, fill_up.mileage, fill_up.fill_date, liters, cost)
                segments.append(segment)
                consumption = segment.consumption
        if fill_up.full_tank:
            anchor, liters, cost = fill_up, Decimal(0), Decimal(0)
        metrics[fill_up.id] = FillUpMetrics(distance, consumption)
        previous = fill_up
    return metrics, segments


def summarize(fill_ups: Sequence[FillUp]) -> FuelStatistics:
    _, segments = analyze(fill_ups)
    total_liters = sum((f.liters for f in fill_ups), Decimal(0))
    priced = [f for f in fill_ups if f.total_price is not None]
    total_cost = sum((f.total_price or Decimal(0) for f in priced), Decimal(0))
    priced_liters = sum((f.liters for f in priced), Decimal(0))

    distance = sum(s.distance for s in segments)
    costed = [s for s in segments if s.cost is not None]
    costed_distance = sum(s.distance for s in costed)

    monthly: dict[str, list[Decimal]] = defaultdict(lambda: [Decimal(0), Decimal(0)])
    for fill_up in fill_ups:
        bucket = monthly[month_key(fill_up.fill_date)]
        bucket[0] += fill_up.liters
        bucket[1] += fill_up.total_price or Decimal(0)

    return FuelStatistics(
        fill_up_count=len(fill_ups),
        total_liters=total_liters,
        total_cost=total_cost,
        distance_tracked=distance,
        average_consumption_l_100km=(
            float(sum((s.liters for s in segments), Decimal(0))) / distance * 100
            if distance
            else None
        ),
        last_consumption_l_100km=segments[-1].consumption if segments else None,
        cost_per_km=(
            float(sum((s.cost or Decimal(0) for s in costed), Decimal(0))) / costed_distance
            if costed_distance
            else None
        ),
        average_price_per_liter=float(total_cost / priced_liters) if priced_liters else None,
        monthly=[MonthlyFuel(month, *values) for month, values in sorted(monthly.items())],
    )


def resolve_prices(
    liters: Decimal, price_per_liter: Decimal | None, total_price: Decimal | None
) -> tuple[Decimal | None, Decimal | None]:
    """Complete (price_per_liter, total_price) from what the user entered."""
    if price_per_liter is not None and total_price is not None:
        if abs(liters * price_per_liter - total_price) > PRICE_TOLERANCE:
            raise ValueError("total_price does not match liters x price_per_liter.")
        return price_per_liter, total_price
    if price_per_liter is not None:
        total = (liters * price_per_liter).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return price_per_liter, total
    if total_price is not None:
        unit = (total_price / liters).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
        return unit, total_price
    return None, None
