// static/char_select_ui.js
import { translateGameText } from "./i18n.js";

export function enhanceCharacterDropdown(row, { characters, imgBase = "/data/img/char" }) {
  const charImgUrl = (id) => `${imgBase}/${id}.png`;

  function setImgWithFallback(imgEl, fallbackEl, url) {
    if (!imgEl || !fallbackEl) return;

    imgEl.classList.remove("d-none");
    fallbackEl.classList.add("d-none");

    imgEl.onload = () => {
      imgEl.classList.remove("d-none");
      fallbackEl.classList.add("d-none");
    };
    imgEl.onerror = () => {
      imgEl.classList.add("d-none");
      fallbackEl.classList.remove("d-none");
    };
    imgEl.src = url;
  }

  function installImgFallback(imgEl, fallbackEl) {
    if (!imgEl || !fallbackEl) return;
    fallbackEl.classList.add("d-none");
    imgEl.classList.remove("d-none");
    imgEl.addEventListener("error", () => {
      imgEl.classList.add("d-none");
      fallbackEl.classList.remove("d-none");
    });
  }

  const hidden = row.querySelector(".member-character");
  if (!hidden) return;

  // ここで row 内の dropdown を探す（あなたのHTML構造に合わせて class を固定）
  const btnLabel = row.querySelector(".member-character-btn-label");
  const btnImg = row.querySelector(".member-character-btn-img");
  const btnFallback = row.querySelector(".member-character-btn-fallback");
  const prefixImg = row.querySelector(".member-character-prefix-img");
  const prefixFallback = row.querySelector(".member-character-prefix-fallback");
  const menu = row.querySelector(".member-character-menu");

  if (!btnLabel || !btnImg || !btnFallback || !menu) return;

  // menu item images init
  menu.querySelectorAll(".member-character-item").forEach((item) => {
    const img = item.querySelector(".member-character-item-img");
    const fb = item.querySelector(".member-character-item-fallback");
    if (img && fb) {
      installImgFallback(img, fb);
      const src = img.dataset.src;
      if (src) img.src = src;
    }
  });

  installImgFallback(btnImg, btnFallback);
  if (prefixImg && prefixFallback) installImgFallback(prefixImg, prefixFallback);

  function setSelected(id) {
    hidden.value = String(id);
    const ch = (characters ?? []).find((x) => String(x.id) === String(id));
    btnLabel.textContent = translateGameText(ch?.name ?? String(id));

    menu.querySelectorAll(".member-character-item.active").forEach((x) => x.classList.remove("active"));
    const active = menu.querySelector(`.member-character-item[data-char-id="${String(id)}"]`);
    if (active) active.classList.add("active");

    setImgWithFallback(btnImg, btnFallback, charImgUrl(id));
    if (prefixImg && prefixFallback) {
      setImgWithFallback(prefixImg, prefixFallback, charImgUrl(id));
    }
  }

  // initial
  setSelected(hidden.value);

  menu.addEventListener("click", (e) => {
    const item = e.target.closest(".member-character-item");
    if (!item) return;
    const id = item.dataset.charId;
    if (!id) return;

    setSelected(id);
    hidden.dispatchEvent(new Event("change", { bubbles: true })); // 既存ロジックに繋ぐ
  });
}
