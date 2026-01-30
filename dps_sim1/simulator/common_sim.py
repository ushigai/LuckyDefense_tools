#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any, Optional, Tuple
import argparse
import math
import random


# 内部定義（ユーザー指定）
ACTION_BASIC = "basic"
ACTION_SKILL1 = "skill1"
ACTION_SKILL2 = "skill2"
ACTION_SKILL3 = "skill3"
ACTION_ULT = "ult"


@dataclass(frozen=True)
class CommonParams:
    # Damage related
    attack_power: float
    base_attack_mult: float
    skill1_mult: float
    skill2_mult: float
    skill3_mult: float
    ult_mult: float

    # Proc rates (percent 0..100)
    skill1_rate: float
    skill2_rate: float
    skill3_rate: float

    # Crit (percent 0..100, multiplier)
    crit_rate: float
    crit_dmg: float

    # Mana system
    attack_speed: float
    ult_mana: float
    attack_mana_recov: float
    mana_buff: float = 1.0


def _validate_params(p: CommonParams) -> None:
    if p.attack_speed <= 0:
        raise ValueError("attack_speed must be > 0")
    if p.mana_buff < 0:
        raise ValueError("mana_buff must be >= 0")
    if p.ult_mana < 0:
        raise ValueError("ult_mana must be >= 0")
    if p.attack_mana_recov < 0:
        raise ValueError("attack_mana_recov must be >= 0")

    for name, r in [("skill1_rate", p.skill1_rate), ("skill2_rate", p.skill2_rate), ("skill3_rate", p.skill3_rate), ("crit_rate", p.crit_rate)]:
        if r < 0 or r > 100:
            raise ValueError(f"{name} must be in [0, 100]")

    s = p.skill1_rate + p.skill2_rate + p.skill3_rate
    if s > 100 + 1e-12:
        raise ValueError("skill1_rate + skill2_rate + skill3_rate must be <= 100")

    if p.crit_dmg < 0:
        raise ValueError("crit_dmg must be >= 0")


def _roll_crit(rng: random.Random, crit_rate_pct: float, crit_dmg: float) -> float:
    # crit_rate_pct is 0..100
    if crit_rate_pct <= 0:
        return 1.0
    if crit_rate_pct >= 100:
        return crit_dmg
    return crit_dmg if (rng.random() < (crit_rate_pct / 100.0)) else 1.0


def _choose_nonult_action(rng: random.Random, p: CommonParams) -> str:
    """
    マナが ult_mana 未満の場合の遷移：
      skill1: skill1_rate
      skill2: skill2_rate
      skill3: skill3_rate
      basic : 100 - sum(skill*_rate)
    """
    r = rng.random() * 100.0
    if r < p.skill1_rate:
        return ACTION_SKILL1
    r -= p.skill1_rate
    if r < p.skill2_rate:
        return ACTION_SKILL2
    r -= p.skill2_rate
    if r < p.skill3_rate:
        return ACTION_SKILL3
    return ACTION_BASIC


def _damage_for_action(action: str, p: CommonParams) -> float:
    if action == ACTION_BASIC:
        mult = p.base_attack_mult
    elif action == ACTION_SKILL1:
        mult = p.skill1_mult
    elif action == ACTION_SKILL2:
        mult = p.skill2_mult
    elif action == ACTION_SKILL3:
        mult = p.skill3_mult
    elif action == ACTION_ULT:
        mult = p.ult_mult
    else:
        raise ValueError(f"unknown action: {action}")
    return p.attack_power * mult

