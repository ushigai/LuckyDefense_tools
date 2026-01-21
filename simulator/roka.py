#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple
import argparse
import random
import math


# 仕様の曖昧ポイント（本文末にも整理）
AMBIGUITIES = [
    "tick→現実時間(秒)の対応が明示されていない（ここでは DPS=damage/tick として出力）",
    "爆弾装填が最初に発生するタイミング（実装: tick=int(attack_speed*10) で初回装填）",
    "爆弾装填(1tick)中もマナ回復(1/attack_speed)は入るか（実装: 入る）",
    "「連射(skill2)」はスタック増加/爆弾消費を伴うか（実装: 伴わない、ダメージ0でtick延長のみ）",
    "爆弾付き基本攻撃(skill1)はスタック増加に含むか（実装: 含む）",
    "貫通弾(skill3)発動後のスタック挙動（実装: 0にリセット）",
]


@dataclass(frozen=True)
class RokaParams5023:
    attack_power: float
    attack_speed: float

    # multipliers (2 -> 2x, 150 -> 150x)
    skill1_mult: float  # 爆弾追加分：attack_power*(1 + skill1_mult)
    skill2_mult: float  # 連射によるtick延長に使用
    skill3_mult: float  # 貫通弾倍率
    ult_mult: float     # ヘッドショット倍率

    # rates are percent 0..100
    skill2_rate: float  # 連射発動率
    crit_rate: float    # 会心率
    bomb_rate: float    # 5個装填率

    crit_dmg: float     # 会心ダメージ倍率
    ult_mana: float      # ult発動マナ閾値


def _pct(p: float) -> float:
    return max(0.0, min(1.0, p / 100.0))


def _roll_bomb_load(rng: random.Random, bomb_rate_pct: float) -> int:
    """
    1) bomb_rate% で 5個
    2) 外れたら 1..5 完全ランダム(一様)
    """
    if rng.random() < _pct(bomb_rate_pct):
        return 5
    return rng.randint(1, 5)


def _apply_crit(rng: random.Random, base_damage: float, crit_rate_pct: float, crit_dmg: float) -> float:
    if base_damage <= 0:
        return 0.0
    if rng.random() < _pct(crit_rate_pct):
        return base_damage * crit_dmg
    return base_damage


def simulate_total_damage_5023(
    params: RokaParams5023,
    ticks: float,
    rng: random.Random,
) -> Tuple[float, float]:
    """
    1試行ぶんのシミュレーション。
    戻り値: (total_damage, effective_ticks)
      - effective_ticks は skill2(連射) による延長込みの最終計測tick(浮動小数)
    """
    # 状態
    t: int = 0
    end_tick: float = float(ticks)

    mana: float = 0.0
    stacks: int = 0
    bombs: int = 0

    # 爆弾装填間隔
    reload_interval: int = int(params.attack_speed * 10)
    if reload_interval < 1:
        reload_interval = 1

    next_reload_tick: int = reload_interval  # 実装: 初回は interval 到達時に装填
    total_damage: float = 0.0

    while t < end_tick:
        action: str = "none"
        damage: float = 0.0

        # --- 爆弾装填 tick (1tick消費) ---
        if t == next_reload_tick:
            action = "reload"
            bombs = _roll_bomb_load(rng, params.bomb_rate)
            next_reload_tick += reload_interval
            # ダメージなし、スタック変化なし

        else:
            # --- 行動決定 (優先順位: ult > skill1 > skill2 > skill3 > basic) ---
            if mana >= params.ult_mana:
                action = "ult"
                damage = params.attack_power * params.ult_mult
                # ultは会心率50%固定
                damage = _apply_crit(rng, damage, 50.0, params.crit_dmg)
                mana = 0.0

            elif bombs > 0:
                action = "skill1"  # 爆弾付き基本攻撃
                bombs -= 1
                damage = params.attack_power * (1.0 + params.skill1_mult)
                damage = _apply_crit(rng, damage, params.crit_rate, params.crit_dmg)
                stacks += 1  # 基本攻撃扱いでスタック獲得

            else:
                # skill2 は「基本攻撃時 skill2_rate%」だが、ここでは bombs/ult がない状況で基本攻撃候補になるので判定
                if rng.random() < _pct(params.skill2_rate):
                    action = "skill2"
                    # ダメージなし、tick延長のみ（丸めなし）
                    extension = params.attack_speed * params.skill2_mult * (1.0 - 1.0 / params.attack_speed)
                    end_tick += extension

                elif stacks >= 15:
                    action = "skill3"
                    damage = params.attack_power * params.skill3_mult
                    damage = _apply_crit(rng, damage, params.crit_rate, params.crit_dmg)
                    stacks = 0

                else:
                    action = "basic"
                    damage = params.attack_power
                    damage = _apply_crit(rng, damage, params.crit_rate, params.crit_dmg)
                    stacks += 1

        total_damage += damage

        # --- tick末尾 マナ回復 ---
        mana += 1.0 / params.attack_speed

        t += 1

    return total_damage, end_tick


