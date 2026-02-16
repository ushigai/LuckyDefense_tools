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

export function renderEnemyOptions(selectedName) {
  if (!Array.isArray(state.ENEMIES) || state.ENEMIES.length === 0) {
    el.enemy.innerHTML = `<option value="" selected>${t("enemyDataMissing")}</option>`;
    return;
  }

  el.enemy.innerHTML = state.ENEMIES.map(e => {
    const sel = String(e.name) === String(selectedName) ? "selected" : "";
    const enemyLabel = translateGameText(e.name);
    return `<option value="${e.name}" ${sel}>${enemyLabel} (${t("hpShort")} ${fmtInt(e.hp)})</option>`;
  }).join("");
}

export function updateEnemyHpUI(totalDamage, enemyName) {
  const enemy = state.ENEMY_MAP.get(String(enemyName));
  if (!enemy || !enemy.hp) {
    setText(el.enemyHpText, `${t("hpShort")}: —`);
    setText(el.enemyHpPct, "—");
    setText(el.enemyHpDetail, "");
    setWidth(el.enemyHpBar, "0%");
    return;
  }

  const hp = Number(enemy.hp);
  const dmg = Number(totalDamage || 0);

  const pct = hp > 0 ? (dmg / hp) * 100 : 0;
  const bar = Math.max(0, Math.min(100, pct));

  setText(el.enemyHpText, `${t("hpShort")}: ${fmtInt(hp)}`);
  setText(el.enemyHpPct, `${pct.toFixed(2)}%`);
  setText(el.enemyHpDetail, `（${fmtInt(dmg)} / ${fmtInt(hp)}）`);
  setWidth(el.enemyHpBar, `${bar}%`);
}
