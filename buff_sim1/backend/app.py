from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Any, Dict, List, Literal, Tuple, DefaultDict
from collections import defaultdict

from flask import Flask, jsonify, request

FPS = 40
DURATION_SEC = 300
TOTAL_FRAMES = DURATION_SEC * FPS
DT = 1.0 / FPS

RefreshMode = Literal["refresh", "extend"]


def round_half_up(x: float) -> int:
    return int(math.floor(x + 0.5))


def frames_for_basic(attack_speed: float) -> int:
    if attack_speed <= 0:
        return 999999
    return max(1, round_half_up(FPS / attack_speed))


@dataclass
class BuffState:
    end_frame: int = -1  # exclusive
    active: bool = False


@dataclass
class Unit:
    unit_id: str
    kind: Literal["attacker", "penguin", "tiger"]
    base_attack_speed: float
    next_ready_frame: int = 0
    rng: random.Random | None = None


def _add_delta(delta: DefaultDict[int, DefaultDict[str, float]], frame: int, target_id: str, amount: float) -> None:
    if frame < 0 or frame > TOTAL_FRAMES:
        return
    delta[frame][target_id] += amount


def _apply_buff_with_refresh(
    *,
    buff_state: BuffState,
    refresh_mode: RefreshMode,
    start_frame: int,
    duration_frames: int,
    targets: List[str],
    delta_map: DefaultDict[int, DefaultDict[str, float]],
    amount: float,
) -> Tuple[int, int]:
    if duration_frames <= 0:
        return (-1, -1)

    start_frame = max(0, min(start_frame, TOTAL_FRAMES))
    new_end = max(0, min(start_frame + duration_frames, TOTAL_FRAMES))

    old_end = buff_state.end_frame if buff_state.active else -1
    active_at_start = buff_state.active and old_end > start_frame

    if not active_at_start:
        for tid in targets:
            _add_delta(delta_map, start_frame, tid, +amount)
            _add_delta(delta_map, new_end, tid, -amount)
        buff_state.active = True
        buff_state.end_frame = new_end
        return (start_frame, new_end)

    if refresh_mode == "refresh":
        if old_end != new_end:
            for tid in targets:
                _add_delta(delta_map, old_end, tid, +amount)
                _add_delta(delta_map, new_end, tid, -amount)
            buff_state.end_frame = new_end
        return (start_frame, new_end)

    if new_end > old_end:
        for tid in targets:
            _add_delta(delta_map, old_end, tid, +amount)
            _add_delta(delta_map, new_end, tid, -amount)
        buff_state.end_frame = new_end
    return (start_frame, buff_state.end_frame)


def merge_segments(segments: List[Dict[str, float]]) -> List[Dict[str, float]]:
    if not segments:
        return []
    segs = sorted(segments, key=lambda s: (s["start"], s["end"]))
    out = [dict(segs[0])]
    for s in segs[1:]:
        last = out[-1]
        if s["start"] <= last["end"]:
            last["end"] = max(last["end"], s["end"])
        else:
            out.append(dict(s))
    return out


