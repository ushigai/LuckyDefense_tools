from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Any, Dict, Tuple


DamageTuple = Tuple[float, float, float, float, float]  # (basic, skill1, skill2, skill3, ult)


def round_half_up(x: float) -> int:
    return int(math.floor(x + 0.5))


@dataclass(frozen=True)
class TopVainParams15011:
    tick: int                 # ベース計測tick（非バフ速度基準の“時間”を表す想定）
    trials: int               # モンテカルロ試行回数
    seed: int | None

    base_attack_mult: float
    attack_speed: float
    attack_power: float
    skill1_mult: float
    skill2_mult: float
    skill2_going: int

    crit_rate: float          # 0..100
    crit_dmg: float           # 倍率（2.5, 150 など）
    ult_mana: float
    ult_buff: float

    def validated(self) -> "TopVainParams15011":
        if self.tick < 0:
            raise ValueError("tick must be >= 0")
        if self.trials <= 0:
            raise ValueError("trials must be > 0")
        if self.attack_speed <= 0:
            raise ValueError("attack_speed must be > 0")
        if self.attack_power < 0:
            raise ValueError("attack_power must be >= 0")
        if not (0 <= self.crit_rate <= 100):
            raise ValueError("crit_rate must be in [0, 100]")
        if self.crit_dmg < 0:
            raise ValueError("crit_dmg must be >= 0")
        if self.ult_mana < 0:
            raise ValueError("ult_mana must be >= 0")
        if self.ult_buff <= 0:
            raise ValueError("ult_buff must be > 0")
        return self

    @property
    def mana_regen_normal(self) -> float:
        return 1.0 / self.attack_speed

    @property
    def mana_regen_buff(self) -> float:
        return 1.0 / (self.attack_speed * self.ult_buff)

    @property
    def ult_buff_ticks(self) -> int:
        # バフ継続：15秒 * (buff中の行動回数/秒 = attack_speed*ult_buff)
        return max(0, round_half_up(15.0 * self.attack_speed * self.ult_buff))

    @property
    def ult_extend_ticks(self) -> int:
        # 計測tick延長：15秒の間に増える行動回数ぶん
        ext = 15.0 * self.attack_speed * (self.ult_buff - 1.0)
        return max(0, round_half_up(ext))


def _is_crit(rng: random.Random, crit_rate: float) -> bool:
    # crit_rate は 0..100
    return rng.random() < (crit_rate / 100.0)


def _apply_crit(base_damage: float, rng: random.Random, crit_rate: float, crit_dmg: float) -> float:
    if base_damage <= 0:
        return 0.0
    return base_damage * (crit_dmg if _is_crit(rng, crit_rate) else 1.0)


