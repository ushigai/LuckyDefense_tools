#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import random
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional, Tuple


ACTION_BASIC = "basic"
ACTION_SKILL1 = "skill1"
ACTION_SKILL2 = "skill2"
ACTION_SKILL3 = "skill3"
ACTION_ULT = "ult"

DamageTuple = Tuple[float, float, float, float, float]
RoundFn = Callable[[float], int]


@dataclass(frozen=True)
class SageKunParams15018:
    tick: int

    attack_power: float
    attack_speed: float

    base_attack_mult: float
    skill1_mult: float
    skill2_mult: float
    skill3_mult: float

    skill1_rate: float
    skill2_rate: float

    crit_rate: float
    crit_dmg: float

    ult_mult: float
    ult_mana: float
    ult_time: float

    attack_mana_recov: float
    mana_buff: float = 1.0

    n_iter: int = 20000
    seed: Optional[int] = None

    def validated(self) -> "SageKunParams15018":
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
            ("skill3_mult", self.skill3_mult),
            ("crit_dmg", self.crit_dmg),
            ("ult_mult", self.ult_mult),
            ("ult_mana", self.ult_mana),
            ("ult_time", self.ult_time),
            ("attack_mana_recov", self.attack_mana_recov),
            ("mana_buff", self.mana_buff),
        ]:
            if value < 0:
                raise ValueError(f"{name} must be >= 0")

        for name, value in [
            ("skill1_rate", self.skill1_rate),
            ("skill2_rate", self.skill2_rate),
            ("crit_rate", self.crit_rate),
        ]:
            if not (0.0 <= value <= 100.0):
                raise ValueError(f"{name} must be in [0, 100]")

        if self.skill1_rate + self.skill2_rate > 100.0:
            raise ValueError("skill1_rate + skill2_rate must be <= 100")
        if self.n_iter <= 0:
            raise ValueError("n_iter must be > 0")

        return self


def _apply_crit(rng: random.Random, crit_rate: float, crit_dmg: float, damage: float) -> float:
    if damage <= 0.0:
        return 0.0
    if rng.random() < (crit_rate / 100.0):
        return damage * crit_dmg
    return damage


def _choose_action(rng: random.Random, skill1_rate: float, skill2_rate: float) -> str:
    roll = rng.random() * 100.0
    if roll < skill1_rate:
        return ACTION_SKILL1
    if roll < (skill1_rate + skill2_rate):
        return ACTION_SKILL2
    return ACTION_BASIC


def _ult_duration_ticks(p: SageKunParams15018, round_fn: RoundFn) -> int:
    return max(0, int(round_fn(p.attack_speed * p.ult_time)))


def simulate_damage_breakdown_once_15018(
    p: SageKunParams15018,
    rng: random.Random,
    round_fn: RoundFn = round,
) -> DamageTuple:
    """
    Return one Monte Carlo trial as:
      (basic_total, 0.0, skill2_total, skill1_total + skill3_total, ult_total)

    skill3_total is the always-on fireball damage dealt once per tick.
    ult_total is the special basic attack damage dealt while the ult buff is
    active.
    """
    mana = 0.0
    ult_ticks_left = 0

    basic_total = 0.0
    skill1_total = 0.0
    skill2_total = 0.0
    skill3_total = 0.0
    ult_total = 0.0

    passive_mana_gain = (1.0 / p.attack_speed) * p.mana_buff
    basic_mana_gain = p.attack_mana_recov
    ult_duration = _ult_duration_ticks(p, round_fn)

    for _ in range(p.tick):
        if ult_ticks_left <= 0 and mana >= p.ult_mana:
            if ult_duration > 0:
                ult_ticks_left = ult_duration
            else:
                mana = 0.0

        in_ult = ult_ticks_left > 0
        action = _choose_action(rng, p.skill1_rate, p.skill2_rate)

        if action == ACTION_BASIC:
            mult = p.ult_mult if in_ult else p.base_attack_mult
            damage = p.attack_power * mult
            if in_ult:
                damage *= 1.5
            dealt = _apply_crit(rng, p.crit_rate, p.crit_dmg, damage)
            if in_ult:
                ult_total += dealt
            else:
                basic_total += dealt
        elif action == ACTION_SKILL1:
            damage = p.attack_power * p.skill1_mult
            if in_ult:
                damage *= 1.5
            dealt = _apply_crit(rng, p.crit_rate, p.crit_dmg, damage)
            skill1_total += dealt
        elif action == ACTION_SKILL2:
            damage = p.attack_power * p.skill2_mult
            if in_ult:
                damage *= 1.5
            dealt = _apply_crit(rng, p.crit_rate, p.crit_dmg, damage)
            skill2_total += dealt
        else:
            raise RuntimeError(f"unknown action: {action}")

        skill3_damage = p.attack_power * p.skill3_mult
        if in_ult:
            skill3_damage *= 1.5
        skill3_dealt = _apply_crit(rng, p.crit_rate, p.crit_dmg, skill3_damage)
        skill3_total += skill3_dealt

        if not in_ult:
            mana += passive_mana_gain
            if action == ACTION_BASIC:
                mana += basic_mana_gain

        if in_ult:
            ult_ticks_left -= 1
            if ult_ticks_left == 0:
                mana = 0.0

    return basic_total, 0.0, skill2_total, skill1_total + skill3_total, ult_total


