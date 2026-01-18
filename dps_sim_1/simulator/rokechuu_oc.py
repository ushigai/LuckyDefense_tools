#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import math
import random
import statistics
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


# =========================
# Core simulation
# =========================

@dataclass(frozen=True)
class RokechuuParams:
    # percentages (0..100)
    skill1_rate: float
    cirt_rate: float

    # multipliers
    skill1_mult: float
    skill2_mult: float
    ult_mult: float
    cirt_dmg: float

    # stats
    attack_power: float
    attack_speed: float
    ult_mana: float

    # time scale
    tick_seconds: float = 1.0  # 1 tick = 1.0 sec (DPS用)


def _clamp01(x: float) -> float:
    return 0.0 if x < 0.0 else 1.0 if x > 1.0 else x


def _p_from_percent(pct: float) -> float:
    return _clamp01(pct / 100.0)


def _roll_crit(rng: random.Random, base_damage: float, p_crit: float, cirt_dmg: float) -> float:
    # cirt_rate の確率で cirt_dmg 倍
    if rng.random() < p_crit:
        return base_damage * cirt_dmg
    return base_damage


def simulate_once(
    ticks: int,
    params: RokechuuParams,
    rng: random.Random,
) -> Dict[str, float]:
    """
    1試行分の合計ダメージ内訳を返す: {"basic":..., "skill1":..., "skill2":..., "ult":...}
    """
    if ticks <= 0:
        return {"basic": 0.0, "skill1": 0.0, "skill2": 0.0, "ult": 0.0}

    p_skill1 = _p_from_percent(params.skill1_rate)
    p_crit = _p_from_percent(params.cirt_rate)

    if params.attack_speed <= 0:
        raise ValueError("attack_speed must be > 0")

    mana: float = 0.0
    basic_stack: int = 0  # basic を実行した回数スタック（15で超爆破ロケット）
    mana_regen_per_basic: float = 1.0 / params.attack_speed  # basic の tick 終了時だけ回復

    totals = {"basic": 0.0, "skill1": 0.0, "skill2": 0.0, "ult": 0.0}

    for _ in range(ticks):
        action = "basic"

        # 優先度: ult > skill2(ロケット) > skill1(確率) > basic
        if mana >= params.ult_mana:
            action = "ult"
            dmg0 = params.attack_power * params.ult_mult
            totals["ult"] += _roll_crit(rng, dmg0, p_crit, params.cirt_dmg)
            mana = 0.0  # ult 後 0

        elif basic_stack >= 15:
            action = "skill2"
            dmg0 = params.attack_power * params.skill2_mult
            totals["skill2"] += _roll_crit(rng, dmg0, p_crit, params.cirt_dmg)
            basic_stack = 0  # ロケットで消費（リセット）

        else:
            # mana < ult_mana かつ stack < 15 のときのみ確率で skill1
            if rng.random() < p_skill1:
                action = "skill1"
                dmg0 = params.attack_power * params.skill1_mult
                totals["skill1"] += _roll_crit(rng, dmg0, p_crit, params.cirt_dmg)
            else:
                action = "basic"
                dmg0 = params.attack_power * 1.0
                totals["basic"] += _roll_crit(rng, dmg0, p_crit, params.cirt_dmg)
                basic_stack += 1

        # tick 最後のマナ回復（basic した tick のみ回復）
        if action == "basic":
            mana += mana_regen_per_basic

    return totals


def simulate_many(
    ticks: int,
    trials: int,
    params: RokechuuParams,
    seed: Optional[int] = None,
) -> Dict[str, object]:
    if trials <= 0:
        raise ValueError("trials must be > 0")

    rng = random.Random(seed)

    totals_per_trial: List[float] = []
    breakdown_sum = {"basic": 0.0, "skill1": 0.0, "skill2": 0.0, "ult": 0.0}

    for _ in range(trials):
        bd = simulate_once(ticks, params, rng)
        for k in breakdown_sum:
            breakdown_sum[k] += float(bd[k])
        totals_per_trial.append(sum(bd.values()))

    mean_total = statistics.fmean(totals_per_trial)
    # 95% CI of mean (normal approx). trialsが十分大きい想定。
    stdev = statistics.pstdev(totals_per_trial)  # population stdev
    se = stdev / math.sqrt(trials)
    ci95 = 1.96 * se

    totals_sorted = sorted(totals_per_trial)
    def percentile(p: float) -> float:
        if not totals_sorted:
            return 0.0
        # nearest-rankっぽい簡易
        idx = int(round((p / 100.0) * (len(totals_sorted) - 1)))
        idx = max(0, min(len(totals_sorted) - 1, idx))
        return float(totals_sorted[idx])

    duration_sec = ticks * params.tick_seconds
    mean_dps = mean_total / duration_sec if duration_sec > 0 else 0.0

    breakdown_mean = {k: v / trials for k, v in breakdown_sum.items()}

    return {
        "ticks": ticks,
        "trials": trials,
        "seed": seed,
        "mean_total_damage": mean_total,
        "mean_dps": mean_dps,
        "ci95_total": ci95,
        "percentiles_total": {
            "p05": percentile(5),
            "p50": percentile(50),
            "p95": percentile(95),
        },
        "mean_breakdown": breakdown_mean,
    }


