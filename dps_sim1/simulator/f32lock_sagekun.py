#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import random
from typing import Any, Dict

from dps_sim1.simulator.f32lock_rounding import round_half_up
from dps_sim1.simulator.sagekun import (
    SageKunParams15018,
    mean_dps_15018 as _mean_dps_15018,
    mean_total_damage_15018 as _mean_total_damage_15018,
    simulate_damage_breakdown_once_15018 as _simulate_damage_breakdown_once_15018,
    simulate_total_damage_once_15018 as _simulate_total_damage_once_15018,
    main as _main,
)


def simulate_damage_breakdown_once_15018(p: SageKunParams15018, rng: random.Random):
    return _simulate_damage_breakdown_once_15018(p, rng, round_fn=round_half_up)


def simulate_total_damage_once_15018(p: SageKunParams15018, rng: random.Random) -> float:
    return _simulate_total_damage_once_15018(p, rng, round_fn=round_half_up)


def mean_total_damage_15018(params: Dict[str, Any]):
    return _mean_total_damage_15018(params, round_fn=round_half_up)


def mean_dps_15018(params: Dict[str, Any]) -> float:
    return _mean_dps_15018(params, round_fn=round_half_up)


def main() -> None:
    _main(round_fn=round_half_up)


if __name__ == "__main__":
    main()
