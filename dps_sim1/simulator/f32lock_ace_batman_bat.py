from __future__ import annotations

import argparse
import math
import random
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple
from dps_sim1.simulator.f32lock_rounding import round_half_up as round

# 便宜上、DPSを「秒あたり」にしたい場合の換算用（既存プロジェクトに合わせて 40FPS を採用）
FPS = 40


def _to_float(x: Any, name: str) -> float:
    try:
        return float(x)
    except Exception as e:
        raise ValueError(f"{name} must be a number, got {x!r}") from e


def _to_int(x: Any, name: str) -> int:
    try:
        return int(x)
    except Exception as e:
        raise ValueError(f"{name} must be an int, got {x!r}") from e


@dataclass(frozen=True)
class AceBatmanParams15210:
    # 任意tick数（ユーザー要求により必須）
    ticks: int

    # 与えられる引数群
    base_attack_mult: float
    attack_speed: float
    attack_power: float
    skill1_mult: float
    crit_rate: float   # 0~100 (percent)
    crit_dmg: float    # multiplier (e.g., 2.5)
    ult_mult: float
    ult_mana: float
    ult_ticks: int

    def validated(self) -> "AceBatmanParams15210":
        if self.ticks < 0:
            raise ValueError("ticks must be >= 0")
        if self.attack_speed <= 0:
            raise ValueError("attack_speed must be > 0")
        if self.attack_power < 0:
            raise ValueError("attack_power must be >= 0")
        if self.base_attack_mult < 0:
            raise ValueError("base_attack_mult must be >= 0")
        if self.skill1_mult < 0:
            raise ValueError("skill1_mult must be >= 0")
        if self.ult_mult < 0:
            raise ValueError("ult_mult must be >= 0")
        if self.ult_mana < 0:
            raise ValueError("ult_mana must be >= 0")
        if self.ult_ticks <= 0:
            raise ValueError("ult_ticks must be > 0")
        if not (0 <= self.crit_rate <= 100):
            raise ValueError("crit_rate must be between 0 and 100")
        if self.crit_dmg < 0:
            raise ValueError("crit_dmg must be >= 0")
        return self


def _apply_crit(rng: random.Random, base_damage: float, crit_rate: float, crit_dmg: float) -> float:
    """crit_rate% の確率で crit_dmg 倍."""
    if base_damage <= 0:
        return 0.0
    if rng.random() < (crit_rate / 100.0):
        return base_damage * crit_dmg
    return base_damage


def simulate_once_15210(p: AceBatmanParams15210, rng: random.Random) -> Dict[str, float]:
    """
    1回試行（乱数は会心のみ）

    ルール（本実装の採用仕様）:
      - 1tickにつき行動は1つ（ult中はultの1hitのみ）
      - basic を10回行うと、次の行動で skill1 を1回発動（basic回数カウントはbasicのみ）
      - マナ回復は毎tick末に mana += 1/attack_speed
      - tick末の回復後、ult中でなく mana>=ult_mana なら ult開始（mana=0に戻す）
      - ult は ult_ticks tick 継続し、各tickで (attack_power * (ult_mult/ult_ticks)) の1hit
    """
    ticks = p.ticks
    mana = 0.0

    # basicを何回打ったか（skill1発動用）
    basic_count = 0
    pending_skill1 = False

    # ult状態
    ult_remaining = 0  # >0ならult中（残りhit tick数）

    dmg_basic = 0.0
    dmg_skill1 = 0.0
    dmg_ult = 0.0

    # 1tickあたりのマナ回復量
    mana_per_tick = 1.0 / p.attack_speed

    # ult 1tickあたりの倍率（例: ult_mult=1000, ult_ticks=5 => 200倍/ tick）
    ult_mult_per_tick = p.ult_mult / float(p.ult_ticks)
    skill_recovery_ticks = max(0, int(round(0.8 * p.attack_speed)) - 1)
    recovery_remaining = 0

    for _ in range(ticks):
        if recovery_remaining > 0:
            recovery_remaining -= 1
            mana += mana_per_tick
            continue

        # --- 行動フェーズ（tickの冒頭で1回だけ） ---
        if ult_remaining > 0:
            # ultの1hit
            base = p.attack_power * ult_mult_per_tick
            dmg_ult += _apply_crit(rng, base, p.crit_rate, p.crit_dmg)
            ult_remaining -= 1

        elif pending_skill1:
            # 竜巻スマッシュ
            base = p.attack_power * p.skill1_mult
            dmg_skill1 += _apply_crit(rng, base, p.crit_rate, p.crit_dmg)
            pending_skill1 = False
            recovery_remaining = skill_recovery_ticks

        else:
            # basic
            base = p.attack_power * p.base_attack_mult
            dmg_basic += _apply_crit(rng, base, p.crit_rate, p.crit_dmg)

            basic_count += 1
            if basic_count >= 10:
                basic_count -= 10
                pending_skill1 = True

        # --- tick末：マナ回復 ---
        mana += mana_per_tick

        # --- tick末：ult開始判定（ult中でない時のみ） ---
        if recovery_remaining == 0 and ult_remaining == 0 and p.ult_mana >= 0 and mana >= p.ult_mana:
            ult_remaining = p.ult_ticks
            mana = 0.0

    return {
        "basic": dmg_basic,
        "skill1": dmg_skill1,
        "skill2": 0.0,
        "skill3": 0.0,
        "ult": dmg_ult,
        "total": dmg_basic + dmg_skill1 + dmg_ult,
    }


