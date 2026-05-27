from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Dict, Tuple, Optional
from dps_sim1.simulator.f32lock_rounding import round_half_up as round


def round_half_up(x: float) -> int:
    """仕様の round() を「0.5 は切り上げ」の四捨五入として扱う（x>=0 想定）"""
    return int(math.floor(x + 0.5))


@dataclass(frozen=True)
class CordiParams:
    # Core
    attack_power: float
    attack_speed: float

    # Rates (%)
    skill1_rate: float
    skill2_rate: float
    crit_rate: float

    # Multipliers (倍率)
    base_attack_mult: float
    skill1_mult: float
    skill2_mult: float
    skill2_dot: float
    skill3_mult: float
    ult_mult: float
    crit_dmg: float

    # Counts / timings
    skill1_count: int
    ult_mana: float
    ult_time: float

    # Mana
    attack_mana_recov: float
    mana_buff: float = 1.0  # 仕様文にあるので採用（末尾の列挙に無かったが重要）

    @staticmethod
    def from_dict(d: Dict) -> "CordiParams":
        # 必須キー（mana_buff は無ければ 1）
        required = [
            "attack_power", "attack_speed",
            "skill1_rate", "skill2_rate",
            "base_attack_mult",
            "skill1_mult", "skill1_count",
            "skill2_mult", "skill2_dot",
            "skill3_mult",
            "crit_rate", "crit_dmg",
            "ult_mult", "ult_mana", "ult_time",
            "attack_mana_recov",
        ]
        missing = [k for k in required if k not in d]
        if missing:
            raise KeyError(f"missing params: {missing}")

        return CordiParams(
            attack_power=float(d["attack_power"]),
            attack_speed=float(d["attack_speed"]),
            skill1_rate=float(d["skill1_rate"]),
            skill2_rate=float(d["skill2_rate"]),
            crit_rate=float(d["crit_rate"]),
            base_attack_mult=float(d["base_attack_mult"]),
            skill1_mult=float(d["skill1_mult"]),
            skill1_count=int(d["skill1_count"]),
            skill2_mult=float(d["skill2_mult"]),
            skill2_dot=float(d["skill2_dot"]),
            skill3_mult=float(d["skill3_mult"]),
            ult_mult=float(d["ult_mult"]),
            crit_dmg=float(d["crit_dmg"]),
            ult_mana=float(d["ult_mana"]),
            ult_time=float(d["ult_time"]),
            attack_mana_recov=float(d["attack_mana_recov"]),
            mana_buff=float(d.get("mana_buff", 1.0)),
        )


class FrostStacks:
    """冷気効果（最大10、各スタックは個別に期限）"""
    __slots__ = ("expirations", "max_stacks")

    def __init__(self, max_stacks: int = 10):
        self.expirations = []  # list[int] of expire_tick (exclusive)
        self.max_stacks = max_stacks

    def purge(self, tick: int) -> None:
        if not self.expirations:
            return
        # 順不同になることがあるので filter
        self.expirations = [e for e in self.expirations if e > tick]

    def count(self) -> int:
        return len(self.expirations)

    def reset(self) -> None:
        self.expirations.clear()

    def add_one(self, tick: int, duration: int) -> None:
        if len(self.expirations) >= self.max_stacks:
            return
        self.expirations.append(tick + duration)

    def set_max_fresh(self, tick: int, duration: int) -> None:
        self.expirations = [tick + duration] * self.max_stacks


