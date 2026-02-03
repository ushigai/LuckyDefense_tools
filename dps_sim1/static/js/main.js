import {
  el,
  RELIC_SELECTS,
  BLOB_FIGURE_NAME_SELECTS,
  BLOB_FIGURE_VALUE_SELECTS,
  PET_NAME_SELECTS,
  PET_LEVEL_SELECTS,
} from "./dom.js";
import { state } from "./state.js";
import { applyStateFromUrl, persistStateToUrl } from "./url_state.js";
import { renderEnemyOptions } from "./enemy_ui.js";
import { addMember } from "./party_ui.js";
import { recalc } from "./recalc.js";
import { loadInitialStateData } from "./data_loader.js";
import { initCommonOptionsUI, syncRelicLevelsFromAllRelic } from "./common_options_ui.js";
import { initPetUI } from "./pet_ui.js";
import { initBlobFigureUI } from "./blob_figure_ui.js";

const URL_PERSIST_ELEMENT_IDS = new Set(["guildBlessing", "unitLevelSumBuff", "petLevelSum"]);

function triggerAutoRecalc() {
  if (el.autoRecalc?.checked) recalc();
}

function addDefaultPartyMembers() {
  addMember(recalc, { characterId: state.CHARACTERS[0]?.id, charLv: 1, treasureLv: 1 });
  addMember(recalc, { characterId: state.CHARACTERS[1]?.id ?? state.CHARACTERS[0]?.id, charLv: 1, treasureLv: 1 });
}

function shouldPersistTargetToUrl(target) {
  if (!target) return false;
  if (RELIC_SELECTS.includes(target)) return true;
  return URL_PERSIST_ELEMENT_IDS.has(target.id);
}

function buildRecalcTargets() {
  return [
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
    ...BLOB_FIGURE_NAME_SELECTS,
    ...BLOB_FIGURE_VALUE_SELECTS,
    el.guildBlessing,
    el.unitLevelSumBuff,
    el.petLevelSum,
  ].filter(Boolean);
}

function bindPrimaryActions() {
  el.btnAddMember.addEventListener("click", () => {
    addMember(recalc, { characterId: state.CHARACTERS[0]?.id, charLv: 1, treasureLv: 1 });
    triggerAutoRecalc();
  });

  el.btnCalc.addEventListener("click", recalc);

  el.allRelicLv.addEventListener("change", () => {
    syncRelicLevelsFromAllRelic();
    persistStateToUrl();
    triggerAutoRecalc();
  });
}

function bindAutoRecalcTargets() {
  buildRecalcTargets().forEach(target => {
    const eventName = target.tagName === "INPUT" ? "input" : "change";
    target.addEventListener(eventName, () => {
      if (shouldPersistTargetToUrl(target)) persistStateToUrl();
      triggerAutoRecalc();
    });
  });
}

async function init() {
  initCommonOptionsUI();

  const { appliedRelic } = applyStateFromUrl();
  if (!appliedRelic) syncRelicLevelsFromAllRelic();

  await loadInitialStateData();

  initBlobFigureUI(() => recalc());
  initPetUI();

  const initialEnemy = state.ENEMIES[0]?.name ?? "";
  renderEnemyOptions(initialEnemy);

  addDefaultPartyMembers();
  bindPrimaryActions();
  bindAutoRecalcTargets();

  recalc();
}

init();
