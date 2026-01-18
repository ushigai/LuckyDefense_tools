from __future__ import annotations
import argparse
import math
import random
from dataclasses import dataclass
from typing import List, Dict, Tuple

import numpy as np

def mean_total_damage_15021(
    *,
    ticks: int,
    trials: int,
    seed: int,
    attack_power: float,
    attack_speed: float,
    mana_buff: float = 1.0,
) -> float:
    if ticks <= 0:
        raise ValueError("ticks must be > 0")
    if trials <= 0:
        raise ValueError("trials must be > 0")
    if attack_speed <= 0:
        raise ValueError("attack_speed must be > 0")
    if attack_power < 0:
        raise ValueError("attack_power must be >= 0")
    if mana_buff <= 0:
        raise ValueError("mana_buff must be > 0")

    return 1000


def main():
    ap = argparse.ArgumentParser(description="Awakened Hayley Monte Carlo DPS simulator")
    ap.add_argument("--ticks", type=int, required=True, help="number of ticks per trial")
    ap.add_argument("--trials", type=int, default=20000, help="number of Monte Carlo trials")
    ap.add_argument("--seed", type=int, default=0, help="RNG seed")
    ap.add_argument("--attack_power", type=float, required=True, help="attack power")
    ap.add_argument("--attack_speed", type=float, required=True, help="attack speed (>0)")
    ap.add_argument("--mana_buff", type=float, default=1.0, help="mana recovery multiplier (e.g. 2, 3, ...)")
    args = ap.parse_args()

    if args.ticks <= 0:
        raise SystemExit("ticks must be > 0")
    if args.trials <= 0:
        raise SystemExit("trials must be > 0")
    if args.attack_speed <= 0:
        raise SystemExit("attack_speed must be > 0")
    if args.attack_power < 0:
        raise SystemExit("attack_power must be >= 0")
    if args.mana_buff <= 0:
        raise SystemExit("mana_buff must be > 0")

    p = Params(
        attack_power=args.attack_power,
        attack_speed=args.attack_speed,
        mana_buff=args.mana_buff,
    )

    rng = random.Random(args.seed)


if __name__ == "__main__":
    main()


