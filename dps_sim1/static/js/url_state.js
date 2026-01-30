import { el, RELIC_KEYS } from "./dom.js";
import { bytesToB64Url, b64UrlToBytes } from "./utils.js";

export const OTHER_DEFAULTS = {
  guildBlessing: "1",
  unitLevelSumBuff: "0",
  petLevelSum: "hoge",
};

export const PET_LEVEL_SUM_VALUES = ["hoge", "fuga", "piyo"];

// --- relic pack/unpack (12 values, each 1..11 => 4bit store level-1) ---
function clampRelicLv(v) {
  v = Number(v);
  if (!Number.isFinite(v)) return 1;
  return Math.max(1, Math.min(11, Math.trunc(v)));
}

function getRelicLevelsFromUI() {
  return RELIC_KEYS.map(k => clampRelicLv(el[k]?.value ?? 1));
}

function setRelicLevelsToUI(levels) {
  if (!Array.isArray(levels) || levels.length !== RELIC_KEYS.length) return;
  RELIC_KEYS.forEach((k, i) => {
    const node = el[k];
    if (!node) return;
    node.value = String(clampRelicLv(levels[i]));
  });
}

function packRelicLevels(levels) {
  let n = 0n;
  for (let i = 0; i < 12; i++) {
    const lv = clampRelicLv(levels[i] ?? 1);
    const v = BigInt((lv - 1) & 0x0f);
    const shift = BigInt((11 - i) * 4);
    n |= (v << shift);
  }
  const bytes = new Uint8Array(6);
  for (let i = 0; i < 6; i++) {
    const shift = BigInt((5 - i) * 8);
    bytes[i] = Number((n >> shift) & 0xffn);
  }
  return bytesToB64Url(bytes);
}

function unpackRelicLevels(rStr) {
  const bytes = b64UrlToBytes(rStr);
  if (bytes.length !== 6) return null;
  let n = 0n;
  for (let i = 0; i < 6; i++) n = (n << 8n) | BigInt(bytes[i]);

  const levels = [];
  for (let i = 0; i < 12; i++) {
    const shift = BigInt((11 - i) * 4);
    const v = Number((n >> shift) & 0x0fn);
    levels.push(clampRelicLv(v + 1));
  }
  return levels;
}

function parseRelicParam(r) {
  if (!r) return null;

  if (String(r).length === 1) {
    const lv = parseInt(r, 36);
    if (Number.isFinite(lv) && lv >= 1 && lv <= 11) {
      return Array(RELIC_KEYS.length).fill(lv);
    }
    return null;
  }

  try {
    return unpackRelicLevels(r);
  } catch {
    return null;
  }
}

// --- other buffs pack/unpack ---
function getOtherBuffsFromUI() {
  return {
    guildBlessing: String(el.guildBlessing?.value ?? OTHER_DEFAULTS.guildBlessing),
    unitLevelSumBuff: String(el.unitLevelSumBuff?.value ?? OTHER_DEFAULTS.unitLevelSumBuff),
    petLevelSum: String(el.petLevelSum?.value ?? OTHER_DEFAULTS.petLevelSum),
  };
}

function packOtherBuffs(other) {
  const g = Math.max(0, Math.min(3, Number(other.guildBlessing ?? OTHER_DEFAULTS.guildBlessing) | 0));
  const u2 = Math.max(0, Math.min(50, Math.round(Number(other.unitLevelSumBuff ?? 0) * 2)));
  const pIdxRaw = PET_LEVEL_SUM_VALUES.indexOf(String(other.petLevelSum ?? OTHER_DEFAULTS.petLevelSum));
  const p = (pIdxRaw >= 0 ? pIdxRaw : 0) & 3;

  const n = ((g & 3) << 8) | ((u2 & 63) << 2) | (p & 3);
  return n.toString(36);
}

function unpackOtherBuffs(oStr) {
  const n = parseInt(oStr, 36);
  if (!Number.isFinite(n)) return null;

  const g = (n >> 8) & 3;
  const u2 = (n >> 2) & 63;
  const p = n & 3;

  const val = u2 / 2;
  const unitLevelSumBuff =
    (u2 === 0) ? "0" :
    (u2 % 2 === 0) ? val.toFixed(1) : String(val);

  return {
    guildBlessing: String(g),
    unitLevelSumBuff,
    petLevelSum: PET_LEVEL_SUM_VALUES[p] ?? OTHER_DEFAULTS.petLevelSum,
  };
}

// --- apply from URL ---
export function applyStateFromUrl() {
  const params = new URLSearchParams(location.search);
  let appliedRelic = false;
  let appliedOther = false;

  const r = params.get("r");
  const relicLevels = parseRelicParam(r);
  if (relicLevels) {
    setRelicLevelsToUI(relicLevels);
    appliedRelic = true;

    const allSame = relicLevels.every(v => v === relicLevels[0]);
    if (allSame && el.allRelicLv) el.allRelicLv.value = String(relicLevels[0]);
  }

  const o = params.get("o");
  if (o) {
    const st = unpackOtherBuffs(o);
    if (st) {
      if (el.guildBlessing) el.guildBlessing.value = st.guildBlessing;
      if (el.unitLevelSumBuff) el.unitLevelSumBuff.value = st.unitLevelSumBuff;
      if (el.petLevelSum) el.petLevelSum.value = st.petLevelSum;
      appliedOther = true;
    }
  }

  return { appliedRelic, appliedOther };
}

export function persistStateToUrl() {
  const params = new URLSearchParams(location.search);

  // relics
  const levels = getRelicLevelsFromUI();
  const allDefaultRelic = levels.every(v => v === 1);
  if (allDefaultRelic) {
    params.delete("r");
  } else {
    const allSame = levels.every(v => v === levels[0]);
    const rVal = allSame ? levels[0].toString(36) : packRelicLevels(levels);
    params.set("r", rVal);
  }

  // other buffs
  const other = getOtherBuffsFromUI();
  const otherIsDefault =
    String(other.guildBlessing) === OTHER_DEFAULTS.guildBlessing &&
    Number(other.unitLevelSumBuff) === Number(OTHER_DEFAULTS.unitLevelSumBuff) &&
    String(other.petLevelSum) === OTHER_DEFAULTS.petLevelSum;

  if (otherIsDefault) {
    params.delete("o");
  } else {
    params.set("o", packOtherBuffs(other));
  }

  const qs = params.toString();
  const newUrl = qs ? `${location.pathname}?${qs}${location.hash}` : `${location.pathname}${location.hash}`;
  const curUrl = `${location.pathname}${location.search}${location.hash}`;
  if (newUrl !== curUrl) history.replaceState(null, "", newUrl);
}

