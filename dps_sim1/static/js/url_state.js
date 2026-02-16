import { el, RELIC_KEYS } from "./dom.js";
import { bytesToB64Url, b64UrlToBytes } from "./utils.js";
import { getExtraFieldsForCharacter } from "./extras.js";
import { getPartyMembers } from "./party_ui.js";

export const OTHER_DEFAULTS = {
  guildBlessing: "1",
  unitLevelSumBuff: "0",
  petLevelSum: "hoge",
};

export const MAIN_BUFF_DEFAULTS = {
  mythEnhanceLv: 1,
  atkBuffPct: 0,
  manaRegenBuffPct: 0,
  speedBuffPct: 0,
  defDown: 190,
  coins: 300000,
};

export const PET_LEVEL_SUM_VALUES = ["hoge", "fuga", "piyo"];
const MAIN_BUFF_PACK_VERSION = 2;
const MAIN_BUFF_PACK_VERSION_LEGACY = 1;
const PET_PACK_VERSION = 1;
const PET_ID_BASE = 61000;
const PET_SLOT_KEYS = [
  ["pet1", "pet1Level"],
  ["pet2", "pet2Level"],
  ["pet3", "pet3Level"],
];
const PARTY_PACK_VERSION = 1;
const MAX_PARTY_MEMBERS = 128;
const MAX_VARINT_BYTES = 10;

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

function clampInt(v, min, max, fallback) {
  const n = Number(v);
  if (!Number.isFinite(n)) return fallback;
  return Math.max(min, Math.min(max, Math.trunc(n)));
}

function clampFloat(v, min, max, fallback) {
  const n = Number(v);
  if (!Number.isFinite(n)) return fallback;
  return Math.max(min, Math.min(max, n));
}

function normalizeMainBuffs(raw = {}) {
  return {
    mythEnhanceLv: clampInt(raw.mythEnhanceLv, 0, 35, MAIN_BUFF_DEFAULTS.mythEnhanceLv),
    atkBuffPct: clampFloat(raw.atkBuffPct, -1000, 10000, MAIN_BUFF_DEFAULTS.atkBuffPct),
    manaRegenBuffPct: clampInt(raw.manaRegenBuffPct, 0, 700, MAIN_BUFF_DEFAULTS.manaRegenBuffPct),
    speedBuffPct: clampFloat(raw.speedBuffPct, -1000, 10000, MAIN_BUFF_DEFAULTS.speedBuffPct),
    defDown: clampFloat(raw.defDown, -10_000_000, 10_000_000, MAIN_BUFF_DEFAULTS.defDown),
    coins: clampInt(raw.coins, 0, 2_000_000_000, MAIN_BUFF_DEFAULTS.coins),
  };
}

function getMainBuffsFromUI() {
  return normalizeMainBuffs({
    mythEnhanceLv: el.mythEnhanceLv?.value,
    atkBuffPct: el.atkBuffPct?.value,
    manaRegenBuffPct: el.manaRegenBuffPct?.value,
    speedBuffPct: el.speedBuffPct?.value,
    defDown: el.defDown?.value,
    coins: el.coins?.value,
  });
}

function setMainBuffsToUI(main) {
  if (!main) return;
  if (el.mythEnhanceLv) el.mythEnhanceLv.value = String(main.mythEnhanceLv);
  if (el.atkBuffPct) el.atkBuffPct.value = String(main.atkBuffPct);
  if (el.manaRegenBuffPct) el.manaRegenBuffPct.value = String(main.manaRegenBuffPct);
  if (el.speedBuffPct) el.speedBuffPct.value = String(main.speedBuffPct);
  if (el.defDown) el.defDown.value = String(main.defDown);
  if (el.coins) el.coins.value = String(main.coins);
}

