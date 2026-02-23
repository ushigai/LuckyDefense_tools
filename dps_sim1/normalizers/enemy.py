from __future__ import annotations

import re
from typing import Any, Dict


def parse_enemy_wave(v: Any) -> int:
    try:
        x = int(v)
    except Exception:
        try:
            x = int(float(v))
        except Exception:
            return 0
    return x if x > 0 else 0


def parse_enemy_mode(mode: Any, name: Any) -> str:
    mode_s = str(mode or "").strip()
    if mode_s:
        return mode_s

    name_s = str(name or "")
    for token in ("ノーマル", "ハード", "地獄", "神"):
        if token in name_s:
            return token
    return ""


def enemy_selection_key(mode: Any, wave: Any, group: Any) -> str:
    return f"{str(mode or '').strip()}|{parse_enemy_wave(wave)}|{str(group or '').strip()}"


def normalize_enemy_entry(e: Dict[str, Any], default_enemy_def: float) -> Dict[str, Any]:
    out = dict(e)
    name = str(out.get("name", "") or "").strip()
    mode = parse_enemy_mode(out.get("mode"), name)
    wave = parse_enemy_wave(out.get("wave", 0))
    if wave <= 0:
        m = re.search(r"(\d+)\s*[Wｗ]", name)
        if m:
            wave = parse_enemy_wave(m.group(1))

    group = str(out.get("group", "") or "").strip()
    if not group and "ボス" in name:
        group = "ボス"

    out["name"] = name
    out["mode"] = mode
    out["wave"] = wave
    out["group"] = group
    out.pop("difficulty", None)
    out["enemy_def"] = float(out.get("enemy_def", default_enemy_def))
    return out


def default_enemy_row(enemy_db: Dict[str, Dict[str, Any]], default_enemy_def: float) -> Dict[str, Any]:
    for row in enemy_db.values():
        return row
    return {
        "mode": "ノーマル",
        "wave": 80,
        "group": "ボス",
        "hp": 2_000_000_000,
        "enemy_def": default_enemy_def,
    }


def resolve_enemy_row(
    common: Dict[str, Any],
    enemy_db: Dict[str, Dict[str, Any]],
    default_enemy_def: float,
) -> Dict[str, Any]:
    mode = str(common.get("enemyMode", "") or "").strip()
    wave = parse_enemy_wave(common.get("enemyWave", 0))
    group = str(common.get("enemyGroup", "") or "").strip()
    key = enemy_selection_key(mode, wave, group)
    row = enemy_db.get(key)
    if row:
        return row
    return default_enemy_row(enemy_db, default_enemy_def)

