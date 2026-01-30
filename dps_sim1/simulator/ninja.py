from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple
import argparse
import math
import random


# ----------------------------
# Core model (Ninja / ID 3007)
# ----------------------------

@dataclass(frozen=True)
class NinjaParams3007:
    # battle stats
    attack_power: float
    attack_speed: float  # used for mana regen per tick

    # rates are percent 0..100
    skill1_rate: float
    skill2_rate: float
    react_rate: float
    crit_rate: float

    # multipliers (2 means 2x, 150 means 150x)
    base_attack_mult: float
    skill1_mult: float
    skill2_mult: float
    ult_mult: float
    crit_dmg: float

    # mana
    ult_mana: float
    mana_buff: float = 1.0  # optional; default 1.0

    def __post_init__(self) -> None:
        if self.attack_speed <= 0:
            raise ValueError("attack_speed must be > 0")
        for name, v in [
            ("skill1_rate", self.skill1_rate),
            ("skill2_rate", self.skill2_rate),
            ("react_rate", self.react_rate),
            ("crit_rate", self.crit_rate),
        ]:
            if not (0.0 <= v <= 100.0):
                raise ValueError(f"{name} must be in [0, 100], got {v}")

        if self.skill1_rate + self.skill2_rate > 100.0 + 1e-9:
            raise ValueError("skill1_rate + skill2_rate must be <= 100")

        if self.crit_dmg < 0:
            raise ValueError("crit_dmg must be >= 0")
        for name, v in [
            ("base_attack_mult", self.base_attack_mult),
            ("skill1_mult", self.skill1_mult),
            ("skill2_mult", self.skill2_mult),
            ("ult_mult", self.ult_mult),
            ("mana_buff", self.mana_buff),
            ("attack_power", self.attack_power),
            ("ult_mana", self.ult_mana),
        ]:
            # multipliers/power can be 0, but not negative
            if v < 0:
                raise ValueError(f"{name} must be >= 0, got {v}")


def _apply_crit(rng: random.Random, raw_damage: float, crit_rate: float, crit_dmg: float) -> float:
    """crit_rate is percent 0..100, crit_dmg is multiplier."""
    if raw_damage <= 0:
        return 0.0
    if rng.random() * 100.0 < crit_rate:
        return raw_damage * crit_dmg
    return raw_damage


def simulate_total_damage_once_3007(params: NinjaParams3007, ticks: int, rng: random.Random) -> float:
    """
    1 trial simulation for given ticks.
    State machine:
      - If in skill2-chain, action is skill2. After action, continue with prob react_rate.
      - Otherwise, at tick start: if mana >= ult_mana -> ult (mana reset to 0), else choose skill1/skill2/basic by rates.
      - Mana regen: at end of EVERY tick, mana += mana_buff * (1/attack_speed).
    """
    if ticks < 0:
        raise ValueError("ticks must be >= 0")

    mana: float = 0.0
    total_damage: float = 0.0

    in_skill2_chain: bool = False

    mana_per_tick: float = params.mana_buff * (1.0 / params.attack_speed)

    for _ in range(ticks):
        action: str

        if in_skill2_chain:
            action = "skill2"
        else:
            if mana >= params.ult_mana and params.ult_mana > 0:
                action = "ult"
            elif params.ult_mana == 0:
                # If ult_mana is 0, ult condition is always satisfied by definition.
                action = "ult"
            else:
                r = rng.random() * 100.0
                if r < params.skill1_rate:
                    action = "skill1"
                elif r < params.skill1_rate + params.skill2_rate:
                    action = "skill2"
                else:
                    action = "basic"

        # execute action (damage + mana changes that occur immediately)
        if action == "basic":
            raw = params.attack_power * params.base_attack_mult
            total_damage += _apply_crit(rng, raw, params.crit_rate, params.crit_dmg)

        elif action == "skill1":
            raw = params.attack_power * params.skill1_mult
            total_damage += _apply_crit(rng, raw, params.crit_rate, params.crit_dmg)

        elif action == "skill2":
            raw = params.attack_power * params.skill2_mult
            total_damage += _apply_crit(rng, raw, params.crit_rate, params.crit_dmg)

        elif action == "ult":
            raw = params.attack_power * params.ult_mult
            total_damage += _apply_crit(rng, raw, params.crit_rate, params.crit_dmg)
            mana = 0.0  # ult casts -> mana reset immediately

        else:
            raise RuntimeError(f"unknown action: {action}")

        # decide chain continuation for skill2
        if action == "skill2":
            if rng.random() * 100.0 < params.react_rate:
                in_skill2_chain = True
            else:
                in_skill2_chain = False
        else:
            in_skill2_chain = False

        # end-of-tick mana recovery
        mana += mana_per_tick

    return total_damage


