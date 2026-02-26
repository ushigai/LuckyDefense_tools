import { el } from "./dom.js";
import { fmtNumber } from "./utils.js";
import { computeViaPython } from "./api.js";
import { collectOptions } from "./options.js";
import { getPartyMembers } from "./party_ui.js";
import { updateEnemyHpUI } from "./enemy_ui.js";
import { state } from "./state.js";
import { t, translateGameText } from "./i18n.js";

function setBusy(isBusy) {
  el.btnCalc.disabled = isBusy;
  el.calcStatus.textContent = isBusy ? t("calculatingStatus", "計算中…") : "";
  el.btnCalc.innerHTML = isBusy
    ? `<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>${t("calculating", "計算中")}`
    : `<i class="bi bi-cpu me-1"></i>${t("calculate", "計算する")}`;
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
    return `<div class="text-secondary small">${t("breakdown", "内訳")}: —</div>`;
  }

  const items = [];

  // basic is always shown
  items.push({ key: "basic", label: t("basicAttack", "基本攻撃"), value: Number(ratioObj.basic ?? 0) });

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
    const safeLabel = translateGameText(String(it.label ?? it.key));
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

function _fmtFormulaNum(x, digits = 6) {
  const n = Number(x);
  if (!Number.isFinite(n)) return "—";
  return new Intl.NumberFormat("ja-JP", { maximumFractionDigits: digits }).format(n);
}

function _fmtFormulaNumRaw(x) {
  const n = Number(x);
  if (!Number.isFinite(n)) return "—";
  const s = n.toFixed(6).replace(/\.?0+$/, "");
  return s === "-0" ? "0" : s;
}

function _slotLabel(characterId, slotKey) {
  const ch = _getCharacterById(characterId) ?? {};
  if (slotKey === "basic") return t("basicAttack", "基本攻撃");
  if (slotKey === "ult") return String(ch.ult ?? "").trim() || "ult";
  if (slotKey === "skill1") return String(ch.skill1 ?? "").trim() || "skill1";
  if (slotKey === "skill2") return String(ch.skill2 ?? "").trim() || "skill2";
  if (slotKey === "skill3") return String(ch.skill3 ?? "").trim() || "skill3";
  return slotKey;
}

function _shouldShowOneFormula(characterId, slotKey, oneValue) {
  if (slotKey === "basic") return true;
  if (Number.isFinite(oneValue) && Math.abs(oneValue) > 0) return true;
  const ch = _getCharacterById(characterId) ?? {};
  if (slotKey === "ult") return String(ch.ult ?? "").trim() !== "";
  const label = _slotLabel(characterId, slotKey);
  return label !== "" && label !== slotKey;
}

function _renderFormulaParts(parts) {
  if (!parts || typeof parts !== "object") return "";
  const numbers = Array.isArray(parts.numbers) ? parts.numbers.filter(v => Number.isFinite(Number(v))) : [];
  const buffs = (parts.buffs && typeof parts.buffs === "object") ? parts.buffs : {};

  const numberChips = numbers.map((v, i) => (
    `<span class="formula-log-chip">numbers[${i}] = ${_escHtml(_fmtFormulaNumRaw(v))}</span>`
  )).join("");

  const buffChips = Object.entries(buffs).map(([k, v]) => (
    `<span class="formula-log-chip">${_escHtml(k)} = ${_escHtml(_fmtFormulaNumRaw(v))}</span>`
  )).join("");

  if (!numberChips && !buffChips) return "";

  return `
    <div class="formula-log-sub mt-1">
      <div class="mb-1">${t("formulaCoeffParts", "係数構成 (mult_parts)")}</div>
      <div>${numberChips || `<span class="text-secondary">${t("none", "なし")}</span>`}</div>
      <div class="mt-1">${buffChips || `<span class="text-secondary">${t("none", "なし")}</span>`}</div>
    </div>
  `;
}

function _renderOneFormulaRow(characterId, debugEntry, slotKey) {
  const oneKey = `${slotKey}_one`;
  const oneValue = Number(debugEntry?.[oneKey] ?? 0);
  if (!_shouldShowOneFormula(characterId, slotKey, oneValue)) return "";

  const atk = Number(debugEntry?.atk ?? NaN);
  const coeff = (Number.isFinite(atk) && Math.abs(atk) > 0) ? (oneValue / atk) : NaN;
  const label = translateGameText(_slotLabel(characterId, slotKey));
  const parts = debugEntry?.mult_parts?.[slotKey];

  let expr;
  if (Number.isFinite(atk) && Math.abs(atk) > 0) {
    expr = `${oneKey} = atk × coeff = ${_fmtFormulaNum(atk)} × ${_fmtFormulaNum(coeff)} = ${_fmtFormulaNum(oneValue)}`;
  } else {
    expr = `${oneKey} = ${_fmtFormulaNum(oneValue)}`;
  }

  return `
    <div class="mb-2">
      <div class="d-flex justify-content-between align-items-start gap-2">
        <div class="small text-secondary">${_escHtml(label)}</div>
        <div class="small text-secondary">${_escHtml(oneKey)}</div>
      </div>
      <div class="formula-log-line">${_escHtml(expr)}</div>
      ${_renderFormulaParts(parts)}
    </div>
  `;
}

function _pickDebugEntry(debugObj, resultMember, index) {
  if (!debugObj || typeof debugObj !== "object") return null;
  const characterId = String(resultMember?.character ?? "");
  const ch = _getCharacterById(characterId);
  const debugKeyByName = String(ch?.name ?? "");
  if (debugKeyByName && debugObj[debugKeyByName] && typeof debugObj[debugKeyByName] === "object") {
    return debugObj[debugKeyByName];
  }
  const entries = Object.values(debugObj).filter(v => v && typeof v === "object");
  return entries[index] ?? null;
}