def simulate_one_trial(params: CordiParams, num_ticks: int, rng: random.Random) -> Tuple[float, float, float, float, float]:
    """
    1試行の総ダメージ（basic, skill1, skill2, skill3, ult_period_total）を返す。
    ult_period_total は「極寒期バフ期間中に発生した全ダメージ合計」（basic/skill/ult_mult含む）。
    """
    # Validate rates
    if params.skill1_rate < 0 or params.skill2_rate < 0 or params.skill1_rate + params.skill2_rate > 100:
        raise ValueError("skill rates must satisfy: 0<=skill1_rate,0<=skill2_rate, skill1+skill2<=100")
    if params.crit_rate < 0 or params.crit_rate > 100:
        raise ValueError("crit_rate must be 0..100")

    # Timing derived
    frost_duration = max(1, int(math.ceil(5.0 * params.attack_speed)))
    dot_interval = max(1, round_half_up(0.5 * params.attack_speed))
    ult_interval = max(1, round_half_up(params.attack_speed))
    ult_duration = max(1, round_half_up(params.attack_speed * params.ult_time))

    # Scheduled multi-hit counts per tick
    # buffer: to safely schedule hits beyond num_ticks-1
    buffer = max(params.skill1_count + 5, 6 * dot_interval + 5, ult_duration + 5)
    skill1_hits = [0] * (num_ticks + buffer)
    skill2_dot_hits = [0] * (num_ticks + buffer)

    # State
    mana = 0.0
    in_ult = False
    ult_ticks_left = 0
    ult_tick_index = 0  # 0.. while in ult
    skill_ult_recovery_ticks = max(0, int(round(0.8 * params.attack_speed)) - 1)
    recovery_remaining = 0

    frost = FrostStacks(max_stacks=10)

    # Totals
    total_basic = 0.0
    total_skill1 = 0.0
    total_skill2 = 0.0
    total_skill3 = 0.0
    total_ult_period = 0.0

    def roll_crit() -> float:
        if rng.random() < (params.crit_rate / 100.0):
            return params.crit_dmg
        return 1.0

    def skill_damage_multiplier() -> float:
        # 極寒期中は「スキルダメージ」1.3倍
        return 1.3 if in_ult else 1.0

    def add_damage(amount: float, bucket: str) -> None:
        nonlocal total_basic, total_skill1, total_skill2, total_skill3, total_ult_period
        if bucket == "basic":
            total_basic += amount
        elif bucket == "skill1":
            total_skill1 += amount
        elif bucket == "skill2":
            total_skill2 += amount
        elif bucket == "skill3":
            total_skill3 += amount
        elif bucket == "ult":  # ult_mult はここには分けず、ult_period_totalにのみ入れる（仕様の返り値に合わせる）
            pass
        else:
            raise ValueError(f"unknown bucket: {bucket}")

        if in_ult:
            total_ult_period += amount

    def hit_basic() -> None:
        dmg = params.attack_power * params.base_attack_mult
        dmg *= roll_crit()
        add_damage(dmg, "basic")

    def hit_skill1(tick: int) -> None:
        # 冷気の期限整理
        frost.purge(tick)

        # 「冷気10のとき skill1 がヒットしたら爆発 -> 冷気0」
        exploded = False
        if frost.count() >= 10:
            # 爆発（skill3）
            exp_dmg = params.attack_power * params.skill3_mult
            exp_dmg *= skill_damage_multiplier()
            exp_dmg *= roll_crit()
            add_damage(exp_dmg, "skill3")
            frost.reset()
            exploded = True

        # skill1本体
        dmg = params.attack_power * params.skill1_mult
        dmg *= skill_damage_multiplier()
        dmg *= roll_crit()
        add_damage(dmg, "skill1")

        # ヒットにより冷気+1
        if not exploded:
            frost.add_one(tick, frost_duration)

    def hit_skill2_mult(tick: int) -> None:
        frost.purge(tick)
        dmg = params.attack_power * params.skill2_mult
        dmg *= skill_damage_multiplier()
        dmg *= roll_crit()
        add_damage(dmg, "skill2")
        frost.add_one(tick, frost_duration)

    def hit_skill2_dot(tick: int) -> None:
        frost.purge(tick)
        dmg = params.attack_power * params.skill2_dot
        dmg *= skill_damage_multiplier()
        dmg *= roll_crit()
        add_damage(dmg, "skill2")
        frost.add_one(tick, frost_duration)

    def hit_ult_pulse(tick: int) -> None:
        # ult_mult ダメージ + 冷気を即座に最大
        frost.purge(tick)
        dmg = params.attack_power * params.ult_mult
        dmg *= skill_damage_multiplier()
        dmg *= roll_crit()
        # 返り値仕様に合わせ、ult_multは「ultカテゴリ」には分けず、ult_period_totalだけ増やす
        # ただしult_period_totalには add_damage経由で入れたいので bucketは適当でOK
        # -> bucketに入れないため add_damageを直接使わず、ult_periodだけ加算する
        nonlocal total_ult_period
        if in_ult:
            total_ult_period += dmg
        else:
            # 原理上ここには来ないが安全に
            pass

        # 冷気最大化（期限は全て fresh にする）
        frost.set_max_fresh(tick, frost_duration)

    for t in range(num_ticks):
        # 期限切れ冷気はtick開始時に落とす
        frost.purge(t)

        # --- 1) 極寒期の定期パルス（先に発生） ---
        if in_ult and ult_ticks_left > 0:
            if (ult_tick_index % ult_interval) == 0:
                hit_ult_pulse(t)

        # --- 2) 既にスケジュールされている DoT/多段 ---
        # skill2 dot
        c2 = skill2_dot_hits[t]
        for _ in range(c2):
            hit_skill2_dot(t)

        # skill1 multi-hits
        c1 = skill1_hits[t]
        for _ in range(c1):
            hit_skill1(t)

        # --- 3) このtickの行動（基本/skill1/skill2/ult） ---
        action = "none"

        if recovery_remaining > 0:
            recovery_remaining -= 1
        else:
            # 極寒期中は「マナ回復できない」＆「再ult判定もしない」として通常行動のみ
            if (not in_ult) and (mana >= params.ult_mana):
                # ult発動（このtickの行動をultに置換）
                in_ult = True
                ult_ticks_left = ult_duration
                ult_tick_index = 0
                action = "ult"

                # 発動即時にパルスが出る想定（ult_tick_index==0 と同義）
                # ただしこのtick既に上で「in_ult=False」だったので出ていないためここで1回入れる
                hit_ult_pulse(t)
                recovery_remaining = skill_ult_recovery_ticks

            else:
                r = rng.random() * 100.0
                if r < params.skill1_rate:
                    action = "skill1"
                    # このtickに1発即時ヒット
                    hit_skill1(t)
                    # 残り (skill1_count-1) を次tick以降に毎tick1回ずつ
                    for i in range(1, max(0, params.skill1_count) ):
                        skill1_hits[t + i] += 1
                    recovery_remaining = skill_ult_recovery_ticks

                elif r < params.skill1_rate + params.skill2_rate:
                    action = "skill2"
                    # 即時: skill2_mult + skill2_dot（別ヒット扱い）
                    hit_skill2_mult(t)
                    hit_skill2_dot(t)
                    # 残り dot を6回、dot_intervalごとに
                    for k in range(1, 7):
                        skill2_dot_hits[t + k * dot_interval] += 1
                    recovery_remaining = skill_ult_recovery_ticks

                else:
                    action = "basic"
                    hit_basic()

        # --- 4) tick最後のマナ回復（極寒期中は回復不可） ---
        if not in_ult:
            gain = (1.0 / params.attack_speed) * params.mana_buff
            if action == "basic":
                gain += params.attack_mana_recov
            # mana_buff は持続回復に乗算し、通常の基本攻撃 +1 には乗算しない。
            mana += gain

        # --- 5) 極寒期の残りtick管理＆終了処理 ---
        if in_ult and ult_ticks_left > 0:
            ult_ticks_left -= 1
            ult_tick_index += 1
            if ult_ticks_left == 0:
                # バフ期間終了後にマナ0
                mana = 0.0
                in_ult = False

    return total_basic, total_skill1, total_skill2, total_skill3, total_ult_period


