from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any, Optional, Tuple
import argparse
import random


# ===== 固定仕様（チャージショット発動時の計測延長 tick）=====
# 10 - 10/1.15 ≒ 1.304347826...
DEFAULT_CHARGE_EXTEND_TICKS = 10.0 - 10.0 / 1.15


@dataclass
class CaptainRokaParams15023:
    attack_power: float
    attack_speed: float

    # rates are 0..100 (%)
    skill1_rate: float

    # multipliers
    skill1_mult: float
    skill2_mult: float
    skill3_mult: float
    ult_mult: float

    # crit
    crit_rate: float   # 0..100 (%)
    crit_dmg: float    # multiplier

    # ult
    ult_mana: float

    # extension per charge shot
    charge_extend_ticks: float = DEFAULT_CHARGE_EXTEND_TICKS


def _validate_params(p: CaptainRokaParams15023) -> None:
    if p.attack_speed <= 0:
        raise ValueError("attack_speed must be > 0")
    for name, r in [("skill1_rate", p.skill1_rate), ("crit_rate", p.crit_rate)]:
        if not (0.0 <= r <= 100.0):
            raise ValueError(f"{name} must be in [0, 100]")
    for name, m in [
        ("skill1_mult", p.skill1_mult),
        ("skill2_mult", p.skill2_mult),
        ("skill3_mult", p.skill3_mult),
        ("ult_mult", p.ult_mult),
        ("crit_dmg", p.crit_dmg),
    ]:
        if m < 0:
            raise ValueError(f"{name} must be >= 0")
    if p.ult_mana < 0:
        raise ValueError("ult_mana must be >= 0")
    if p.charge_extend_ticks < 0:
        raise ValueError("charge_extend_ticks must be >= 0")


def _roll_crit(rng: random.Random, crit_rate_pct: float, crit_dmg: float) -> float:
    """Return multiplier (1 or crit_dmg)."""
    return crit_dmg if (rng.random() < crit_rate_pct / 100.0) else 1.0


def _simulate_one_trial_core_15023(
    p: CaptainRokaParams15023,
    base_ticks: int,
    rng: random.Random,
) -> Tuple[float, Dict[str, float], Dict[str, int], int]:
    """Core simulator returning (total_damage, dmg_breakdown, action_counts, simulated_ticks)."""
    _validate_params(p)
    if base_ticks < 0:
        raise ValueError("base_ticks must be >= 0")

    mana = 0.0
    basic_stack = 0
    burst_count = 0

    end_time = float(base_ticks)
    t = 0

    dmg_br: Dict[str, float] = {"basic": 0.0, "skill1": 0.0, "skill2": 0.0, "skill3": 0.0, "ult": 0.0}
    counts: Dict[str, int] = {"basic": 0, "skill1": 0, "skill2": 0, "skill3": 0, "ult": 0}

    while t < end_time:
        action = "basic"
        mult = 1.0

        if mana >= p.ult_mana and p.ult_mana > 0:
            action = "ult"
            mult = p.ult_mult
            mana = 0.0
        else:
            if burst_count >= 3:
                action = "skill3"
                mult = p.skill3_mult
                burst_count -= 3
                end_time += p.charge_extend_ticks
            elif basic_stack >= 5:
                action = "skill2"
                mult = p.skill2_mult
                basic_stack -= 5
                burst_count += 1
            else:
                if rng.random() < p.skill1_rate / 100.0:
                    action = "skill1"
                    mult = p.skill1_mult
                else:
                    action = "basic"
                    mult = 1.0
                    basic_stack += 1

        dealt = p.attack_power * mult
        dealt *= _roll_crit(rng, p.crit_rate, p.crit_dmg)

        dmg_br[action] += dealt
        counts[action] += 1

        mana += 1.0 / p.attack_speed
        t += 1

    total_damage = sum(dmg_br.values())
    return total_damage, dmg_br, counts, t

def simulate_one_trial_15023(
    p: CaptainRokaParams15023,
    base_ticks: int,
    rng: random.Random,
) -> Tuple[float, Dict[str, int], int]:
    """
    1試行分の総ダメージを返す（従来互換ラッパ）。
    戻り値: (total_damage, action_counts, simulated_ticks)
    """
    total, _br, counts, t = _simulate_one_trial_core_15023(p, base_ticks, rng)
    return total, counts, t


