import {
  el,
  RELIC_SELECTS,
  BLOB_FIGURE_NAME_SELECTS,
  BLOB_FIGURE_VALUE_SELECTS,
  PET_NAME_SELECTS,
  PET_LEVEL_SELECTS,
} from "./dom.js";
import { state, ALLOWED_CHARACTER_IDS, ALLOWLIST_EMPTY_MEANS_ALL } from "./state.js";
import { levelOptions } from "./utils.js";
import { applyStateFromUrl, persistStateToUrl } from "./url_state.js";
import { renderEnemyOptions } from "./enemy_ui.js";
import { addMember } from "./party_ui.js";
import { recalc } from "./recalc.js";
import { upgradeSelectToImageDropdown } from "./blob_figure_image_select.js";

// ここだけ数値を変えれば、画像サイズを調整できます
const PET_IMAGE_DROPDOWN_SIZE = {
  buttonIconSizePx: 26, // 選択中のアイコンサイズ
  menuIconSizePx: 26,   // メニュー内のアイコンサイズ
  buttonImageZoom: 1.0, // 1.0=等倍 / 1.2=拡大(自動トリミング)
  menuImageZoom: 1.45,   // 1.0=等倍 / 1.2=拡大(自動トリミング)
};

const BLOB_IMAGE_DROPDOWN_SIZE = {
  buttonIconSizePx: 26, // 選択中のアイコンサイズ
  menuIconSizePx: 26,   // メニュー内のアイコンサイズ
  buttonImageZoom: 1.0, // 1.0=等倍 / 1.2=拡大(自動トリミング)
  menuImageZoom: 1.25,   // 1.0=等倍 / 1.2=拡大(自動トリミング)
};

function syncRelicLevelsFromAllRelic() {
  const v = Number(el.allRelicLv.value || 1);
  RELIC_SELECTS.forEach(sel => {
    if (!sel) return;
    sel.value = String(v);
  });
}

function populateUnitLevelSumBuffSelect(selectedValue = null) {
  const sel = document.getElementById("unitLevelSumBuff");
  if (!sel) return;
  const prev = selectedValue ?? sel.value ?? "0";

  const min2 = 0;
  const max2 = 50;

  sel.innerHTML = "";
  for (let v2 = min2; v2 <= max2; v2++) {
    const val = v2 / 2;
    const isInt = (v2 % 2 === 0);
    const valueStr = (val === 0)
      ? "0"
      : (isInt ? val.toFixed(1) : String(val));

    const opt = document.createElement("option");
    opt.value = valueStr;
    opt.textContent = valueStr;

    if (valueStr === prev || Number(valueStr) === Number(prev)) opt.selected = true;
    sel.appendChild(opt);
  }
}

function populatePetNameSelects() {
  const names = PET_NAME_SELECTS ?? [];
  if (!names.length) return;

  const pets = state.PETS ?? [];
  names.forEach(sel => {
    if (!sel) return;
    const prev = String(sel.value ?? "");
    sel.innerHTML = "";

    const noneOpt = document.createElement("option");
    noneOpt.value = "";
    noneOpt.textContent = "なし";
    sel.appendChild(noneOpt);

    pets.forEach(p => {
      const id = String(p.id ?? "");
      if (!id) return;
      const opt = document.createElement("option");
      opt.value = id;
      opt.textContent = String(p.name ?? id);
      opt.dataset.petId = id;
      sel.appendChild(opt);
    });

    if (prev) sel.value = prev;
  });
}

function populatePetLevelSelect(idx, selectedValue = null) {
  const nameSel = PET_NAME_SELECTS?.[idx];
  const levelSel = PET_LEVEL_SELECTS?.[idx];
  if (!nameSel || !levelSel) return;

  const hasName = String(nameSel.value ?? "") !== "";
  const prev = Number(selectedValue ?? levelSel.value ?? 1);

  levelSel.innerHTML = "";
  if (!hasName) {
    const opt = document.createElement("option");
    opt.value = "";
    opt.textContent = "—";
    levelSel.appendChild(opt);
    levelSel.disabled = true;
    return;
  }

  levelSel.innerHTML = levelOptions(50, Number.isFinite(prev) ? prev : 1);
  levelSel.disabled = false;
}

function initPetUI() {
  const names = PET_NAME_SELECTS ?? [];
  const levels = PET_LEVEL_SELECTS ?? [];
  if (!names.length || !levels.length) return;

  populatePetNameSelects();
  names.forEach(sel => {
    upgradeSelectToImageDropdown(sel, {
      idDatasetKey: "petId",
      imgBase: "/data/img/pet",
      unknownImg: "/data/img/blob_figure/unknown.png",
      buttonIconSizePx: PET_IMAGE_DROPDOWN_SIZE.buttonIconSizePx,
      menuIconSizePx: PET_IMAGE_DROPDOWN_SIZE.menuIconSizePx,
      buttonImageZoom: PET_IMAGE_DROPDOWN_SIZE.buttonImageZoom,
      menuImageZoom: PET_IMAGE_DROPDOWN_SIZE.menuImageZoom,
    });
  });

  for (let i = 0; i < Math.min(names.length, levels.length); i++) {
    populatePetLevelSelect(i);
    names[i].addEventListener("change", () => {
      populatePetLevelSelect(i, null);
    });
  }
}


