import { BLOB_FIGURE_NAME_SELECTS, BLOB_FIGURE_VALUE_SELECTS, el } from "./dom.js";
import { state } from "./state.js";
import { upgradeSelectToImageDropdown } from "./blob_figure_image_select.js";
import { isEnglish, t, translateGameText } from "./i18n.js";

const BLOB_IMAGE_DROPDOWN_SIZE = {
  buttonIconSizePx: 26,
  menuIconSizePx: 26,
  buttonImageZoom: 1.25,
  menuImageZoom: 1.25,
};

function decimalsFromStep(step) {
  const s = String(step);
  if (s.includes("e-")) {
    const p = Number(s.split("e-")[1]);
    return Number.isFinite(p) ? p : 0;
  }
  const dot = s.indexOf(".");
  return dot >= 0 ? (s.length - dot - 1) : 0;
}

function buildRangedOptions(min, max, step) {
  const decimals = decimalsFromStep(step);
  const scale = Math.pow(10, decimals);
  const minI = Math.round(Number(min) * scale);
  const maxI = Math.round(Number(max) * scale);
  const stepI = Math.max(1, Math.round(Number(step) * scale));

  const values = [];
  for (let v = minI; v <= maxI; v += stepI) {
    const x = v / scale;
    values.push(decimals > 0 ? x.toFixed(decimals) : String(x));
  }
  return values;
}

function populateBlobFigureNameSelects() {
  const nameSelects = BLOB_FIGURE_NAME_SELECTS ?? [];
  if (!nameSelects.length) return;

  const figures = state.BLOB_FIGURES ?? [];
  nameSelects.forEach(select => {
    if (!select) return;
    const previous = select.value ?? "";
    select.innerHTML = "";

    const noneOption = document.createElement("option");
    noneOption.value = "";
    noneOption.textContent = t("none", "なし");
    select.appendChild(noneOption);

    figures.forEach(figure => {
      const option = document.createElement("option");
      option.value = String(figure.name ?? "");
      const name = translateGameText(String(figure.name ?? ""));
      const desc = translateGameText(String(figure.description ?? ""));
      if (desc) {
        option.textContent = isEnglish() ? `${name} (${desc})` : `${name}（${desc}）`;
      } else {
        option.textContent = name;
      }
      if (figure.id !== undefined && figure.id !== null) {
        option.dataset.figureId = String(figure.id);
      }
      select.appendChild(option);
    });

    if (previous) select.value = previous;
  });
}

function populateBlobFigureValueSelect(index, selectedValue = null) {
  const nameSelect = BLOB_FIGURE_NAME_SELECTS?.[index];
  const valueSelect = BLOB_FIGURE_VALUE_SELECTS?.[index];
  if (!nameSelect || !valueSelect) return;

  const name = String(nameSelect.value ?? "");
  const previous = selectedValue ?? valueSelect.value ?? "";

  valueSelect.innerHTML = "";

  if (!name) {
    const option = document.createElement("option");
    option.value = "";
    option.textContent = "—";
    valueSelect.appendChild(option);
    valueSelect.disabled = true;
    return;
  }

  const figure = state.BLOB_FIGURE_MAP?.get(name);
  const buff = figure?.buff ?? null;
  const min = buff?.min ?? 0;
  const max = buff?.max ?? 0;
  const step = buff?.step ?? 1;
  const options = buildRangedOptions(min, max, step);

  options.forEach(value => {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = value;
    if (value === previous || Number(value) === Number(previous)) option.selected = true;
    valueSelect.appendChild(option);
  });

  if (!valueSelect.value && options.length) valueSelect.value = options[0];
  valueSelect.disabled = false;
}

function maybeAutoRecalc(onAutoRecalc) {
  if (typeof onAutoRecalc !== "function") return;
  if (el.autoRecalc?.checked) onAutoRecalc();
}

export function initBlobFigureUI(onAutoRecalc) {
  const nameSelects = BLOB_FIGURE_NAME_SELECTS ?? [];
  const valueSelects = BLOB_FIGURE_VALUE_SELECTS ?? [];
  if (!nameSelects.length || !valueSelects.length) return;

  populateBlobFigureNameSelects();

  nameSelects.forEach(select => {
    upgradeSelectToImageDropdown(select, {
      idDatasetKey: "figureId",
      imgBase: "/data/img/blob_figure",
      unknownImg: "/data/img/blob_figure/unknown.png",
      buttonIconSizePx: BLOB_IMAGE_DROPDOWN_SIZE.buttonIconSizePx,
      menuIconSizePx: BLOB_IMAGE_DROPDOWN_SIZE.menuIconSizePx,
      buttonImageZoom: BLOB_IMAGE_DROPDOWN_SIZE.buttonImageZoom,
      menuImageZoom: BLOB_IMAGE_DROPDOWN_SIZE.menuImageZoom,
    });
  });

  for (let i = 0; i < Math.min(nameSelects.length, valueSelects.length); i++) {
    populateBlobFigureValueSelect(i);

    nameSelects[i].addEventListener("change", () => {
      populateBlobFigureValueSelect(i, null);
      maybeAutoRecalc(onAutoRecalc);
    });

    valueSelects[i].addEventListener("change", () => {
      maybeAutoRecalc(onAutoRecalc);
    });
  }
}
