from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any, Optional, Tuple
import argparse
import random
import math


# internal action names
ACT_BASIC = "basic"
ACT_SKILL1 = "skill1"  # チューチュービーム
ACT_SKILL2 = "skill2"  # 超爆破ロケット
ACT_ULT = "ult"        # ミニチュー


@dataclass
class RokechuuParams5115:
    attack_power: float
    attack_speed: float

    # percent 0..100
    skill1_rate: float
    crit_rate: float

    # multiplier (2 => 2x, 150 => 150x)
    skill1_mult: float
    skill2_mult: float
    ult_mult: float
    crit_dmg: float

    # mana for ult
    ult_mana: float

    # stack threshold for skill2
    skill2_stack_threshold: int = 15


def _validate_params(p: RokechuuParams5115) -> None:
    if p.attack_speed <= 0:
        raise ValueError("attack_speed must be > 0")
    for name, v in [("skill1_rate", p.skill1_rate), ("crit_rate", p.crit_rate)]:
        if not (0.0 <= v <= 100.0):
            raise ValueError(f"{name} must be in [0, 100], got {v}")
    for name, v in [
        ("attack_power", p.attack_power),
        ("skill1_mult", p.skill1_mult),
        ("skill2_mult", p.skill2_mult),
        ("ult_mult", p.ult_mult),
        ("crit_dmg", p.crit_dmg),
        ("ult_mana", p.ult_mana),
    ]:
        if v < 0:
            raise ValueError(f"{name} must be >= 0, got {v}")
    if p.skill2_stack_threshold <= 0:
        raise ValueError("skill2_stack_threshold must be > 0")


def _ticks_from_duration_sec(duration_sec: float, attack_speed: float) -> int:
    # 指示通り、attack_speed による計算で小数が出る場合は round() で丸め込む
    # duration_sec は現実時間(秒)、1tick = 1/attack_speed 秒 として ticks=duration*attack_speed
    return int(round(duration_sec * attack_speed))


def _crit_multiplier(rng: random.Random, crit_rate_pct: float, crit_dmg: float) -> float:
    if crit_rate_pct <= 0:
        return 1.0
    if crit_rate_pct >= 100:
        return crit_dmg
    return crit_dmg if (rng.random() < (crit_rate_pct / 100.0)) else 1.0


def _action_multiplier(action: str, p: RokechuuParams5115) -> float:
    if action == ACT_BASIC:
        return 1.0
    if action == ACT_SKILL1:
        return p.skill1_mult
    if action == ACT_SKILL2:
        return p.skill2_mult
    if action == ACT_ULT:
        return p.ult_mult
    raise ValueError(f"Unknown action: {action}")


def _choose_action(mana: float, basic_stack: int, p: RokechuuParams5115, rng: random.Random) -> str:
    # Mermaidに沿って優先度を「ult判定 → stackでskill2 → 確率でskill1 → basic」とする
    if mana >= p.ult_mana:
        return ACT_ULT
    if basic_stack >= p.skill2_stack_threshold:
        return ACT_SKILL2

    # skill1_rate%
    if p.skill1_rate >= 100:
        return ACT_SKILL1
    if p.skill1_rate > 0 and (rng.random() < (p.skill1_rate / 100.0)):
        return ACT_SKILL1
    return ACT_BASIC