function packMainBuffsLegacy(main) {
  const st = normalizeMainBuffs(main);
  return [
    MAIN_BUFF_PACK_VERSION_LEGACY,
    st.mythEnhanceLv,
    st.atkBuffPct,
    st.manaRegenBuffPct,
    st.speedBuffPct,
    st.defDown,
    st.coins,
  ].join(",");
}

function unpackMainBuffsLegacy(mStr) {
  const parts = String(mStr ?? "").split(",");
  if (parts.length !== 7) return null;

  const version = Number(parts[0]);
  if (!Number.isFinite(version) || Math.trunc(version) !== MAIN_BUFF_PACK_VERSION_LEGACY) return null;

  return normalizeMainBuffs({
    mythEnhanceLv: parts[1],
    atkBuffPct: parts[2],
    manaRegenBuffPct: parts[3],
    speedBuffPct: parts[4],
    defDown: parts[5],
    coins: parts[6],
  });
}

function isIntegerValue(v) {
  return Number.isFinite(v) && Math.trunc(v) === v;
}

function packMainBuffs(main) {
  const st = normalizeMainBuffs(main);

  // Fractional values are rare in this UI. Keep backward-compatible text format for them.
  if (!isIntegerValue(st.atkBuffPct) || !isIntegerValue(st.speedBuffPct) || !isIntegerValue(st.defDown)) {
    return packMainBuffsLegacy(st);
  }

  const out = [];
  writeVarUint(out, MAIN_BUFF_PACK_VERSION);
  writeVarUint(out, encodeZigZag(st.mythEnhanceLv - MAIN_BUFF_DEFAULTS.mythEnhanceLv));
  writeVarUint(out, encodeZigZag(st.atkBuffPct - MAIN_BUFF_DEFAULTS.atkBuffPct));
  writeVarUint(out, encodeZigZag(st.manaRegenBuffPct - MAIN_BUFF_DEFAULTS.manaRegenBuffPct));
  writeVarUint(out, encodeZigZag(st.speedBuffPct - MAIN_BUFF_DEFAULTS.speedBuffPct));
  writeVarUint(out, encodeZigZag(st.defDown - MAIN_BUFF_DEFAULTS.defDown));
  writeVarUint(out, encodeZigZag(st.coins - MAIN_BUFF_DEFAULTS.coins));

  return bytesToB64Url(new Uint8Array(out));
}

function unpackMainBuffsBinary(mStr) {
  try {
    const bytes = b64UrlToBytes(String(mStr ?? ""));
    const cursor = { i: 0 };
    const versionRaw = readVarUint(bytes, cursor);
    const version = toSafeNumber(versionRaw, -1);
    if (version !== MAIN_BUFF_PACK_VERSION) return null;

    const dMythRaw = readVarUint(bytes, cursor);
    const dAtkRaw = readVarUint(bytes, cursor);
    const dManaRaw = readVarUint(bytes, cursor);
    const dSpeedRaw = readVarUint(bytes, cursor);
    const dDefRaw = readVarUint(bytes, cursor);
    const dCoinsRaw = readVarUint(bytes, cursor);
    if (
      dMythRaw === null ||
      dAtkRaw === null ||
      dManaRaw === null ||
      dSpeedRaw === null ||
      dDefRaw === null ||
      dCoinsRaw === null
    ) {
      return null;
    }

    if (cursor.i !== bytes.length) return null;

    return normalizeMainBuffs({
      mythEnhanceLv: MAIN_BUFF_DEFAULTS.mythEnhanceLv + toSafeNumber(decodeZigZag(dMythRaw), 0),
      atkBuffPct: MAIN_BUFF_DEFAULTS.atkBuffPct + toSafeNumber(decodeZigZag(dAtkRaw), 0),
      manaRegenBuffPct: MAIN_BUFF_DEFAULTS.manaRegenBuffPct + toSafeNumber(decodeZigZag(dManaRaw), 0),
      speedBuffPct: MAIN_BUFF_DEFAULTS.speedBuffPct + toSafeNumber(decodeZigZag(dSpeedRaw), 0),
      defDown: MAIN_BUFF_DEFAULTS.defDown + toSafeNumber(decodeZigZag(dDefRaw), 0),
      coins: MAIN_BUFF_DEFAULTS.coins + toSafeNumber(decodeZigZag(dCoinsRaw), 0),
    });
  } catch {
    return null;
  }
}

