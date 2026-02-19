import React, { useEffect, useMemo, useRef, useState } from "react";

const FPS = 40;
const DURATION_SEC = 300;
const APP_VERSION = "v0.1.0";

const LANG_PARAM = "lang";
const LANG_STORAGE_KEY = "dps_tool_lang";
const SUPPORTED_LANGS = new Set(["ja", "en", "kr"]);

const DISPLAY_CHARACTERS = [
  { key: "tiger", name: "虎の師父", color: "#d97706" },
  { key: "penguin", name: "ペンギン楽師", color: "#4f46e5" },
  { key: "ato", name: "アト", color: "#0891b2" },
  { key: "chronoAto", name: "時空アト", color: "#0369a1" },
  { key: "tar", name: "タール", color: "#dc2626" },
  { key: "kitty", name: "猫の魔法使い", color: "#c026d3" },
  { key: "grandmama", name: "グランドママ", color: "#16a34a" },
  { key: "supergravity", name: "スーパー重力弾", color: "#7c3aed" },
  { key: "chad", name: "チャド", color: "#ea580c" },
  { key: "gigachad", name: "ギガチャド", color: "#111827" },
];

const BUFF_CHARACTER_CONFIG = [
  {
    key: "penguin",
    name: "ペンギン楽師",
    prefix: "buffPenguin",
    levels: [6, 9, 12, 15],
    treasures: ["専用", "幸運のお守り", "ブーストドリンク", "なし"],
    counts: [1, 2, 3, 4, 5, 6],
    defaultTreasure: "専用",
  },
  {
    key: "tiger",
    name: "虎の師父",
    prefix: "buffTiger",
    levels: [6, 9, 12, 15],
    treasures: ["なし"],
    counts: [1, 2, 3, 4, 5, 6],
    defaultTreasure: "なし",
  },
  {
    key: "ato",
    name: "アト",
    prefix: "buffAto",
    levels: [6, 9, 12, 15],
    treasures: ["専用", "幸運のお守り", "ブーストドリンク", "なし"],
    counts: [1, 2, 3, 4, 5, 6],
    defaultTreasure: "専用",
  },
  {
    key: "chronoAto",
    name: "時空アト",
    prefix: "buffChronoAto",
    levels: [6, 9, 12, 15],
    treasures: ["なし"],
    counts: [1, 2],
    defaultTreasure: "なし",
  },
  {
    key: "tar",
    name: "タール",
    prefix: "buffTar",
    levels: [6, 9, 12, 15],
    treasures: ["専用", "幸運のお守り", "ブーストドリンク", "なし"],
    counts: [1, 2, 3, 4, 5, 6],
    defaultTreasure: "専用",
  },
  {
    key: "kitty",
    name: "猫の魔法使い",
    prefix: "buffKitty",
    levels: [6, 9, 12, 15],
    treasures: ["専用", "幸運のお守り", "ブーストドリンク", "ペンライト", "風車", "なし"],
    counts: [1, 2, 3, 4, 5, 6],
    defaultTreasure: "専用",
  },
  {
    key: "grandmama",
    name: "グランドママ",
    prefix: "buffGrandmama",
    levels: [6, 9, 12, 15],
    treasures: ["なし"],
    counts: [1, 2],
    defaultTreasure: "なし",
  },
  {
    key: "supergravity",
    name: "スーパー重力弾",
    prefix: "buffSupergravity",
    levels: [6, 9, 12, 15],
    treasures: ["なし"],
    counts: [1, 2],
    defaultTreasure: "なし",
  },
  {
    key: "chad",
    name: "チャド",
    prefix: "buffChad",
    levels: [6, 9, 12, 15],
    treasures: ["専用", "幸運のお守り", "ブーストドリンク", "なし"],
    counts: [1, 2, 3, 4, 5, 6],
    defaultTreasure: "専用",
  },
  {
    key: "gigachad",
    name: "ギガチャド",
    prefix: "buffGigachad",
    levels: [6, 9, 12, 15],
    treasures: ["なし"],
    counts: [1, 2],
    defaultTreasure: "なし",
  },
];