def simulate_once_core(p: CommonParams, ticks: int, rng: random.Random) -> Tuple[float, Dict[str, float], Dict[str, int]]:
    """Run one trial and return (total_damage, dmg_breakdown, action_counts)."""
    if ticks < 0:
        raise ValueError("ticks must be >= 0")

    mana = 0.0
    dmg_br = {ACTION_BASIC: 0.0, ACTION_SKILL1: 0.0, ACTION_SKILL2: 0.0, ACTION_SKILL3: 0.0, ACTION_ULT: 0.0}
    counts = {ACTION_BASIC: 0, ACTION_SKILL1: 0, ACTION_SKILL2: 0, ACTION_SKILL3: 0, ACTION_ULT: 0}

    passive_recov = (1.0 / p.attack_speed) * p.mana_buff
    attack_recov = p.attack_mana_recov * p.mana_buff

    for _ in range(ticks):
        if mana >= p.ult_mana and p.ult_mana > 0:
            action = ACTION_ULT
            mana = 0.0
        elif mana >= p.ult_mana and p.ult_mana == 0:
            action = ACTION_ULT
            mana = 0.0
        else:
            action = _choose_nonult_action(rng, p)

        base = _damage_for_action(action, p)
        crit_mult = _roll_crit(rng, p.crit_rate, p.crit_dmg)
        dealt = base * crit_mult
        dmg_br[action] += dealt
        counts[action] += 1

        mana += passive_recov
        if action == ACTION_BASIC:
            mana += attack_recov

    total = sum(dmg_br.values())
    return total, dmg_br, counts


def simulate_once(p: CommonParams, ticks: int, rng: random.Random) -> Tuple[float, Dict[str, int]]:
    """
    1試行分のシミュレーションを実行して (総ダメージ, 行動回数dict) を返す。
    （従来互換の薄いラッパ）
    """
    total, _br, counts = simulate_once_core(p, ticks, rng)
    return total, counts


def simulate_many(p: CommonParams, ticks: int, trials: int, seed: Optional[int] = None) -> Dict[str, Any]:
    _validate_params(p)
    if trials <= 0:
        raise ValueError("trials must be > 0")

    rng = random.Random(seed)

    damages = []
    sum_counts = {ACTION_BASIC: 0, ACTION_SKILL1: 0, ACTION_SKILL2: 0, ACTION_SKILL3: 0, ACTION_ULT: 0}
    sum_breakdown = {ACTION_BASIC: 0.0, ACTION_SKILL1: 0.0, ACTION_SKILL2: 0.0, ACTION_SKILL3: 0.0, ACTION_ULT: 0.0}

    for _ in range(trials):
        d, br, c = simulate_once_core(p, ticks, rng)
        damages.append(d)
        for k in sum_counts:
            sum_counts[k] += c.get(k, 0)
        for k in sum_breakdown:
            sum_breakdown[k] += br.get(k, 0.0)

    mean = sum(damages) / trials
    # 標本分散（不偏に寄せる）
    if trials >= 2:
        var = sum((x - mean) ** 2 for x in damages) / (trials - 1)
    else:
        var = 0.0
    std = math.sqrt(var)

    avg_counts = {k: v / trials for k, v in sum_counts.items()}
    mean_breakdown_total = {k: v / trials for k, v in sum_breakdown.items()}

    return {
        "ticks": ticks,
        "trials": trials,
        "seed": seed,
        "mean_total_damage": mean,
        "std_total_damage": std,
        "mean_damage_per_tick": (mean / ticks) if ticks > 0 else 0.0,
        "avg_action_counts": avg_counts,
        "mean_breakdown_total": mean_breakdown_total,
    }


def mean_total_damage_common(options: Dict[str, Any]) -> Tuple[float, float, float, float, float]:
    """
    外部から「平均総ダメージ」だけ取りたい用。

    options例:
      {
        "attack_power": 100000,
        "base_attack_mult": 1.0,
        "skill1_rate": 20,
        "skill2_rate": 10,
        "skill3_rate": 5,
        "attack_speed": 1.5,
        "attack_mana_recov": 1,
        "mana_buff": 1.0,
        "skill1_mult": 2.0,
        "skill2_mult": 3.0,
        "skill3_mult": 4.0,
        "ult_mult": 10.0,
        "ult_mana": 190,
        "crit_rate": 20,
        "crit_dmg": 2.5,
        "ticks": 1000,
        "trials": 10000,
        "seed": 1
      }
    """
    p = CommonParams(
        attack_power=float(options["attack_power"]),
        base_attack_mult=float(options["base_attack_mult"]),
        skill1_mult=float(options["skill1_mult"]),
        skill2_mult=float(options["skill2_mult"]),
        skill3_mult=float(options["skill3_mult"]),
        ult_mult=float(options["ult_mult"]),
        skill1_rate=float(options["skill1_rate"]),
        skill2_rate=float(options["skill2_rate"]),
        skill3_rate=float(options["skill3_rate"]),
        crit_rate=float(options["crit_rate"]),
        crit_dmg=float(options["crit_dmg"]),
        attack_speed=float(options["attack_speed"]),
        ult_mana=float(options["ult_mana"]),
        attack_mana_recov=float(options["attack_mana_recov"]),
        mana_buff=float(options.get("mana_buff", 1.0)),
    )
    ticks = int(options["ticks"])
    trials = int(options.get("trials", 10000))
    seed = options.get("seed", None)
    result = simulate_many(p, ticks=ticks, trials=trials, seed=seed)
    br = result.get('mean_breakdown_total', {})
    return (float(br.get(ACTION_BASIC, 0.0)), float(br.get(ACTION_SKILL1, 0.0)), float(br.get(ACTION_SKILL2, 0.0)), float(br.get(ACTION_SKILL3, 0.0)), float(br.get(ACTION_ULT, 0.0)))