def simulate(
    *,
    seed: int,
    refresh_mode: RefreshMode,
    attacker_base_attack_speed: float,
    penguin_count: int,
    tiger_count: int,
    emit_basic_events: bool = False,
) -> Dict[str, Any]:
    penguin_count = max(0, int(penguin_count))
    tiger_count = max(0, int(tiger_count))

    units: List[Unit] = []
    attacker = Unit(unit_id="attacker", kind="attacker", base_attack_speed=float(attacker_base_attack_speed), next_ready_frame=TOTAL_FRAMES + 1)
    units.append(attacker)

    base_rng = random.Random(seed)

    def unit_rng(unit_index: int) -> random.Random:
        sub = base_rng.randrange(0, 2**31 - 1) ^ (unit_index * 0x9E3779B1)
        return random.Random(sub)

    for i in range(penguin_count):
        units.append(Unit(unit_id=f"penguin_{i+1}", kind="penguin", base_attack_speed=1.5, next_ready_frame=0, rng=unit_rng(1000 + i)))
    for i in range(tiger_count):
        units.append(Unit(unit_id=f"tiger_{i+1}", kind="tiger", base_attack_speed=2.4, next_ready_frame=0, rng=unit_rng(2000 + i)))

    unit_ids = [u.unit_id for u in units]

    delta_tiger: DefaultDict[int, DefaultDict[str, float]] = defaultdict(lambda: defaultdict(float))
    delta_penguin: DefaultDict[int, DefaultDict[str, float]] = defaultdict(lambda: defaultdict(float))

    tiger_add: Dict[str, float] = {uid: 0.0 for uid in unit_ids}
    penguin_add: Dict[str, float] = {uid: 0.0 for uid in unit_ids}

    tiger_howl_state: Dict[str, BuffState] = {}
    penguin_allegro_state: Dict[str, BuffState] = {}

    events: List[Dict[str, Any]] = []
    attacker_series: List[Dict[str, Any]] = []

    attacker_tiger_active = [False] * TOTAL_FRAMES
    attacker_penguin_active = [False] * TOTAL_FRAMES

    def push_event(frame: int, etype: str, label: str) -> None:
        events.append({"frame": frame, "t": frame / FPS, "type": etype, "label": label})

    for frame in range(TOTAL_FRAMES):
        if frame in delta_tiger:
            for tid, d in delta_tiger[frame].items():
                tiger_add[tid] += d
        if frame in delta_penguin:
            for tid, d in delta_penguin[frame].items():
                penguin_add[tid] += d

        attacker_buff_add = tiger_add["attacker"] + penguin_add["attacker"]
        attacker_as = max(0.0, attacker.base_attack_speed * (1.0 + attacker_buff_add))
        attacker_series.append({"frame": frame, "t": frame / FPS, "attackerAttackSpeed": attacker_as, "buffAddTotal": attacker_buff_add})

        attacker_tiger_active[frame] = tiger_add["attacker"] > 0.0
        attacker_penguin_active[frame] = penguin_add["attacker"] > 0.0

        for u in units:
            if u.kind == "attacker":
                continue
            if u.next_ready_frame != frame:
                continue

            buff_add = tiger_add[u.unit_id] + penguin_add[u.unit_id]
            current_as = max(0.0, u.base_attack_speed * (1.0 + buff_add))
            r = u.rng.random() if u.rng else random.random()

            if u.kind == "penguin":
                if r < 0.10:
                    start = frame + 1
                    duration = 3 * FPS
                    state = penguin_allegro_state.setdefault(u.unit_id, BuffState())
                    targets = [tid for tid in unit_ids if tid != u.unit_id]
                    _apply_buff_with_refresh(
                        buff_state=state,
                        refresh_mode=refresh_mode,
                        start_frame=start,
                        duration_frames=duration,
                        targets=targets,
                        delta_map=delta_penguin,
                        amount=0.2,
                    )
                    push_event(frame, "penguin", f"ペンギン#{u.unit_id.split('_')[1]}: アレグロ(+20%AS 3s, 自分除く)")
                    u.next_ready_frame = min(frame + 33, TOTAL_FRAMES)
                    continue

                if r < 0.25:
                    push_event(frame, "penguin_nothing", f"ペンギン#{u.unit_id.split('_')[1]}: なにもしない(29F)")
                    u.next_ready_frame = min(frame + 29, TOTAL_FRAMES)
                    continue

                dur = frames_for_basic(current_as)
                if emit_basic_events:
                    push_event(frame, "penguin_basic", f"ペンギン#{u.unit_id.split('_')[1]}: 基本攻撃 {dur}F (AS={current_as:.3f})")
                u.next_ready_frame = min(frame + dur, TOTAL_FRAMES)
                continue

            if u.kind == "tiger":
                if r < 0.08:
                    start = frame + 1
                    duration = 2 * FPS
                    state = tiger_howl_state.setdefault(u.unit_id, BuffState())
                    targets = unit_ids[:]
                    _apply_buff_with_refresh(
                        buff_state=state,
                        refresh_mode=refresh_mode,
                        start_frame=start,
                        duration_frames=duration,
                        targets=targets,
                        delta_map=delta_tiger,
                        amount=0.2,
                    )
                    push_event(frame, "tiger", f"虎#{u.unit_id.split('_')[1]}: 遠吠え(+20%AS 2s, 全員)")
                    u.next_ready_frame = min(frame + 20, TOTAL_FRAMES)
                    continue

                dur = frames_for_basic(current_as)
                if emit_basic_events:
                    push_event(frame, "tiger_basic", f"虎#{u.unit_id.split('_')[1]}: 基本攻撃 {dur}F (AS={current_as:.3f})")
                u.next_ready_frame = min(frame + dur, TOTAL_FRAMES)
                continue

    def build_segments(active_flags: List[bool]) -> List[Dict[str, float]]:
        segs: List[Dict[str, float]] = []
        on = False
        start_f = 0
        for f, a in enumerate(active_flags):
            if a and not on:
                on = True
                start_f = f
            if on and not a:
                segs.append({"start": start_f / FPS, "end": f / FPS})
                on = False
        if on:
            segs.append({"start": start_f / FPS, "end": TOTAL_FRAMES / FPS})
        return merge_segments(segs)

    return {
        "durationSec": DURATION_SEC,
        "fps": FPS,
        "dt": DT,
        "seed": seed,
        "refreshMode": refresh_mode,
        "units": {"attacker": {"baseAttackSpeed": attacker.base_attack_speed}, "penguinCount": penguin_count, "tigerCount": tiger_count},
        "buffs": {"tiger": build_segments(attacker_tiger_active), "penguin": build_segments(attacker_penguin_active)},
        "events": events,
        "series": attacker_series,
    }


app = Flask(__name__)


@app.get("/healthz")
def healthz():
    return jsonify({"ok": True})


@app.post("/api/simulate")
def api_simulate():
    data = request.get_json(silent=True) or {}

    seed = int(data.get("seed", 123456))
    refresh_mode = data.get("refreshMode", "refresh")
    if refresh_mode not in ("refresh", "extend"):
        refresh_mode = "refresh"

    attacker = data.get("attacker", {}) or {}
    attacker_base_as = float(attacker.get("attackSpeed", 1.0))

    buffers = data.get("buffers", {}) or {}
    penguin_count = int(buffers.get("penguinCount", 0))
    tiger_count = int(buffers.get("tigerCount", 0))

    emit_basic = bool(data.get("emitBasicEvents", False))

    out = simulate(
        seed=seed,
        refresh_mode=refresh_mode,
        attacker_base_attack_speed=attacker_base_as,
        penguin_count=penguin_count,
        tiger_count=tiger_count,
        emit_basic_events=emit_basic,
    )
    return jsonify(out)
