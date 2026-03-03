# bamba.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple, Optional
import argparse
import math
import random
from dps_sim1.simulator.f32lock_rounding import round_half_up as round


DamageTuple = Tuple[float, float, float, float, float]  # (basic, skill1, skill2, skill3, ult)


@dataclass(frozen=True)
class BambaParams:
    # required (program args)
    base_attack_mult: float
    skill1_times: int
    skill2_rate: float  # 0..100 (%)
    attack_speed: float
    attack_power: float
    skill1_mult: float
    skill2_mult: float
    crit_rate: float  # 0..100 (%)
    crit_dmg: float
    ult_mult: float
    ult_mana: float

    # optional (spec mentions but not listed in args; default based on description)
    attack_mana_recov: float = 1.0  # per tick: attack_mana_recov / attack_speed
    ult_buff_mult: float = 1.5
    ult_buff_ticks_factor: float = 10.0  # buff ticks = round(ult_buff_ticks_factor * attack_speed)
    hammer_basic_mult: float = 2.0
    hammer_basic_charges: int = 3


def _get_required(d: Dict, k: str):
    if k not in d:
        raise KeyError(f"missing param: {k}")
    return d[k]


def parse_bamba_params(params_dict: Dict) -> BambaParams:
    """
    params_dict から BambaParams を組み立てる（余計なキーは無視）。
    必須キー:
      base_attack_mult, skill1_times, skill2_rate, attack_speed, attack_power,
      skill1_mult, skill2_mult, crit_rate, crit_dmg, ult_mult, ult_mana
    任意キー:
      attack_mana_recov, ult_buff_mult, ult_buff_ticks_factor,
      hammer_basic_mult, hammer_basic_charges
    """
    p = BambaParams(
        base_attack_mult=float(_get_required(params_dict, "base_attack_mult")),
        skill1_times=int(_get_required(params_dict, "skill1_times")),
        skill2_rate=float(_get_required(params_dict, "skill2_rate")),
        attack_speed=float(_get_required(params_dict, "attack_speed")),
        attack_power=float(_get_required(params_dict, "attack_power")),
        skill1_mult=float(_get_required(params_dict, "skill1_mult")),
        skill2_mult=float(_get_required(params_dict, "skill2_mult")),
        crit_rate=float(_get_required(params_dict, "crit_rate")),
        crit_dmg=float(_get_required(params_dict, "crit_dmg")),
        ult_mult=float(_get_required(params_dict, "ult_mult")),
        ult_mana=float(_get_required(params_dict, "ult_mana")),
        attack_mana_recov=float(params_dict.get("attack_mana_recov", 1.0)),
        ult_buff_mult=float(params_dict.get("ult_buff_mult", 1.5)),
        ult_buff_ticks_factor=float(params_dict.get("ult_buff_ticks_factor", 10.0)),
        hammer_basic_mult=float(params_dict.get("hammer_basic_mult", 2.0)),
        hammer_basic_charges=int(params_dict.get("hammer_basic_charges", 3)),
    )

    if p.attack_speed <= 0:
        raise ValueError("attack_speed must be > 0")
    if not (0.0 <= p.skill2_rate <= 100.0):
        raise ValueError("skill2_rate must be in [0,100]")
    if not (0.0 <= p.crit_rate <= 100.0):
        raise ValueError("crit_rate must be in [0,100]")
    if p.skill1_times < 0:
        raise ValueError("skill1_times must be >= 0")
    if p.hammer_basic_charges < 0:
        raise ValueError("hammer_basic_charges must be >= 0")
    return p


def _roll_crit(base_damage: float, crit_rate_pct: float, crit_dmg: float, rng: random.Random) -> float:
    if base_damage == 0:
        return 0.0
    if rng.random() < (crit_rate_pct / 100.0):
        return base_damage * crit_dmg
    return base_damage


def _buff_ticks(p: BambaParams) -> int:
    # tick は整数なので丸めが必要。仕様が曖昧なので round を採用（後述）。
    return int(round(p.ult_buff_ticks_factor * p.attack_speed))


