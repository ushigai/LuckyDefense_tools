#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import random
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple


@dataclass(frozen=True)
class MasterKunParams5018:
    tick: int

    attack_power: float
    attack_speed: float

    base_attack_mult: float
    skill1_mult: float
    skill2_mult: float

    skill1_rate: float  # percent 0..100
    skill2_rate: float  # percent 0..100
    skill3_rate: float  # percent 0..100 (NOTE: 未定義のため 0 を要求)

    crit_rate: float    # percent 0..100
    crit_dmg: float     # multiplier (e.g., 2.5)

    skill1_interval: float

    n_iter: int = 20000
    seed: Optional[int] = None

    def validated(self) -> "MasterKunParams5018":
        if self.tick < 0:
            raise ValueError("tick must be >= 0")
        if self.attack_power < 0:
            raise ValueError("attack_power must be >= 0")
        if self.attack_speed <= 0:
            raise ValueError("attack_speed must be > 0")

        for name, v in [
            ("base_attack_mult", self.base_attack_mult),
            ("skill1_mult", self.skill1_mult),
            ("skill2_mult", self.skill2_mult),
            ("crit_dmg", self.crit_dmg),
        ]:
            if v < 0:
                raise ValueError(f"{name} must be >= 0")

        for name, v in [
            ("skill1_rate", self.skill1_rate),
            ("skill2_rate", self.skill2_rate),
            ("skill3_rate", self.skill3_rate),
            ("crit_rate", self.crit_rate),
        ]:
            if not (0 <= v <= 100):
                raise ValueError(f"{name} must be in [0, 100]")

        # 本文の状態遷移が skill1/skill2 のみなので、それに合わせる
        if self.skill3_rate != 0:
            raise ValueError(
                "skill3_rate is provided but 'skill3' behavior/damage is not defined in the spec. "
                "Set skill3_rate=0 for now (or define skill3's damage model)."
            )

        if self.skill1_rate + self.skill2_rate > 100:
            raise ValueError("skill1_rate + skill2_rate must be <= 100")

        if self.skill1_interval <= 0:
            raise ValueError("skill1_interval must be > 0")

        if self.n_iter <= 0:
            raise ValueError("n_iter must be > 0")

        return self


def _roll_crit(rng: random.Random, crit_rate_percent: float, crit_dmg: float, base_damage: float) -> float:
    """1回のダメージイベントに対して会心判定"""
    if base_damage <= 0:
        return 0.0
    if rng.random() < (crit_rate_percent / 100.0):
        return base_damage * crit_dmg
    return base_damage


def _choose_action_basic_skill1_skill2(
    rng: random.Random, skill1_rate: float, skill2_rate: float
) -> str:
    """
    1tickにおける行動選択:
      basic: 100 - skill1_rate - skill2_rate
      skill1: skill1_rate
      skill2: skill2_rate
    """
    u = rng.random() * 100.0
    if u < skill1_rate:
        return "skill1"
    if u < skill1_rate + skill2_rate:
        return "skill2"
    return "basic"


def simulate_total_damage_once_5018(p: MasterKunParams5018, rng: random.Random) -> float:
    """
    1試行分の総ダメージをシミュレーションして返す。
    - 各tickで basic/skill1/skill2 のいずれかを実行（skill1/skill2は基本攻撃の置き換え）
    - skill1（回転炎）は DoT を発生させ、効果時間は attack_speed*10 tick
      途中で再発動した場合は「同時発動せず効果時間をリセット」
    - DoT の 1tick ダメージは:
        attack_power * (skill1_mult / (attack_speed * skill1_interval))
      ※ attack_speed*10 tick 継続するので、理想的な総量は attack_power * skill1_mult * 10 / skill1_interval
    - 会心は「各ダメージイベント」ごとに独立判定（DoTも毎tick判定）
    """
    total = 0.0

    # DoT の残り時間（tick単位、floatで保持して端数にも対応）
    dot_remaining = 0.0

    # 事前計算
    dot_duration = p.attack_speed * 10.0
    dot_per_full_tick = p.attack_power * (p.skill1_mult / (p.attack_speed * p.skill1_interval))

    basic_damage_base = p.attack_power * p.base_attack_mult
    skill2_damage_base = p.attack_power * p.skill2_mult

    for _ in range(p.tick):
        action = _choose_action_basic_skill1_skill2(rng, p.skill1_rate, p.skill2_rate)

        # 行動による直接ダメージ or DoT更新
        if action == "basic":
            total += _roll_crit(rng, p.crit_rate, p.crit_dmg, basic_damage_base)
        elif action == "skill2":
            total += _roll_crit(rng, p.crit_rate, p.crit_dmg, skill2_damage_base)
        elif action == "skill1":
            # 効果時間をリセット（スタックしない）
            dot_remaining = dot_duration
        else:
            raise RuntimeError(f"Unknown action: {action}")

        # DoTダメージ（このtickにおける継続ダメージ）
        # 端数tickを許容するため、dot_remaining が 0<.. <1 の場合は partial で比例配分
        if dot_remaining > 0.0 and dot_per_full_tick > 0.0:
            active = 1.0 if dot_remaining >= 1.0 else dot_remaining  # 0~1
            dot_damage = dot_per_full_tick * active
            total += _roll_crit(rng, p.crit_rate, p.crit_dmg, dot_damage)

        dot_remaining -= 1.0

    return total


