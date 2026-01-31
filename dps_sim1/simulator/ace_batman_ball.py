from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Any, Dict, Tuple, Optional

DamageTuple = Tuple[float, float, float, float, float]


def _round_half_up(x: float) -> int:
    # 0.5 は切り上げ（例: 12.5 -> 13）
    return int(math.floor(x + 0.5))


def _clamp01(p: float) -> float:
    if p < 0.0:
        return 0.0
    if p > 1.0:
        return 1.0
    return p


def _crit_multiplier(rng: random.Random, crit_rate_pct: float, crit_dmg: float) -> float:
    # crit_rate_pct は 0~100（%）
    p = _clamp01(crit_rate_pct / 100.0)
    return crit_dmg if rng.random() < p else 1.0


@dataclass(frozen=True)
class AceBatmanPitcherParams15110:
    tick: int

    attack_power: float
    attack_speed: float

    base_attack_mult: float

    skill1_rate: float          # 0~100 (%)
    skill1_react: int           # 1~3
    skill1_mult: float

    ult_mana: float
    ult_mult: float

    add_rate: float             # 0~100 (%)
    add_mult: float

    crit_rate: float            # 0~100 (%)
    crit_dmg: float             # multiplier (e.g. 2.5)

    seed: Optional[int] = None
    trials: int = 20000

    def validated(self) -> "AceBatmanPitcherParams15110":
        if self.tick < 0:
            raise ValueError("tick must be >= 0")
        if self.attack_power < 0:
            raise ValueError("attack_power must be >= 0")
        if self.attack_speed <= 0:
            raise ValueError("attack_speed must be > 0")

        for name, v in [
            ("base_attack_mult", self.base_attack_mult),
            ("skill1_mult", self.skill1_mult),
            ("ult_mult", self.ult_mult),
            ("add_mult", self.add_mult),
            ("crit_dmg", self.crit_dmg),
            ("ult_mana", self.ult_mana),
        ]:
            if v < 0:
                raise ValueError(f"{name} must be >= 0")

        for name, v in [
            ("skill1_rate", self.skill1_rate),
            ("add_rate", self.add_rate),
            ("crit_rate", self.crit_rate),
        ]:
            if not (0 <= v <= 100):
                raise ValueError(f"{name} must be in [0, 100]")

        if not (1 <= int(self.skill1_react) <= 3):
            raise ValueError("skill1_react must be an integer in [1, 3]")

        if self.trials <= 0:
            raise ValueError("trials must be > 0")

        return self

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "AceBatmanPitcherParams15110":
        return AceBatmanPitcherParams15110(
            tick=int(d.get("tick", 0)),
            attack_power=float(d["attack_power"]),
            attack_speed=float(d["attack_speed"]),
            base_attack_mult=float(d["base_attack_mult"]),
            skill1_rate=float(d["skill1_rate"]),
            skill1_react=int(d["skill1_react"]),
            skill1_mult=float(d["skill1_mult"]),
            ult_mana=float(d["ult_mana"]),
            ult_mult=float(d["ult_mult"]),
            add_rate=float(d["add_rate"]),
            add_mult=float(d["add_mult"]),
            crit_rate=float(d["crit_rate"]),
            crit_dmg=float(d["crit_dmg"]),
            seed=(None if d.get("seed", None) is None else int(d["seed"])),
            trials=int(d.get("trials", 20000)),
        )


