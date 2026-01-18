#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Awakened Hayley DPS simulator (Monte Carlo, tick-based)

Internal names:
  basic  : basic attack
  skill1 : 太陽の光線
  skill2 : 太古の爆発 (energy injection + delayed / triple instant explosion)
  ult    : フレア (channeling, no mana gain, no basic)

Assumptions / details are written at bottom in __main__ output and in notes.
"""

from __future__ import annotations

from dataclasses import dataclass
import argparse
import math
import random
from typing import Dict, List, Tuple


@dataclass(frozen=True)
class Params:
    # rates are given in percent (0..100)
    skill1_rate: float
    skill2_rate: float
    crit_rate: float  # percent
    # multipliers are given as plain multipliers (2 => 2x, 150 => 150x)
    crit_dmg: float
    skill1_mult: float
    skill2_mult: float
    skill3_mult: float
    # core stats
    attack_power: float
    attack_speed: float
    # mana system
    ult_mana: float
    mana_buff: float
    # time scaling
    tick_seconds: float = 1.0
    # how to apply crit to ult damage:
    #  - "per_tick": each tick of ult can crit independently (more variance)
    #  - "once"    : treat ult as one damage action and crit once on total
    ult_crit_mode: str = "per_tick"


def _validate(p: Params) -> None:
    if p.attack_speed <= 0:
        raise ValueError("attack_speed must be > 0")
    for name, v in [
        ("skill1_rate", p.skill1_rate),
        ("skill2_rate", p.skill2_rate),
        ("crit_rate", p.crit_rate),
    ]:
        if not (0 <= v <= 100):
            raise ValueError(f"{name} must be in [0, 100], got {v}")

    if p.skill1_rate + p.skill2_rate > 100 + 1e-9:
        raise ValueError("skill1_rate + skill2_rate must be <= 100")

    if p.crit_dmg < 1:
        raise ValueError("crit_dmg must be >= 1")
    if p.mana_buff <= 0:
        raise ValueError("mana_buff must be > 0")
    if p.tick_seconds <= 0:
        raise ValueError("tick_seconds must be > 0")
    if p.ult_crit_mode not in ("per_tick", "once"):
        raise ValueError("ult_crit_mode must be 'per_tick' or 'once'")


def _apply_crit(rng_random, dmg: float, crit_rate_pct: float, crit_dmg: float) -> float:
    # crit_rate is percent (0..100)
    if dmg <= 0:
        return 0.0
    if rng_random() < (crit_rate_pct / 100.0):
        return dmg * crit_dmg
    return dmg


def simulate_once(ticks: int, p: Params, rng: random.Random) -> Tuple[float, Dict[str, float]]:
    """
    Returns:
      total_damage,
      breakdown_damage (keys: basic, skill1, skill2, ult)
    """
    _validate(p)
    if ticks <= 0:
        return 0.0, {"basic": 0.0, "skill1": 0.0, "skill2": 0.0, "ult": 0.0}

    r = rng.random  # local bind for speed

    # tick-derived integers (rounded by round() as requested)
    skill2_delay = int(round(10.0 * p.attack_speed))
    ult_channel_ticks = int(round(10.0 * p.attack_speed)) + 1  # include activation tick

    # damage per action (base, before crit)
    dmg_basic = p.attack_power * 1.0
    dmg_skill1 = p.attack_power * p.skill1_mult
    dmg_skill2_single = p.attack_power * p.skill2_mult
    dmg_skill2_triple_each = p.attack_power * (p.skill2_mult * 2.0)  # per injected energy when triple
    dmg_ult_total = p.attack_power * p.skill3_mult

    # mana gains (before buff)
    mana_tick = (1.0 / p.attack_speed) * p.mana_buff
    mana_basic_bonus = 1.0 * p.mana_buff  # only when basic happens

    # state
    mana = 0.0
    ult_remaining = 0  # if >0, we are in ult channel
    skill2_energies_expiry: List[int] = []  # list of expiry ticks, max 2 in steady state

    total = 0.0
    breakdown = {"basic": 0.0, "skill1": 0.0, "skill2": 0.0, "ult": 0.0}

    # If ult crit mode is "once", decide crit at ult start and store multiplier
    ult_once_multiplier = 1.0  # only used in "once"

    for t in range(ticks):
        # 1) process delayed skill2 explosions scheduled for this tick
        if skill2_energies_expiry:
            remain: List[int] = []
            for exp in skill2_energies_expiry:
                if exp <= t:
                    # single energy explodes now
                    d = _apply_crit(r, dmg_skill2_single, p.crit_rate, p.crit_dmg)
                    total += d
                    breakdown["skill2"] += d
                else:
                    remain.append(exp)
            skill2_energies_expiry = remain

        # 2) if currently channeling ult
        if ult_remaining > 0:
            if p.ult_crit_mode == "per_tick":
                per_tick = dmg_ult_total / float(ult_channel_ticks)
                d = _apply_crit(r, per_tick, p.crit_rate, p.crit_dmg)
                total += d
                breakdown["ult"] += d
            else:
                # "once": distribute already-crit total over ticks
                per_tick = (dmg_ult_total * ult_once_multiplier) / float(ult_channel_ticks)
                total += per_tick
                breakdown["ult"] += per_tick

            ult_remaining -= 1
            if ult_remaining == 0:
                # after ult ends, mana is 0 and we return to basic state
                mana = 0.0
            continue  # no mana gain during ult

        # 3) not in ult: check ult availability (at tick start)
        if mana >= p.ult_mana:
            # enter ult this tick
            mana = 0.0
            ult_remaining = ult_channel_ticks

            if p.ult_crit_mode == "once":
                # decide crit once for the whole ult
                if r() < (p.crit_rate / 100.0):
                    ult_once_multiplier = p.crit_dmg
                else:
                    ult_once_multiplier = 1.0

            # deal first tick of ult damage immediately (same tick)
            if p.ult_crit_mode == "per_tick":
                per_tick = dmg_ult_total / float(ult_channel_ticks)
                d = _apply_crit(r, per_tick, p.crit_rate, p.crit_dmg)
                total += d
                breakdown["ult"] += d
            else:
                per_tick = (dmg_ult_total * ult_once_multiplier) / float(ult_channel_ticks)
                total += per_tick
                breakdown["ult"] += per_tick

            ult_remaining -= 1
            # no mana gain on this tick
            if ult_remaining == 0:
                mana = 0.0
            continue

        # 4) choose action for this tick (skill1 / skill2 / basic)
        u = r() * 100.0
        did_basic = False

        if u < p.skill1_rate:
            # skill1: immediate damage
            d = _apply_crit(r, dmg_skill1, p.crit_rate, p.crit_dmg)
            total += d
            breakdown["skill1"] += d

            # end-of-tick mana gain (tick-only)
            mana += mana_tick

        elif u < (p.skill1_rate + p.skill2_rate):
            # skill2: inject energy
            expiry = t + skill2_delay
            skill2_energies_expiry.append(expiry)

            # if 3 energies within window, instant explosion now
            if len(skill2_energies_expiry) >= 3:
                # instant: 3 energies explode, each damage is skill2_mult*2
                for _ in range(3):
                    d = _apply_crit(r, dmg_skill2_triple_each, p.crit_rate, p.crit_dmg)
                    total += d
                    breakdown["skill2"] += d
                skill2_energies_expiry.clear()

            # end-of-tick mana gain (tick-only)
            mana += mana_tick

        else:
            # basic: immediate damage
            d = _apply_crit(r, dmg_basic, p.crit_rate, p.crit_dmg)
            total += d
            breakdown["basic"] += d
            did_basic = True

            # end-of-tick mana gain (tick + basic bonus)
            mana += mana_tick
            if did_basic:
                mana += mana_basic_bonus

    return total, breakdown


def simulate(
    ticks: int,
    trials: int,
    p: Params,
    seed: int = 0,
) -> Dict[str, object]:
    """
    Returns dict including:
      mean_total_damage, mean_dps, ci95_total, percentiles_total, mean_breakdown
    """
    _validate(p)
    if trials <= 0:
        raise ValueError("trials must be > 0")

    rng = random.Random(seed)

    totals: List[float] = []
    breakdown_sum = {"basic": 0.0, "skill1": 0.0, "skill2": 0.0, "ult": 0.0}

    for _ in range(trials):
        total, br = simulate_once(ticks, p, rng)
        totals.append(total)
        for k in breakdown_sum:
            breakdown_sum[k] += br.get(k, 0.0)

    # stats
    mean_total = sum(totals) / trials

    # sample std
    if trials >= 2:
        var = sum((x - mean_total) ** 2 for x in totals) / (trials - 1)
        sd = math.sqrt(var)
        se = sd / math.sqrt(trials)
        ci95 = 1.96 * se
    else:
        ci95 = 0.0

    totals_sorted = sorted(totals)

    def percentile(pct: float) -> float:
        # pct: 0..100
        if not totals_sorted:
            return 0.0
        if pct <= 0:
            return totals_sorted[0]
        if pct >= 100:
            return totals_sorted[-1]
        pos = (len(totals_sorted) - 1) * (pct / 100.0)
        lo = int(math.floor(pos))
        hi = int(math.ceil(pos))
        if lo == hi:
            return totals_sorted[lo]
        frac = pos - lo
        return totals_sorted[lo] * (1 - frac) + totals_sorted[hi] * frac

    duration_sec = ticks * p.tick_seconds
    mean_dps = mean_total / duration_sec if duration_sec > 0 else 0.0

    mean_breakdown = {k: v / trials for k, v in breakdown_sum.items()}

    return {
        "ticks": ticks,
        "trials": trials,
        "seed": seed,
        "tick_seconds": p.tick_seconds,
        "mean_total_damage": mean_total,
        "mean_DPS": mean_dps,
        "ci95_total": ci95,
        "percentiles_total": {
            "p05": percentile(5),
            "p50": percentile(50),
            "p95": percentile(95),
        },
        "mean_breakdown": mean_breakdown,
    }


def mean_total_damage_15021(
    ticks: int,
    trials: int,
    seed: int,
    *,
    skill1_rate: float,
    skill2_rate: float,
    attack_speed: float,
    attack_power: float,
    skill1_mult: float,
    skill2_mult: float,
    skill3_mult: float,
    ult_mana: float,
    mana_buff: float,
    crit_rate: float,
    crit_dmg: float,
    tick_seconds: float = 1.0,
    ult_crit_mode: str = "per_tick",
) -> float:
    """
    External-call friendly function: returns mean_total_damage only.
    """
    p = Params(
        skill1_rate=skill1_rate,
        skill2_rate=skill2_rate,
        crit_rate=crit_rate,
        crit_dmg=crit_dmg,
        skill1_mult=skill1_mult,
        skill2_mult=skill2_mult,
        skill3_mult=skill3_mult,
        attack_power=attack_power,
        attack_speed=attack_speed,
        ult_mana=ult_mana,
        mana_buff=mana_buff,
        tick_seconds=tick_seconds,
        ult_crit_mode=ult_crit_mode,
    )
    res = simulate(ticks=ticks, trials=trials, p=p, seed=seed)
    return float(res["mean_total_damage"])


def _build_argparser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="Awakened Hayley DPS Monte Carlo Simulator (tick-based)")
    ap.add_argument("--ticks", type=int, required=True, help="simulation ticks")
    ap.add_argument("--trials", type=int, default=1000, help="number of Monte Carlo trials")
    ap.add_argument("--seed", type=int, default=0, help="RNG seed")

    ap.add_argument("--attack-power", type=float, required=True)
    ap.add_argument("--attack-speed", type=float, required=True)

    ap.add_argument("--skill1-rate", type=float, required=True, help="percent 0..100")
    ap.add_argument("--skill2-rate", type=float, required=True, help="percent 0..100")

    ap.add_argument("--skill1-mult", type=float, required=True)
    ap.add_argument("--skill2-mult", type=float, required=True)
    ap.add_argument("--skill3-mult", type=float, required=True)

    ap.add_argument("--ult-mana", type=float, required=True)
    ap.add_argument("--mana-buff", type=float, default=1.0)

    ap.add_argument("--crit-rate", type=float, required=True, help="percent 0..100")
    ap.add_argument("--crit-dmg", type=float, required=True, help="multiplier")

    ap.add_argument("--tick-seconds", type=float, default=1.0, help="seconds per tick (default 1.0)")
    ap.add_argument(
        "--ult-crit-mode",
        choices=["per_tick", "once"],
        default="per_tick",
        help="crit application for ult damage: per_tick or once",
    )
    return ap


def main() -> None:
    args = _build_argparser().parse_args()

    p = Params(
        skill1_rate=args.skill1_rate,
        skill2_rate=args.skill2_rate,
        crit_rate=args.crit_rate,
        crit_dmg=args.crit_dmg,
        skill1_mult=args.skill1_mult,
        skill2_mult=args.skill2_mult,
        skill3_mult=args.skill3_mult,
        attack_power=args.attack_power,
        attack_speed=args.attack_speed,
        ult_mana=args.ult_mana,
        mana_buff=args.mana_buff,
        tick_seconds=args.tick_seconds,
        ult_crit_mode=args.ult_crit_mode,
    )

    res = simulate(ticks=args.ticks, trials=args.trials, p=p, seed=args.seed)

    print("=== Awakened Hayley Damage Simulation ===")
    print(f"ticks             : {res['ticks']}")
    print(f"trials            : {res['trials']}")
    print(f"tick_seconds      : {res['tick_seconds']}")
    print(f"seed              : {res['seed']}")
    print("--- params ---")
    print(f"attack_power      : {args.attack_power}")
    print(f"attack_speed      : {args.attack_speed}")
    print(f"ult_mana          : {args.ult_mana}")
    print(f"mana_buff         : {args.mana_buff}")
    print(f"skill1_rate       : {args.skill1_rate}%")
    print(f"skill2_rate       : {args.skill2_rate}%")
    print(f"skill1_mult       : {args.skill1_mult}")
    print(f"skill2_mult       : {args.skill2_mult}")
    print(f"skill3_mult       : {args.skill3_mult}")
    print(f"crit_rate         : {args.crit_rate}%")
    print(f"crit_dmg          : {args.crit_dmg}")
    print(f"ult_crit_mode     : {args.ult_crit_mode}")

    print("--- results ---")
    print(f"mean_total_damage : {res['mean_total_damage']:.6f}")
    print(f"mean_DPS          : {res['mean_DPS']:.6f}")
    print(f"95% CI (total)    : ±{res['ci95_total']:.6f}")
    pct = res["percentiles_total"]
    print(f"percentiles total : p05={pct['p05']:.6f}, p50={pct['p50']:.6f}, p95={pct['p95']:.6f}")

    br = res["mean_breakdown"]
    print("--- mean breakdown (total damage per trial) ---")
    print(f" basic : {br['basic']:.6f}")
    print(f" skill1: {br['skill1']:.6f}")
    print(f" skill2: {br['skill2']:.6f}")
    print(f" ult   : {br['ult']:.6f}")

    print()
    print("Notes:")
    print(" - tick由来の時間(10*attack_speed等)は round() で整数tickに丸めています。")
    print(" - mana回復は各tickの最後。basicのみ +1 回復が追加され、mana_buff は全回復に乗算。")
    print(" - ult中は『基本攻撃不可・マナ回復不可』として実装。skill2の遅延爆発はult中でも進行/発生します。")


if __name__ == "__main__":
    main()

