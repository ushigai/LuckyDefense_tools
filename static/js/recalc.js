import { el } from "./dom.js";
import { fmtNumber } from "./utils.js";
import { computeViaPython } from "./api.js";
import { collectOptions } from "./options.js";
import { getPartyMembers } from "./party_ui.js";
import { updateEnemyHpUI } from "./enemy_ui.js";
import { EXTRA_KEY_LABEL } from "./extras.js";
import { state } from "./state.js";

function setBusy(isBusy) {
  el.btnCalc.disabled = isBusy;
  el.calcStatus.textContent = isBusy ? "計算中…" : "";
  el.btnCalc.innerHTML = isBusy
    ? '<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>計算中'
    : '<i class="bi bi-cpu me-1"></i>計算する';
}


function _getCharacterById(id) {
  return (state.CHARACTERS ?? []).find(c => String(c.id) === String(id)) ?? null;
}

function _formatPct(x) {
  if (!isFinite(x) || x <= 0) return "0.0";
  return x.toFixed(1);
}

function _escHtml(s) {
  return String(s ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/\"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function _renderDpsRatio(characterId, ratioObj) {
  // ratioObj: {basic, skill1, skill2, skill3, ult} (values are raw damage totals)
  if (!ratioObj || typeof ratioObj !== "object") return "";

  const ch = _getCharacterById(characterId) ?? {};

  // total damage is computed from raw keys (even if some labels are hidden)
  const KEYS = ["basic", "skill1", "skill2", "skill3", "ult"];
  const total = KEYS.reduce((a, k) => {
    const v = Number(ratioObj?.[k] ?? 0);
    return a + (isFinite(v) ? v : 0);
  }, 0);

  // If everything is 0, show a small placeholder
  if (!isFinite(total) || total <= 0) {
    return `<div class="text-secondary small">内訳: —</div>`;
  }

  const items = [];

  // basic is always shown
  items.push({ key: "basic", label: "基本攻撃", value: Number(ratioObj.basic ?? 0) });

  // skill labels come from characters.json; if empty string, don't show that row
  const s1name = String(ch.skill1 ?? "").trim();
  const s2name = String(ch.skill2 ?? "").trim();
  const s3name = String(ch.skill3 ?? "").trim();

  if (s1name !== "") items.push({ key: "skill1", label: s1name, value: Number(ratioObj.skill1 ?? 0) });
  if (s2name !== "") items.push({ key: "skill2", label: s2name, value: Number(ratioObj.skill2 ?? 0) });
  if (s3name !== "") items.push({ key: "skill3", label: s3name, value: Number(ratioObj.skill3 ?? 0) });

  // ult label: if characters.json has ult="" then don't show at all
  const hasUltKey = Object.prototype.hasOwnProperty.call(ch, "ult");
  const ultName = hasUltKey ? String(ch.ult ?? "").trim() : "ult";
  if (ultName !== "") {
    items.push({ key: "ult", label: ultName, value: Number(ratioObj.ult ?? 0) });
  }

  const rows = items.map(it => {
    const v = isFinite(it.value) ? it.value : 0;
    const pct = (v / total) * 100;
    const pctStr = _formatPct(pct);
    const safeLabel = String(it.label ?? it.key);
    const width = Math.max(0, Math.min(100, pct));
    return `
      <div class="mb-2">
        <div class="d-flex justify-content-between small">
          <span class="text-secondary text-truncate me-2" title="${_escHtml(safeLabel)}">${_escHtml(safeLabel)}</span>
          <span class="metric">${pctStr}%</span>
        </div>
        <div class="progress" style="height: 6px;">
          <div class="progress-bar" role="progressbar" style="width: ${width}%" aria-valuenow="${pctStr}" aria-valuemin="0" aria-valuemax="100"></div>
        </div>
      </div>
    `;
  }).join("");

  return `
    <div class="mt-2 text-start">
      ${rows}
    </div>
  `;
}

export async function recalc() {
  const options = collectOptions();
  const members = getPartyMembers();
  if (members.length === 0) return;

  const party = members.map(m => {
    const obj = { character: m.character, charLv: m.charLv, treasureLv: m.treasureLv, runeName: m.runeName, runeRarity: m.runeRarity };
    Object.assign(obj, m.extras || {});
    return obj;
  });

  setBusy(true);
  try {
    const data = await computeViaPython(party, options);

    const dpsList = (data.members ?? []).map(x => Number(x.dps ?? 0));
    const total = Number(data.totalDps ?? dpsList.reduce((a, b) => a + b, 0));

    el.totalValue.textContent = fmtNumber(Math.round(total));
    updateEnemyHpUI(total, options.enemy);

    (data.members ?? []).forEach((r, i) => {
      const dps = Number(r.dps ?? 0);
      members[i].dpsEl.textContent = fmtNumber(dps);

      const share = (total > 0) ? (dps / total) * 100 : (100 / members.length);
      members[i].shareEl.textContent = `share: ${share.toFixed(3)}%`;

      // DPS 内訳（basic/skill/ult）
      let ratioObj = null;
      if (r && r.dpsRatio && typeof r.dpsRatio === "object") {
        ratioObj = r.dpsRatio;
      } else if (Array.isArray(data?.dpsRatio) && data.dpsRatio[i] && typeof data.dpsRatio[i] === "object") {
        ratioObj = data.dpsRatio[i];
      } else if (members.length === 1 && data && typeof data.dpsRatio === "object") {
        ratioObj = data.dpsRatio;
      }
      if (members[i].ratioEl) {
        members[i].ratioEl.innerHTML = _renderDpsRatio(r.character ?? members[i].character, ratioObj);
      }
    });

    const debugObj = data?.Debug ?? data?.DebugMessage;
    let debugBlock = "";
    if (debugObj && typeof debugObj === "object") {
      const pretty = JSON.stringify(debugObj, null, 2);
      const lines = String(pretty).split("\n").map(l => `  ${l}`).join("\n");
      debugBlock = `\n\nDebug:\n${lines}`;
    } else if (typeof debugObj === "string" && debugObj.trim() !== "") {
      debugBlock = `\n\nDebug:\n  ${debugObj.trim()}`;
    }

    const partyLog = (data.members ?? []).map(m => {
      const name = (state.CHARACTERS.find(c => String(c.id) === String(m.character))?.name) ?? m.character;
      const dps = Number(m.dps ?? 0);
      const share = (total > 0) ? (dps / total) * 100 : 0;

      const extraParts = [];
      for (const [k, label] of Object.entries(EXTRA_KEY_LABEL)) {
        const v = m?.[k];
        if (v === undefined || v === null) continue;
        extraParts.push(`${label}=${v}`);
      }
const runePart = (m?.runeName && m.runeName !== "なし")
  ? ` | ルーン=${m.runeName}(${m.runeRarity ?? "なし"})`
  : "";
const extra = extraParts.length ? ` | ${extraParts.join(" | ")}` : "";
return `  - ${name} | dps=${Math.round(dps).toLocaleString("ja-JP")} | share=${share.toFixed(3)}%${runePart}${extra}`;

    }).join("\n");

    const totalStr = Math.round(total).toLocaleString("ja-JP");

    el.log.textContent =
`options(common):
  enemy            = ${options.enemy}
  durationSec      = ${options.durationSec}
  allRelicLv       = ${options.allRelicLv}
  mythEnhanceLv    = ${options.mythEnhanceLv}
  atkBuffPct       = ${options.atkBuffPct}%
  manaRegenBuffPct = ${options.manaRegenBuffPct}%
  speedBuffPct     = ${options.speedBuffPct}%
  defDown          = ${options.defDown}
  coins            = ${options.coins}
  trials           = ${options.trials}
  seed             = ${options.seed}
  multiplier       = ${options.multiplier}

party(per character):
${partyLog}
${debugBlock}

total(add) = ${totalStr}

result:
  total(add) = ${totalStr}`;
  } catch (e) {
    el.log.textContent = String(e);
  } finally {
    setBusy(false);
  }
}

