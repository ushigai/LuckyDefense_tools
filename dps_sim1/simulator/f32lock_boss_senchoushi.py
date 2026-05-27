# boss_senchoushi_15024.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Any, Dict, Tuple, Optional
import math
import random
from dps_sim1.simulator.f32lock_rounding import round_half_up as round


def _clamp(x: float, lo: float, hi: float) -> float:
    return lo if x < lo else hi if x > hi else x


@dataclass(frozen=True)
class BossSenchoushiParams15024:
    # rates are given in 0..100 (%)
    skill1_rate: float
    skill2_rate: float
    crit_rate: float
    ult_buff: float

    # multipliers are given as raw multiplier (2 => x2, 150 => x150)
    skill1_mult: float
    skill2_mult: float
    skill3_mult: float
    ult_mult: float
    crit_dmg: float

    # core stats
    attack_speed: float
    attack_power: float

    # mana system (NOT listed in your "引数として与えられる" list, but required by your spec)
    ult_mana: float
    mana_buff: float

    @staticmethod
    def from_dict(d: Mapping[str, Any]) -> "BossSenchoushiParams15024":
        # Required keys by this implementation
        required = [
            "skill1_rate", "skill2_rate", "attack_speed", "attack_power",
            "skill1_mult", "skill2_mult", "skill3_mult",
            "crit_rate", "crit_dmg",
            "ult_mana", "mana_buff",
            "ult_mult", "ult_buff",
        ]
        missing = [k for k in required if k not in d]
        if missing:
            raise KeyError(f"Missing keys in params: {missing}")

        return BossSenchoushiParams15024(
            skill1_rate=float(d["skill1_rate"]),
            skill2_rate=float(d["skill2_rate"]),
            attack_speed=float(d["attack_speed"]),
            attack_power=float(d["attack_power"]),
            skill1_mult=float(d["skill1_mult"]),
            skill2_mult=float(d["skill2_mult"]),
            skill3_mult=float(d["skill3_mult"]),
            crit_rate=float(d["crit_rate"]),
            crit_dmg=float(d["crit_dmg"]),
            ult_mana=float(d["ult_mana"]),
            mana_buff=float(d["mana_buff"]),
            ult_mult=float(d["ult_mult"]),
            ult_buff=float(d["ult_buff"]),
        )


def _roll_crit(rng: random.Random, crit_rate_pct: float, crit_dmg: float, base_damage: float) -> float:
    if base_damage == 0:
        return 0.0
    p = _clamp(crit_rate_pct, 0.0, 100.0) / 100.0
    if rng.random() < p:
        return base_damage * crit_dmg
    return base_damage


def _choose_action(rng: random.Random, s1_pct: float, s2_pct: float) -> str:
    """
    Returns one of: 'basic', 'skill1', 'skill2'
    Probability model:
      skill1: s1_pct
      skill2: s2_pct
      basic: 100 - s1_pct - s2_pct
    If s1_pct + s2_pct > 100, we renormalize skill1/skill2 to sum to 100 and set basic=0.
    """
    s1 = _clamp(s1_pct, 0.0, 100.0)
    s2 = _clamp(s2_pct, 0.0, 100.0)

    total = s1 + s2
    if total > 100.0:
        # Renormalize to avoid negative basic probability
        s1 = 100.0 * (s1 / total) if total > 0 else 0.0
        s2 = 100.0 * (s2 / total) if total > 0 else 0.0
        total = 100.0

    r = rng.random() * 100.0
    if r < s1:
        return "skill1"
    if r < s1 + s2:
        return "skill2"
    return "basic"


