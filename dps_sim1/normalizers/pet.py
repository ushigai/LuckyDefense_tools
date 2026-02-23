from __future__ import annotations

from typing import Any, Dict, List, Tuple


def _clamp_int(v: Any, lo: int, hi: int, default: int) -> int:
    try:
        x = int(v)
    except Exception:
        return default
    return max(lo, min(hi, x))


def is_none_token(v: Any) -> bool:
    s = str(v or "").strip().lower()
    return s in ("", "なし", "none", "null", "0")


def resolve_pet_id_name(
    pid: Any,
    pname: Any,
    pet_db_by_id: Dict[str, Dict[str, Any]],
    pet_db_by_name: Dict[str, Dict[str, Any]],
) -> Tuple[str, str]:
    pid_s = str(pid or "").strip()
    if pid_s.lower().endswith(".png"):
        pid_s = pid_s[:-4].strip()

    if not is_none_token(pid_s):
        if pid_s.isdigit():
            row = pet_db_by_id.get(pid_s, {})
            return pid_s, str(row.get("name", "") or "")
        if pid_s in pet_db_by_name:
            row = pet_db_by_name[pid_s]
            return str(row.get("id", "") or ""), str(row.get("name", "") or pid_s)

    name_s = str(pname or "").strip()
    if is_none_token(name_s):
        return "", ""

    if name_s in pet_db_by_name:
        row = pet_db_by_name[name_s]
        return str(row.get("id", "") or ""), str(row.get("name", "") or name_s)
    if name_s.isdigit():
        row = pet_db_by_id.get(name_s, {})
        if row:
            return name_s, str(row.get("name", "") or "")
    return "", ""


def normalize_pets(
    options: Any,
    pet_db_by_id: Dict[str, Dict[str, Any]],
    pet_db_by_name: Dict[str, Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Normalize pet options to [{id, name, level, image}] (max 3)."""
    if not isinstance(options, dict):
        return []

    raw_rows: List[Dict[str, Any]] = []

    pets = options.get("pets")
    if isinstance(pets, list):
        for p in pets:
            if not isinstance(p, dict):
                continue
            raw_rows.append(
                {
                    "id": p.get("id", p.get("petId", p.get("petID", ""))),
                    "name": p.get("name", p.get("petName", "")),
                    "level": p.get("level", p.get("lv", p.get("petLv", p.get("petLevel", "")))),
                }
            )

    if not raw_rows:
        for i in (1, 2, 3):
            pid = options.get(
                f"pet{i}",
                options.get(f"pet{i}Id", options.get(f"pet{i}ID", "")),
            )
            pname = options.get(f"pet{i}Name", "")
            lv = options.get(
                f"pet{i}Level",
                options.get(f"pet{i}Lv", options.get(f"pet{i}level", "")),
            )
            raw_rows.append({"id": pid, "name": pname, "level": lv})

    if not raw_rows:
        pet_obj = options.get("pet")
        if isinstance(pet_obj, dict):
            raw_rows.append(
                {
                    "id": pet_obj.get("id", pet_obj.get("petId", "")),
                    "name": pet_obj.get("name", pet_obj.get("petName", "")),
                    "level": pet_obj.get("level", pet_obj.get("lv", pet_obj.get("petLv", ""))),
                }
            )
        else:
            raw_rows.append(
                {
                    "id": options.get("petId", options.get("petID", "")),
                    "name": options.get("petName", ""),
                    "level": options.get("petLv", options.get("petLevel", options.get("pet_level", ""))),
                }
            )

    out: List[Dict[str, Any]] = []
    for row in raw_rows:
        pid, pname = resolve_pet_id_name(row.get("id"), row.get("name"), pet_db_by_id, pet_db_by_name)
        if not pid:
            continue
        level = _clamp_int(row.get("level"), 1, 50, 1)
        out.append(
            {
                "id": pid,
                "petId": pid,
                "name": pname or pid,
                "level": level,
                "petLv": level,
                "image": f"/data/img/pet/{pid}.png",
            }
        )
        if len(out) >= 3:
            break
    return out


def normalize_pet(
    options: Any,
    pet_db_by_id: Dict[str, Dict[str, Any]],
    pet_db_by_name: Dict[str, Dict[str, Any]],
) -> Dict[str, Any] | None:
    pets = normalize_pets(options, pet_db_by_id, pet_db_by_name)
    return pets[0] if pets else None


def to_pet_slots(
    pets: List[Dict[str, Any]],
) -> Tuple[Dict[str, Any] | None, Dict[str, Any] | None, Dict[str, Any] | None]:
    pet1 = pets[0] if len(pets) >= 1 else None
    pet2 = pets[1] if len(pets) >= 2 else None
    pet3 = pets[2] if len(pets) >= 3 else None
    return pet1, pet2, pet3


def pet_param_at_lv(
    pet_id: str,
    pet_lv: int,
    param_no: int,
    pet_db_by_id: Dict[str, Dict[str, Any]],
    skill_idx: int = 0,
) -> float | None:
    """Read pet skill parameter at level. Returns None when not available."""
    if not pet_id:
        return None
    row = pet_db_by_id.get(str(pet_id), {})
    raw = row.get("raw") if isinstance(row, dict) else None
    if not isinstance(raw, dict):
        return None

    skills = raw.get("skills", [])
    if not isinstance(skills, list) or not (0 <= skill_idx < len(skills)):
        return None
    skill = skills[skill_idx]
    if not isinstance(skill, dict):
        return None

    arr = skill.get(f"Paramter_{param_no}", skill.get(f"Parameter_{param_no}", []))
    if not isinstance(arr, list) or len(arr) == 0:
        return None

    idx = max(0, min(len(arr) - 1, int(pet_lv) - 1))
    try:
        return float(arr[idx])
    except Exception:
        return None
