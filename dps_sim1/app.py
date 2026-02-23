from __future__ import annotations

import copy
import csv
import json
import math
import os
import hashlib
import random
import time
from collections import OrderedDict
from threading import Lock
from typing import Any, Dict, List, Callable, Tuple
from datetime import datetime, timezone
from functools import lru_cache

from data.treasure_db import load_treasure_db
from data.char_params import *

from flask import Flask, jsonify, request, send_from_directory
from dps_sim1.normalizers import blob as blob_normalizer
from dps_sim1.normalizers import enemy as enemy_normalizer
from dps_sim1.normalizers import pet as pet_normalizer
from dps_sim1.simulator.awakened_hayley import mean_total_damage_15021
from dps_sim1.simulator.hayley import mean_total_damage_5021
from dps_sim1.simulator.rokechuu_oc import mean_total_damage_5115
from dps_sim1.simulator.watt import mean_total_damage_5013
from dps_sim1.simulator.chona import mean_total_damage_5019
from dps_sim1.simulator.iam_meow import mean_total_damage_15004
from dps_sim1.simulator.boss_senchoushi import mean_total_damage_15024
from dps_sim1.simulator.doctorpulse import mean_total_damage_14002
from dps_sim1.simulator.captain_roka import mean_total_damage_15023
from dps_sim1.simulator.ninja import mean_total_damage_3007
from dps_sim1.simulator.masterkun import mean_total_damage_5018
from dps_sim1.simulator.roka import mean_total_damage_5023
from dps_sim1.simulator.ghost_ninja import mean_total_damage_13007
from dps_sim1.simulator.prim_bamba import mean_total_damage_15001
from dps_sim1.simulator.darkload_dragon import mean_total_damage_15006
from dps_sim1.simulator.ace_batman_ball import mean_total_damage_15110
from dps_sim1.simulator.ace_batman_bat import mean_total_damage_15210
from dps_sim1.simulator.top_vein import mean_total_damage_15011
from dps_sim1.simulator.bamba import mean_total_damage_5001
from dps_sim1.simulator.queen_coldy import mean_total_damage_15002
from dps_sim1.simulator.common_sim import mean_total_damage_common
from dps_sim1.simulator.f32lock_awakened_hayley import mean_total_damage_15021 as mean_total_damage_15021_f32lock
from dps_sim1.simulator.f32lock_hayley import mean_total_damage_5021 as mean_total_damage_5021_f32lock
from dps_sim1.simulator.f32lock_rokechuu_oc import mean_total_damage_5115 as mean_total_damage_5115_f32lock
from dps_sim1.simulator.f32lock_chona import mean_total_damage_5019 as mean_total_damage_5019_f32lock
from dps_sim1.simulator.f32lock_iam_meow import mean_total_damage_15004 as mean_total_damage_15004_f32lock
from dps_sim1.simulator.f32lock_boss_senchoushi import mean_total_damage_15024 as mean_total_damage_15024_f32lock
from dps_sim1.simulator.f32lock_doctorpulse import mean_total_damage_14002 as mean_total_damage_14002_f32lock
from dps_sim1.simulator.f32lock_captain_roka import mean_total_damage_15023 as mean_total_damage_15023_f32lock
from dps_sim1.simulator.f32lock_ninja import mean_total_damage_3007 as mean_total_damage_3007_f32lock
from dps_sim1.simulator.f32lock_masterkun import mean_total_damage_5018 as mean_total_damage_5018_f32lock
from dps_sim1.simulator.f32lock_roka import mean_total_damage_5023 as mean_total_damage_5023_f32lock
from dps_sim1.simulator.f32lock_ghost_ninja import mean_total_damage_13007 as mean_total_damage_13007_f32lock
from dps_sim1.simulator.f32lock_prim_bamba import mean_total_damage_15001 as mean_total_damage_15001_f32lock
from dps_sim1.simulator.f32lock_darkload_dragon import mean_total_damage_15006 as mean_total_damage_15006_f32lock
from dps_sim1.simulator.f32lock_ace_batman_ball import mean_total_damage_15110 as mean_total_damage_15110_f32lock
from dps_sim1.simulator.f32lock_ace_batman_bat import mean_total_damage_15210 as mean_total_damage_15210_f32lock
from dps_sim1.simulator.f32lock_top_vein import mean_total_damage_15011 as mean_total_damage_15011_f32lock
from dps_sim1.simulator.f32lock_bamba import mean_total_damage_5001 as mean_total_damage_5001_f32lock
from dps_sim1.simulator.f32lock_queen_coldy import mean_total_damage_15002 as mean_total_damage_15002_f32lock
from dps_sim1.simulator.f32lock_common_sim import mean_total_damage_common as mean_total_damage_common_f32lock


DamageTuple = Tuple[float, float, float, float, float]


def _as_damage_tuple(x: Any) -> DamageTuple:
    """Normalize simulator return to a 5-tuple.

    Backward compatible:
      - If a simulator still returns a float (total), treat it as basic damage.
    """
    if isinstance(x, (tuple, list)) and len(x) == 5:
        return (float(x[0]), float(x[1]), float(x[2]), float(x[3]), float(x[4]))
    if isinstance(x, dict):
        keys = ("basic", "skill1", "skill2", "skill3", "ult")
        if all(k in x for k in keys):
            return (float(x["basic"]), float(x["skill1"]), float(x["skill2"]), float(x["skill3"]), float(x["ult"]))
    try:
        return (float(x), 0.0, 0.0, 0.0, 0.0)
    except Exception:
        return (0.0, 0.0, 0.0, 0.0, 0.0)


def _wrap_damage_func(fn: Callable[..., Any]) -> Callable[..., DamageTuple]:
    def wrapped(*args: Any, **kwargs: Any) -> DamageTuple:
        return _as_damage_tuple(fn(*args, **kwargs))

    return wrapped


# Ensure all simulators return (basic, skill1, skill2, skill3, ult)
mean_total_damage_15021 = _wrap_damage_func(mean_total_damage_15021)
mean_total_damage_5021 = _wrap_damage_func(mean_total_damage_5021)
mean_total_damage_5115 = _wrap_damage_func(mean_total_damage_5115)
mean_total_damage_5013 = _wrap_damage_func(mean_total_damage_5013)
mean_total_damage_5019 = _wrap_damage_func(mean_total_damage_5019)
mean_total_damage_15004 = _wrap_damage_func(mean_total_damage_15004)
mean_total_damage_15024 = _wrap_damage_func(mean_total_damage_15024)
mean_total_damage_14002 = _wrap_damage_func(mean_total_damage_14002)
mean_total_damage_15023 = _wrap_damage_func(mean_total_damage_15023)
mean_total_damage_3007 = _wrap_damage_func(mean_total_damage_3007)
mean_total_damage_5018 = _wrap_damage_func(mean_total_damage_5018)
mean_total_damage_5023 = _wrap_damage_func(mean_total_damage_5023)
mean_total_damage_13007 = _wrap_damage_func(mean_total_damage_13007)
mean_total_damage_common = _wrap_damage_func(mean_total_damage_common)
mean_total_damage_15021_f32lock = _wrap_damage_func(mean_total_damage_15021_f32lock)
mean_total_damage_5021_f32lock = _wrap_damage_func(mean_total_damage_5021_f32lock)
mean_total_damage_5115_f32lock = _wrap_damage_func(mean_total_damage_5115_f32lock)
mean_total_damage_5019_f32lock = _wrap_damage_func(mean_total_damage_5019_f32lock)
mean_total_damage_15004_f32lock = _wrap_damage_func(mean_total_damage_15004_f32lock)
mean_total_damage_15024_f32lock = _wrap_damage_func(mean_total_damage_15024_f32lock)
mean_total_damage_14002_f32lock = _wrap_damage_func(mean_total_damage_14002_f32lock)
mean_total_damage_15023_f32lock = _wrap_damage_func(mean_total_damage_15023_f32lock)
mean_total_damage_3007_f32lock = _wrap_damage_func(mean_total_damage_3007_f32lock)
mean_total_damage_5018_f32lock = _wrap_damage_func(mean_total_damage_5018_f32lock)
mean_total_damage_5023_f32lock = _wrap_damage_func(mean_total_damage_5023_f32lock)
mean_total_damage_13007_f32lock = _wrap_damage_func(mean_total_damage_13007_f32lock)
mean_total_damage_15001_f32lock = _wrap_damage_func(mean_total_damage_15001_f32lock)
mean_total_damage_15006_f32lock = _wrap_damage_func(mean_total_damage_15006_f32lock)
mean_total_damage_15110_f32lock = _wrap_damage_func(mean_total_damage_15110_f32lock)
mean_total_damage_15210_f32lock = _wrap_damage_func(mean_total_damage_15210_f32lock)
mean_total_damage_15011_f32lock = _wrap_damage_func(mean_total_damage_15011_f32lock)
mean_total_damage_5001_f32lock = _wrap_damage_func(mean_total_damage_5001_f32lock)
mean_total_damage_15002_f32lock = _wrap_damage_func(mean_total_damage_15002_f32lock)
mean_total_damage_common_f32lock = _wrap_damage_func(mean_total_damage_common_f32lock)

MEAN_TOTAL_DAMAGE_15021_BASE = mean_total_damage_15021
MEAN_TOTAL_DAMAGE_5021_BASE = mean_total_damage_5021
MEAN_TOTAL_DAMAGE_5115_BASE = mean_total_damage_5115
MEAN_TOTAL_DAMAGE_5019_BASE = mean_total_damage_5019
MEAN_TOTAL_DAMAGE_15004_BASE = mean_total_damage_15004
MEAN_TOTAL_DAMAGE_15024_BASE = mean_total_damage_15024
MEAN_TOTAL_DAMAGE_14002_BASE = mean_total_damage_14002
MEAN_TOTAL_DAMAGE_15023_BASE = mean_total_damage_15023
MEAN_TOTAL_DAMAGE_3007_BASE = mean_total_damage_3007
MEAN_TOTAL_DAMAGE_5018_BASE = mean_total_damage_5018
MEAN_TOTAL_DAMAGE_5023_BASE = mean_total_damage_5023
MEAN_TOTAL_DAMAGE_13007_BASE = mean_total_damage_13007
MEAN_TOTAL_DAMAGE_15001_BASE = mean_total_damage_15001
MEAN_TOTAL_DAMAGE_15006_BASE = mean_total_damage_15006
MEAN_TOTAL_DAMAGE_15110_BASE = mean_total_damage_15110
MEAN_TOTAL_DAMAGE_15210_BASE = mean_total_damage_15210
MEAN_TOTAL_DAMAGE_15011_BASE = mean_total_damage_15011
MEAN_TOTAL_DAMAGE_5001_BASE = mean_total_damage_5001
MEAN_TOTAL_DAMAGE_15002_BASE = mean_total_damage_15002
MEAN_TOTAL_DAMAGE_COMMON_BASE = mean_total_damage_common


APP_DIR = os.path.dirname(os.path.abspath(__file__))
# repo root (data/ はルートに置いたまま)
BASE_DIR = os.path.abspath(os.path.join(APP_DIR, os.pardir))

STATIC_DIR = os.path.join(APP_DIR, "static")
DATA_DIR = os.path.join(BASE_DIR, "data")
TEXT_CSV_PATHS = [
    os.path.join(DATA_DIR, "Text.csv"),
    os.path.join(DATA_DIR, "Text2.csv"),
]

app = Flask(__name__)

_MEMBER_DPS_CACHE_VERSION = 1


def _json_error(message: str, status: int):
    return jsonify({"error": message}), status


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except Exception:
        return int(default)


MEMBER_DPS_CACHE_MAXSIZE = max(1, _env_int("MEMBER_DPS_CACHE_MAXSIZE", 10**6))
MEMBER_DPS_CACHE_CLEAR_SEC = max(0, _env_int("MEMBER_DPS_CACHE_CLEAR_SEC", 1800))
_MEMBER_DPS_CACHE: OrderedDict[str, Tuple[float, Dict[str, float], Dict[str, Any]]] = OrderedDict()
_MEMBER_DPS_CACHE_LOCK = Lock()
_MEMBER_DPS_CACHE_HITS = 0
_MEMBER_DPS_CACHE_MISSES = 0
_MEMBER_DPS_CACHE_CLEAR_COUNT = 0
_MEMBER_DPS_CACHE_NEXT_CLEAR_TS = (
    time.monotonic() + MEMBER_DPS_CACHE_CLEAR_SEC if MEMBER_DPS_CACHE_CLEAR_SEC > 0 else None
)


_MULT_SLOT_KEYS = ("basic", "skill1", "skill2", "skill3", "ult")
def _empty_mult_parts() -> Dict[str, Dict[str, List[Any]]]:
    return {slot: {"numbers": [], "buffs": []} for slot in _MULT_SLOT_KEYS}


def _mp(numbers: List[float | int], buffs: List[str]) -> Dict[str, List[Any]]:
    return {
        "numbers": [float(x) if isinstance(x, float) else x for x in numbers],
        "buffs": list(buffs),
    }


def _mparts(**kwargs: Dict[str, List[Any]]) -> Dict[str, Dict[str, List[Any]]]:
    base = _empty_mult_parts()
    for k, v in kwargs.items():
        if k in base:
            base[k] = {"numbers": list(v.get("numbers", [])), "buffs": list(v.get("buffs", []))}
    return base


def _member_dps_cache_key(character_id: str, common: Dict[str, Any], member: Dict[str, Any]) -> str:
    payload = {
        "v": _MEMBER_DPS_CACHE_VERSION,
        "character": character_id,
        "common": common,
        "member": member,
    }
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _member_dps_cache_get(key: str) -> Tuple[float, Dict[str, float], Dict[str, Any]] | None:
    global _MEMBER_DPS_CACHE_HITS, _MEMBER_DPS_CACHE_MISSES
    with _MEMBER_DPS_CACHE_LOCK:
        cached = _MEMBER_DPS_CACHE.get(key)
        if cached is None:
            _MEMBER_DPS_CACHE_MISSES += 1
            return None
        _MEMBER_DPS_CACHE.move_to_end(key)
        _MEMBER_DPS_CACHE_HITS += 1
        dps, dps_ratio, debug_message = cached
    return dps, copy.deepcopy(dps_ratio), copy.deepcopy(debug_message)


def _member_dps_cache_put(key: str, value: Tuple[float, Dict[str, float], Dict[str, Any]]) -> None:
    dps, dps_ratio, debug_message = value
    stored = (float(dps), copy.deepcopy(dps_ratio), copy.deepcopy(debug_message))
    with _MEMBER_DPS_CACHE_LOCK:
        _MEMBER_DPS_CACHE[key] = stored
        _MEMBER_DPS_CACHE.move_to_end(key)
        while len(_MEMBER_DPS_CACHE) > MEMBER_DPS_CACHE_MAXSIZE:
            _MEMBER_DPS_CACHE.popitem(last=False)


def _maybe_clear_member_dps_cache(now_monotonic: float | None = None) -> None:
    global _MEMBER_DPS_CACHE_NEXT_CLEAR_TS, _MEMBER_DPS_CACHE_CLEAR_COUNT
    if MEMBER_DPS_CACHE_CLEAR_SEC <= 0:
        return
    now = time.monotonic() if now_monotonic is None else now_monotonic
    with _MEMBER_DPS_CACHE_LOCK:
        next_clear_ts = _MEMBER_DPS_CACHE_NEXT_CLEAR_TS
        if next_clear_ts is None:
            _MEMBER_DPS_CACHE_NEXT_CLEAR_TS = now + MEMBER_DPS_CACHE_CLEAR_SEC
            return
        if now < next_clear_ts:
            return
        _MEMBER_DPS_CACHE.clear()
        _MEMBER_DPS_CACHE_CLEAR_COUNT += 1
        _MEMBER_DPS_CACHE_NEXT_CLEAR_TS = now + MEMBER_DPS_CACHE_CLEAR_SEC


def _member_dps_cache_info() -> Dict[str, Any]:
    with _MEMBER_DPS_CACHE_LOCK:
        next_clear_in_sec: int | None = None
        if MEMBER_DPS_CACHE_CLEAR_SEC > 0 and _MEMBER_DPS_CACHE_NEXT_CLEAR_TS is not None:
            next_clear_in_sec = max(0, int(_MEMBER_DPS_CACHE_NEXT_CLEAR_TS - time.monotonic()))
        return {
            "hits": _MEMBER_DPS_CACHE_HITS,
            "misses": _MEMBER_DPS_CACHE_MISSES,
            "size": len(_MEMBER_DPS_CACHE),
            "maxSize": MEMBER_DPS_CACHE_MAXSIZE,
            "clearEverySec": MEMBER_DPS_CACHE_CLEAR_SEC,
            "nextClearInSec": next_clear_in_sec,
            "clearCount": _MEMBER_DPS_CACHE_CLEAR_COUNT,
        }


def _clean_csv_cell(value: Any) -> str:
    s = str(value or "").strip()
    if len(s) >= 2 and s[0] == '"' and s[-1] == '"':
        s = s[1:-1].strip()
    return s