function decimalsFromStep(step) {
  const s = String(step);
  if (s.includes("e-")) {
    const p = Number(s.split("e-")[1]);
    return Number.isFinite(p) ? p : 0;
  }
  const dot = s.indexOf(".");
  return dot >= 0 ? (s.length - dot - 1) : 0;
}

function buildRangedOptions(min, max, step) {
  const dec = decimalsFromStep(step);
  const scale = Math.pow(10, dec);
  const minI = Math.round(Number(min) * scale);
  const maxI = Math.round(Number(max) * scale);
  const stepI = Math.max(1, Math.round(Number(step) * scale));

  const out = [];
  for (let v = minI; v <= maxI; v += stepI) {
    const x = v / scale;
    out.push(dec > 0 ? x.toFixed(dec) : String(x));
  }
  return out;
}

function populateBlobFigureNameSelects() {
  const names = BLOB_FIGURE_NAME_SELECTS ?? [];
  if (!names.length) return;

  const figures = state.BLOB_FIGURES ?? [];
  names.forEach(sel => {
    if (!sel) return;
    const prev = sel.value ?? "";
    sel.innerHTML = "";

    const noneOpt = document.createElement("option");
    noneOpt.value = "";
    noneOpt.textContent = "なし";
    sel.appendChild(noneOpt);

    figures.forEach(f => {
      const opt = document.createElement("option");
      opt.value = String(f.name ?? "");
      const desc = String(f.description ?? "");
      opt.textContent = `${f.name}（${desc}）`;
      if (f.id !== undefined && f.id !== null) {
        opt.dataset.figureId = String(f.id);
      }
      sel.appendChild(opt);
    });

    if (prev) sel.value = prev;
  });
}

function populateBlobFigureValueSelect(idx, selectedValue = null) {
  const nameSel = BLOB_FIGURE_NAME_SELECTS?.[idx];
  const valSel = BLOB_FIGURE_VALUE_SELECTS?.[idx];
  if (!nameSel || !valSel) return;

  const name = String(nameSel.value ?? "");
  const prev = selectedValue ?? valSel.value ?? "";

  valSel.innerHTML = "";

  if (!name) {
    const opt = document.createElement("option");
    opt.value = "";
    opt.textContent = "—";
    valSel.appendChild(opt);
    valSel.disabled = true;
    return;
  }

  const fig = state.BLOB_FIGURE_MAP?.get(name);
  const buff = fig?.buff ?? null;
  const min = buff?.min ?? 0;
  const max = buff?.max ?? 0;
  const step = buff?.step ?? 1;

  const opts = buildRangedOptions(min, max, step);

  opts.forEach(v => {
    const opt = document.createElement("option");
    opt.value = v;
    opt.textContent = v;
    if (v === prev || Number(v) === Number(prev)) opt.selected = true;
    valSel.appendChild(opt);
  });

  if (!valSel.value && opts.length) valSel.value = opts[0];
  valSel.disabled = false;
}

function initBlobFigureUI() {
  const names = BLOB_FIGURE_NAME_SELECTS ?? [];
  const vals = BLOB_FIGURE_VALUE_SELECTS ?? [];
  if (!names.length || !vals.length) return;

  populateBlobFigureNameSelects();
  (BLOB_FIGURE_NAME_SELECTS ?? []).forEach(sel => {
    upgradeSelectToImageDropdown(sel, {
      idDatasetKey: "figureId",
      imgBase: "/data/img/blob_figure",
      unknownImg: "/data/img/blob_figure/unknown.png",
      buttonIconSizePx: BLOB_IMAGE_DROPDOWN_SIZE.buttonIconSizePx,
      menuIconSizePx: BLOB_IMAGE_DROPDOWN_SIZE.menuIconSizePx,
      buttonImageZoom: BLOB_IMAGE_DROPDOWN_SIZE.buttonImageZoom,
      menuImageZoom: BLOB_IMAGE_DROPDOWN_SIZE.menuImageZoom,
    });
  });


  for (let i = 0; i < Math.min(names.length, vals.length); i++) {
    populateBlobFigureValueSelect(i);

    names[i].addEventListener("change", () => {
      populateBlobFigureValueSelect(i, null);
      if (el.autoRecalc?.checked) recalc();
    });

    vals[i].addEventListener("change", () => {
      if (el.autoRecalc?.checked) recalc();
    });
  }
}


