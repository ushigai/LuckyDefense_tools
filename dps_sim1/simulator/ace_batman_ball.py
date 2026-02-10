from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional
import math
import random


# -----------------------------
# Utilities
# -----------------------------
def _pct_to_prob(x: float) -> float:
    """0~100 (%) -> 0~1 probability"""
    return max(0.0, min(1.0, x / 100.0))


def _as_float(x: Any, name: str) -> float:
    try:
        return float(x)
    except Exception as e:
        raise ValueError(f"{name} must be a number, got {x!r}") from e


def _as_int(x: Any, name: str) -> int:
    try:
        v = int(x)
    except Exception as e:
        raise ValueError(f"{name} must be an int, got {x!r}") from e
    return v


def _validate_nonneg(v: float, name: str) -> None:
    if v < 0:
        raise ValueError(f"{name} must be >= 0, got {v}")


def _validate_rate_0_100(v: float, name: str) -> None:
    if not (0.0 <= v <= 100.0):
        raise ValueError(f"{name} must be in [0, 100], got {v}")


# -----------------------------
# Params
# -----------------------------
@dataclass(frozen=True)
class AceBatmanPitcherParams15110:
    # core
    base_attack_mult: float
    skill1_rate: float  # percent 0..100
    attack_speed: float
    attack_power: float
    skill1_mult: float
    ult_mult: float
    ult_mana: float

    # crit
    crit_rate: float  # percent 0..100
    crit_dmg: float   # multiplier (e.g., 2.5)

    # strikeout chaining
    skill1_react1: float  # percent 0..100 (1st->2nd)
    skill1_react2: float  # percent 0..100 (2nd->3rd)

    # buff add-on during ult buff state
    add_rate: float  # percent 0..100
    add_mult: float  # multiplier to be ADDED to base_attack_mult when proc

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "AceBatmanPitcherParams15110":
        # Required keys (you can add defaults here if you want)
        p = AceBatmanPitcherParams15110(
            base_attack_mult=_as_float(d["base_attack_mult"], "base_attack_mult"),
            skill1_rate=_as_float(d["skill1_rate"], "skill1_rate"),
            attack_speed=_as_float(d["attack_speed"], "attack_speed"),
            attack_power=_as_float(d["attack_power"], "attack_power"),
            skill1_mult=_as_float(d["skill1_mult"], "skill1_mult"),
            ult_mult=_as_float(d["ult_mult"], "ult_mult"),
            ult_mana=_as_float(d["ult_mana"], "ult_mana"),
            crit_rate=_as_float(d["crit_rate"], "crit_rate"),
            crit_dmg=_as_float(d["crit_dmg"], "crit_dmg"),
            skill1_react1=_as_float(d["skill1_react1"], "skill1_react1"),
            skill1_react2=_as_float(d["skill1_react2"], "skill1_react2"),
            add_rate=_as_float(d["add_rate"], "add_rate"),
            add_mult=_as_float(d["add_mult"], "add_mult"),
        )
        p.validate()
        return p

    def validate(self) -> None:
        _validate_nonneg(self.base_attack_mult, "base_attack_mult")
        _validate_nonneg(self.attack_speed, "attack_speed")
        _validate_nonneg(self.attack_power, "attack_power")
        _validate_nonneg(self.skill1_mult, "skill1_mult")
        _validate_nonneg(self.ult_mult, "ult_mult")
        _validate_nonneg(self.ult_mana, "ult_mana")
        _validate_nonneg(self.crit_dmg, "crit_dmg")
        _validate_nonneg(self.add_mult, "add_mult")

        if self.attack_speed <= 0:
            raise ValueError(f"attack_speed must be > 0, got {self.attack_speed}")

        _validate_rate_0_100(self.skill1_rate, "skill1_rate")
        _validate_rate_0_100(self.crit_rate, "crit_rate")
        _validate_rate_0_100(self.skill1_react1, "skill1_react1")
        _validate_rate_0_100(self.skill1_react2, "skill1_react2")
        _validate_rate_0_100(self.add_rate, "add_rate")


# -----------------------------
# Core simulation
# -----------------------------
def _roll_crit(rng: random.Random, crit_p: float, crit_dmg: float) -> float:
    return crit_dmg if (rng.random() < crit_p) else 1.0


def _damage(attack_power: float, mult: float, crit_mul: float) -> float:
    return attack_power * mult * crit_mul