function unpackMainBuffs(mStr) {
  const raw = String(mStr ?? "");
  if (!raw) return null;
  if (raw.includes(",")) return unpackMainBuffsLegacy(raw);
  return unpackMainBuffsBinary(raw);
}

function normalizePetId(raw) {
  const s = String(raw ?? "").trim();
  if (!/^\d+$/.test(s)) return "";
  const id = Math.trunc(Number(s));
  if (!Number.isFinite(id) || id <= 0) return "";
  return String(id);
}

function clampPetLevel(v) {
  return clampInt(v, 1, 50, 1);
}

function getPetSlotsFromUI() {
  return PET_SLOT_KEYS.map(([petKey, levelKey]) => {
    const id = normalizePetId(el[petKey]?.value);
    if (!id) return null;
    return {
      id,
      level: clampPetLevel(el[levelKey]?.value),
    };
  });
}

function setPetSlotsToUI(slots) {
  if (!Array.isArray(slots) || slots.length !== PET_SLOT_KEYS.length) return;
  PET_SLOT_KEYS.forEach(([petKey, levelKey], i) => {
    const slot = slots[i];
    if (!slot?.id) {
      if (el[petKey]) el[petKey].value = "";
      if (el[petKey]) el[petKey].dispatchEvent(new Event("change", { bubbles: true }));
      return;
    }

    if (el[petKey]) el[petKey].value = String(slot.id);
    if (el[petKey]) el[petKey].dispatchEvent(new Event("change", { bubbles: true }));
    if (el[levelKey]) el[levelKey].value = String(clampPetLevel(slot.level));
  });
}

function packPetSlots(slots) {
  const normalized = PET_SLOT_KEYS.map((_, i) => {
    const slot = slots?.[i];
    if (!slot?.id) return null;
    const id = normalizePetId(slot.id);
    if (!id) return null;
    return {
      id,
      level: clampPetLevel(slot.level),
    };
  });

  const out = [];
  writeVarUint(out, PET_PACK_VERSION);

  let mask = 0;
  normalized.forEach((slot, i) => {
    if (slot?.id) mask |= (1 << i);
  });
  writeVarUint(out, mask);

  normalized.forEach(slot => {
    if (!slot?.id) return;
    const idNum = Math.trunc(Number(slot.id));
    writeVarUint(out, encodeZigZag(idNum - PET_ID_BASE));
    writeVarUint(out, slot.level - 1);
  });

  return bytesToB64Url(new Uint8Array(out));
}

function unpackPetSlots(tStr) {
  try {
    const bytes = b64UrlToBytes(String(tStr ?? ""));
    const cursor = { i: 0 };

    const versionRaw = readVarUint(bytes, cursor);
    const version = toSafeNumber(versionRaw, -1);
    if (version !== PET_PACK_VERSION) return null;

    const maskRaw = readVarUint(bytes, cursor);
    const mask = toSafeNumber(maskRaw, -1);
    if (!Number.isInteger(mask) || mask < 0 || mask > 0b111) return null;

    const slots = PET_SLOT_KEYS.map(() => null);
    for (let i = 0; i < PET_SLOT_KEYS.length; i++) {
      const present = (mask & (1 << i)) !== 0;
      if (!present) continue;

      const idDeltaRaw = readVarUint(bytes, cursor);
      const lvMinusOneRaw = readVarUint(bytes, cursor);
      if (idDeltaRaw === null || lvMinusOneRaw === null) return null;

      const idDelta = toSafeNumber(decodeZigZag(idDeltaRaw), 0);
      const id = normalizePetId(PET_ID_BASE + idDelta);
      if (!id) continue;

      slots[i] = {
        id,
        level: clampPetLevel(toSafeNumber(lvMinusOneRaw, 0) + 1),
      };
    }

    if (cursor.i !== bytes.length) return null;
    return slots;
  } catch {
    return null;
  }
}

