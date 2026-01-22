#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional
import argparse
import random
import math


@dataclass(frozen=True)
class WattParams5013:
    # 入力
    attack_power: float
    attack_speed: float  # 仕様上は引数として受け取るが、本モデルでは未使用
    watt_stack: int
    tick: int
    buff_mult: float     # 仕様上は引数として受け取るが、本モデルでは未使用
    ult_mult: float
    cirt_rate: float     # 0..100 (%)
    cirt_dmg: float      # 倍率 (2.5なら2.5倍、150なら150倍)

    def validate(self) -> None:
        if self.attack_power < 0:
            raise ValueError("attack_power must be >= 0")
        if self.attack_speed <= 0:
            raise ValueError("attack_speed must be > 0")
        if self.watt_stack < 0:
            raise ValueError("watt_stack must be >= 0")
        if self.tick < 0:
            raise ValueError("tick must be >= 0")
        if self.ult_mult < 0:
            raise ValueError("ult_mult must be >= 0")
        if not (0.0 <= self.cirt_rate <= 100.0):
            raise ValueError("cirt_rate must be in [0, 100]")
        if self.cirt_dmg < 0:
            raise ValueError("cirt_dmg must be >= 0")


def num_attacks(params: WattParams5013) -> int:
    # tick回攻撃したいが、スタックが尽きたら行動しない
    return min(params.tick, params.watt_stack)


def mean_total_damage(params: WattParams5013) -> float:
    """
    期待値（平均）の総ダメージを解析的に返す。
    1回攻撃の基礎ダメージ: attack_power * ult_mult
    クリティカル: cirt_rate(%) の確率で cirt_dmg 倍
    """
    params.validate()
    n = num_attacks(params)
    base = params.attack_power * params.ult_mult

    p = params.cirt_rate / 100.0
    expected_mult = (1.0 - p) + p * params.cirt_dmg  # = 1 + p*(cirt_dmg-1)

    return n * base * expected_mult


def sample_total_damage_once(params: WattParams5013, rng: random.Random) -> float:
    """
    乱数により1回分の総ダメージ（実現値）を返す。
    """
    params.validate()
    n = num_attacks(params)
    base = params.attack_power * params.ult_mult
    p = params.cirt_rate / 100.0

    total = 0.0
    for _ in range(n):
        if rng.random() < p:
            total += base * params.cirt_dmg
        else:
            total += base
    return total


def monte_carlo_mean(params: WattParams5013, trials: int, seed: Optional[int] = None) -> Dict[str, float]:
    """
    モンテカルロで平均などを推定（任意機能）。
    """
    if trials <= 0:
        raise ValueError("trials must be > 0")

    rng = random.Random(seed)
    values = [sample_total_damage_once(params, rng) for _ in range(trials)]
    m = sum(values) / trials
    v = sum((x - m) ** 2 for x in values) / trials
    return {
        "mean": m,
        "std": math.sqrt(v),
        "min": min(values),
        "max": max(values),
    }


def mean_total_damage_5013(options: Dict[str, Any]) -> float:
    """
    外部から「平均総ダメージ」だけ取りたい用。
    options例:
      {
        "attack_power": 100000,
        "attack_speed": 1.5,
        "watt_stack": 30,
        "tick": 20,
        "buff_mult": 0.05,
        "ult_mult": 2.0,
        "cirt_rate": 20,
        "cirt_dmg": 2.5,
      }
    """
    params = WattParams5013(
        attack_power=float(options["attack_power"]),
        attack_speed=float(options["attack_speed"]),
        watt_stack=int(options["watt_stack"]),
        tick=int(options["tick"]),
        buff_mult=float(options["buff_mult"]),
        ult_mult=float(options["ult_mult"]),
        cirt_rate=float(options["cirt_rate"]),
        cirt_dmg=float(options["cirt_dmg"]),
    )
    return mean_total_damage(params)


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Watt (5013) total damage calculator")
    p.add_argument("--attack-power", type=float, required=True)
    p.add_argument("--attack-speed", type=float, required=True)
    p.add_argument("--watt-stack", type=int, required=True)
    p.add_argument("--tick", type=int, required=True)
    p.add_argument("--buff-mult", type=float, required=True)
    p.add_argument("--ult-mult", type=float, required=True)
    p.add_argument("--cirt-rate", type=float, required=True)
    p.add_argument("--cirt-dmg", type=float, required=True)

    # 任意
    p.add_argument("--sample", action="store_true", help="乱数で1回分の総ダメージ(実現値)も表示")
    p.add_argument("--seed", type=int, default=1, help="乱数シード (sample/monte-carlo用)")
    p.add_argument("--monte-carlo", action="store_true", help="モンテカルロ推定も表示")
    p.add_argument("--trials", type=int, default=10000, help="モンテカルロ試行回数")
    return p


def main() -> None:
    args = build_arg_parser().parse_args()

    params = WattParams5013(
        attack_power=args.attack_power,
        attack_speed=args.attack_speed,
        watt_stack=args.watt_stack,
        tick=args.tick,
        buff_mult=args.buff_mult,
        ult_mult=args.ult_mult,
        cirt_rate=args.cirt_rate,
        cirt_dmg=args.cirt_dmg,
    )

    n = num_attacks(params)
    mean_dmg = mean_total_damage(params)

    print(f"attacks={n} (min(tick, watt_stack))")
    print(f"mean_total_damage={mean_dmg}")

    if args.sample:
        rng = random.Random(args.seed)
        one = sample_total_damage_once(params, rng)
        print(f"sample_total_damage(seed={args.seed})={one}")

    if args.monte_carlo:
        stats = monte_carlo_mean(params, trials=args.trials, seed=args.seed)
        print(f"monte_carlo(trials={args.trials}, seed={args.seed}) mean={stats['mean']} std={stats['std']} min={stats['min']} max={stats['max']}")


if __name__ == "__main__":
    main()

