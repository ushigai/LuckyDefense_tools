import { el } from "./dom.js";
import { state } from "./state.js";
import { levelOptions } from "./utils.js";
import { getExtraFieldsForCharacter, readRowExtraValues, renderExtraControls } from "./extras.js";
import { enhanceCharacterDropdown } from "./char_select_ui.js";
import { t, translateGameText } from "./i18n.js";

const RUNE_RARITY_ORDER = ["卓越", "不滅", "神話", "レジェンド", "エピック", "レア", "ノーマル"];
const NONE_VALUE = "なし";

function charImgUrl(id) {
  return `/data/img/char/${id}.png`;
}

function treasureLevelOptions(max, selected = 0) {
  const sel = Number(selected ?? 0);
  let s = `<option value="0" ${sel === 0 ? "selected" : ""}>${t("none")}</option>`;
  for (let i = 1; i <= max; i++) {
    s += `<option value="${i}" ${i === sel ? "selected" : ""}>${i}</option>`;
  }
  return s;
}

function makeCharDropdown(selectedId) {
  const selected = (state.CHARACTERS ?? []).find(c => String(c.id) === String(selectedId));
  const selectedName = translateGameText(selected?.name ?? String(selectedId));

  const items = (state.CHARACTERS ?? []).map(c => {
    const active = (String(c.id) === String(selectedId)) ? "active" : "";
    const name = translateGameText(c.name);
    return `
      <li>
        <button type="button"
          class="dropdown-item d-flex align-items-center gap-2 member-character-item ${active}"
          data-char-id="${c.id}">
          <span class="char-icon-wrap">
            <img class="char-icon member-character-item-img" data-src="${charImgUrl(c.id)}" alt="">
            <i class="bi bi-person member-character-item-fallback d-none"></i>
          </span>
          <span>${name}</span>
        </button>
      </li>
    `;
  }).join("");

  return `
    <div class="dropdown flex-grow-1">
      <button type="button"
        class="form-select text-start rounded-end-3 member-character-btn dropdown-toggle"
        style="min-width:0" data-bs-toggle="dropdown" aria-expanded="false">
        <span class="d-flex align-items-center gap-2 w-100">
        <span class="char-icon-wrap">
          <img class="char-icon member-character-btn-img" alt="">
          <i class="bi bi-person member-character-btn-fallback d-none"></i>
        </span>
          <span class="member-character-btn-label flex-grow-1 text-truncate">${selectedName}</span>
        </span>
      </button>
      <ul class="dropdown-menu w-100 member-character-menu">
        ${items}
      </ul>
      <!-- 既存ロジックが読むのはこれ（class名を維持） -->
      <input type="hidden" class="member-character" value="${selectedId}">
    </div>
  `;
}

function makeRuneNameOptions(selectedName = NONE_VALUE) {
  const names = (state.RUNES ?? []).map(r => String(r.name));
  const opts = [NONE_VALUE, ...names];
  return opts.map(n =>
    `<option value="${n}" ${String(n) === String(selectedName) ? "selected" : ""}>${translateGameText(n)}</option>`
  ).join("");
}

function getRuneEntryByName(name) {
  if (!name || name === NONE_VALUE) return null;
  if (state.RUNE_MAP && state.RUNE_MAP.get) return state.RUNE_MAP.get(String(name)) ?? null;
  return (state.RUNES ?? []).find(r => String(r.name) === String(name)) ?? null;
}

function makeRuneRarityOptions(runeName, selectedRarity = NONE_VALUE) {
  if (!runeName || runeName === NONE_VALUE) {
    return `<option value="${NONE_VALUE}" selected>${t("none")}</option>`;
  }
  const entry = getRuneEntryByName(runeName);
  const data = entry?.data ?? {};
  const available = RUNE_RARITY_ORDER.filter(k => {
    const x = data?.[k];
    const buff = x?.buff;
    return x && Array.isArray(buff) && buff.length > 0;
  });

  if (!available.length) {
    return `<option value="${NONE_VALUE}" selected>${t("none")}</option>`;
  }

  const opts = [NONE_VALUE, ...available];
  const safeSelected = (opts.includes(selectedRarity)) ? selectedRarity : (available[0] ?? NONE_VALUE);
  return opts.map(r =>
    `<option value="${r}" ${String(r) === String(safeSelected) ? "selected" : ""}>${translateGameText(r)}</option>`
  ).join("");
}