def simulate_once_bamba(p: BambaParams, num_ticks: int, rng: random.Random) -> Dict[str, float]:
    """
    1試行分の合計ダメージを返す。
    返り値のキー: 'basic','skill1','skill2','ult'
      - ult は「気爆ダメージ」＋「バフ期間中に出た全ダメージ（基本/スキル含む）」を集約
    """
    totals = {"basic": 0.0, "skill1": 0.0, "skill2": 0.0, "ult": 0.0}

    mana = 0.0
    buff_remain = 0  # >0 ならバフ中
    hammer_charges = 0  # 次の基本攻撃ダメージ2倍の残り回数

    # 「基本攻撃を skill1_times 回行うと次の基本攻撃の代わりに skill1」
    basic_count_since_skill1 = 0

    mana_per_tick = p.attack_mana_recov / p.attack_speed
    duration = _buff_ticks(p)

    for _t in range(num_ticks):
        in_buff = buff_remain > 0

        # 1) 行動（ダメージ発生）
        if mana >= p.ult_mana:
            # ult 発動（このtickの行動を消費）
            dmg = p.attack_power * p.ult_mult
            dmg = _roll_crit(dmg, p.crit_rate, p.crit_dmg, rng)
            if in_buff:
                dmg *= p.ult_buff_mult
            totals["ult"] += dmg  # ult 自体も ult 枠

            mana = 0.0
            # バフ開始/更新
            buff_remain = max(duration, 0)

        else:
            # skill1 優先（「次の基本攻撃の代わり」）
            if p.skill1_times > 0 and basic_count_since_skill1 >= p.skill1_times:
                dmg = p.attack_power * p.skill1_mult
                dmg = _roll_crit(dmg, p.crit_rate, p.crit_dmg, rng)
                if in_buff:
                    dmg *= p.ult_buff_mult
                    totals["ult"] += dmg
                else:
                    totals["skill1"] += dmg
                basic_count_since_skill1 = 0

            else:
                # basic のタイミングで skill2_rate でハンマー
                if rng.random() < (p.skill2_rate / 100.0):
                    dmg = p.attack_power * p.skill2_mult
                    dmg = _roll_crit(dmg, p.crit_rate, p.crit_dmg, rng)
                    if in_buff:
                        dmg *= p.ult_buff_mult
                        totals["ult"] += dmg
                    else:
                        totals["skill2"] += dmg

                    # ハンマー後「以降3回の基本攻撃ダメージ2倍」
                    hammer_charges = p.hammer_basic_charges

                    # NOTE: ハンマーが「基本攻撃を行った回数」に含まれるかは仕様が曖昧。
                    # ここでは「基本攻撃そのものではない」とみなし、カウントしない（後述）。
                else:
                    # 基本攻撃
                    dmg = p.attack_power * p.base_attack_mult
                    if hammer_charges > 0:
                        dmg *= p.hammer_basic_mult
                        hammer_charges -= 1

                    dmg = _roll_crit(dmg, p.crit_rate, p.crit_dmg, rng)
                    if in_buff:
                        dmg *= p.ult_buff_mult
                        totals["ult"] += dmg
                    else:
                        totals["basic"] += dmg

                    basic_count_since_skill1 += 1

        # 2) tickの最後にマナ回復
        mana += mana_per_tick

        # 3) tickの最後にバフ残りtickを減らす（ult発動tick自体には適用されない想定）
        if buff_remain > 0:
            buff_remain -= 1

    return totals


