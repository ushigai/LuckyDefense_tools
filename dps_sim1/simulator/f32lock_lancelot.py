from __future__ import annotations

from typing import Any, Dict, Optional, Tuple
import argparse
import math
import random

from dps_sim1.simulator.f32lock_rounding import round_half_up as round
from dps_sim1.simulator.lancelot import (
    ACTION_BASIC,
    ACTION_SKILL1,
    ACTION_SKILL2,
    ACTION_ULT,
    LancelotParams5003,
    _choose_nonult_action,
    _damage_for_action,
    _validate_params,
)


def _simulate_one_trial_core(
    params: LancelotParams5003,
    ticks: int,
    rng: random.Random,
) -> Tuple[float, Dict[str, float], Dict[str, int]]:
    if ticks < 0:
        raise ValueError("ticks must be >= 0")

    mana = 0.0
    dmg_br = {
        ACTION_BASIC: 0.0,
        ACTION_SKILL1: 0.0,
        ACTION_SKILL2: 0.0,
        ACTION_ULT: 0.0,
    }
    counts = {
        ACTION_BASIC: 0,
        ACTION_SKILL1: 0,
        ACTION_SKILL2: 0,
        ACTION_ULT: 0,
    }

    passive_mana_per_tick = (1.0 / params.attack_speed) * params.mana_buff
    basic_bonus_mana = params.attack_mana_recov * params.mana_buff
    skill_ult_recovery_ticks = max(0, int(round(0.8 * params.attack_speed)) - 1)
    recovery_remaining = 0

    for _ in range(ticks):
        if recovery_remaining > 0:
            recovery_remaining -= 1
            mana += passive_mana_per_tick
            continue

        if mana >= params.ult_mana:
            action = ACTION_ULT
            mana = 0.0
        else:
            action = _choose_nonult_action(rng, params)

        dealt = _damage_for_action(action, params, rng)
        dmg_br[action] += dealt
        counts[action] += 1

        if action in {ACTION_SKILL1, ACTION_SKILL2, ACTION_ULT}:
            recovery_remaining = skill_ult_recovery_ticks

        # Recovery is always applied at the end of each tick.
        mana += passive_mana_per_tick
        if action == ACTION_BASIC:
            mana += basic_bonus_mana

    total = dmg_br[ACTION_BASIC] + dmg_br[ACTION_SKILL1] + dmg_br[ACTION_SKILL2] + dmg_br[ACTION_ULT]
    return total, dmg_br, counts


def run_monte_carlo_5003(
    params: LancelotParams5003,
    ticks: int,
    trials: int,
    seed: Optional[int] = None,
) -> Dict[str, Any]:
    _validate_params(params)
    if ticks < 0:
        raise ValueError("ticks must be >= 0")
    if trials <= 0:
        raise ValueError("trials must be > 0")

    rng = random.Random(seed)
    totals = []
    breakdown_sum = {
        ACTION_BASIC: 0.0,
        ACTION_SKILL1: 0.0,
        ACTION_SKILL2: 0.0,
        ACTION_ULT: 0.0,
    }
    counts_sum = {
        ACTION_BASIC: 0,
        ACTION_SKILL1: 0,
        ACTION_SKILL2: 0,
        ACTION_ULT: 0,
    }

    for _ in range(trials):
        total, breakdown, counts = _simulate_one_trial_core(params, ticks, rng)
        totals.append(total)
        for key in breakdown_sum:
            breakdown_sum[key] += breakdown[key]
        for key in counts_sum:
            counts_sum[key] += counts[key]

    mean_total = sum(totals) / float(trials)
    if trials >= 2:
        var = sum((x - mean_total) ** 2 for x in totals) / float(trials - 1)
        std_total = math.sqrt(var)
    else:
        std_total = 0.0

    return {
        "ticks": ticks,
        "trials": trials,
        "seed": seed,
        "mean_total_damage": mean_total,
        "std_total_damage": std_total,
        "mean_breakdown_total": {k: v / float(trials) for k, v in breakdown_sum.items()},
        "mean_counts": {k: v / float(trials) for k, v in counts_sum.items()},
    }