def mean_total_damage_15210(
    params: Dict[str, Any],
    n_iter: int = 10000,
    seed: Optional[int] = 0,
) -> Tuple[float, float, float, float, float]:
    """
    外部参照用：エースバットマン打者(15210)の平均ダメージを返す。

    引数:
      params: dict（必須キー: ticks, base_attack_mult, attack_speed, attack_power, skill1_mult,
                    crit_rate, crit_dmg, ult_mult, ult_mana, ult_ticks）
      n_iter: 試行回数
      seed: 乱数seed（再現性用）

    戻り値:
      (basic, skill1, skill2, skill3, ult) の平均（期待値）
    """
    if n_iter <= 0:
        raise ValueError("n_iter must be > 0")

    p = AceBatmanParams15210(
        ticks=_to_int(params.get("ticks"), "ticks"),
        base_attack_mult=_to_float(params.get("base_attack_mult"), "base_attack_mult"),
        attack_speed=_to_float(params.get("attack_speed"), "attack_speed"),
        attack_power=_to_float(params.get("attack_power"), "attack_power"),
        skill1_mult=_to_float(params.get("skill1_mult"), "skill1_mult"),
        crit_rate=_to_float(params.get("crit_rate"), "crit_rate"),
        crit_dmg=_to_float(params.get("crit_dmg"), "crit_dmg"),
        ult_mult=_to_float(params.get("ult_mult"), "ult_mult"),
        ult_mana=_to_float(params.get("ult_mana"), "ult_mana"),
        ult_ticks=_to_int(params.get("ult_ticks"), "ult_ticks"),
    ).validated()

    sum_basic = 0.0
    sum_skill1 = 0.0
    sum_ult = 0.0
    sum_total = 0.0

    # 再現性のために試行ごとにseedをずらす（同一seedでも n_iter を変えても破綻しにくい）
    base_seed = 0 if seed is None else int(seed)

    for i in range(n_iter):
        rng = random.Random(base_seed + i)
        out = simulate_once_15210(p, rng)
        sum_basic += out["basic"]
        sum_skill1 += out["skill1"]
        sum_ult += out["ult"]
        sum_total += out["total"]

    inv = 1.0 / float(n_iter)
    return sum_basic*inv, sum_skill1*inv, 0.0, 0.0, sum_ult*inv


def _calc_dps(total_damage: float, ticks: int) -> float:
    # 1tick = 1/FPS 秒と仮定した場合の DPS
    sec = ticks / float(FPS) if ticks > 0 else 0.0
    return (total_damage / sec) if sec > 0 else 0.0


def main() -> None:
    ap = argparse.ArgumentParser(description="Ace Batman Batter (15210) Monte Carlo damage calculator")
    ap.add_argument("--ticks", type=int, required=True)

    ap.add_argument("--base_attack_mult", type=float, required=True)
    ap.add_argument("--attack_speed", type=float, required=True)
    ap.add_argument("--attack_power", type=float, required=True)
    ap.add_argument("--skill1_mult", type=float, required=True)
    ap.add_argument("--crit_rate", type=float, required=True)
    ap.add_argument("--crit_dmg", type=float, required=True)
    ap.add_argument("--ult_mult", type=float, required=True)
    ap.add_argument("--ult_mana", type=float, required=True)
    ap.add_argument("--ult_ticks", type=int, required=True)

    ap.add_argument("--n_iter", type=int, default=10000)
    ap.add_argument("--seed", type=int, default=0)

    args = ap.parse_args()

    params = {
        "ticks": args.ticks,
        "base_attack_mult": args.base_attack_mult,
        "attack_speed": args.attack_speed,
        "attack_power": args.attack_power,
        "skill1_mult": args.skill1_mult,
        "crit_rate": args.crit_rate,
        "crit_dmg": args.crit_dmg,
        "ult_mult": args.ult_mult,
        "ult_mana": args.ult_mana,
        "ult_ticks": args.ult_ticks,
    }

    mean = mean_total_damage_15210(params, n_iter=args.n_iter, seed=args.seed)

    print("=== mean damage (expected) ===")
    print(f"basic : {mean['basic']:.6f}")
    print(f"skill1: {mean['skill1']:.6f}")
    print(f"ult   : {mean['ult']:.6f}")
    print(f"total : {mean['total']:.6f}")

    print("\n=== derived ===")
    print(f"DPS (assuming {FPS} ticks/sec): {_calc_dps(mean['total'], args.ticks):.6f}")


if __name__ == "__main__":
    main()