function clampCharacterId(v) {
  v = Number(v);
  if (!Number.isFinite(v)) return 0;
  return Math.max(0, Math.trunc(v));
}

function clampCharacterLv(v) {
  v = Number(v);
  if (!Number.isFinite(v)) return 1;
  return Math.max(1, Math.min(15, Math.trunc(v)));
}

function clampTreasureLv(v) {
  v = Number(v);
  if (!Number.isFinite(v)) return 0;
  return Math.max(0, Math.min(11, Math.trunc(v)));
}

function asNonNegativeBigInt(value) {
  if (typeof value === "bigint") return value < 0n ? 0n : value;
  const n = Number(value);
  if (!Number.isFinite(n)) return 0n;
  return BigInt(Math.max(0, Math.trunc(n)));
}

function toSafeNumber(value, fallback = 0) {
  if (typeof value !== "bigint") return fallback;
  const min = BigInt(Number.MIN_SAFE_INTEGER);
  const max = BigInt(Number.MAX_SAFE_INTEGER);
  if (value < min || value > max) return fallback;
  return Number(value);
}

function writeVarUint(outBytes, value) {
  let n = asNonNegativeBigInt(value);
  while (n >= 0x80n) {
    outBytes.push(Number((n & 0x7fn) | 0x80n));
    n >>= 7n;
  }
  outBytes.push(Number(n));
}

function readVarUint(bytes, cursor) {
  let out = 0n;
  let shift = 0n;
  for (let i = 0; i < MAX_VARINT_BYTES; i++) {
    if (cursor.i >= bytes.length) return null;
    const b = BigInt(bytes[cursor.i++]);
    out |= (b & 0x7fn) << shift;
    if ((b & 0x80n) === 0n) return out;
    shift += 7n;
  }
  return null;
}

function encodeZigZag(value) {
  const x = BigInt(Math.trunc(Number(value) || 0));
  return x >= 0n ? (x << 1n) : ((-x << 1n) - 1n);
}

function decodeZigZag(value) {
  return (value & 1n) === 0n ? (value >> 1n) : -((value + 1n) >> 1n);
}

function getFieldCodec(field) {
  const rawStep = Number(field?.step);
  const step = (Number.isFinite(rawStep) && rawStep > 0) ? rawStep : 1;
  const stepStr = String(field?.step ?? "");
  const decimals = stepStr.includes(".") ? (stepStr.split(".")[1] || "").length : 0;
  const scale = 10 ** decimals;
  const stepUnits = Math.max(1, Math.round(step * scale));

  const rawMin = Number(field?.min);
  const hasMin = Number.isFinite(rawMin);
  const minUnits = hasMin ? Math.round(rawMin * scale) : 0;

  const rawMax = Number(field?.max);
  const hasMax = Number.isFinite(rawMax);
  const maxUnits = hasMax ? Math.round(rawMax * scale) : null;
  const maxIndexRaw = hasMax ? Math.round((maxUnits - minUnits) / stepUnits) : null;
  const maxIndex = hasMax ? Math.max(0, maxIndexRaw) : null;

  const rawDef = Number(field?.def);
  const safeDef = Number.isFinite(rawDef) ? rawDef : (hasMin ? rawMin : 0);
  const defUnits = Math.round(safeDef * scale);
  let defIndex = Math.round((defUnits - minUnits) / stepUnits);
  if (hasMin) defIndex = Math.max(0, defIndex);
  if (hasMax) defIndex = Math.min(maxIndex, defIndex);

  return {
    scale,
    decimals,
    stepUnits,
    minUnits,
    hasMin,
    hasMax,
    maxIndex,
    defIndex,
  };
}