def _simulate_once(p: TopVainParams15011, rng: random.Random) -> DamageTuple:
    # 集計：非バフ中の basic/skill1/skill2 と、バフ中（ult枠）の合計
    basic_total = 0.0
    skill1_total = 0.0
    skill2_total = 0.0
    ult_bucket_total = 0.0

    # 行動制御
    next_action: str = "basic"  # "basic" | "skill1" | "skill2"
    triad_basic = 0             # 0..2（3回でskill1）
    block_basic = 0             # 0..15（15回到達でskill1後にskill2）
    pending_skill2 = False

    # マナ・バフ
    mana = 0.0
    buff_remaining = 0  # バフが残っている“行動tick数”（整数）

    # 計測tick（ベースtick + ultによる延長）
    t = 0
    end_tick = p.tick

    while t < end_tick:
        buff_active = buff_remaining > 0

        # tick開始時にult判定
        if mana >= p.ult_mana and p.ult_mana > 0:
            # ultをこのtickで発動（ダメージなし）
            mana = 0.0

            # バフ開始（このtickの後から有効として扱う：buff_remainingは次tickから減る）
            # 既にバフ中に再発動した場合は「更新（上書き）」として扱う
            buff_remaining = p.ult_buff_ticks

            # 計測tickを延長
            end_tick += p.ult_extend_ticks

            # ult tickの最後にマナ回復（このtickは“発動前状態”のbuff_activeで決める）
            mana += (p.mana_regen_buff if buff_active else p.mana_regen_normal)

            # このtickはバフ時間を消費しない（buffは次tickから減らす）
            t += 1
            continue

        # 通常行動（basic / skill1 / skill2）
        action = next_action

        if action == "basic":
            dmg = p.attack_power * p.base_attack_mult
            if buff_active:
                dmg *= 3.0
            dmg = _apply_crit(dmg, rng, p.crit_rate, p.crit_dmg)

            if buff_active:
                ult_bucket_total += dmg
            else:
                basic_total += dmg

            triad_basic += 1
            block_basic += 1

            if triad_basic == 3:
                triad_basic = 0
                next_action = "skill1"
                if block_basic == 15 and p.skill2_going:
                    pending_skill2 = True
            else:
                next_action = "basic"

        elif action == "skill1":
            dmg = p.attack_power * p.skill1_mult
            dmg = _apply_crit(dmg, rng, p.crit_rate, p.crit_dmg)

            if buff_active:
                ult_bucket_total += dmg
            else:
                skill1_total += dmg

            if pending_skill2:
                next_action = "skill2"
                pending_skill2 = False
            else:
                next_action = "basic"

        elif action == "skill2":
            dmg = p.attack_power * p.skill2_mult
            dmg = _apply_crit(dmg, rng, p.crit_rate, p.crit_dmg)

            if buff_active:
                ult_bucket_total += dmg
            else:
                skill2_total += dmg

            # サイクルリセット
            next_action = "basic"
            triad_basic = 0
            block_basic = 0
        else:
            # 念のため
            next_action = "basic"

        # tick最後にマナ回復
        mana += (p.mana_regen_buff if buff_active else p.mana_regen_normal)

        # バフ時間消費（このtickがバフ中なら1減らす）
        if buff_active:
            buff_remaining -= 1
            if buff_remaining < 0:
                buff_remaining = 0

        t += 1

    return (basic_total, skill1_total, skill2_total, 0.0, ult_bucket_total)


def mean_total_damage_15011(args: Dict[str, Any]) -> DamageTuple:
    """
    TopVain(15011) の平均ダメージ合計（モンテカルロ）を返す。

    返り値: (basic, skill1, skill2, skill3, ult)
      - basic/skill1/skill2: 非バフ中に発生した各ダメージ合計
      - ult: バフ中に発生した “基本(3倍) + skill1 + skill2” の合計
      - skill3: 未使用のため 0
    """
    p = TopVainParams15011(
        tick=int(args.get("tick", 0)),
        trials=int(args.get("trials", 20000)),
        seed=args.get("seed", None),

        base_attack_mult=float(args["base_attack_mult"]),
        attack_speed=float(args["attack_speed"]),
        attack_power=float(args["attack_power"]),
        skill1_mult=float(args["skill1_mult"]),
        skill2_mult=float(args["skill2_mult"]),
        skill2_going=int(args["skill2_going"]),

        crit_rate=float(args["crit_rate"]),
        crit_dmg=float(args["crit_dmg"]),
        ult_mana=float(args["ult_mana"]),
        ult_buff=float(args["ult_buff"]),
    ).validated()

    rng_master = random.Random(p.seed)

    acc0 = acc1 = acc2 = acc3 = acc4 = 0.0
    for _ in range(p.trials):
        # 試行ごとに独立な乱数系列（seed固定でも試行間で変化）
        trial_seed = rng_master.getrandbits(64)
        rng = random.Random(trial_seed)
        d0, d1, d2, d3, d4 = _simulate_once(p, rng)
        acc0 += d0
        acc1 += d1
        acc2 += d2
        acc3 += d3
        acc4 += d4

    inv = 1.0 / p.trials
    return (acc0 * inv, acc1 * inv, acc2 * inv, acc3 * inv, acc4 * inv)


def mean_dps_15011(args: Dict[str, Any]) -> DamageTuple:
    """
    参考：DPS（/秒）で返す版。

    “ベース計測tick” を「非バフ時の行動tick」= attack_speed 回/秒 と解釈し、
    経過秒数 = tick / attack_speed として DPS を算出する。
    """
    dmg = mean_total_damage_15011(args)
    attack_speed = float(args["attack_speed"])
    tick = int(args.get("tick", 0))
    time_sec = (tick / attack_speed) if attack_speed > 0 else 0.0
    if time_sec <= 0:
        return (0.0, 0.0, 0.0, 0.0, 0.0)
    return tuple(x / time_sec for x in dmg)  # type: ignore