export function addMember(recalcFn, {
  characterId = (state.CHARACTERS[0]?.id ?? "15024"),
  charLv = 1,
  treasureLv = 0,
  runeName = NONE_VALUE,
  runeRarity = NONE_VALUE,
  extras = {},
  onStateChange = null,
} = {}) {
  const id = `m${++state.memberSeq}`;
  const row = document.createElement("div");
  row.className = "p-3 rounded-4 shadow-sm row-card border";
  row.dataset.memberId = id;
  const emitStateChange = () => {
    if (typeof onStateChange === "function") onStateChange();
  };

  row.innerHTML = `
    <div class="row g-2 align-items-start">
      <div class="col-12 col-md-8">
        <div class="row g-2">
          <div class="col-12">
            <label class="form-label text-secondary small mb-1">${t("character")}</label>
            <div class="input-group">
              ${makeCharDropdown(characterId)}
            </div>
          </div>

          <div class="col-6">
            <label class="form-label text-secondary small mb-1">${t("characterLevel")}</label>
            <select class="form-select member-charlv rounded-3">
              ${levelOptions(15, charLv)}
            </select>
          </div>

          <div class="col-6 member-treasure-wrap">
            <label class="form-label text-secondary small mb-1">${t("treasureLevel")}</label>
            <select class="form-select member-treasurelv rounded-3">
              ${treasureLevelOptions(11, treasureLv)}
            </select>
          </div>

          <div class="w-100"></div>

          <div class="col-6 member-rune-wrap d-none">
            <label class="form-label text-secondary small mb-1">${t("rune")}</label>
            <select class="form-select member-rune-name rounded-3">
              ${makeRuneNameOptions(runeName)}
            </select>
          </div>

          <div class="col-6 member-rune-wrap d-none">
            <label class="form-label text-secondary small mb-1">${t("runeRarity")}</label>
            <select class="form-select member-rune-rarity rounded-3">
              ${makeRuneRarityOptions(runeName, runeRarity)}
            </select>
          </div>

          <div class="col-12">
            <div class="row g-2 member-extra-container"></div>
          </div>
        </div>
      </div>

      <div class="col-12 col-md-4 text-md-end">
        <div class="fw-semibold metric member-dps">—</div>
        <div class="text-secondary small member-share">${t("share")}: —</div>
        <div class="mt-2 member-dpsratio"></div>
        <button class="btn btn-outline-secondary btn-sm rounded-3 mt-2 member-remove">
          <i class="bi bi-x-lg me-1"></i>${t("remove")}
        </button>
      </div>
    </div>
  `;

  enhanceCharacterDropdown(row, { characters: state.CHARACTERS, imgBase: "/data/img/char" });

  function getSelectedCharacterObj() {
    const chId = row.querySelector(".member-character").value;
    return state.CHARACTERS.find(c => String(c.id) === String(chId));
  }

  function updateTreasureVisibility() {
    const ch = getSelectedCharacterObj();
    const isMythic = (ch?.rarity === "mythic");
    const wrap = row.querySelector(".member-treasure-wrap");
    const sel = row.querySelector(".member-treasurelv");
    if (!wrap || !sel) return;

    if (isMythic) {
      // 復元（なければ 0=なし）
      sel.value = row.dataset.savedTreasureLv ?? "0";
      wrap.classList.remove("d-none");
      sel.disabled = false;
    } else {
      row.dataset.savedTreasureLv = sel.value;
      // mythic以外は財宝を送らない（0=なし）
      sel.value = "0";
      sel.disabled = true;
      wrap.classList.add("d-none");
    }
  }

  function updateRuneVisibility() {
    const ch = getSelectedCharacterObj();
    const isImmortal = (ch?.rarity === "immortal");
    const wraps = row.querySelectorAll(".member-rune-wrap");
    const nameSel = row.querySelector(".member-rune-name");
    const rarSel = row.querySelector(".member-rune-rarity");
    if (!wraps || !nameSel || !rarSel) return;

    if (isImmortal) {
      if (row.dataset.savedRuneName) nameSel.value = row.dataset.savedRuneName;
      if (row.dataset.savedRuneRarity) rarSel.value = row.dataset.savedRuneRarity;

      wraps.forEach(w => w.classList.remove("d-none"));
      nameSel.disabled = false;

      rarSel.innerHTML = makeRuneRarityOptions(nameSel.value, rarSel.value);
      rarSel.disabled = (nameSel.value === NONE_VALUE);

      if (nameSel.value !== NONE_VALUE && rarSel.value === NONE_VALUE) {
        const opt = rarSel.querySelector(`option[value]:not([value='${NONE_VALUE}'])`);
        if (opt) rarSel.value = opt.value;
      }
    } else {
      row.dataset.savedRuneName = nameSel.value;
      row.dataset.savedRuneRarity = rarSel.value;

      nameSel.value = NONE_VALUE;
      rarSel.value = NONE_VALUE;
      rarSel.innerHTML = `<option value="${NONE_VALUE}" selected>${t("none")}</option>`;

      nameSel.disabled = true;
      rarSel.disabled = true;
      wraps.forEach(w => w.classList.add("d-none"));
    }
  }

  function updateRuneRarityOptions() {
    const nameSel = row.querySelector(".member-rune-name");
    const rarSel = row.querySelector(".member-rune-rarity");
    if (!nameSel || !rarSel) return;

    const runeName = nameSel.value || NONE_VALUE;
    if (runeName === NONE_VALUE) {
      rarSel.innerHTML = `<option value="${NONE_VALUE}" selected>${t("none")}</option>`;
      rarSel.value = NONE_VALUE;
      rarSel.disabled = true;
      return;
    }

    const prev = rarSel.value || NONE_VALUE;
    rarSel.innerHTML = makeRuneRarityOptions(runeName, prev);
    rarSel.disabled = false;
  }

  function toggleExtras() {
    const ch = row.querySelector(".member-character").value;
    renderExtraControls(row, ch, {}, recalcFn, emitStateChange);
  }

  row.querySelector(".member-remove").addEventListener("click", () => {
    row.remove();
    if (el.partyList.children.length === 0) {
      addMember(recalcFn, { onStateChange });
    }
    emitStateChange();
    if (el.autoRecalc.checked) recalcFn();
  });

  [
    [".member-character", "change"],
    [".member-charlv", "change"],
    [".member-treasurelv", "change"],
    [".member-rune-name", "change"],
    [".member-rune-rarity", "change"],
  ].forEach(([sel, evt]) => {
    const node = row.querySelector(sel);
    if (!node) return;
    node.addEventListener(evt, () => {
      if (sel === ".member-character") {
        updateTreasureVisibility();
        updateRuneVisibility();
        toggleExtras();
      }
      if (sel === ".member-rune-name") {
        updateRuneRarityOptions();
      }
      emitStateChange();
      if (el.autoRecalc.checked) recalcFn();
    });
  });

  el.partyList.appendChild(row);

  // 初期表示の反映
  updateTreasureVisibility();
  updateRuneVisibility();
  renderExtraControls(row, row.querySelector(".member-character").value, extras, recalcFn, emitStateChange);
}

