"""Boss 選鳥師 (ID:15024) Monte Carlo simulator.

Internal action names
---------------------
- basic  : 基本攻撃
- skill1 : ハードシャッフル
- skill2 : プライムサークル
- skill3 : トリックトークン (no tick; simultaneous)
- ult    : フィナーレ

Notes
-----
- This model advances time in *integer ticks* (t = 0, 1, 2, ...).
- Durations/windows that depend on attack_speed (e.g. 12*attack_speed, 0.8*attack_speed,
  5*attack_speed) are kept as floats and are *not rounded*.
- To support fractional tick windows, the ult buff is tracked as a float end-time
  (buff_end_time). Buff is active at tick t if t < buff_end_time.

Main exported helper
--------------------
mean_total_damage_15024(...): returns the Monte-Carlo mean of total damage over the given
number of ticks (or durationSec).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional
import argparse
import math
import random


@dataclass(frozen=True)
class BossParams15024:
    attack_power: float
    attack_speed: float
    skill1_rate: float
    skill2_rate: float
    skill1_mult: float
    skill2_mult: float
    skill3_mult: float
    ult_mult: float
    ult_mana: float
    mana_buff: float
    ult_buff: float
    crit_rate: float
    crit_dmg: float


def _crit_multiplier(rng: random.Random, crit_rate: float, crit_dmg: float) -> tuple[float, float, float, float, float]:
    """Return crit multiplier for a single damage event."""
    if crit_rate <= 0.0:
        return 1.0
    if crit_rate >= 100.0:
        return float(crit_dmg)
    return float(crit_dmg) if (rng.random() * 100.0) < crit_rate else 1.0


def _choose_action(
    rng: random.Random,
    mana: float,
    params: BossParams15024,
    buff_active: bool,
) -> str:
    """Choose the main action for this tick."""
    if mana >= params.ult_mana:
        return "ult"

    s1 = params.skill1_rate + (params.ult_buff if buff_active else 0.0)
    s2 = params.skill2_rate + (params.ult_buff if buff_active else 0.0)

    w1 = max(0.0, float(s1))
    w2 = max(0.0, float(s2))
    w_basic = 100.0 - w1 - w2
    if w_basic < 0.0:
        w_basic = 0.0

    total = w1 + w2 + w_basic
    if total <= 0.0:
        return "basic"

    r = rng.random() * total
    if r < w1:
        return "skill1"
    if r < w1 + w2:
        return "skill2"
    return "basic"


def simulate_trial_breakdown_15024(
    params: BossParams15024,
    ticks: int,
    rng: random.Random,
) -> tuple[float, float, float, float, float]:
    """Simulate one trial and return (basic, skill1, skill2, skill3, ult)."""
    if ticks < 0:
        raise ValueError("ticks must be >= 0")
    if params.attack_speed <= 0.0:
        raise ValueError("attack_speed must be > 0")

    mana: float = 0.0
    pending_mana_reset: bool = False
    buff_end_time: float = 0.0

    skill_count: int = 0
    last_skill1_tick: Optional[int] = None
    last_skill2_tick: Optional[int] = None

    basic_sum = 0.0
    skill1_sum = 0.0
    skill2_sum = 0.0
    skill3_sum = 0.0
    ult_sum = 0.0

    trick_window: float = 5.0 * params.attack_speed
    ult_duration: float = 12.0 * params.attack_speed + 1.0
    ult_extend: float = 0.8 * params.attack_speed

    for t in range(ticks):
        if pending_mana_reset:
            mana = 0.0
            pending_mana_reset = False

        buff_active: bool = float(t) < buff_end_time
        action = _choose_action(rng=rng, mana=mana, params=params, buff_active=buff_active)

        if action == "basic":
            dealt = params.attack_power * 1.0 * _crit_multiplier(rng, params.crit_rate, params.crit_dmg)
            basic_sum += dealt

        elif action == "skill1":
            dealt = params.attack_power * params.skill1_mult * _crit_multiplier(rng, params.crit_rate, params.crit_dmg)
            skill1_sum += dealt
            skill_count += 1
            last_skill1_tick = t

        elif action == "skill2":
            dealt = params.attack_power * params.skill2_mult * _crit_multiplier(rng, params.crit_rate, params.crit_dmg)
            skill2_sum += dealt
            skill_count += 1
            last_skill2_tick = t
            if buff_active:
                buff_end_time += ult_extend

        elif action == "ult":
            dealt = params.attack_power * params.ult_mult * _crit_multiplier(rng, params.crit_rate, params.crit_dmg)
            ult_sum += dealt
            buff_end_time = float(t) + ult_duration
            pending_mana_reset = True

        else:
            raise RuntimeError(f"unknown action: {action}")

        # Trick token (skill3)
        if action in ("skill1", "skill2"):
            if skill_count % 3 == 0:
                mult3 = float(params.skill3_mult)
                if last_skill1_tick is not None and (float(t - last_skill1_tick) <= trick_window):
                    mult3 += 5.0
                if last_skill2_tick is not None and (float(t - last_skill2_tick) <= trick_window):
                    mult3 += 1.1

                dealt3 = params.attack_power * mult3 * _crit_multiplier(rng, params.crit_rate, params.crit_dmg)
                skill3_sum += dealt3

                if buff_active:
                    buff_end_time += ult_extend

        mana += params.mana_buff * (1.0 / params.attack_speed)
        if action == "basic":
            mana += params.mana_buff * 1.0

    return (basic_sum, skill1_sum, skill2_sum, skill3_sum, ult_sum)


def simulate_trial_total_damage_15024(
    params: BossParams15024,
    ticks: int,
    rng: random.Random,
) -> tuple[float, float, float, float, float]:
    """Simulate one trial and return total damage (legacy wrapper)."""
    return float(sum(simulate_trial_breakdown_15024(params=params, ticks=ticks, rng=rng)))



def mean_total_damage_15024(
    *,
    attack_power: float,
    attack_speed: float,
    skill1_rate: float,
    skill2_rate: float,
    skill1_mult: float,
    skill2_mult: float,
    skill3_mult: float,
    ult_mult: float,
    ult_mana: float,
    mana_buff: float = 1.0,
    ult_buff: float = 0.0,
    crit_rate: float = 0.0,
    crit_dmg: float = 1.0,
    ticks: Optional[int] = None,
    durationSec: Optional[float] = None,
    trials: int = 10_000,
    seed: Optional[int] = 1,
) -> tuple[float, float, float, float, float]:
    """Return Monte-Carlo mean of total damage.

    You can specify either:
      - ticks: number of integer ticks to simulate
      - durationSec: duration in seconds (interpreted as: ticks_per_second = attack_speed)

    If durationSec yields a non-integer tick count, this simulates floor(durationSec * attack_speed)
    ticks (no rounding up).
    """
    if ticks is None:
        if durationSec is None:
            raise ValueError("either ticks or durationSec must be provided")
        # Interpret: attack_speed = ticks per second.
        ticks = int(math.floor(float(durationSec) * float(attack_speed)))

    if trials <= 0:
        raise ValueError("trials must be > 0")

    params = BossParams15024(
        attack_power=float(attack_power),
        attack_speed=float(attack_speed),
        skill1_rate=float(skill1_rate),
        skill2_rate=float(skill2_rate),
        skill1_mult=float(skill1_mult),
        skill2_mult=float(skill2_mult),
        skill3_mult=float(skill3_mult),
        ult_mult=float(ult_mult),
        ult_mana=float(ult_mana),
        mana_buff=float(mana_buff),
        ult_buff=float(ult_buff),
        crit_rate=float(crit_rate),
        crit_dmg=float(crit_dmg),
    )

    rng = random.Random(seed)
    sum_basic = sum_skill1 = sum_skill2 = sum_skill3 = sum_ult = 0.0
    for _ in range(int(trials)):
        b, s1, s2, s3, u = simulate_trial_breakdown_15024(params=params, ticks=int(ticks), rng=rng)
        sum_basic += b
        sum_skill1 += s1
        sum_skill2 += s2
        sum_skill3 += s3
        sum_ult += u
    return (sum_basic / float(trials), sum_skill1 / float(trials), sum_skill2 / float(trials), sum_skill3 / float(trials), sum_ult / float(trials))


def mean_total_damage_15024_options(options: Dict[str, Any]) -> tuple[float, float, float, float, float]:
    """Dict-based wrapper (handy for plugging into existing code that uses options dicts)."""
    return mean_total_damage_15024(
        attack_power=options["attack_power"],
        attack_speed=options["attack_speed"],
        skill1_rate=options["skill1_rate"],
        skill2_rate=options["skill2_rate"],
        skill1_mult=options["skill1_mult"],
        skill2_mult=options["skill2_mult"],
        skill3_mult=options["skill3_mult"],
        ult_mult=options["ult_mult"],
        ult_mana=options["ult_mana"],
        mana_buff=options.get("mana_buff", 1.0),
        ult_buff=options.get("ult_buff", 0.0),
        crit_rate=options.get("crit_rate", 0.0),
        crit_dmg=options.get("crit_dmg", 1.0),
        ticks=options.get("ticks"),
        durationSec=options.get("durationSec"),
        trials=options.get("trials", 10_000),
        seed=options.get("seed", 1),
    )


def _cli() -> int:
    p = argparse.ArgumentParser(description="Boss 選鳥師(15024) Monte Carlo simulator")

    p.add_argument("--attack_power", type=float, required=True)
    p.add_argument("--attack_speed", type=float, required=True)

    p.add_argument("--skill1_rate", type=float, required=True, help="percent (0-100)")
    p.add_argument("--skill2_rate", type=float, required=True, help="percent (0-100)")

    p.add_argument("--skill1_mult", type=float, required=True)
    p.add_argument("--skill2_mult", type=float, required=True)
    p.add_argument("--skill3_mult", type=float, required=True)

    p.add_argument("--ult_mult", type=float, required=True)
    p.add_argument("--ult_buff", type=float, required=True, help="percent to add to skill1/2 rates during buff")
    p.add_argument("--ult_mana", type=float, required=True)

    p.add_argument("--mana_buff", type=float, default=1.0)

    p.add_argument("--crit_rate", type=float, required=True, help="percent (0-100)")
    p.add_argument("--crit_dmg", type=float, required=True, help="multiplier")

    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--ticks", type=int)
    g.add_argument("--durationSec", type=float)

    p.add_argument("--trials", type=int, default=10_000)
    p.add_argument("--seed", type=int, default=1)

    args = p.parse_args()

    br = mean_total_damage_15024(
        attack_power=args.attack_power,
        attack_speed=args.attack_speed,
        skill1_rate=args.skill1_rate,
        skill2_rate=args.skill2_rate,
        skill1_mult=args.skill1_mult,
        skill2_mult=args.skill2_mult,
        skill3_mult=args.skill3_mult,
        ult_mult=args.ult_mult,
        ult_mana=args.ult_mana,
        mana_buff=args.mana_buff,
        ult_buff=args.ult_buff,
        crit_rate=args.crit_rate,
        crit_dmg=args.crit_dmg,
        ticks=args.ticks,
        durationSec=args.durationSec,
        trials=args.trials,
        seed=args.seed,
    )


    mean_total = sum(br)
    # Estimate DPS under a common interpretation: ticks_per_second = attack_speed.
    # If ticks specified directly, durationSec = ticks / attack_speed.
    if args.ticks is not None:
        duration = float(args.ticks) / float(args.attack_speed)
    else:
        duration = float(args.durationSec)

    mean_dps = mean_total / duration if duration > 0.0 else float("nan")

    print(f"mean_total_damage = {mean_total:.6f}")
    print(f"durationSec        = {duration:.6f}")
    print(f"mean_DPS           = {mean_dps:.6f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli())