const NUMERIC_COLUMNS = [
  { key: "characterName", label: "キャラ名", always: true, className: "text-start" },
  { key: "skill1Count", label: "スキル1発動回数", digits: 0 },
  { key: "skill2Count", label: "スキル2発動回数", digits: 0 },
  { key: "skill3Count", label: "スキル3発動回数", digits: 0 },
  { key: "ultimateCount", label: "究極スキル発動回数", digits: 0 },
  { key: "buffTimeSec", label: "物理/魔法等バフ時間(秒)", digits: 2 },
  { key: "manaCooldownRecoveryTotal", label: "マナ/クールタイム回復量合計", digits: 2 },
  { key: "average", label: "平均", always: true, digits: 2 },
];

function clamp(n, a, b) {
  return Math.max(a, Math.min(b, n));
}

function fmt(n, d = 2) {
  return Number.isFinite(n) ? n.toFixed(d) : "-";
}

function parseNonNegativeInt(value, fallback = 0) {
  const n = Number(value);
  if (!Number.isFinite(n)) return fallback;
  return Math.max(0, Math.floor(n));
}

function formatTimeMMSS(sec) {
  const s = Math.max(0, Math.floor(sec));
  const mm = Math.floor(s / 60);
  const ss = s % 60;
  return `${mm}:${String(ss).padStart(2, "0")}`;
}

function sumSegments(segs) {
  return (segs || []).reduce((acc, segment) => acc + Math.max(0, segment.end - segment.start), 0);
}

function isActiveAt(segs, t) {
  for (const segment of segs || []) {
    if (t < segment.start) return false;
    if (t >= segment.start && t < segment.end) return true;
  }
  return false;
}

function normalizeLang(raw) {
  const normalized = String(raw || "").trim().toLowerCase();
  if (normalized === "ko") return "kr";
  return SUPPORTED_LANGS.has(normalized) ? normalized : null;
}

function resolveInitialLang() {
  try {
    const params = new URLSearchParams(window.location.search);
    const fromQuery = normalizeLang(params.get(LANG_PARAM));
    if (fromQuery) return fromQuery;
  } catch (_error) {
    // noop
  }

  try {
    const fromStorage = normalizeLang(window.localStorage.getItem(LANG_STORAGE_KEY));
    if (fromStorage) return fromStorage;
  } catch (_error) {
    // noop
  }

  const browserLang = normalizeLang((navigator.language || "").slice(0, 2));
  return browserLang || "ja";
}

function syncLangToQuery(lang) {
  try {
    const url = new URL(window.location.href);
    url.searchParams.set(LANG_PARAM, lang);
    window.history.replaceState({}, "", url.toString());
  } catch (_error) {
    // noop
  }
}

function createInitialBufferSettings() {
  const out = {};
  for (const config of BUFF_CHARACTER_CONFIG) {
    out[config.key] = {
      lv: Number(config.levels[0] || 6),
      treasure: String(config.defaultTreasure || config.treasures[0] || "なし"),
      count: Number(config.counts[0] || 1),
      increase: 0,
    };
  }
  return out;
}

function normalize(raw) {
  const out = { ...raw };
  out.durationSec = Number(out.durationSec ?? DURATION_SEC);
  out.fps = Number(out.fps ?? FPS);

  const sourceBuffs = out.buffs && typeof out.buffs === "object" ? out.buffs : {};
  out.buffs = {};
  for (const character of DISPLAY_CHARACTERS) {
    const source = Array.isArray(sourceBuffs[character.key]) ? sourceBuffs[character.key] : [];
    out.buffs[character.key] = source
      .map((segment) => ({
        start: Number(segment?.start ?? 0),
        end: Number(segment?.end ?? 0),
      }))
      .filter((segment) => Number.isFinite(segment.start) && Number.isFinite(segment.end) && segment.end > segment.start);
  }

  out.events = Array.isArray(out.events)
    ? out.events.map((event, index) => ({
        id: event?.id || `${event?.frame ?? 0}-${event?.type ?? "event"}-${index}`,
        frame: Number(event?.frame ?? 0),
        t: Number(event?.t ?? 0),
        type: String(event?.type ?? "event"),
        label: String(event?.label ?? ""),
      }))
    : [];

  out.series = Array.isArray(out.series) ? out.series : [];
  return out;
}

function createEmptyResult() {
  return normalize({
    durationSec: DURATION_SEC,
    fps: FPS,
    buffs: {},
    events: [],
    series: [],
  });
}

