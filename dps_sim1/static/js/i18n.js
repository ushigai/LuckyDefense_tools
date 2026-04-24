const JP_CHAR_RE = /[ぁ-んァ-ン一-龯々ー]/;
const LANG_PARAM = "lang";
const LANG_STORAGE_KEY = "dps_sim1.lang";

const SUPPORTED_LANGS = new Set(["ja", "en", "kr"]);

let currentLang = "en";
let initialized = false;
let textMapLoaded = false;
const JA_TO_LOCALE_MAPS = {
  en: new Map(),
  kr: new Map(),
};

function hasJapanese(text) {
  return JP_CHAR_RE.test(String(text ?? ""));
}

function normalizeLang(raw) {
  const s = String(raw ?? "").trim().toLowerCase();
  if (!s) return null;
  if (s.startsWith("ja")) return "ja";
  if (s.startsWith("en")) return "en";
  if (s === "kr" || s.startsWith("ko")) return "kr";
  if (SUPPORTED_LANGS.has(s)) return s;
  return null;
}

function getQueryLang() {
  try {
    const qp = new URLSearchParams(window.location.search);
    return normalizeLang(qp.get(LANG_PARAM));
  } catch {
    // ignore
  }
  return null;
}

function resolveNavigatorLang() {
  try {
    const candidates = [];
    const nav = window.navigator;
    if (Array.isArray(nav?.languages)) candidates.push(...nav.languages);
    candidates.push(nav?.language, nav?.userLanguage, nav?.browserLanguage);

    for (const candidate of candidates) {
      const normalized = normalizeLang(candidate);
      if (normalized) return normalized;
    }
  } catch {
    // ignore
  }
  return null;
}

function persistLang(lang) {
  try {
    window.localStorage.setItem(LANG_STORAGE_KEY, lang);
  } catch {
    // ignore
  }
}

function resolveInitialLang() {
  const fromQuery = getQueryLang();
  if (fromQuery) return fromQuery;

  try {
    const fromStorage = normalizeLang(window.localStorage.getItem(LANG_STORAGE_KEY));
    if (fromStorage) return fromStorage;
  } catch {
    // ignore
  }

  const fromNavigator = resolveNavigatorLang();
  if (fromNavigator) return fromNavigator;

  return "en";
}

function withLangInUrl(lang) {
  const url = new URL(window.location.href);
  url.searchParams.set(LANG_PARAM, lang);
  return url.toString();
}

function redirectToLangUrl(lang) {
  const nextUrl = withLangInUrl(lang);
  if (nextUrl === window.location.href) return false;
  window.location.replace(nextUrl);
  return true;
}

function setupLanguageSelector() {
  const select = document.getElementById("langSelect");
  if (!select) return;

  select.value = currentLang;
  select.addEventListener("change", () => {
    const nextLang = normalizeLang(select.value) ?? "en";
    persistLang(nextLang);
    const nextUrl = withLangInUrl(nextLang);
    if (nextUrl !== window.location.href) {
      window.location.assign(nextUrl);
      return;
    }
    window.location.reload();
  });
}

function trimCell(value) {
  const s = String(value ?? "").trim();
  if (s.startsWith('"') && s.endsWith('"') && s.length >= 2) {
    return s.slice(1, -1).trim();
  }
  return s;
}

function lookupExactText(text) {
  const key = trimCell(text);
  if (!key) return "";

  const localeMap = JA_TO_LOCALE_MAPS[currentLang];
  const fromCsv = localeMap?.get(key);
  if (fromCsv) return fromCsv;

  return "";
}