def mean_total_damage_5003(options: Dict[str, Any]) -> Tuple[float, float, float, float, float]:
    params = LancelotParams5003(
        attack_power=float(options["attack_power"]),
        attack_speed=float(options["attack_speed"]),
        base_attack_mult=float(options["base_attack_mult"]),
        skill1_mult=float(options["skill1_mult"]),
        skill2_mult=float(options["skill2_mult"]),
        ult_mult=float(options["ult_mult"]),
        skill1_rate=float(options["skill1_rate"]),
        skill2_rate=float(options["skill2_rate"]),
        crit_rate=float(options["crit_rate"]),
        crit_dmg=float(options["crit_dmg"]),
        additional_dmg=float(options["additional_dmg"]),
        ult_mana=float(options["ult_mana"]),
        attack_mana_recov=float(options["attack_mana_recov"]),
        mana_buff=float(options.get("mana_buff", 1.0)),
    )

    trials = int(options.get("trials", 10000))
    seed = options.get("seed", None)
    if "ticks" in options and options["ticks"] is not None:
        ticks = int(options["ticks"])
    elif "durationSec" in options and options["durationSec"] is not None:
        ticks = int(round(float(options["durationSec"]) * params.attack_speed))
    else:
        raise ValueError("options must include either 'ticks' or 'durationSec'.")

    result = run_monte_carlo_5003(params=params, ticks=ticks, trials=trials, seed=seed)
    br = result.get("mean_breakdown_total", {})
    return (
        float(br.get(ACTION_BASIC, 0.0)),
        float(br.get(ACTION_SKILL1, 0.0)),
        float(br.get(ACTION_SKILL2, 0.0)),
        0.0,
        float(br.get(ACTION_ULT, 0.0)),
    )


def main() -> None:
    ap = argparse.ArgumentParser(description="Lancelot(5003) f32lock Monte-Carlo damage simulator")
    ap.add_argument("--attack_power", type=float, required=True)
    ap.add_argument("--attack_speed", type=float, required=True)

    ap.add_argument("--base_attack_mult", type=float, required=True)
    ap.add_argument("--skill1_mult", type=float, required=True)
    ap.add_argument("--skill2_mult", type=float, required=True)
    ap.add_argument("--ult_mult", type=float, required=True)
    ap.add_argument("--additional_dmg", type=float, required=True)

    ap.add_argument("--skill1_rate", type=float, required=True, help="0..100")
    ap.add_argument("--skill2_rate", type=float, required=True, help="0..100")
    ap.add_argument("--crit_rate", type=float, required=True, help="0..100")
    ap.add_argument("--crit_dmg", type=float, required=True)

    ap.add_argument("--ult_mana", type=float, required=True)
    ap.add_argument("--attack_mana_recov", type=float, required=True)
    ap.add_argument("--mana_buff", type=float, default=1.0)

    ap.add_argument("--ticks", type=int, default=None)
    ap.add_argument("--durationSec", type=float, default=None)
    ap.add_argument("--trials", type=int, default=10000)
    ap.add_argument("--seed", type=int, default=None)
    args = ap.parse_args()

    if args.ticks is not None:
        ticks = int(args.ticks)
    elif args.durationSec is not None:
        ticks = int(round(float(args.durationSec) * float(args.attack_speed)))
    else:
        raise ValueError("Either --ticks or --durationSec is required.")

    params = LancelotParams5003(
        attack_power=args.attack_power,
        attack_speed=args.attack_speed,
        base_attack_mult=args.base_attack_mult,
        skill1_mult=args.skill1_mult,
        skill2_mult=args.skill2_mult,
        ult_mult=args.ult_mult,
        skill1_rate=args.skill1_rate,
        skill2_rate=args.skill2_rate,
        crit_rate=args.crit_rate,
        crit_dmg=args.crit_dmg,
        additional_dmg=args.additional_dmg,
        ult_mana=args.ult_mana,
        attack_mana_recov=args.attack_mana_recov,
        mana_buff=args.mana_buff,
    )
    out = run_monte_carlo_5003(params=params, ticks=ticks, trials=args.trials, seed=args.seed)
    br = out["mean_breakdown_total"]

    print("=== Lancelot(5003) f32lock Monte-Carlo Result ===")
    print(f"ticks={out['ticks']}  trials={out['trials']}  seed={out['seed']}")
    print(f"mean_total_damage={out['mean_total_damage']:.6f}")
    print(f"std_total_damage={out['std_total_damage']:.6f}")
    print("mean_breakdown_total:")
    print(f"  basic={br[ACTION_BASIC]:.6f}")
    print(f"  skill1={br[ACTION_SKILL1]:.6f}")
    print(f"  skill2={br[ACTION_SKILL2]:.6f}")
    print(f"  ult={br[ACTION_ULT]:.6f}")


if __name__ == "__main__":
    main()