function _renderOneDamageFormulaLog(data, fallbackMembers) {
  const debugObj = data?.Debug ?? data?.DebugMessage;
  if (!debugObj || typeof debugObj !== "object") return "";

  const resultMembers = Array.isArray(data?.members) && data.members.length > 0
    ? data.members
    : (Array.isArray(fallbackMembers) ? fallbackMembers : []);

  if (!Array.isArray(resultMembers) || resultMembers.length === 0) return "";

  const blocks = resultMembers.map((r, i) => {
    const characterId = String(r?.character ?? fallbackMembers?.[i]?.character ?? "");
    const ch = _getCharacterById(characterId) ?? {};
    const debugEntry = _pickDebugEntry(debugObj, { character: characterId }, i);
    if (!debugEntry || typeof debugEntry !== "object") return "";

    const charName = translateGameText(String(ch.name ?? characterId));
    const headerMeta = [
      characterId ? `ID ${characterId}` : "",
      (r?.charLv != null) ? `Lv ${r.charLv}` : "",
      (r?.treasureLv != null) ? `専用財宝 Lv ${r.treasureLv}` : "",
    ].filter(Boolean).join(" / ");

    const statChips = [
      ["base_atk", debugEntry?.base_atk],
      ["atk", debugEntry?.atk],
      ["base_speed", debugEntry?.base_speed],
      ["speed", debugEntry?.speed],
      ["ult_mana", debugEntry?.ult_mana],
    ].filter(([, v]) => Number.isFinite(Number(v)))
      .map(([k, v]) => `<span class="formula-log-chip">${_escHtml(k)} = ${_escHtml(_fmtFormulaNumRaw(v))}</span>`)
      .join("");

    const rows = ["basic", "skill1", "skill2", "skill3", "ult"]
      .map(slot => _renderOneFormulaRow(characterId, debugEntry, slot))
      .join("");

    const critParts = [];
    const critRateParts = debugEntry?.mult_parts?.crit_rate;
    const critDmgParts = debugEntry?.mult_parts?.crit_dmg;
    if (critRateParts && typeof critRateParts === "object") {
      const chips = _renderFormulaParts(critRateParts);
      if (chips) {
        critParts.push(`
          <div class="mt-2">
            <div class="small text-secondary mb-1">${t("critRateRef", "会心率の構成値 (参考)")}</div>
            ${chips}
          </div>
        `);
      }
    }
    if (critDmgParts && typeof critDmgParts === "object") {
      const chips = _renderFormulaParts(critDmgParts);
      if (chips) {
        critParts.push(`
          <div class="mt-2">
            <div class="small text-secondary mb-1">${t("critDmgRef", "会心ダメの構成値 (参考)")}</div>
            ${chips}
          </div>
        `);
      }
    }

    return `
      <div class="card formula-log-card rounded-3 mb-2">
        <div class="card-body py-2 px-3">
          <div class="d-flex flex-wrap justify-content-between align-items-center gap-2 mb-2">
            <div class="fw-semibold small">${_escHtml(charName)}</div>
            <div class="text-secondary small">${_escHtml(headerMeta)}</div>
          </div>
          <div class="mb-2">${statChips}</div>
          ${rows || `<div class="text-secondary small">${t("noFormulaData", "式データなし")}</div>`}
          ${critParts.join("")}
        </div>
      </div>
    `;
  }).join("");

  if (!blocks) return "";
  return `
    <div class="mb-2">
      <div class="small fw-semibold mb-2">${t("oneDamageFormulaTitle", "1回分ダメージ式 (*_one)")}</div>
      <div class="small text-secondary mb-2">${t("oneDamageFormulaNote", "※ 行ごとの式は *_one の正確な数値式です。下の chips は backend の mult_parts（キャラ別係数構成値）をそのまま表示しています。")}</div>
      ${blocks}
    </div>
  `;
}

function readBlobFigures() {
  const out = [];
  for (let i = 1; i <= 5; i++) {
    const name = document.getElementById(`blobFigureName${i}`)?.value ?? "";
    if (!name) continue; // なし

    const v = document.getElementById(`blobFigureValue${i}`)?.value ?? "";
    const value = Number(v);
    if (!Number.isFinite(value)) continue;

    out.push({ name, value });
  }
  return out;
}


export async function recalc() {
  const options = collectOptions();
  options.blobFigures = readBlobFigures();
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
    updateEnemyHpUI(total, options);

    (data.members ?? []).forEach((r, i) => {
      const dps = Number(r.dps ?? 0);
      members[i].dpsEl.textContent = fmtNumber(dps);

      const share = (total > 0) ? (dps / total) * 100 : (100 / members.length);
      members[i].shareEl.textContent = `${t("share", "share")}: ${share.toFixed(3)}%`;

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
    if (el.logFormula) {
      el.logFormula.innerHTML = _renderOneDamageFormulaLog(data, members);
    }
    if (debugObj && typeof debugObj === "object") {
      el.log.textContent = `Debug:\n${JSON.stringify(debugObj, null, 2)}`;
    } else if (typeof debugObj === "string" && debugObj.trim() !== "") {
      el.log.textContent = `Debug:\n${debugObj.trim()}`;
    } else {
      el.log.textContent = "—";
    }
  } catch (e) {
    if (el.logFormula) el.logFormula.innerHTML = "";
    el.log.textContent = String(e);
  } finally {
    setBusy(false);
  }
}
