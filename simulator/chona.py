# simulator/chona_5019.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any, Optional, Tuple
import argparse
import random
import statistics as stats
import math


# 内部定義
ACTION_BASIC = "basic"
ACTION_SKILL1 = "skill1"
ACTION_SKILL2 = "skill2"
ACTION_ULT = "ult"


@dataclass(frozen=True)
class ChonaParams5019:
    attack_power: float
    attack_speed: float
    skill1_rate: float   # 0..100 (%)
    skill1_mult: float   # x倍
    skill2_mult: float   # x倍
    ult_mult: float      # x倍
    ult_mana: float
    cirt_rate: float     # 0..100 (%)
    cirt_dmg: float      # x倍


def _clamp(x: float, lo: float, hi: float) -> float:
    return lo if x < lo else hi if x > hi else x


def ticks_from_duration(duration_sec: float, attack_speed: float) -> int:
    """
    durationSec から ticks を計算。
    指示通り小数になる場合は round() で丸める。
    """
    if attack_speed <= 0:
        raise ValueError("attack_speed must be > 0")
    # durationSec * attacks_per_sec で tick 数
    t = round(duration_sec * attack_speed)
    return int(max(0, t))


def duration_from_ticks(ticks: int, attack_speed: float) -> float:
    """
    ticks から durationSec を逆算。
    """
    if attack_speed <= 0:
        raise ValueError("attack_speed must be > 0")
    return float(ticks) / float(attack_speed)


def _roll_crit(rng: random.Random, cirt_rate: float) -> bool:
    return (rng.random() * 100.0) < cirt_rate


def _deal_damage(
    rng: random.Random,
    attack_power: float,
    mult: float,
    cirt_rate: float,
    cirt_dmg: float,
) -> Tuple[float, bool]:
    dmg = attack_power * mult
    is_crit = _roll_crit(rng, cirt_rate)
    if is_crit:
        dmg *= cirt_dmg
    return dmg, is_crit


def simulate_once(
    params: ChonaParams5019,
    ticks: int,
    rng: random.Random,
) -> Dict[str, Any]:
    """
    1 trial 分をシミュレートして総ダメージなどを返す。
    """
    # sanitize
    skill1_rate = _clamp(params.skill1_rate, 0.0, 100.0)
    cirt_rate = _clamp(params.cirt_rate, 0.0, 100.0)

    mana = 0.0
    basic_stack = 0

    total_damage = 0.0

    counts = {ACTION_BASIC: 0, ACTION_SKILL1: 0, ACTION_SKILL2: 0, ACTION_ULT: 0}
    crit_counts = {ACTION_BASIC: 0, ACTION_SKILL1: 0, ACTION_SKILL2: 0, ACTION_ULT: 0}
    dmg_sums = {ACTION_BASIC: 0.0, ACTION_SKILL1: 0.0, ACTION_SKILL2: 0.0, ACTION_ULT: 0.0}

    for _ in range(ticks):
        # === 行動選択（状態遷移） ===
        if mana >= params.ult_mana:
            action = ACTION_ULT
            mult = params.ult_mult
            # ult 発動後マナは 0
            mana = 0.0
        else:
            # stack 25 到達時は「植物のつる」
            if basic_stack >= 25:
                action = ACTION_SKILL2
                mult = params.skill2_mult
                basic_stack = 0
            else:
                r = rng.random() * 100.0
                if r < skill1_rate:
                    action = ACTION_SKILL1
                    mult = params.skill1_mult
                else:
                    action = ACTION_BASIC
                    mult = 1.0

        # === ダメージ ===
        dmg, is_crit = _deal_damage(
            rng=rng,
            attack_power=params.attack_power,
            mult=mult,
            cirt_rate=cirt_rate,
            cirt_dmg=params.cirt_dmg,
        )
        total_damage += dmg

        counts[action] += 1
        dmg_sums[action] += dmg
        if is_crit:
            crit_counts[action] += 1

        # === tick 終了時処理（マナ回復） ===
        # 指定: 基本攻撃なら (1/attack_speed) 回復、スキル発動なら回復なし
        if action == ACTION_BASIC:
            basic_stack += 1
            mana += 1.0 / params.attack_speed

    return {
        "total_damage": total_damage,
        "counts": counts,
        "crit_counts": crit_counts,
        "damage_by_action": dmg_sums,
    }


def run_monte_carlo(
    params: ChonaParams5019,
    ticks: int,
    trials: int,
    seed: Optional[int] = None,
) -> Dict[str, Any]:
    if trials <= 0:
        raise ValueError("trials must be > 0")
    if ticks < 0:
        raise ValueError("ticks must be >= 0")

    rng = random.Random(seed)

    totals = []
    agg_counts = {ACTION_BASIC: 0, ACTION_SKILL1: 0, ACTION_SKILL2: 0, ACTION_ULT: 0}
    agg_crit = {ACTION_BASIC: 0, ACTION_SKILL1: 0, ACTION_SKILL2: 0, ACTION_ULT: 0}
    agg_dmg = {ACTION_BASIC: 0.0, ACTION_SKILL1: 0.0, ACTION_SKILL2: 0.0, ACTION_ULT: 0.0}

    for _ in range(trials):
        out = simulate_once(params, ticks, rng)
        totals.append(float(out["total_damage"]))
        for k in agg_counts:
            agg_counts[k] += int(out["counts"][k])
            agg_crit[k] += int(out["crit_counts"][k])
            agg_dmg[k] += float(out["damage_by_action"][k])

    mean_total = stats.fmean(totals)
    sd = stats.pstdev(totals) if trials >= 2 else 0.0
    se = (sd / math.sqrt(trials)) if trials >= 2 else 0.0
    ci95 = 1.96 * se if trials >= 2 else 0.0

    duration_sec = duration_from_ticks(ticks, params.attack_speed) if params.attack_speed > 0 else 0.0
    mean_dps = (mean_total / duration_sec) if duration_sec > 0 else 0.0

    return {
        "meta": {
            "ticks": ticks,
            "durationSec": duration_sec,
            "trials": trials,
            "seed": seed,
        },
        "mean_total_damage": mean_total,
        "mean_dps": mean_dps,
        "stdev_total_damage": sd,
        "ci95_total_damage": (mean_total - ci95, mean_total + ci95),
        "avg_counts_per_trial": {k: agg_counts[k] / trials for k in agg_counts},
        "avg_damage_by_action_per_trial": {k: agg_dmg[k] / trials for k in agg_dmg},
        "avg_crit_counts_per_trial": {k: agg_crit[k] / trials for k in agg_crit},
    }


