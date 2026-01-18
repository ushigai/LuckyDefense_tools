#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations
import argparse
from dataclasses import dataclass
from typing import Any, Dict, Optional, Union


@dataclass(frozen=True)
class WattParams:
    watt_stack: int
    tick: int
    attack_speed: float
    attack_power: float
    buff_mult: float
    ult_mult: float
    cirt_rate: float  # 0~100 (percent)
    cirt_dmg: float   # multiplier (e.g., 2.5)

    def validated(self) -> "WattParams":
        if self.watt_stack < 0:
            raise ValueError("watt_stack must be >= 0")
        if self.tick < 0:
            raise ValueError("tick must be >= 0")
        if self.attack_speed <= 0:
            raise ValueError("attack_speed must be > 0")
        if self.attack_power < 0:
            raise ValueError("attack_power must be >= 0")
        if self.ult_mult < 0:
            raise ValueError("ult_mult must be >= 0")
        if self.cirt_dmg < 0:
            raise ValueError("cirt_dmg must be >= 0")
        # cirt_rate は多少の入力ブレを許容して clamp する
        return self


def _clamp(x: float, lo: float, hi: float) -> float:
    return lo if x < lo else hi if x > hi else x


def mean_total_damage_5013(
    watt_stack: Optional[int] = None,
    tick: Optional[int] = None,
    attack_speed: Optional[float] = None,
    attack_power: Optional[float] = None,
    buff_mult: Optional[float] = None,
    ult_mult: Optional[float] = None,
    cirt_rate: Optional[float] = None,
    cirt_dmg: Optional[float] = None,
    *,
    options: Optional[Dict[str, Any]] = None,
    # 重要な曖昧点：スタックを「消費前」の値で参照するか
    stack_is_before_consume: bool = True,
) -> float:
    """
    ワット(5013)の期待総ダメージ（会心込みの平均）を返す。

    使い方:
      - 直接引数で渡す
      - options=dict でまとめて渡す（外部呼び出し用）

    stack_is_before_consume=True のとき:
      1発目は current_stack = watt_stack で計算し、その後 1 消費する想定。
      （つまりスタック値は s, s-1, s-2, ...）
    """
    if options is not None:
        # options優先（不足は direct arg にフォールバック）
        def pick(key: str, cur: Any) -> Any:
            return options.get(key, cur)

        watt_stack = pick("watt_stack", watt_stack)
        tick = pick("tick", tick)
        attack_speed = pick("attack_speed", attack_speed)
        attack_power = pick("attack_power", attack_power)
        buff_mult = pick("buff_mult", buff_mult)
        ult_mult = pick("ult_mult", ult_mult)
        cirt_rate = pick("cirt_rate", cirt_rate)
        cirt_dmg = pick("cirt_dmg", cirt_dmg)

    # 必須チェック
    missing = [k for k, v in {
        "watt_stack": watt_stack,
        "tick": tick,
        "attack_speed": attack_speed,
        "attack_power": attack_power,
        "buff_mult": buff_mult,
        "ult_mult": ult_mult,
        "cirt_rate": cirt_rate,
        "cirt_dmg": cirt_dmg,
    }.items() if v is None]
    if missing:
        raise ValueError(f"Missing required params: {', '.join(missing)}")

    p = WattParams(
        watt_stack=int(watt_stack),  # type: ignore[arg-type]
        tick=int(tick),              # type: ignore[arg-type]
        attack_speed=float(attack_speed),  # type: ignore[arg-type]
        attack_power=float(attack_power),  # type: ignore[arg-type]
        buff_mult=float(buff_mult),        # type: ignore[arg-type]
        ult_mult=float(ult_mult),          # type: ignore[arg-type]
        cirt_rate=float(cirt_rate),        # type: ignore[arg-type]
        cirt_dmg=float(cirt_dmg),          # type: ignore[arg-type]
    ).validated()

    n = min(p.tick, p.watt_stack)
    if n <= 0:
        return 0.0

    # 会心の期待倍率
    crit_p = _clamp(p.cirt_rate / 100.0, 0.0, 1.0)
    expected_crit_mult = (1.0 - crit_p) + (crit_p * p.cirt_dmg)

    # 各攻撃の stack 値列
    # before_consume: s, s-1, ..., s-n+1
    # after_consume : s-1, s-2, ..., s-n
    s = p.watt_stack
    if stack_is_before_consume:
        first = s - (n - 1)
        last = s
    else:
        first = s - n
        last = s - 1

    # sum_{k=first..last} (1 + k*buff_mult) = n + buff_mult * sum k
    sum_k = n * (first + last) / 2.0
    sum_term = n + (p.buff_mult * sum_k)

    total = p.attack_power * p.ult_mult * expected_crit_mult * sum_term
    return float(total)


def _build_argparser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="Watt(5013) total damage calculator (expected value with crit).")
    ap.add_argument("--watt_stack", type=int, required=True, help="initial watt stack (energy)")
    ap.add_argument("--tick", type=int, required=True, help="number of attacks to attempt")
    ap.add_argument("--attack_speed", type=float, required=True, help="attack speed (currently unused in calc)")
    ap.add_argument("--attack_power", type=float, required=True, help="attack power")
    ap.add_argument("--buff_mult", type=float, required=True, help="buff multiplier per stack (e.g., 0.05)")
    ap.add_argument("--ult_mult", type=float, required=True, help="ult multiplier (e.g., 2 means 2x)")
    ap.add_argument("--cirt_rate", type=float, required=True, help="crit rate percent (0~100)")
    ap.add_argument("--cirt_dmg", type=float, required=True, help="crit damage multiplier (e.g., 2.5)")
    ap.add_argument(
        "--stack_after_consume",
        action="store_true",
        help="if set, use (stack after consuming 1) for damage formula each hit",
    )
    return ap


def main() -> None:
    ap = _build_argparser()
    args = ap.parse_args()

    total = mean_total_damage_5013(
        watt_stack=args.watt_stack,
        tick=args.tick,
        attack_speed=args.attack_speed,
        attack_power=args.attack_power,
        buff_mult=args.buff_mult,
        ult_mult=args.ult_mult,
        cirt_rate=args.cirt_rate,
        cirt_dmg=args.cirt_dmg,
        stack_is_before_consume=not args.stack_after_consume,
    )

    print(f"{total:.10f}")


if __name__ == "__main__":
    main()