# =========================
# External-call function
# =========================

def mean_total_damage_5115(
    ticks: int,
    trials: int = 1000,
    *,
    skill1_rate: float,
    attack_speed: float,
    attack_power: float,
    skill1_mult: float,
    skill2_mult: float,
    ult_mult: float,
    ult_mana: float,
    cirt_rate: float,
    cirt_dmg: float,
    seed: Optional[int] = None,
    tick_seconds: float = 1.0,
) -> float:
    """
    外部から「平均総ダメージ」だけ参照する用。
    """
    params = RokechuuParams(
        skill1_rate=skill1_rate,
        cirt_rate=cirt_rate,
        skill1_mult=skill1_mult,
        skill2_mult=skill2_mult,
        ult_mult=ult_mult,
        cirt_dmg=cirt_dmg,
        attack_power=attack_power,
        attack_speed=attack_speed,
        ult_mana=ult_mana,
        tick_seconds=tick_seconds,
    )
    res = simulate_many(ticks=ticks, trials=trials, params=params, seed=seed)
    return float(res["mean_total_damage"])


# =========================
# CLI
# =========================

def _compute_ticks_from_duration(duration_sec: float, attack_speed: float) -> int:
    # 「attack_speed によって tick数を計算 → 小数なら round()」の要件に対応
    # ここでは「1秒あたり attack_speed 回行動」として ticks = round(duration_sec * attack_speed)
    return int(round(duration_sec * attack_speed))


def main() -> None:
    ap = argparse.ArgumentParser(description="Rokechuu(5115) Monte Carlo DPS Simulator")
    ap.add_argument("--ticks", type=int, default=None, help="simulate ticks (int). If omitted, --durationSec is used.")
    ap.add_argument("--durationSec", type=float, default=None, help="simulate seconds. ticks=round(durationSec*attack_speed)")
    ap.add_argument("--trials", type=int, default=1000)
    ap.add_argument("--seed", type=int, default=None)

    ap.add_argument("--attack_power", type=float, required=True)
    ap.add_argument("--attack_speed", type=float, required=True)
    ap.add_argument("--ult_mana", type=float, required=True)

    ap.add_argument("--skill1_rate", type=float, required=True, help="0..100 (percent)")
    ap.add_argument("--skill1_mult", type=float, required=True)
    ap.add_argument("--skill2_mult", type=float, required=True)
    ap.add_argument("--ult_mult", type=float, required=True)

    ap.add_argument("--cirt_rate", type=float, required=True, help="0..100 (percent)")
    ap.add_argument("--cirt_dmg", type=float, required=True)

    ap.add_argument("--tick_seconds", type=float, default=1.0, help="seconds per tick for DPS output (default 1.0)")

    args = ap.parse_args()

    if args.ticks is None:
        if args.durationSec is None:
            raise SystemExit("Either --ticks or --durationSec is required.")
        ticks = _compute_ticks_from_duration(args.durationSec, args.attack_speed)
    else:
        ticks = int(args.ticks)

    params = RokechuuParams(
        skill1_rate=args.skill1_rate,
        cirt_rate=args.cirt_rate,
        skill1_mult=args.skill1_mult,
        skill2_mult=args.skill2_mult,
        ult_mult=args.ult_mult,
        cirt_dmg=args.cirt_dmg,
        attack_power=args.attack_power,
        attack_speed=args.attack_speed,
        ult_mana=args.ult_mana,
        tick_seconds=args.tick_seconds,
    )

    res = simulate_many(ticks=ticks, trials=args.trials, params=params, seed=args.seed)

    print("=== Rokechuu(5115) Damage Simulation ===")
    print(f"ticks             : {res['ticks']}")
    print(f"trials            : {res['trials']}")
    print(f"tick_seconds      : {params.tick_seconds}")
    print(f"seed              : {res['seed']}")
    print("--- params ---")
    print(f"attack_power      : {params.attack_power}")
    print(f"attack_speed      : {params.attack_speed}")
    print(f"ult_mana          : {params.ult_mana}")
    print(f"skill1_rate(%)    : {params.skill1_rate}")
    print(f"skill1_mult       : {params.skill1_mult}")
    print(f"skill2_mult       : {params.skill2_mult}")
    print(f"ult_mult          : {params.ult_mult}")
    print(f"cirt_rate(%)      : {params.cirt_rate}")
    print(f"cirt_dmg          : {params.cirt_dmg}")

    print("--- results ---")
    print(f"mean_total_damage : {res['mean_total_damage']:.6f}")
    print(f"mean_DPS          : {res['mean_dps']:.6f}")
    print(f"95% CI (total)    : ±{res['ci95_total']:.6f}")
    p = res["percentiles_total"]
    print(f"percentiles total : p05={p['p05']:.6f}, p50={p['p50']:.6f}, p95={p['p95']:.6f}")

    b = res["mean_breakdown"]
    print("--- mean breakdown (total damage per trial) ---")
    print(f" basic : {b['basic']:.6f}")
    print(f" skill1: {b['skill1']:.6f}")
    print(f" skill2: {b['skill2']:.6f}")
    print(f" ult   : {b['ult']:.6f}")


if __name__ == "__main__":
    main()