export function getPartyMembers() {
  const rows = [...el.partyList.querySelectorAll("[data-member-id]")];
  return rows.map(r => {
    const character = r.querySelector(".member-character").value;
    const charLv = Number(r.querySelector(".member-charlv").value || 1);

    const treasureSel = r.querySelector(".member-treasurelv");
    let treasureLv = Number(treasureSel?.value || 0);
    if (treasureSel?.disabled) treasureLv = 0;

    const runeNameSel = r.querySelector(".member-rune-name");
    const runeRaritySel = r.querySelector(".member-rune-rarity");
    const runeName = (runeNameSel && !runeNameSel.disabled) ? (runeNameSel.value || NONE_VALUE) : NONE_VALUE;
    const runeRarity = (runeRaritySel && !runeRaritySel.disabled) ? (runeRaritySel.value || NONE_VALUE) : NONE_VALUE;

    const extras = {};
    const fields = getExtraFieldsForCharacter(character);
    const raw = readRowExtraValues(r);

    fields.forEach(f => {
      const v = raw[f.key];
      if (v === undefined || v === "") return;
      extras[f.key] = Number(v);
    });

    return {
      rowEl: r,
      character,
      charLv,
      treasureLv,
      runeName,
      runeRarity,
      extras,
      dpsEl: r.querySelector(".member-dps"),
      shareEl: r.querySelector(".member-share"),
      ratioEl: r.querySelector(".member-dpsratio"),
    };
  });
}
