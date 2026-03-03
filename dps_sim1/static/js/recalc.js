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

function _getMemberRatio(data, memberRows, index) {
  const row = Array.isArray(data?.members) ? data.members[index] : null;
  if (row && row.dpsRatio && typeof row.dpsRatio === "object") {
    return row.dpsRatio;
  }
  if (Array.isArray(data?.dpsRatio) && data.dpsRatio[index] && typeof data.dpsRatio[index] === "object") {
    return data.dpsRatio[index];
  }
  if (Array.isArray(memberRows) && memberRows.length === 1 && data && !Array.isArray(data.dpsRatio) && typeof data.dpsRatio === "object") {
    return data.dpsRatio;
  }
  return null;
}

function _getActionMeta(characterId, slotKey) {
  const ch = _getCharacterById(characterId) ?? {};
  const meta = (ch.actionMeta && typeof ch.actionMeta === "object") ? ch.actionMeta : {};
  const slotMeta = meta?.[slotKey];
  if (slotMeta && typeof slotMeta === "object") return slotMeta;
  if (slotKey === "basic") {
    return { damageType: "physical", targetType: "single" };
  }
  return null;
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

function _computeCategorizedDamage(data, memberRows) {
  const membersData = Array.isArray(data?.members) ? data.members : [];
  if (membersData.length === 0) {
    return {
      physical: 0,
      magic: 0,
      single: 0,
      aoe: 0,
    };
  }

  const slotKeys = ["basic", "skill1", "skill2", "skill3", "ult"];
  const sums = {
    physical: 0,
    magic: 0,
    single: 0,
    aoe: 0,
  };

  membersData.forEach((row, index) => {
    const memberDps = Number(row?.dps ?? 0);
    if (!Number.isFinite(memberDps) || memberDps <= 0) return;

    const ratioObj = _getMemberRatio(data, memberRows, index);
    if (!ratioObj || typeof ratioObj !== "object") return;

    const ratioTotal = slotKeys.reduce((acc, key) => {
      const value = Number(ratioObj?.[key] ?? 0);
      return acc + (Number.isFinite(value) ? Math.max(0, value) : 0);
    }, 0);
    if (!(ratioTotal > 0)) return;

    const characterId = row?.character ?? memberRows?.[index]?.character;
    slotKeys.forEach(slotKey => {
      const rawValue = Number(ratioObj?.[slotKey] ?? 0);
      if (!Number.isFinite(rawValue) || rawValue <= 0) return;

      const slotMeta = _getActionMeta(characterId, slotKey);
      if (!slotMeta) return;

      const allocatedDps = memberDps * rawValue / ratioTotal;
      if (!Number.isFinite(allocatedDps) || allocatedDps <= 0) return;

      if (slotMeta.damageType === "physical") sums.physical += allocatedDps;
      if (slotMeta.damageType === "magic") sums.magic += allocatedDps;
      if (slotMeta.targetType === "single") sums.single += allocatedDps;
      if (slotMeta.targetType === "aoe") sums.aoe += allocatedDps;
    });
  });

  return sums;
}

function _renderTotalBreakdown(data, memberRows) {
  const membersData = Array.isArray(data?.members) ? data.members : [];
  const sums = _computeCategorizedDamage(data, memberRows);

  const fallbackTotal = membersData.reduce((acc, row) => {
    const value = Number(row?.dps ?? 0);
    return acc + (Number.isFinite(value) ? value : 0);
  }, 0);
  const total = Number(data?.totalDps ?? fallbackTotal);
  const safeTotal = (Number.isFinite(total) && total > 0) ? total : 0;
  if (!(safeTotal > 0)) {
    return `<div class="small text-secondary">${t("breakdown", "内訳")}: —</div>`;
  }

  const items = [
    { label: t("physicalDamage", "物理"), value: sums.physical },
    { label: t("magicDamage", "魔法"), value: sums.magic },
    { label: t("singleDamage", "単体"), value: sums.single },
    { label: t("aoeDamage", "複数"), value: sums.aoe },
  ];

  const blocks = items.map(item => {
    const value = Number.isFinite(item.value) ? item.value : 0;
    const pct = safeTotal > 0 ? (value / safeTotal) * 100 : 0;
    return `
      <div class="col-6">
        <div class="rounded-3 border px-2 py-2 h-100 bg-white bg-opacity-50">
          <div class="small text-secondary">${_escHtml(item.label)}</div>
          <div class="small fw-semibold metric">${_escHtml(fmtNumber(Math.round(value)))}</div>
          <div class="small text-secondary">${_escHtml(_formatPct(pct))}%</div>
        </div>
      </div>
    `;
  }).join("");

  return `
    <div class="small text-secondary mb-1">${t("categorizedDamage", "区分別合計")}</div>
    <div class="row g-2">
      ${blocks}
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

function _formatFormulaPartsInline(parts) {
  if (!parts || typeof parts !== "object") return "";
  const numbers = Array.isArray(parts.numbers)
    ? parts.numbers.map(v => Number(v)).filter(Number.isFinite)
    : [];
  const buffEntries = (parts.buffs && typeof parts.buffs === "object")
    ? Object.entries(parts.buffs)
        .map(([k, v]) => [String(k), Number(v)])
        .filter(([, v]) => Number.isFinite(v))
    : [];

  if (numbers.length === 0 && buffEntries.length === 0) return "";

  const numbersText = `numbers=[${numbers.map(v => _fmtFormulaNumRaw(v)).join(", ")}]`;
  const buffsText = `buffs={${buffEntries.map(([k, v]) => `${k}=${_fmtFormulaNumRaw(v)}`).join(", ")}}`;
  return `${numbersText}, ${buffsText}`;
}

function _approxEqual(a, b) {
  if (!Number.isFinite(a) || !Number.isFinite(b)) return false;
  const scale = Math.max(1, Math.abs(a), Math.abs(b));
  return Math.abs(a - b) <= scale * 1e-9;
}

function _buildCoeffDetailFromMultParts(parts, coeffActual) {
  if (!parts || typeof parts !== "object") return { exact: null, lines: [] };
  const numbers = Array.isArray(parts.numbers)
    ? parts.numbers.map(v => Number(v)).filter(Number.isFinite)
    : [];
  const buffEntries = (parts.buffs && typeof parts.buffs === "object")
    ? Object.entries(parts.buffs)
        .map(([k, v]) => [String(k), Number(v)])
        .filter(([, v]) => Number.isFinite(v))
    : [];

  if (numbers.length === 0 && buffEntries.length === 0) return { exact: null, lines: [] };

  const buffKeys = buffEntries.map(([k]) => k);
  const buffVals = buffEntries.map(([, v]) => v);
  const sumNumbers = numbers.reduce((a, b) => a + b, 0);
  const sumBuffs = buffVals.reduce((a, b) => a + b, 0);
  const symBuffSum = buffKeys.join(" + ");
  const numBuffSum = buffVals.map(v => _fmtFormulaNum(v)).join(" + ");

  const candidates = [];
  if (numbers.length > 0 && buffEntries.length === 0) {
    const symExpr = numbers.length === 1
      ? _fmtFormulaNumRaw(numbers[0])
      : `(${numbers.map(v => _fmtFormulaNumRaw(v)).join(" + ")})`;
    const numExpr = numbers.length === 1
      ? _fmtFormulaNum(numbers[0])
      : `(${numbers.map(v => _fmtFormulaNum(v)).join(" + ")})`;
    candidates.push({ symExpr, numExpr, value: sumNumbers });
  }
  if (numbers.length === 0 && buffEntries.length > 0) {
    const symExpr = buffEntries.length === 1 ? symBuffSum : `(${symBuffSum})`;
    const numExpr = buffEntries.length === 1 ? numBuffSum : `(${numBuffSum})`;
    candidates.push({ symExpr, numExpr, value: sumBuffs });
  }
  if (numbers.length > 0 && buffEntries.length > 0) {
    for (const n of numbers) {
      candidates.push({
        symExpr: `${_fmtFormulaNumRaw(n)} * (${symBuffSum})`,
        numExpr: `${_fmtFormulaNum(n)} * (${numBuffSum})`,
        value: n * sumBuffs,
      });
    }
    candidates.push({
      symExpr: `(${numbers.map(v => _fmtFormulaNumRaw(v)).join(" + ")}) * (${symBuffSum})`,
      numExpr: `(${numbers.map(v => _fmtFormulaNum(v)).join(" + ")}) * (${numBuffSum})`,
      value: sumNumbers * sumBuffs,
    });
  }

  if (Number.isFinite(coeffActual)) {
    const exact = candidates.find(c => _approxEqual(c.value, coeffActual));
    if (exact) {
      return { exact, lines: [] };
    }
  }

  const fallback = _formatFormulaPartsInline(parts);
  return { exact: null, lines: fallback ? [`mult_parts (参考): ${fallback}`] : [] };
}

function _lvAtkBuff(charLv) {
  const lv = Number(charLv);
  if (!Number.isFinite(lv)) return 1.0;
  if (lv < 3) return 1.0;
  if (lv < 9) return 1.1;
  if (lv < 15) return 1.1;
  return 1.2;
}

function _renderAtkFormula(characterId, resultMember, debugEntry, options) {
  const meta = (debugEntry?.atk_formula_meta && typeof debugEntry.atk_formula_meta === "object")
    ? debugEntry.atk_formula_meta
    : null;
  if (!meta) return "";

  const ch = _getCharacterById(characterId) ?? {};
  const charLv = Number(resultMember?.charLv ?? NaN);
  const lv1Atk = Number(ch.attack_damage ?? NaN);
  const upgradeAtk = Number(ch.upgrade_attack_damage ?? NaN);
  const baseAtk = Number(debugEntry?.base_atk ?? NaN);
  const atkFinal = Number(debugEntry?.atk ?? NaN);
  if (![charLv, lv1Atk, upgradeAtk, baseAtk, atkFinal].every(Number.isFinite)) return "";

  const lvBuffAtk = _lvAtkBuff(charLv);

  const opt = (options && typeof options === "object") ? options : {};
  const mythEnhanceLv = Number(opt.mythEnhanceLv ?? 1);
  const coins = Number(opt.coins ?? 0);
  const unitLevelSumBuff = Number(opt.unitLevelSumBuff ?? 0) / 100;
  const atkBuffPctInput = Number(opt.atkBuffPct ?? 0) / 100;
  const guildBlessing = Number(opt.guildBlessing ?? 0);
  const guildBuffAtk = guildBlessing >= 1 ? 0.02 : 0;

  const variant = String(meta.variant ?? "standard");
  const powerPotion = Number(meta.PowerPotion ?? NaN);
  const moneyGun = Number(meta.MoneyGun ?? NaN);
  if (![powerPotion, moneyGun].every(Number.isFinite)) return "";

  const atkBuffPctAutoBonus = Number(meta.atkBuffPct_auto_bonus ?? 0);
  const atkBuffPctTotal = atkBuffPctInput + atkBuffPctAutoBonus;
  const runeAtkSum = Number(meta.RuneAtkSum ?? 0);
  const batEnh = Number(meta.batEnh ?? 0);
  const emotion = Number(meta.emotion ?? 0);
  const aceEnh = Number(meta.aceEnh ?? 0);
  const veinBonus = Number(meta.veinBonus ?? 0);

  const intake = Number(resultMember?.intake ?? 0);
  const cannibalCount = Number(resultMember?.cannibalCount ?? 0);
  const starPower = Number(resultMember?.starPower ?? 0);
  const starPowerMult = charLv < 6 ? 2 : 4;

  const blobDiamond = Number(debugEntry?.blobFigures?.["ダイヤ"] ?? 0);
  const petAtkBuff = Number(debugEntry?.pet_buff?.AttackDamage ?? 0);
  const strongestCreature = Number(debugEntry?.StrongestCreature ?? 0);
  const mythTerm = 0.5 * ((Number.isFinite(mythEnhanceLv) ? mythEnhanceLv : 1) - 1);
  const moneyGunTerm = coins * moneyGun / 100;

  const isHayleyVariant = variant === "hayley_5021_star_power";
  const startTerms = isHayleyVariant ? { base_atk: baseAtk } : { base_atk: baseAtk, intake };
  const whiteTextAttackLabel = "WhiteTextAttack";
  const greenTextAttackLabel = "GreenTextAttack";
  const startExpr = isHayleyVariant ? whiteTextAttackLabel : `${whiteTextAttackLabel} + intake`;

  const groups = isHayleyVariant
    ? [
        {
          label: "artifact+party",
          expr: "2*PowerPotion + unitLevelSumBuff",
          terms: {
            "2*PowerPotion": powerPotion * 2,
            unitLevelSumBuff,
          },
        },
        {
          label: "myth",
          expr: "0.5*(mythEnhanceLv - 1)",
          terms: {
            "0.5*(mythEnhanceLv - 1)": mythTerm,
          },
        },
        {
          label: "coin+atkBuff+starPower",
          expr: "atkBuffPct + coins*MoneyGun/100 + starPower*starPower_mult",
          terms: {
            atkBuffPct: atkBuffPctTotal,
            "coins*MoneyGun/100": moneyGunTerm,
            "starPower*starPower_mult": starPower * starPowerMult,
          },
        },
      ]
    : [
        {
          label: "artifact+party+rune+blob+pet",
          expr: '2*PowerPotion + Blob["ダイヤ"] + RuneAtkSum + cannibalCount + pet_buff["AttackDamage"] + unitLevelSumBuff',
          terms: {
            "2*PowerPotion": powerPotion * 2,
            'Blob["ダイヤ"]': blobDiamond,
            RuneAtkSum: runeAtkSum,
            cannibalCount,
            'pet_buff["AttackDamage"]': petAtkBuff,
            unitLevelSumBuff,
          },
        },
        {
          label: "myth+vein",
          expr: "0.5*(mythEnhanceLv - 1) + ヴェイン",
          terms: {
            "0.5*(mythEnhanceLv - 1)": mythTerm,
            "ヴェイン": veinBonus,
          },
        },
        {
          label: "coin+atkBuff+character+etc",
          expr: "StrongestCreature + aceEnh + atkBuffPct + batEnh + coins*MoneyGun/100 + emotion",
          terms: {
            StrongestCreature: strongestCreature,
            aceEnh,
            atkBuffPct: atkBuffPctTotal,
            batEnh,
            "coins*MoneyGun/100": moneyGunTerm,
            emotion,
          },
        },
      ];

  const note = isHayleyVariant
    ? "Hayley (5021) はこの分岐で atk を再計算します（intake/cannibal/rune/blob/pet攻撃バフを使わない）"
    : "";

  const startResult = Object.values(startTerms).reduce((sum, v) => {
    const n = Number(v);
    return sum + (Number.isFinite(n) ? n : 0);
  }, 0);
  const startNumericExpr = isHayleyVariant
    ? _fmtFormulaNum(baseAtk)
    : `${_fmtFormulaNum(baseAtk)} + ${_fmtFormulaNum(intake)}`;

  const lines = [];
  lines.push(`${whiteTextAttackLabel} = (lv1_atk + (char_lv - 1) * upgrade_atk) * lv_buff_atk = (${_fmtFormulaNum(lv1Atk)} + (${_fmtFormulaNum(charLv)} - 1) * ${_fmtFormulaNum(upgradeAtk)}) * ${_fmtFormulaNum(lvBuffAtk)} = ${_fmtFormulaNum(baseAtk)}`);
  lines.push(`atk0 = ${startExpr} = ${startNumericExpr} = ${_fmtFormulaNum(startResult)}`);

  let prevLabel = "atk0";
  let prevAfter = startResult;
  groups.forEach((g, idx) => {
    const terms = (g?.terms && typeof g.terms === "object") ? g.terms : {};
    const termEntries = Object.entries(terms).filter(([, v]) => Number.isFinite(Number(v)));
    const termVals = termEntries.map(([, v]) => Number(v));
    const termsSum = termVals.reduce((a, b) => a + b, 0);
    const factor = 1 + termsSum;
    const after = prevAfter * factor;
    const nextLabel = `atk${idx + 1}`;
    const symbolic = String(g?.expr ?? "");
    lines.push(`${nextLabel} = ${prevLabel} * (1 + ${symbolic}) = ${_fmtFormulaNum(prevAfter)} * ${_fmtFormulaNum(factor)} = ${_fmtFormulaNum(after)}`);

    prevLabel = nextLabel;
    prevAfter = after;
  });

  const guildFactor = 1 + guildBuffAtk;
  const afterGuild = prevAfter * guildFactor;
  lines.push(`${greenTextAttackLabel} = ${prevLabel} * (1 + guildBuff_atk) = ${_fmtFormulaNum(prevAfter)} * ${_fmtFormulaNum(guildFactor)} = ${_fmtFormulaNum(afterGuild)}`);
  prevLabel = greenTextAttackLabel;
  prevAfter = afterGuild;

  lines.push(`atk = ${prevLabel} + ${whiteTextAttackLabel} = ${_fmtFormulaNum(prevAfter)} + ${_fmtFormulaNum(baseAtk)} = ${_fmtFormulaNum(atkFinal)}`);

  const linesHtml = lines.map(line => `<div class="formula-log-line">${_escHtml(line)}</div>`).join("");
  const noteHtml = note ? `<div class="formula-log-sub mt-1 text-secondary">${_escHtml(note)}</div>` : "";

  return `
    <div class="mb-3">
      <div class="small fw-semibold mb-2">${t("atkFormulaTitle", "atk 計算式")}</div>
      ${linesHtml}
      ${noteHtml}
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

  const coeffDetail = _buildCoeffDetailFromMultParts(parts, coeff);
  const exactCoeff = coeffDetail?.exact ?? null;

  let expr;
  if (Number.isFinite(atk) && Math.abs(atk) > 0 && exactCoeff) {
    expr = `${oneKey} = atk × ${exactCoeff.symExpr} = ${_fmtFormulaNum(atk)} × ${exactCoeff.numExpr} = ${_fmtFormulaNum(oneValue)}`;
  } else if (Number.isFinite(atk) && Math.abs(atk) > 0) {
    expr = `${oneKey} = atk × coeff = ${_fmtFormulaNum(atk)} × ${_fmtFormulaNum(coeff)} = ${_fmtFormulaNum(oneValue)}`;
  } else {
    expr = `${oneKey} = ${_fmtFormulaNum(oneValue)}`;
  }
  const detailLines = exactCoeff ? [] : (coeffDetail?.lines ?? []);
  const detailHtml = detailLines
    .map(line => `<div class="formula-log-line text-secondary small">${_escHtml(line)}</div>`)
    .join("");

  return `
    <div class="mb-2">
      <div class="d-flex justify-content-between align-items-start gap-2">
        <div class="small text-secondary">${_escHtml(label)}</div>
        <div class="small text-secondary">${_escHtml(oneKey)}</div>
      </div>
      <div class="formula-log-line">${_escHtml(expr)}</div>
      ${detailHtml}
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

function _renderOneDamageFormulaLog(data, fallbackMembers, options) {
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

    const atkFormulaBlock = _renderAtkFormula(characterId, r, debugEntry, options);
    const rows = ["basic", "skill1", "skill2", "skill3", "ult"]
      .map(slot => _renderOneFormulaRow(characterId, debugEntry, slot))
      .join("");

    const critParts = [];
    const critRateParts = debugEntry?.mult_parts?.crit_rate;
    const critDmgParts = debugEntry?.mult_parts?.crit_dmg;
    if (critRateParts && typeof critRateParts === "object") {
      const partsInline = _formatFormulaPartsInline(critRateParts);
      if (partsInline) {
        critParts.push(`
          <div class="formula-log-line text-secondary small mt-2">${_escHtml(`${t("critRateRef", "会心率の構成値 (参考)")}: ${partsInline}`)}</div>
        `);
      }
    }
    if (critDmgParts && typeof critDmgParts === "object") {
      const partsInline = _formatFormulaPartsInline(critDmgParts);
      if (partsInline) {
        critParts.push(`
          <div class="formula-log-line text-secondary small mt-1">${_escHtml(`${t("critDmgRef", "会心ダメの構成値 (参考)")}: ${partsInline}`)}</div>
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
          ${atkFormulaBlock}
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
      <div class="small text-secondary mb-2">${t("oneDamageFormulaNote", "※ 各キャラの先頭に atk の段階計算を表示します。行ごとの式は *_one の正確な数値式です。mult_parts / 会心の構成値は参考として1行に簡略表示しています。")}</div>
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
    const categorizedDamage = _computeCategorizedDamage(data, members);

    el.totalValue.textContent = fmtNumber(Math.round(total));
    if (el.totalBreakdown) {
      el.totalBreakdown.innerHTML = _renderTotalBreakdown(data, members);
    }
    updateEnemyHpUI(categorizedDamage, options);

    (data.members ?? []).forEach((r, i) => {
      const dps = Number(r.dps ?? 0);
      members[i].dpsEl.textContent = fmtNumber(dps);

      const share = (total > 0) ? (dps / total) * 100 : (100 / members.length);
      members[i].shareEl.textContent = `${t("share", "share")}: ${share.toFixed(3)}%`;

      // DPS 内訳（basic/skill/ult）
      const ratioObj = _getMemberRatio(data, members, i);
      if (members[i].ratioEl) {
        members[i].ratioEl.innerHTML = _renderDpsRatio(r.character ?? members[i].character, ratioObj);
      }
    });

    const debugObj = data?.Debug ?? data?.DebugMessage;
    if (el.logFormula) {
      el.logFormula.innerHTML = _renderOneDamageFormulaLog(data, members, options);
    }
    if (debugObj && typeof debugObj === "object") {
      el.log.textContent = `Debug:\n${JSON.stringify(debugObj, null, 2)}`;
    } else if (typeof debugObj === "string" && debugObj.trim() !== "") {
      el.log.textContent = `Debug:\n${debugObj.trim()}`;
    } else {
      el.log.textContent = "—";
    }
  } catch (e) {
    if (el.totalBreakdown) el.totalBreakdown.innerHTML = "";
    if (el.logFormula) el.logFormula.innerHTML = "";
    el.log.textContent = String(e);
  } finally {
    setBusy(false);
  }
}
