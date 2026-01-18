import { el } from "./dom.js";
import { state } from "./state.js";
import { levelOptions } from "./utils.js";
import { getExtraFieldsForCharacter, readRowExtraValues, renderExtraControls } from "./extras.js";

function makeCharOptions(selectedId) {
  return state.CHARACTERS.map(c =>
    `<option value="${c.id}" ${String(c.id) === String(selectedId) ? "selected" : ""}>${c.name}</option>`
  ).join("");
}

export function addMember(recalcFn, {
  characterId = (state.CHARACTERS[0]?.id ?? "15024"),
  charLv = 1,
  treasureLv = 1,
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

          <div class="col-6 col-lg-3">
            <label class="form-label text-secondary small mb-1">専用財宝レベル</label>
            <select class="form-select member-treasurelv rounded-3">
              ${levelOptions(15, treasureLv)}
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
  ].forEach(([sel, evt]) => {
    const node = row.querySelector(sel);
    if (!node) return;
    node.addEventListener(evt, () => {
      if (sel === ".member-character") toggleExtras();
      if (el.autoRecalc.checked) recalcFn();
    });
  });

  el.partyList.appendChild(row);
  renderExtraControls(row, row.querySelector(".member-character").value, { ...extras, intake, mythCount }, recalcFn);
}

export function getPartyMembers() {
  const rows = [...el.partyList.querySelectorAll("[data-member-id]")];
  return rows.map(r => {
    const character = r.querySelector(".member-character").value;
    const charLv = Number(r.querySelector(".member-charlv").value || 1);
    const treasureLv = Number(r.querySelector(".member-treasurelv").value || 1);

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
      extras,
      dpsEl: r.querySelector(".member-dps"),
      shareEl: r.querySelector(".member-share"),
    };
  });
}

