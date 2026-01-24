import { el } from "./dom.js";
import { state } from "./state.js";
import { levelOptions } from "./utils.js";
import { getExtraFieldsForCharacter, readRowExtraValues, renderExtraControls } from "./extras.js";

function makeCharOptions(selectedId) {
  return state.CHARACTERS.map(c =>
    `<option value="${c.id}" ${String(c.id) === String(selectedId) ? "selected" : ""}>${c.name}</option>`
  ).join("");
}
const RUNE_RARITY_ORDER = ["卓越", "不滅", "神話", "レジェンド", "エピック", "レア", "ノーマル"];

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
          <div class="col-12 col-lg-6">
            <label class="form-label text-secondary small mb-1">キャラ</label>
            <div class="input-group">
              <span class="input-group-text bg-white"><i class="bi bi-person"></i></span>
              <select class="form-select member-character rounded-end-3">
                ${makeCharOptions(characterId)}
              </select>
            </div>
          </div>

          <div class="col-6 col-lg-3">
            <label class="form-label text-secondary small mb-1">キャラレベル</label>
            <select class="form-select member-charlv rounded-3">
              ${levelOptions(15, charLv)}
            </select>
          </div>

          <div class="col-6 col-lg-3 member-treasure-wrap">
            <label class="form-label text-secondary small mb-1">専用財宝レベル</label>
            <select class="form-select member-treasurelv rounded-3">
              ${levelOptions(11, treasureLv)}
            </select>
          </div>

<div class="col-12 col-lg-6 member-rune-wrap d-none">
  <label class="form-label text-secondary small mb-1">ルーン</label>
  <select class="form-select member-rune-name rounded-3">
    ${makeRuneNameOptions(runeName)}
  </select>
</div>

<div class="col-6 col-lg-3 member-rune-wrap d-none">
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
        <button class="btn btn-outline-secondary btn-sm rounded-3 mt-2 member-remove">
          <i class="bi bi-x-lg me-1"></i>削除
        </button>
      </div>
    </div>
  `;

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
      // 復帰時は直前の値を戻す（あれば）
      if (row.dataset.savedTreasureLv) sel.value = row.dataset.savedTreasureLv;
      wrap.classList.remove("d-none");
      sel.disabled = false;
    } else {
      // 非mythicは表示しない＆計算上はLv=1固定
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

    // refresh rarity options based on selected rune
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
    // 非mythic（= disabled）なら計算上1固定
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
    };
  });
}

