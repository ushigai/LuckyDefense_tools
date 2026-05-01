#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import random
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional, Tuple

from dps_sim1.simulator.f32lock_rounding import round_half_up as round


ACTION_BASIC = "basic"
ACTION_SKILL1 = "skill1"
ACTION_SKILL2 = "skill2"
ACTION_SKILL3 = "skill3"
ACTION_ULT = "ult"

DamageTuple = Tuple[float, float, float, float, float]
RoundFn = Callable[[float], int]


@dataclass(frozen=True)
class EvergreenChonaParams15019:
    tick: int

    attack_power: float
    attack_speed: float

    base_attack_mult: float
    skill1_mult: float
    skill2_mult: float
    skill2_double_rate: float
    ult_mult: float

    crit_rate: float
    crit_dmg: float

    n_iter: int = 10000
    seed: Optional[int] = None

    def validated(self) -> "EvergreenChonaParams15019":
        if self.tick < 0:
            raise ValueError("tick must be >= 0")
        if self.attack_power < 0:
            raise ValueError("attack_power must be >= 0")
        if self.attack_speed <= 0:
            raise ValueError("attack_speed must be > 0")

        for name, value in [
            ("base_attack_mult", self.base_attack_mult),
            ("skill1_mult", self.skill1_mult),
            ("skill2_mult", self.skill2_mult),
            ("ult_mult", self.ult_mult),
            ("crit_dmg", self.crit_dmg),
        ]:
            if value < 0:
                raise ValueError(f"{name} must be >= 0")

        for name, value in [
            ("skill2_double_rate", self.skill2_double_rate),
            ("crit_rate", self.crit_rate),
        ]:
            if not (0.0 <= value <= 100.0):
                raise ValueError(f"{name} must be in [0, 100]")

        if self.n_iter <= 0:
            raise ValueError("n_iter must be > 0")

        return self


def _roll_percent(rng: random.Random, pct_0_100: float) -> bool:
    return rng.random() < (pct_0_100 / 100.0)


def _apply_crit(rng: random.Random, crit_rate: float, crit_dmg: float, damage: float) -> float:
    if damage <= 0.0:
        return 0.0
    if _roll_percent(rng, crit_rate):
        return damage * crit_dmg
    return damage


def _damage(p: EvergreenChonaParams15019, rng: random.Random, mult: float) -> float:
    return _apply_crit(rng, p.crit_rate, p.crit_dmg, p.attack_power * mult)


def _mini_duration_ticks(p: EvergreenChonaParams15019, round_fn: RoundFn) -> int:
    return max(0, int(round_fn(30.0 * p.attack_speed)))


def simulate_damage_breakdown_once_15019(
    p: EvergreenChonaParams15019,
    rng: random.Random,
    round_fn: RoundFn = round,
) -> DamageTuple:
    """
    Return one Monte Carlo trial as:
      (basic_total, skill1_total, skill2_total, 0.0, ult_total)

    One tick performs one basic attack. Skill1 is added every 9th basic attack.
    Skill2 summons mini trees every 20th basic attack. Active mini trees deal
    skill2 damage once per tick until their duration expires. When the field
    reaches 5 or more mini trees, all mini trees are consumed and ult damage is
    dealt immediately.
    """
    mini_duration = _mini_duration_ticks(p, round_fn)
    mini_trees: list[int] = []
    attack_count = 0

    basic_total = 0.0
    skill1_total = 0.0
    skill2_total = 0.0
    ult_total = 0.0

    for _ in range(p.tick):
        attack_count += 1
        basic_total += _damage(p, rng, p.base_attack_mult)

        if attack_count % 9 == 0:
            skill1_total += _damage(p, rng, p.skill1_mult)

        if attack_count % 20 == 0:
            summon_count = 2 if _roll_percent(rng, p.skill2_double_rate) else 1
            if mini_duration > 0:
                mini_trees.extend([mini_duration] * summon_count)

            if len(mini_trees) >= 5:
                ult_total += _damage(p, rng, p.ult_mult)
                mini_trees.clear()

        if mini_trees:
            next_mini_trees: list[int] = []
            for remaining_ticks in mini_trees:
                if remaining_ticks <= 0:
                    continue
                skill2_total += _damage(p, rng, p.skill2_mult)
                remaining_ticks -= 1
                if remaining_ticks > 0:
                    next_mini_trees.append(remaining_ticks)
            mini_trees = next_mini_trees

    return basic_total, skill1_total, skill2_total, 0.0, ult_total