def simulate_damage_breakdown_once_5018(p: MasterKunParams5018, rng: random.Random) -> Tuple[float, float, float, float, float]:
    """
    1試行分のダメージ内訳を返す。
    戻り値: (basic, skill1, skill2, skill3, ult)
      - skill1 は DoT の継続ダメージとして skill1 に計上
      - このキャラは skill3/ult を持たないため 0.0
    """
    dmg_basic = 0.0
    dmg_skill1 = 0.0
    dmg_skill2 = 0.0

    dot_remaining = 0.0

    dot_duration = p.attack_speed * 10.0
    dot_per_full_tick = p.attack_power * (p.skill1_mult / (p.attack_speed * p.skill1_interval))

    basic_damage_base = p.attack_power * p.base_attack_mult
    skill2_damage_base = p.attack_power * p.skill2_mult

    for _ in range(p.tick):
        action = _choose_action_basic_skill1_skill2(rng, p.skill1_rate, p.skill2_rate)

        if action == "basic":
            dmg_basic += _roll_crit(rng, p.crit_rate, p.crit_dmg, basic_damage_base)
        elif action == "skill2":
            dmg_skill2 += _roll_crit(rng, p.crit_rate, p.crit_dmg, skill2_damage_base)
        elif action == "skill1":
            dot_remaining = dot_duration
        else:
            raise RuntimeError(f"Unknown action: {action}")

        if dot_remaining > 0.0 and dot_per_full_tick > 0.0:
            active = 1.0 if dot_remaining >= 1.0 else dot_remaining
            dot_damage = dot_per_full_tick * active
            dmg_skill1 += _roll_crit(rng, p.crit_rate, p.crit_dmg, dot_damage)

        dot_remaining -= 1.0

    return dmg_basic, dmg_skill1, dmg_skill2, 0.0, 0.0

def mean_total_damage_5018(params: Dict[str, Any]) -> Tuple[float, float, float, float, float]:
    """
    外部から参照する用:
      params(dict) を受け取り、モンテカルロ平均の総ダメージ内訳を返す。

    戻り値: (basic, skill1, skill2, skill3, ult)
      - skill3/ult は存在しないため 0.0
    """
    p = MasterKunParams5018(**params).validated()
    rng = random.Random(p.seed)

    s_basic = s_s1 = s_s2 = s_s3 = s_ult = 0.0
    for _ in range(p.n_iter):
        b, s1, s2, s3, u = simulate_damage_breakdown_once_5018(p, rng)
        s_basic += b
        s_s1 += s1
        s_s2 += s2
        s_s3 += s3
        s_ult += u

    inv = 1.0 / float(p.n_iter)
    return s_basic * inv, s_s1 * inv, s_s2 * inv, s_s3 * inv, s_ult * inv

def mean_dps_5018(params: Dict[str, Any]) -> float:
    """平均DPS（= 平均総ダメージ / tick）"""
    tick = int(params["tick"])
    if tick <= 0:
        return 0.0
    b, s1, s2, s3, u = mean_total_damage_5018(params)
    total = b + s1 + s2 + s3 + u
    return total / tick

def _build_arg_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="MasterKun(5018) Monte Carlo damage/DPS simulator")

    ap.add_argument("--tick", type=int, required=True)

    ap.add_argument("--attack_power", type=float, required=True)
    ap.add_argument("--attack_speed", type=float, required=True)

    ap.add_argument("--base_attack_mult", type=float, required=True)
    ap.add_argument("--skill1_mult", type=float, required=True)
    ap.add_argument("--skill2_mult", type=float, required=True)

    ap.add_argument("--skill1_rate", type=float, required=True)
    ap.add_argument("--skill2_rate", type=float, required=True)
    ap.add_argument("--skill3_rate", type=float, default=0.0)

    ap.add_argument("--crit_rate", type=float, required=True)
    ap.add_argument("--crit_dmg", type=float, required=True)

    ap.add_argument("--skill1_interval", type=float, required=True)

    ap.add_argument("--n_iter", type=int, default=20000)
    ap.add_argument("--seed", type=int, default=None)

    return ap


def main() -> None:
    ap = _build_arg_parser()
    a = ap.parse_args()

    params = vars(a)
    b, s1, s2, s3, u = mean_total_damage_5018(params)
    mean_total = b + s1 + s2 + s3 + u
    dps = mean_total / params["tick"] if params["tick"] > 0 else 0.0

    print(f"mean_total_damage = {mean_total:.6f}")
    print(f"mean_dps          = {dps:.6f}")


if __name__ == "__main__":
    main()