def mean_total_damage_5023(options: Dict[str, Any]) -> float:
    """
    外部から「平均総ダメージ」だけ取りたい用。
    options例:
      {
        "attack_power": 100000,
        "attack_speed": 1.5,
        "skill1_mult": 2,
        "skill2_mult": 10,
        "skill2_rate": 20,
        "skill3_mult": 8,
        "ult_mult": 50,
        "ult_mana": 190,
        "crit_rate": 20,
        "crit_dmg": 2.5,
        "bomb_rate": 30,
        "ticks": 600,
        "trials": 10000,
        "seed": 1
      }
    """
    # 互換キー（過去の綴り揺れ吸収）
    crit_rate = options.get("crit_rate", options.get("cirt_rate"))
    crit_dmg = options.get("crit_dmg", options.get("cirt_dmg"))

    params = RokaParams5023(
        attack_power=float(options["attack_power"]),
        attack_speed=float(options["attack_speed"]),
        skill1_mult=float(options["skill1_mult"]),
        skill2_mult=float(options["skill2_mult"]),
        skill3_mult=float(options["skill3_mult"]),
        ult_mult=float(options["ult_mult"]),
        skill2_rate=float(options["skill2_rate"]),
        crit_rate=float(crit_rate),
        crit_dmg=float(crit_dmg),
        bomb_rate=float(options["bomb_rate"]),
        ult_mana=float(options["ult_mana"]),
    )

    ticks = float(options.get("ticks", options.get("durationSec")))
    if ticks is None:
        raise ValueError("options に ticks (推奨) もしくは durationSec を指定してください。")

    trials = int(options.get("trials", 10000))
    seed = options.get("seed", None)
    rng = random.Random(seed)

    s = 0.0
    for _ in range(trials):
        dmg, _end = simulate_total_damage_5023(params=params, ticks=ticks, rng=rng)
        s += dmg
    return s / trials


def _main() -> None:
    ap = argparse.ArgumentParser(description="Roka(5023) Monte-Carlo damage simulator (tick-based)")
    ap.add_argument("--attack_power", type=float, required=True)
    ap.add_argument("--attack_speed", type=float, required=True)

    ap.add_argument("--skill1_mult", type=float, required=True)
    ap.add_argument("--skill2_mult", type=float, required=True)
    ap.add_argument("--skill2_rate", type=float, required=True)
    ap.add_argument("--skill3_mult", type=float, required=True)
    ap.add_argument("--ult_mult", type=float, required=True)
    ap.add_argument("--ult_mana", type=float, required=True)

    ap.add_argument("--crit_rate", type=float, required=True)
    ap.add_argument("--crit_dmg", type=float, required=True)
    ap.add_argument("--bomb_rate", type=float, required=True)

    ap.add_argument("--ticks", type=float, required=True, help="計測tick数（skill2で延長され得る）")
    ap.add_argument("--trials", type=int, default=10000)
    ap.add_argument("--seed", type=int, default=1)

    args = ap.parse_args()

    params = RokaParams5023(
        attack_power=args.attack_power,
        attack_speed=args.attack_speed,
        skill1_mult=args.skill1_mult,
        skill2_mult=args.skill2_mult,
        skill3_mult=args.skill3_mult,
        ult_mult=args.ult_mult,
        skill2_rate=args.skill2_rate,
        crit_rate=args.crit_rate,
        crit_dmg=args.crit_dmg,
        bomb_rate=args.bomb_rate,
        ult_mana=args.ult_mana,
    )

    rng = random.Random(args.seed)

    total_list = []
    dps_list = []
    end_list = []

    for _ in range(args.trials):
        total, end_tick = simulate_total_damage_5023(params=params, ticks=args.ticks, rng=rng)
        total_list.append(total)
        end_list.append(end_tick)
        dps_list.append(total / end_tick if end_tick > 0 else 0.0)

    mean_total = sum(total_list) / len(total_list)
    mean_end = sum(end_list) / len(end_list)
    mean_dps = sum(dps_list) / len(dps_list)

    # 参考: ばらつき（標準偏差）
    def _std(xs):
        m = sum(xs) / len(xs)
        v = sum((x - m) ** 2 for x in xs) / max(1, (len(xs) - 1))
        return math.sqrt(v)

    print("== Roka(5023) Monte-Carlo ==")
    print(f"trials={args.trials} seed={args.seed}")
    print(f"base_ticks={args.ticks}")
    print(f"mean_effective_ticks={mean_end:.6f}")
    print(f"mean_total_damage={mean_total:.6f}")
    print(f"mean_DPS(damage/tick)={mean_dps:.6f}")
    print(f"std_total_damage={_std(total_list):.6f}")
    print(f"std_DPS={_std(dps_list):.6f}")

    print("\n[Ambiguities implemented as assumptions]")
    for a in AMBIGUITIES:
        print(f"- {a}")


if __name__ == "__main__":
    _main()

