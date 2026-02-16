import { el, RELIC_SELECTS } from "./dom.js";
import { levelOptions } from "./utils.js";

function ensureRelicIconFrame(select) {
  if (!select) return null;

  if (select.parentElement?.classList.contains("relic-select-with-icon")) {
    return select.parentElement.querySelector(".relic-select-icon");
  }

  const parent = select.parentElement;
  if (!parent) return null;

  const frame = document.createElement("div");
  frame.className = "relic-select-with-icon";

  const iconFrame = document.createElement("span");
  iconFrame.className = "relic-select-icon-frame";

  const icon = document.createElement("img");
  icon.className = "relic-select-icon d-none";
  icon.alt = "";
  icon.loading = "eager";
  icon.decoding = "async";

  parent.insertBefore(frame, select);
  iconFrame.appendChild(icon);
  frame.appendChild(iconFrame);
  frame.appendChild(select);
  return icon;
}

function relicImagePathFromArtifact(artifact) {
  const rawNoStr = String(artifact?.no_str ?? "").trim();
  if (!/^\d+$/.test(rawNoStr)) return "";
  const noStr = rawNoStr.padStart(2, "0");
  return `/data/img/relic/100${noStr}.png`;
}

function setRelicIcon(select, iconUrl) {
  const icon = ensureRelicIconFrame(select);
  if (!icon) return;

  if (!iconUrl) {
    icon.onload = null;
    icon.onerror = null;
    icon.classList.add("d-none");
    icon.removeAttribute("src");
    return;
  }

  if (icon.getAttribute("src") === iconUrl) {
    icon.classList.remove("d-none");
    return;
  }

  icon.onload = () => {
    icon.classList.remove("d-none");
  };
  icon.onerror = () => {
    icon.onload = null;
    icon.onerror = null;
    icon.classList.add("d-none");
  };
  icon.classList.remove("d-none");
  icon.src = iconUrl;

  // Some browsers may fulfill cached images before the load handler runs.
  if (icon.complete) {
    if (icon.naturalWidth > 0 && icon.naturalHeight > 0) {
      icon.classList.remove("d-none");
    } else {
      icon.classList.add("d-none");
    }
  }
}

export function syncRelicLevelsFromAllRelic() {
  const allRelicLevel = Number(el.allRelicLv?.value || 1);
  RELIC_SELECTS.forEach(select => {
    if (!select) return;
    select.value = String(allRelicLevel);
  });
}

export function applyRelicIcons(artifactMap = new Map()) {
  RELIC_SELECTS.forEach(select => {
    if (!select) return;
    const artifactName = String(select.dataset.artifactName ?? "").trim();
    const artifact = artifactName ? artifactMap.get(artifactName) : null;
    const iconUrl = relicImagePathFromArtifact(artifact);
    setRelicIcon(select, iconUrl);
  });
}

export function populateUnitLevelSumBuffSelect(selectedValue = null) {
  const select = document.getElementById("unitLevelSumBuff");
  if (!select) return;

  const previous = selectedValue ?? select.value ?? "0";
  const minHalfStep = 0;
  const maxHalfStep = 50;

  select.innerHTML = "";
  for (let halfStep = minHalfStep; halfStep <= maxHalfStep; halfStep++) {
    const value = halfStep / 2;
    const isInteger = (halfStep % 2 === 0);
    const valueStr = (value === 0)
      ? "0"
      : (isInteger ? value.toFixed(1) : String(value));

    const option = document.createElement("option");
    option.value = valueStr;
    option.textContent = valueStr;
    if (valueStr === previous || Number(valueStr) === Number(previous)) option.selected = true;
    select.appendChild(option);
  }
}

export function initCommonOptionsUI() {
  if (el.allRelicLv) el.allRelicLv.innerHTML = levelOptions(11, 1);
  populateUnitLevelSumBuffSelect("0");

  const selectedRelicLevel = Number(el.allRelicLv?.value || 1);
  RELIC_SELECTS.forEach(select => {
    if (!select) return;
    select.innerHTML = levelOptions(11, selectedRelicLevel);
  });

  applyRelicIcons();
}