async function init() {
  el.allRelicLv.innerHTML = levelOptions(11, 1);
  populateUnitLevelSumBuffSelect("0");

  RELIC_SELECTS.forEach(sel => {
    sel.innerHTML = levelOptions(11, Number(el.allRelicLv.value || 1));
  });

  const { appliedRelic } = applyStateFromUrl();
  if (!appliedRelic) syncRelicLevelsFromAllRelic();

  // load characters
  const res = await fetch("/data/characters.json");
  const obj = await res.json();
  const all = obj.characters ?? [];

  if (ALLOWED_CHARACTER_IDS.length === 0 && ALLOWLIST_EMPTY_MEANS_ALL) {
    state.CHARACTERS = all;
  } else {
    const map = new Map(all.map(c => [String(c.id), c]));
    state.CHARACTERS = ALLOWED_CHARACTER_IDS.map(id => map.get(String(id))).filter(Boolean);
  }
  if (!state.CHARACTERS.length) {
    console.warn("No allowed characters matched. Falling back to all characters.");
    state.CHARACTERS = all;
  }

  // load enemies
  const er = await fetch("/data/enemy.json");
  const eobj = await er.json();
  state.ENEMIES = eobj.enemies ?? [];
  state.ENEMY_MAP = new Map(state.ENEMIES.map(e => [String(e.name), e]));

  // load pets (optional; missing file should not break UI)
  try {
    const pr = await fetch("/data/pets.json");
    if (pr.ok) {
      const pobj = await pr.json();
      state.PETS = Array.isArray(pobj) ? pobj : (pobj.pets ?? []);
      state.PET_MAP = new Map((state.PETS ?? []).map(p => [String(p.id), p]));
    } else {
      console.warn("pets.json not found:", pr.status);
      state.PETS = [];
      state.PET_MAP = new Map();
    }
  } catch (e) {
    console.warn("Failed to load pets.json:", e);
    state.PETS = [];
    state.PET_MAP = new Map();
  }

// load runes (optional; missing file should not break UI)
try {
  const rr = await fetch("/data/runes.json");
  if (rr.ok) {
    const robj = await rr.json();
    // expected: Array<{name: string, data: {卓越|不滅|...: {description, buff}}}>
    state.RUNES = Array.isArray(robj) ? robj : (robj.runes ?? []);
    state.RUNE_MAP = new Map((state.RUNES ?? []).map(r => [String(r.name), r]));
  } else {
    console.warn("runes.json not found:", rr.status);
    state.RUNES = [];
    state.RUNE_MAP = new Map();
  }
} catch (e) {
  console.warn("Failed to load runes.json:", e);
  state.RUNES = [];
  state.RUNE_MAP = new Map();
}


  // load blob figures (optional; missing file should not break UI)
  try {
    const br = await fetch("/data/blob_figures.json");
    if (br.ok) {
      const bobj = await br.json();
      // expected: Array<{name: string, description: string, buff: {min,max,step}}>
      state.BLOB_FIGURES = Array.isArray(bobj) ? bobj : (bobj.figures ?? []);
      state.BLOB_FIGURE_MAP = new Map((state.BLOB_FIGURES ?? []).map(b => [String(b.name), b]));
    } else {
      console.warn("blob_figures.json not found:", br.status);
      state.BLOB_FIGURES = [];
      state.BLOB_FIGURE_MAP = new Map();
    }
  } catch (e) {
    console.warn("Failed to load blob_figures.json:", e);
    state.BLOB_FIGURES = [];
    state.BLOB_FIGURE_MAP = new Map();
  }

  initBlobFigureUI();
  initPetUI();


  const initialEnemy = state.ENEMIES[0]?.name ?? "";
  renderEnemyOptions(initialEnemy);

  // default party
  addMember(recalc, { characterId: state.CHARACTERS[0]?.id, charLv: 1, treasureLv: 1 });
  addMember(recalc, { characterId: state.CHARACTERS[1]?.id ?? state.CHARACTERS[0]?.id, charLv: 1, treasureLv: 1 });

  el.btnAddMember.addEventListener("click", () => {
    addMember(recalc, { characterId: state.CHARACTERS[0]?.id, charLv: 1, treasureLv: 1 });
    if (el.autoRecalc.checked) recalc();
  });

  el.btnCalc.addEventListener("click", recalc);

  el.allRelicLv.addEventListener("change", () => {
    syncRelicLevelsFromAllRelic();
    persistStateToUrl();
    if (el.autoRecalc.checked) recalc();
  });

  const RECALC_TARGETS = [
    el.enemy,
    el.durationSec,
    el.mythEnhanceLv,
    el.atkBuffPct,
    el.manaRegenBuffPct,
    el.speedBuffPct,
    el.defDown,
    el.coins,
    el.trials,
    el.seed,
    el.multiplier,
    ...RELIC_SELECTS,
    ...PET_NAME_SELECTS,
    ...PET_LEVEL_SELECTS,
    ...BLOB_FIGURE_NAME_SELECTS, ...BLOB_FIGURE_VALUE_SELECTS,
    el.guildBlessing, el.unitLevelSumBuff, el.petLevelSum,
  ].filter(Boolean);

  RECALC_TARGETS.forEach(x => {
    x.addEventListener(x.tagName === "INPUT" ? "input" : "change", () => {
      if (RELIC_SELECTS.includes(x) || x === el.guildBlessing || x === el.unitLevelSumBuff || x === el.petLevelSum) {
        persistStateToUrl();
      }
      if (el.autoRecalc.checked) recalc();
    });
  });

  recalc();
}

init();