def monte_carlo_mean_total_damage_3007(
    params: NinjaParams3007,
    ticks: int,
    trials: int,
    seed: Optional[int] = None,
) -> Tuple[float, float]:
    """
    Returns (mean_total_damage, sample_stddev).
    """
    if trials <= 0:
        raise ValueError("trials must be > 0")

    rng = random.Random(seed)
    values = []
    for _ in range(trials):
        values.append(simulate_total_damage_once_3007(params, ticks, rng))

    mean = sum(values) / trials
    if trials == 1:
        return mean, 0.0

    # sample stddev
    var = sum((x - mean) ** 2 for x in values) / (trials - 1)
    return mean, math.sqrt(var)


# ----------------------------
# External API function
# ----------------------------

def simulate_damage_breakdown_once_3007(
    params: NinjaParams3007,
    ticks: int,
    rng: random.Random,
) -> Tuple[float, float, float, float, float]:
    """
    1 trial simulation for given ticks.
    Returns damage breakdown: (basic, skill1, skill2, skill3, ult).
      - skill3 is not present for this character, so it is always 0.0
    """
    if ticks < 0:
        raise ValueError("ticks must be >= 0")

    mana: float = 0.0
    in_skill2_chain: bool = False

    dmg_basic = 0.0
    dmg_skill1 = 0.0
    dmg_skill2 = 0.0
    dmg_ult = 0.0

    mana_per_tick: float = params.mana_buff * (1.0 / params.attack_speed)

    for _ in range(ticks):
        action: str

        if in_skill2_chain:
            action = "skill2"
        else:
            if mana >= params.ult_mana and params.ult_mana > 0:
                action = "ult"
            elif params.ult_mana == 0:
                action = "ult"
            else:
                r = rng.random() * 100.0
                if r < params.skill1_rate:
                    action = "skill1"
                elif r < params.skill1_rate + params.skill2_rate:
                    action = "skill2"
                else:
                    action = "basic"

        if action == "basic":
            raw = params.attack_power * params.base_attack_mult
            dmg_basic += _apply_crit(rng, raw, params.crit_rate, params.crit_dmg)

        elif action == "skill1":
            raw = params.attack_power * params.skill1_mult
            dmg_skill1 += _apply_crit(rng, raw, params.crit_rate, params.crit_dmg)

        elif action == "skill2":
            raw = params.attack_power * params.skill2_mult
            dmg_skill2 += _apply_crit(rng, raw, params.crit_rate, params.crit_dmg)

        elif action == "ult":
            raw = params.attack_power * params.ult_mult
            dmg_ult += _apply_crit(rng, raw, params.crit_rate, params.crit_dmg)
            mana = 0.0

        else:
            raise RuntimeError(f"unknown action: {action}")

        if action == "skill2":
            if rng.random() * 100.0 < params.react_rate:
                in_skill2_chain = True
            else:
                in_skill2_chain = False
        else:
            in_skill2_chain = False

        mana += mana_per_tick

    return dmg_basic, dmg_skill1, dmg_skill2, 0.0, dmg_ult