def _load_single_text_csv_rows(csv_path: str) -> List[Dict[str, str]]:
    if not os.path.exists(csv_path):
        return []

    rows: List[Dict[str, str]] = []
    with open(csv_path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f, skipinitialspace=True)

        # row-1 is a type hint line: "string, string, ...".
        try:
            next(reader)
        except StopIteration:
            return []

        try:
            header_raw = next(reader)
        except StopIteration:
            return []

        header = [_clean_csv_cell(col) for col in header_raw]
        header_idx = {name: i for i, name in enumerate(header)}
        ja_idx = header_idx.get("ja")
        if ja_idx is None:
            return []

        width = len(header)
        for row in reader:
            if not row:
                continue
            if len(row) < width:
                row = row + [""] * (width - len(row))

            row_obj: Dict[str, str] = {}
            for i, key in enumerate(header):
                if not key:
                    continue
                row_obj[key] = _clean_csv_cell(row[i]) if i < len(row) else ""
            rows.append(row_obj)
    return rows


@lru_cache(maxsize=1)
def _load_text_csv_rows() -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    for csv_path in TEXT_CSV_PATHS:
        rows.extend(_load_single_text_csv_rows(csv_path))
    return rows


@lru_cache(maxsize=1)
def _build_ja_to_locale_maps() -> Dict[str, Dict[str, str]]:
    out: Dict[str, Dict[str, str]] = {
        "en": {},
        "kr": {},
    }
    for row in _load_text_csv_rows():
        ja = row.get("ja", "")
        if not ja:
            continue

        for lang_key, csv_col in (("en", "en"), ("kr", "ko")):
            dst = row.get(csv_col, "")
            if not dst:
                continue
            # Keep first hit to avoid unstable overwrites across duplicated text rows.
            if ja not in out[lang_key]:
                out[lang_key][ja] = dst
    return out


def load_characters() -> Dict[str, Dict[str, Any]]:
    path = os.path.join(DATA_DIR, "characters.json")
    with open(path, "r", encoding="utf-8") as f:
        obj = json.load(f)
    out: Dict[str, Dict[str, Any]] = {}
    for c in obj.get("characters", []):
        out[str(c["id"])] = c
    return out

def load_artifacts() -> Dict[str, Dict[str, Any]]:
    """
    lv4 = artifacts["力のポーション"]["effects"]["lv4"] # 13

    '力のポーション': {
        'no': 1, 'no_str': '01', 'grid': '1_1', 'tier': 'A', 'name': '力のポーション', 
        'effects': {'lv1': 10, 'lv2': 11, 'lv3': 12, 'lv4': 13, 'lv5': 14, 'lv6': 15, 'lv7': 16, 'lv8': 17, 'lv9': 18, 'lv10': 19, 'lv11': 20}, 
        'increment': '+１%', 'remarks': '実際の効果は表示値の２倍', 'image_url': 'https://img.atwiki.jp/luckydefense/attach/17/430/01.png'}, 
    '妖精の弓': {...},
    """
    path = os.path.join(DATA_DIR, "artifacts_expanded.json")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    artifacts_list = data["artifacts"]
    index: Dict[str, Dict[str, Any]] = {}

    for a in artifacts_list:
        name = a["name"]
        if name in index:
            raise ValueError(f"duplicate artifact name: {name!r}")
        index[name] = a
    return index

def load_enemies() -> Dict[str, Dict[str, Any]]:
    path = os.path.join(DATA_DIR, "enemy.json")
    with open(path, "r", encoding="utf-8") as f:
        obj = json.load(f)
    out: Dict[str, Dict[str, Any]] = {}
    for e in obj.get("enemies", []):
        if not isinstance(e, dict):
            continue
        normalized = _normalize_enemy_entry(e)
        key = _enemy_selection_key(normalized.get("mode"), normalized.get("wave"), normalized.get("group"))
        if key == _enemy_selection_key("", 0, ""):
            continue
        out[key] = normalized
    return out


def _default_enemy_def() -> float:
    return 148.0


def _parse_enemy_wave(v: Any) -> int:
    return enemy_normalizer.parse_enemy_wave(v)


def _parse_enemy_mode(mode: Any, name: Any) -> str:
    return enemy_normalizer.parse_enemy_mode(mode, name)


def _normalize_enemy_entry(e: Dict[str, Any]) -> Dict[str, Any]:
    return enemy_normalizer.normalize_enemy_entry(e, _default_enemy_def())


def _enemy_selection_key(mode: Any, wave: Any, group: Any) -> str:
    return enemy_normalizer.enemy_selection_key(mode, wave, group)


def _default_enemy_row() -> Dict[str, Any]:
    return enemy_normalizer.default_enemy_row(ENEMY_DB, _default_enemy_def())


def _resolve_enemy_row(common: Dict[str, Any]) -> Dict[str, Any]:
    return enemy_normalizer.resolve_enemy_row(common, ENEMY_DB, _default_enemy_def())

def load_runes() -> Dict[str, Dict[str, Any]]:
    """Load runes.json (list) into name->entry mapping."""
    path = os.path.join(DATA_DIR, "runes.json")
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        obj = json.load(f)
    if not isinstance(obj, list):
        return {}
    out: Dict[str, Dict[str, Any]] = {}
    for r in obj:
        try:
            name = str(r.get("name", ""))
        except Exception:
            continue
        if not name:
            continue
        out[name] = r
    return out

def load_blob_figures() -> Dict[str, Dict[str, Any]]:
    """Load blob_figures.json (list) into name->entry mapping."""
    path = os.path.join(DATA_DIR, "blob_figures.json")
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            obj = json.load(f)
    except Exception:
        return {}
    if not isinstance(obj, list):
        return {}
    out: Dict[str, Dict[str, Any]] = {}
    for r in obj:
        if not isinstance(r, dict):
            continue
        name = str(r.get("name", "") or "")
        if not name:
            continue
        out[name] = r
    return out