function fieldValueToIndex(value, field) {
  const codec = getFieldCodec(field);
  const n = Number(value);
  if (!Number.isFinite(n)) return codec.defIndex;

  const units = Math.round(n * codec.scale);
  let index = Math.round((units - codec.minUnits) / codec.stepUnits);
  if (codec.hasMin) index = Math.max(0, index);
  if (codec.hasMax) index = Math.min(codec.maxIndex, index);
  return index;
}

function fieldIndexToValue(index, field) {
  const codec = getFieldCodec(field);
  let idx = Number(index);
  if (!Number.isFinite(idx)) idx = codec.defIndex;
  idx = Math.trunc(idx);
  if (codec.hasMin) idx = Math.max(0, idx);
  if (codec.hasMax) idx = Math.min(codec.maxIndex, idx);

  const value = (codec.minUnits + idx * codec.stepUnits) / codec.scale;
  return codec.decimals > 0 ? Number(value.toFixed(codec.decimals)) : Math.trunc(value);
}

function getPartyMembersFromUI() {
  return getPartyMembers().map(m => ({
    characterId: clampCharacterId(m.character),
    charLv: clampCharacterLv(m.charLv),
    treasureLv: clampTreasureLv(m.treasureLv),
    extras: m.extras ?? {},
  }));
}

function packPartyMembers(members) {
  const out = [];
  writeVarUint(out, PARTY_PACK_VERSION);
  writeVarUint(out, members.length);

  members.forEach(member => {
    const characterId = clampCharacterId(member.characterId ?? member.character);
    const charLv = clampCharacterLv(member.charLv);
    const treasureLv = clampTreasureLv(member.treasureLv);

    writeVarUint(out, characterId);
    out.push(((charLv - 1) << 4) | (treasureLv & 0x0f));

    const fields = getExtraFieldsForCharacter(String(characterId));
    if (!fields.length) return;

    let extrasMask = 0n;
    const deltas = [];

    fields.forEach((field, i) => {
      const codec = getFieldCodec(field);
      const currentIndex = fieldValueToIndex(member.extras?.[field.key], field);
      const delta = currentIndex - codec.defIndex;
      if (delta === 0) return;
      extrasMask |= (1n << BigInt(i));
      deltas.push(delta);
    });

    writeVarUint(out, extrasMask);
    deltas.forEach(delta => writeVarUint(out, encodeZigZag(delta)));
  });

  return bytesToB64Url(new Uint8Array(out));
}

function unpackPartyMembers(pStr) {
  const bytes = b64UrlToBytes(pStr);
  const cursor = { i: 0 };

  const versionRaw = readVarUint(bytes, cursor);
  const version = toSafeNumber(versionRaw, -1);
  if (version !== PARTY_PACK_VERSION) return null;

  const countRaw = readVarUint(bytes, cursor);
  const count = toSafeNumber(countRaw, -1);
  if (!Number.isInteger(count) || count < 0 || count > MAX_PARTY_MEMBERS) return null;

  const members = [];

  for (let i = 0; i < count; i++) {
    const characterIdRaw = readVarUint(bytes, cursor);
    if (characterIdRaw === null) return null;

    if (cursor.i >= bytes.length) return null;
    const lvBits = bytes[cursor.i++];

    const characterId = String(clampCharacterId(toSafeNumber(characterIdRaw, 0)));
    const charLv = clampCharacterLv((lvBits >> 4) + 1);
    const treasureLv = clampTreasureLv(lvBits & 0x0f);

    const extras = {};
    const fields = getExtraFieldsForCharacter(characterId);
    if (fields.length > 0) {
      const maskRaw = readVarUint(bytes, cursor);
      if (maskRaw === null) return null;
      if ((maskRaw >> BigInt(fields.length)) !== 0n) return null;

      for (let fi = 0; fi < fields.length; fi++) {
        const bit = (maskRaw >> BigInt(fi)) & 1n;
        if (bit === 0n) continue;

        const zz = readVarUint(bytes, cursor);
        if (zz === null) return null;

        const delta = toSafeNumber(decodeZigZag(zz), 0);
        if (delta === 0) continue;

        const field = fields[fi];
        const codec = getFieldCodec(field);
        extras[field.key] = fieldIndexToValue(codec.defIndex + delta, field);
      }
    }

    members.push({
      characterId,
      charLv,
      treasureLv,
      extras,
    });
  }

  if (cursor.i !== bytes.length) return null;
  return members;
}

