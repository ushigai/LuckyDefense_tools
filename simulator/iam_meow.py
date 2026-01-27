# iam_nyan_15004.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Union, Tuple
import random
import math


@dataclass(frozen=True)
class IamNyanParams15004:
    # core
    attack_power: float
    attack_speed: float  # attacks per second (tick length = 1/attack_speed sec)
    mana_buff: float

    # proc rates (0..100)
    skill1_rate: float
    skill2_rate: float

    # damage multipliers
    skill1_mult: float
    skill2_mult: float
    ult_mult: float

    # ult
    ult_mana: float
    ult_cooldown: int  # ticks

    # crit
    crit_rate: float   # 0..100
    crit_dmg: float    # e.g. 2.5


def _validate_params(p: IamNyanParams15004) -> None:
    if p.attack_speed <= 0:
        raise ValueError("attack_speed must be > 0")
    if p.mana_buff <= 0:
        raise ValueError("mana_buff must be > 0")
    for name, r in [("skill1_rate", p.skill1_rate), ("skill2_rate", p.skill2_rate), ("crit_rate", p.crit_rate)]:
        if not (0 <= r <= 100):
            raise ValueError(f"{name} must be in [0, 100]")
    if p.skill1_rate + p.skill2_rate > 100 + 1e-9:
        raise ValueError("skill1_rate + skill2_rate must be <= 100")
    if p.ult_cooldown < 0:
        raise ValueError("ult_cooldown must be >= 0")
    if p.crit_dmg <= 0:
        raise ValueError("crit_dmg must be > 0")
    if p.attack_power < 0:
        raise ValueError("attack_power must be >= 0")
    # multipliers can be any >=0 (allow 0)
    for name, m in [("skill1_mult", p.skill1_mult), ("skill2_mult", p.skill2_mult), ("ult_mult", p.ult_mult)]:
        if m < 0:
            raise ValueError(f"{name} must be >= 0")
    if p.ult_mana < 0:
        raise ValueError("ult_mana must be >= 0")


def _roll_crit(rng: random.Random, crit_rate: float, crit_dmg: float) -> float:
    """Return multiplier (1.0 or crit_dmg). crit_rate is 0..100."""
    if crit_rate <= 0:
        return 1.0
    # r in [0,100)
    return crit_dmg if (rng.random() * 100.0) < crit_rate else 1.0


def _damage_for(action: str, p: IamNyanParams15004) -> float:
    """Base damage without crit."""
    if action == "basic":
        mult = 1.0
    elif action == "skill1":
        mult = p.skill1_mult
    elif action == "skill2":
        mult = p.skill2_mult
    elif action == "ult":
        mult = p.ult_mult
    else:
        raise ValueError(f"unknown action: {action}")
    return p.attack_power * mult


def simulate_one_trial_breakdown_15004(
    p: IamNyanParams15004,
    ticks: int,
    rng: random.Random,
) -> Tuple[float, float, float, float, float]:
    """
    1 trial のダメージ内訳を返す。
    戻り値: (basic, skill1, skill2, skill3, ult)
      - skill3 は存在しないため常に 0.0
    """
    if ticks <= 0:
        return 0.0, 0.0, 0.0, 0.0, 0.0

    mana = 0.0
    cd = 0  # remaining cooldown ticks

    dmg_basic = 0.0
    dmg_skill1 = 0.0
    dmg_skill2 = 0.0
    dmg_ult = 0.0

    per_tick_regen = (1.0 / p.attack_speed) * p.mana_buff

    for _ in range(ticks):
        if cd > 0:
            cd -= 1
            # cooldown中は「基本攻撃、スキル、究極、マナ回復全て不可」
            continue

        # action selection (ult has priority)
        action: str
        if mana >= p.ult_mana:
            action = "ult"
            mana = 0.0
            cd = p.ult_cooldown
        else:
            r = rng.random() * 100.0
            if r < p.skill1_rate:
                action = "skill1"
            elif r < (p.skill1_rate + p.skill2_rate):
                action = "skill2"
            else:
                action = "basic"

        dmg = _damage_for(action, p)
        dmg *= _roll_crit(rng, p.crit_rate, p.crit_dmg)

        if action == "basic":
            dmg_basic += dmg
            mana += 1.0 * p.mana_buff
        elif action == "skill1":
            dmg_skill1 += dmg
        elif action == "skill2":
            dmg_skill2 += dmg
        elif action == "ult":
            dmg_ult += dmg
        else:
            raise RuntimeError(f"unknown action: {action}")

        # end-of-tick regen
        mana += per_tick_regen

    return dmg_basic, dmg_skill1, dmg_skill2, 0.0, dmg_ult

