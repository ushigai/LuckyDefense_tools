import { el } from "./dom.js";
import { state } from "./state.js";
import { levelOptions } from "./utils.js";
import { getExtraFieldsForCharacter, readRowExtraValues, renderExtraControls } from "./extras.js";
import { enhanceCharacterDropdown } from "./char_select_ui.js";

const RUNE_RARITY_ORDER = ["卓越", "不滅", "神話", "レジェンド", "エピック", "レア", "ノーマル"];

function charImgUrl(id) {
  return `/data/img/${id}.png`;
}

function makeCharDropdown(selectedId) {
  const selected = (state.CHARACTERS ?? []).find(c => String(c.id) === String(selectedId));
  const selectedName = selected?.name ?? String(selectedId);

  const items = (state.CHARACTERS ?? []).map(c => {
    const active = (String(c.id) === String(selectedId)) ? "active" : "";
    return `
      <li>
        <button type="button"
          class="dropdown-item d-flex align-items-center gap-2 member-character-item ${active}"
          data-char-id="${c.id}">
          <span class="char-icon-wrap">
            <img class="char-icon member-character-item-img" data-src="${charImgUrl(c.id)}" alt="">
            <i class="bi bi-person member-character-item-fallback d-none"></i>
          </span>
          <span>${c.name}</span>
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

function makeRuneNameOptions(selectedName = "なし") {
  const names = (state.RUNES ?? []).map(r => String(r.name));
  const opts = ["なし", ...names];
  return opts.map(n =>
    `<option value="${n}" ${String(n) === String(selectedName) ? "selected" : ""}>${n}</option>`
  ).join("");
}

function getRuneEntryByName(name) {
  if (!name || name === "なし") return null;
  if (state.RUNE_MAP && state.RUNE_MAP.get) return state.RUNE_MAP.get(String(name)) ?? null;
  return (state.RUNES ?? []).find(r => String(r.name) === String(name)) ?? null;
}

function makeRuneRarityOptions(runeName, selectedRarity = "なし") {
  if (!runeName || runeName === "なし") {
    return `<option value="なし" selected>なし</option>`;
  }
  const entry = getRuneEntryByName(runeName);
  const data = entry?.data ?? {};
  const available = RUNE_RARITY_ORDER.filter(k => {
    const x = data?.[k];
    const buff = x?.buff;
    return x && Array.isArray(buff) && buff.length > 0;
  });

  if (!available.length) {
    return `<option value="なし" selected>なし</option>`;
  }

  const opts = ["なし", ...available];
  const safeSelected = (opts.includes(selectedRarity)) ? selectedRarity : (available[0] ?? "なし");
  return opts.map(r =>
    `<option value="${r}" ${String(r) === String(safeSelected) ? "selected" : ""}>${r}</option>`
  ).join("");
}

export function addMember(recalcFn, {
  characterId = (state.CHARACTERS[0]?.id ?? "15024"),
  charLv = 1,
  treasureLv = 1,
  runeName = "なし",
  runeRarity = "なし",
  intake = 0,
  mythCount = 0,
  extras = {},
} = {}) {
  const id = `m${++state.memberSeq}`;
  const row = document.createElement("div");
  row.className = "p-3 rounded-4 shadow-sm row-card border";
  row.dataset.memberId = id;

  row.innerHTML = `
    <div class="row g-2 align-items-start">
      <div class="col-12 col-md-8">
        <div class="row g-2">
          <div class="col-12">
            <label class="form-label text-secondary small mb-1">キャラ</label>
            <div class="input-group">
              ${makeCharDropdown(characterId)}
            </div>
          </div>

          <div class="col-6">
            <label class="form-label text-secondary small mb-1">キャラレベル</label>
            <select class="form-select member-charlv rounded-3">
              ${levelOptions(15, charLv)}
            </select>
          </div>

          <div class="col-6 member-treasure-wrap">
            <label class="form-label text-secondary small mb-1">専用財宝レベル</label>
            <select class="form-select member-treasurelv rounded-3">
              ${levelOptions(11, treasureLv)}
            </select>
          </div>

          <div class="w-100"></div>

          <div class="col-6 member-rune-wrap d-none">
            <label class="form-label text-secondary small mb-1">ルーン</label>
            <select class="form-select member-rune-name rounded-3">
              ${makeRuneNameOptions(runeName)}
            </select>
          </div>

          <div class="col-6 member-rune-wrap d-none">
            <label class="form-label text-secondary small mb-1">ルーンレアリティ</label>
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
        <div class="text-secondary small member-share">share: —</div>
        <div class="mt-2 member-dpsratio"></div>
        <button class="btn btn-outline-secondary btn-sm rounded-3 mt-2 member-remove">
          <i class="bi bi-x-lg me-1"></i>削除
        </button>
      </div>
    </div>
  `;

  enhanceCharacterDropdown(row, { characters: state.CHARACTERS, imgBase: "/data/img" });

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
      if (row.dataset.savedTreasureLv) sel.value = row.dataset.savedTreasureLv;
      wrap.classList.remove("d-none");
      sel.disabled = false;
    } else {
      row.dataset.savedTreasureLv = sel.value;
      sel.value = "1";
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
      rarSel.disabled = (nameSel.value === "なし");

      if (nameSel.value !== "なし" && rarSel.value === "なし") {
        const opt = rarSel.querySelector("option[value]:not([value='なし'])");
        if (opt) rarSel.value = opt.value;
      }
    } else {
      row.dataset.savedRuneName = nameSel.value;
      row.dataset.savedRuneRarity = rarSel.value;

      nameSel.value = "なし";
      rarSel.value = "なし";
      rarSel.innerHTML = `<option value="なし" selected>なし</option>`;

      nameSel.disabled = true;
      rarSel.disabled = true;
      wraps.forEach(w => w.classList.add("d-none"));
    }
  }

  function updateRuneRarityOptions() {
    const nameSel = row.querySelector(".member-rune-name");
    const rarSel = row.querySelector(".member-rune-rarity");
    if (!nameSel || !rarSel) return;

    const runeName = nameSel.value || "なし";
    if (runeName === "なし") {
      rarSel.innerHTML = `<option value="なし" selected>なし</option>`;
      rarSel.value = "なし";
      rarSel.disabled = true;
      return;
    }

    const prev = rarSel.value || "なし";
    rarSel.innerHTML = makeRuneRarityOptions(runeName, prev);
    rarSel.disabled = false;
  }

  function toggleExtras() {
    const ch = row.querySelector(".member-character").value;
    renderExtraControls(row, ch, {}, recalcFn);
  }

  row.querySelector(".member-remove").addEventListener("click", () => {
    row.remove();
    if (el.partyList.children.length === 0) addMember(recalcFn);
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
      if (el.autoRecalc.checked) recalcFn();
    });
  });

  el.partyList.appendChild(row);

  // 初期表示の反映
  updateTreasureVisibility();
  updateRuneVisibility();
  renderExtraControls(row, row.querySelector(".member-character").value, { ...extras, intake, mythCount }, recalcFn);
}

export function getPartyMembers() {
  const rows = [...el.partyList.querySelectorAll("[data-member-id]")];
  return rows.map(r => {
    const character = r.querySelector(".member-character").value;
    const charLv = Number(r.querySelector(".member-charlv").value || 1);

    const treasureSel = r.querySelector(".member-treasurelv");
    let treasureLv = Number(treasureSel?.value || 1);
    if (treasureSel?.disabled) treasureLv = 1;

    const runeNameSel = r.querySelector(".member-rune-name");
    const runeRaritySel = r.querySelector(".member-rune-rarity");
    const runeName = (runeNameSel && !runeNameSel.disabled) ? (runeNameSel.value || "なし") : "なし";
    const runeRarity = (runeRaritySel && !runeRaritySel.disabled) ? (runeRaritySel.value || "なし") : "なし";

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