def mean_total_damage_15002(
    params_dict: Dict,
    num_ticks: int,
    trials: int = 2000,
    seed: int = 0,
) -> Tuple[float, float, float, float, float]:
    """
    女王コルディの期待総ダメージ（モンテカルロ平均）を返す。
    返り値: (basic_total, skill1_total, skill2_total, skill3_total, ult_period_total)

    - ult_period_total は「極寒期バフ期間中に発生したダメージ合計」（カテゴリと重複する“部分和”）
    """
    params = CordiParams.from_dict(params_dict)

    sum_basic = 0.0
    sum_s1 = 0.0
    sum_s2 = 0.0
    sum_s3 = 0.0
    sum_ult_period = 0.0

    base_rng = random.Random(seed)
    for i in range(trials):
        # 試行ごとに独立シード（再現性維持）
        trial_seed = base_rng.randrange(1 << 30)
        rng = random.Random(trial_seed)

        b, s1, s2, s3, up = simulate_one_trial(params, num_ticks, rng)
        sum_basic += b
        sum_s1 += s1
        sum_s2 += s2
        sum_s3 += s3
        sum_ult_period += up

    inv = 1.0 / trials
    return (sum_basic * inv, sum_s1 * inv, sum_s2 * inv, sum_s3 * inv, sum_ult_period * inv)


# おまけ：DPS（1tick=1単位時間）として見たい場合
def mean_dps_15002(params_dict: Dict, num_ticks: int, trials: int = 2000, seed: int = 0) -> Dict[str, float]:
    b, s1, s2, s3, up = mean_total_damage_15002(params_dict, num_ticks, trials, seed)
    total = b + s1 + s2 + s3
    return {
        "basic": b / num_ticks,
        "skill1": s1 / num_ticks,
        "skill2": s2 / num_ticks,
        "skill3": s3 / num_ticks,
        "total": total / num_ticks,
        "ult_period_total_per_tick": up / num_ticks,  # “部分和”なので参考値
    }
