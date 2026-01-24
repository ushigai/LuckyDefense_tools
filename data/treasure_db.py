# treasure_db.py
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple, Union

Number = Union[int, float]
Cell = Union[str, Number]
Row = List[Cell]

_INT_RE = re.compile(r"^-?\d+$")
_FLOAT_RE = re.compile(r"^-?\d+\.\d+$")

def _coerce_cell(x: Any) -> Cell:
    if x is None:
        return "-"
    if isinstance(x, (int, float)):
        return x
    s = str(x).strip()
    if s == "" or s == "-":
        return "-"
    if _INT_RE.match(s):
        return int(s)
    if _FLOAT_RE.match(s):
        return float(s)
    return s

class LevelTable(list):
    def __getitem__(self, level: int) -> Row:
        row = super().__getitem__(level)
        if row is None:
            raise KeyError(f"祭壇レベル {level} の行が存在しません")
        return row

@dataclass(frozen=True)
class TreasureTable:
    name: str
    columns: List[str]
    rows_by_level: LevelTable

    @property
    def col_index(self) -> Dict[str, int]:
        return {c: i for i, c in enumerate(self.columns)}

    def get(self, level: int, column: Union[int, str]) -> Cell:
        row = self.rows_by_level[level]
        idx = column if isinstance(column, int) else self.col_index[column]
        return row[idx]

def build_treasure_db(formatted: Dict[str, Any]) -> Tuple[Dict[str, LevelTable], Dict[str, TreasureTable]]:
    treasures = formatted.get("treasures", [])
    db: Dict[str, LevelTable] = {}
    tables: Dict[str, TreasureTable] = {}

    for t in treasures:
        name = str(t["name"])
        columns = [str(c) for c in t.get("columns", [])]
        rows_raw = t.get("rows", [])

        levels: List[int] = []
        coerced_rows: List[Row] = []
        for r in rows_raw:
            cr = [_coerce_cell(x) for x in r]
            try:
                lvl = int(cr[0])  # type: ignore[arg-type]
            except Exception:
                continue
            cr[0] = lvl
            levels.append(lvl)
            coerced_rows.append(cr)

        if not levels:
            continue

        max_level = max(levels)
        table = LevelTable([None] * (max_level + 1))
        for cr in coerced_rows:
            lvl = int(cr[0])  # type: ignore[arg-type]
            table[lvl] = cr

        db[name] = table
        tables[name] = TreasureTable(name=name, columns=columns, rows_by_level=table)

    return db, tables

def load_treasure_db(json_path: str) -> Tuple[Dict[str, LevelTable], Dict[str, TreasureTable]]:
    with open(json_path, "r", encoding="utf-8") as f:
        formatted = json.load(f)
    return build_treasure_db(formatted)