def load_pets() -> Tuple[Dict[str, Dict[str, Any]], Dict[str, Dict[str, Any]]]:
    """Load pets.json into id/name lookup maps."""
    path = os.path.join(DATA_DIR, "pets.json")
    if not os.path.exists(path):
        return {}, {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            obj = json.load(f)
    except Exception:
        return {}, {}
    if not isinstance(obj, list):
        return {}, {}

    by_id: Dict[str, Dict[str, Any]] = {}
    by_name: Dict[str, Dict[str, Any]] = {}
    for p in obj:
        if not isinstance(p, dict):
            continue
        pid = str(p.get("id", "") or "").strip()
        name = str(p.get("name", "") or "").strip()
        if not pid:
            continue
        row = {"id": pid, "name": name, "raw": p}
        by_id[pid] = row
        if name and name not in by_name:
            by_name[name] = row
    return by_id, by_name


TREASURE_DB, _ = load_treasure_db(os.path.join(DATA_DIR, "treasures.json"))

ARTIFACTS_DB = load_artifacts()
CHAR_DB = load_characters()
ENEMY_DB = load_enemies()
RUNES_DB = load_runes()
BLOB_FIGURES_DB = load_blob_figures()
PET_DB_BY_ID, PET_DB_BY_NAME = load_pets()
PHISICS_CHAR = [3007, 5001, 5005, 5010, 5011, 5012, 5014, 5015, 5019, 5020, 5023, 5114, 5115, 5214, 13007, 15001, 15010, 15011, 15020, 15023, 15110, 15210]


@app.get("/")
def index():
    return send_from_directory(STATIC_DIR, "index.html")


@app.get("/static/<path:filename>")
def static_files(filename: str):
    return send_from_directory(STATIC_DIR, filename)


@app.get("/data/<path:filename>")
def data_files(filename: str):
    return send_from_directory(DATA_DIR, filename)


@app.get("/api/i18n/textmap")
def api_i18n_textmap():
    maps = _build_ja_to_locale_maps()
    ja_to_en = maps.get("en", {})
    ja_to_kr = maps.get("kr", {})
    sources = [f"data/{os.path.basename(p)}" for p in TEXT_CSV_PATHS if os.path.exists(p)]
    return jsonify(
        {
            "source": sources,
            "count": len(ja_to_en),
            "jaToEn": ja_to_en,
            "jaToKr": ja_to_kr,
            "jaToLocale": maps,
        }
    )


def clamp_int(v: Any, lo: int, hi: int, default: int) -> int:
    try:
        x = int(v)
    except Exception:
        return default
    return max(lo, min(hi, x))


def clamp_float(v: Any, lo: float, hi: float, default: float) -> float:
    try:
        x = float(v)
    except Exception:
        return default
    return max(lo, min(hi, x))


def _decimals_from_step(step: Any) -> int:
    return blob_normalizer.decimals_from_step(step)


def _snap_to_step(x: float, lo: float, step: float) -> float:
    return blob_normalizer.snap_to_step(x, lo, step)


def _normalize_blob_figures(v: Any) -> List[Dict[str, Any]]:
    return blob_normalizer.normalize_blob_figures(v, BLOB_FIGURES_DB)



def _is_none_token(v: Any) -> bool:
    return pet_normalizer.is_none_token(v)


def _resolve_pet_id_name(pid: Any, pname: Any) -> Tuple[str, str]:
    return pet_normalizer.resolve_pet_id_name(pid, pname, PET_DB_BY_ID, PET_DB_BY_NAME)


def _normalize_pets(options: Any) -> List[Dict[str, Any]]:
    return pet_normalizer.normalize_pets(options, PET_DB_BY_ID, PET_DB_BY_NAME)


def _normalize_pet(options: Any) -> Dict[str, Any] | None:
    return pet_normalizer.normalize_pet(options, PET_DB_BY_ID, PET_DB_BY_NAME)


def _to_pet_slots(pets: List[Dict[str, Any]]) -> Tuple[Dict[str, Any] | None, Dict[str, Any] | None, Dict[str, Any] | None]:
    return pet_normalizer.to_pet_slots(pets)


def _pet_param_at_lv(pet_id: str, pet_lv: int, param_no: int, skill_idx: int = 0) -> float | None:
    return pet_normalizer.pet_param_at_lv(pet_id, pet_lv, param_no, PET_DB_BY_ID, skill_idx=skill_idx)


def _build_member_debug_tail(
    *,
    base_atk: float,
    atk: float,
    ticks: int,
    base_speed: float,
    speed: float,
    ult_mana: float,
    t_buff1: float | int,
    t_buff2: float | int,
    t_buff3: float | int,
    is_phisics: bool,
    strongest_creature: float | int,
    basic_one: float | int,
    skill1_one: float | int,
    skill2_one: float | int,
    skill3_one: float | int,
    ult_one: float | int,
    mult_parts: Dict[str, Dict[str, List[Any]]],
) -> Dict[str, Any]:
    return {
        "base_atk": base_atk,
        "atk": atk,
        "ticks": ticks,
        "base_speed": base_speed,
        "speed": speed,
        "ult_mana": ult_mana,
        "t_buff1": t_buff1,
        "t_buff2": t_buff2,
        "t_buff3": t_buff3,
        "isPhisics": is_phisics,
        "StrongestCreature": strongest_creature,
        "basic_one": basic_one,
        "skill1_one": skill1_one,
        "skill2_one": skill2_one,
        "skill3_one": skill3_one,
        "ult_one": ult_one,
        "mult_parts": copy.deepcopy(mult_parts),
    }


def sign(n):
    if n:
        if n < 0:
            return -1
        return 1
    return 0


def compute_member_dps(character_id: str, common: Dict[str, Any], member: Dict[str, Any]) -> Tuple[float, Dict[str, float], Dict[str, Any]]:
    """
    1. 初期化
        1. 変数の初期化
            1. デバッグメッセージ
            2. 専用財宝バフ
            3. 計算結果
            4. シミュレーション関数
        2. JSONや引数からデータ取得
            1. common（共通バフ）取得
            2. 遺物レベル
            3. キャラ個別数値
        3. ペット
        4. ブロッブ人形
        5. ルーン
        6. 数値計算
            1. 防御から物理バフを計算
            2. 攻撃力/攻撃速度計算
            3. カテゴリ別バフ値加算
    2. キャラDPS計算
        1. 洗剤再度計算
        2. ./simulate/*.py丸投げ
        2. キャラパッシブ（覚醒ヘイリーの異種神話数など）
    3. その他
        1. デバッグメッセージの定義
        2. 対ボス、対気絶、物理増加などを乗算
    
    """
    # ======= 変数の初期化 =======
    DebugMessage = dict()
    t_buff1,t_buff2,t_buff3 = 0,0,0
    ans = 0
    TICK_COEFF = 1000
    basic, skill1, skill2, skill3, ult = 0,0,0,0,0
    basic_one, skill1_one, skill2_one, skill3_one, ult_one = 0,0,0,0,0
    DamageIncreasePassive = 0
    mult_parts = _empty_mult_parts()
    use_f32lock = str(common.get("f32lock", "disable")).strip().lower() == "enable"

    mean_total_damage_15021 = mean_total_damage_15021_f32lock if use_f32lock else MEAN_TOTAL_DAMAGE_15021_BASE
    mean_total_damage_5021 = mean_total_damage_5021_f32lock if use_f32lock else MEAN_TOTAL_DAMAGE_5021_BASE
    mean_total_damage_5115 = mean_total_damage_5115_f32lock if use_f32lock else MEAN_TOTAL_DAMAGE_5115_BASE
    mean_total_damage_5019 = mean_total_damage_5019_f32lock if use_f32lock else MEAN_TOTAL_DAMAGE_5019_BASE
    mean_total_damage_15004 = mean_total_damage_15004_f32lock if use_f32lock else MEAN_TOTAL_DAMAGE_15004_BASE
    mean_total_damage_15024 = mean_total_damage_15024_f32lock if use_f32lock else MEAN_TOTAL_DAMAGE_15024_BASE
    mean_total_damage_14002 = mean_total_damage_14002_f32lock if use_f32lock else MEAN_TOTAL_DAMAGE_14002_BASE
    mean_total_damage_15023 = mean_total_damage_15023_f32lock if use_f32lock else MEAN_TOTAL_DAMAGE_15023_BASE
    mean_total_damage_3007 = mean_total_damage_3007_f32lock if use_f32lock else MEAN_TOTAL_DAMAGE_3007_BASE
    mean_total_damage_5018 = mean_total_damage_5018_f32lock if use_f32lock else MEAN_TOTAL_DAMAGE_5018_BASE
    mean_total_damage_5023 = mean_total_damage_5023_f32lock if use_f32lock else MEAN_TOTAL_DAMAGE_5023_BASE
    mean_total_damage_13007 = mean_total_damage_13007_f32lock if use_f32lock else MEAN_TOTAL_DAMAGE_13007_BASE
    mean_total_damage_15001 = mean_total_damage_15001_f32lock if use_f32lock else MEAN_TOTAL_DAMAGE_15001_BASE
    mean_total_damage_15006 = mean_total_damage_15006_f32lock if use_f32lock else MEAN_TOTAL_DAMAGE_15006_BASE
    mean_total_damage_15110 = mean_total_damage_15110_f32lock if use_f32lock else MEAN_TOTAL_DAMAGE_15110_BASE
    mean_total_damage_15210 = mean_total_damage_15210_f32lock if use_f32lock else MEAN_TOTAL_DAMAGE_15210_BASE
    mean_total_damage_15011 = mean_total_damage_15011_f32lock if use_f32lock else MEAN_TOTAL_DAMAGE_15011_BASE
    mean_total_damage_5001 = mean_total_damage_5001_f32lock if use_f32lock else MEAN_TOTAL_DAMAGE_5001_BASE
    mean_total_damage_15002 = mean_total_damage_15002_f32lock if use_f32lock else MEAN_TOTAL_DAMAGE_15002_BASE
    mean_total_damage_common = mean_total_damage_common_f32lock if use_f32lock else MEAN_TOTAL_DAMAGE_COMMON_BASE

    # ======= common（共通バフ）取得 =======
    duration_sec = int(common.get("durationSec", 60))
    trials = int(common.get("trials", 1))
    all_relic_lv = int(common.get("allRelicLv", 1))
    ArtifactLv = all_relic_lv
    seed = int(common.get("seed", 0))
    coins = int(common.get("coins", 0))
    char_lv = int(member.get("charLv", 1))
    guildBlessing = int(common.get("guildBlessing", 0))
    guildBuff_atk = 0.02 if 1 <= guildBlessing else 0
    guildBuff_boss = 0.05 if 2 <= guildBlessing else 0
    unitLevelSumBuff = float(common.get("unitLevelSumBuff", 0)) / 100
    atkBuffPct = float(common.get("atkBuffPct", 0)) / 100
    speedBuffPct = float(common.get("speedBuffPct", 0)) / 100
    defDown = float(common.get("defDown", 190))
    enemy_def = float(common.get("enemyDef", _default_enemy_def()))
    if not math.isfinite(enemy_def):
        enemy_def = _default_enemy_def()
    mythEnhanceLv = int(common.get("mythEnhanceLv", 1))

    # ======= 遺物レベル =======
    treasure_lv = int(member.get("treasureLv", 0))
    money_gun_lv = int(common.get("moneyGunLv", all_relic_lv))
    power_potion_lv = int(common.get("powerPotionLv", all_relic_lv))
    fairy_bow_lv = int(common.get("fairyBowLv", all_relic_lv))
    great_sword_lv = int(common.get("greatSwordLv", all_relic_lv))
    secret_book_lv = int(common.get("secretBookLv", all_relic_lv))
    bambaDoll = int(common.get("bambaDollLv", all_relic_lv))
    bat_lv = int(common.get("batLv", all_relic_lv))
    wizard_hat_lv = int(common.get("wizardHatLv", all_relic_lv))
    bomb_lv = int(common.get("bombLv", all_relic_lv))
    old_book_lv = int(common.get("oldBookLv", all_relic_lv))
    sage_yogurt_lv = int(common.get("sageYogurtLv", all_relic_lv))
    magic_gauntlet_lv = int(common.get("magicGauntletLv", all_relic_lv))
    mana_buff = int(common.get("manaRegenBuffPct", 0))
    PowerPotion   = float(ARTIFACTS_DB["力のポーション"]["effects"]["lv" + str(power_potion_lv)]) / 100
    MoneyGun      = float(ARTIFACTS_DB["マネーガン"]["effects"]["lv" + str(money_gun_lv)]) / 100
    FairyBow      = float(ARTIFACTS_DB["妖精の弓"]["effects"][f"lv{fairy_bow_lv}"]) / 100
    GreatSword    = float(ARTIFACTS_DB["大剣"]["effects"][f"lv{great_sword_lv}"]) / 100
    SecretBook    = float(ARTIFACTS_DB["秘伝書"]["effects"][f"lv{secret_book_lv}"]) / 100
    BambaDoll     = float(ARTIFACTS_DB["バンバの人形"]["effects"][f"lv{bambaDoll}"])
    Bat           = float(ARTIFACTS_DB["バット"]["effects"][f"lv{bat_lv}"]) / 100
    WizardHat     = float(ARTIFACTS_DB["魔法使いの帽子"]["effects"][f"lv{wizard_hat_lv}"]) / 100
    Bomb          = float(ARTIFACTS_DB["爆弾"]["effects"][f"lv{bomb_lv}"]) / 100
    OldBook       = float(ARTIFACTS_DB["古びた本"]["effects"][f"lv{old_book_lv}"])
    SageYogurt    = float(ARTIFACTS_DB["賢者のヨーグルト"]["effects"][f"lv{sage_yogurt_lv}"]) / 100
    MagicGauntlet = float(ARTIFACTS_DB["マジック籠手"]["effects"][f"lv{magic_gauntlet_lv}"]) / 100
    
    # ======= キャラ個別数値 =======
    mythCount = int(member.get("mythCount", 0))
    starPower = int(member.get("starPower", 0))
    energyCount = int(member.get("energyCount", 0))
    robots = int(member.get("robots", 0))
    roka_crit_ = int(member.get("roka_crit_", 0))
    roka_crit = int(member.get("roka_crit", 0))
    techEnhance = 1 + int(member.get("techEnhance", 0)) / 10
    uchiCells = float(member.get("uchiCells", 0))
    batEnhance = int(member.get("batEnhance", 0))
    batEnhance = batEnhance_db[batEnhance]
    batEnhance_ = int(member.get("batEnhance_", 0))
    strikeout = float(member.get("strikeout", 1.0))
    emotionControl = int(member.get("emotionControl", 0))
    StrongestCreature = int(member.get("StrongestCreature", 0))
    StrongestCreature *= 0.3 if character_id == "5106" else 0.4
    score = int(member.get("score", 0)) / 100
    intake = int(member.get("intake", 0))
    blueBlob = int(member.get("blueBlob", 0))
    redBlob = int(member.get("redBlob", 0))
    greenBlob = int(member.get("greenBlob", 0))
    BlobLvSum = blueBlob + redBlob + greenBlob
    icecount = int(member.get("icecount", 0))
    icerate = int(member.get("icerate", 0)) / 100
    icecount_ = int(member.get("icecount_", 1))

    # ======= ペット =======
    pet_buff = {
        "AttackDamage": 0.0, # 攻撃力増加
        "SpRegen": 0.0, # マナ回復増加
        "BasicAttackDamage": 0.0, # 基本攻撃ダメ増加
        "UltimateDamage": 0.0, # 究極ダメ増加
        "BossMonsterDamage": 0.0, # 対ボスダメ増加
        "MovementSpeed": 0.0, # 移動相度増加（未実装）
        "SlowMovementSpeed": 0.0, # 鈍化（未実装）
        "DecreaseDefenseValue": 0.0, # 防御減少
        "StunAttack": 0.0, # 気絶攻撃（未実装）
        "GetStartFreeUnit": 0.0, # ユニットおまけ（未実装）
        "CooltimeRegen": 0.0, # クールタイム減少
        "HpPercentageAttack": 0.0, # ギガグラ（未実装）
        "FreeSummon": 0.0, # 無料召喚（未実装）
        "PhysicalDamage": 0.0, # 物理ダメ
        "MagicalDamage": 0.0, # 魔法ダメ
        "CriticalDamage": 0.0, # クリダメ
        "GetStartAdditionalPoint": 0.0, # コイン獲得（未実装）
        "AttackSpeed": 0.0, # 攻撃速度増加
        "GetSpecialPoint": 0.0, # 幸運石獲得（未実装）
        "CriticalPercentage": 0.0, # クリ率
        "GetAdditionalPointWhenSell": 0.0, # 販売時コイン（未実装）
        "KillWaveMonsterAtWaveCount": 0.0, # きあいのタスキ（未実装）
        "TotalAttackDamagePercentageBuff": 0.0, # 謎バフ
    }
    pet_slots: Dict[str, Dict[str, Any]] = {}
    for slot_key in ("pet1", "pet2", "pet3"):
        p = common.get(slot_key)
        if not isinstance(p, dict):
            pid, plv = "", 1
        else:
            pid = str(p.get("id", p.get("petId", "")) or "")
            plv = clamp_int(p.get("level", p.get("petLv", 1)), 1, 50, 1)
        skill_idx = 0
        get_start_free_unit = ""
        if pid:
            row = PET_DB_BY_ID.get(pid, {})
            raw = row.get("raw") if isinstance(row, dict) else None
            skills = raw.get("skills", []) if isinstance(raw, dict) else []
            for idx, skill in enumerate(skills):
                PetSkillType = skill.get("PetSkillType", "")
                param = skill.get("Paramter_1", [0]*50)[plv - 1] / 100
                if PetSkillType in ["SpRegen", "CriticalPercentage"]:
                    param = skill.get("Paramter_1", [0]*50)[plv - 1]
                pet_buff[PetSkillType] += param
    DebugMessage["pet_buff"] = pet_buff

    # ======= ブロッブ人形 =======
    BlobFigureBuff = {
        "片目": 0.0, # 未実装
        "仮面": 0.0, # 未実装
        "ぺたんこ": 0.0, # 未実装
        "肉": 0.0,
        "ハロウィン": 0.0,
        "パン": 0.0, 
        "軍人": 0.0,
        "バンバ": 0.0,
        "バット": 0.0, # 未実装
        "魔法使い": 0.0,
        "ドラゴン": 0.0,
        "スカル": 0.0,
        "サイボーグ": 0.0,
        "溶岩": 0.0,
        "ウォーター": 0.0,
        "ファイヤー": 0.0,
        "ゴールド": 0.0,
        "ダイヤ": 0.0,
    }

    for blobFigure in common.get("blobFigures", []):
        name = blobFigure.get("name")
        if name in BlobFigureBuff:
            BlobFigureBuff[name] = float(blobFigure.get("value", 0)) / 100
            if name in ["ドラゴン"] :
                BlobFigureBuff[name] = float(blobFigure.get("value", 0))
    DebugMessage["blobFigures"] = BlobFigureBuff

    # ======= ルーン =======
    RuneAtkSum = 0
    rune_name = str(member.get("runeName", "なし") or "なし")
    rune_rarity = str(member.get("runeRarity", "なし") or "なし")
    rune_effects: Dict[str, float] = {}
    if rune_name != "なし" and rune_rarity != "なし":
        rune_buff = RUNES_DB.get(rune_name).get("data").get(rune_rarity).get("buff")
        if rune_name == "hoge":
            pass
        if rune_name == "hoge":
            pass

    # ======= 防御から物理バフを計算 =======
    def_dec_per = 1 - BlobFigureBuff["軍人"] + pet_buff["DecreaseDefenseValue"] # 専用じゃない遺物どうするか
    enemy_def *= def_dec_per
    def_mult = 1 + sign(defDown - enemy_def)*(1 - 50/(3*abs(defDown - enemy_def) + 50))
    def_mult_prim_bamba = 1 + sign(defDown - enemy_def*0.75)*(1 - 50/(3*abs(defDown - enemy_def*0.75) + 50))

    # ======= 緑字攻撃力/攻撃速度計算 =======
    upgrade_atk = int(CHAR_DB[character_id]["upgrade_attack_damage"])
    base_speed = float(CHAR_DB[character_id]["attack_speed"])
    ult_mana = int(CHAR_DB[character_id]["sp"])
    lv1_atk = int(CHAR_DB[character_id]["attack_damage"])
    base_atk = lv1_atk + ((char_lv - 1) * upgrade_atk)
    if char_lv < 3:
        lv_buff_atk, lv_buff_speed = 1.0, 1.0
    elif char_lv < 9:
        lv_buff_atk, lv_buff_speed = 1.1, 1.0
    elif char_lv < 15:
        lv_buff_atk, lv_buff_speed = 1.1, 1.1
    else:
        lv_buff_atk, lv_buff_speed = 1.2, 1.2
    base_atk *= lv_buff_atk
    base_speed *= lv_buff_speed
    atk = base_atk + intake
    atk *= 1 + PowerPotion*2 + member.get("cannibalCount", 0) + unitLevelSumBuff + RuneAtkSum + BlobFigureBuff["ダイヤ"] + pet_buff["AttackDamage"]
    atk *= 1 + (int(common.get("mythEnhanceLv", 1)) - 1)*0.5 + int(member.get("ヴェイン", 0))
    if character_id in ["5023", "15004", "15011", "15024"]:
        atkBuffPct += 10
    if character_id in ["15023"]:
        atkBuffPct += 12
    if character_id in ["15021"]:
        atkBuffPct += 20
    atk *= 1 + coins*MoneyGun/100 + atkBuffPct + StrongestCreature + batEnhance + emotionControl_db[emotionControl] + ace_batman_attack_enhance[batEnhance_] / 100
    atk *= 1 + guildBuff_atk
    atk += base_atk
    speed = base_speed*(1 + speedBuffPct)*(1 + FairyBow*2 + BlobFigureBuff["ゴールド"] + pet_buff["AttackSpeed"])
    speed = min(speed, 8.0)
    # NOTE : ウチとワットの攻撃速度も変更すること！

    # ======= その他数値計算 =======
    crit_rate = 5 + BambaDoll + BlobFigureBuff["ドラゴン"] + pet_buff["CriticalPercentage"]
    crit_dmg = 2.5 + BlobFigureBuff["魔法使い"] + pet_buff["CriticalDamage"]
    mana_buff += BlobFigureBuff["ハロウィン"] + pet_buff["SpRegen"]
    mana_buff = 1 if mana_buff == 0 else mana_buff // 100 + 1
    MagicBuff1 = 1 + SecretBook + WizardHat + BlobFigureBuff["溶岩"] + BlobFigureBuff["スカル"] + pet_buff["MagicalDamage"]
    PhysicBuff1 = 1 + SecretBook + Bat + BlobFigureBuff["溶岩"] + BlobFigureBuff["サイボーグ"] + pet_buff["PhysicalDamage"]
    CooltimeBuff1 = 1 - BlobFigureBuff["肉"] - pet_buff["CooltimeRegen"]
    UltManaBuff1 = 1 - SageYogurt
    RateBuff1 = OldBook + BlobFigureBuff["パン"]
    UltBuff1 = 1 + pet_buff["UltimateDamage"]
    BasicAttackBuff1 = 1 + pet_buff["BasicAttackDamage"] + BlobFigureBuff["ファイヤー"]
    BossBuff1 = 1 + GreatSword + BlobFigureBuff["ウォーター"] + pet_buff["BossMonsterDamage"] + guildBuff_boss
    StunBuff1 = 1 + Bomb + BlobFigureBuff["バンバ"]
    PartyCat = 1 + pet_buff["TotalAttackDamagePercentageBuff"]
    TICK_COEFF = (30000 // (speed*duration_sec)) * 1
    ticks = int(speed * duration_sec* TICK_COEFF)

    if character_id == "1001":  # 弓兵
        ans = 1000
    elif character_id == "1002":  # 榴弾兵
        ans = 2000
    elif character_id == "1003":  # 野蛮人
        ans = 3000
    elif character_id == "1004":  # 水の精霊
        ans = 4000
    elif character_id == "1005":  # 山賊
        ans = 5000
    elif character_id == "2001":  # レンジャー
        ans = 6000
    elif character_id == "2002":  # ショックロボット
        ans = 7000
    elif character_id == "2003":  # 聖騎士
        ans = 8000
    elif character_id == "2004":  # サンドマン
        ans = 9000
    elif character_id == "2005":  # 悪魔の兵士
        ans = 10000
    elif character_id == "3001":  # 電気ロボット
        ans = 11000
    elif character_id == "3002":  # 木
        ans = 12000
    elif character_id == "3003":  # ハンター
        ans = 13000
    elif character_id == "3004":  # 重力弾
        basic, skill1, skill2, skill3, ult = mean_total_damage_15021(
            ticks=int(speed * duration_sec * TICK_COEFF),
            trials=int(common.get("trials", 1)),
            seed=seed,
            attack_power=atk,
            attack_speed=speed,
            mana_buff=mana_buff,
        )
        basic *= BasicAttackBuff1
        ans = basic + skill1 + skill2 + skill3 + ult
        ans = 14000
    elif character_id == "3005":  # イーグル将軍
        ans = 15000
    elif character_id == "3006":  # ウルフ戦士
        ans = 16000
    elif character_id == "3007":  # 忍者
        t_buff1 = float(TREASURE_DB["忍者"][treasure_lv][1])
        t_buff2 = float(TREASURE_DB["忍者"][treasure_lv][2]) / 100
        params = {
            "attack_power": atk,
            "attack_speed": speed,
            "base_attack_mult": 1.0,
            "skill1_rate": 10+RateBuff1,
            "skill2_rate": 12+RateBuff1 if 6 <= char_lv else 0,
            "react_rate": 55+t_buff1,
            "skill1_mult": 40*PhysicBuff1,
            "skill2_mult": 50*(PhysicBuff1+t_buff2),
            "ult_mult": 180*(PhysicBuff1+UltBuff1),
            "ult_mana": ult_mana*CooltimeBuff1 if 12 <= char_lv else 10**100,
            "mana_buff": 1,
            "crit_rate": crit_rate,
            "crit_dmg": crit_dmg,
            "ticks": ticks,
            "trials": trials,
            "seed": seed
        }
        basic_one = atk * params["base_attack_mult"]
        skill1_one = atk * params["skill1_mult"]
        skill2_one = atk * params["skill2_mult"]
        skill3_one = 0
        ult_one = atk * params["ult_mult"]
        basic, skill1, skill2, skill3, ult = mean_total_damage_3007(params)
        basic *= BasicAttackBuff1
        ans = basic + skill1 + skill2 + skill3 + ult
        mult_parts = _mparts(
            basic=_mp([1.0], []),
            skill1=_mp([40], ["PhysicBuff1"]),
            skill2=_mp([50], ["PhysicBuff1", "t_buff2"]),
            ult=_mp([180], ["PhysicBuff1", "UltBuff1"]),
        )
    elif character_id == "4001":  # オークシャーマン
        ans = mean_total_damage_15021(
            ticks=int(speed * duration_sec * TICK_COEFF),
            trials=int(common.get("trials", 1)),
            seed=seed,
            attack_power=atk,
            attack_speed=speed,
            mana_buff=mana_buff,
        )
        ans = 18000
    elif character_id == "4002":  # パルス発生器
        ans = mean_total_damage_15021(
            ticks=int(speed * duration_sec * TICK_COEFF),
            trials=int(common.get("trials", 1)),
            seed=seed,
            attack_power=atk,
            attack_speed=speed,
            mana_buff=mana_buff,
        )
        ans = 19000
    elif character_id == "4003":  # ウォーマシン
        ans = 20000
    elif character_id == "4004":  # 虎の師父
        ans = 21000
    elif character_id == "4005":  # 嵐の精霊
        ans = 22000
    elif character_id == "4006":  # 猫の魔法使い
        ans = mean_total_damage_15021(
            ticks=int(speed * duration_sec * TICK_COEFF),
            trials=int(common.get("trials", 1)),
            seed=seed,
            attack_power=atk,
            attack_speed=speed,
            mana_buff=mana_buff,
        )
        ans = 23000
    elif character_id == "4007":  # 保安官
        ans = 24000
    elif character_id == "4008":  # 謎のレジェンド
        ans = 25000
    elif character_id == "5001":  # バンバ
        params = {
            "attack_power": atk,
            "attack_speed": speed,
            "base_attack_mult": 1.0,
            "skill1_times": 10,
            "skill1_mult": 30*MagicBuff1,
            "skill2_rate": 8 + RateBuff1,
            "skill2_mult": 20*MagicBuff1,
            "ult_mana": ult_mana*UltManaBuff1,
            "ult_mult": 40,
            "crit_rate": crit_rate,
            "crit_dmg": crit_dmg,
        }
        basic_one = atk * params["base_attack_mult"]
        skill1_one = atk * params["skill1_mult"]
        skill2_one = atk * params["skill2_mult"]
        skill3_one = 0
        ult_one = atk * params["ult_mult"]
        ans = mean_total_damage_5001(params, ticks, trials, seed)
        mult_parts = _mparts(
            basic=_mp([1.0], []),
            skill1=_mp([30], ["MagicBuff1"]),
            skill2=_mp([20], ["MagicBuff1"]),
            ult=_mp([40], []),
        )
    elif character_id == "5002":  # コルディ
        params = {
            "ticks": ticks,
            "trials": trials,
            "seed": seed,
            "attack_power": atk,
            "attack_speed": speed,
            "base_attack_mult": 1.0,
            "skill1_rate": 8 + RateBuff1 if 6 <= char_lv else 0,
            "skill1_mult": 20*MagicBuff1,
            "skill2_rate": 8 + RateBuff1,
            "skill2_mult": 20*MagicBuff1,
            "skill3_rate": 0,
            "skill3_mult": 0,
            "ult_mana": ult_mana*UltManaBuff1,
            "ult_mult": 15*icecount*icerate*(MagicBuff1+UltBuff1),
            "attack_mana_recov": 1,
            "mana_buff": mana_buff,
            "crit_rate": crit_rate,
            "crit_dmg": crit_dmg + MagicGauntlet,
        }
        basic_one = atk * params["base_attack_mult"]
        skill1_one = atk * params["skill1_mult"]
        skill2_one = atk * params["skill2_mult"]
        skill3_one = atk * params["skill3_mult"]
        ult_one = atk * params["ult_mult"]
        basic, skill1, skill2, skill3, ult = mean_total_damage_common(params)
        basic *= BasicAttackBuff1
        ans = basic + skill1 + skill2 + skill3 + ult
        mult_parts = _mparts(
            basic=_mp([1.0], []),
            skill1=_mp([20], ["MagicBuff1"]),
            skill2=_mp([20], ["MagicBuff1"]),
            skill3=_mp([0], []),
            ult=_mp([15], ["icecount", "icerate", "MagicBuff1", "UltBuff1"]),
        )
    elif character_id == "5003":  # ランスロット
        ans = 28000
    elif character_id == "5004":  # アイアンニャン
        t_buff1 = float(TREASURE_DB["アイアンニャン"][treasure_lv][1]) / 100
        t_buff2 = float(TREASURE_DB["アイアンニャン"][treasure_lv][2])
        params = {
            "ticks": ticks,
            "trials": trials,
            "seed": seed,
            "attack_power": atk,
            "attack_speed": speed,
            "base_attack_mult": 5.0,
            "skill1_rate": 8 + RateBuff1,
            "skill1_mult": 40*(t_buff1+MagicBuff1) if char_lv < 12 else 60*(t_buff1+MagicBuff1),
            "skill2_rate": 0,
            "skill2_mult": 0,
            "skill3_rate": 0,
            "skill3_mult": 0,
            "ult_mana": ult_mana*UltManaBuff1,
            "ult_mult": 180*(t_buff1+MagicBuff1+UltBuff1) if char_lv < 12 else 270*(t_buff1+MagicBuff1+UltBuff1),
            "attack_mana_recov": 1,
            "mana_buff": mana_buff,
            "crit_rate": crit_rate + t_buff2,
            "crit_dmg": crit_dmg + MagicGauntlet,
        }
        basic_one = atk * params["base_attack_mult"]
        skill1_one = atk * params["skill1_mult"]
        skill2_one = atk * params["skill2_mult"]
        skill3_one = atk * params["skill3_mult"]
        ult_one = atk * params["ult_mult"]
        basic, skill1, skill2, skill3, ult = mean_total_damage_common(params)
        basic *= BasicAttackBuff1
        ans = basic + skill1 + skill2 + skill3 + ult
        mult_parts = _mparts(
            basic=_mp([5.0], []),
            skill1=_mp([40, 60], ["t_buff1", "MagicBuff1"]),
            skill2=_mp([0], []),
            skill3=_mp([0], []),
            ult=_mp([180, 270], ["t_buff1", "MagicBuff1", "UltBuff1"]),
        )
    elif character_id == "5005":  # ブロッブ
        ans = sp * 1000
    elif character_id == "5006":  # ドラゴン(変身前)
        ans = 0
    elif character_id == "5007":  # モノポリーマン
        ans = mean_total_damage_15021(
            ticks=int(speed * duration_sec * TICK_COEFF),
            trials=int(common.get("trials", 1)),
            seed=seed,
            attack_power=atk,
            attack_speed=speed,
            mana_buff=mana_buff,
        )
        ans = 32000
    elif character_id == "5008":  # ママ
        t_buff1 = int(TREASURE_DB["ママ"][treasure_lv][2]) / 100
        params = {
            "ticks": ticks,
            "trials": trials,
            "seed": seed,
            "attack_power": atk,
            "attack_speed": speed,
            "base_attack_mult": 5.0,
            "skill1_rate": 8 + RateBuff1 if 6 <= char_lv else 0,
            "skill1_mult": 15*(MagicBuff1+t_buff1) if char_lv < 12 else 30*(MagicBuff1+t_buff1),
            "skill2_rate": 0,
            "skill2_mult": 0,
            "skill3_rate": 0,
            "skill3_mult": 0,
            "ult_mana": ult_mana*UltManaBuff1,
            "ult_mult": 20*(MagicBuff1+t_buff1+UltBuff1) if char_lv < 12 else 40*(MagicBuff1+t_buff1+UltBuff1),
            "attack_mana_recov": 1,
            "mana_buff": mana_buff,
            "crit_rate": crit_rate,
            "crit_dmg": crit_dmg + MagicGauntlet,
        }
        basic_one = atk * params["base_attack_mult"]
        skill1_one = atk * params["skill1_mult"]
        skill2_one = atk * params["skill2_mult"]
        skill3_one = atk * params["skill3_mult"]
        ult_one = atk * params["ult_mult"]
        basic, skill1, skill2, skill3, ult = mean_total_damage_common(params)
        basic *= BasicAttackBuff1
        ans = basic + skill1 + skill2 + skill3 + ult
        mult_parts = _mparts(
            basic=_mp([5.0], []),
            skill1=_mp([15, 30], ["MagicBuff1", "t_buff1"]),
            skill2=_mp([0], []),
            skill3=_mp([0], []),
            ult=_mp([20, 40], ["MagicBuff1", "t_buff1", "UltBuff1"]),
        )
    elif character_id == "5009":  # カエルの王様
        
        
        ans = mean_total_damage_15021(
            ticks=int(speed * duration_sec * TICK_COEFF),
            trials=int(common.get("trials", 1)),
            seed=seed,
            attack_power=atk,
            attack_speed=speed,
            mana_buff=mana_buff,
        )
        ans = 34000
    elif character_id == "5010":  # バットマン
        t_buff1 = float(TREASURE_DB["バットマン"][treasure_lv][2])
        params = {
            "ticks": ticks,
            "trials": trials,
            "seed": seed,
            "attack_power": atk,
            "attack_speed": speed,
            "base_attack_mult": 1.0,
            "skill1_rate": 12 + RateBuff1,
            "skill1_mult": 40*PhysicBuff1,
            "skill2_rate": 0,
            "skill2_mult": 0,
            "skill3_rate": 0,
            "skill3_mult": 0,
            "ult_mana": ult_mana*CooltimeBuff1,
            "ult_mult": 70*(PhysicBuff1+UltBuff1),
            "attack_mana_recov": 0,
            "mana_buff": 1,
            "crit_rate": crit_rate + t_buff1,
            "crit_dmg": crit_dmg,
        }
        basic_one = atk * params["base_attack_mult"]
        skill1_one = atk * params["skill1_mult"]
        skill2_one = atk * params["skill2_mult"]
        skill3_one = atk * params["skill3_mult"]
        ult_one = atk * params["ult_mult"]
        basic, skill1, skill2, skill3, ult = mean_total_damage_common(params)
        basic *= BasicAttackBuff1
        ans = basic + skill1 + skill2 + skill3 + ult
        mult_parts = _mparts(
            basic=_mp([1.0], []),
            skill1=_mp([40], ["PhysicBuff1"]),
            skill2=_mp([0], []),
            skill3=_mp([0], []),
            ult=_mp([70], ["PhysicBuff1", "UltBuff1"]),
        )
    elif character_id == "5011":  # ヴェイン
        ans = mean_total_damage_15021(
            ticks=int(speed * duration_sec * TICK_COEFF),
            trials=int(common.get("trials", 1)),
            seed=seed,
            attack_power=atk,
            attack_speed=speed,
            mana_buff=mana_buff,
        )
        ans = 36000
    elif character_id == "5012":  # インディ
        
        
        ans = mean_total_damage_15021(
            ticks=int(speed * duration_sec * TICK_COEFF),
            trials=int(common.get("trials", 1)),
            seed=seed,
            attack_power=atk,
            attack_speed=speed,
            mana_buff=mana_buff,
        )
        ans = 37000
    elif character_id == "5013":  # ワット（究極発動中）
        buff_mult = 0.03 if char_lv < 6 else 0.05
        ult_mult = 20*(MagicBuff1+UltBuff1)
        speed = min(speed*2, 8.0)
        cirt_dmg = crit_dmg + MagicGauntlet
        DebugMessage["atk"] = atk
        DebugMessage["speed"] = speed
        DebugMessage["cirt_dmg"] = cirt_dmg
        DebugMessage["crit_rate"] = crit_rate
        DebugMessage["buff_mult"] = buff_mult
        DebugMessage["ult_mult"] = ult_mult
        DebugMessage["energyCount"] = energyCount
        basic, skill1, skill2, skill3, ult = mean_total_damage_5013(
            tick=int(speed * duration_sec),
            attack_power=atk,
            attack_speed=speed,
            buff_mult=buff_mult,
            cirt_rate=crit_rate,
            cirt_dmg=cirt_dmg,
            ult_mult=ult_mult,
            watt_stack=energyCount,
        )
        basic *= BasicAttackBuff1
        DebugMessage["ans"] = basic + skill1 + skill2 + skill3 + ult
        basic *= TICK_COEFF
        skill1 *= TICK_COEFF
        skill2 *= TICK_COEFF
        skill3 *= TICK_COEFF
        ult *= TICK_COEFF
        ans = basic + skill1 + skill2 + skill3 + ult
        mult_parts = _mparts(
            ult=_mp([20], ["MagicBuff1", "UltBuff1"]),
        )
        ult_one = atk * (20 * (MagicBuff1 + UltBuff1))
    elif character_id == "5014":  # タール小
        
        
        ans = mean_total_damage_15021(
            ticks=int(speed * duration_sec * TICK_COEFF),
            trials=int(common.get("trials", 1)),
            seed=seed,
            attack_power=atk,
            attack_speed=speed,
            mana_buff=mana_buff,
        )
        ans = 39000
    elif character_id == "5015":  # ロケッチュー(変身前)
        #ans = mean_total_damage_15021(
            #ticks=int(speed * duration_sec * TICK_COEFF),
            #trials=int(common.get("trials", 1)),
            #seed=seed,
            #attack_power=atk,
            #attack_speed=speed,
            #mana_buff=mana_buff,
        #)
        ans = 40000
    elif character_id == "5016":  # ウチ
        t_buff1 = 1 + float(TREASURE_DB["ウチ"][treasure_lv][1])
        t_buff2 = float(TREASURE_DB["ウチ"][treasure_lv][2]) / 100
        speed = base_speed*(1 + speedBuffPct + t_buff2)*(1 + FairyBow + BlobFigureBuff["ゴールド"] + pet_buff["AttackSpeed"])
        speed = min(speed, 8.0)
        params = {
            "ticks": ticks,
            "trials": trials,
            "seed": seed,
            "attack_power": atk,
            "attack_speed": speed,
            "base_attack_mult": 1.0,
            "skill1_rate": 10 + RateBuff1 if char_lv < 12 else 20 + RateBuff1,
            "skill1_mult": 75*t_buff1*MagicBuff1,
            "skill2_rate": 0,
            "skill2_mult": 0,
            "skill3_rate": 0,
            "skill3_mult": 0,
            "ult_mana": ult_mana*UltManaBuff1,
            "ult_mult": 398*(MagicBuff1+UltBuff1),
            "attack_mana_recov": 1,
            "mana_buff": mana_buff,
            "crit_rate": crit_rate,
            "crit_dmg": crit_dmg + MagicGauntlet,
        }
        basic_one = atk * params["base_attack_mult"]
        skill1_one = atk * params["skill1_mult"]
        skill2_one = atk * params["skill2_mult"]
        skill3_one = atk * params["skill3_mult"]
        ult_one = atk * params["ult_mult"]
        basic, skill1, skill2, skill3, ult = mean_total_damage_common(params)
        basic *= BasicAttackBuff1
        ans = basic + skill1 + skill2 + skill3 + ult
        ans *= uchiCells * 1.41421356 + 1 if 6 <= char_lv else 1
        mult_parts = _mparts(
            basic=_mp([1.0], []),
            skill1=_mp([75], ["t_buff1", "MagicBuff1"]),
            skill2=_mp([0], []),
            skill3=_mp([0], []),
            ult=_mp([398], ["MagicBuff1", "UltBuff1"]),
        )
    elif character_id == "5017":  # ビリ
        
        
        ans = mean_total_damage_15021(
            ticks=int(speed * duration_sec * TICK_COEFF),
            trials=int(common.get("trials", 1)),
            seed=seed,
            attack_power=atk,
            attack_speed=speed,
            mana_buff=mana_buff,
        )
        ans = 42000
    elif character_id == "5018":  # マスタークン
        t_buff1 = 1 + float(TREASURE_DB["マスタークン"][treasure_lv][1]) /100
        t_buff2 = float(TREASURE_DB["マスタークン"][treasure_lv][2])
        skill1_interval = [2.1, 1.05, 0.7, 0.525, 0.42]
        params = {
            "tick": ticks,
            "attack_power": atk,
            "attack_speed": speed,
            "base_attack_mult": 1.0,
            "skill1_mult": 5.5*(MagicBuff1)*t_buff1 if char_lv < 12 else 5.5*(MagicBuff1 + 0.5)*t_buff1,
            "skill2_mult": 50*(MagicBuff1) if char_lv < 12 else 50*(MagicBuff1 + 0.5)*1.5,
            "skill1_rate": 6 + RateBuff1 + t_buff2 if 6 <= char_lv else 0,
            "skill2_rate": 8 + RateBuff1 + t_buff2,
            "skill3_rate": 0,
            "crit_rate": crit_rate,
            "crit_dmg": crit_dmg + MagicGauntlet,
            "skill1_interval": skill1_interval[2 + emotionControl // 30 - 1],
            "n_iter": trials,
            "seed": seed,
        }
        basic_one = atk * params["base_attack_mult"]
        skill1_one = atk * params["skill1_mult"]
        skill2_one = atk * params["skill2_mult"]
        skill3_one = 0
        ult_one = 0
        basic, skill1, skill2, skill3, ult = mean_total_damage_5018(params)
        basic *= BasicAttackBuff1
        ans = basic + skill1 + skill2 + skill3 + ult
        mult_parts = _mparts(
            basic=_mp([1.0], []),
            skill1=_mp([5.5, 0.5], ["MagicBuff1", "t_buff1"]),
            skill2=_mp([50, 0.5, 1.5], ["MagicBuff1"]),
        )
    elif character_id == "5019":  # チョナ
        t_buff1 = float(TREASURE_DB["チョナ"][treasure_lv][1]) / 100
        t_buff2 = float(TREASURE_DB["チョナ"][treasure_lv][2])
        ult_rate = 0.12
        ult_rate += t_buff2/100
        ult_mult_ = 30*ult_rate*65 + 30*(1 - ult_rate)*25
        params = {
            "ticks": ticks,
            "trials": trials,
            "seed": seed,
            "attack_power": atk,
            "attack_speed": speed,
            "skill1_rate": 15 + RateBuff1 + t_buff2 if 6 <= char_lv else 10 + RateBuff1 + t_buff2,
            "skill1_mult": 60*PhysicBuff1,
            "skill2_mult": 70*PhysicBuff1,
            "ult_mult": 750*(PhysicBuff1+UltBuff1) if char_lv < 12 else ult_mult_*(PhysicBuff1+UltBuff1),
            "ult_mana": 40*(CooltimeBuff1 - t_buff1),
            "crit_rate": crit_rate,
            "crit_dmg": crit_dmg,
        }
        basic_one = atk
        skill1_one = atk * params["skill1_mult"]
        skill2_one = atk * params["skill2_mult"]
        skill3_one = 0
        ult_one = atk * params["ult_mult"]
        basic, skill1, skill2, skill3, ult = mean_total_damage_5019(params)
        basic *= BasicAttackBuff1
        ans = basic + skill1 + skill2 + skill3 + ult
        mult_parts = _mparts(
            basic=_mp([1], []),
            skill1=_mp([60], ["PhysicBuff1"]),
            skill2=_mp([70], ["PhysicBuff1"]),
            ult=_mp([750, 30, 65, 25, 0.12, 100], ["PhysicBuff1", "UltBuff1", "t_buff2"]),
        )
    elif character_id == "5020":  # ペンギン楽師
        t_buff1 = float(TREASURE_DB["ペンギン楽師"][treasure_lv][2])
        params = {
            "ticks": ticks,
            "trials": trials,
            "seed": seed,
            "attack_power": atk,
            "attack_speed": speed,
            "base_attack_mult": 1.0,
            "skill1_rate": 10 + RateBuff1 + t_buff1,
            "skill1_mult": 0,
            "skill2_rate": 10+RateBuff1+t_buff1 if char_lv < 6 else 15+RateBuff1+t_buff1,
            "skill2_mult": 60*PhysicBuff1,
            "skill3_rate": 0,
            "skill3_mult": 0,
            "ult_mana": 10**100,
            "ult_mult": 1 + UltBuff1,
            "attack_mana_recov": 1,
            "mana_buff": mana_buff,
            "crit_rate": crit_rate,
            "crit_dmg": crit_dmg,
        }
        basic_one = atk * params["base_attack_mult"]
        skill1_one = atk * params["skill1_mult"]
        skill2_one = atk * params["skill2_mult"]
        skill3_one = atk * params["skill3_mult"]
        ult_one = atk * params["ult_mult"]
        basic, skill1, skill2, skill3, ult = mean_total_damage_common(params)
        basic *= BasicAttackBuff1
        ans = basic + skill1 + skill2 + skill3 + ult
        mult_parts = _mparts(
            basic=_mp([1.0], []),
            skill1=_mp([0], []),
            skill2=_mp([60], ["PhysicBuff1"]),
            skill3=_mp([0], []),
            ult=_mp([1], ["UltBuff1"]),
        )
    elif character_id == "5021":  # ヘイリー
        t_buff1 = float(TREASURE_DB["ヘイリー"][treasure_lv][2]) / 100
        skill1_rate = 10 + RateBuff1
        skill2_rate = 0 if char_lv < 12 else 12 + RateBuff1
        skill1_mult = 50*MagicBuff1
        skill2_mult = 50*MagicBuff1
        ult_mana = 250*UltManaBuff1
        crit_dmg = crit_dmg + MagicGauntlet + t_buff1

        starPower_mult = 2 if char_lv < 6 else 4
        atk = base_atk
        atk *= 1 + PowerPotion*2 + unitLevelSumBuff
        atk *= 1 + (int(common.get("mythEnhanceLv", 1)) - 1)*0.5
        atk *= 1 + coins*MoneyGun/100 + atkBuffPct + starPower*starPower_mult
        atk *= 1 + guildBuff_atk
        atk += base_atk

        attack_power_ult = base_atk
        attack_power_ult *= 1 + PowerPotion*2 + unitLevelSumBuff
        attack_power_ult *= 1 + (int(common.get("mythEnhanceLv", 1)) - 1)*0.5
        attack_power_ult *= 1 + coins*MoneyGun/100 + atkBuffPct + starPower*starPower_mult*1.5
        attack_power_ult *= 1 + guildBuff_atk
        attack_power_ult += base_atk

        basic_one = atk
        skill1_one = atk * skill1_mult
        skill2_one = atk * skill2_mult
        ult_one = 0
        basic, skill1, skill2, skill3, ult = mean_total_damage_5021(
            ticks=ticks,
            trials=trials,
            seed=seed,
            skill1_rate=skill1_rate,
            skill2_rate=skill2_rate,
            attack_speed=speed,
            attack_power=atk,
            skill1_mult=skill1_mult,
            skill2_mult=skill2_mult,
            attack_power_ult=attack_power_ult,
            ult_mana=ult_mana,
            mana_buff=mana_buff,
            tick_seconds=1.0,
            crit_rate=crit_rate,
            crit_dmg=crit_dmg,
        )
        basic *= BasicAttackBuff1
        ans = basic + skill1 + skill2 + skill3 + ult
        mult_parts = _mparts(
            basic=_mp([1], []),
            skill1=_mp([50], ["MagicBuff1"]),
            skill2=_mp([50], ["MagicBuff1"]),
        )
    elif character_id == "5022":  # アト
        
        
        ans = mean_total_damage_15021(
            ticks=int(speed * duration_sec * TICK_COEFF),
            trials=int(common.get("trials", 1)),
            seed=seed,
            attack_power=atk,
            attack_speed=speed,
            mana_buff=mana_buff,
        )
        ans = 47000
    elif character_id == "5023":  # ロカ
        t_buff1 = float(TREASURE_DB["ロカ"][treasure_lv][1])
        t_buff2 = float(TREASURE_DB["ロカ"][treasure_lv][2]) / 100
        params = {
            "ticks": ticks,
            "trials": trials,
            "seed": seed,
            "attack_power": atk,
            "attack_speed": speed,
            "skill1_mult": 40*PhysicBuff1 if 12 <= char_lv else 20*PhysicBuff1,
            "skill2_mult": 10 if 6 <= char_lv else 6,
            "skill2_rate": 7 + RateBuff1,
            "skill3_mult": 65*PhysicBuff1,
            "ult_mult": 200*(PhysicBuff1+UltBuff1),
            "ult_mana": ult_mana*CooltimeBuff1,
            "crit_rate": roka_crit + crit_rate,
            "bomb_rate": t_buff1,
            "crit_dmg": crit_dmg + t_buff2,
        }
        basic_one = atk
        skill1_one = atk * params["skill1_mult"]
        skill2_one = atk * params["skill2_mult"]
        skill3_one = atk * params["skill3_mult"]
        ult_one = atk * params["ult_mult"]
        basic, skill1, skill2, skill3, ult = mean_total_damage_5023(params)
        basic *= BasicAttackBuff1
        ans = basic + skill1 + skill2 + skill3 + ult
        mult_parts = _mparts(
            basic=_mp([1], []),
            skill1=_mp([20, 40], ["PhysicBuff1"]),
            skill2=_mp([6, 10], []),
            skill3=_mp([65], ["PhysicBuff1"]),
            ult=_mp([200], ["PhysicBuff1", "UltBuff1"]),
        )
    elif character_id == "5024":  # 選鳥師
        t_buff2 = float(TREASURE_DB["選鳥師"][treasure_lv][2])
        MagicBuff1 += score if char_lv < 6 else score*2
        params = {
            "ticks": ticks,
            "trials": trials,
            "seed": seed,
            "attack_power": atk,
            "attack_speed": speed,
            "base_attack_mult": 1.0,
            "skill1_rate": 8 + RateBuff1 + t_buff2,
            "skill1_mult": 35*(MagicBuff1) if score < 0.3 else 105*(MagicBuff1),
            "skill2_rate": 6 + RateBuff1 + t_buff2 if 12 <= char_lv else 0,
            "skill2_mult": 24*(MagicBuff1) if score < 0.7 else 40*(MagicBuff1),
            "skill3_rate": 0,
            "skill3_mult": 0,
            "ult_mana": 10**100,
            "ult_mult": 0*(1 + UltBuff1),
            "attack_mana_recov": 1,
            "mana_buff": 1,
            "crit_rate": crit_rate,
            "crit_dmg": crit_dmg + MagicGauntlet,
        }
        basic_one = atk * params["base_attack_mult"]
        skill1_one = atk * params["skill1_mult"]
        skill2_one = atk * params["skill2_mult"]
        skill3_one = atk * params["skill3_mult"]
        ult_one = atk * params["ult_mult"]
        basic, skill1, skill2, skill3, ult = mean_total_damage_common(params)
        basic *= BasicAttackBuff1
        ans = basic + skill1 + skill2 + skill3 + ult
        mult_parts = _mparts(
            basic=_mp([1.0], []),
            skill1=_mp([35, 105], ["MagicBuff1"]),
            skill2=_mp([24, 40], ["MagicBuff1"]),
            skill3=_mp([0], []),
            ult=_mp([0, 1], ["UltBuff1"]),
        )
    elif character_id == "5104":  # アイアンニャン
        t_buff1 = float(TREASURE_DB["アイアンニャン"][treasure_lv][1]) / 100
        t_buff2 = float(TREASURE_DB["アイアンニャン"][treasure_lv][2])
        params = {
            "ticks": ticks,
            "trials": trials,
            "seed": seed,
            "attack_power": atk,
            "attack_speed": speed,
            "base_attack_mult": 5.0,
            "skill1_rate": 8 + RateBuff1,
            "skill1_mult": 40*(t_buff1+MagicBuff1) if char_lv < 12 else 60*(t_buff1+MagicBuff1),
            "skill2_rate": 0,
            "skill2_mult": 0,
            "skill3_rate": 0,
            "skill3_mult": 0,
            "ult_mana": ult_mana*UltManaBuff1,
            "ult_mult": 180*(t_buff1+MagicBuff1+UltBuff1) if char_lv < 12 else 270*(t_buff1+MagicBuff1+UltBuff1),
            "attack_mana_recov": 1,
            "mana_buff": mana_buff,
            "crit_rate": crit_rate + t_buff2,
            "crit_dmg": crit_dmg + MagicGauntlet,
        }
        basic_one = atk * params["base_attack_mult"]
        skill1_one = atk * params["skill1_mult"]
        skill2_one = atk * params["skill2_mult"]
        skill3_one = atk * params["skill3_mult"]
        ult_one = atk * params["ult_mult"]
        basic, skill1, skill2, skill3, ult = mean_total_damage_common(params)
        basic *= BasicAttackBuff1
        ans = basic + skill1 + skill2 + skill3 + ult
        mult_parts = _mparts(
            basic=_mp([5.0], []),
            skill1=_mp([40, 60], ["t_buff1", "MagicBuff1"]),
            skill2=_mp([0], []),
            skill3=_mp([0], []),
            ult=_mp([180, 270], ["t_buff1", "MagicBuff1", "UltBuff1"]),
        )
    elif character_id == "5106":  # ドラゴン(変身後)
        t_buff1 = float(TREASURE_DB["ドラゴン"][treasure_lv][2]) / 100
        t_buff2 = float(TREASURE_DB["ドラゴン"][treasure_lv][3]) / 100
        params = {
            "ticks": ticks,
            "trials": trials,
            "seed": seed,
            "attack_power": atk,
            "attack_speed": speed,
            "base_attack_mult": 1.0,
            "skill1_rate": 8 + RateBuff1,
            "skill1_mult": 50*(MagicBuff1+t_buff2),
            "skill2_rate": 10 + RateBuff1,
            "skill2_mult": 60*(MagicBuff1+t_buff2),
            "skill3_rate": 0,
            "skill3_mult": 0,
            "ult_mana": 100*UltManaBuff1 if 12 <= char_lv else 10**100,
            "ult_mult": 180*(MagicBuff1+t_buff2+UltBuff1),
            "attack_mana_recov": 1,
            "mana_buff": mana_buff,
            "crit_rate": crit_rate,
            "crit_dmg": crit_dmg + MagicGauntlet,
        }
        basic_one = atk * params["base_attack_mult"]
        skill1_one = atk * params["skill1_mult"]
        skill2_one = atk * params["skill2_mult"]
        skill3_one = atk * params["skill3_mult"]
        ult_one = atk * params["ult_mult"]
        basic, skill1, skill2, skill3, ult = mean_total_damage_common(params)
        basic *= BasicAttackBuff1
        ans = basic + skill1 + skill2 + skill3 + ult
        mult_parts = _mparts(
            basic=_mp([1.0], []),
            skill1=_mp([50], ["MagicBuff1", "t_buff2"]),
            skill2=_mp([60], ["MagicBuff1", "t_buff2"]),
            skill3=_mp([0], []),
            ult=_mp([180], ["MagicBuff1", "t_buff2", "UltBuff1"]),
        )
    elif character_id == "5108":  # インプ
        
        
        ans = mean_total_damage_15021(
            ticks=int(speed * duration_sec * TICK_COEFF),
            trials=int(common.get("trials", 1)),
            seed=seed,
            attack_power=atk,
            attack_speed=speed,
            mana_buff=mana_buff,
        )
        ans = 52000
    elif character_id == "5109":  # キングダイアン
        t_buff1 = float(TREASURE_DB["キングダイアン"][treasure_lv][2]) / 100
        params = {
            "ticks": ticks,
            "trials": trials,
            "seed": seed,
            "attack_power": atk,
            "attack_speed": speed,
            "base_attack_mult": 7.5,
            "skill1_rate": 0,
            "skill1_mult": 0,
            "skill2_rate": 0,
            "skill2_mult": 0,
            "skill3_rate": 0,
            "skill3_mult": 0,
            "ult_mana": ult_mana*UltManaBuff1,
            "ult_mult": 1000*(MagicBuff1+t_buff1+UltBuff1),
            "attack_mana_recov": 1,
            "mana_buff": mana_buff,
            "crit_rate": crit_rate,
            "crit_dmg": crit_dmg + MagicGauntlet,
        }
        basic_one = atk * params["base_attack_mult"]
        skill1_one = atk * params["skill1_mult"]
        skill2_one = atk * params["skill2_mult"]
        skill3_one = atk * params["skill3_mult"]
        ult_one = atk * params["ult_mult"]
        basic, skill1, skill2, skill3, ult = mean_total_damage_common(params)
        basic *= BasicAttackBuff1
        ans = basic + skill1 + skill2 + skill3 + ult
        mult_parts = _mparts(
            basic=_mp([7.5], []),
            skill1=_mp([0], []),
            skill2=_mp([0], []),
            skill3=_mp([0], []),
            ult=_mp([1000], ["MagicBuff1", "t_buff1", "UltBuff1"]),
        )
    elif character_id == "5114":  # タール中
        
        
        ans = mean_total_damage_15021(
            ticks=int(speed * duration_sec * TICK_COEFF),
            trials=int(common.get("trials", 1)),
            seed=seed,
            attack_power=atk,
            attack_speed=speed,
            mana_buff=mana_buff,
        )
        ans = 54000
    elif character_id == "5115":  # ロケッチュー(変身後)
        t_buff1 = int(TREASURE_DB["ロケッチュー"][treasure_lv][2])
        params = {
            "ticks": ticks,
            "trials": trials,
            "seed": seed,
            "attack_power": atk,
            "attack_speed": speed,
            "skill1_rate": 10 + RateBuff1,
            "skill1_mult": 60*PhysicBuff1,
            "skill2_mult": 160*PhysicBuff1,
            "skill2_stack": t_buff1 if 12 <= char_lv else 10**100,
            "ult_mult": 700*(PhysicBuff1+UltBuff1),
            "ult_mana": 25*CooltimeBuff1,
            "crit_rate": crit_rate,
            "crit_dmg": crit_dmg,
        }
        basic_one = atk
        skill1_one = atk * params["skill1_mult"]
        skill2_one = atk * params["skill2_mult"]
        skill3_one = 0
        ult_one = atk * params["ult_mult"]
        basic, skill1, skill2, skill3, ult = mean_total_damage_5115(params)
        basic *= BasicAttackBuff1
        ans = basic + skill1 + skill2 + skill3 + ult
        ans *= 1.5
        mult_parts = _mparts(
            basic=_mp([1], []),
            skill1=_mp([60], ["PhysicBuff1"]),
            skill2=_mp([160], ["PhysicBuff1"]),
            ult=_mp([700], ["PhysicBuff1", "UltBuff1"]),
        )
    elif character_id == "5204":  # アイアンニャンv2
        t_buff1 = float(TREASURE_DB["アイアンニャン"][treasure_lv][1]) / 100
        t_buff2 = float(TREASURE_DB["アイアンニャン"][treasure_lv][2])
        params = {
            "ticks": ticks,
            "trials": trials,
            "seed": seed,
            "attack_power": atk,
            "attack_speed": speed,
            "base_attack_mult": 5.0,
            "skill1_rate": 8 + RateBuff1,
            "skill1_mult": 50*(MagicBuff1+t_buff1+techEnhance) if char_lv < 12 else 75*(MagicBuff1+t_buff1+techEnhance),
            "skill2_rate": 0,
            "skill2_mult": 0,
            "skill3_rate": 0,
            "skill3_mult": 0,
            "ult_mana": ult_mana*UltManaBuff1,
            "ult_mult": 360*(MagicBuff1+t_buff1+techEnhance+UltBuff1) if char_lv < 12 else 540*(MagicBuff1+t_buff1+techEnhance+UltBuff1),
            "attack_mana_recov": 1,
            "mana_buff": mana_buff,
            "crit_rate": crit_rate + t_buff2,
            "crit_dmg": crit_dmg + MagicGauntlet,
        }
        basic_one = atk * params["base_attack_mult"]
        skill1_one = atk * params["skill1_mult"]
        skill2_one = atk * params["skill2_mult"]
        skill3_one = atk * params["skill3_mult"]
        ult_one = atk * params["ult_mult"]
        basic, skill1, skill2, skill3, ult = mean_total_damage_common(params)
        basic *= BasicAttackBuff1
        ans = basic + skill1 + skill2 + skill3 + ult
        mult_parts = _mparts(
            basic=_mp([5.0], []),
            skill1=_mp([50, 75], ["MagicBuff1", "t_buff1", "techEnhance"]),
            skill2=_mp([0], []),
            skill3=_mp([0], []),
            ult=_mp([360, 540], ["MagicBuff1", "t_buff1", "techEnhance", "UltBuff1"]),
        )
    elif character_id == "5206":  # 偉大な卵
        ans = 0
    elif character_id == "5214":  # タール大
        t_buff1 = float(TREASURE_DB["タール"][treasure_lv][2])
        params = {
            "ticks": ticks,
            "trials": trials,
            "seed": seed,
            "attack_power": atk,
            "attack_speed": speed,
            "base_attack_mult": 1,
            "skill1_rate": 12 + RateBuff1 + t_buff1,
            "skill1_mult": 200*PhysicBuff1,
            "skill2_rate": 12 + RateBuff1 + t_buff1,
            "skill2_mult": 50*PhysicBuff1,
            "skill3_rate": 0,
            "skill3_mult": 0,
            "ult_mana": ult_mana*UltManaBuff1,
            "ult_mult": 150*(PhysicBuff1+UltBuff1)*1.3,
            "attack_mana_recov": 1,
            "mana_buff": mana_buff,
            "crit_rate": crit_rate,
            "crit_dmg": crit_dmg,
        }
        basic_one = atk * params["base_attack_mult"]
        skill1_one = atk * params["skill1_mult"]
        skill2_one = atk * params["skill2_mult"]
        skill3_one = atk * params["skill3_mult"]
        ult_one = atk * params["ult_mult"]
        basic, skill1, skill2, skill3, ult = mean_total_damage_common(params)
        basic *= BasicAttackBuff1
        ans = basic + skill1 + skill2 + skill3 + ult
        mult_parts = _mparts(
            basic=_mp([1], []),
            skill1=_mp([200], ["PhysicBuff1"]),
            skill2=_mp([50], ["PhysicBuff1"]),
            skill3=_mp([0], []),
            ult=_mp([150, 1.3], ["PhysicBuff1", "UltBuff1"]),
        )
    elif character_id == "5306":  # ドレイン
        t_buff1 = float(TREASURE_DB["ドラゴン"][treasure_lv][2]) / 100 # 火花
        t_buff2 = float(TREASURE_DB["ドラゴン"][treasure_lv][3]) / 100 # スキル
        MagicBuff1 += t_buff2
        MagicBuff2 = MagicBuff1 + t_buff1
        params = {
            "ticks": ticks,
            "trials": trials,
            "seed": seed,
            "attack_power": atk,
            "attack_speed": speed,
            "base_attack_mult": 1.0,
            "skill1_rate": 8 + RateBuff1,
            "skill1_mult": (50*MagicBuff1 + 25*MagicBuff2),
            "skill2_rate": 10 + RateBuff1,
            "skill2_mult": (60*MagicBuff1 + 25*MagicBuff2),
            "skill3_rate": 0,
            "skill3_mult": 0,
            "ult_mana": ult_mana*UltManaBuff1 if 12 <= char_lv else 10**100,
            "ult_mult": 180*(MagicBuff1+UltBuff1) + 75*(MagicBuff2+UltBuff1),
            "attack_mana_recov": 1,
            "mana_buff": mana_buff,
            "crit_rate": crit_rate,
            "crit_dmg": crit_dmg + MagicGauntlet,
        }
        basic_one = atk * params["base_attack_mult"]
        skill1_one = atk * params["skill1_mult"]
        skill2_one = atk * params["skill2_mult"]
        skill3_one = atk * params["skill3_mult"]
        ult_one = atk * params["ult_mult"]
        basic, skill1, skill2, skill3, ult = mean_total_damage_common(params)
        basic *= BasicAttackBuff1
        ans = basic + skill1 + skill2 + skill3 + ult
        mult_parts = _mparts(
            basic=_mp([1.0], []),
            skill1=_mp([50, 25], ["MagicBuff1", "MagicBuff2"]),
            skill2=_mp([60, 25], ["MagicBuff1", "MagicBuff2"]),
            skill3=_mp([0], []),
            ult=_mp([180, 75], ["MagicBuff1", "MagicBuff2", "UltBuff1"]),
        )
    elif character_id == "13004":  # スーパー重力弾
        params = {
            "ticks": ticks,
            "trials": trials,
            "seed": seed,
            "attack_power": atk,
            "attack_speed": speed,
            "base_attack_mult": 1.5,
            "skill1_rate": 7 + RateBuff1,
            "skill1_mult": 50*MagicBuff1,
            "skill2_rate": 11 + RateBuff1,
            "skill2_mult": 40*MagicBuff1,
            "skill3_rate": 0,
            "skill3_mult": 0,
            "ult_mana": ult_mana,
            "ult_mult": 90*(MagicBuff1+UltBuff1),
            "attack_mana_recov": 1,
            "mana_buff": mana_buff,
            "crit_rate": crit_rate,
            "crit_dmg": crit_dmg + MagicGauntlet,
        }
        basic_one = atk * params["base_attack_mult"]
        skill1_one = atk * params["skill1_mult"]
        skill2_one = atk * params["skill2_mult"]
        skill3_one = atk * params["skill3_mult"]
        ult_one = atk * params["ult_mult"]
        basic, skill1, skill2, skill3, ult = mean_total_damage_common(params)
        basic *= BasicAttackBuff1
        ans = basic + skill1 + skill2 + skill3 + ult
        mult_parts = _mparts(
            basic=_mp([1.5], []),
            skill1=_mp([50], ["MagicBuff1"]),
            skill2=_mp([40], ["MagicBuff1"]),
            skill3=_mp([0], []),
            ult=_mp([90], ["MagicBuff1", "UltBuff1"]),
        )
    elif character_id == "13007":  # 鬼神忍者
        params = {
            "tick": ticks,
            "trials": trials,
            "seed": seed,
            "base_attack_mult": 1,
            "skill1_stack": 10,
            "skill1_mult": 200*PhysicBuff1,
            "skill2_rate": 10+RateBuff1 if 6 <= char_lv else 0,
            "react_rate": 50,
            "skill2_mult": 40*PhysicBuff1,
            "attack_speed": speed,
            "attack_power": atk,
            "crit_rate": crit_rate if char_lv < 12 else crit_rate + 15,
            "crit_dmg": crit_dmg,
            "ult_mult": 425*(PhysicBuff1+UltBuff1),
            "ult_mana": ult_mana*CooltimeBuff1,
            "mana_buff": 1,
        }
        basic_one = atk * params["base_attack_mult"]
        skill1_one = atk * params["skill1_mult"]
        skill2_one = atk * params["skill2_mult"]
        skill3_one = 0
        ult_one = atk * params["ult_mult"]
        basic, skill1, skill2, skill3, ult = mean_total_damage_13007(params)
        basic *= BasicAttackBuff1
        ans = basic + skill1 + skill2 + skill3 + ult
        mult_parts = _mparts(
            basic=_mp([1], []),
            skill1=_mp([200], ["PhysicBuff1"]),
            skill2=_mp([40], ["PhysicBuff1"]),
            ult=_mp([350], ["PhysicBuff1", "UltBuff1"]),
        )
    elif character_id == "14002":  # ドクターパルス
        skill1_rate = 10 + RateBuff1
        skill1_mult = 70*MagicBuff1
        ult_mana = 550*UltManaBuff1
        ult_mult = 120*(MagicBuff1+UltBuff1)
        crit_dmg = crit_dmg + MagicGauntlet
        basic_one = atk
        skill1_one = atk * skill1_mult
        ult_one = atk * ult_mult
        basic, skill1, skill2, skill3, ult = mean_total_damage_14002(
            ticks=ticks,
            trials=trials,
            seed=seed,
            robots=robots,
            attack_speed=speed,
            attack_power=atk,
            skill1_rate=skill1_rate,
            skill1_mult=skill1_mult,
            ult_mana=ult_mana,
            ult_mult=ult_mult,
            mana_buff=mana_buff,
            crit_rate=crit_rate,
            crit_dmg=crit_dmg,
        )
        basic *= BasicAttackBuff1
        ans = basic + skill1 + skill2 + skill3 + ult
        if 12 <= char_lv:
            mult = (1 + 0.15*robots)
            basic *= mult
            skill1 *= mult
            skill2 *= mult
            skill3 *= mult
            ult *= mult
            ans = basic + skill1 + skill2 + skill3 + ult
        mult_parts = _mparts(
            basic=_mp([1], []),
            skill1=_mp([70], ["MagicBuff1"]),
            ult=_mp([120], ["MagicBuff1", "UltBuff1"]),
        )
    elif character_id == "15001":  # 原始バンバ
        params = {
            "tick": ticks,
            "trials": trials,
            "seed": seed,
            "base_attack_mult": 7.5,
            "skill1_rate": 10+RateBuff1,
            "skill1_mult": 200*PhysicBuff1,
            "skill2_mult": 80*PhysicBuff1,
            "attack_speed": speed,
            "attack_power": atk,
            "crit_rate": crit_rate,
            "crit_dmg": crit_dmg,
            "ult_mana": ult_mana*CooltimeBuff1 if 6 <= char_lv else 10**100,
            "ult_time": 10 if char_lv < 12 else 20,
        }
        basic_one = atk * params["base_attack_mult"]
        skill1_one = atk * params["skill1_mult"]
        skill2_one = atk * params["skill2_mult"]
        skill3_one = 0
        ult_one = 0
        basic, skill1, skill2, skill3, ult = mean_total_damage_15001(params)
        basic *= BasicAttackBuff1
        ans = basic + skill1 + skill2 + skill3 + ult
        mult_parts = _mparts(
            basic=_mp([7.5], []),
            skill1=_mp([200], ["PhysicBuff1"]),
            skill2=_mp([80], ["PhysicBuff1"]),
        )
    elif character_id == "15002":  # 女王コルディ
        params = {
            "base_attack_mult": 1,
            "skill1_rate": 8+RateBuff1,
            "skill2_rate": 8+RateBuff1,
            "skill1_mult": 25*MagicBuff1,
            "skill1_count": icecount_,
            "skill2_mult": 100*MagicBuff1,
            "skill2_dot": 30*MagicBuff1,
            "skill3_mult": 60*MagicBuff1 if char_lv < 12 else 120*MagicBuff1,
            "attack_speed": speed,
            "attack_power": atk,
            "crit_rate": crit_rate,
            "crit_dmg": crit_dmg+MagicGauntlet,
            "ult_mana": ult_mana*UltManaBuff1,
            "ult_mult": 35*UltBuff1*MagicBuff1,
            "ult_time": 10 if char_lv < 6 else 15,
            "mana_buff": mana_buff, 
            "attack_mana_recov": 1, 
        }
        basic_one = atk * params["base_attack_mult"]
        skill1_one = atk * params["skill1_mult"]
        skill2_one = atk * params["skill2_mult"]
        skill3_one = atk * params["skill3_mult"]
        ult_one = atk * params["ult_mult"]
        basic, skill1, skill2, skill3, ult = mean_total_damage_15002(params, ticks, trials, seed)
        basic *= BasicAttackBuff1
        ans = basic + skill1 + skill2 + skill3 + ult
        mult_parts = _mparts(
            basic=_mp([1], []),
            skill1=_mp([25], ["MagicBuff1"]),
            skill2=_mp([100], ["MagicBuff1"]),
            skill3=_mp([60, 120], ["MagicBuff1"]),
            ult=_mp([35], ["UltBuff1", "MagicBuff1"]),
        )
    elif character_id == "15005":  # ブロッブ団
        # 多分まちがい
        #PassiveBuff = BlobLvSum / 10 if char_lv < 6 else max((BlobLvSum - 3) / 10, 0) 
        PassiveBuff = 1 + 0.25*BlobLvSum if 12 <= char_lv else 1 + 0.10*BlobLvSum
        DebugMessage["BlobLvSum"] = BlobLvSum
        params = {
            "ticks": ticks,
            "trials": trials,
            "seed": seed,
            "attack_power": atk,
            "attack_speed": speed,
            "base_attack_mult": 1.0,
            "skill1_rate": 5 + RateBuff1,
            "skill1_mult": 30*PhysicBuff1,
            "skill2_rate": 5 + RateBuff1,
            "skill2_mult": 40*(1 + redBlob / 10)*MagicBuff1,
            "skill3_rate": 5 + RateBuff1,
            "skill3_mult": 40.6*PhysicBuff1,
            "ult_mana": ult_mana*UltManaBuff1,
            "ult_mult": 110*(1 + 0.10*BlobLvSum)*(MagicBuff1+UltBuff1),
            "attack_mana_recov": 1,
            "mana_buff": mana_buff,
            "crit_rate": crit_rate,
            "crit_dmg": crit_dmg,
        }
        basic_one = atk * params["base_attack_mult"]
        skill1_one = atk * params["skill1_mult"]
        skill2_one = atk * params["skill2_mult"]
        skill3_one = atk * params["skill3_mult"]
        ult_one = atk * params["ult_mult"]
        basic, skill1, skill2, skill3, ult = mean_total_damage_common(params)
        basic *= BasicAttackBuff1
        skill1 *= def_mult
        skill3 *= def_mult
        ans = basic + skill1 + skill2 + skill3 + ult
        ans *= PassiveBuff
        mult_parts = _mparts(
            basic=_mp([1.0], []),
            skill1=_mp([30], ["PhysicBuff1"]),
            skill2=_mp([40, 1, 10], ["redBlob", "MagicBuff1"]),
            skill3=_mp([40.6], ["PhysicBuff1"]),
            ult=_mp([110, 1, 0.10], ["BlobLvSum", "MagicBuff1", "UltBuff1"]),
        )
    elif character_id == "15004":  # アイアムニャン
        skill1_rate = 11 + RateBuff1 if 12 <= char_lv else 7 + RateBuff1
        skill2_rate = 11 + RateBuff1 if 12 <= char_lv else 7 + RateBuff1
        skill1_mult = 180*MagicBuff1
        skill2_mult = 200*MagicBuff1
        ult_mana = 300*UltManaBuff1
        ult_mult = 1000*(MagicBuff1+UltBuff1) if char_lv < 6 else 1500*(MagicBuff1+UltBuff1)
        ult_cooldown = int(speed*3) if char_lv < 6 else int(speed*4.5)
        crit_dmg = crit_dmg + MagicGauntlet
        basic_one = atk
        skill1_one = atk * skill1_mult
        skill2_one = atk * skill2_mult
        ult_one = atk * ult_mult
        basic, skill1, skill2, skill3, ult = mean_total_damage_15004(
            ticks=ticks,
            trials=trials,
            seed=seed,
            attack_power=atk,
            attack_speed=speed,
            skill1_rate=skill1_rate,
            skill2_rate=skill2_rate,
            skill1_mult=skill1_mult,
            skill2_mult=skill2_mult,
            ult_mult=ult_mult,
            ult_mana=ult_mana,
            ult_cooldown=ult_cooldown,
            mana_buff=mana_buff,
            crit_rate=crit_rate,
            crit_dmg=crit_dmg,
        )
        basic *= BasicAttackBuff1
        ans = basic + skill1 + skill2 + skill3 + ult
        mult = (1 + mana_buff//0.5 * 0.05) # アイアムニャンパッシブ
        basic *= mult
        skill1 *= mult
        skill2 *= mult
        skill3 *= mult
        ult *= mult
        ans = basic + skill1 + skill2 + skill3 + ult
        mult_parts = _mparts(
            basic=_mp([1], []),
            skill1=_mp([180], ["MagicBuff1"]),
            skill2=_mp([200], ["MagicBuff1"]),
            ult=_mp([1000, 1500], ["MagicBuff1", "UltBuff1"]),
        )
    elif character_id == "15006":  # 魔王ドラゴン
        params = {
            "tick": ticks,
            "n_iter": trials,
            "base_attack_mult": 1.0,
            "skill1_rate": 8 + RateBuff1,
            "skill2_rate": 11 + RateBuff1,
            "attack_speed": speed,
            "attack_power": atk,
            "skill1_mult": 350*MagicBuff1,
            "skill2_mult": 320*MagicBuff1,
            "skill3_mult": 25*MagicBuff1,
            "ult_mult": 550*(MagicBuff1+UltBuff1) if char_lv < 12 else 650*(MagicBuff1+UltBuff1),
            "ult_mana": ult_mana,
            "attack_mana_recov": 1.0,
            "mana_buff": mana_buff,
            "crit_rate": crit_rate,
            "crit_dmg": crit_dmg + MagicGauntlet,
            "seed": seed
        }
        basic_one = atk * params["base_attack_mult"]
        skill1_one = atk * params["skill1_mult"]
        skill2_one = atk * params["skill2_mult"]
        skill3_one = atk * params["skill3_mult"]
        ult_one = atk * params["ult_mult"]
        basic, skill1, skill2, skill3, ult = mean_total_damage_15006(params)
        basic *= BasicAttackBuff1
        ans = basic + skill1 + skill2 + skill3 + ult
        mult_parts = _mparts(
            basic=_mp([1.0], []),
            skill1=_mp([350], ["MagicBuff1"]),
            skill2=_mp([320], ["MagicBuff1"]),
            skill3=_mp([25], ["MagicBuff1"]),
            ult=_mp([550, 650], ["MagicBuff1", "UltBuff1"]),
        )
    elif character_id == "15008":  # グランドママ
        ans = mean_total_damage_15021(
            ticks=int(speed * duration_sec * TICK_COEFF),
            trials=int(common.get("trials", 1)),
            seed=seed,
            attack_power=atk,
            attack_speed=speed,
            mana_buff=mana_buff,
        )
        ans = 65000
    elif character_id == "15009":  # カエルの死神
        params = {
            "ticks": ticks,
            "trials": trials,
            "seed": seed,
            "attack_power": atk,
            "attack_speed": speed,
            "base_attack_mult": 1.0,
            "skill1_rate": 8 + RateBuff1,
            "skill1_mult": 120*MagicBuff1,
            "skill2_rate": 12 + RateBuff1,
            "skill2_mult": 90*MagicBuff1,
            "skill3_rate": 0,
            "skill3_mult": 0,
            "ult_mana": 10**100,
            "ult_mult": 1 + UltBuff1,
            "attack_mana_recov": 1,
            "mana_buff": mana_buff,
            "crit_rate": crit_rate,
            "crit_dmg": crit_dmg + MagicGauntlet,
        }
        basic_one = atk * params["base_attack_mult"]
        skill1_one = atk * params["skill1_mult"]
        skill2_one = atk * params["skill2_mult"]
        skill3_one = atk * params["skill3_mult"]
        ult_one = atk * params["ult_mult"]
        basic, skill1, skill2, skill3, ult = mean_total_damage_common(params)
        basic *= BasicAttackBuff1
        ans = basic + skill1 + skill2 + skill3 + ult
        mult_parts = _mparts(
            basic=_mp([1.0], []),
            skill1=_mp([120], ["MagicBuff1"]),
            skill2=_mp([90], ["MagicBuff1"]),
            skill3=_mp([0], []),
            ult=_mp([1], ["UltBuff1"]),
        )
    elif character_id == "15010":  # エースバットマン
        ans = 0
    elif character_id == "15011":  # トップヴェイン
        params = {
            "tick": ticks,
            "trials": trials,
            "seed": seed,
            "attack_power": atk,
            "attack_speed": speed,
            "base_attack_mult": (20*PhysicBuff1 + 1*BasicAttackBuff1),
            "skill1_mult": 70*PhysicBuff1,
            "skill2_mult": 330*PhysicBuff1,
            "skill2_going": True if 6 <= char_lv else False,
            "ult_mana": ult_mana*CooltimeBuff1,
            "ult_buff": 2.5 if char_lv < 12 else 3.5,
            "crit_rate": crit_rate,
            "crit_dmg": crit_dmg,
        }
        basic_one = atk * params["base_attack_mult"]
        skill1_one = atk * params["skill1_mult"]
        skill2_one = atk * params["skill2_mult"]
        skill3_one = 0
        ult_one = 0
        basic, skill1, skill2, skill3, ult = mean_total_damage_15011(params)
        if 6 <= char_lv: # 破裂の矢の効果をどう処理するか
            coeff = 1 + enemy_def / 330
            skill2 *= coeff
        ans = basic + skill1 + skill2 + skill3 + ult
        mult_parts = _mparts(
            basic=_mp([20, 1], ["PhysicBuff1", "BasicAttackBuff1"]),
            skill1=_mp([70], ["PhysicBuff1"]),
            skill2=_mp([330], ["PhysicBuff1"]),
        )
    elif character_id == "15020":  # ノイズペンギンキング
        ans = mean_total_damage_15021(
            ticks=int(speed * duration_sec * TICK_COEFF),
            trials=int(common.get("trials", 1)),
            seed=seed,
            attack_power=atk,
            attack_speed=speed,
            mana_buff=mana_buff,
        )
        ans = 69000
    elif character_id == "15021":  # 覚醒ヘイリー
        skill1_rate = 10 + RateBuff1
        skill2_rate = 15 + RateBuff1 if 12 <= char_lv else 10 + RateBuff1
        skill1_mult = 180*MagicBuff1
        skill2_mult = 100*MagicBuff1
        skill3_mult = 1125*(MagicBuff1+UltBuff1)
        ult_mana = 250*UltManaBuff1
        crit_dmg = crit_dmg + MagicGauntlet
        basic_one = atk
        skill1_one = atk * skill1_mult
        skill2_one = atk * skill2_mult
        skill3_one = atk * skill3_mult
        ult_one = 0
        basic, skill1, skill2, skill3, ult = mean_total_damage_15021(
            ticks=ticks,
            trials=trials,
            seed=seed,
            skill1_rate=skill1_rate,
            skill2_rate=skill2_rate,
            attack_speed=speed,
            attack_power=atk,
            skill1_mult=skill1_mult,
            skill2_mult=skill2_mult,
            skill3_mult=skill3_mult,
            ult_mana=ult_mana,
            mana_buff=mana_buff,
            tick_seconds=1.0,
            crit_rate=crit_rate,
            crit_dmg=crit_dmg,
        )
        basic *= BasicAttackBuff1
        mult = (1 + mythCount*0.05) # 覚醒ヘイリーパッシブ
        basic *= mult
        skill1 *= mult
        skill2 *= mult
        skill3 *= mult
        ult *= mult
        ans = basic + skill1 + skill2 + skill3 + ult
        mult_parts = _mparts(
            basic=_mp([1], []),
            skill1=_mp([180], ["MagicBuff1"]),
            skill2=_mp([100], ["MagicBuff1"]),
            skill3=_mp([1125], ["MagicBuff1", "UltBuff1"]),
        )
    elif character_id == "15022":  # 時空アト
        ans = mean_total_damage_15021(
            ticks=int(speed * duration_sec * TICK_COEFF),
            trials=int(common.get("trials", 1)),
            seed=seed,
            attack_power=atk,
            attack_speed=speed,
            mana_buff=mana_buff,
        )
        ans = 70000
    elif character_id == "15023":  # キャプテンロカ
        params = {
            "ticks": ticks,
            "trials": trials,
            "seed": seed,
            "attack_power": atk,
            "attack_speed": speed,
            "skill1_rate": 9 + RateBuff1,
            "skill1_mult": 467.5*PhysicBuff1 if 12 <= char_lv else 330*PhysicBuff1,
            "skill2_mult": 40*PhysicBuff1,
            "skill3_mult": 150*PhysicBuff1,
            "ult_mult": 350*(PhysicBuff1+UltBuff1) if 6 <= char_lv else 233.333*(PhysicBuff1+UltBuff1),
            "ult_mana": ult_mana*CooltimeBuff1,
            "crit_rate": roka_crit_ + crit_rate,
            "crit_dmg": crit_dmg,
        }
        basic_one = atk
        skill1_one = atk * params["skill1_mult"]
        skill2_one = atk * params["skill2_mult"]
        skill3_one = atk * params["skill3_mult"]
        ult_one = atk * params["ult_mult"]
        basic, skill1, skill2, skill3, ult = mean_total_damage_15023(params)
        basic *= BasicAttackBuff1
        ans = basic + skill1 + skill2 + skill3 + ult
        mult_parts = _mparts(
            basic=_mp([1], []),
            skill1=_mp([467.5, 330], ["PhysicBuff1"]),
            skill2=_mp([40], ["PhysicBuff1"]),
            skill3=_mp([150], ["PhysicBuff1"]),
            ult=_mp([350, 233.333], ["PhysicBuff1", "UltBuff1"]),
        )
    elif character_id == "15024":  # ボス選鳥師
        params = {
            "attack_power": atk,
            "attack_speed": speed,
            "skill1_rate": 11 + RateBuff1,
            "skill2_rate": 10 + RateBuff1,
            "skill1_mult": 330*MagicBuff1,
            "skill2_mult": 160*MagicBuff1,
            "skill3_mult": 5*MagicBuff1 + 5 if 6 <= char_lv else 5*MagicBuff1,
            "mana_buff": mana_buff,
            "ult_mana": 250*UltManaBuff1,
            "ult_mult": 300*(MagicBuff1+UltBuff1),
            "crit_dmg": crit_dmg + MagicGauntlet,
            "crit_rate": crit_rate,
            "ult_buff": 5 if char_lv < 12 else 10
        }
        basic_one = atk
        skill1_one = atk * params["skill1_mult"]
        skill2_one = atk * params["skill2_mult"]
        skill3_one = atk * params["skill3_mult"]
        ult_one = atk * params["ult_mult"]
        basic, skill1, skill2, skill3, ult = mean_total_damage_15024(
            params_dict=params, num_ticks=ticks, trials=trials, seed=seed
        )
        basic *= BasicAttackBuff1
        ans = basic + skill1 + skill2 + skill3 + ult
        mult_parts = _mparts(
            basic=_mp([1], []),
            skill1=_mp([330], ["MagicBuff1"]),
            skill2=_mp([160], ["MagicBuff1"]),
            skill3=_mp([5, 5], ["MagicBuff1"]),
            ult=_mp([300], ["MagicBuff1", "UltBuff1"]),
        )
    elif character_id == "15109":  # 死神ダイアン
        params = {
            "ticks": ticks,
            "trials": trials,
            "seed": seed,
            "attack_power": atk,
            "attack_speed": speed,
            "base_attack_mult": 20.0,
            "skill1_rate": 8 + RateBuff1 if char_lv < 6 else 13 + RateBuff1,
            "skill1_mult": 350*MagicBuff1,
            "skill2_rate": 0,
            "skill2_mult": 0,
            "skill3_rate": 0,
            "skill3_mult": 0,
            "ult_mana": ult_mana*UltManaBuff1,
            "ult_mult": 1200*(MagicBuff1+UltBuff1),
            "attack_mana_recov": 1,
            "mana_buff": mana_buff,
            "crit_rate": crit_rate,
            "crit_dmg": crit_dmg + MagicGauntlet,
        }
        basic_one = atk * params["base_attack_mult"]
        skill1_one = atk * params["skill1_mult"]
        skill2_one = atk * params["skill2_mult"]
        skill3_one = atk * params["skill3_mult"]
        ult_one = atk * params["ult_mult"]
        basic, skill1, skill2, skill3, ult = mean_total_damage_common(params)
        basic *= BasicAttackBuff1
        ans = basic + skill1 + skill2 + skill3 + ult
        mult_parts = _mparts(
            basic=_mp([20.0], []),
            skill1=_mp([350], ["MagicBuff1"]),
            skill2=_mp([0], []),
            skill3=_mp([0], []),
            ult=_mp([1200], ["MagicBuff1", "UltBuff1"]),
        )
    elif character_id == "15110":  # バットマン投手
        strikeout = int(strikeout*100)
        skill1_react1 = min(strikeout - 100, 100) if strikeout < 200 else 100
        skill1_react2 = max(strikeout - 200, 0) if strikeout < 300 else 100
        DebugMessage["skill1_react1"] = skill1_react1
        DebugMessage["skill1_react2"] = skill1_react2
        params = {
            "attack_power": atk,
            "attack_speed": speed,
            "base_attack_mult": 1.0,
            "skill1_rate": 10 + RateBuff1,
            "skill1_mult": 160*PhysicBuff1,
            "skill1_react1": skill1_react1,
            "skill1_react2": skill1_react2,
            "ult_mana": ult_mana*CooltimeBuff1 if 6 <= char_lv else 10**100,
            "ult_mult": 400*(PhysicBuff1+UltBuff1),
            "add_rate": 10 if char_lv < 12 else 20,
            "add_mult": 100*PhysicBuff1,
            "crit_rate": crit_rate,
            "crit_dmg": crit_dmg,
        }
        basic_one = atk * params["base_attack_mult"]
        skill1_one = atk * params["skill1_mult"]
        skill2_one = 0
        skill3_one = 0
        ult_one = atk * params["ult_mult"]
        basic, skill1, skill2, skill3, ult = mean_total_damage_15110(params, ticks=ticks, n_trials=trials, seed=seed)
        basic *= BasicAttackBuff1
        ans = basic + skill1 + skill2 + skill3 + ult
        mult_parts = _mparts(
            basic=_mp([1.0], []),
            skill1=_mp([160], ["PhysicBuff1"]),
            ult=_mp([400], ["PhysicBuff1", "UltBuff1"]),
        )
    elif character_id == "15210":  # バットマン打者
        # この式（乗算でさらに複利で働く式）は間違い
        #if char_lv < 12: 
            #ult_mult = sum([120*(1.5**i) for i in range(ace_batman_attack_ult_ticks[batEnhance_])])*PhysicBuff1
        #else:
            #ult_mult = sum([120*(1.5**i) for i in range(ace_batman_attack_ult_ticks[batEnhance_])])*(PhysicBuff1 + 0.5)
        # 実際は単に加算されているだけ
        if char_lv < 12: 
            ult_mult = sum([120*(PhysicBuff1 + UltBuff1 + 0.5*i) for i in range(ace_batman_attack_ult_ticks[batEnhance_])])
        else:
            ult_mult = sum([120*(PhysicBuff1 + UltBuff1 + 1.0*i) for i in range(ace_batman_attack_ult_ticks[batEnhance_])])
        params = {
            "ticks": ticks,
            "attack_power": atk,
            "attack_speed": speed,
            "base_attack_mult": 1.0,
            "skill1_mult": 250*PhysicBuff1,
            "ult_mana": ult_mana*CooltimeBuff1 if 6 <= char_lv else 10**100,
            "ult_mult": ult_mult,
            "ult_ticks": ace_batman_attack_ult_ticks[batEnhance_],
            "crit_rate": crit_rate,
            "crit_dmg": crit_dmg,
        }
        basic_one = atk * params["base_attack_mult"]
        skill1_one = atk * params["skill1_mult"]
        skill2_one = 0
        skill3_one = 0
        ult_one = atk * params["ult_mult"]
        basic, skill1, skill2, skill3, ult = mean_total_damage_15210(params, n_iter=trials, seed=seed)
        basic *= BasicAttackBuff1
        ans = basic + skill1 + skill2 + skill3 + ult
        mult_parts = _mparts(
            basic=_mp([1.0], []),
            skill1=_mp([250], ["PhysicBuff1"]),
            ult=_mp([120, 0.5, 1.0], ["PhysicBuff1", "UltBuff1"]),
        )
    else:
        ans = 0

    isPhisics = int(character_id) in PHISICS_CHAR
    if isPhisics:
        ans *= def_mult
        if character_id == "15001":
            ans = def_mult*(basic + skill1 + skill2) + def_mult_prim_bamba * ult
    DebugMessage.update(
        _build_member_debug_tail(
            base_atk=base_atk,
            atk=atk,
            ticks=ticks,
            base_speed=base_speed,
            speed=speed,
            ult_mana=ult_mana,
            t_buff1=t_buff1,
            t_buff2=t_buff2,
            t_buff3=t_buff3,
            is_phisics=isPhisics,
            strongest_creature=StrongestCreature,
            basic_one=basic_one,
            skill1_one=skill1_one,
            skill2_one=skill2_one,
            skill3_one=skill3_one,
            ult_one=ult_one,
            mult_parts=mult_parts,
        )
    )
    dps_ratio = {"basic": basic, "skill1": skill1, "skill2": skill2, "skill3": skill3, "ult": ult}
    return (
        (ans / TICK_COEFF) * float(common.get("multiplier", 1)) * BossBuff1 * StunBuff1 * PartyCat,
        dps_ratio,
        DebugMessage,
    )

@app.post("/api/calc")
def api_calc():
    data = request.get_json(force=True, silent=False)
    if not isinstance(data, dict):
        return _json_error("invalid json", 400)
    _maybe_clear_member_dps_cache()

    common = data.get("options", {})
    party = data.get("party", [])
    if not isinstance(common, dict) or not isinstance(party, list) or len(party) == 0:
        return _json_error("options/party invalid", 400)

    enemy_row = _resolve_enemy_row(common)
    enemy_mode = str(enemy_row.get("mode", ""))
    enemy_wave = _parse_enemy_wave(enemy_row.get("wave", 0))
    enemy_group = str(enemy_row.get("group", ""))
    enemy_def = clamp_float(enemy_row.get("enemy_def", _default_enemy_def()), -10_000_000, 10_000_000, _default_enemy_def())
    duration_sec = clamp_float(common.get("durationSec", 60), 60, 24 * 3600, 60)
    all_relic_lv = clamp_int(common.get("allRelicLv", common.get("relicLv", 1)), 1, 11, 1)
    mythEnhanceLv = clamp_int(common.get("mythEnhanceLv", 0), 1, 35, 1)
    trials = clamp_int(common.get("trials", 3), 1, 100, 3)
    seed = clamp_int(common.get("seed", 1), 0, 2_147_483_647, 1)
    atk_buff_pct = clamp_float(common.get("atkBuffPct", 0), -1000, 10000, 0)
    speed_buff_pct = clamp_float(common.get("speedBuffPct", 0), -1000, 10000, 0)
    multiplier = clamp_float(common.get("multiplier", 1), -2_147_483_648, 2_147_483_647, 1)
    f32lock = "enable" if str(common.get("f32lock", "disable")).strip().lower() == "enable" else "disable"
    mana_regen_buff_pct = clamp_int(common.get("manaRegenBuffPct", 0), 0, 700, 0)
    def_down = clamp_float(common.get("defDown", 190), -10_000_000, 10_000_000, 190)
    coins = clamp_int(common.get("coins", 300000), 0, 2_000_000_000, 300000)
    guildBlessing = clamp_int(common.get("guildBlessing", 0), 0, 2, 0)
    unitLevelSumBuff = clamp_float(common.get("unitLevelSumBuff", 0), 0, 25, 0)

    blob_figures = _normalize_blob_figures(common.get("blobFigures", []))

    pets = _normalize_pets(common)
    pet1, pet2, pet3 = _to_pet_slots(pets)
    pet = pet1  # backward compatible alias

    tick_sec = 1.0
    ticks = int(duration_sec / tick_sec)

    def clamp_relic_lv(key: str) -> int:
        return clamp_int(common.get(key, all_relic_lv), 1, 11, all_relic_lv)

    money_gun_lv = clamp_relic_lv("moneyGunLv")
    power_potion_lv = clamp_relic_lv("powerPotionLv")
    fairy_bow_lv = clamp_relic_lv("fairyBowLv")
    great_sword_lv = clamp_relic_lv("greatSwordLv")
    secret_book_lv = clamp_relic_lv("secretBookLv")
    bambaDoll = clamp_relic_lv("bambaDollLv")
    bat_lv = clamp_relic_lv("batLv")
    wizard_hat_lv = clamp_relic_lv("wizardHatLv")
    bomb_lv = clamp_relic_lv("bombLv")
    old_book_lv = clamp_relic_lv("oldBookLv")
    sage_yogurt_lv = clamp_relic_lv("sageYogurtLv")
    magic_gauntlet_lv = clamp_relic_lv("magicGauntletLv")

    common_s = {
        "enemyMode": enemy_mode,
        "enemyWave": enemy_wave,
        "enemyGroup": enemy_group,
        "enemyDef": enemy_def,
        "durationSec": duration_sec,
        "tickSec": tick_sec,
        "trials": trials,
        "seed": seed,
        "f32lock": f32lock,
        "multiplier": multiplier,
        "allRelicLv": all_relic_lv,
        "mythEnhanceLv": mythEnhanceLv,
        "atkBuffPct": atk_buff_pct,
        "manaRegenBuffPct": mana_regen_buff_pct,
        "speedBuffPct": speed_buff_pct,
        "defDown": def_down,
        "coins": coins,
        "moneyGunLv": money_gun_lv,
        "powerPotionLv": power_potion_lv,
        "fairyBowLv": fairy_bow_lv,
        "greatSwordLv": great_sword_lv,
        "secretBookLv": secret_book_lv,
        "bambaDollLv": bambaDoll,
        "batLv": bat_lv,
        "wizardHatLv": wizard_hat_lv,
        "bombLv": bomb_lv,
        "oldBookLv": old_book_lv,
        "sageYogurtLv": sage_yogurt_lv,
        "magicGauntletLv": magic_gauntlet_lv,
        "guildBlessing": guildBlessing,
        "unitLevelSumBuff": unitLevelSumBuff,
        "blobFigures": blob_figures,
        "pet1": pet1,
        "pet2": pet2,
        "pet3": pet3,
        "pet": pet,
    }

    members_out: List[Dict[str, Any]] = []
    dps_list: List[float] = []
    dps_ratio_list = []
    DebugMessages = dict()
    char_ids: List[str] = []
    use_member_cache = (seed == 1)

    for m in party:
        if not isinstance(m, dict):
            return _json_error("party must be list of objects", 400)

        cid = str(m.get("character", ""))
        if cid not in CHAR_DB:
            return _json_error(f"unknown character: {cid}", 400)

        char_lv = clamp_int(m.get("charLv", 1), 1, 15, 1)
        treasure_lv = clamp_int(m.get("treasureLv", 0), 0, 15, 0)

        rune_name = str(m.get("runeName", "なし") or "なし")
        rune_rarity = str(m.get("runeRarity", "なし") or "なし")

        member_s: Dict[str, Any] = {
            "character": cid,
            "charLv": char_lv,
            "treasureLv": treasure_lv,
            "runeName": rune_name,
            "runeRarity": rune_rarity,
        }
# === Extra per-character parameters (UI dropdowns) ===
        cname = str(CHAR_DB.get(cid, {}).get("name", ""))
        member_s["mythCount"] = clamp_int(m.get("mythCount", 0), 0, 30, 0)
        v = clamp_float(m.get("intake", 0), 0, 1_000_000, 0)
        member_s["intake"] = v
        member_s["blobintake"] = v
        member_s["uchiCells"] = clamp_float(m.get("uchiCells", 1.0), 1.0, 5.0, 1.0)
        member_s["batEnhance_"] = clamp_int(m.get("batEnhance_", 0), 0, 20, 0)
        member_s["batEnhance"] = clamp_int(m.get("batEnhance", 0), 0, 20, 0)
        member_s["strikeout"] = clamp_float(m.get("strikeout", 1.0), 1.0, 3.0, 1.0)
        member_s["starPower"] = clamp_int(m.get("starPower", 0), 0, 10, 0)
        member_s["emotionControl"] = clamp_int(m.get("emotionControl", 0), 0, 99, 0)
        member_s["sparkBonusDmg"] = clamp_float(m.get("sparkBonusDmg", 0.0), 0.0, 3.0, 0.0)
        ec = clamp_int(m.get("energyCount", 0), 0, 2_000_000_000, 0)
        member_s["energyCount"] = ec
        member_s["techEnhance"] = clamp_int(m.get("techEnhance", 0), 0, 10, 0)
        member_s["score"] = clamp_int(m.get("score", 0), 0, 100, 0)
        cc = clamp_int(m.get("cannibalCount", 0), 0, 2_000_000_000, 0)
        member_s["cannibalCount"] = cc
        member_s["training"] = clamp_int(m.get("training", 0), 0, 30, 0)
        member_s["StrongestCreature"] = clamp_int(m.get("StrongestCreature", 0), 0, 1000, 0)
        member_s["robots"] = clamp_int(m.get("robots", 0), 0, 4, 0)
        member_s["roka_crit_"] = clamp_int(m.get("roka_crit_", 0), 0, 30, 0)
        member_s["roka_crit"] = clamp_int(m.get("roka_crit", 0), 0, 30, 0)
        member_s["blueBlob"] = clamp_int(m.get("blueBlob", 0), 0, 20, 0)
        member_s["redBlob"] = clamp_int(m.get("redBlob", 0), 0, 20, 0)
        member_s["greenBlob"] = clamp_int(m.get("greenBlob", 0), 0, 20, 0)
        member_s["icecount"] = clamp_int(m.get("icecount", 0), 10, 10**100, 0)
        member_s["icerate"] = clamp_int(m.get("icerate", 0), 0, 100, 0)
        member_s["icecount_"] = clamp_int(m.get("icecount_", 6), 1, 15, 1)
        common_m = dict(common_s)

        if use_member_cache:
            cache_key = _member_dps_cache_key(cid, common_m, member_s)
            cached = _member_dps_cache_get(cache_key)
            if cached is None:
                dps, dps_ratio, debug_message = compute_member_dps(cid, common_m, member_s)
                _member_dps_cache_put(cache_key, (dps, dps_ratio, debug_message))
            else:
                dps, dps_ratio, debug_message = cached
        else:
            dps, dps_ratio, debug_message = compute_member_dps(cid, common_m, member_s)

        dps_list.append(dps)
        dps_ratio_list.append(dps_ratio)
        DebugMessages[cname or cid] = debug_message

        members_out.append(
            {
                "character": cid,
                "charLv": char_lv,
                "treasureLv": treasure_lv,
                "runeName": member_s.get("runeName"),
                "runeRarity": member_s.get("runeRarity"),
                "intake": member_s.get("intake"),
                "mythCount": member_s.get("mythCount"),
                "uchiCells": member_s.get("uchiCells"),
                "batEnhance": member_s.get("batEnhance"),
                "batEnhance_": member_s.get("batEnhance_"),
                "strikeout": member_s.get("strikeout"),
                "starPower": member_s.get("starPower"),
                "emotionControl": member_s.get("emotionControl"),
                "sparkBonusDmg": member_s.get("sparkBonusDmg"),
                "energyCount": member_s.get("energyCount"),
                "techEnhance": member_s.get("techEnhance"),
                "score": member_s.get("score"),
                "cannibalCount": member_s.get("cannibalCount"),
                "training": member_s.get("training"),
                "StrongestCreature": member_s.get("StrongestCreature"),
                "robots": member_s.get("robots"),
                "roka_crit_": member_s.get("roka_crit_"),
                "roka_crit": member_s.get("roka_crit"),
                "dps": dps,
                "dpsRatio": dps_ratio,
            }
        )

    total = sum(dps_list)

    if total > 0:
        for i in range(len(members_out)):
            members_out[i]["share"] = dps_list[i] / total
    else:
        eq = 1.0 / len(members_out)
        for i in range(len(members_out)):
            members_out[i]["share"] = eq

    cache_info = _member_dps_cache_info()

    return jsonify(
        {
            "meta": {"ticks": ticks, "trials": trials, "memberCache": cache_info},  # フロント表示はしないが、残してOK
            "totalDps": total,
            "dpsRatio": dps_ratio_list,
            "members": members_out,
            "pet1": pet1,
            "pet2": pet2,
            "pet3": pet3,
            "pet": pet,
            "Debug": DebugMessages,
        }
    )

def _survey_env(name: str, default: str = "") -> str:
    try:
        return str(os.environ.get(name, default) or default).strip()
    except Exception:
        return default

def _survey_enabled() -> bool:
    # Enable only when Spreadsheet ID is present.
    return bool(_survey_env("SURVEY_SHEETS_SPREADSHEET_ID"))

def _client_ip() -> str:
    # Behind Caddy/reverse-proxy, the original IP is typically in X-Forwarded-For.
    xff = request.headers.get("X-Forwarded-For", "")
    if xff:
        # take the left-most (original client)
        ip = xff.split(",")[0].strip()
        if ip:
            return ip
    xri = request.headers.get("X-Real-IP", "").strip()
    if xri:
        return xri
    return (request.remote_addr or "").strip()

def _hash_ip(ip: str) -> str:
    # Store hashed IP only (optional). Avoid storing raw IP in Sheets.
    salt = _survey_env("SURVEY_IP_SALT")
    ip = (ip or "").strip()
    if not ip or not salt:
        return ""
    h = hashlib.sha256((salt + "|" + ip).encode("utf-8")).hexdigest()
    return h

@lru_cache(maxsize=1)
def _sheets_service():
    # Lazy import so the app can still run without survey deps installed.
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
    except Exception as e:  # pragma: no cover
        raise RuntimeError("google sheets dependencies are not installed") from e

    cred_path = _survey_env("GOOGLE_APPLICATION_CREDENTIALS")
    if not cred_path:
        raise RuntimeError("GOOGLE_APPLICATION_CREDENTIALS is not set")
    if not os.path.exists(cred_path):
        raise RuntimeError(f"credentials file not found: {cred_path}")

    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = service_account.Credentials.from_service_account_file(cred_path, scopes=scopes)
    # cache_discovery=False to avoid writing discovery cache files in containers.
    return build("sheets", "v4", credentials=creds, cache_discovery=False)

def _append_survey_row(row: List[Any]) -> None:
    try:
        from googleapiclient.errors import HttpError
    except Exception:
        HttpError = Exception  # type: ignore

    spreadsheet_id = _survey_env("SURVEY_SHEETS_SPREADSHEET_ID")
    range_a1 = _survey_env("SURVEY_SHEETS_RANGE", "responses!A:Z")
    if not spreadsheet_id:
        raise RuntimeError("SURVEY_SHEETS_SPREADSHEET_ID is not set")

    svc = _sheets_service()
    body = {"values": [row]}
    try:
        (
            svc.spreadsheets()
            .values()
            .append(
                spreadsheetId=spreadsheet_id,
                range=range_a1,
                valueInputOption="RAW",
                insertDataOption="INSERT_ROWS",
                body=body,
            )
            .execute()
        )
    except HttpError as e:  # pragma: no cover
        # Bubble up but keep original message for logging.
        raise RuntimeError(f"sheets append failed: {e}") from e

def _read_survey_rows() -> List[List[Any]]:
    try:
        from googleapiclient.errors import HttpError
    except Exception:
        HttpError = Exception  # type: ignore

    spreadsheet_id = _survey_env("SURVEY_SHEETS_SPREADSHEET_ID")
    range_a1 = _survey_env("SURVEY_SHEETS_RANGE", "responses!A:Z")
    if not spreadsheet_id:
        raise RuntimeError("SURVEY_SHEETS_SPREADSHEET_ID is not set")

    svc = _sheets_service()
    try:
        result = (
            svc.spreadsheets()
            .values()
            .get(spreadsheetId=spreadsheet_id, range=range_a1)
            .execute()
        )
    except HttpError as e:  # pragma: no cover
        raise RuntimeError(f"sheets read failed: {e}") from e
    values = result.get("values", [])
    if not isinstance(values, list):
        return []
    return values

@app.get("/api/survey")
def api_survey_list():
    if not _survey_enabled():
        return _json_error("survey is not configured", 503)

    limit = clamp_int(request.args.get("limit"), 1, 100, 30)
    page_filter = str(request.args.get("page", "") or "").strip()

    try:
        rows = _read_survey_rows()
    except Exception as e:
        print(f"[survey] read failed: {e}")
        return _json_error("failed to load survey", 503)

    items = []
    for row in rows:
        if not isinstance(row, list):
            continue
        ts = str(row[0]) if len(row) > 0 else ""
        page = str(row[1]) if len(row) > 1 else ""
        version = str(row[2]) if len(row) > 2 else ""
        message = str(row[3]) if len(row) > 3 else ""
        message = message.replace("\x00", "")
        if not message:
            continue
        if page_filter and page_filter not in page:
            continue
        items.append({"ts": ts, "page": page, "version": version, "message": message})

    if len(items) > limit:
        items = items[-limit:]

    return jsonify({"items": items})

@app.post("/api/survey")
def api_survey():
    """Append a survey response to Google Sheets.

    Env:
      - SURVEY_SHEETS_SPREADSHEET_ID: required
      - SURVEY_SHEETS_RANGE: optional (default: responses!A:Z)
      - GOOGLE_APPLICATION_CREDENTIALS: required (service account JSON path)
      - SURVEY_IP_SALT: optional (if set, hashed IP will be stored)
    """
    if not _survey_enabled():
        return _json_error("survey is not configured", 503)

    data = request.get_json(force=True, silent=False)
    if not isinstance(data, dict):
        return _json_error("invalid json", 400)

    # required
    #if "rating" not in data:
        #return jsonify({"error": "rating is required"}), 400
    #rating = clamp_int(data.get("rating"), 1, 5, -1)
    #if rating < 1 or rating > 5:
        #return jsonify({"error": "rating must be 1..5"}), 400

    # optional fields
    category = str(data.get("category", "other") or "other").strip()
    if len(category) > 50:
        category = category[:50]

    message = str(data.get("message", "") or "")
    message = message.replace("\x00", "")
    if len(message) > 500:
        message = message[:500]

    page = str(data.get("page", "") or "").strip()
    if not page:
        page = str(request.headers.get("Referer", "") or "").strip()
    if len(page) > 300:
        page = page[:300]

    #tool = str(data.get("tool", "dps") or "dps").strip()
    #if len(tool) > 50:
        #tool = tool[:50]

    version = str(data.get("version", "") or "").strip()
    if len(version) > 100:
        version = version[:100]

    ua = str(request.headers.get("User-Agent", "") or "")
    ua = ua.replace("\x00", "")
    if len(ua) > 400:
        ua = ua[:400]

    ip_hash = _hash_ip(_client_ip())
    ts = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")

    #row = [ts, tool, tool_version, rating, category, message, page, ua, ip_hash]
    row = [ts, page, version, message, ua, ip_hash]

    try:
        _append_survey_row(row)
    except Exception as e:
        print(f"[survey] append failed: {e}")
        return _json_error("failed to save survey", 503)

    return jsonify({"ok": True})
