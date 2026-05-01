from __future__ import annotations

import random
from typing import Any, Dict

from dps_sim1.simulator.evergreen_chona import (
    DamageTuple,
    EvergreenChonaParams15019,
    mean_dps_15019 as _mean_dps_15019,
    mean_total_damage_15019 as _mean_total_damage_15019,
    simulate_damage_breakdown_once_15019 as _simulate_damage_breakdown_once_15019,
    simulate_total_damage_once_15019 as _simulate_total_damage_once_15019,
)
from dps_sim1.simulator.f32lock_rounding import round_half_up


def simulate_damage_breakdown_once_15019(
    p: EvergreenChonaParams15019,
    rng: random.Random,
) -> DamageTuple:
    return _simulate_damage_breakdown_once_15019(p, rng, round_fn=round_half_up)


def simulate_total_damage_once_15019(
    p: EvergreenChonaParams15019,
    rng: random.Random,
) -> float:
    return _simulate_total_damage_once_15019(p, rng, round_fn=round_half_up)


def mean_total_damage_15019(params: Dict[str, Any]) -> DamageTuple:
    return _mean_total_damage_15019(params, round_fn=round_half_up)


def mean_dps_15019(params: Dict[str, Any]) -> float:
    return _mean_dps_15019(params, round_fn=round_half_up)