def simulate_one_trial_5115(
    p: RokechuuParams5115,
    ticks: int,
    rng: random.Random,
    return_counts: bool = False,
) -> Tuple[float, Optional[Dict[str, int]]]:
    """
    1試行分の総ダメージを返す。
    状態:
      - mana: 初期0。tick末尾で +1/attack_speed。ult発動時は即0へ戻す。
      - basic_stack: basic実行時のみ +1。閾値(15)到達後は次の判定でskill2を発動し、その時に0へリセット。
    """
    mana = 0.0
    basic_stack = 0
    total_damage = 0.0

    counts = {ACT_BASIC: 0, ACT_SKILL1: 0, ACT_SKILL2: 0, ACT_ULT: 0} if return_counts else None

    for _ in range(ticks):
        action = _choose_action(mana, basic_stack, p, rng)

        # damage
        mult = _action_multiplier(action, p)
        dmg = p.attack_power * mult
        dmg *= _crit_multiplier(rng, p.crit_rate, p.crit_dmg)
        total_damage += dmg

        if counts is not None:
            counts[action] += 1

        # state updates right after action
        if action == ACT_BASIC:
            basic_stack += 1
        elif action == ACT_SKILL2:
            basic_stack = 0  # 超爆破ロケット発動で消費/リセット扱い
        # skill1/ultではスタック増えない想定

        if action == ACT_ULT:
            mana = 0.0  # ミニチュー発動後マナ0

        # end-of-tick mana regen
        mana += (1.0 / p.attack_speed)

    return total_damage, counts


def simulate_one_trial_breakdown_5115(
    p: RokechuuParams5115,
    ticks: int,
    rng: random.Random,
) -> Tuple[float, float, float, float, float]:
    """
    1試行分のダメージ内訳を返す。
    戻り値: (basic, skill1, skill2, skill3, ult)
      - このキャラは skill3 を持たないため常に 0.0
    """
    mana = 0.0
    basic_stack = 0

    dmg_basic = 0.0
    dmg_skill1 = 0.0
    dmg_skill2 = 0.0
    dmg_ult = 0.0

    for _ in range(ticks):
        action = _choose_action(mana, basic_stack, p, rng)

        mult = _action_multiplier(action, p)
        dmg = p.attack_power * mult
        dmg *= _crit_multiplier(rng, p.crit_rate, p.crit_dmg)

        if action == ACT_BASIC:
            dmg_basic += dmg
            basic_stack += 1
        elif action == ACT_SKILL1:
            dmg_skill1 += dmg
            # スタック増えない
        elif action == ACT_SKILL2:
            dmg_skill2 += dmg
            basic_stack = 0
        elif action == ACT_ULT:
            dmg_ult += dmg
            mana = 0.0
        else:
            raise RuntimeError(f"Unknown action: {action}")

        # end-of-tick mana regen
        mana += (1.0 / p.attack_speed)

    return dmg_basic, dmg_skill1, dmg_skill2, 0.0, dmg_ult

def mean_total_damage_5115(options: Dict[str, Any]) -> Tuple[float, float, float, float, float]:
    """
    外部から平均総ダメージ内訳を取得するための関数。

    戻り値: (basic, skill1, skill2, skill3, ult)
      - skill3 は存在しないため常に 0.0
    """
    p = RokechuuParams5115(
        attack_power=float(options["attack_power"]),
        attack_speed=float(options["attack_speed"]),
        skill1_rate=float(options["skill1_rate"]),
        skill1_mult=float(options["skill1_mult"]),
        skill2_mult=float(options["skill2_mult"]),
        ult_mult=float(options["ult_mult"]),
        ult_mana=float(options["ult_mana"]),
        crit_rate=float(options["crit_rate"]),
        crit_dmg=float(options["crit_dmg"]),
    )
    _validate_params(p)

    if "ticks" in options and options["ticks"] is not None:
        ticks = int(round(float(options["ticks"])))
    elif "durationSec" in options and options["durationSec"] is not None:
        ticks = _ticks_from_duration_sec(float(options["durationSec"]), p.attack_speed)
    else:
        raise ValueError("Either 'ticks' or 'durationSec' must be provided in options")

    trials = int(options.get("trials", 20000))
    if trials <= 0:
        raise ValueError("trials must be > 0")

    seed = options.get("seed", None)
    rng = random.Random(seed)

    s_basic = s_s1 = s_s2 = s_s3 = s_ult = 0.0
    for _ in range(trials):
        b, s1, s2, s3, u = simulate_one_trial_breakdown_5115(p, ticks, rng)
        s_basic += b
        s_s1 += s1
        s_s2 += s2
        s_s3 += s3
        s_ult += u

    inv = 1.0 / float(trials)
    return s_basic * inv, s_s1 * inv, s_s2 * inv, s_s3 * inv, s_ult * inv

