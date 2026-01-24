import { el, RELIC_SELECTS } from "./dom.js";
import { state, ALLOWED_CHARACTER_IDS, ALLOWLIST_EMPTY_MEANS_ALL } from "./state.js";
import { levelOptions } from "./utils.js";
import { applyStateFromUrl, persistStateToUrl } from "./url_state.js";
import { renderEnemyOptions } from "./enemy_ui.js";
import { addMember } from "./party_ui.js";
import { recalc } from "./recalc.js";

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

  const allowSet = new Set(ALLOWED_CHARACTER_IDS.map(String));
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
    el.pet1, el.pet2, el.pet3,
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