def mean_total_damage_15023(options: Dict[str, Any]) -> Tuple[float, float, float, float, float]:
    """
    外部から「平均総ダメージ」だけ取りたい用。

    options例:
      {
        "attack_power": 100000,
        "attack_speed": 1.5,
        "skill1_rate": 20,
        "skill1_mult": 2,
        "skill2_mult": 3,
        "skill3_mult": 5,
        "ult_mult": 10,
        "ult_mana": 190,
        "crit_rate": 20,
        "crit_dmg": 2.5,
        "ticks": 100,      # base ticks
        "trials": 10000,
        "seed": 1
      }
    """
    ticks = options.get("ticks", None)
    if ticks is None:
        # 互換のため。durationSec を tick と同一視（曖昧点として後述）
        duration_sec = options.get("durationSec", None)
        if duration_sec is None:
            raise KeyError("options must include 'ticks' (or 'durationSec')")
        ticks = int(round(float(duration_sec)))

    p = CaptainRokaParams15023(
        attack_power=float(options["attack_power"]),
        attack_speed=float(options["attack_speed"]),
        skill1_rate=float(options["skill1_rate"]),
        skill1_mult=float(options["skill1_mult"]),
        skill2_mult=float(options["skill2_mult"]),
        skill3_mult=float(options["skill3_mult"]),
        ult_mult=float(options["ult_mult"]),
        ult_mana=float(options["ult_mana"]),
        crit_rate=float(options["crit_rate"]),
        crit_dmg=float(options["crit_dmg"]),
        charge_extend_ticks=float(options.get("charge_extend_ticks", DEFAULT_CHARGE_EXTEND_TICKS)),
    )

    trials = int(options.get("trials", 10000))
    seed = options.get("seed", None)

    if trials <= 0:
        raise ValueError("trials must be > 0")

    rng = random.Random(seed)

    sum_basic = sum_skill1 = sum_skill2 = sum_skill3 = sum_ult = 0.0
    for _ in range(trials):
        _total, br, _counts, _t = _simulate_one_trial_core_15023(p, int(ticks), rng)
        sum_basic += br['basic']
        sum_skill1 += br['skill1']
        sum_skill2 += br['skill2']
        sum_skill3 += br['skill3']
        sum_ult += br['ult']

    return (sum_basic / trials, sum_skill1 / trials, sum_skill2 / trials, sum_skill3 / trials, sum_ult / trials)


def main() -> None:
    ap = argparse.ArgumentParser(description="Captain Roka (15023) Monte Carlo total damage / DPT tool")
    ap.add_argument("--attack_power", type=float, required=True)
    ap.add_argument("--attack_speed", type=float, required=True)

    ap.add_argument("--skill1_rate", type=float, required=True)
    ap.add_argument("--skill1_mult", type=float, required=True)
    ap.add_argument("--skill2_mult", type=float, required=True)
    ap.add_argument("--skill3_mult", type=float, required=True)
    ap.add_argument("--ult_mult", type=float, required=True)

    ap.add_argument("--ult_mana", type=float, required=True)

    ap.add_argument("--crit_rate", type=float, required=True)
    ap.add_argument("--crit_dmg", type=float, required=True)

    ap.add_argument("--ticks", type=int, required=True, help="base ticks (charge shot extends this internally)")
    ap.add_argument("--trials", type=int, default=10000)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--charge_extend_ticks", type=float, default=DEFAULT_CHARGE_EXTEND_TICKS)

    args = ap.parse_args()

    p = CaptainRokaParams15023(
        attack_power=args.attack_power,
        attack_speed=args.attack_speed,
        skill1_rate=args.skill1_rate,
        skill1_mult=args.skill1_mult,
        skill2_mult=args.skill2_mult,
        skill3_mult=args.skill3_mult,
        ult_mult=args.ult_mult,
        ult_mana=args.ult_mana,
        crit_rate=args.crit_rate,
        crit_dmg=args.crit_dmg,
        charge_extend_ticks=args.charge_extend_ticks,
    )
    _validate_params(p)

    rng = random.Random(args.seed)

    sum_dmg = 0.0
    sum_ticks = 0
    sum_counts = {"basic": 0, "skill1": 0, "skill2": 0, "skill3": 0, "ult": 0}

    for _ in range(args.trials):
        dmg, counts, sim_ticks = simulate_one_trial_15023(p, args.ticks, rng)
        sum_dmg += dmg
        sum_ticks += sim_ticks
        for k in sum_counts:
            sum_counts[k] += counts.get(k, 0)

    mean_dmg = sum_dmg / args.trials
    mean_ticks = sum_ticks / args.trials
    dpt = mean_dmg / mean_ticks if mean_ticks > 0 else 0.0

    print("=== Captain Roka 15023 Monte Carlo Result ===")
    print(f"trials          : {args.trials}")
    print(f"base ticks      : {args.ticks}")
    print(f"mean sim ticks  : {mean_ticks:.6f} (charge extension included)")
    print(f"mean total dmg  : {mean_dmg:.6f}")
    print(f"damage per tick : {dpt:.6f}  (※1tick=1秒ならこれがDPS)")
    print("--- mean action counts (per trial) ---")
    for k in ["basic", "skill1", "skill2", "skill3", "ult"]:
        print(f"{k:6s}: {sum_counts[k] / args.trials:.6f}")


if __name__ == "__main__":
    main()

