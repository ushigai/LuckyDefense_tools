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
import { getCurrentLang, initI18n, translateDomTree } from "./i18n.js";
import { initReleaseNotesPopup } from "./release_notes_popup.js";

const URL_PERSIST_ELEMENT_IDS = new Set([
  "enemyMode",
  "enemyWave",
  "enemyGroup",
  "durationSec",
  "trials",
  "seed",
  "seedRandomize",
  "f32lock",
  "multiplier",
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

const COIN_NUMBER_FORMATTERS = {
  ja: new Intl.NumberFormat("ja-JP"),
  en: new Intl.NumberFormat("en-US"),
  kr: new Intl.NumberFormat("ko-KR"),
};

function formatCoinsDigitLabel(digits) {
  const lang = getCurrentLang();
  if (lang === "en") return `${digits} digits`;
  if (lang === "kr") return `${digits}자리`;
  return `${digits}桁`;
}

function buildCoinsPreviewText(rawValue) {
  const raw = String(rawValue ?? "").trim();
  const lang = getCurrentLang();
  const formatter = COIN_NUMBER_FORMATTERS[lang] ?? COIN_NUMBER_FORMATTERS.ja;

  if (!raw) {
    if (lang === "en") return "Enter a value to preview";
    if (lang === "kr") return "값을 입력하면 여기에 표시됩니다";
    return "値を入力するとここに表示されます";
  }

  const n = Number(raw);
  if (!Number.isFinite(n)) {
    if (lang === "en") return "Invalid number";
    if (lang === "kr") return "유효한 숫자를 입력하세요";
    return "有効な数値を入力してください";
  }

  const normalized = Math.max(0, Math.trunc(n));
  const grouped = formatter.format(normalized);
  const digits = String(normalized).length;
  return `${grouped} (${formatCoinsDigitLabel(digits)})`;
}

function updateCoinsPreview() {
  if (!el.coinsPreview) return;
  el.coinsPreview.textContent = buildCoinsPreviewText(el.coins?.value ?? "");
}

function triggerAutoRecalc() {
  if (el.autoRecalc?.checked) recalcWithSeedRandomization();
}

function addPartyMemberRow(options = {}) {
  addMember(recalcWithSeedRandomization, { ...options, onStateChange: persistStateToUrl });
}

function isSeedRandomizationEnabled() {
  return String(el.seedRandomize?.value ?? "disabled") === "enabled";
}

function createRandomSeedInt32() {
  if (window.crypto?.getRandomValues) {
    const values = new Uint32Array(1);
    window.crypto.getRandomValues(values);
    return values[0] & 0x7fff_ffff;
  }
  return Math.trunc(Math.random() * 0x8000_0000);
}

function normalizeSeedInputValue({ allowEmpty = false } = {}) {
  if (!el.seed) return;
  const rawText = String(el.seed.value ?? "").trim();
  if (allowEmpty && rawText === "") return;
  const raw = Number(rawText);
  const normalized = Number.isFinite(raw)
    ? Math.max(0, Math.min(2_147_483_647, Math.trunc(raw)))
    : 1;
  el.seed.value = String(normalized);
}

function randomizeSeedIfEnabled() {
  if (!el.seed || !isSeedRandomizationEnabled()) return;
  el.seed.value = String(createRandomSeedInt32());
}

function recalcWithSeedRandomization() {
  if (isSeedRandomizationEnabled()) {
    randomizeSeedIfEnabled();
  } else {
    normalizeSeedInputValue({ allowEmpty: false });
  }
  recalc();
}

function resolveCharacterId(rawId) {
  const hit = (state.CHARACTERS ?? []).find(c => String(c.id) === String(rawId));
  return hit?.id ?? state.CHARACTERS[0]?.id;
}

function addDefaultPartyMembers() {
  addPartyMemberRow({ characterId: state.CHARACTERS[0]?.id, charLv: 1, treasureLv: 0 });
  addPartyMemberRow({ characterId: state.CHARACTERS[1]?.id ?? state.CHARACTERS[0]?.id, charLv: 1, treasureLv: 0 });
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
    el.enemyMode,
    el.enemyWave,
    el.enemyGroup,
    el.durationSec,
    el.mythEnhanceLv,
    el.atkBuffPct,
    el.manaRegenBuffPct,
    el.speedBuffPct,
    el.defDown,
    el.coins,
    el.trials,
    el.seed,
    el.seedRandomize,
    el.f32lock,
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
  const syncEnemySelectors = () => {
    renderEnemyOptions({
      mode: String(el.enemyMode?.value ?? ""),
      wave: Number(el.enemyWave?.value || 0),
      group: String(el.enemyGroup?.value ?? ""),
    });
  };

  el.btnAddMember.addEventListener("click", () => {
    addPartyMemberRow({ characterId: state.CHARACTERS[0]?.id, charLv: 1, treasureLv: 0 });
    persistStateToUrl();
    triggerAutoRecalc();
  });

  el.btnCalc.addEventListener("click", recalcWithSeedRandomization);
  el.seed?.addEventListener("input", () => normalizeSeedInputValue({ allowEmpty: true }));
  el.seed?.addEventListener("change", () => normalizeSeedInputValue({ allowEmpty: false }));
  el.coins?.addEventListener("input", updateCoinsPreview);
  el.coins?.addEventListener("change", updateCoinsPreview);

  [el.enemyMode, el.enemyWave, el.enemyGroup].filter(Boolean).forEach(target => {
    target.addEventListener("change", syncEnemySelectors);
  });

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
  const redirected = await initI18n();
  if (redirected) return;
  initCommonOptionsUI();

  await loadInitialStateData();
  applyRelicIcons(state.ARTIFACT_MAP);

  initBlobFigureUI(() => recalcWithSeedRandomization());
  initPetUI();

  const { appliedRelic, enemySelection, partyMembers } = applyStateFromUrl();
  if (!appliedRelic) syncRelicLevelsFromAllRelic();

  const initialEnemy = enemySelection ?? {
    mode: String(state.ENEMIES[0]?.mode ?? ""),
    wave: Number(state.ENEMIES[0]?.wave ?? 0),
    group: String(state.ENEMIES[0]?.group ?? ""),
  };
  renderEnemyOptions(initialEnemy);

  if (!addPartyMembersFromUrl(partyMembers)) {
    addDefaultPartyMembers();
  }
  bindPrimaryActions();
  bindAutoRecalcTargets();

  recalcWithSeedRandomization();
  translateDomTree(document.body);
  updateCoinsPreview();
  initReleaseNotesPopup();
}

init();
