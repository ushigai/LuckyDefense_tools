from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any, Optional, Tuple
import argparse
import random


# =========================
# Params
# =========================
@dataclass(frozen=True)
class ChonaParams5019:
    attack_power: float
    attack_speed: float

    # rate is 0..100 (%)
    skill1_rate: float

    # multiplier (2 -> 2x, 150 -> 150x)
    skill1_mult: float
    skill2_mult: float
    ult_mult: float

    ult_mana: float

    # crit rate is 0..100 (%)
    crit_rate: float

    # crit dmg multiplier (2.5 -> 2.5x)
    crit_dmg: float


# =========================
# Core simulation
# =========================
def _roll_percent(rng: random.Random, pct_0_100: float) -> bool:
    """Return True with pct_0_100% probability."""
    return (rng.random() * 100.0) < pct_0_100


def _simulate_one_trial(
    params: ChonaParams5019,
    ticks: int,
    rng: random.Random,
) -> Tuple[float, Dict[str, int]]:
    """
    1 trial 分をシミュレートして total_damage を返す。
    counts は action 回数の内訳。
    """
    mana = 0.0
    basic_stack = 0  # "基本攻撃を発動した回数" を数えるスタック

    total_damage = 0.0
    counts = {"basic": 0, "skill1": 0, "skill2": 0, "ult": 0}

    for _ in range(ticks):
        # ===== action decision (priority) =====
        # 1) ult if mana >= ult_mana
        # 2) skill2 if basic_stack >= 25
        # 3) skill1 by skill1_rate
        # 4) otherwise basic
        if mana >= params.ult_mana:
            action = "ult"
            mult = params.ult_mult
            mana = 0.0  # ult 発動後マナは0に戻る
            # stackは変化なし（基本攻撃ではないため）
        elif basic_stack >= 25:
            action = "skill2"
            mult = params.skill2_mult
            basic_stack = 0  # 植物のつる発動でスタック消費（0に戻す想定）
        else:
            if _roll_percent(rng, params.skill1_rate):
                action = "skill1"
                mult = params.skill1_mult
            else:
                action = "basic"
                mult = 1.0
                basic_stack += 1  # 基本攻撃を1回発動するたびにスタック+1

        # ===== damage =====
        dmg = params.attack_power * mult

        # crit
        if _roll_percent(rng, params.crit_rate):
            dmg *= params.crit_dmg

        total_damage += dmg
        counts[action] += 1

        # ===== end-of-tick mana recovery =====
        # 「各tickの最後に適用」：行動種別に関係なく回復する扱い
        mana += (1.0 / params.attack_speed)

    return total_damage, counts


def run_monte_carlo_5019(
    params: ChonaParams5019,
    ticks: int,
    trials: int,
    seed: Optional[int] = None,
) -> Dict[str, Any]:
    rng = random.Random(seed)

    total_sum = 0.0
    counts_sum = {"basic": 0, "skill1": 0, "skill2": 0, "ult": 0}

    for _ in range(trials):
        dmg, counts = _simulate_one_trial(params, ticks, rng)
        total_sum += dmg
        for k in counts_sum:
            counts_sum[k] += counts[k]

    mean_total = total_sum / float(trials)

    # 参考: tick→秒の変換を「1tick = 1/attack_speed 秒」と仮定すると…
    duration_sec_est = ticks / params.attack_speed
    mean_dps_est = mean_total / duration_sec_est if duration_sec_est > 0 else 0.0

    return {
        "mean_total_damage": mean_total,
        "ticks": ticks,
        "trials": trials,
        "mean_counts": {k: counts_sum[k] / float(trials) for k in counts_sum},
        "duration_sec_est": duration_sec_est,
        "mean_dps_est": mean_dps_est,
    }


