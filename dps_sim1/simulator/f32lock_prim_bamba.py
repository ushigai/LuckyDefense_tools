from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple
from dps_sim1.simulator.f32lock_rounding import round_half_up as round


DamageTuple = Tuple[float, float, float, float, float]


def round_half_up(x: float) -> int:
    """四捨五入 (0.5 は切り上げ)。"""
    return int(math.floor(x + 0.5))


@dataclass(frozen=True)
class PrimitiveBambaParams:
    # simulation
    tick: int  # 計測tick（究極で延長される前のベース）
    trials: int = 20000
    seed: Optional[int] = None

    # stats
    base_attack_mult: float = 1.0
    skill1_rate: float = 0.0  # percent 0..100
    attack_speed: float = 1.0
    attack_power: float = 0.0
    skill1_mult: float = 1.0
    skill2_mult: float = 1.0
    crit_rate: float = 0.0  # percent 0..100
    crit_dmg: float = 2.0   # multiplier
    ult_mana: float = 999999.0
    ult_time: float = 0.0

    def validated(self) -> "PrimitiveBambaParams":
        if self.tick < 0:
            raise ValueError("tick must be >= 0")
        if self.trials <= 0:
            raise ValueError("trials must be >= 1")
        if self.attack_speed <= 0:
            raise ValueError("attack_speed must be > 0")
        if not (0.0 <= self.skill1_rate <= 100.0):
            raise ValueError("skill1_rate must be in [0, 100]")
        if not (0.0 <= self.crit_rate <= 100.0):
            raise ValueError("crit_rate must be in [0, 100]")
        if self.crit_dmg < 0:
            raise ValueError("crit_dmg must be >= 0")
        if self.ult_mana < 0:
            raise ValueError("ult_mana must be >= 0")
        if self.ult_time < 0:
            raise ValueError("ult_time must be >= 0")
        return self


def _deal_damage(
    rng: random.Random,
    base: float,
    crit_rate_p: float,
    crit_dmg: float,
) -> float:
    """base は（バフ倍率込みで）確定した基礎ダメージ。ここで会心抽選だけ行う。"""
    if crit_rate_p > 0.0 and rng.random() < crit_rate_p:
        return base * crit_dmg
    return base


def _simulate_once(p: PrimitiveBambaParams, rng: random.Random) -> Tuple[float, float, float, float, int, bool]:
    """
    1試行のシミュレーション。
    Returns:
      nonbuff_basic, nonbuff_skill1, nonbuff_skill2, buff_all, elapsed_ticks, capped
    """
    # prob
    p_skill1 = p.skill1_rate / 100.0
    p_crit = p.crit_rate / 100.0

    # state
    mana = 0.0
    buff_remaining = 0  # >0 の間、ダメージ2倍
    basic_counter = 0
    pending_uppercut = False
    skill_ult_recovery_ticks = max(0, int(round(0.8 * p.attack_speed)) - 1)
    recovery_remaining = 0

    nonbuff_basic = 0.0
    nonbuff_skill1 = 0.0
    nonbuff_skill2 = 0.0
    buff_all = 0.0

    target_end = p.tick  # 究極で延長される
    t = 0

    # 無限延長対策（あり得ないパラメータで暴走しないよう保険）
    # 通常用途ではまず到達しません。
    hard_cap = max(p.tick * 100, p.tick + 1_000_000, 100_000)

    capped = False

    while t < target_end:
        if t >= hard_cap:
            capped = True
            break

        in_buff = buff_remaining > 0

        if recovery_remaining > 0:
            recovery_remaining -= 1
            mana += 1.0 / p.attack_speed

            if buff_remaining > 0:
                buff_remaining -= 1

            if p.ult_mana > 0 and mana >= p.ult_mana:
                ext_ticks = round_half_up(p.ult_time * p.attack_speed * 0.3)
                if ext_ticks > 0:
                    target_end += ext_ticks

                buff_ticks = round_half_up(p.ult_time * p.attack_speed * 1.3)
                mana = 0.0
                if buff_ticks > 0:
                    buff_remaining = buff_ticks

                recovery_remaining = skill_ult_recovery_ticks

            t += 1
            continue

        # --- 1tickの行動（基本 / skill1 / skill2） ---
        if pending_uppercut:
            # skill2（アッパーカット）優先
            pending_uppercut = False
            base = p.attack_power * p.skill2_mult
            if in_buff:
                base *= 2.0
            dmg = _deal_damage(rng, base, p_crit, p.crit_dmg)
            if in_buff:
                buff_all += dmg
            else:
                nonbuff_skill2 += dmg
            recovery_remaining = skill_ult_recovery_ticks

        else:
            # 基本攻撃時に skill1 へ遷移
            if p_skill1 > 0.0 and rng.random() < p_skill1:
                # skill1（乱打）
                base = p.attack_power * p.skill1_mult
                if in_buff:
                    base *= 2.0
                dmg = _deal_damage(rng, base, p_crit, p.crit_dmg)
                if in_buff:
                    buff_all += dmg
                else:
                    nonbuff_skill1 += dmg
                recovery_remaining = skill_ult_recovery_ticks
            else:
                # basic
                base = p.attack_power * p.base_attack_mult
                if in_buff:
                    base *= 2.0
                dmg = _deal_damage(rng, base, p_crit, p.crit_dmg)
                if in_buff:
                    buff_all += dmg
                else:
                    nonbuff_basic += dmg

                # basic を10回ごとに skill2 を予約
                basic_counter += 1
                if basic_counter >= 10:
                    basic_counter = 0
                    pending_uppercut = True

        # --- tickの最後：マナ回復（仕様どおり「最後」） ---
        mana += 1.0 / p.attack_speed

        # --- バフ残りtickを減らす（このtickの行動はバフ適用済みなので最後に減らす） ---
        if buff_remaining > 0:
            buff_remaining -= 1

        # --- ult判定（バフ中でも再発動可能） ---
        if p.ult_mana > 0 and mana >= p.ult_mana:
            # 発動時に計測tick延長
            ext_ticks = round_half_up(p.ult_time * p.attack_speed * 0.3)
            if ext_ticks > 0:
                target_end += ext_ticks

            # バフtick
            buff_ticks = round_half_up(p.ult_time * p.attack_speed * 1.3)
            mana = 0.0
            if buff_ticks > 0:
                buff_remaining = buff_ticks

            # 究極自体はダメージ無し（=計上不要）
            recovery_remaining = skill_ult_recovery_ticks

        t += 1

    elapsed_ticks = min(t, hard_cap)
    return nonbuff_basic, nonbuff_skill1, nonbuff_skill2, buff_all, elapsed_ticks, capped