async function simulateViaApi(payload) {
  const response = await fetch("api/simulate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const text = await response.text().catch(() => "");
    throw new Error(`API error ${response.status}: ${text || response.statusText}`);
  }

  const data = await response.json();
  return normalize(data);
}

function eventColor(eventType) {
  if (eventType.includes("tiger")) return "#d97706";
  if (eventType.includes("penguin")) return "#4f46e5";
  return "#6b7280";
}

function SegmentsRow({ title, segments, durationSec, color, onBarMove, onBarLeave }) {
  return (
    <div className="lineItem">
      <div className="lineTitleWrap">
        <div className="lineTitle">{title}</div>
      </div>
      <div className="bar" onMouseMove={onBarMove} onMouseLeave={onBarLeave}>
        {segments.map((segment, index) => {
          const left = (segment.start / durationSec) * 100;
          const width = ((segment.end - segment.start) / durationSec) * 100;
          return (
            <div
              key={`${title}-${index}-${segment.start}-${segment.end}`}
              className="seg"
              style={{ left: `${left}%`, width: `${width}%`, backgroundColor: color }}
              title={`${fmt(segment.start, 3)}s→${fmt(segment.end, 3)}s`}
            />
          );
        })}
        {Array.from({ length: 11 }).map((_, idx) => (
          <div key={`${title}-tick-${idx}`} className="tick" style={{ left: `${(idx / 10) * 100}%` }} />
        ))}
      </div>
    </div>
  );
}

function EventRow({ events, durationSec, onBarMove, onBarLeave }) {
  return (
    <div className="lineItem">
      <div className="lineTitleWrap">
        <div className="lineTitle">発動イベント</div>
      </div>
      <div className="bar" onMouseMove={onBarMove} onMouseLeave={onBarLeave}>
        {events.map((event) => {
          const left = (event.t / durationSec) * 100;
          return (
            <div
              key={event.id}
              className="eventMark"
              style={{ left: `${left}%`, backgroundColor: eventColor(event.type) }}
              title={`F${event.frame} ${fmt(event.t, 3)}s: ${event.label}`}
            />
          );
        })}
        {Array.from({ length: 11 }).map((_, idx) => (
          <div key={`event-tick-${idx}`} className="tick" style={{ left: `${(idx / 10) * 100}%`, opacity: 0.35 }} />
        ))}
      </div>
    </div>
  );
}