def mean_total_damage_5019(
    *,
    attack_power: float,
    attack_speed: float,
    skill1_rate: float,
    skill1_mult: float,
    skill2_mult: float,
    ult_mult: float,
    ult_mana: float,
    cirt_rate: float,
    cirt_dmg: float,
    durationSec: Optional[float] = 60.0,
    ticks: Optional[int] = None,
    trials: int = 10000,
    seed: Optional[int] = None,
) -> float:
    """
    外部から「平均総ダメージ」だけ取得するための関数。

    - ticks を指定した場合: その tick 数で計算
    - ticks が None の場合: durationSec * attack_speed を round() して ticks を計算
    """
    params = ChonaParams5019(
        attack_power=float(attack_power),
        attack_speed=float(attack_speed),
        skill1_rate=float(skill1_rate),
        skill1_mult=float(skill1_mult),
        skill2_mult=float(skill2_mult),
        ult_mult=float(ult_mult),
        ult_mana=float(ult_mana),
        cirt_rate=float(cirt_rate),
        cirt_dmg=float(cirt_dmg),
    )

    if ticks is None:
        if durationSec is None:
            raise ValueError("Either ticks or durationSec must be provided")
        ticks_i = ticks_from_duration(float(durationSec), params.attack_speed)
    else:
        ticks_i = int(ticks)

    result = run_monte_carlo(params=params, ticks=ticks_i, trials=int(trials), seed=seed)
    return float(result["mean_total_damage"])


def _build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Chona(5019) Monte Carlo DPS / total damage simulator")
    p.add_argument("--attack_power", type=float, required=True)
    p.add_argument("--attack_speed", type=float, required=True)

    p.add_argument("--skill1_rate", type=float, required=True)
    p.add_argument("--skill1_mult", type=float, required=True)
    p.add_argument("--skill2_mult", type=float, required=True)

    p.add_argument("--ult_mult", type=float, required=True)
    p.add_argument("--ult_mana", type=float, required=True)

    p.add_argument("--cirt_rate", type=float, required=True)
    p.add_argument("--cirt_dmg", type=float, required=True)

    g = p.add_mutually_exclusive_group(required=False)
    g.add_argument("--ticks", type=int, default=None, help="simulate exactly this many ticks")
    g.add_argument("--durationSec", type=float, default=60.0, help="simulate this duration in seconds")

    p.add_argument("--trials", type=int, default=10000)
    p.add_argument("--seed", type=int, default=None)

    return p


def main() -> None:
    args = _build_arg_parser().parse_args()

    params = ChonaParams5019(
        attack_power=args.attack_power,
        attack_speed=args.attack_speed,
        skill1_rate=args.skill1_rate,
        skill1_mult=args.skill1_mult,
        skill2_mult=args.skill2_mult,
        ult_mult=args.ult_mult,
        ult_mana=args.ult_mana,
        cirt_rate=args.cirt_rate,
        cirt_dmg=args.cirt_dmg,
    )

    if args.ticks is None:
        ticks = ticks_from_duration(args.durationSec, params.attack_speed)
    else:
        ticks = int(args.ticks)

    result = run_monte_carlo(params=params, ticks=ticks, trials=args.trials, seed=args.seed)

    # 見やすいテキスト出力
    meta = result["meta"]
    print("=== Chona(5019) Simulation Result ===")
    print(f"ticks        : {meta['ticks']}")
    print(f"durationSec  : {meta['durationSec']:.6f}")
    print(f"trials       : {meta['trials']}")
    print(f"seed         : {meta['seed']}")
    print("")
    print(f"mean_total_damage : {result['mean_total_damage']:.6f}")
    print(f"mean_dps          : {result['mean_dps']:.6f}")
    lo, hi = result["ci95_total_damage"]
    print(f"CI95(total_damage): [{lo:.6f}, {hi:.6f}]")
    print("")
    print("--- avg counts per trial ---")
    for k, v in result["avg_counts_per_trial"].items():
        print(f"{k:6s}: {v:.6f}")
    print("")
    print("--- avg damage by action per trial ---")
    for k, v in result["avg_damage_by_action_per_trial"].items():
        print(f"{k:6s}: {v:.6f}")
    print("")
    print("--- avg crit counts per trial ---")
    for k, v in result["avg_crit_counts_per_trial"].items():
        print(f"{k:6s}: {v:.6f}")


if __name__ == "__main__":
    main()