def mean_total_damage_15001(params: Dict[str, Any]) -> DamageTuple:
    """
    外部から辞書で呼べる平均ダメージ計算。
    返す値は平均の
      - 非バフ basic 合計
      - 非バフ skill1 合計
      - 非バフ skill2 合計
      - skill3 は常に 0
      - バフ中（basic+skill1+skill2）合計を ult スロットに集約
    """
    p = PrimitiveBambaParams(
        tick=int(params.get("tick", 0)),
        trials=int(params.get("trials", 0)),
        seed=params.get("seed", None),

        base_attack_mult=float(params["base_attack_mult"]),
        skill1_rate=float(params["skill1_rate"]),
        attack_speed=float(params["attack_speed"]),
        attack_power=float(params["attack_power"]),
        skill1_mult=float(params["skill1_mult"]),
        skill2_mult=float(params["skill2_mult"]),
        crit_rate=float(params["crit_rate"]),
        crit_dmg=float(params["crit_dmg"]),
        ult_mana=float(params["ult_mana"]),
        ult_time=float(params["ult_time"]),
    ).validated()

    rng = random.Random(p.seed)

    sum_nb_basic = 0.0
    sum_nb_s1 = 0.0
    sum_nb_s2 = 0.0
    sum_buff = 0.0

    for _ in range(p.trials):
        nb_basic, nb_s1, nb_s2, buff_all, _, _ = _simulate_once(p, rng)
        sum_nb_basic += nb_basic
        sum_nb_s1 += nb_s1
        sum_nb_s2 += nb_s2
        sum_buff += buff_all

    mean_nb_basic = sum_nb_basic / p.trials
    mean_nb_s1 = sum_nb_s1 / p.trials
    mean_nb_s2 = sum_nb_s2 / p.trials
    mean_buff = sum_buff / p.trials

    return mean_nb_basic, mean_nb_s1, mean_nb_s2, 0.0, mean_buff


def mean_total_damage_primitive_bamba(params: Dict[str, Any]) -> DamageTuple:
    """互換用の英語名。アプリ本体と同じ5スロット返却を返す。"""
    return mean_total_damage_15001(params)


# ユーザー要望の関数名（日本語識別子）も用意
def mean_total_damage_原始バンバ(params: Dict[str, Any]) -> DamageTuple:
    return mean_total_damage_primitive_bamba(params)


if __name__ == "__main__":
    import argparse
    import json

    ap = argparse.ArgumentParser(description="Primitive Bamba Monte Carlo DPS tool")
    ap.add_argument("--tick", type=int, required=True)
    ap.add_argument("--trials", type=int, default=20000)
    ap.add_argument("--seed", type=int, default=None)

    ap.add_argument("--base_attack_mult", type=float, required=True)
    ap.add_argument("--skill1_rate", type=float, required=True)
    ap.add_argument("--attack_speed", type=float, required=True)
    ap.add_argument("--attack_power", type=float, required=True)
    ap.add_argument("--skill1_mult", type=float, required=True)
    ap.add_argument("--skill2_mult", type=float, required=True)
    ap.add_argument("--crit_rate", type=float, required=True)
    ap.add_argument("--crit_dmg", type=float, required=True)
    ap.add_argument("--ult_mana", type=float, required=True)
    ap.add_argument("--ult_time", type=float, required=True)

    args = ap.parse_args()

    params = vars(args)
    out = mean_total_damage_primitive_bamba(params)
    print(json.dumps(out, ensure_ascii=False, indent=2))