def simulate_total_damage_once_15019(
    p: EvergreenChonaParams15019,
    rng: random.Random,
    round_fn: RoundFn = round,
) -> float:
    basic, skill1, skill2, skill3, ult = simulate_damage_breakdown_once_15019(
        p,
        rng,
        round_fn=round_fn,
    )
    return basic + skill1 + skill2 + skill3 + ult


def _coerce_params(options: Dict[str, Any]) -> EvergreenChonaParams15019:
    if "tick" in options and options["tick"] is not None:
        tick = int(options["tick"])
    elif "ticks" in options and options["ticks"] is not None:
        tick = int(options["ticks"])
    elif "durationSec" in options and options["durationSec"] is not None:
        attack_speed = float(options["attack_speed"])
        tick = int(round(float(options["durationSec"]) * attack_speed))
    else:
        raise ValueError("options must include 'tick', 'ticks', or 'durationSec'.")

    n_iter = int(options.get("n_iter", options.get("trials", 10000)))
    seed_raw = options.get("seed", None)
    seed = None if seed_raw is None else int(seed_raw)

    return EvergreenChonaParams15019(
        tick=tick,
        attack_power=float(options["attack_power"]),
        attack_speed=float(options["attack_speed"]),
        base_attack_mult=float(options["base_attack_mult"]),
        skill1_mult=float(options["skill1_mult"]),
        skill2_mult=float(options["skill2_mult"]),
        skill2_double_rate=float(options["skill2_double_rate"]),
        ult_mult=float(options["ult_mult"]),
        crit_rate=float(options["crit_rate"]),
        crit_dmg=float(options["crit_dmg"]),
        n_iter=n_iter,
        seed=seed,
    ).validated()


def mean_total_damage_15019(
    params: Dict[str, Any],
    round_fn: RoundFn = round,
) -> DamageTuple:
    p = _coerce_params(params)
    rng = random.Random(p.seed)

    sum_basic = 0.0
    sum_skill1 = 0.0
    sum_skill2 = 0.0
    sum_skill3 = 0.0
    sum_ult = 0.0

    for _ in range(p.n_iter):
        basic, skill1, skill2, skill3, ult = simulate_damage_breakdown_once_15019(
            p,
            rng,
            round_fn=round_fn,
        )
        sum_basic += basic
        sum_skill1 += skill1
        sum_skill2 += skill2
        sum_skill3 += skill3
        sum_ult += ult

    inv = 1.0 / float(p.n_iter)
    return (
        sum_basic * inv,
        sum_skill1 * inv,
        sum_skill2 * inv,
        sum_skill3 * inv,
        sum_ult * inv,
    )


def mean_dps_15019(
    params: Dict[str, Any],
    round_fn: RoundFn = round,
) -> float:
    p = _coerce_params(params)
    if p.tick <= 0:
        return 0.0
    basic, skill1, skill2, skill3, ult = mean_total_damage_15019(params, round_fn=round_fn)
    return (basic + skill1 + skill2 + skill3 + ult) / float(p.tick)


def _build_arg_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="Evergreen Chona(15019) Monte Carlo damage simulator")
    ap.add_argument("--tick", "--ticks", dest="tick", type=int, required=True)
    ap.add_argument("--attack_power", type=float, required=True)
    ap.add_argument("--attack_speed", type=float, required=True)
    ap.add_argument("--base_attack_mult", type=float, required=True)
    ap.add_argument("--skill1_mult", type=float, required=True)
    ap.add_argument("--skill2_mult", type=float, required=True)
    ap.add_argument("--skill2_double_rate", type=float, required=True, help="0..100 (%)")
    ap.add_argument("--ult_mult", type=float, required=True)
    ap.add_argument("--crit_rate", type=float, required=True, help="0..100 (%)")
    ap.add_argument("--crit_dmg", type=float, required=True)
    ap.add_argument("--n_iter", "--trials", dest="n_iter", type=int, default=10000)
    ap.add_argument("--seed", type=int, default=None)
    return ap


def main() -> None:
    args = _build_arg_parser().parse_args()
    params = vars(args)
    basic, skill1, skill2, skill3, ult = mean_total_damage_15019(params)
    total = basic + skill1 + skill2 + skill3 + ult
    tick = max(1, int(args.tick))

    print(f"basic      : {basic:.6f}")
    print(f"skill1     : {skill1:.6f}")
    print(f"skill2     : {skill2:.6f}")
    print(f"skill3     : {skill3:.6f}")
    print(f"ult        : {ult:.6f}")
    print(f"total      : {total:.6f}")
    print(f"damage/tick: {total / tick:.6f}")


if __name__ == "__main__":
    main()
