# doctor_pulse_14002.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Dict, Any, Tuple
import argparse
import random
import math


@dataclass
class DoctorPulseParams14002:
    attack_power: float
    attack_speed: float
    skill1_rate: float     # 0-100
    skill1_mult: float     # multiplier (e.g., 2 => 2x, 150 => 150x)
    ult_mult: float        # multiplier
    ult_mana: float
    mana_buff: float       # multiplies ALL mana gain
    crit_rate: float       # 0-100
    crit_dmg: float        # multiplier
    robots: float          # robots count (treated as numeric)

    def validate(self) -> None:
        if self.attack_speed <= 0:
            raise ValueError("attack_speed must be > 0")
        for name, v in [
            ("skill1_rate", self.skill1_rate),
            ("crit_rate", self.crit_rate),
        ]:
            if not (0.0 <= v <= 100.0):
                raise ValueError(f"{name} must be in [0,100], got {v}")
        if self.mana_buff <= 0:
            raise ValueError("mana_buff must be > 0")
        if self.crit_dmg < 1.0:
            raise ValueError("crit_dmg must be >= 1.0")
        if self.robots < 0:
            raise ValueError("robots must be >= 0")


def _apply_crit(rng: random.Random, dmg: float, crit_rate01: float, crit_dmg: float) -> float:
    if dmg <= 0:
        return 0.0
    if rng.random() < crit_rate01:
        return dmg * crit_dmg
    return dmg


def _simulate_one_trial(
    p: DoctorPulseParams14002,
    ticks: int,
    rng: random.Random,
) -> float:
    """
    1試行分の総ダメージを返す。
    状態:
      - 通常時: mana 回復あり
      - バフ中: ダメージ5倍、mana回復なし
      - ult発動tick: ダメージなし(仕様上未記載のため)、そのtick末もmana回復なし
      - バフ終了tick末: ult_mult*robots の追加ダメージ(バフ終了後扱いで5倍は乗せない)
    """
    # precompute
    skill1_p = p.skill1_rate / 100.0
    crit_p = p.crit_rate / 100.0

    # damage bases (仕様文の書き方に合わせ、attack_power を乗算する前提)
    basic_base = p.attack_power * p.robots * 10.0
    skill1_base = p.attack_power * p.skill1_mult * p.robots
    ult_explosion_base = p.attack_power * p.ult_mult * p.robots

    # mana gains per tick end (buff not active)
    regen_per_tick = 1.0 / p.attack_speed
    mana_gain_basic = (p.robots + regen_per_tick) * p.mana_buff
    mana_gain_skill1 = (regen_per_tick) * p.mana_buff

    # buff ticks (round per requirement)
    buff_ticks = int(round(10.0 * p.attack_speed))
    if buff_ticks < 1:
        buff_ticks = 1  # 0tickバフは扱いづらいので最低1に丸め

    total = 0.0
    mana = 0.0

    # バフ中の「バフが乗る攻撃tick」残り
    buff_remaining = 0
    # ult発動したtickは、tick末のmana回復を止めたい（バフ開始が即時のため）
    ult_cast_this_tick = False

    for _ in range(ticks):
        ult_cast_this_tick = False

        if buff_remaining > 0:
            # ===== buff状態 =====
            # mana回復できないので mana は固定（ult後0想定だが、念のため維持）
            # 行動は通常どおり (mana>=ult_mana にはならない想定)
            if rng.random() < skill1_p:
                # skill1
                dmg = _apply_crit(rng, skill1_base * 5.0, crit_p, p.crit_dmg)
                total += dmg
            else:
                # basic
                dmg = _apply_crit(rng, basic_base * 5.0, crit_p, p.crit_dmg)
                total += dmg

            # tick end: mana regen 없음
            buff_remaining -= 1

            # バフ終了直後に追加ダメージ（バフ終了後扱いで5倍は乗せない）
            if buff_remaining == 0:
                explosion = _apply_crit(rng, ult_explosion_base, crit_p, p.crit_dmg)
                total += explosion
                mana = 0.0  # 仕様: バフ時間終了後にマナ0で回復可能に

        else:
            # ===== normal状態 =====
            if mana >= p.ult_mana and p.ult_mana > 0:
                # ult
                mana = 0.0
                buff_remaining = buff_ticks
                ult_cast_this_tick = True
                # 仕様に「過熱自体の即時ダメージ」が書かれていないので 0 とする
            else:
                # skill1 or basic
                if rng.random() < skill1_p:
                    # skill1
                    dmg = _apply_crit(rng, skill1_base, crit_p, p.crit_dmg)
                    total += dmg
                    # tick end mana
                    mana += mana_gain_skill1
                else:
                    # basic
                    dmg = _apply_crit(rng, basic_base, crit_p, p.crit_dmg)
                    total += dmg
                    # tick end mana
                    mana += mana_gain_basic

            # ultを撃ったtick末は、バフ開始即時として mana回復なし
            if ult_cast_this_tick:
                pass

    return total


