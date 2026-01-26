#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import random
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple


# Internal action names (requested)
ACTION_BASIC = "basic"
ACTION_SKILL1 = "skill1"  # 投擲
ACTION_SKILL2 = "skill2"  # 排除
ACTION_ULT = "ult"        # 斬首


@dataclass(frozen=True)
class OnigamiNinjaParams:
    # Simulation settings
    tick: int
    trials: int = 20000
    seed: int = 0

    # Rates are percentages (0..100)
    skill2_rate: float = 0.0   # 基本攻撃時に排除へ遷移する確率
    react_rate: float = 0.0    # 排除の再発動確率（失敗するまで継続）
    crit_rate: float = 0.0     # 会心率

    # Multipliers
    base_attack_mult: float = 1.0
    skill1_mult: float = 1.0
    skill2_mult: float = 1.0
    ult_mult: float = 1.0
    crit_dmg: float = 2.0

    # Core stats
    attack_power: float = 0.0
    attack_speed: float = 1.0

    # Skill1 stack
    skill1_stack: int = 999999  # N回basicでskill1発動

    # Mana
    ult_mana: float = 999999.0
    mana_buff: float = 1.0

    def validated(self) -> "OnigamiNinjaParams":
        if self.tick < 0:
            raise ValueError("tick must be >= 0")
        if self.trials <= 0:
            raise ValueError("trials must be > 0")
        if self.attack_speed <= 0:
            raise ValueError("attack_speed must be > 0")
        if self.attack_power < 0:
            raise ValueError("attack_power must be >= 0")
        if self.skill1_stack <= 0:
            raise ValueError("skill1_stack must be >= 1")

        for name, v in [
            ("skill2_rate", self.skill2_rate),
            ("react_rate", self.react_rate),
            ("crit_rate", self.crit_rate),
        ]:
            if not (0.0 <= v <= 100.0):
                raise ValueError(f"{name} must be between 0 and 100")

        if self.crit_dmg < 0:
            raise ValueError("crit_dmg must be >= 0")
        if self.mana_buff < 0:
            raise ValueError("mana_buff must be >= 0")
        if self.ult_mana < 0:
            raise ValueError("ult_mana must be >= 0")

        for name, v in [
            ("base_attack_mult", self.base_attack_mult),
            ("skill1_mult", self.skill1_mult),
            ("skill2_mult", self.skill2_mult),
            ("ult_mult", self.ult_mult),
        ]:
            if v < 0:
                raise ValueError(f"{name} must be >= 0")

        return self


def _roll_percent(rng: random.Random, pct: float) -> bool:
    # True with probability pct%
    return rng.random() * 100.0 < pct


def _apply_crit(rng: random.Random, base_damage: float, crit_rate: float, crit_dmg: float) -> Tuple[float, bool]:
    if base_damage <= 0:
        return 0.0, False
    is_crit = _roll_percent(rng, crit_rate)
    return (base_damage * crit_dmg if is_crit else base_damage), is_crit


def _mana_regen_per_tick(params: OnigamiNinjaParams) -> float:
    # "1tick経過時に 1/attack_speed 回復" に mana_buff を乗算
    return (1.0 / params.attack_speed) * params.mana_buff


def _simulate_once(params: OnigamiNinjaParams, rng: random.Random) -> float:
    tick_limit = params.tick
    used = 0

    total_damage = 0.0
    mana = 0.0
    stack = 0

    mana_regen = _mana_regen_per_tick(params)

    while used < tick_limit:
        # Priority: ult if mana enough
        if mana >= params.ult_mana:
            dmg, _ = _apply_crit(rng, params.attack_power * params.ult_mult, params.crit_rate, params.crit_dmg)
            total_damage += dmg
            mana = 0.0  # ult後0
            # end-of-tick regen
            mana += mana_regen
            used += 1
            continue

        # Priority: skill1 if stack enough
        if stack >= params.skill1_stack:
            dmg, is_crit = _apply_crit(rng, params.attack_power * params.skill1_mult, params.crit_rate, params.crit_dmg)
            total_damage += dmg
            if is_crit:
                mana += 16.0 * params.mana_buff  # skill1 crit => +16 (buff乗算)
            stack = 0
            mana += mana_regen
            used += 1
            continue

        # Otherwise: "基本攻撃時にskill2_rateで排除"
        if _roll_percent(rng, params.skill2_rate):
            # skill2 cast
            dmg, _ = _apply_crit(rng, params.attack_power * params.skill2_mult, params.crit_rate, params.crit_dmg)
            total_damage += dmg
            mana += 4.0 * params.mana_buff  # skill2(含む再発動) => +4 (buff乗算)

            mana += mana_regen
            used += 1

            # Re-activation chain: continue until react fails
            while used < tick_limit and _roll_percent(rng, params.react_rate):
                # At the start of a chained tick, ult can preempt (assumption; see notes below)
                if mana >= params.ult_mana:
                    break

                dmg2, _ = _apply_crit(rng, params.attack_power * params.skill2_mult, params.crit_rate, params.crit_dmg)
                total_damage += dmg2
                mana += 4.0 * params.mana_buff
                mana += mana_regen
                used += 1

            continue

        # basic attack
        dmg, _ = _apply_crit(rng, params.attack_power * params.base_attack_mult, params.crit_rate, params.crit_dmg)
        total_damage += dmg
        stack += 1
        mana += mana_regen
        used += 1

    return total_damage