def simulate_once_15024(
    params: BossSenchoushiParams15024,
    *,
    num_ticks: int,
    rng: random.Random,
) -> Dict[str, float]:
    """
    Simulate one run for num_ticks ticks.

    Internal action names:
      basic, skill1, skill2, skill3, ult

    Returns damage totals by category:
      {'basic':..., 'skill1':..., 'skill2':..., 'skill3':..., 'ult':...}
    """
    if num_ticks <= 0:
        return {"basic": 0.0, "skill1": 0.0, "skill2": 0.0, "skill3": 0.0, "ult": 0.0}

    # State
    mana = 0.0
    mana_reset_next_tick = False

    # Trick token counter: every 3 activations of (skill1 or skill2)
    skill12_count = 0

    # For skill3 bonus window
    last_skill1_tick: float = -1e30
    last_skill2_tick: float = -1e30

    # Ult buff: use "expires_at" as a float tick index threshold, no rounding.
    # Active if current_tick <= buff_expires_at.
    buff_expires_at: float = -1e30  # inactive

    dmg = {"basic": 0.0, "skill1": 0.0, "skill2": 0.0, "skill3": 0.0, "ult": 0.0}

    # Pre-calc for mana recovery
    if params.attack_speed <= 0:
        raise ValueError("attack_speed must be > 0")
    base_tick_mana = (1.0 / params.attack_speed) * params.mana_buff
    basic_extra_mana = 1.0

    # Window sizes / durations (float, no rounding)
    skill3_window = 5.0 * params.attack_speed
    ult_base_duration = 12.0 * params.attack_speed
    ult_extend = 0.8 * params.attack_speed
    skill_ult_recovery_ticks = max(0, int(round(0.8 * params.attack_speed)) - 1)
    recovery_remaining = 0

    for t in range(num_ticks):
        tf = float(t)

        # "フィナーレ発動後の次のtickでマナが0"
        if mana_reset_next_tick:
            mana = 0.0
            mana_reset_next_tick = False

        buff_active = tf <= buff_expires_at

        if recovery_remaining > 0:
            recovery_remaining -= 1
            mana += base_tick_mana
            continue

        # Action decision
        if mana >= params.ult_mana:
            action = "ult"
        else:
            add = params.ult_buff if buff_active else 0.0
            action = _choose_action(rng, params.skill1_rate + add, params.skill2_rate + add)

        # Damage phase (and skill bookkeeping)
        if action == "basic":
            base = params.attack_power * 1.0
            dealt = _roll_crit(rng, params.crit_rate, params.crit_dmg, base)
            dmg["basic"] += dealt

        elif action == "skill1":
            base = params.attack_power * params.skill1_mult
            dealt = _roll_crit(rng, params.crit_rate, params.crit_dmg, base)
            dmg["skill1"] += dealt
            recovery_remaining = skill_ult_recovery_ticks

            last_skill1_tick = tf
            skill12_count += 1

        elif action == "skill2":
            base = params.attack_power * params.skill2_mult
            dealt = _roll_crit(rng, params.crit_rate, params.crit_dmg, base)
            dmg["skill2"] += dealt
            recovery_remaining = skill_ult_recovery_ticks

            last_skill2_tick = tf
            skill12_count += 1

        elif action == "ult":
            base = params.attack_power * params.ult_mult
            dealt = _roll_crit(rng, params.crit_rate, params.crit_dmg, base)
            dmg["ult"] += dealt

            # Start/refresh buff: active on ticks where tick <= t + 12*attack_speed
            buff_expires_at = tf + ult_base_duration

            # Mana resets at the next tick
            mana_reset_next_tick = True
            recovery_remaining = skill_ult_recovery_ticks

        else:
            raise RuntimeError(f"Unknown action: {action}")

        # Trick token trigger (skill3) — simultaneous, consumes no tick, no mana change
        # Trigger can happen multiple times if skill12_count jumps by >3 (not possible here, but keep robust).
        while skill12_count >= 3:
            skill12_count -= 3

            # Compute skill3 multiplier with conditional bonuses
            mult = params.skill3_mult
            if (tf - last_skill1_tick) <= skill3_window:
                mult += 5.0
            if (tf - last_skill2_tick) <= skill3_window:
                mult += 1.1

            base = params.attack_power * mult
            dealt = _roll_crit(rng, params.crit_rate, params.crit_dmg, base)
            dmg["skill3"] += dealt

            # Extend buff duration if buff is active "when skill3 fires"
            if tf <= buff_expires_at:
                buff_expires_at += ult_extend

        # End-of-tick mana recovery (mana_buff applies to tick recovery only)
        # - basic: +1 + (1/attack_speed)
        # - skill1/skill2/ult: +(1/attack_speed)
        if action == "basic":
            mana += base_tick_mana + basic_extra_mana
        else:
            mana += base_tick_mana

    return dmg


