from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, List, Tuple
import argparse
import math
import random


@dataclass(frozen=True)
class WattParams5013:
    attack_power: float
    attack_speed: float  # 現仕様では計算に未使用（最後に曖昧点として指摘）
    watt_stack: int
    tick: int
    buff_mult: float
    ult_mult: float
    cirt_rate: float  # 0..100 (%)
    cirt_dmg: float   # 2 -> 2x, 150 -> 150x


def _validate_params(p: WattParams5013) -> None:
    if p.watt_stack < 0:
        raise ValueError("watt_stack must be >= 0")
    if p.tick < 0:
        raise ValueError("tick must be >= 0")
    if not (0.0 <= p.cirt_rate <= 100.0):
        raise ValueError("cirt_rate must be in [0, 100]")
    # 係数類はゲーム仕様次第だが、通常は負にならないはずなので最低限チェック
    if p.attack_power < 0:
        raise ValueError("attack_power must be >= 0")
    if p.ult_mult < 0:
        raise ValueError("ult_mult must be >= 0")
    if p.cirt_dmg < 0:
        raise ValueError("cirt_dmg must be >= 0")
    # buff_mult はマイナスも理論上可能だが、想定外ならここで弾ける
    # if p.buff_mult < 0: raise ValueError("buff_mult must be >= 0")


def _num_attacks(p: WattParams5013) -> int:
    # tick 回行動を試みるが、スタックが尽きたら以降ダメージ0（行動しない）
    return min(p.tick, p.watt_stack)


def _base_damage_for_stack(p: WattParams5013, current_stack: int) -> float:
    # 仕様に忠実に：damage = attack_power * (1 + watt_stack * buff_mult) * ult_mult
    # current_stack はその攻撃時点の watt_stack を使う（後述の曖昧点）
    return p.attack_power * (1.0 + current_stack * p.buff_mult) * p.ult_mult


def expected_total_damage(p: WattParams5013) -> Tuple[float, float]:
    """
    会心を含む総ダメージの期待値と標準偏差（各攻撃の会心が独立と仮定）を返す。
    """
    _validate_params(p)

    n = _num_attacks(p)
    if n <= 0:
        return 0.0, 0.0

    pr = p.cirt_rate / 100.0
    # 1 or cirt_dmg の二点分布
    e_mult = (1.0 - pr) * 1.0 + pr * p.cirt_dmg
    e_mult2 = (1.0 - pr) * 1.0 * 1.0 + pr * (p.cirt_dmg * p.cirt_dmg)
    var_mult = e_mult2 - e_mult * e_mult

    total_mean = 0.0
    total_var = 0.0

    # 攻撃ごとにスタックが 1 ずつ減る想定（「攻撃時点のスタック」を使う）
    # 例: watt_stack=5, tick>=5 のとき stack: 5,4,3,2,1 で攻撃
    for i in range(n):
        current_stack = p.watt_stack - i
        base = _base_damage_for_stack(p, current_stack)
        total_mean += base * e_mult
        total_var += (base * base) * var_mult  # 独立のため和

    total_std = math.sqrt(max(0.0, total_var))
    return total_mean, total_std


def simulate_total_damage(
    p: WattParams5013,
    trials: int,
    seed: Optional[int] = None
) -> Dict[str, float]:
    """
    モンテカルロで総ダメージを推定（会心の乱数部分を実際に振る）。
    """
    _validate_params(p)
    if trials <= 0:
        raise ValueError("trials must be >= 1")

    rng = random.Random(seed)
    n = _num_attacks(p)
    pr = p.cirt_rate / 100.0

    samples: List[float] = []
    for _ in range(trials):
        total = 0.0
        for i in range(n):
            current_stack = p.watt_stack - i
            base = _base_damage_for_stack(p, current_stack)
            if rng.random() < pr:
                total += base * p.cirt_dmg
            else:
                total += base
        samples.append(total)

    samples.sort()
    mean = sum(samples) / trials
    # 不偏分散でなく母分散寄りの簡易（用途的に十分）
    var = sum((x - mean) ** 2 for x in samples) / trials
    std = math.sqrt(var)

    def pct(q: float) -> float:
        # q in [0,1]
        if trials == 1:
            return samples[0]
        idx = int(round(q * (trials - 1)))
        idx = max(0, min(trials - 1, idx))
        return samples[idx]

    return {
        "mean": mean,
        "std": std,
        "p05": pct(0.05),
        "p50": pct(0.50),
        "p95": pct(0.95),
        "min": samples[0],
        "max": samples[-1],
    }


def mean_total_damage_5013(options: Dict[str, Any]) -> float:
    """
    外部から「期待値の総ダメージ」だけ欲しいとき用。

    options例:
      {
        "attack_power": 100000,
        "attack_speed": 1.5,
        "watt_stack": 20,
        "tick": 30,
        "buff_mult": 0.05,
        "ult_mult": 2,
        "cirt_rate": 20,
        "cirt_dmg": 2.5
      }
    """
    p = WattParams5013(
        attack_power=float(options["attack_power"]),
        attack_speed=float(options["attack_speed"]),
        watt_stack=int(options["watt_stack"]),
        tick=int(options["tick"]),
        buff_mult=float(options["buff_mult"]),
        ult_mult=float(options["ult_mult"]),
        cirt_rate=float(options["cirt_rate"]),
        cirt_dmg=float(options["cirt_dmg"]),
    )
    mean, _std = expected_total_damage(p)
    return mean


def main() -> None:
    ap = argparse.ArgumentParser(description="Watt(5013) total damage calculator (expected value + optional MC).")
    ap.add_argument("--attack_power", type=float, required=True)
    ap.add_argument("--attack_speed", type=float, required=True)
    ap.add_argument("--watt_stack", type=int, required=True)
    ap.add_argument("--tick", type=int, required=True)
    ap.add_argument("--buff_mult", type=float, required=True)
    ap.add_argument("--ult_mult", type=float, required=True)
    ap.add_argument("--cirt_rate", type=float, required=True)
    ap.add_argument("--cirt_dmg", type=float, required=True)

    ap.add_argument("--trials", type=int, default=0, help="If > 0, run Monte Carlo simulation for validation.")
    ap.add_argument("--seed", type=int, default=None)

    args = ap.parse_args()

    p = WattParams5013(
        attack_power=args.attack_power,
        attack_speed=args.attack_speed,
        watt_stack=args.watt_stack,
        tick=args.tick,
        buff_mult=args.buff_mult,
        ult_mult=args.ult_mult,
        cirt_rate=args.cirt_rate,
        cirt_dmg=args.cirt_dmg,
    )

    mean, std = expected_total_damage(p)
    n = _num_attacks(p)

    print("=== Watt(5013) Total Damage ===")
    print(f"effective_attacks = {n} (min(tick, watt_stack))")
    print(f"expected_total_damage = {mean:.6f}")
    print(f"expected_std (crit randomness only) = {std:.6f}")

    if args.trials and args.trials > 0:
        mc = simulate_total_damage(p, trials=args.trials, seed=args.seed)
        print("\n--- Monte Carlo (validation) ---")
        print(f"trials = {args.trials}, seed = {args.seed}")
        print(f"mc_mean = {mc['mean']:.6f}")
        print(f"mc_std  = {mc['std']:.6f}")
        print(f"p05={mc['p05']:.6f}  p50={mc['p50']:.6f}  p95={mc['p95']:.6f}")
        print(f"min={mc['min']:.6f}  max={mc['max']:.6f}")


if __name__ == "__main__":
    main()

