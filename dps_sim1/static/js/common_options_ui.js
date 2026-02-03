import { el, RELIC_SELECTS } from "./dom.js";
import { levelOptions } from "./utils.js";

export function syncRelicLevelsFromAllRelic() {
  const allRelicLevel = Number(el.allRelicLv?.value || 1);
  RELIC_SELECTS.forEach(select => {
    if (!select) return;
    select.value = String(allRelicLevel);
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
}