def _simulate_once(p: AceBatmanPitcherParams15110, rng: random.Random) -> DamageTuple:
    """
    1 tick = 1 行動（基本攻撃 or skill1の1回攻撃 or ult）
    mana回復は各tickの最後に +1/attack_speed
    """
    tick_n = p.tick
    if tick_n == 0:
        return (0.0, 0.0, 0.0, 0.0, 0.0)

    mana = 0.0

    # バフ残りtick数（このtick開始時点で >0 ならバフ有効）
    buff_remain = 0

    # ストライクアウト残り攻撃回数（このtickで実行する分も含めた残数）
    skill1_remain = 0

    basic_total = 0.0
    skill1_total = 0.0
    ult_total = 0.0  # ult + add をここに合算

    p_skill1 = _clamp01(p.skill1_rate / 100.0)
    p_add = _clamp01(p.add_rate / 100.0)

    # バフ時間: 8 * attack_speed tick（整数化の仕方は仕様が曖昧なので half-up 丸め）
    buff_duration = _round_half_up(8.0 * p.attack_speed)
    if buff_duration < 0:
        buff_duration = 0

    mana_regen = 1.0 / p.attack_speed

    for _ in range(tick_n):
        buff_active = buff_remain > 0
        dec_buff_after = 1 if buff_active else 0

        # --- 行動選択（優先度: ult > 継続skill1 > 通常抽選） ---
        # ult_mana が 0 の場合の挙動は危険なので、validatedで ult_mana>=0 は許してるが、
        # 実運用では ult_mana>0 を推奨。ここでは ult_mana>0 のときのみ発動判定にする。
        if p.ult_mana > 0 and mana >= p.ult_mana:
            # フィニッシュピッチ
            cm = _crit_multiplier(rng, p.crit_rate, p.crit_dmg)
            ult_total += p.attack_power * p.ult_mult * cm

            # マナ0、バフ開始
            mana = 0.0
            buff_remain = buff_duration

            # ※ここで skill1 を中断するかは仕様が曖昧。ここでは「中断（キャンセル）」扱い。
            skill1_remain = 0

        elif skill1_remain > 0:
            # ストライクアウト継続（1tickで1回攻撃）
            cm = _crit_multiplier(rng, p.crit_rate, p.crit_dmg)
            skill1_total += p.attack_power * p.skill1_mult * cm
            skill1_remain -= 1

        else:
            # 通常: skill1抽選 or basic
            if rng.random() < p_skill1:
                # ストライクアウト開始
                skill1_remain = int(p.skill1_react)
                cm = _crit_multiplier(rng, p.crit_rate, p.crit_dmg)
                skill1_total += p.attack_power * p.skill1_mult * cm
                skill1_remain -= 1
            else:
                # 基本攻撃（バフ中のみ add 抽選で追加ダメージ）
                add_proc = buff_active and (rng.random() < p_add)

                cm = _crit_multiplier(rng, p.crit_rate, p.crit_dmg)

                # 仕様どおり「add は basic に加算される」けど、集計上は
                # basic部分と add部分を分けて返したいので、同一クリティカル倍率で分割計上する
                basic_total += p.attack_power * p.base_attack_mult * cm
                if add_proc:
                    ult_total += p.attack_power * p.add_mult * cm

        # --- tick末処理 ---
        if dec_buff_after:
            buff_remain -= 1

        mana += mana_regen

    return (basic_total, skill1_total, 0.0, 0.0, ult_total)


def mean_total_damage_15110(params: Dict[str, Any]) -> DamageTuple:
    """
    外部から呼ぶ用。
    params は dict を受け取り、平均ダメージ(5-tuple)を返す。
      (basic, skill1, skill2, skill3, ult)
    ※ ult は「フィニッシュピッチ + バフ中の追加攻撃(add)」の合算
    """
    p = AceBatmanPitcherParams15110.from_dict(params).validated()

    rng = random.Random(p.seed)

    b = s1 = u = 0.0
    for _ in range(p.trials):
        tb, ts1, _, _, tu = _simulate_once(p, rng)
        b += tb
        s1 += ts1
        u += tu

    inv = 1.0 / float(p.trials)
    return (b * inv, s1 * inv, 0.0, 0.0, u * inv)


def mean_total_damage_15110_compact(params: Dict[str, Any]) -> Tuple[float, float, float]:
    """
    要求仕様の「3項目だけほしい」場合のショートカット。
      (basic_total, skill1_total, ult_plus_add_total)
    """
    basic, skill1, _, _, ult = mean_total_damage_15110(params)
    return (basic, skill1, ult)

