import { el } from "./dom.js";
import { state } from "./state.js";

export const EXTRA_KEY_LABEL = {
  intake: "摂取値",
  mythCount: "異種神話数",
  uchiCells: "マス数",
  batEnhance: "バット強化",
  starPower: "星の力",
  emotionControl: "感情コントロール",
  sparkBonusDmg: "火花追加ダメージ",
  energyCount: "エネルギー個数（究極中）",
  techEnhance: "技術強化",
  score: "スコア",
  cannibalCount: "共食い回数",
  training: "鍛錬",
  StrongestCreature: "動物ユニット数",
  robots: "ドローン",
};

// name -> fields
export const EXTRA_FIELDS_BY_NAME = {
  "覚醒ヘイリー": [{ key: "mythCount", label: "異種神話数", kind: "number", min: 0, step: 1, def: 0 }],
  "ブロッブ":     [{ key: "intake", label: "摂取値", kind: "number", min: 0, step: 1, def: 0 }],

  "バットマン":   [{ key: "batEnhance", label: "バット強化", kind: "select-int", min: 1, max: 20, def: 1 }],
  "ヘイリー":     [{ key: "starPower", label: "星の力", kind: "select-int", min: 0, max: 10, def: 0 }],
  "マスタークン": [{ key: "emotionControl", label: "感情コントロール", kind: "select-int", min: 0, max: 99, def: 0 }],
  "ランスロット": [{ key: "sparkBonusDmg", label: "火花追加ダメージ", kind: "select-float", min: 0.0, max: 3.0, step: 0.1, def: 0.0 }],
  "ワット":       [{ key: "energyCount", label: "エネルギー個数（究極中）", kind: "number", min: 1, step: 1, def: 1 }],
  "ワット（究極発動中）": [{ key: "energyCount", label: "エネルギー個数（究極中）", kind: "number", min: 1, step: 1, def: 1 }],
  "アイアンニャンv2": [{ key: "techEnhance", label: "技術強化", kind: "select-int", min: 0, max: 10, def: 0 }],
  "選鳥師":       [{ key: "score", label: "スコア", kind: "select-int", min: 0, max: 100, def: 0 }],
  "タール":       [{ key: "cannibalCount", label: "共食い回数", kind: "number", min: 0, step: 1, def: 0 }],
  "バンバ":       [{ key: "training", label: "鍛錬", kind: "select-int", min: 0, max: 30, def: 0 }],
  "ドラゴン":     [{ key: "StrongestCreature", label: "動物ユニット数", kind: "number", min: 1, step: 1, def: 1 }],
  "ドクターパルス":     [{ key: "robots", label: "ドローン", kind: "number", min: 1, max: 4, def: 1 }],
};

export function getCharNameById(characterId) {
  return (state.CHARACTERS.find(c => String(c.id) === String(characterId))?.name) ?? String(characterId);
}

export function getExtraFieldsForCharacter(characterId) {
  const name = getCharNameById(characterId);
  return EXTRA_FIELDS_BY_NAME[name] ?? [];
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

export function renderExtraControls(row, characterId, initialExtras = {}, recalcFn) {
  // 値の保持（キャラ切り替えでフォームを作り直すため）
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
    label.textContent = f.label;

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
      if (el.autoRecalc?.checked && typeof recalcFn === "function") recalcFn();
    });

    col.appendChild(label);
    col.appendChild(input);
    container.appendChild(col);
  });
}

