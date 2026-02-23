from __future__ import annotations

from typing import Any, Dict, List


def _clamp_float(v: Any, lo: float, hi: float, default: float) -> float:
    try:
        x = float(v)
    except Exception:
        return default
    return max(lo, min(hi, x))


def decimals_from_step(step: Any) -> int:
    try:
        s = str(step)
    except Exception:
        return 0
    if "e-" in s:
        try:
            return int(s.split("e-")[1])
        except Exception:
            return 0
    if "." in s:
        return len(s.split(".")[1])
    return 0


def snap_to_step(x: float, lo: float, step: float) -> float:
    if step <= 0:
        return x
    n = round((x - lo) / step)
    return lo + n * step


def normalize_blob_figures(v: Any, blob_figures_db: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Normalize common['blobFigures'] to a safe list of {name, value}."""
    if not isinstance(v, list):
        return []
    out: List[Dict[str, Any]] = []
    for item in v:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name", "") or "")
        if not name:
            continue
        spec = blob_figures_db.get(name)
        if not spec:
            continue
        buff = spec.get("buff") if isinstance(spec, dict) else None
        if not isinstance(buff, dict):
            continue
        lo = float(buff.get("min", 0))
        hi = float(buff.get("max", 0))
        step = float(buff.get("step", 1))
        raw = item.get("value", None)
        x = _clamp_float(raw, lo, hi, lo)
        x = snap_to_step(x, lo, step)
        dec = decimals_from_step(step)
        if dec > 0:
            x = round(x, dec)
        else:
            x = float(int(round(x)))
        out.append({"name": name, "value": x})
        if len(out) >= 5:
            break
    return out