async function loadTextMap() {
  if (textMapLoaded) return;
  textMapLoaded = true;
  try {
    const res = await fetch("/api/i18n/textmap");
    if (!res.ok) return;
    const payload = await res.json();
    const tableByLocale = payload?.jaToLocale;
    if (tableByLocale && typeof tableByLocale === "object") {
      for (const lang of ["en", "kr"]) {
        const table = tableByLocale[lang];
        if (!table || typeof table !== "object") continue;
        for (const [jaRaw, dstRaw] of Object.entries(table)) {
          const ja = trimCell(jaRaw);
          const dst = trimCell(dstRaw);
          if (!ja || !dst) continue;
          if (!JA_TO_LOCALE_MAPS[lang].has(ja)) {
            JA_TO_LOCALE_MAPS[lang].set(ja, dst);
          }
        }
      }
      return;
    }

    // Backward compatibility payload shape
    const enTable = payload?.jaToEn;
    if (enTable && typeof enTable === "object") {
      for (const [jaRaw, dstRaw] of Object.entries(enTable)) {
        const ja = trimCell(jaRaw);
        const dst = trimCell(dstRaw);
        if (!ja || !dst) continue;
        if (!JA_TO_LOCALE_MAPS.en.has(ja)) {
          JA_TO_LOCALE_MAPS.en.set(ja, dst);
        }
      }
    }
    const krTable = payload?.jaToKr;
    if (krTable && typeof krTable === "object") {
      for (const [jaRaw, dstRaw] of Object.entries(krTable)) {
        const ja = trimCell(jaRaw);
        const dst = trimCell(dstRaw);
        if (!ja || !dst) continue;
        if (!JA_TO_LOCALE_MAPS.kr.has(ja)) {
          JA_TO_LOCALE_MAPS.kr.set(ja, dst);
        }
      }
    }
  } catch {
    // ignore: just keep map empty
  }
}

function translateTrimmedText(text) {
  const raw = String(text ?? "");
  if (!raw || currentLang === "ja") return raw;

  const exact = lookupExactText(raw);
  if (exact) return exact;

  // 機械翻訳は行わない。未登録語は日本語のまま。
  return raw;
}

function translateWithSpacing(rawText) {
  const raw = String(rawText ?? "");
  if (!raw || currentLang === "ja") return raw;
  if (!hasJapanese(raw)) return raw;

  const m = raw.match(/^(\s*)([\s\S]*?)(\s*)$/);
  if (!m) return translateTrimmedText(raw);
  const leading = m[1] ?? "";
  const body = m[2] ?? "";
  const trailing = m[3] ?? "";
  const translated = translateTrimmedText(body);
  return `${leading}${translated}${trailing}`;
}

function shouldSkipNode(node) {
  const parent = node.parentElement;
  if (!parent) return true;
  if (parent.closest("[data-i18n-skip]")) return true;

  const tag = parent.tagName;
  if (!tag) return false;
  if (tag === "SCRIPT" || tag === "STYLE" || tag === "CODE" || tag === "PRE" || tag === "NOSCRIPT") return true;
  return false;
}

export function translateDomTree(root = document.body) {
  if (currentLang === "ja") return;
  if (!root) return;

  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
  const textNodes = [];
  let n = walker.nextNode();
  while (n) {
    if (!shouldSkipNode(n)) textNodes.push(n);
    n = walker.nextNode();
  }

  textNodes.forEach((node) => {
    const src = node.nodeValue;
    if (!src || !hasJapanese(src)) return;
    node.nodeValue = translateWithSpacing(src);
  });

  const attrs = ["placeholder", "title", "aria-label"];
  root.querySelectorAll?.("[placeholder], [title], [aria-label]").forEach((el) => {
    if (el.closest("[data-i18n-skip]")) return;
    attrs.forEach((attr) => {
      const cur = el.getAttribute(attr);
      if (!cur || !hasJapanese(cur)) return;
      el.setAttribute(attr, translateWithSpacing(cur));
    });
  });
}

export function t(key, fallback = "") {
  const src = String(fallback || key || "");
  return translateWithSpacing(src);
}

export function getCurrentLang() {
  return currentLang;
}

export function isEnglish() {
  return currentLang === "en";
}

export function translateGameText(text) {
  if (currentLang === "ja") return String(text ?? "");
  return translateWithSpacing(String(text ?? ""));
}

export async function initI18n() {
  if (initialized) return false;

  currentLang = resolveInitialLang();
  if (!SUPPORTED_LANGS.has(currentLang)) currentLang = "en";

  persistLang(currentLang);
  if (redirectToLangUrl(currentLang)) return true;

  document.documentElement.lang = currentLang;
  setupLanguageSelector();

  if (currentLang !== "ja") {
    await loadTextMap();
    translateDomTree(document.body);
  }

  window.__dpsI18n = {
    lang: () => currentLang,
    t,
    translateGameText,
  };
  initialized = true;
  return false;
}
