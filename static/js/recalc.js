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

