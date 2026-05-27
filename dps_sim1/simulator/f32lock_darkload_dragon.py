from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Any, Dict, Tuple
from dps_sim1.simulator.f32lock_rounding import round_half_up as round

DamageTuple = Tuple[float, float, float, float, float]


def _to_float(d: Dict[str, Any], key: str, default: float | None = None) -> float:
    if key in d:
        return float(d[key])
    if default is None:
        raise KeyError(f"missing required param: {key}")
    return float(default)


def _to_int(d: Dict[str, Any], key: str, default: int | None = None) -> int:
    if key in d:
        return int(d[key])
    if default is None:
        raise KeyError(f"missing required param: {key}")
    return int(default)


def _clamp(x: float, lo: float, hi: float) -> float:
    return lo if x < lo else hi if x > hi else x


@dataclass(frozen=True)
class DemonDragonParams15006:
    tick: int
    n_iter: int

    base_attack_mult: float
    skill1_rate: float  # percent 0..100
    skill2_rate: float  # percent 0..100

    attack_speed: float
    attack_power: float

    skill1_mult: float
    skill2_mult: float
    skill3_mult: float
    ult_mult: float

    ult_mana: float
    attack_mana_recov: float
    mana_buff: float

    crit_rate: float  # percent 0..100
    crit_dmg: float   # multiplier

    seed: int | None = None

    def validated(self) -> "DemonDragonParams15006":
        if self.tick < 0:
            raise ValueError("tick must be >= 0")
        if self.n_iter <= 0:
            raise ValueError("n_iter must be > 0")

        if self.attack_speed <= 0:
            raise ValueError("attack_speed must be > 0")
        if self.attack_power < 0:
            raise ValueError("attack_power must be >= 0")

        if self.mana_buff <= 0:
            raise ValueError("mana_buff must be > 0")
        if self.ult_mana <= 0:
            raise ValueError("ult_mana must be > 0 (otherwise ult would be always-ready)")

        if self.crit_dmg < 0:
            raise ValueError("crit_dmg must be >= 0")

        # rates
        r1 = _clamp(self.skill1_rate, 0.0, 100.0)
        r2 = _clamp(self.skill2_rate, 0.0, 100.0)
        if r1 + r2 > 100.0 + 1e-9:
            raise ValueError("skill1_rate + skill2_rate must be <= 100")

        # allow negative multipliers? 基本は0以上を想定
        for name, v in [
            ("base_attack_mult", self.base_attack_mult),
            ("skill1_mult", self.skill1_mult),
            ("skill2_mult", self.skill2_mult),
            ("skill3_mult", self.skill3_mult),
            ("ult_mult", self.ult_mult),
        ]:
            if v < 0:
                raise ValueError(f"{name} must be >= 0")

        if self.attack_mana_recov < 0:
            raise ValueError("attack_mana_recov must be >= 0")

        return self


def _crit_mul(rng: random.Random, crit_rate_percent: float, crit_dmg: float) -> float:
    p = _clamp(crit_rate_percent, 0.0, 100.0) / 100.0
    return crit_dmg if rng.random() < p else 1.0


