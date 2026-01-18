"""
ゲームのキャラのDPS算出をモンテカルロシミュレーションを使用して行いたい。

そのキャラは1000tickに1回攻撃を行う。攻撃時に8%の確率でスキルを発動し自身に7000tick間速度バフをかける。速度バフ間では870tickごとに攻撃を行うようになる。速度バフ間でさらに速度バフをかけるスキルを発動した場合バフ時間を7000tickにリセットするだけで時間は加算されない。

仕様で曖昧な部分があれば最後にまとめて指摘してほしい
"""

import random
import math
from dataclasses import dataclass
from typing import Optional, Dict, Any, List


@dataclass
class SimResult:
    mean_total_damage: float
    mean_dps: float
    ci95_total_damage: float
    percentiles_total_damage: Dict[str, float]
    mean_attacks: float
    mean_skill_procs: float


def _percentile(sorted_vals: List[float], q: float) -> float:
    """
    q in [0,1]. linear interpolation.
    """
    if not sorted_vals:
        return 0.0
    n = len(sorted_vals)
    if n == 1:
        return float(sorted_vals[0])
    pos = (n - 1) * q
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))
    if lo == hi:
        return float(sorted_vals[lo])
    w = pos - lo
    return float(sorted_vals[lo] * (1 - w) + sorted_vals[hi] * w)


def simulate_dps_monte_carlo(
    total_ticks: int,
    trials: int,
    *,
    p_skill: float = 0.08,
    base_interval: int = 1000,
    buff_interval: int = 870,
    buff_duration: int = 7000,
    dmg_basic: float = 1.0,
    dmg_skill: float = 0.0,
    tick_seconds: float = 1.0,
    first_attack_tick: int = 0,
    seed: Optional[int] = None,
    reschedule_on_buff_end: bool = False,
) -> SimResult:
    """
    reschedule_on_buff_end:
      False (default): 攻撃後に決めた次回攻撃tickは固定（途中でバフが切れても再計算しない）
      True          : バフが次回攻撃より先に切れる場合、残りクールダウンを「速度変化」で補正して遅らせる
                     （より“動的AS”っぽい挙動）
    """
    if total_ticks <= 0:
        raise ValueError("total_ticks must be > 0")
    if trials <= 0:
        raise ValueError("trials must be > 0")
    if not (0.0 <= p_skill <= 1.0):
        raise ValueError("p_skill must be in [0,1]")
    if base_interval <= 0 or buff_interval <= 0 or buff_duration <= 0:
        raise ValueError("intervals/duration must be > 0")
    if tick_seconds <= 0:
        raise ValueError("tick_seconds must be > 0")

    rng = random.Random(seed)

    totals: List[float] = []
    attacks_list: List[int] = []
    procs_list: List[int] = []

    total_seconds = total_ticks * tick_seconds

    for _ in range(trials):
        t = first_attack_tick
        buff_end = -10**18  # effectively "not buffed"
        next_attack = t

        total_damage = 0.0
        attacks = 0
        procs = 0

        while next_attack < total_ticks:
            t = next_attack

            # attack happens
            attacks += 1
            total_damage += dmg_basic

            # proc?
            if rng.random() < p_skill:
                procs += 1
                total_damage += dmg_skill
                buff_end = t + buff_duration  # reset only (no stacking)

            # decide next interval based on buff state right after this attack
            in_buff = (t < buff_end)
            interval = buff_interval if in_buff else base_interval
            candidate_next = t + interval

            if reschedule_on_buff_end and in_buff and buff_end < candidate_next:
                # buff expires before the scheduled next attack.
                # We model cooldown progress in normalized units:
                # during buff: progress rate = 1/buff_interval per tick
                progressed = (buff_end - t) / buff_interval  # < 1 here
                progressed = max(0.0, min(progressed, 1.0))
                remaining_norm = 1.0 - progressed
                # after buff ends, progress rate becomes 1/base_interval
                candidate_next = int(round(buff_end + remaining_norm * base_interval))

            next_attack = candidate_next

        totals.append(total_damage)
        attacks_list.append(attacks)
        procs_list.append(procs)

    # stats
    mean_total = sum(totals) / trials
    mean_attacks = sum(attacks_list) / trials
    mean_procs = sum(procs_list) / trials

    # sample std
    if trials >= 2:
        var = sum((x - mean_total) ** 2 for x in totals) / (trials - 1)
        std = math.sqrt(var)
        ci95 = 1.96 * std / math.sqrt(trials)  # normal approx
    else:
        ci95 = 0.0

    s = sorted(totals)
    p05 = _percentile(s, 0.05)
    p50 = _percentile(s, 0.50)
    p95 = _percentile(s, 0.95)

    mean_dps = mean_total / total_seconds

    return SimResult(
        mean_total_damage=mean_total,
        mean_dps=mean_dps,
        ci95_total_damage=ci95,
        percentiles_total_damage={"p05": p05, "p50": p50, "p95": p95},
        mean_attacks=mean_attacks,
        mean_skill_procs=mean_procs,
    )


if __name__ == "__main__":
    # 例：ダメージ未定なので dmg_basic=1 として「DPS=平均攻撃回数/秒」みたいに見る
    r = simulate_dps_monte_carlo(
        total_ticks=1000*10000,
        trials=100,
        p_skill=0.08,
        base_interval=1000,
        buff_interval=870,
        buff_duration=7000,
        dmg_basic=1.0,
        dmg_skill=0.0,
        tick_seconds=1.0,
        first_attack_tick=0,
        seed=1,
        reschedule_on_buff_end=False,
    )

    print("=== Result ===")
    print(f"mean_total_damage : {r.mean_total_damage:.6f}")
    print(f"mean_DPS          : {r.mean_dps:.6f}")
    print(f"95% CI (total)    : ±{r.ci95_total_damage:.6f}")
    print(f"percentiles total : p05={r.percentiles_total_damage['p05']:.6f}, "
          f"p50={r.percentiles_total_damage['p50']:.6f}, "
          f"p95={r.percentiles_total_damage['p95']:.6f}")
    print(f"mean_attacks      : {r.mean_attacks:.3f}")
    print(f"mean_skill_procs  : {r.mean_skill_procs:.3f}")