def mean_total_damage_3007(options: Dict[str, Any]) -> Tuple[float, float, float, float, float]:
    """
    外部から「平均総ダメージ内訳」を取りたい用。

    戻り値: (basic, skill1, skill2, skill3, ult)
      - skill3 は存在しないため常に 0.0
    """
    params = NinjaParams3007(
        attack_power=float(options["attack_power"]),
        attack_speed=float(options["attack_speed"]),
        base_attack_mult=float(options["base_attack_mult"]),
        skill1_rate=float(options["skill1_rate"]),
        skill2_rate=float(options["skill2_rate"]),
        react_rate=float(options["react_rate"]),
        skill1_mult=float(options["skill1_mult"]),
        skill2_mult=float(options["skill2_mult"]),
        ult_mult=float(options["ult_mult"]),
        ult_mana=float(options["ult_mana"]),
        crit_rate=float(options["crit_rate"]),
        crit_dmg=float(options["crit_dmg"]),
        mana_buff=float(options.get("mana_buff", 1.0)),
    )

    ticks = int(options["ticks"])
    trials = int(options.get("trials", 10000))
    if trials <= 0:
        raise ValueError("trials must be > 0")

    seed = options.get("seed", None)
    seed_int = int(seed) if seed is not None else None
    rng = random.Random(seed_int)

    s_basic = s_s1 = s_s2 = s_s3 = s_ult = 0.0
    for _ in range(trials):
        b, s1, s2, s3, u = simulate_damage_breakdown_once_3007(params, ticks, rng)
        s_basic += b
        s_s1 += s1
        s_s2 += s2
        s_s3 += s3
        s_ult += u

    inv = 1.0 / float(trials)
    return s_basic * inv, s_s1 * inv, s_s2 * inv, s_s3 * inv, s_ult * inv

def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Ninja (ID 3007) Monte Carlo damage simulator (tick-based).")

    p.add_argument("--ticks", type=int, required=True, help="number of ticks to simulate")
    p.add_argument("--trials", type=int, default=10000, help="Monte Carlo trials (default: 10000)")
    p.add_argument("--seed", type=int, default=None, help="random seed")

    p.add_argument("--attack_power", type=float, required=True)
    p.add_argument("--attack_speed", type=float, required=True)

    p.add_argument("--base_attack_mult", type=float, required=True)
    p.add_argument("--skill1_rate", type=float, required=True)
    p.add_argument("--skill2_rate", type=float, required=True)
    p.add_argument("--react_rate", type=float, required=True)

    p.add_argument("--skill1_mult", type=float, required=True)
    p.add_argument("--skill2_mult", type=float, required=True)
    p.add_argument("--ult_mult", type=float, required=True)
    p.add_argument("--ult_mana", type=float, required=True)

    p.add_argument("--crit_rate", type=float, required=True)
    p.add_argument("--crit_dmg", type=float, required=True)

    # optional (mentioned in spec text)
    p.add_argument("--mana_buff", type=float, default=1.0, help="mana recovery multiplier (default: 1.0)")

    return p


def main() -> None:
    args = build_arg_parser().parse_args()

    params = NinjaParams3007(
        attack_power=args.attack_power,
        attack_speed=args.attack_speed,
        base_attack_mult=args.base_attack_mult,
        skill1_rate=args.skill1_rate,
        skill2_rate=args.skill2_rate,
        react_rate=args.react_rate,
        skill1_mult=args.skill1_mult,
        skill2_mult=args.skill2_mult,
        ult_mult=args.ult_mult,
        ult_mana=args.ult_mana,
        crit_rate=args.crit_rate,
        crit_dmg=args.crit_dmg,
        mana_buff=args.mana_buff,
    )

    mean, std = monte_carlo_mean_total_damage_3007(
        params=params,
        ticks=args.ticks,
        trials=args.trials,
        seed=args.seed,
    )

    dmg_per_tick = mean / args.ticks if args.ticks > 0 else 0.0

    # 95% CI for mean (normal approx) — trials が十分大きい前提の目安
    ci95 = 0.0
    if args.trials > 1:
        ci95 = 1.96 * (std / math.sqrt(args.trials))

    print("=== Ninja (ID 3007) Monte Carlo Result ===")
    print(f"ticks   : {args.ticks}")
    print(f"trials  : {args.trials}")
    print(f"seed    : {args.seed}")
    print("-----------------------------------------")
    print(f"mean_total_damage : {mean:.6f}")
    print(f"damage_per_tick   : {dmg_per_tick:.6f}")
    print(f"sample_stddev     : {std:.6f}")
    if args.trials > 1:
        print(f"95% CI (mean)     : ±{ci95:.6f}  (normal approx)")
    print("=========================================")


if __name__ == "__main__":
    main()