def _simulate_once(p: DemonDragonParams15006, rng: random.Random) -> DamageTuple:
    """
    1 tick = 1回の行動（basic / skill1 / skill2 / ult のいずれか）
    - skill3(火炎の印) は skill1/skill2 を合計5回発動するたびに「追加ダメージ」として即時発生（tick消費なし）
    - マナ回復は各tickの最後に適用（mana_buffは持続回復に乗算）
    - ult は「tick開始時に mana>=ult_mana なら発動」として実装（詳細は末尾の曖昧仕様参照）
    """
    basic_d = 0.0
    s1_d = 0.0
    s2_d = 0.0
    s3_d = 0.0
    ult_d = 0.0

    mana = 0.0
    skill_counter = 0  # skill1 + skill2 の累計カウント

    # thresholds
    r1 = _clamp(p.skill1_rate, 0.0, 100.0) / 100.0
    r2 = _clamp(p.skill2_rate, 0.0, 100.0) / 100.0
    t1 = r1
    t2 = r1 + r2  # skill2 threshold

    base_mana_per_tick = 1.0 / p.attack_speed
    skill_ult_recovery_ticks = max(0, int(round(0.8 * p.attack_speed)) - 1)
    recovery_remaining = 0

    for _ in range(p.tick):
        if recovery_remaining > 0:
            recovery_remaining -= 1
            mana += (base_mana_per_tick * p.mana_buff)
            continue

        # (A) ult優先：tick開始時にマナが溜まっていれば ult
        if mana >= p.ult_mana:
            dmg = p.attack_power * p.ult_mult * _crit_mul(rng, p.crit_rate, p.crit_dmg)
            ult_d += dmg
            mana = 0.0  # ult後 0 に戻る（超過分は保持しない想定）

            # tick最後のマナ回復（ult中は「基本攻撃」ではないので base のみ）
            mana += (base_mana_per_tick * p.mana_buff)
            recovery_remaining = skill_ult_recovery_ticks
            continue

        # (B) basic / skill1 / skill2 を抽選
        u = rng.random()
        if u < t1:
            # skill1
            dmg = p.attack_power * p.skill1_mult * _crit_mul(rng, p.crit_rate, p.crit_dmg)
            s1_d += dmg

            skill_counter += 1
            if skill_counter % 5 == 0:
                # skill3 追加ダメージ（tick消費なし）
                dmg3 = p.attack_power * p.skill3_mult * _crit_mul(rng, p.crit_rate, p.crit_dmg)
                s3_d += dmg3

            # tick最後のマナ回復（skill扱い：baseのみ）
            mana += (base_mana_per_tick * p.mana_buff)
            recovery_remaining = skill_ult_recovery_ticks

        elif u < t2:
            # skill2
            dmg = p.attack_power * p.skill2_mult * _crit_mul(rng, p.crit_rate, p.crit_dmg)
            s2_d += dmg

            skill_counter += 1
            if skill_counter % 5 == 0:
                dmg3 = p.attack_power * p.skill3_mult * _crit_mul(rng, p.crit_rate, p.crit_dmg)
                s3_d += dmg3

            mana += (base_mana_per_tick * p.mana_buff)
            recovery_remaining = skill_ult_recovery_ticks

        else:
            # basic
            dmg = p.attack_power * p.base_attack_mult * _crit_mul(rng, p.crit_rate, p.crit_dmg)
            basic_d += dmg

            # tick最後のマナ回復（basic扱い：attack_mana_recov + base）
            mana += (base_mana_per_tick * p.mana_buff) + p.attack_mana_recov

    return (basic_d, s1_d, s2_d, s3_d, ult_d)


def mean_total_damage_15006(params: Dict[str, Any]) -> DamageTuple:
    """
    外部参照用:
      - 引数: dict
      - 返り値: (basic, skill1, skill2, skill3, ult) の平均ダメージ合計
    """
    p = DemonDragonParams15006(
        tick=_to_int(params, "tick"),
        n_iter=_to_int(params, "n_iter", 20000),

        base_attack_mult=_to_float(params, "base_attack_mult"),
        skill1_rate=_to_float(params, "skill1_rate"),
        skill2_rate=_to_float(params, "skill2_rate"),

        attack_speed=_to_float(params, "attack_speed"),
        attack_power=_to_float(params, "attack_power"),

        skill1_mult=_to_float(params, "skill1_mult"),
        skill2_mult=_to_float(params, "skill2_mult"),
        skill3_mult=_to_float(params, "skill3_mult"),
        ult_mult=_to_float(params, "ult_mult"),

        ult_mana=_to_float(params, "ult_mana"),
        attack_mana_recov=_to_float(params, "attack_mana_recov"),
        mana_buff=_to_float(params, "mana_buff", 1.0),

        crit_rate=_to_float(params, "crit_rate"),
        crit_dmg=_to_float(params, "crit_dmg"),

        seed=(int(params["seed"]) if "seed" in params and params["seed"] is not None else None),
    ).validated()

    rng = random.Random(p.seed)
    sum_basic = 0.0
    sum_s1 = 0.0
    sum_s2 = 0.0
    sum_s3 = 0.0
    sum_ult = 0.0

    # 反復ごとにrngを進める（seed固定なら再現性あり）
    for _ in range(p.n_iter):
        b, s1, s2, s3, u = _simulate_once(p, rng)
        sum_basic += b
        sum_s1 += s1
        sum_s2 += s2
        sum_s3 += s3
        sum_ult += u

    inv = 1.0 / float(p.n_iter)
    return (sum_basic * inv, sum_s1 * inv, sum_s2 * inv, sum_s3 * inv, sum_ult * inv)


# 任意: 手元で動作確認したい時用
if __name__ == "__main__":
    example = dict(
        tick=3000,
        n_iter=20000,
        base_attack_mult=1.0,
        skill1_rate=20,
        skill2_rate=10,
        attack_speed=1.5,
        attack_power=1000,
        skill1_mult=2.0,
        skill2_mult=3.5,
        skill3_mult=5.0,
        ult_mult=10.0,
        ult_mana=100,
        attack_mana_recov=1.0,
        mana_buff=1.0,
        crit_rate=20,
        crit_dmg=2.5,
        seed=42,
    )
    out = mean_total_damage_15006(example)
    total = sum(out)
    print("mean damage tuple (basic, skill1, skill2, skill3, ult) =", out)
    print("mean total =", total)
    if example["tick"] > 0:
        print("mean damage per tick =", total / example["tick"])
