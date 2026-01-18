#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Hayley (id: 5021) Monte Carlo DPS Simulator

- 1 tick ごとに行動(基本/スキル/究極)を1回行う
- 行動決定は tick 開始時、マナ回復は tick 末尾
- mana_buff は「すべてのマナ回復処理」に乗算（基本+1 と 1/attack_speed の両方）
- ult 発動でバフ状態へ。バフ中はマナ回復不可。バフ終了時にマナは 0。
- 会心: 1行動につき1回判定。確率 crit_rate で crit_dmg 倍

Usage (example):
  python hayley_5021.py --ticks 42000 --trials 1000 --seed 1 \
    --attack-speed 1.5 --attack-power 82500 --attack-power-ult 120000 \
    --skill1-rate 10 --skill2-rate 10 --skill1-mult 150 --skill2-mult 80 \
    --ult-mana 190 --mana-buff 1.0 --crit-rate 20 --crit-dmg 2.5
"""

from __future__ import annotations

from dataclasses import dataclass
import argparse
import math
import random
from typing import Dict, Tuple, List


# ----------------------------
# Config
# ----------------------------
@dataclass(frozen=True)
class HayleyConfig:
    # given
    attack_speed: float
    attack_power: float
    attack_power_ult: float

    skill1_rate_pct: float  # 0..100
    skill2_rate_pct: float  # 0..100
    skill1_mult: float      # e.g. 2 => 2x, 150 => 150x
    skill2_mult: float

    ult_mana: float
    mana_buff: float

    crit_rate_pct: float    # 0..100
    crit_dmg: float         # e.g. 2.5

    # ult buff behavior
    ult_buff_mult: float = 1.5
    ult_buff_ticks_base: float = 30.0  # buff ticks = round(ult_buff_ticks_base * attack_speed)

    # tick_seconds for DPS conversion
    tick_seconds: float = 1.0


# ----------------------------
# Helpers
# ----------------------------
def _clamp01(x: float) -> float:
    return 0.0 if x < 0.0 else 1.0 if x > 1.0 else x


def _percentile(sorted_vals: List[float], q: float) -> float:
    """
    q: 0..100
    linear interpolation between closest ranks
    """
    if not sorted_vals:
        return 0.0
    if q <= 0:
        return sorted_vals[0]
    if q >= 100:
        return sorted_vals[-1]
    n = len(sorted_vals)
    pos = (q / 100.0) * (n - 1)
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))
    if lo == hi:
        return sorted_vals[lo]
    w = pos - lo
    return sorted_vals[lo] * (1.0 - w) + sorted_vals[hi] * w


def _crit_multiplier(rng: random.Random, crit_rate: float, crit_dmg: float) -> float:
    return crit_dmg if rng.random() < crit_rate else 1.0


# ----------------------------
# Core simulation (one trial)
# ----------------------------
def _simulate_one_trial(ticks: int, rng: random.Random, cfg: HayleyConfig) -> Tuple[float, Dict[str, float], Dict[str, int]]:
    """
    returns:
      total_damage,
      breakdown_damage: {basic, skill1, skill2, ult},
      casts: {basic, skill1, skill2, ult}
    """
    # precompute probabilities
    p1 = _clamp01(cfg.skill1_rate_pct / 100.0)
    p2 = _clamp01(cfg.skill2_rate_pct / 100.0)
    if p1 + p2 > 1.0 + 1e-12:
        raise ValueError(f"skill1_rate + skill2_rate が 100% を超えています: {cfg.skill1_rate_pct}+{cfg.skill2_rate_pct}")

    crit_rate = _clamp01(cfg.crit_rate_pct / 100.0)

    # ult buff ticks (rounded as requested)
    buff_ticks_total = int(round(cfg.ult_buff_ticks_base * cfg.attack_speed))
    if buff_ticks_total < 0:
        buff_ticks_total = 0

    mana: float = 0.0
    buff_ticks_left: int = 0  # >0 means buff active (including current tick if set before action)

    total = 0.0
    dmg = {"basic": 0.0, "skill1": 0.0, "skill2": 0.0, "ult": 0.0}
    casts = {"basic": 0, "skill1": 0, "skill2": 0, "ult": 0}

    atk_speed = cfg.attack_speed
    if atk_speed <= 0:
        raise ValueError("attack_speed は正の値である必要があります")

    # mana regen base per tick (before mana_buff)
    base_regen = 1.0 / atk_speed

    for _t in range(ticks):
        buff_active = (buff_ticks_left > 0)

        # ---- decide action at tick start
        # ult check only when NOT already in buff
        if (not buff_active) and (mana + 1e-12 >= cfg.ult_mana):
            action = "ult"
            casts["ult"] += 1

            # buff starts immediately and includes this tick
            if buff_ticks_total > 0:
                buff_ticks_left = buff_ticks_total
                buff_active = True
            else:
                buff_ticks_left = 0
                buff_active = False

            # ult damage: use buffed attack power if buff includes activation tick
            ap = cfg.attack_power_ult if buff_active else cfg.attack_power
            # 仕様ミス0倍が正しそう
            mult = 0.0  # ult multiplier is not provided in spec
            c = _crit_multiplier(rng, crit_rate, cfg.crit_dmg)
            dealt = ap * mult * c

            total += dealt
            dmg["ult"] += dealt

            # mana does not recover during buff; and spec says mana becomes 0 when buff ends.
            # (We also keep mana as-is here; it will be forced to 0 at buff end.)
            # If you prefer "ult consumes mana immediately", set mana=0 here.
            # mana = 0.0

        else:
            # normal action selection
            r = rng.random()
            if r < p1:
                action = "skill1"
                casts["skill1"] += 1
            elif r < p1 + p2:
                action = "skill2"
                casts["skill2"] += 1
            else:
                action = "basic"
                casts["basic"] += 1

            # damage calculation
            ap = cfg.attack_power_ult if buff_active else cfg.attack_power
            if action == "basic":
                mult = 1.0
            elif action == "skill1":
                mult = cfg.skill1_mult * (cfg.ult_buff_mult if buff_active else 1.0)
            else:  # skill2
                mult = cfg.skill2_mult * (cfg.ult_buff_mult if buff_active else 1.0)

            c = _crit_multiplier(rng, crit_rate, cfg.crit_dmg)
            dealt = ap * mult * c

            total += dealt
            dmg[action] += dealt

        # ---- tick end: mana recovery / buff decrement
        if buff_active:
            # no mana recovery during buff
            # decrement buff and end check
            if buff_ticks_left > 0:
                buff_ticks_left -= 1
                if buff_ticks_left == 0:
                    mana = 0.0  # buff end -> mana reset to 0
        else:
            # mana recovery applies
            # all mana recovery is multiplied by mana_buff
            gain = base_regen
            if action == "basic":
                gain += 1.0
            gain *= cfg.mana_buff
            mana += gain

    return total, dmg, casts


# ----------------------------
# Aggregation
# ----------------------------
def run_simulation(ticks: int, trials: int, seed: int, cfg: HayleyConfig) -> Dict:
    if ticks <= 0:
        raise ValueError("ticks は正の整数である必要があります")
    if trials <= 0:
        raise ValueError("trials は正の整数である必要があります")

    rng = random.Random(seed)

    totals: List[float] = []
    sum_breakdown = {"basic": 0.0, "skill1": 0.0, "skill2": 0.0, "ult": 0.0}
    sum_casts = {"basic": 0, "skill1": 0, "skill2": 0, "ult": 0}

    for _ in range(trials):
        t_total, t_dmg, t_casts = _simulate_one_trial(ticks, rng, cfg)
        totals.append(t_total)
        for k in sum_breakdown:
            sum_breakdown[k] += t_dmg[k]
        for k in sum_casts:
            sum_casts[k] += t_casts[k]

    mean_total = sum(totals) / trials
    mean_dps = mean_total / (ticks * cfg.tick_seconds)

    # 95% CI for mean(total)
    if trials >= 2:
        var = sum((x - mean_total) ** 2 for x in totals) / (trials - 1)
        sd = math.sqrt(var)
        se = sd / math.sqrt(trials)
        ci95_pm = 1.96 * se
    else:
        ci95_pm = 0.0

    totals_sorted = sorted(totals)
    percentiles = {
        "p05": _percentile(totals_sorted, 5.0),
        "p50": _percentile(totals_sorted, 50.0),
        "p95": _percentile(totals_sorted, 95.0),
    }

    mean_breakdown_total = {k: (sum_breakdown[k] / trials) for k in sum_breakdown}
    mean_casts = {k: (sum_casts[k] / trials) for k in sum_casts}

    return {
        "mean_total_damage": mean_total,
        "mean_dps": mean_dps,
        "ci95_total_pm": ci95_pm,
        "percentiles_total": percentiles,
        "mean_breakdown_total": mean_breakdown_total,
        "mean_casts": mean_casts,
    }


# ----------------------------
# External function requested
# ----------------------------
def mean_total_damage_5021(
    *,
    ticks: int,
    trials: int,
    seed: int,
    skill1_rate: float,
    skill2_rate: float,
    attack_speed: float,
    attack_power: float,
    skill1_mult: float,
    skill2_mult: float,
    crit_rate: float,
    crit_dmg: float,
    attack_power_ult: float,
    ult_mana: float,
    mana_buff: float = 1.0,
    tick_seconds: float = 1.0,
) -> float:
    """
    外部から「平均総ダメージ」だけ参照するための関数。
    """
    cfg = HayleyConfig(
        attack_speed=attack_speed,
        attack_power=attack_power,
        attack_power_ult=attack_power_ult,
        skill1_rate_pct=skill1_rate,
        skill2_rate_pct=skill2_rate,
        skill1_mult=skill1_mult,
        skill2_mult=skill2_mult,
        ult_mana=ult_mana,
        mana_buff=mana_buff,
        crit_rate_pct=crit_rate,
        crit_dmg=crit_dmg,
        tick_seconds=tick_seconds,
    )
    result = run_simulation(ticks=ticks, trials=trials, seed=seed, cfg=cfg)
    return float(result["mean_total_damage"])


# ----------------------------
# CLI
# ----------------------------
def _build_argparser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Hayley (5021) Monte Carlo DPS Simulator")

    p.add_argument("--ticks", type=int, required=True)
    p.add_argument("--trials", type=int, required=True)
    p.add_argument("--seed", type=int, default=1)

    p.add_argument("--attack-speed", type=float, required=True)
    p.add_argument("--attack-power", type=float, required=True)
    p.add_argument("--attack-power-ult", type=float, required=True)

    p.add_argument("--skill1-rate", type=float, required=True, help="0..100 (%)")
    p.add_argument("--skill2-rate", type=float, required=True, help="0..100 (%)")
    p.add_argument("--skill1-mult", type=float, required=True, help="倍率 (2 => 2x, 150 => 150x)")
    p.add_argument("--skill2-mult", type=float, required=True)

    p.add_argument("--ult-mana", type=float, required=True)
    p.add_argument("--mana-buff", type=float, default=1.0)

    p.add_argument("--crit-rate", type=float, required=True, help="0..100 (%)")
    p.add_argument("--crit-dmg", type=float, required=True)

    p.add_argument("--tick-seconds", type=float, default=1.0)

    return p


def main() -> None:
    args = _build_argparser().parse_args()

    cfg = HayleyConfig(
        attack_speed=args.attack_speed,
        attack_power=args.attack_power,
        attack_power_ult=args.attack_power_ult,
        skill1_rate_pct=args.skill1_rate,
        skill2_rate_pct=args.skill2_rate,
        skill1_mult=args.skill1_mult,
        skill2_mult=args.skill2_mult,
        ult_mana=args.ult_mana,
        mana_buff=args.mana_buff,
        crit_rate_pct=args.crit_rate,
        crit_dmg=args.crit_dmg,
        tick_seconds=args.tick_seconds,
    )

    res = run_simulation(ticks=args.ticks, trials=args.trials, seed=args.seed, cfg=cfg)

    print("=== Hayley (5021) Damage Simulation ===")
    print(f"ticks             : {args.ticks}")
    print(f"trials            : {args.trials}")
    print(f"tick_seconds      : {cfg.tick_seconds}")
    print(f"seed              : {args.seed}")
    print("--- params ---")
    print(f"attack_speed      : {cfg.attack_speed}")
    print(f"attack_power      : {cfg.attack_power}")
    print(f"attack_power_ult  : {cfg.attack_power_ult}")
    print(f"skill1_rate(%)    : {cfg.skill1_rate_pct}")
    print(f"skill2_rate(%)    : {cfg.skill2_rate_pct}")
    print(f"skill1_mult       : {cfg.skill1_mult}")
    print(f"skill2_mult       : {cfg.skill2_mult}")
    print(f"ult_mana          : {cfg.ult_mana}")
    print(f"mana_buff         : {cfg.mana_buff}")
    print(f"crit_rate(%)      : {cfg.crit_rate_pct}")
    print(f"crit_dmg          : {cfg.crit_dmg}")

    print("--- results ---")
    print(f"mean_total_damage : {res['mean_total_damage']:.6f}")
    print(f"mean_DPS          : {res['mean_dps']:.6f}")
    print(f"95% CI (total)    : ±{res['ci95_total_pm']:.6f}")
    p = res["percentiles_total"]
    print(f"percentiles total : p05={p['p05']:.6f}, p50={p['p50']:.6f}, p95={p['p95']:.6f}")

    b = res["mean_breakdown_total"]
    c = res["mean_casts"]
    print("--- mean breakdown (total damage per trial) ---")
    print(f" basic : {b['basic']:.6f}  (casts={c['basic']:.3f})")
    print(f" skill1: {b['skill1']:.6f}  (casts={c['skill1']:.3f})")
    print(f" skill2: {b['skill2']:.6f}  (casts={c['skill2']:.3f})")
    print(f" ult   : {b['ult']:.6f}  (casts={c['ult']:.3f})")


if __name__ == "__main__":
    main()