def _build_argparser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="common DPS Monte Carlo simulator (tick-based)")
    ap.add_argument("--ticks", type=int, required=True, help="number of ticks to simulate")
    ap.add_argument("--trials", type=int, default=10000, help="number of Monte Carlo trials")
    ap.add_argument("--seed", type=int, default=None, help="random seed")

    ap.add_argument("--attack_power", type=float, required=True)
    ap.add_argument("--attack_speed", type=float, required=True)
    ap.add_argument("--mana_buff", type=float, default=1.0)
    ap.add_argument("--ult_mana", type=float, required=True)
    ap.add_argument("--attack_mana_recov", type=float, required=True)

    ap.add_argument("--base_attack_mult", type=float, required=True)
    ap.add_argument("--skill1_mult", type=float, required=True)
    ap.add_argument("--skill2_mult", type=float, required=True)
    ap.add_argument("--skill3_mult", type=float, required=True)
    ap.add_argument("--ult_mult", type=float, required=True)

    ap.add_argument("--skill1_rate", type=float, required=True, help="percent 0..100")
    ap.add_argument("--skill2_rate", type=float, required=True, help="percent 0..100")
    ap.add_argument("--skill3_rate", type=float, required=True, help="percent 0..100")

    ap.add_argument("--crit_rate", type=float, required=True, help="percent 0..100")
    ap.add_argument("--crit_dmg", type=float, required=True, help="multiplier (e.g., 2.5)")

    return ap


def main() -> None:
    ap = _build_argparser()
    args = ap.parse_args()

    p = CommonParams(
        attack_power=args.attack_power,
        base_attack_mult=args.base_attack_mult,
        skill1_mult=args.skill1_mult,
        skill2_mult=args.skill2_mult,
        skill3_mult=args.skill3_mult,
        ult_mult=args.ult_mult,
        skill1_rate=args.skill1_rate,
        skill2_rate=args.skill2_rate,
        skill3_rate=args.skill3_rate,
        crit_rate=args.crit_rate,
        crit_dmg=args.crit_dmg,
        attack_speed=args.attack_speed,
        ult_mana=args.ult_mana,
        attack_mana_recov=args.attack_mana_recov,
        mana_buff=args.mana_buff,
    )

    result = simulate_many(p, ticks=args.ticks, trials=args.trials, seed=args.seed)

    print("=== common Monte Carlo result ===")
    print(f"ticks: {result['ticks']}")
    print(f"trials: {result['trials']}")
    print(f"seed: {result['seed']}")
    print(f"mean_total_damage: {result['mean_total_damage']:.6f}")
    print(f"std_total_damage:  {result['std_total_damage']:.6f}")
    print(f"mean_damage_per_tick: {result['mean_damage_per_tick']:.6f}")
    print("avg_action_counts_per_trial:")
    for k in [ACTION_ULT, ACTION_SKILL1, ACTION_SKILL2, ACTION_SKILL3, ACTION_BASIC]:
        print(f"  {k}: {result['avg_action_counts'][k]:.3f}")


if __name__ == "__main__":
    main()

