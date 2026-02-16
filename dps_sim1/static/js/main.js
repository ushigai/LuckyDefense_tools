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
import { applyRelicIcons, initCommonOptionsUI, syncRelicLevelsFromAllRelic } from "./common_options_ui.js";
import { initPetUI } from "./pet_ui.js";
import { initBlobFigureUI } from "./blob_figure_ui.js";
import { initI18n, translateDomTree } from "./i18n.js";

const URL_PERSIST_ELEMENT_IDS = new Set([
  "mythEnhanceLv",
  "atkBuffPct",
  "manaRegenBuffPct",
  "speedBuffPct",
  "defDown",
  "coins",
  "guildBlessing",
  "unitLevelSumBuff",
  "petLevelSum",
]);

function triggerAutoRecalc() {
  if (el.autoRecalc?.checked) recalc();
}

function addPartyMemberRow(options = {}) {
  addMember(recalc, { ...options, onStateChange: persistStateToUrl });
}

function resolveCharacterId(rawId) {
  const hit = (state.CHARACTERS ?? []).find(c => String(c.id) === String(rawId));
  return hit?.id ?? state.CHARACTERS[0]?.id;
}

function addDefaultPartyMembers() {
  addPartyMemberRow({ characterId: state.CHARACTERS[0]?.id, charLv: 1, treasureLv: 1 });
  addPartyMemberRow({ characterId: state.CHARACTERS[1]?.id ?? state.CHARACTERS[0]?.id, charLv: 1, treasureLv: 1 });
}

function addPartyMembersFromUrl(partyMembers) {
  if (!Array.isArray(partyMembers) || partyMembers.length === 0) return false;

  let added = 0;
  partyMembers.forEach(member => {
    const characterId = resolveCharacterId(member?.characterId);
    if (!characterId) return;

    addPartyMemberRow({
      characterId,
      charLv: Number(member?.charLv ?? 1),
      treasureLv: Number(member?.treasureLv ?? 0),
      extras: (member?.extras && typeof member.extras === "object") ? member.extras : {},
    });
    added += 1;
  });

  return added > 0;
}

function shouldPersistTargetToUrl(target) {
  if (!target) return false;
  if (RELIC_SELECTS.includes(target)) return true;
  if (PET_NAME_SELECTS.includes(target)) return true;
  if (PET_LEVEL_SELECTS.includes(target)) return true;
  return URL_PERSIST_ELEMENT_IDS.has(target.id);
}

function getBuffCharacterTargets() {
  return Array.from(document.querySelectorAll(".buff-character-select"));
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
    ...getBuffCharacterTargets(),
    el.guildBlessing,
    el.unitLevelSumBuff,
    el.petLevelSum,
  ].filter(Boolean);
}

function bindPrimaryActions() {
  el.btnAddMember.addEventListener("click", () => {
    addPartyMemberRow({ characterId: state.CHARACTERS[0]?.id, charLv: 1, treasureLv: 1 });
    persistStateToUrl();
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
  await initI18n();
  initCommonOptionsUI();

  await loadInitialStateData();
  applyRelicIcons(state.ARTIFACT_MAP);

  initBlobFigureUI(() => recalc());
  initPetUI();

  const { appliedRelic, partyMembers } = applyStateFromUrl();
  if (!appliedRelic) syncRelicLevelsFromAllRelic();

  const initialEnemy = state.ENEMIES[0]?.name ?? "";
  renderEnemyOptions(initialEnemy);

  if (!addPartyMembersFromUrl(partyMembers)) {
    addDefaultPartyMembers();
  }
  bindPrimaryActions();
  bindAutoRecalcTargets();

  recalc();
  translateDomTree(document.body);
}

init();