def simulate_one_trial_15004(p: IamNyanParams15004, ticks: int, rng: random.Random) -> float:
    """
    1 trial の総ダメージを返す。
    仕様:
      - 1 tick ごとに行動判定（cooldown中は一切不可 + マナ回復も無し）
      - cooldownでない場合:
          1) (tick開始時) mana >= ult_mana なら ult を優先発動し mana=0
          2) そうでなければ基本攻撃判定:
               skill1_rate% -> skill1
               skill2_rate% -> skill2
               残り -> basic
          3) 行動に応じてダメージ（critあり）
          4) マナ回復:
               - basic の時だけ +1
               - tick終端で +1/attack_speed
             ※いずれも mana_buff を乗算
      - ult 発動後は「次の tick から」ult_cooldown tick 分 cooldown（その期間は何もできない）
    """
    if ticks <= 0:
        return 0.0

    mana = 0.0
    cd = 0  # remaining cooldown ticks (counts down on each tick)

    total = 0.0
    per_tick_regen = (1.0 / p.attack_speed) * p.mana_buff

    for _ in range(ticks):
        if cd > 0:
            cd -= 1
            # cooldown中は「基本攻撃、スキル、究極、マナ回復全て不可」
            continue

        # action selection (ult has priority)
        action: str
        if mana >= p.ult_mana:
            action = "ult"
            mana = 0.0
            # cooldown starts from next tick
            cd = p.ult_cooldown
        else:
            r = rng.random() * 100.0
            if r < p.skill1_rate:
                action = "skill1"
            elif r < (p.skill1_rate + p.skill2_rate):
                action = "skill2"
            else:
                action = "basic"

        # damage (with crit)
        dmg = _damage_for(action, p)
        dmg *= _roll_crit(rng, p.crit_rate, p.crit_dmg)
        total += dmg

        # mana recovery: basic gives +1, then end-of-tick regen
        if action == "basic":
            mana += 1.0 * p.mana_buff
        mana += per_tick_regen

    return total


def simulate_many_15004(
    p: IamNyanParams15004,
    ticks: int,
    trials: int = 10000,
    seed: Optional[int] = 1,
) -> Dict[str, float]:
    """
    Monte Carlo:
      returns dict: mean, stdev, stderr
    """
    _validate_params(p)
    if ticks < 0:
        raise ValueError("ticks must be >= 0")
    if trials <= 0:
        raise ValueError("trials must be > 0")

    rng = random.Random(seed)

    # Welford for numerically stable mean/variance
    mean = 0.0
    m2 = 0.0
    n = 0

    for _ in range(trials):
        x = simulate_one_trial_15004(p, ticks, rng)
        n += 1
        delta = x - mean
        mean += delta / n
        delta2 = x - mean
        m2 += delta * delta2

    var = (m2 / (n - 1)) if n > 1 else 0.0
    stdev = math.sqrt(var)
    stderr = stdev / math.sqrt(n) if n > 0 else 0.0

    return {"mean": mean, "stdev": stdev, "stderr": stderr}


def _ticks_from_duration(durationSec: float, attack_speed: float) -> int:
    """
    tick = 1/attack_speed 秒 とみなし、durationSec を tick に変換。
    端数は「四捨五入」ではなく「切り捨て」にしています（安定重視）。
    """
    if durationSec <= 0:
        return 0
    if attack_speed <= 0:
        raise ValueError("attack_speed must be > 0")
    return int(durationSec * attack_speed)


