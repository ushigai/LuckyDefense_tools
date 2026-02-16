const JP_CHAR_RE = /[ぁ-んァ-ン一-龯々ー]/;
const LANG_PARAM = "lang";
const LANG_STORAGE_KEY = "dps_sim1.lang";

const SUPPORTED_LANGS = new Set(["ja", "en", "kr"]);

const APP_STRINGS = {
  ja: {
    none: "なし",
    character: "キャラ",
    characterLevel: "キャラレベル",
    treasureLevel: "専用財宝レベル",
    rune: "ルーン（未実装）",
    runeRarity: "ルーンレアリティ",
    remove: "削除",
    share: "share",
    calculating: "計算中",
    calculatingStatus: "計算中…",
    calculate: "計算する",
    breakdown: "内訳",
    basicAttack: "基本攻撃",
    enemyDataMissing: "敵データなし",
    hpShort: "HP",
  },
  en: {
    none: "None",
    character: "Character",
    characterLevel: "Character Level",
    treasureLevel: "Exclusive Treasure Level",
    rune: "Rune (Not Implemented)",
    runeRarity: "Rune Rarity",
    remove: "Remove",
    share: "share",
    calculating: "Calculating",
    calculatingStatus: "Calculating...",
    calculate: "Calculate",
    breakdown: "Breakdown",
    basicAttack: "Basic Attack",
    enemyDataMissing: "No enemy data",
    hpShort: "HP",
  },
  kr: {
    none: "없음",
    character: "캐릭터",
    characterLevel: "캐릭터 레벨",
    treasureLevel: "전용 보물 레벨",
    rune: "룬 (미구현)",
    runeRarity: "룬 희귀도",
    remove: "삭제",
    share: "share",
    calculating: "계산 중",
    calculatingStatus: "계산 중...",
    calculate: "계산하기",
    breakdown: "내역",
    basicAttack: "기본 공격",
    enemyDataMissing: "적 데이터 없음",
    hpShort: "HP",
  },
};

// App固有の表現で Text.csv に存在しないものだけを明示的に登録する。
// 未登録語は自動翻訳せず、日本語のまま表示する。
const APP_TERM_OVERRIDES = {
  en: new Map([
    ["敵との距離（マス数）", "Distance to Enemy (Tiles)"],
    ["異種神話数", "Distinct Mythic Count"],
    ["摂取値", "Intake Value"],
    ["火花追加ダメージ", "Spark Bonus Damage"],
    ["エネルギー個数（究極中）", "Energy Count (During Ultimate)"],
    ["鍛錬", "Training"],
    ["動物ユニット数", "Animal Unit Count"],
    ["ドローン", "Drones"],
    ["ストライクアウト平均回数", "Average Strike-Out Count"],
    ["エースバットマン投手", "Ace Bat Man Pitcher"],
    ["エースバットマン打者", "Ace Bat Man Batter"],
    ["ロケッチュー（変身後）", "Rocket Chu (Transformed)"],
    ["送信中…", "Sending..."],
    ["送信しました。ありがとうございます。", "Sent. Thank you."],
    ["送信に失敗しました。", "Failed to send."],
  ]),
  kr: new Map([
    ["送信中…", "전송 중..."],
    ["送信しました。ありがとうございます。", "전송되었습니다. 감사합니다."],
    ["送信に失敗しました。", "전송에 실패했습니다."],
  ]),
};

let currentLang = "ja";
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

function resolveInitialLang() {
  try {
    const qp = new URLSearchParams(window.location.search);
    const fromQuery = normalizeLang(qp.get(LANG_PARAM));
    if (fromQuery) return fromQuery;
  } catch {
    // ignore
  }

  try {
    const fromStorage = normalizeLang(window.localStorage.getItem(LANG_STORAGE_KEY));
    if (fromStorage) return fromStorage;
  } catch {
    // ignore
  }
  return "ja";
}

function withLangInUrl(lang) {
  const url = new URL(window.location.href);
  if (lang === "ja") {
    url.searchParams.delete(LANG_PARAM);
  } else {
    url.searchParams.set(LANG_PARAM, lang);
  }
  return url.toString();
}

function setupLanguageSelector() {
  const select = document.getElementById("langSelect");
  if (!select) return;

  select.value = currentLang;
  select.addEventListener("change", () => {
    const nextLang = normalizeLang(select.value) ?? "ja";
    try {
      window.localStorage.setItem(LANG_STORAGE_KEY, nextLang);
    } catch {
      // ignore
    }
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

  const fromApp = APP_TERM_OVERRIDES[currentLang]?.get(key);
  if (fromApp) return fromApp;

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
  const dict = APP_STRINGS[currentLang] ?? APP_STRINGS.ja;
  if (Object.prototype.hasOwnProperty.call(dict, key)) return dict[key];
  if (Object.prototype.hasOwnProperty.call(APP_STRINGS.ja, key)) return APP_STRINGS.ja[key];
  return fallback || key;
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
  if (initialized) return;

  currentLang = resolveInitialLang();
  if (!SUPPORTED_LANGS.has(currentLang)) currentLang = "ja";

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
}
