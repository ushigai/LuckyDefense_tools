import { PET_NAME_SELECTS, PET_LEVEL_SELECTS } from "./dom.js";
import { state } from "./state.js";
import { levelOptions } from "./utils.js";
import { upgradeSelectToImageDropdown } from "./blob_figure_image_select.js";
import { t, translateGameText } from "./i18n.js";

const PET_IMAGE_DROPDOWN_SIZE = {
  buttonIconSizePx: 26,
  menuIconSizePx: 26,
  buttonImageZoom: 1.45,
  menuImageZoom: 1.45,
};

function populatePetNameSelects() {
  const nameSelects = PET_NAME_SELECTS ?? [];
  if (!nameSelects.length) return;

  const pets = state.PETS ?? [];
  nameSelects.forEach(select => {
    if (!select) return;
    const previous = String(select.value ?? "");
    select.innerHTML = "";

    const noneOption = document.createElement("option");
    noneOption.value = "";
    noneOption.textContent = t("none");
    select.appendChild(noneOption);

    pets.forEach(pet => {
      const id = String(pet.id ?? "");
      if (!id) return;

      const option = document.createElement("option");
      option.value = id;
      option.textContent = translateGameText(String(pet.name ?? id));
      option.dataset.petId = id;
      select.appendChild(option);
    });

    if (previous) select.value = previous;
  });
}

function populatePetLevelSelect(index, selectedValue = null) {
  const nameSelect = PET_NAME_SELECTS?.[index];
  const levelSelect = PET_LEVEL_SELECTS?.[index];
  if (!nameSelect || !levelSelect) return;

  const hasPet = String(nameSelect.value ?? "") !== "";
  const previous = Number(selectedValue ?? levelSelect.value ?? 1);

  levelSelect.innerHTML = "";
  if (!hasPet) {
    const option = document.createElement("option");
    option.value = "";
    option.textContent = "—";
    levelSelect.appendChild(option);
    levelSelect.disabled = true;
    return;
  }

  levelSelect.innerHTML = levelOptions(50, Number.isFinite(previous) ? previous : 1);
  levelSelect.disabled = false;
}

export function initPetUI() {
  const nameSelects = PET_NAME_SELECTS ?? [];
  const levelSelects = PET_LEVEL_SELECTS ?? [];
  if (!nameSelects.length || !levelSelects.length) return;

  populatePetNameSelects();

  nameSelects.forEach(select => {
    upgradeSelectToImageDropdown(select, {
      idDatasetKey: "petId",
      imgBase: "/data/img/pet",
      unknownImg: "/data/img/blob_figure/unknown.png",
      buttonIconSizePx: PET_IMAGE_DROPDOWN_SIZE.buttonIconSizePx,
      menuIconSizePx: PET_IMAGE_DROPDOWN_SIZE.menuIconSizePx,
      buttonImageZoom: PET_IMAGE_DROPDOWN_SIZE.buttonImageZoom,
      menuImageZoom: PET_IMAGE_DROPDOWN_SIZE.menuImageZoom,
    });
  });

  for (let i = 0; i < Math.min(nameSelects.length, levelSelects.length); i++) {
    populatePetLevelSelect(i);
    nameSelects[i].addEventListener("change", () => {
      populatePetLevelSelect(i, null);
    });
  }
}
