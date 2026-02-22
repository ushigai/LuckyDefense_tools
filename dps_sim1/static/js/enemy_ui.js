import { el } from "./dom.js";
import { fmtInt } from "./utils.js";
import { state } from "./state.js";
import { t, translateGameText } from "./i18n.js";

function setText(elm, value) {
  if (!elm) return;
  elm.textContent = value;
}

function setWidth(elm, value) {
  if (!elm) return;
  elm.style.width = value;
}

function setSelectOptions(selectEl, values, selectedValue, labeler = value => String(value)) {
  if (!selectEl) return;
  if (!Array.isArray(values) || values.length === 0) {
    selectEl.innerHTML = `<option value="" selected>${t("enemyDataMissing", "敵データなし")}</option>`;
    return;
  }

  selectEl.innerHTML = values.map(value => {
    const sel = String(value) === String(selectedValue) ? "selected" : "";
    return `<option value="${String(value)}" ${sel}>${labeler(value)}</option>`;
  }).join("");
}

function uniqueByString(values) {
  const out = [];
  const seen = new Set();
  values.forEach(value => {
    const key = String(value);
    if (seen.has(key)) return;
    seen.add(key);
    out.push(value);
  });
  return out;
}

function normalizeSelection(source) {
  if (!source || typeof source !== "object") {
    return {
      mode: "",
      wave: 0,
      group: "",
    };
  }
  return {
    mode: String(source.enemyMode ?? source.mode ?? ""),
    wave: Number(source.enemyWave ?? source.wave ?? 0),
    group: String(source.enemyGroup ?? source.group ?? ""),
  };
}

function resolveEnemy(selectionSource) {
  const selection = normalizeSelection(selectionSource);
  const candidates = Array.isArray(state.ENEMIES) ? state.ENEMIES : [];
  if (candidates.length === 0) return null;

  const byCompositeKey = candidates.find(enemy =>
    String(enemy?.mode ?? "") === selection.mode &&
    Number(enemy?.wave ?? 0) === selection.wave &&
    String(enemy?.group ?? "") === selection.group
  );
  if (byCompositeKey) return byCompositeKey;

  return candidates[0] ?? null;
}

export function renderEnemyOptions(selectedSource) {
  if (!Array.isArray(state.ENEMIES) || state.ENEMIES.length === 0) {
    setSelectOptions(el.enemyMode, [], "");
    setSelectOptions(el.enemyWave, [], "");
    setSelectOptions(el.enemyGroup, [], "");
    return null;
  }

  const selected = normalizeSelection(selectedSource);
  const enemyBySelection = resolveEnemy(selected);
  const initialMode = selected.mode || String(enemyBySelection?.mode ?? "");
  const initialWave = selected.wave || Number(enemyBySelection?.wave ?? 0);
  const initialGroup = selected.group || String(enemyBySelection?.group ?? "");

  const modeOptions = uniqueByString(
    state.ENEMIES.map(enemy => String(enemy?.mode ?? "")).filter(Boolean)
  );
  const mode = modeOptions.includes(initialMode)
    ? initialMode
    : (modeOptions[0] ?? "");
  setSelectOptions(el.enemyMode, modeOptions, mode, value => translateGameText(String(value)));

  const waveOptions = uniqueByString(
    state.ENEMIES
      .filter(enemy => String(enemy?.mode ?? "") === String(mode))
      .map(enemy => Number(enemy?.wave ?? 0))
      .filter(wave => Number.isFinite(wave) && wave > 0)
      .sort((a, b) => a - b)
  );
  const wave = waveOptions.includes(initialWave) ? initialWave : Number(waveOptions[0] ?? 0);
  setSelectOptions(el.enemyWave, waveOptions, wave, value => String(value));

  const groupOptions = uniqueByString(
    state.ENEMIES
      .filter(enemy =>
        String(enemy?.mode ?? "") === String(mode) &&
        Number(enemy?.wave ?? 0) === Number(wave)
      )
      .map(enemy => String(enemy?.group ?? ""))
      .filter(Boolean)
  );
  const group = groupOptions.includes(initialGroup) ? initialGroup : (groupOptions[0] ?? "");
  setSelectOptions(el.enemyGroup, groupOptions, group, value => translateGameText(String(value)));

  return resolveEnemy({ mode, wave, group });
}

export function updateEnemyHpUI(totalDamage, selectedSource) {
  const enemy = resolveEnemy(selectedSource);
  if (!enemy || !enemy.hp) {
    setText(el.enemyHpText, `${t("hpShort", "HP")}: —`);
    setText(el.enemyHpPct, "—");
    setText(el.enemyHpDetail, "");
    setWidth(el.enemyHpBar, "0%");
    return;
  }

  const hp = Number(enemy.hp);
  const dmg = Number(totalDamage || 0);

  const pct = hp > 0 ? (dmg / hp) * 100 : 0;
  const bar = Math.max(0, Math.min(100, pct));

  setText(el.enemyHpText, `${t("hpShort", "HP")}: ${fmtInt(hp)}`);
  setText(el.enemyHpPct, `${pct.toFixed(2)}%`);
  setText(el.enemyHpDetail, `（${fmtInt(dmg)} / ${fmtInt(hp)}）`);
  setWidth(el.enemyHpBar, `${bar}%`);
}