function parsePartyParam(p) {
  if (!p) return null;
  try {
    return unpackPartyMembers(p);
  } catch {
    return null;
  }
}

// --- apply from URL ---
export function applyStateFromUrl() {
  const params = new URLSearchParams(location.search);
  let appliedRelic = false;
  let appliedMain = false;
  let appliedPets = false;
  let appliedOther = false;
  let appliedParty = false;
  let partyMembers = [];

  const r = params.get("r");
  const relicLevels = parseRelicParam(r);
  if (relicLevels) {
    setRelicLevelsToUI(relicLevels);
    appliedRelic = true;

    const allSame = relicLevels.every(v => v === relicLevels[0]);
    if (allSame && el.allRelicLv) el.allRelicLv.value = String(relicLevels[0]);
  }

  const m = params.get("m");
  if (m) {
    const st = unpackMainBuffs(m);
    if (st) {
      setMainBuffsToUI(st);
      appliedMain = true;
    }
  }

  const t = params.get("t");
  if (t) {
    const petSlots = unpackPetSlots(t);
    if (petSlots) {
      setPetSlotsToUI(petSlots);
      appliedPets = true;
    }
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

  const p = params.get("p");
  const parsedParty = parsePartyParam(p);
  if (Array.isArray(parsedParty)) {
    partyMembers = parsedParty;
    appliedParty = true;
  }

  return { appliedRelic, appliedMain, appliedPets, appliedOther, appliedParty, partyMembers };
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

  // main buffs
  const main = getMainBuffsFromUI();
  const mainIsDefault =
    Number(main.mythEnhanceLv) === Number(MAIN_BUFF_DEFAULTS.mythEnhanceLv) &&
    Number(main.atkBuffPct) === Number(MAIN_BUFF_DEFAULTS.atkBuffPct) &&
    Number(main.manaRegenBuffPct) === Number(MAIN_BUFF_DEFAULTS.manaRegenBuffPct) &&
    Number(main.speedBuffPct) === Number(MAIN_BUFF_DEFAULTS.speedBuffPct) &&
    Number(main.defDown) === Number(MAIN_BUFF_DEFAULTS.defDown) &&
    Number(main.coins) === Number(MAIN_BUFF_DEFAULTS.coins);

  if (mainIsDefault) {
    params.delete("m");
  } else {
    params.set("m", packMainBuffs(main));
  }

  // pet slots
  const petSlots = getPetSlotsFromUI();
  const petsAreDefault = petSlots.every(slot => !slot?.id);
  if (petsAreDefault) {
    params.delete("t");
  } else {
    params.set("t", packPetSlots(petSlots));
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

  // party members (without rune fields)
  const partyMembers = getPartyMembersFromUI();
  if (partyMembers.length === 0) {
    params.delete("p");
  } else {
    params.set("p", packPartyMembers(partyMembers));
  }

  const qs = params.toString();
  const newUrl = qs ? `${location.pathname}?${qs}${location.hash}` : `${location.pathname}${location.hash}`;
  const curUrl = `${location.pathname}${location.search}${location.hash}`;
  if (newUrl !== curUrl) history.replaceState(null, "", newUrl);
}
