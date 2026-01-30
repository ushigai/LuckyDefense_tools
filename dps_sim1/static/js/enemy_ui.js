import { el } from "./dom.js";
import { fmtInt } from "./utils.js";
import { state } from "./state.js";

export function renderEnemyOptions(selectedName) {
  if (!Array.isArray(state.ENEMIES) || state.ENEMIES.length === 0) {
    el.enemy.innerHTML = `<option value="" selected>敵データなし</option>`;
    return;
  }

  el.enemy.innerHTML = state.ENEMIES.map(e => {
    const sel = String(e.name) === String(selectedName) ? "selected" : "";
    return `<option value="${e.name}" ${sel}>${e.name} (HP ${fmtInt(e.hp)})</option>`;
  }).join("");
}

export function updateEnemyHpUI(totalDamage, enemyName) {
  const enemy = state.ENEMY_MAP.get(String(enemyName));
  if (!enemy || !enemy.hp) {
    el.enemyHpText.textContent = "HP: —";
    el.enemyHpPct.textContent = "—";
    el.enemyHpDetail.textContent = "";
    el.enemyHpBar.style.width = "0%";
    return;
  }

  const hp = Number(enemy.hp);
  const dmg = Number(totalDamage || 0);

  const pct = hp > 0 ? (dmg / hp) * 100 : 0;
  const bar = Math.max(0, Math.min(100, pct));

  el.enemyHpText.textContent = `HP: ${fmtInt(hp)}`;
  el.enemyHpPct.textContent = `${pct.toFixed(2)}%`;
  el.enemyHpDetail.textContent = `（${fmtInt(dmg)} / ${fmtInt(hp)}）`;
  el.enemyHpBar.style.width = `${bar}%`;
}