def mean_total_damage_13007(params: Dict[str, Any], tick: Optional[int] = None, trials: Optional[int] = None,
                           seed: Optional[int] = None) -> float:
    """
    外部参照用: 鬼神忍者(13007)の平均総ダメージを返す（モンテカルロ）

    params dict 必須キー（推奨）:
      - tick (または引数tickで指定)
      - base_attack_mult, skill1_stack, skill2_rate, react_rate
      - attack_speed, attack_power
      - skill1_mult, skill2_mult
      - crit_rate, crit_dmg
      - ult_mult, ult_mana
      - mana_buff

    rate系は 0..100（百分率）
    *_mult, crit_dmg, mana_buff は倍率（2なら2倍）
    """
    # pick values: function args override dict if provided
    merged = dict(params)

    if tick is not None:
        merged["tick"] = tick
    if trials is not None:
        merged["trials"] = trials
    if seed is not None:
        merged["seed"] = seed

    p = OnigamiNinjaParams(
        tick=int(merged["tick"]),
        trials=int(merged.get("trials", 20000)),
        seed=int(merged.get("seed", 0)),

        base_attack_mult=float(merged["base_attack_mult"]),
        skill1_stack=int(merged["skill1_stack"]),
        skill2_rate=float(merged["skill2_rate"]),
        react_rate=float(merged.get("react_rate", 0.0)),

        attack_speed=float(merged["attack_speed"]),
        attack_power=float(merged["attack_power"]),

        skill1_mult=float(merged["skill1_mult"]),
        skill2_mult=float(merged["skill2_mult"]),

        crit_rate=float(merged["crit_rate"]),
        crit_dmg=float(merged["crit_dmg"]),

        ult_mult=float(merged["ult_mult"]),
        ult_mana=float(merged["ult_mana"]),

        mana_buff=float(merged.get("mana_buff", 1.0)),
    ).validated()

    rng = random.Random(p.seed)
    total = 0.0
    for _ in range(p.trials):
        total += _simulate_once(p, rng)
    return total / p.trials


def _build_argparser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="Onigami Ninja DPS/TotalDamage Monte Carlo (ID:13007)")
    ap.add_argument("--tick", type=int, required=True)

    ap.add_argument("--base_attack_mult", type=float, required=True)
    ap.add_argument("--skill1_stack", type=int, required=True)
    ap.add_argument("--skill1_mult", type=float, required=True)

    ap.add_argument("--skill2_rate", type=float, required=True)
    ap.add_argument("--react_rate", type=float, required=True)
    ap.add_argument("--skill2_mult", type=float, required=True)

    ap.add_argument("--attack_speed", type=float, required=True)
    ap.add_argument("--attack_power", type=float, required=True)

    ap.add_argument("--crit_rate", type=float, required=True)
    ap.add_argument("--crit_dmg", type=float, required=True)

    ap.add_argument("--ult_mult", type=float, required=True)
    ap.add_argument("--ult_mana", type=float, required=True)

    ap.add_argument("--mana_buff", type=float, default=1.0)

    ap.add_argument("--trials", type=int, default=20000)
    ap.add_argument("--seed", type=int, default=0)

    ap.add_argument("--print_dps", action="store_true", help="平均DPS(=平均総ダメ/ tick)も表示")
    return ap


def main() -> None:
    ap = _build_argparser()
    args = ap.parse_args()

    params = {
        "tick": args.tick,
        "base_attack_mult": args.base_attack_mult,
        "skill1_stack": args.skill1_stack,
        "skill1_mult": args.skill1_mult,

        "skill2_rate": args.skill2_rate,
        "react_rate": args.react_rate,
        "skill2_mult": args.skill2_mult,

        "attack_speed": args.attack_speed,
        "attack_power": args.attack_power,

        "crit_rate": args.crit_rate,
        "crit_dmg": args.crit_dmg,

        "ult_mult": args.ult_mult,
        "ult_mana": args.ult_mana,

        "mana_buff": args.mana_buff,

        "trials": args.trials,
        "seed": args.seed,
    }

    mean_dmg = mean_total_damage_13007(params)
    print(f"mean_total_damage={mean_dmg:.6f}")
    if args.print_dps:
        dps = mean_dmg / args.tick if args.tick > 0 else 0.0
        print(f"mean_dps={dps:.6f}")


if __name__ == "__main__":
    main()

