import { state, ALLOWED_CHARACTER_IDS, ALLOWLIST_EMPTY_MEANS_ALL } from "./state.js";

function toList(payload, key) {
  if (Array.isArray(payload)) return payload;
  const nested = payload?.[key];
  return Array.isArray(nested) ? nested : [];
}

function setEmptyOptionalState(stateKey, mapKey) {
  state[stateKey] = [];
  state[mapKey] = new Map();
}

async function readRequiredJson(path) {
  const response = await fetch(path);
  return await response.json();
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
  state.ENEMIES = payload.enemies ?? [];
  state.ENEMY_MAP = new Map((state.ENEMIES ?? []).map(enemy => [String(enemy.name), enemy]));
}

export async function loadOptionalStateData() {
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
