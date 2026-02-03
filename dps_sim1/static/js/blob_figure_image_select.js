const IMG_BASE = "/data/img/blob_figure";
const UNKNOWN_IMG = `${IMG_BASE}/unknown.png`;

function normalizePx(value, fallback) {
  const n = Number(value);
  return Number.isFinite(n) && n > 0 ? n : fallback;
}

function imgUrlFromOption(opt, idDatasetKey, imgBase, unknownImg) {
  const id = String(opt?.dataset?.[idDatasetKey] ?? "");
  return id ? `${imgBase}/${id}.png` : unknownImg;
}

export function upgradeSelectToImageDropdown(selectEl, config = {}) {
  if (!selectEl) return;
  if (selectEl.dataset.upgraded === "1") return;
  selectEl.dataset.upgraded = "1";

  const idDatasetKey = String(config.idDatasetKey ?? "figureId");
  const imgBase = String(config.imgBase ?? IMG_BASE);
  const unknownImg = String(config.unknownImg ?? UNKNOWN_IMG);
  const buttonIconSizePx = normalizePx(config.buttonIconSizePx, 26);
  const menuIconSizePx = normalizePx(config.menuIconSizePx, 26);
  const buttonImageZoom = normalizePx(config.buttonImageZoom, 1);
  const menuImageZoom = normalizePx(config.menuImageZoom, 1);
  const iconCornerRadiusPx = normalizePx(config.iconCornerRadiusPx, 6);

  // 元selectは値保持用に隠す
  selectEl.classList.add("d-none");

  const wrap = document.createElement("div");
  wrap.className = "dropdown w-100";

  const btn = document.createElement("button");
  btn.type = "button";
  btn.className = "btn btn-outline-secondary w-100 d-flex align-items-center justify-content-between";
  btn.setAttribute("data-bs-toggle", "dropdown");
  btn.setAttribute("aria-expanded", "false");

  const left = document.createElement("span");
  left.className = "d-flex align-items-center gap-2 text-truncate";

  const iconFrame = document.createElement("span");
  iconFrame.style.width = `${buttonIconSizePx}px`;
  iconFrame.style.height = `${buttonIconSizePx}px`;
  iconFrame.style.overflow = "hidden";
  iconFrame.style.borderRadius = `${iconCornerRadiusPx}px`;
  iconFrame.style.display = "inline-flex";
  iconFrame.style.alignItems = "center";
  iconFrame.style.justifyContent = "center";
  iconFrame.style.flex = "0 0 auto";

  const icon = document.createElement("img");
  icon.style.width = "100%";
  icon.style.height = "100%";
  icon.style.objectFit = "cover";
  icon.style.imageRendering = "pixelated";
  icon.style.transformOrigin = "center center";
  icon.style.transform = `scale(${buttonImageZoom})`;
  icon.alt = "";
  icon.loading = "lazy";
  icon.src = unknownImg;
  icon.onerror = () => {
    icon.onerror = null;
    icon.src = unknownImg;
  };

  const label = document.createElement("span");
  label.className = "text-truncate";

  iconFrame.appendChild(icon);
  left.append(iconFrame, label);

  const caret = document.createElement("span");
  caret.className = "ms-2";
  caret.innerHTML = '<i class="bi bi-chevron-down"></i>';

  btn.append(left, caret);

  const menu = document.createElement("ul");
  menu.className = "dropdown-menu w-100 p-1";
  menu.style.maxHeight = "320px";
  menu.style.overflow = "auto";

  function syncFromSelect() {
    const opt = selectEl.selectedOptions?.[0];
    icon.src = imgUrlFromOption(opt, idDatasetKey, imgBase, unknownImg);
    label.textContent = opt?.textContent ?? "なし";
  }

  function rebuildMenu() {
    menu.innerHTML = "";
    for (const opt of Array.from(selectEl.options)) {
      const li = document.createElement("li");
      const item = document.createElement("button");
      item.type = "button";
      item.className = "dropdown-item d-flex align-items-center gap-2";

      const oimgFrame = document.createElement("span");
      oimgFrame.style.width = `${menuIconSizePx}px`;
      oimgFrame.style.height = `${menuIconSizePx}px`;
      oimgFrame.style.overflow = "hidden";
      oimgFrame.style.borderRadius = `${iconCornerRadiusPx}px`;
      oimgFrame.style.display = "inline-flex";
      oimgFrame.style.alignItems = "center";
      oimgFrame.style.justifyContent = "center";
      oimgFrame.style.flex = "0 0 auto";

      const oimg = document.createElement("img");
      oimg.style.width = "100%";
      oimg.style.height = "100%";
      oimg.style.objectFit = "cover";
      oimg.style.imageRendering = "pixelated";
      oimg.style.transformOrigin = "center center";
      oimg.style.transform = `scale(${menuImageZoom})`;
      oimg.alt = "";
      oimg.loading = "lazy";
      oimg.src = imgUrlFromOption(opt, idDatasetKey, imgBase, unknownImg);
      oimg.onerror = () => {
        oimg.onerror = null;
        oimg.src = unknownImg;
      };

      const text = document.createElement("span");
      text.className = "text-truncate";
      text.textContent = opt.textContent;

      oimgFrame.appendChild(oimg);
      item.append(oimgFrame, text);
      item.addEventListener("click", () => {
        selectEl.value = opt.value;
        // 既存のchange処理（数値プルダウン再生成・autoRecalc）を生かす
        selectEl.dispatchEvent(new Event("change", { bubbles: true }));
      });

      li.appendChild(item);
      menu.appendChild(li);
    }
  }

  // selectの前に差し込む
  selectEl.parentNode.insertBefore(wrap, selectEl);
  wrap.append(btn, menu);

  selectEl.addEventListener("change", syncFromSelect);

  rebuildMenu();
  syncFromSelect();
}