# =========================
# External function requested
# =========================
def mean_total_damage_5019(options: Dict[str, Any]) -> float:
    """
    外部から「平均総ダメージ」だけ取りたい用。

    options例:
      {
        "attack_power": 100000,
        "attack_speed": 1.5,
        "skill1_rate": 20,
        "skill1_mult": 2.0,
        "skill2_mult": 5.0,
        "ult_mult": 10.0,
        "ult_mana": 190,
        "crit_rate": 20,
        "crit_dmg": 2.5,
        "ticks": 90,          # or "durationSec": 60
        "trials": 10000,
        "seed": 1
      }
    """
    params = ChonaParams5019(
        attack_power=float(options["attack_power"]),
        attack_speed=float(options["attack_speed"]),
        skill1_rate=float(options["skill1_rate"]),
        skill1_mult=float(options["skill1_mult"]),
        skill2_mult=float(options["skill2_mult"]),
        ult_mult=float(options["ult_mult"]),
        ult_mana=float(options["ult_mana"]),
        crit_rate=float(options["crit_rate"]),
        crit_dmg=float(options["crit_dmg"]),
    )

    trials = int(options.get("trials", 10000))
    seed = options.get("seed", None)

    # 任意tick数 or durationSec を許容
    if "ticks" in options and options["ticks"] is not None:
        ticks = int(options["ticks"])
    elif "durationSec" in options and options["durationSec"] is not None:
        duration_sec = float(options["durationSec"])
        # 指示通り round() で丸め込み
        ticks = int(round(duration_sec * params.attack_speed))
    else:
        raise ValueError("options must include either 'ticks' or 'durationSec'.")

    result = run_monte_carlo_5019(params=params, ticks=ticks, trials=trials, seed=seed)
    return float(result["mean_total_damage"])


# =========================
# CLI
# =========================
def main() -> None:
    ap = argparse.ArgumentParser(description="Chona(5019) Monte-Carlo total damage simulator")

    ap.add_argument("--attack_power", type=float, required=True)
    ap.add_argument("--attack_speed", type=float, required=True)

    ap.add_argument("--skill1_rate", type=float, required=True, help="0..100 (%)")
    ap.add_argument("--skill1_mult", type=float, required=True)
    ap.add_argument("--skill2_mult", type=float, required=True)
    ap.add_argument("--ult_mult", type=float, required=True)
    ap.add_argument("--ult_mana", type=float, required=True)

    ap.add_argument("--crit_rate", type=float, required=True, help="0..100 (%)")
    ap.add_argument("--crit_dmg", type=float, required=True)

    # ticks or durationSec
    ap.add_argument("--ticks", type=int, default=None, help="simulate this many ticks")
    ap.add_argument("--durationSec", type=float, default=None, help="simulate by seconds (ticks=round(durationSec*attack_speed))")

    ap.add_argument("--trials", type=int, default=10000)
    ap.add_argument("--seed", type=int, default=None)

    args = ap.parse_args()

    if args.skill1_rate < 0 or args.skill1_rate > 100:
        raise ValueError("skill1_rate must be 0..100")
    if args.crit_rate < 0 or args.crit_rate > 100:
        raise ValueError("crit_rate must be 0..100")
    if args.attack_speed <= 0:
        raise ValueError("attack_speed must be > 0")
    if args.ult_mana < 0:
        raise ValueError("ult_mana must be >= 0")

    if args.ticks is not None:
        ticks = int(args.ticks)
    elif args.durationSec is not None:
        ticks = int(round(float(args.durationSec) * float(args.attack_speed)))
    else:
        raise ValueError("Either --ticks or --durationSec is required.")

    params = ChonaParams5019(
        attack_power=args.attack_power,
        attack_speed=args.attack_speed,
        skill1_rate=args.skill1_rate,
        skill1_mult=args.skill1_mult,
        skill2_mult=args.skill2_mult,
        ult_mult=args.ult_mult,
        ult_mana=args.ult_mana,
        crit_rate=args.crit_rate,
        crit_dmg=args.crit_dmg,
    )

    result = run_monte_carlo_5019(params=params, ticks=ticks, trials=args.trials, seed=args.seed)

    print("=== Chona(5019) Monte-Carlo Result ===")
    print(f"ticks={result['ticks']}  trials={result['trials']}")
    print(f"mean_total_damage={result['mean_total_damage']:.6f}")
    print(f"duration_sec_est(ticks/attack_speed)={result['duration_sec_est']:.6f}")
    print(f"mean_dps_est={result['mean_dps_est']:.6f}")
    print("mean_counts_per_trial:", {k: round(v, 3) for k, v in result["mean_counts"].items()})


if __name__ == "__main__":
    main()