def simulate_total_damage_15110_once(
    params: AceBatmanPitcherParams15110,
    ticks: int,
    rng: random.Random,
) -> Dict[str, float]:
    """
    1試行ぶんの tick シミュレーション。
    返り値は:
      - basic: 基本攻撃の合計ダメージ（※追加分を除いた“基礎分”だけ）
      - skill1: ストライクアウト合計ダメージ
      - ult_add: フィニッシュピッチ(ult) + 追加攻撃(= add_mult 部分) の合計ダメージ
      - total: 全合計
    """
    if ticks <= 0:
        return {"basic": 0.0, "skill1": 0.0, "ult_add": 0.0, "total": 0.0}

    # probabilities
    p_skill1 = _pct_to_prob(params.skill1_rate)
    p_react1 = _pct_to_prob(params.skill1_react1)
    p_react2 = _pct_to_prob(params.skill1_react2)
    p_add = _pct_to_prob(params.add_rate)
    p_crit = _pct_to_prob(params.crit_rate)

    # state
    mana = 0.0
    buff_remaining = 0  # ticks remaining in buff state
    # strikeout chain state:
    # 0: not in chain
    # 1: next action is skill1 1st hit (only occurs when selected from basic)
    # 2: next action is skill1 2nd hit
    # 3: next action is skill1 3rd hit
    chain_next = 0

    # results
    dmg_basic = 0.0
    dmg_skill1 = 0.0
    dmg_ult_add = 0.0

    # regen per tick end
    mana_regen = 1.0 / params.attack_speed

    # buff duration ticks
    # NOTE: spec says "8*attck_speed tick". We interpret as 8*attack_speed ticks, integerized.
    buff_duration_ticks = int(math.ceil(8.0 * params.attack_speed))

    for _t in range(ticks):
        # 1) choose action (1 tick consumes exactly one action)
        # Priority:
        #   - If currently continuing strikeout chain => do skill1 hit
        #   - Else if mana >= ult_mana => do ult
        #   - Else pick basic vs skill1 by skill1_rate
        if chain_next != 0:
            # perform strikeout hit
            crit_mul = _roll_crit(rng, p_crit, params.crit_dmg)
            dmg = _damage(params.attack_power, params.skill1_mult, crit_mul)
            dmg_skill1 += dmg

            # advance chain
            if chain_next == 1:
                # after 1st hit, decide whether 2nd triggers
                if rng.random() < p_react1:
                    chain_next = 2
                else:
                    chain_next = 0
            elif chain_next == 2:
                # after 2nd hit, decide whether 3rd triggers
                if rng.random() < p_react2:
                    chain_next = 3
                else:
                    chain_next = 0
            else:
                # chain_next == 3 ends after 3rd
                chain_next = 0

        else:
            if mana >= params.ult_mana and params.ult_mana > 0:
                # ult
                crit_mul = _roll_crit(rng, p_crit, params.crit_dmg)
                dmg = _damage(params.attack_power, params.ult_mult, crit_mul)
                dmg_ult_add += dmg

                mana = 0.0
                buff_remaining = buff_duration_ticks

            else:
                # decide basic vs starting skill1
                if rng.random() < p_skill1:
                    # start skill1 chain: this tick is 1st hit
                    chain_next = 1
                    # execute immediately by looping logic once:
                    # do the same as chain branch without duplicating too much
                    crit_mul = _roll_crit(rng, p_crit, params.crit_dmg)
                    dmg = _damage(params.attack_power, params.skill1_mult, crit_mul)
                    dmg_skill1 += dmg
                    # after 1st hit, decide whether 2nd triggers
                    if rng.random() < p_react1:
                        chain_next = 2
                    else:
                        chain_next = 0
                else:
                    # basic
                    # base part
                    crit_mul = _roll_crit(rng, p_crit, params.crit_dmg)
                    dmg_base = _damage(params.attack_power, params.base_attack_mult, crit_mul)
                    dmg_basic += dmg_base

                    # add-on (only during buff state) => counts into ult_add bucket as "追加攻撃(= add_mult 部分)"
                    if buff_remaining > 0 and (rng.random() < p_add):
                        dmg_add = _damage(params.attack_power, params.add_mult, crit_mul)
                        dmg_ult_add += dmg_add

        # 2) tick end: mana regen applies always (including buff state)
        mana += mana_regen

        # 3) decrement buff
        if buff_remaining > 0:
            buff_remaining -= 1

    total = dmg_basic + dmg_skill1 + dmg_ult_add
    return {"basic": dmg_basic, "skill1": dmg_skill1, "ult_add": dmg_ult_add, "total": total}


def mean_total_damage_15110(
    params_dict: Dict[str, Any],
    ticks: int,
    n_trials: int = 20000,
    seed: Optional[int] = 0,
) -> Dict[str, float]:
    """
    外部から参照するための関数。
    - params_dict: 仕様で指定されたパラメータ辞書
    - ticks: 任意 tick 数
    - n_trials: モンテカルロ試行回数
    - seed: 再現性のための乱数 seed

    返り値:
      - basic: 基本攻撃(基礎分のみ)の平均ダメージ合計
      - skill1: ストライクアウトの平均ダメージ合計
      - ult_add: フィニッシュピッチ + 追加攻撃(add_mult分)の平均ダメージ合計
      - total: 全平均合計
    """
    if n_trials <= 0:
        raise ValueError(f"n_trials must be > 0, got {n_trials}")
    if ticks < 0:
        raise ValueError(f"ticks must be >= 0, got {ticks}")

    params = AceBatmanPitcherParams15110.from_dict(params_dict)
    rng = random.Random(seed)

    sum_basic = 0.0
    sum_skill1 = 0.0
    sum_ult_add = 0.0
    sum_total = 0.0

    for _ in range(n_trials):
        out = simulate_total_damage_15110_once(params, ticks, rng)
        sum_basic += out["basic"]
        sum_skill1 += out["skill1"]
        sum_ult_add += out["ult_add"]
        sum_total += out["total"]

    inv = 1.0 / n_trials
    return sum_basic * inv, sum_skill1 * inv, 0, 0, sum_ult_add * inv
    return {
        "basic": sum_basic * inv,
        "skill1": sum_skill1 * inv,
        "ult_add": sum_ult_add * inv,
        "total": sum_total * inv,
    }


# -----------------------------
# Example usage (remove if not needed)
# -----------------------------
if __name__ == "__main__":
    params = {
        "base_attack_mult": 1.0,
        "skill1_rate": 30,
        "attack_speed": 1.5,
        "attack_power": 1000,
        "skill1_mult": 2.0,
        "crit_rate": 20,
        "crit_dmg": 2.5,
        "ult_mult": 10.0,
        "ult_mana": 20,
        "skill1_react1": 100,
        "skill1_react2": 20,
        "add_rate": 50,
        "add_mult": 0.5,
    }
    print(mean_total_damage_15110(params, ticks=40*60, n_trials=5000, seed=123))