def simulate_14002(
    *,
    attack_power: float,
    attack_speed: float,
    skill1_rate: float,
    skill1_mult: float,
    ult_mult: float,
    ult_mana: float,
    crit_rate: float,
    crit_dmg: float,
    robots: float,
    mana_buff: float = 1.0,
    ticks: Optional[int] = None,
    durationSec: Optional[float] = None,
    trials: int = 10000,
    seed: int = 1,
) -> Dict[str, Any]:
    """
    平均総ダメージ・平均DPSなどを返すユーティリティ。
    - ticks 指定 or durationSec 指定（durationSecの場合 ticks=round(durationSec*attack_speed)）
    """
    if ticks is None:
        if durationSec is None:
            raise ValueError("Either ticks or durationSec must be provided.")
        # tick数の丸め要件
        ticks = int(round(float(durationSec) * float(attack_speed)))
    ticks = int(ticks)
    if ticks < 0:
        raise ValueError("ticks must be >= 0")
    if trials <= 0:
        raise ValueError("trials must be > 0")

    p = DoctorPulseParams14002(
        attack_power=float(attack_power),
        attack_speed=float(attack_speed),
        skill1_rate=float(skill1_rate),
        skill1_mult=float(skill1_mult),
        ult_mult=float(ult_mult),
        ult_mana=float(ult_mana),
        mana_buff=float(mana_buff),
        crit_rate=float(crit_rate),
        crit_dmg=float(crit_dmg),
        robots=float(robots),
    )
    p.validate()

    rng = random.Random(seed)

    total_sum = 0.0
    for _ in range(trials):
        total_sum += _simulate_one_trial(p, ticks, rng)

    mean_total = total_sum / trials

    # DPS: 1tick = 1/attack_speed sec と解釈 => elapsed_sec = ticks/attack_speed
    elapsed_sec = (ticks / p.attack_speed) if p.attack_speed > 0 else float("inf")
    mean_dps = (mean_total / elapsed_sec) if elapsed_sec > 0 else 0.0
    mean_dpt = (mean_total / ticks) if ticks > 0 else 0.0  # damage per tick (参考)

    return {
        "mean_total_damage": mean_total,
        "mean_dps": mean_dps,
        "mean_damage_per_tick": mean_dpt,
        "ticks": ticks,
        "elapsed_sec": elapsed_sec,
        "trials": trials,
        "seed": seed,
        "params": p,
    }


def mean_total_damage_14002(
    attack_power: float,
    attack_speed: float,
    skill1_rate: float,
    skill1_mult: float,
    ult_mult: float,
    ult_mana: float,
    crit_rate: float,
    crit_dmg: float,
    robots: float,
    mana_buff: float = 1.0,
    ticks: Optional[int] = None,
    durationSec: Optional[float] = None,
    trials: int = 10000,
    seed: int = 1,
) -> float:
    """
    外部から「平均総ダメージ」だけ取りたい用。
    引数はCLI相当の値を直接渡せる形。
    """
    return float(
        simulate_14002(
            attack_power=attack_power,
            attack_speed=attack_speed,
            skill1_rate=skill1_rate,
            skill1_mult=skill1_mult,
            ult_mult=ult_mult,
            ult_mana=ult_mana,
            crit_rate=crit_rate,
            crit_dmg=crit_dmg,
            robots=robots,
            mana_buff=mana_buff,
            ticks=ticks,
            durationSec=durationSec,
            trials=trials,
            seed=seed,
        )["mean_total_damage"]
    )


def _build_argparser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="Doctor Pulse (14002) Monte Carlo DPS/Total Damage simulator")
    ap.add_argument("--attack_power", type=float, required=True)
    ap.add_argument("--attack_speed", type=float, required=True)
    ap.add_argument("--skill1_rate", type=float, required=True, help="0-100 (%)")
    ap.add_argument("--skill1_mult", type=float, required=True, help="multiplier (2 => 2x, 150 => 150x)")
    ap.add_argument("--ult_mult", type=float, required=True)
    ap.add_argument("--ult_mana", type=float, required=True)
    ap.add_argument("--crit_rate", type=float, required=True, help="0-100 (%)")
    ap.add_argument("--crit_dmg", type=float, required=True)
    ap.add_argument("--robots", type=float, required=True)
    ap.add_argument("--mana_buff", type=float, default=1.0)

    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--ticks", type=int, help="simulate for N ticks")
    g.add_argument("--durationSec", type=float, help="simulate for N seconds (ticks = round(durationSec*attack_speed))")

    ap.add_argument("--trials", type=int, default=10000)
    ap.add_argument("--seed", type=int, default=1)
    return ap


def main() -> None:
    ap = _build_argparser()
    args = ap.parse_args()

    result = simulate_14002(
        attack_power=args.attack_power,
        attack_speed=args.attack_speed,
        skill1_rate=args.skill1_rate,
        skill1_mult=args.skill1_mult,
        ult_mult=args.ult_mult,
        ult_mana=args.ult_mana,
        crit_rate=args.crit_rate,
        crit_dmg=args.crit_dmg,
        robots=args.robots,
        mana_buff=args.mana_buff,
        ticks=args.ticks,
        durationSec=args.durationSec,
        trials=args.trials,
        seed=args.seed,
    )

    mean_total = result["mean_total_damage"]
    mean_dps = result["mean_dps"]
    mean_dpt = result["mean_damage_per_tick"]
    ticks = result["ticks"]
    elapsed_sec = result["elapsed_sec"]

    print("=== Doctor Pulse (14002) Simulation Result ===")
    print(f"ticks        : {ticks}")
    print(f"elapsed_sec  : {elapsed_sec:.6f}")
    print(f"trials       : {result['trials']}")
    print(f"seed         : {result['seed']}")
    print("---")
    print(f"mean_total_damage    : {mean_total:.6f}")
    print(f"mean_dps             : {mean_dps:.6f}")
    print(f"mean_damage_per_tick : {mean_dpt:.6f}")


if __name__ == "__main__":
    main()