export default function App() {
  const [lang, setLang] = useState(resolveInitialLang);
  const [seed, setSeed] = useState(123456);
  const [allRelicLv, setAllRelicLv] = useState(6);
  const [manaRegenBuffPct, setManaRegenBuffPct] = useState(0);
  const [speedBuffPct, setSpeedBuffPct] = useState(0);
  const [attackerASWhite, setAttackerASWhite] = useState(1.0);
  const [attackerManaRecovery, setAttackerManaRecovery] = useState(0);
  const [attackerCooldownRecovery, setAttackerCooldownRecovery] = useState(0);
  const [bufferSettings, setBufferSettings] = useState(createInitialBufferSettings);

  const [activeTab, setActiveTab] = useState("timeline");
  const [visibleCharacterKeys, setVisibleCharacterKeys] = useState(DISPLAY_CHARACTERS.map((character) => character.key));

  const [result, setResult] = useState(createEmptyResult);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");
  const [hover, setHover] = useState(null);

  const initRef = useRef(false);

  const displayedCharacters = useMemo(() => {
    const visible = new Set(visibleCharacterKeys);
    return DISPLAY_CHARACTERS.filter((character) => visible.has(character.key));
  }, [visibleCharacterKeys]);

  const eventsByFrame = useMemo(() => {
    const map = new Map();
    for (const event of result.events) {
      if (!map.has(event.frame)) map.set(event.frame, []);
      map.get(event.frame).push(event);
    }
    return map;
  }, [result.events]);

  const hoverEvents = hover ? eventsByFrame.get(hover.frame) || [] : [];

  const hoverBuffStates = useMemo(() => {
    if (!hover) return [];
    return displayedCharacters.map((character) => ({
      key: character.key,
      name: character.name,
      active: isActiveAt(result.buffs[character.key], hover.t),
    }));
  }, [displayedCharacters, hover, result.buffs]);

  const timelineEvents = useMemo(() => result.events.filter((event) => Number.isFinite(event.t)), [result.events]);

  const numericRows = useMemo(
    () =>
      displayedCharacters.map((character) => {
        const buffTimeSec = sumSegments(result.buffs[character.key] || []);
        return {
          key: character.key,
          characterName: character.name,
          skill1Count: 0,
          skill2Count: 0,
          skill3Count: 0,
          ultimateCount: 0,
          buffTimeSec,
          manaCooldownRecoveryTotal: 0,
          average: 1,
        };
      }),
    [displayedCharacters, result.buffs],
  );

  const visibleNumericColumns = useMemo(
    () =>
      NUMERIC_COLUMNS.filter((column) => {
        if (column.always) return true;
        return numericRows.some((row) => Math.abs(Number(row[column.key] || 0)) > 0);
      }),
    [numericRows],
  );

  useEffect(() => {
    document.documentElement.lang = lang;
    try {
      window.localStorage.setItem(LANG_STORAGE_KEY, lang);
    } catch (_error) {
      // noop
    }
    syncLangToQuery(lang);
  }, [lang]);

  const runSimulation = async () => {
    setLoading(true);
    setErr("");

    const tigerCount = Number(bufferSettings.tiger?.count || 0);
    const penguinCount = Number(bufferSettings.penguin?.count || 0);

    const payload = {
      seed: Number(seed),
      allRelicLv: Number(allRelicLv),
      manaRegenBuffPct: Number(manaRegenBuffPct),
      speedBuffPct: Number(speedBuffPct),
      attacker: {
        attackSpeed: Number(attackerASWhite),
        manaRecovery: Number(attackerManaRecovery),
        cooldownRecovery: Number(attackerCooldownRecovery),
      },
      buffers: {
        tigerCount,
        penguinCount,
      },
    };

    try {
      const next = await simulateViaApi(payload);
      setResult(next);
    } catch (error) {
      setErr(String(error?.message || error));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (initRef.current) return;
    initRef.current = true;
    runSimulation();
  }, []);

  const onBarMove = (ev) => {
    const rect = ev.currentTarget.getBoundingClientRect();
    const x = clamp(ev.clientX - rect.left, 0, rect.width);
    const p = rect.width <= 0 ? 0 : x / rect.width;

    const duration = Number(result.durationSec || DURATION_SEC);
    const fps = Number(result.fps || FPS);
    const maxFrame = Math.max(1, Math.floor(duration * fps)) - 1;
    const frame = clamp(Math.floor(p * duration * fps), 0, maxFrame);

    setHover({ frame, t: frame / fps, xPct: p * 100 });
  };

  const onBarLeave = () => setHover(null);

  const updateBufferSetting = (key, field, value) => {
    setBufferSettings((prev) => ({
      ...prev,
      [key]: {
        ...(prev[key] || {}),
        [field]: value,
      },
    }));
  };

  const toggleCharacter = (key) => {
    setVisibleCharacterKeys((prev) => (prev.includes(key) ? prev.filter((value) => value !== key) : [...prev, key]));
  };

  const randomizeSeed = () => {
    setSeed(Math.floor(Math.random() * (2 ** 31 - 1)));
  };

  const formatNumericCell = (row, column) => {
    if (column.key === "characterName") return row.characterName;
    const value = Number(row[column.key] || 0);
    return fmt(value, column.digits ?? 2);
  };

  return (
    <>
      <nav className="navbar navbar-expand-lg bg-white border-bottom">
        <div className="container py-1 d-flex align-items-center justify-content-between gap-3">
          <a className="navbar-brand fw-semibold" href="#">
            <i className="bi bi-speedometer2 me-1"></i>
            DPS Calculator
            <span className="ms-2 small text-muted fw-normal">{APP_VERSION}</span>
          </a>
          <div className="d-flex align-items-center gap-2">
            <label className="small text-secondary mb-0" htmlFor="langSelect">
              Lang
            </label>
            <select
              id="langSelect"
              className="form-select form-select-sm rounded-3"
              style={{ width: "110px" }}
              value={lang}
              onChange={(event) => setLang(normalizeLang(event.target.value) || "ja")}
            >
              <option value="ja">日本語</option>
              <option value="en">English</option>
              <option value="kr">한국어</option>
            </select>
          </div>
        </div>
      </nav>

      <main className="container py-4">
        <div className="card shadow-sm border-0 rounded-4 mb-3">
          <div className="card-body p-4">
            <div className="fw-semibold mb-3">
              <i className="bi bi-sliders2 me-1"></i>
              シミュレーション情報
            </div>
            <div className="row g-3">
              <div className="col-12 col-md-4">
                <label className="form-label text-secondary small" htmlFor="allRelicLv">
                  全遺物レベル
                </label>
                <select
                  id="allRelicLv"
                  className="form-select rounded-3"
                  value={String(allRelicLv)}
                  onChange={(event) => setAllRelicLv(clamp(parseNonNegativeInt(event.target.value, 6), 1, 11))}
                >
                  {Array.from({ length: 11 }).map((_, idx) => {
                    const level = idx + 1;
                    return (
                      <option key={`relic-level-${level}`} value={String(level)}>
                        {level}
                      </option>
                    );
                  })}
                </select>
              </div>
              <div className="col-12 col-md-4">
                <label className="form-label text-secondary small" htmlFor="manaRegenBuffPct">
                  マナ回復速度バフ%
                </label>
                <input
                  id="manaRegenBuffPct"
                  type="number"
                  className="form-control rounded-3"
                  min="0"
                  step="1"
                  value={manaRegenBuffPct}
                  onChange={(event) => setManaRegenBuffPct(parseNonNegativeInt(event.target.value, 0))}
                />
              </div>
              <div className="col-12 col-md-4">
                <label className="form-label text-secondary small" htmlFor="speedBuffPct">
                  攻撃速度バフ%
                </label>
                <input
                  id="speedBuffPct"
                  type="number"
                  className="form-control rounded-3"
                  min="0"
                  step="1"
                  value={speedBuffPct}
                  onChange={(event) => setSpeedBuffPct(parseNonNegativeInt(event.target.value, 0))}
                />
              </div>
              <div className="col-12 col-md-4">
                <label className="form-label text-secondary small" htmlFor="attackerASWhite">
                  アタッカーの白字攻撃速度
                </label>
                <input
                  id="attackerASWhite"
                  type="number"
                  className="form-control rounded-3"
                  min="0"
                  step="0.01"
                  value={attackerASWhite}
                  onChange={(event) => setAttackerASWhite(Number(event.target.value))}
                />
              </div>
              <div className="col-12 col-md-4">
                <label className="form-label text-secondary small" htmlFor="attackerManaRecovery">
                  アタッカーのマナ回復
                </label>
                <input
                  id="attackerManaRecovery"
                  type="number"
                  className="form-control rounded-3"
                  step="0.1"
                  value={attackerManaRecovery}
                  onChange={(event) => setAttackerManaRecovery(Number(event.target.value))}
                />
              </div>
              <div className="col-12 col-md-4">
                <label className="form-label text-secondary small" htmlFor="attackerCooldownRecovery">
                  アタッカーのクールタイム回復
                </label>
                <input
                  id="attackerCooldownRecovery"
                  type="number"
                  className="form-control rounded-3"
                  step="0.1"
                  value={attackerCooldownRecovery}
                  onChange={(event) => setAttackerCooldownRecovery(Number(event.target.value))}
                />
              </div>
              <div className="col-12 col-md-4">
                <label className="form-label text-secondary small" htmlFor="seed">
                  SEED値
                </label>
                <input
                  id="seed"
                  type="number"
                  className="form-control rounded-3"
                  value={seed}
                  onChange={(event) => setSeed(Number(event.target.value))}
                />
              </div>
            </div>

            <div className="d-flex flex-wrap align-items-center gap-2 mt-3">
              <button className="btn btn-dark rounded-3" type="button" onClick={runSimulation} disabled={loading}>
                {loading ? "シミュレーション実行中..." : "シミュレーション実行"}
              </button>
              <button className="btn btn-outline-secondary rounded-3" type="button" onClick={randomizeSeed}>
                SEEDランダム
              </button>
            </div>

            {err ? (
              <div className="alert alert-danger small mt-3 mb-0" role="alert">
                {err}
              </div>
            ) : null}
          </div>
        </div>

        <div className="card shadow-sm border-0 rounded-4 mb-3">
          <div className="card-body p-4">
            <details open>
              <summary className="fw-semibold">
                <i className="bi bi-person-gear me-2"></i>
                バフキャラ設定（未実装）
              </summary>
              <div className="table-responsive mt-3">
                <table className="table table-sm align-middle mb-0">
                  <thead>
                    <tr>
                      <th scope="col">キャラ名</th>
                      <th scope="col">Lv</th>
                      <th scope="col">財宝</th>
                      <th scope="col">数</th>
                      <th scope="col">平均増加量</th>
                    </tr>
                  </thead>
                  <tbody>
                    {BUFF_CHARACTER_CONFIG.map((config) => {
                      const setting = bufferSettings[config.key] || {};
                      return (
                        <tr key={config.key}>
                          <th scope="row">{config.name}</th>
                          <td>
                            <select
                              id={`${config.prefix}Lv`}
                              className="form-select form-select-sm rounded-3"
                              value={String(setting.lv ?? 6)}
                              onChange={(event) => updateBufferSetting(config.key, "lv", Number(event.target.value))}
                            >
                              {config.levels.map((level) => (
                                <option key={`${config.key}-level-${level}`} value={String(level)}>
                                  {level}
                                </option>
                              ))}
                            </select>
                          </td>
                          <td>
                            <select
                              id={`${config.prefix}Treasure`}
                              className="form-select form-select-sm rounded-3"
                              value={String(setting.treasure ?? config.treasures[0] ?? "なし")}
                              onChange={(event) => updateBufferSetting(config.key, "treasure", event.target.value)}
                            >
                              {config.treasures.map((treasure) => (
                                <option key={`${config.key}-treasure-${treasure}`} value={treasure}>
                                  {treasure}
                                </option>
                              ))}
                            </select>
                          </td>
                          <td>
                            <select
                              id={`${config.prefix}Count`}
                              className="form-select form-select-sm rounded-3"
                              value={String(setting.count ?? 1)}
                              onChange={(event) => updateBufferSetting(config.key, "count", Number(event.target.value))}
                            >
                              {config.counts.map((count) => (
                                <option key={`${config.key}-count-${count}`} value={String(count)}>
                                  {count}
                                </option>
                              ))}
                            </select>
                          </td>
                          <td>
                            <input
                              id={`${config.prefix}Increase`}
                              type="number"
                              className="form-control form-control-sm rounded-3"
                              value={Number(setting.increase ?? 0)}
                              step="0.1"
                              onChange={(event) => updateBufferSetting(config.key, "increase", Number(event.target.value))}
                            />
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </details>
          </div>
        </div>

        <div className="card shadow-sm border-0 rounded-4">
          <div className="card-body p-4">
            <div className="d-flex flex-wrap align-items-center justify-content-between gap-2">
              <div className="fw-semibold">
                <i className="bi bi-graph-up me-1"></i>
                シミュレーション結果
              </div>
              <div className="small text-secondary">
                全{formatTimeMMSS(result.durationSec)}（{fmt(result.durationSec, 0)}s）
              </div>
            </div>

            <div className="mt-3">
              <div className="d-flex flex-wrap align-items-center gap-2 mb-2">
                <div className="small text-secondary">表示キャラ（タブ共通）</div>
                <button
                  type="button"
                  className="btn btn-sm btn-outline-secondary rounded-3"
                  onClick={() => setVisibleCharacterKeys(DISPLAY_CHARACTERS.map((character) => character.key))}
                >
                  全選択
                </button>
                <button type="button" className="btn btn-sm btn-outline-secondary rounded-3" onClick={() => setVisibleCharacterKeys([])}>
                  全解除
                </button>
              </div>
              <div className="character-toggle-grid">
                {DISPLAY_CHARACTERS.map((character) => {
                  const checked = visibleCharacterKeys.includes(character.key);
                  return (
                    <label key={character.key} className={`character-toggle ${checked ? "active" : ""}`}>
                      <input type="checkbox" checked={checked} onChange={() => toggleCharacter(character.key)} />
                      <span>{character.name}</span>
                    </label>
                  );
                })}
              </div>
            </div>

            <ul className="nav nav-tabs mt-3">
              <li className="nav-item">
                <button
                  type="button"
                  className={`nav-link ${activeTab === "timeline" ? "active" : ""}`}
                  onClick={() => setActiveTab("timeline")}
                >
                  タイムライン
                </button>
              </li>
              <li className="nav-item">
                <button
                  type="button"
                  className={`nav-link ${activeTab === "metrics" ? "active" : ""}`}
                  onClick={() => setActiveTab("metrics")}
                >
                  数値データ
                </button>
              </li>
            </ul>

            {activeTab === "timeline" ? (
              <div className="timeline-layout mt-3">
                <div className="timelineWrap">
                  <div className="hoverZone">{hover ? <div className="hoverLine" style={{ left: `${hover.xPct}%` }} /> : null}</div>
                  {displayedCharacters.length === 0 ? (
                    <div className="small text-secondary">表示キャラを1体以上選択してください。</div>
                  ) : (
                    <div className="timelineRows">
                      {displayedCharacters.map((character) => (
                        <SegmentsRow
                          key={character.key}
                          title={character.name}
                          segments={result.buffs[character.key] || []}
                          durationSec={result.durationSec}
                          color={character.color}
                          onBarMove={onBarMove}
                          onBarLeave={onBarLeave}
                        />
                      ))}
                      <EventRow events={timelineEvents} durationSec={result.durationSec} onBarMove={onBarMove} onBarLeave={onBarLeave} />
                    </div>
                  )}
                </div>

                <div className="hover-card">
                  <div className="fw-semibold mb-2">ホバー情報</div>
                  {!hover ? (
                    <div className="small text-secondary">タイムライン上をホバーすると表示されます。</div>
                  ) : (
                    <>
                      <div className="small mb-1">
                        時刻: <span className="fw-semibold">{formatTimeMMSS(hover.t)}</span> ({fmt(hover.t, 3)}s)
                      </div>
                      <div className="small mb-2">
                        フレーム: <span className="fw-semibold">F{hover.frame}</span>
                      </div>

                      <div className="status-grid mb-2">
                        {hoverBuffStates.map((state) => (
                          <div key={`hover-state-${state.key}`} className={`status-chip ${state.active ? "on" : "off"}`}>
                            <div className="status-name">{state.name}</div>
                            <div className="status-value">{state.active ? "ON" : "OFF"}</div>
                          </div>
                        ))}
                      </div>

                      <div className="small text-secondary mb-1">このフレームのイベント</div>
                      {hoverEvents.length === 0 ? (
                        <div className="small text-secondary">なし</div>
                      ) : (
                        <div className="hover-events">
                          {hoverEvents.slice(0, 12).map((event) => (
                            <div key={`hover-event-${event.id}`} className="small hover-event-item">
                              • {event.label}
                            </div>
                          ))}
                          {hoverEvents.length > 12 ? <div className="small text-secondary">...（{hoverEvents.length}件）</div> : null}
                        </div>
                      )}
                    </>
                  )}
                </div>
              </div>
            ) : (
              <div className="table-responsive mt-3">
                {displayedCharacters.length === 0 ? (
                  <div className="small text-secondary">表示キャラを1体以上選択してください。</div>
                ) : (
                  <table className="table table-sm align-middle mb-0 result-table">
                    <thead>
                      <tr>
                        {visibleNumericColumns.map((column) => (
                          <th key={`col-${column.key}`} scope="col" className={column.className || "text-end"}>
                            {column.label}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {numericRows.map((row) => (
                        <tr key={`row-${row.key}`}>
                          {visibleNumericColumns.map((column) => (
                            <td key={`cell-${row.key}-${column.key}`} className={column.className || "text-end"}>
                              {formatNumericCell(row, column)}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>
            )}
          </div>
        </div>

        <div className="mt-3 d-flex flex-wrap justify-content-center align-items-start gap-3">
          <details className="release-notes d-inline-block text-start">
            <summary className="small">リリースノート</summary>
            <div className="rn-body small">
              <div className="rn-ver">{APP_VERSION} (2026/02/17 00:00)</div>
              <ul className="mb-0 ps-3">
                <li>`buff_sim1`のフロントUIをDPSツール寄せに再構成</li>
                <li>シミュレーション結果に「タイムライン/数値データ」タブを追加</li>
                <li>表示キャラ共通化、ホバー情報のバフON/OFF一覧を追加</li>
                <li>バフキャラ設定（未実装）テーブルを実装</li>
              </ul>
            </div>
          </details>
          <div className="copyright-note small">
            <div>© 2026 @ushigai</div>
            <div>Lucky Defense is a game by 111%.</div>
            <div>Fan-made tool, not affiliated with 111%.</div>
          </div>
        </div>
      </main>
    </>
  );
}
