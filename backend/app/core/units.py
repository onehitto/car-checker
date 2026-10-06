"""Unit conversions. Data is stored in kilometres and litres; conversion happens at the edges."""

from enum import StrEnum

KM_PER_MILE = 1.609344
L_100KM_TO_MPG_US = 235.214583
L_100KM_TO_MPG_UK = 282.480936


class DistanceUnit(StrEnum):
    KM = "km"
    MI = "mi"


class ConsumptionUnit(StrEnum):
    L_100KM = "l_100km"
    KM_L = "km_l"
    MPG_US = "mpg_us"
    MPG_UK = "mpg_uk"


def convert_distance(km: float, unit: DistanceUnit) -> float:
    return km / KM_PER_MILE if unit is DistanceUnit.MI else km


def convert_consumption(l_per_100km: float, unit: ConsumptionUnit) -> float:
    """Convert a L/100 km figure. Inverse units (km/L, MPG) are undefined for 0."""
    if unit is ConsumptionUnit.L_100KM:
        return l_per_100km
    if l_per_100km <= 0:
        raise ValueError("Consumption must be positive to convert to an inverse unit")
    if unit is ConsumptionUnit.KM_L:
        return 100 / l_per_100km
    if unit is ConsumptionUnit.MPG_US:
        return L_100KM_TO_MPG_US / l_per_100km
    return L_100KM_TO_MPG_UK / l_per_100km