def main() -> None:
    ap = argparse.ArgumentParser(description="Rokechuu(5115) Monte Carlo DPS simulator (tick-based)")
    ap.add_argument("--attack_power", type=float, required=True)
    ap.add_argument("--attack_speed", type=float, required=True)

    ap.add_argument("--skill1_rate", type=float, required=True, help="percent 0..100")
    ap.add_argument("--skill1_mult", type=float, required=True, help="multiplier (2 => 2x, 150 => 150x)")
    ap.add_argument("--skill2_mult", type=float, required=True)
    ap.add_argument("--ult_mult", type=float, required=True)
    ap.add_argument("--ult_mana", type=float, required=True)

    ap.add_argument("--crit_rate", type=float, required=True, help="percent 0..100")
    ap.add_argument("--crit_dmg", type=float, required=True, help="multiplier (e.g., 2.5)")

    g = ap.add_mutually_exclusive_group()
    g.add_argument("--ticks", type=float, default=None, help="number of ticks (rounded with round())")
    g.add_argument("--durationSec", type=float, default=None, help="simulate for seconds; ticks=round(durationSec*attack_speed)")

    ap.add_argument("--trials", type=int, default=20000)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--show_counts", action="store_true", help="show average action counts per trial")

    args = ap.parse_args()

    p = RokechuuParams5115(
        attack_power=args.attack_power,
        attack_speed=args.attack_speed,
        skill1_rate=args.skill1_rate,
        skill1_mult=args.skill1_mult,
        skill2_mult=args.skill2_mult,
        ult_mult=args.ult_mult,
        ult_mana=args.ult_mana,
        crit_rate=args.crit_rate,
        crit_dmg=args.crit_dmg,
    )
    _validate_params(p)

    if args.ticks is not None:
        ticks = int(round(args.ticks))
        duration_sec = ticks / p.attack_speed  # 1tick = 1/attack_speed sec 仮定
    elif args.durationSec is not None:
        duration_sec = float(args.durationSec)
        ticks = _ticks_from_duration_sec(duration_sec, p.attack_speed)
    else:
        # デフォルトは60秒相当（ticks=round(60*attack_speed)）
        duration_sec = 60.0
        ticks = _ticks_from_duration_sec(duration_sec, p.attack_speed)

    rng = random.Random(args.seed)

    sum_dmg = 0.0
    sum_counts = {ACT_BASIC: 0, ACT_SKILL1: 0, ACT_SKILL2: 0, ACT_ULT: 0} if args.show_counts else None

    for _ in range(args.trials):
        dmg, counts = simulate_one_trial_5115(p, ticks, rng, return_counts=args.show_counts)
        sum_dmg += dmg
        if args.show_counts and counts is not None and sum_counts is not None:
            for k in sum_counts:
                sum_counts[k] += counts[k]

    mean_dmg = sum_dmg / float(args.trials)
    dps = mean_dmg / duration_sec if duration_sec > 0 else float("nan")
    dpt = mean_dmg / float(ticks) if ticks > 0 else float("nan")

    print("=== Rokechuu(5115) Simulation ===")
    print(f"trials        : {args.trials}")
    print(f"seed          : {args.seed}")
    print(f"ticks         : {ticks}")
    print(f"duration(sec) : {duration_sec:.6f}")
    print(f"mean_total_damage : {mean_dmg:.6f}")
    print(f"damage_per_tick   : {dpt:.6f}")
    print(f"DPS               : {dps:.6f}")

    if args.show_counts and sum_counts is not None:
        print("--- mean action counts (per trial) ---")
        for k in [ACT_BASIC, ACT_SKILL1, ACT_SKILL2, ACT_ULT]:
            print(f"{k:6s}: {sum_counts[k] / float(args.trials):.6f}")


if __name__ == "__main__":
    main()