def mean_total_damage_5001(
    params_dict: Dict,
    num_ticks: int,
    trials: int = 20000,
    seed: Optional[int] = 0,
) -> DamageTuple:
    """
    外部から参照する用の関数。
    返り値: (basic, skill1, skill2, skill3, ult)
      - ult は「気爆」＋「バフ期間中に出た全ダメージ（基本/スキル含む）」の合算
    """
    if num_ticks <= 0:
        return (0.0, 0.0, 0.0, 0.0, 0.0)
    p = parse_bamba_params(params_dict)
    if trials <= 0:
        raise ValueError("trials must be > 0")

    rng = random.Random(seed)
    acc_basic = acc_skill1 = acc_skill2 = acc_ult = 0.0

    for _ in range(trials):
        totals = simulate_once_bamba(p, num_ticks, rng)
        acc_basic += totals["basic"]
        acc_skill1 += totals["skill1"]
        acc_skill2 += totals["skill2"]
        acc_ult += totals["ult"]

    inv = 1.0 / trials
    return (acc_basic * inv, acc_skill1 * inv, acc_skill2 * inv, 0.0, acc_ult * inv)


def mean_dps_5001(
    params_dict: Dict,
    num_ticks: int,
    trials: int = 20000,
    seed: Optional[int] = 0,
) -> Dict[str, float]:
    """
    平均DPS（tickあたり平均ダメージ）をカテゴリ別に返す。
    """
    basic, skill1, skill2, skill3, ult = mean_total_damage_5001(params_dict, num_ticks, trials=trials, seed=seed)
    denom = float(num_ticks) if num_ticks > 0 else 1.0
    return {
        "basic": basic / denom,
        "skill1": skill1 / denom,
        "skill2": skill2 / denom,
        "skill3": skill3 / denom,
        "ult": ult / denom,
        "total": (basic + skill1 + skill2 + skill3 + ult) / denom,
    }


def _cli() -> int:
    ap = argparse.ArgumentParser(description="Bamba DPS Monte Carlo simulator (tick-based)")
    ap.add_argument("--ticks", type=int, required=True)
    ap.add_argument("--trials", type=int, default=20000)
    ap.add_argument("--seed", type=int, default=0)

    # required params
    ap.add_argument("--base_attack_mult", type=float, required=True)
    ap.add_argument("--skill1_times", type=int, required=True)
    ap.add_argument("--skill2_rate", type=float, required=True)
    ap.add_argument("--attack_speed", type=float, required=True)
    ap.add_argument("--attack_power", type=float, required=True)
    ap.add_argument("--skill1_mult", type=float, required=True)
    ap.add_argument("--skill2_mult", type=float, required=True)
    ap.add_argument("--crit_rate", type=float, required=True)
    ap.add_argument("--crit_dmg", type=float, required=True)
    ap.add_argument("--ult_mult", type=float, required=True)
    ap.add_argument("--ult_mana", type=float, required=True)

    # optional
    ap.add_argument("--attack_mana_recov", type=float, default=1.0)
    ap.add_argument("--ult_buff_mult", type=float, default=1.5)
    ap.add_argument("--ult_buff_ticks_factor", type=float, default=10.0)
    ap.add_argument("--hammer_basic_mult", type=float, default=2.0)
    ap.add_argument("--hammer_basic_charges", type=int, default=3)

    args = ap.parse_args()

    params = vars(args)
    ticks = params.pop("ticks")
    trials = params.pop("trials")
    seed = params.pop("seed")

    basic, skill1, skill2, ult = mean_total_damage_5001(params, ticks, trials=trials, seed=seed)
    total = basic + skill1 + skill2 + ult

    print("=== mean total damage ===")
    print(f"basic : {basic:.6f}")
    print(f"skill1: {skill1:.6f}")
    print(f"skill2: {skill2:.6f}")
    print(f"ult   : {ult:.6f}")
    print(f"total : {total:.6f}")
    print()

    dps = mean_dps_5001(params, ticks, trials=trials, seed=seed)
    print("=== mean dps (per tick) ===")
    for k in ["basic", "skill1", "skill2", "ult", "total"]:
        print(f"{k:5s}: {dps[k]:.6f}")

    if total > 0:
        print()
        print("=== share ===")
        print(f"basic : {basic/total:.6%}")
        print(f"skill1: {skill1/total:.6%}")
        print(f"skill2: {skill2/total:.6%}")
        print(f"ult   : {ult/total:.6%}")

    return 0


if __name__ == "__main__":
    raise SystemExit(_cli())