def simulate_total_damage_once_15018(
    p: SageKunParams15018,
    rng: random.Random,
    round_fn: RoundFn = round,
) -> float:
    basic, skill1, skill2, skill3, ult = simulate_damage_breakdown_once_15018(
        p,
        rng,
        round_fn=round_fn,
    )
    return basic + skill1 + skill2 + skill3 + ult


def mean_total_damage_15018(
    params: Dict[str, Any],
    round_fn: RoundFn = round,
) -> DamageTuple:
    p = SageKunParams15018(**params).validated()
    rng = random.Random(p.seed)

    sum_basic = 0.0
    sum_skill1 = 0.0
    sum_skill2 = 0.0
    sum_skill3 = 0.0
    sum_ult = 0.0

    for _ in range(p.n_iter):
        basic, skill1, skill2, skill3, ult = simulate_damage_breakdown_once_15018(
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


def mean_dps_15018(
    params: Dict[str, Any],
    round_fn: RoundFn = round,
) -> float:
    tick = int(params["tick"])
    if tick <= 0:
        return 0.0
    basic, skill1, skill2, skill3, ult = mean_total_damage_15018(params, round_fn=round_fn)
    return (basic + skill1 + skill2 + skill3 + ult) / float(tick)


def _build_arg_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="SageKun(15018) Monte Carlo damage simulator")
    ap.add_argument("--tick", type=int, required=True)

    ap.add_argument("--attack_power", type=float, required=True)
    ap.add_argument("--attack_speed", type=float, required=True)

    ap.add_argument("--base_attack_mult", type=float, required=True)
    ap.add_argument("--skill1_mult", type=float, required=True)
    ap.add_argument("--skill2_mult", type=float, required=True)
    ap.add_argument("--skill3_mult", type=float, required=True)

    ap.add_argument("--skill1_rate", type=float, required=True)
    ap.add_argument("--skill2_rate", type=float, required=True)

    ap.add_argument("--crit_rate", type=float, required=True)
    ap.add_argument("--crit_dmg", type=float, required=True)

    ap.add_argument("--ult_mult", type=float, required=True)
    ap.add_argument("--ult_mana", type=float, required=True)
    ap.add_argument("--ult_time", type=float, required=True)

    ap.add_argument("--attack_mana_recov", type=float, required=True)
    ap.add_argument("--mana_buff", type=float, default=1.0)

    ap.add_argument("--n_iter", type=int, default=20000)
    ap.add_argument("--seed", type=int, default=None)
    return ap


def main(round_fn: RoundFn = round) -> None:
    args = _build_arg_parser().parse_args()
    params = vars(args)
    basic, skill1, skill2, skill3, ult = mean_total_damage_15018(params, round_fn=round_fn)
    total = basic + skill1 + skill2 + skill3 + ult
    tick = max(1, int(args.tick))

    print(f"basic      : {basic:.6f}")
    print(f"skill1     : {skill1:.6f}")
    print(f"skill2     : {skill2:.6f}")
    print(f"skill3     : {skill3:.6f}")
    print(f"ult        : {ult:.6f}")
    print(f"total      : {total:.6f}")
    print(f"dps        : {total / tick:.6f}")


if __name__ == "__main__":
    main()
