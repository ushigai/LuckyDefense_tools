import { state, ALLOWED_CHARACTER_IDS, ALLOWLIST_EMPTY_MEANS_ALL } from "./state.js";

function toList(payload, key) {
  if (Array.isArray(payload)) return payload;
  const nested = payload?.[key];
  return Array.isArray(nested) ? nested : [];
}

function parseEnemyWave(rawWave, name) {
  const wave = Number(rawWave);
  if (Number.isFinite(wave) && wave > 0) return Math.trunc(wave);
  const match = String(name ?? "").match(/(\d+)\s*[Wｗ]/);
  if (!match) return 0;
  const parsed = Number(match[1]);
  return Number.isFinite(parsed) ? parsed : 0;
}

function parseEnemyMode(rawMode, name) {
  const mode = String(rawMode ?? "").trim();
  if (mode) return mode;

  const nameStr = String(name ?? "");
  for (const token of ["ノーマル", "ハード", "地獄", "神"]) {
    if (nameStr.includes(token)) return token;
  }
  return "";
}

function parseEnemyGroup(rawGroup, name) {
  const group = String(rawGroup ?? "").trim();
  if (group) return group;
  return String(name ?? "").includes("ボス") ? "ボス" : "";
}

function normalizeEnemyEntry(rawEnemy) {
  const name = String(rawEnemy?.name ?? "").trim();
  const mode = parseEnemyMode(rawEnemy?.mode, name);
  const wave = parseEnemyWave(rawEnemy?.wave, name);
  const group = parseEnemyGroup(rawEnemy?.group, name);
  return {
    ...rawEnemy,
    mode,
    wave,
    group,
    name,
  };
}

function enemySelectionKey(enemy) {
  return `${String(enemy?.mode ?? "")}|${Number(enemy?.wave ?? 0)}|${String(enemy?.group ?? "")}`;
}

function normalizeEnemyUiFilter(raw) {
  if (!raw || typeof raw !== "object") {
    return {
      enabled: false,
      modes: new Set(),
      waves: new Set(),
      groups: new Set(),
      keys: new Set(),
    };
  }

  const toStringSet = values => new Set(
    Array.isArray(values)
      ? values.map(v => String(v ?? "").trim()).filter(Boolean)
      : []
  );
  const toNumberSet = values => new Set(
    Array.isArray(values)
      ? values
          .map(v => Number(v))
          .filter(v => Number.isFinite(v) && v > 0)
          .map(v => Math.trunc(v))
      : []
  );

  return {
    enabled: raw.enabled !== false,
    modes: toStringSet(raw.modes),
    waves: toNumberSet(raw.waves),
    groups: toStringSet(raw.groups),
    keys: toStringSet(raw.keys),
  };
}

function isEnemyVisibleInUi(enemy, filter) {
  if (!filter?.enabled) return true;

  const key = enemySelectionKey(enemy);
  if (filter.keys.size > 0 && !filter.keys.has(key)) return false;

  const mode = String(enemy?.mode ?? "");
  if (filter.modes.size > 0 && !filter.modes.has(mode)) return false;

  const wave = Number(enemy?.wave ?? 0);
  if (filter.waves.size > 0 && !filter.waves.has(Math.trunc(wave))) return false;

  const group = String(enemy?.group ?? "");
  if (filter.groups.size > 0 && !filter.groups.has(group)) return false;

  return true;
}

function setEmptyOptionalState(stateKey, mapKey) {
  state[stateKey] = [];
  state[mapKey] = new Map();
}

async function readRequiredJson(path) {
  const response = await fetch(path);
  return await response.json();
}

async function readOptionalJson(path, label) {
  try {
    const response = await fetch(path);
    if (!response.ok) {
      if (response.status !== 404) console.warn(`${label} not found:`, response.status);
      return null;
    }
    return await response.json();
  } catch (error) {
    console.warn(`Failed to load ${label}:`, error);
    return null;
  }
}

async function loadOptionalCollection({
  path,
  label,
  stateKey,
  mapKey,
  arrayKey,
  mapEntryKey,
}) {
  try {
    const response = await fetch(path);
    if (!response.ok) {
      console.warn(`${label} not found:`, response.status);
      setEmptyOptionalState(stateKey, mapKey);
      return;
    }

    const payload = await response.json();
    const list = toList(payload, arrayKey);
    state[stateKey] = list;
    state[mapKey] = new Map(list.map(item => [String(item?.[mapEntryKey]), item]));
  } catch (error) {
    console.warn(`Failed to load ${label}:`, error);
    setEmptyOptionalState(stateKey, mapKey);
  }
}

function applyCharacterAllowList(allCharacters) {
  if (ALLOWED_CHARACTER_IDS.length === 0 && ALLOWLIST_EMPTY_MEANS_ALL) {
    return allCharacters;
  }

  const characterById = new Map(allCharacters.map(character => [String(character.id), character]));
  const filtered = ALLOWED_CHARACTER_IDS
    .map(id => characterById.get(String(id)))
    .filter(Boolean);

  if (filtered.length > 0) return filtered;

  console.warn("No allowed characters matched. Falling back to all characters.");
  return allCharacters;
}

export async function loadCharacters() {
  const payload = await readRequiredJson("/data/characters.json");
  const allCharacters = payload.characters ?? [];
  state.CHARACTERS = applyCharacterAllowList(allCharacters);
}

export async function loadEnemies() {
  const payload = await readRequiredJson("/data/enemy.json");
  const allEnemies = (payload.enemies ?? [])
    .map(normalizeEnemyEntry)
    .filter(enemy => String(enemy.mode) !== "" && Number(enemy.wave) > 0 && String(enemy.group) !== "");
  const uiFilterPayload = await readOptionalJson("/data/enemy_ui_filter.json", "enemy_ui_filter.json");
  const uiFilter = normalizeEnemyUiFilter(uiFilterPayload);
  const filteredEnemies = allEnemies.filter(enemy => isEnemyVisibleInUi(enemy, uiFilter));
  state.ENEMIES = (filteredEnemies.length > 0 || allEnemies.length === 0) ? filteredEnemies : allEnemies;
  if (filteredEnemies.length === 0 && allEnemies.length > 0 && uiFilter.enabled) {
    console.warn("enemy_ui_filter.json excluded every enemy. Falling back to all enemies.");
  }
  state.ENEMY_MAP = new Map((state.ENEMIES ?? []).map(enemy => [enemySelectionKey(enemy), enemy]));
}

export async function loadOptionalStateData() {
  await loadOptionalCollection({
    path: "/data/artifacts_expanded.json",
    label: "artifacts_expanded.json",
    stateKey: "ARTIFACTS",
    mapKey: "ARTIFACT_MAP",
    arrayKey: "artifacts",
    mapEntryKey: "name",
  });

  await loadOptionalCollection({
    path: "/data/pets.json",
    label: "pets.json",
    stateKey: "PETS",
    mapKey: "PET_MAP",
    arrayKey: "pets",
    mapEntryKey: "id",
  });

  await loadOptionalCollection({
    path: "/data/runes.json",
    label: "runes.json",
    stateKey: "RUNES",
    mapKey: "RUNE_MAP",
    arrayKey: "runes",
    mapEntryKey: "name",
  });

  await loadOptionalCollection({
    path: "/data/blob_figures.json",
    label: "blob_figures.json",
    stateKey: "BLOB_FIGURES",
    mapKey: "BLOB_FIGURE_MAP",
    arrayKey: "figures",
    mapEntryKey: "name",
  });
}

export async function loadInitialStateData() {
  await loadCharacters();
  await loadEnemies();
  await loadOptionalStateData();
}