def mean_total_damage_15004(
    options: Optional[Dict[str, Any]] = None,
    /,
    **kwargs: Any,
) -> Tuple[float, float, float, float, float]:
    """
    外部から「平均総ダメージ内訳」を取りたい用。

    戻り値: (basic, skill1, skill2, skill3, ult)
      - skill3 は存在しないため常に 0.0
    """
    data: Dict[str, Any] = {}
    if options:
        data.update(options)
    data.update(kwargs)

    # allow legacy typos (cirt_*)
    if "crit_rate" not in data and "cirt_rate" in data:
        data["crit_rate"] = data["cirt_rate"]
    if "crit_dmg" not in data and "cirt_dmg" in data:
        data["crit_dmg"] = data["cirt_dmg"]

    required = [
        "attack_power", "attack_speed",
        "skill1_rate", "skill2_rate",
        "skill1_mult", "skill2_mult",
        "ult_mult", "ult_mana", "ult_cooldown",
    ]
    missing = [k for k in required if k not in data]
    if missing:
        raise KeyError(f"missing required options: {missing}")

    p = IamNyanParams15004(
        attack_power=float(data["attack_power"]),
        attack_speed=float(data["attack_speed"]),
        mana_buff=float(data.get("mana_buff", 1.0)),

        skill1_rate=float(data["skill1_rate"]),
        skill2_rate=float(data["skill2_rate"]),

        skill1_mult=float(data["skill1_mult"]),
        skill2_mult=float(data["skill2_mult"]),
        ult_mult=float(data["ult_mult"]),

        ult_mana=float(data["ult_mana"]),
        ult_cooldown=int(data["ult_cooldown"]),

        crit_rate=float(data.get("crit_rate", 0.0)),
        crit_dmg=float(data.get("crit_dmg", 1.0)),
    )
    _validate_params(p)

    trials = int(data.get("trials", 10000))
    if trials <= 0:
        raise ValueError("trials must be > 0")
    seed = data.get("seed", 1)

    # ticks resolution: ticks preferred, else durationSec
    if "ticks" in data and data["ticks"] is not None:
        ticks = int(data["ticks"])
    else:
        durationSec = float(data.get("durationSec", 60.0))
        ticks = _ticks_from_duration(durationSec, p.attack_speed)

    rng = random.Random(seed)

    s_basic = s_s1 = s_s2 = s_s3 = s_ult = 0.0
    for _ in range(trials):
        b, s1, s2, s3, u = simulate_one_trial_breakdown_15004(p, ticks, rng)
        s_basic += b
        s_s1 += s1
        s_s2 += s2
        s_s3 += s3
        s_ult += u

    inv = 1.0 / float(trials)
    return s_basic * inv, s_s1 * inv, s_s2 * inv, s_s3 * inv, s_ult * inv

def mean_dps_15004(
    options: Optional[Dict[str, Any]] = None,
    /,
    **kwargs: Any,
) -> float:
    """
    平均DPS（= 平均総ダメージ / 経過秒）を返すユーティリティ。
    - ticks 指定時は durationSec = ticks / attack_speed とみなす。
    - durationSec 指定時はそのまま。
    """
    data: Dict[str, Any] = {}
    if options:
        data.update(options)
    data.update(kwargs)

    if "ticks" in data and data["ticks"] is not None:
        ticks = int(data["ticks"])
        attack_speed = float(data["attack_speed"])
        durationSec = ticks / attack_speed if attack_speed > 0 else 0.0
    else:
        durationSec = float(data.get("durationSec", 60.0))

    b, s1, s2, s3, u = mean_total_damage_15004(data)
    total = b + s1 + s2 + s3 + u
    return total / durationSec if durationSec > 0 else 0.0

if __name__ == "__main__":
    # simple CLI
    import argparse

    ap = argparse.ArgumentParser(description="IamNyan(15004) Monte Carlo total damage simulator")
    ap.add_argument("--attack_power", type=float, required=True)
    ap.add_argument("--attack_speed", type=float, required=True)
    ap.add_argument("--skill1_rate", type=float, required=True)
    ap.add_argument("--skill2_rate", type=float, required=True)
    ap.add_argument("--skill1_mult", type=float, required=True)
    ap.add_argument("--skill2_mult", type=float, required=True)
    ap.add_argument("--ult_mult", type=float, required=True)
    ap.add_argument("--ult_mana", type=float, required=True)
    ap.add_argument("--ult_cooldown", type=int, required=True)

    ap.add_argument("--mana_buff", type=float, default=1.0)
    ap.add_argument("--crit_rate", type=float, default=0.0)
    ap.add_argument("--crit_dmg", type=float, default=1.0)

    g = ap.add_mutually_exclusive_group(required=False)
    g.add_argument("--ticks", type=int, default=None)
    g.add_argument("--durationSec", type=float, default=60.0)

    ap.add_argument("--trials", type=int, default=10000)
    ap.add_argument("--seed", type=int, default=1)

    args = ap.parse_args()

    opts = vars(args)
    b, s1, s2, s3, u = mean_total_damage_15004(opts)
    mean_total = b + s1 + s2 + s3 + u
    mean_dps = mean_dps_15004(opts)
    ticks = opts["ticks"] if opts["ticks"] is not None else _ticks_from_duration(opts["durationSec"], opts["attack_speed"])
    print(f"ticks={ticks}, trials={opts['trials']}, seed={opts['seed']}")
    print(f"mean_total_damage={mean_total:.6f}")
    print(f"mean_dps={mean_dps:.6f}")