def mean_total_damage_15024(
    params_dict: Mapping[str, Any],
    *,
    num_ticks: int,
    trials: int = 20000,
    seed: Optional[int] = 0,
) -> Dict[str, Any]:
    """
    Monte Carlo mean damage for BossSenchoushi (15024).

    Args:
      params_dict: dict-like. Required keys:
        - skill1_rate, skill2_rate, attack_speed, attack_power
        - skill1_mult, skill2_mult, skill3_mult
        - crit_rate, crit_dmg
        - ult_mana, mana_buff
        - ult_mult, ult_buff
      num_ticks: simulation ticks per trial
      trials: number of Monte Carlo trials
      seed: RNG seed (None => non-deterministic)

    Returns:
      {
        "mean_damage": {"basic":..., "skill1":..., "skill2":..., "skill3":..., "ult":...},
        "mean_total": float,
        "mean_ratio": {"basic":..., ...}  # each in 0..1
      }
    """
    if trials <= 0:
        raise ValueError("trials must be > 0")

    params = BossSenchoushiParams15024.from_dict(params_dict)
    rng = random.Random(seed)

    acc = {"basic": 0.0, "skill1": 0.0, "skill2": 0.0, "skill3": 0.0, "ult": 0.0}
    for _ in range(trials):
        one = simulate_once_15024(params, num_ticks=num_ticks, rng=rng)
        for k in acc:
            acc[k] += one[k]

    mean_damage = {k: v / trials for k, v in acc.items()}
    mean_total = sum(mean_damage.values())
    if mean_total > 0:
        mean_ratio = {k: mean_damage[k] / mean_total for k in mean_damage}
    else:
        mean_ratio = {k: 0.0 for k in mean_damage}

    return mean_damage["basic"],mean_damage["skill1"],mean_damage["skill2"],mean_damage["skill3"],mean_damage["ult"]
    return {
        "mean_damage": mean_damage,
        "mean_total": mean_total,
        "mean_ratio": mean_ratio,
    }


# Optional convenience: raw tuple return (if you prefer positional)
def mean_total_damage_tuple_15024(
    params_dict: Mapping[str, Any],
    *,
    num_ticks: int,
    trials: int = 20000,
    seed: Optional[int] = 0,
) -> Tuple[float, float, float, float, float]:
    """
    Returns (basic, skill1, skill2, skill3, ult)
    """
    out = mean_total_damage_15024(params_dict, num_ticks=num_ticks, trials=trials, seed=seed)
    md = out["mean_damage"]
    return (md["basic"], md["skill1"], md["skill2"], md["skill3"], md["ult"])


if __name__ == "__main__":
    # Example usage
    params = {
        "skill1_rate": 20,
        "skill2_rate": 10,
        "attack_speed": 1.8599999999999999,
        "attack_power": 3441300,
        "skill1_mult": 3.0,
        "skill2_mult": 4.0,
        "skill3_mult": 2.0,
        "crit_rate": 20,
        "crit_dmg": 2.5,
        "ult_mana": 30,
        "mana_buff": 1.0,
        "ult_mult": 10.0,
        "ult_buff": 5.0,
    }
    print(mean_total_damage_15024(params, num_ticks=4000, trials=5000, seed=123))
