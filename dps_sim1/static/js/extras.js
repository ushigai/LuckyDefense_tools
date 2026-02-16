import { el } from "./dom.js";
import { translateGameText } from "./i18n.js";

export const EXTRA_FIELDS_BY_CHARACTER_ID = {
  "15021": [{ key: "mythCount", label: "異種神話数", kind: "number", min: 0, step: 1, def: 0 }],
  //"5005": [{ key: "intake", label: "摂取値", kind: "number", min: 0, step: 1, def: 0 }],
  "5016": [{ key: "uchiCells", label: "敵との距離（マス数）", kind: "select-float", min: 1.0, max: 5.0, step: 0.1, def: 5.0 }],
  "5010": [{ key: "batEnhance", label: "バット強化", kind: "select-int", min: 1, max: 20, def: 1 }],
  "15210": [{ key: "batEnhance_", label: "バット強化", kind: "select-int", min: 10, max: 20, def: 10 }],
  "15110": [
    { key: "strikeout", label: "ストライクアウト平均回数", kind: "select-float", min: 1.0, max: 3.0, step: 0.1, def: 1.0 },
    { key: "batEnhance_", label: "バット強化", kind: "select-int", min: 10, max: 20, def: 10 },
  ],
  "5021": [{ key: "starPower", label: "星の力", kind: "select-int", min: 0, max: 10, def: 0 }],
  "5018": [{ key: "emotionControl", label: "感情コントロール", kind: "select-int", min: 0, max: 99, def: 0 }],
  "5003": [{ key: "sparkBonusDmg", label: "火花追加ダメージ", kind: "select-float", min: 0.0, max: 3.0, step: 0.1, def: 0.0 }],
  "5013": [{ key: "energyCount", label: "エネルギー個数（究極中）", kind: "number", min: 1, step: 1, def: 1 }],
  "5204": [{ key: "techEnhance", label: "技術強化", kind: "select-int", min: 0, max: 10, def: 0 }],
  "5024": [{ key: "score", label: "スコア", kind: "select-int", min: 0, max: 100, def: 0 }],
  "5306": [{ key: "cannibalCount", label: "共食い回数", kind: "number", min: 0, step: 1, def: 0 }],
  "5001": [{ key: "training", label: "鍛錬", kind: "select-int", min: 0, max: 30, def: 0 }],
  "5106": [{ key: "StrongestCreature", label: "動物ユニット数", kind: "number", min: 1, step: 1, def: 1 }],
  "15006": [{ key: "StrongestCreature", label: "動物ユニット数", kind: "number", min: 1, step: 1, def: 1 }],
  "14002": [{ key: "robots", label: "ドローン", kind: "select-int", min: 1, max: 4, def: 1 }],
  "5023": [{ key: "roka_crit", label: "クリティカル率増加", kind: "select-int", min: 1, max: 30, def: 30 }],
  "15023": [{ key: "roka_crit_", label: "クリティカル率増加", kind: "select-int", min: 1, max: 30, step: 1, def: 30 }],
  "15005": [
    { key: "intake", label: "摂取値", kind: "number", min: 0, max: 10000000000, step: 1, def: 25000 },
    { key: "blueBlob", label: "青ブロッブレベル", kind: "select-int", min: 0, max: 20, step: 1, def: 3 },
    { key: "redBlob", label: "赤ブロッブレベル", kind: "select-int", min: 0, max: 20, step: 1, def: 3 },
    { key: "greenBlob", label: "緑ブロッブレベル", kind: "select-int", min: 0, max: 20, step: 1, def: 3 },
  ],
  "5002": [
    { key: "icecount", label: "氷河の合計個数", kind: "number", min: 10, max: 1000000000, step: 1, def: 20 },
    { key: "icerate", label: "氷河命中確率%", kind: "select-int", min: 0, max: 100, step: 1, def: 40 },
  ],
};

export function getExtraFieldsForCharacter(characterId) {
  return EXTRA_FIELDS_BY_CHARACTER_ID[String(characterId)] ?? [];
}

function selectOptionsInt(min, max, selected) {
  const sel = Number(selected);
  let s = "";
  for (let i = min; i <= max; i++) {
    s += `<option value="${i}" ${i === sel ? "selected" : ""}>${i}</option>`;
  }
  return s;
}

function selectOptionsFloat(min, max, step, selected) {
  const stepStr = String(step);
  const decimals = (stepStr.split(".")[1] || "").length;
  const scale = 10 ** decimals;

  const minI = Math.round(Number(min) * scale);
  const maxI = Math.round(Number(max) * scale);
  const stepI = Math.max(1, Math.round(Number(step) * scale));
  const sel = Math.round(Number(selected) * scale);

  let s = "";
  for (let v = minI; v <= maxI; v += stepI) {
    const val = v / scale;
    const valueStr = val.toFixed(decimals);
    const isSel = (v === sel);
    s += `<option value="${valueStr}" ${isSel ? "selected" : ""}>${valueStr}</option>`;
  }
  return s;
}

export function readRowExtraValues(row) {
  const out = {};
  row.querySelectorAll(".member-extra[data-extra-key]").forEach(node => {
    const k = node.dataset.extraKey;
    out[k] = node.value;
  });
  return out;
}

export function renderExtraControls(row, characterId, initialExtras = {}, recalcFn, onStateChangeFn = null) {
  row._extraValues = { ...(row._extraValues || {}), ...readRowExtraValues(row), ...initialExtras };

  const fields = getExtraFieldsForCharacter(characterId);
  const container = row.querySelector(".member-extra-container");
  if (!container) return;

  container.innerHTML = "";
  if (!fields.length) return;

  fields.forEach(f => {
    const col = document.createElement("div");
    col.className = "col-12 col-lg-6";

    const label = document.createElement("label");
    label.className = "form-label text-secondary small mb-1";
    label.textContent = translateGameText(f.label);

    let input;
    const currentVal = (row._extraValues[f.key] ?? f.def);

    if (f.kind === "select-int") {
      input = document.createElement("select");
      input.className = "form-select member-extra rounded-3";
      input.dataset.extraKey = f.key;
      input.innerHTML = selectOptionsInt(f.min, f.max, currentVal);
    } else if (f.kind === "select-float") {
      input = document.createElement("select");
      input.className = "form-select member-extra rounded-3";
      input.dataset.extraKey = f.key;
      input.innerHTML = selectOptionsFloat(f.min, f.max, f.step, currentVal);
    } else {
      input = document.createElement("input");
      input.type = "number";
      input.className = "form-control member-extra rounded-3";
      input.dataset.extraKey = f.key;
      if (f.min !== undefined) input.min = String(f.min);
      if (f.max !== undefined) input.max = String(f.max);
      if (f.step !== undefined) input.step = String(f.step);
      input.value = String(currentVal);
    }

    input.addEventListener(input.tagName === "INPUT" ? "input" : "change", () => {
      row._extraValues[f.key] = input.value;
      if (typeof onStateChangeFn === "function") onStateChangeFn();
      if (el.autoRecalc?.checked && typeof recalcFn === "function") recalcFn();
    });

    col.appendChild(label);
    col.appendChild(input);
    container.appendChild(col);
  });
}
