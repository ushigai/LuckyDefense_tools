export const state = {
  CHARACTERS: [],
  ENEMIES: [],
  ENEMY_MAP: new Map(),
  memberSeq: 0,
};

export const ALLOWED_CHARACTER_IDS = [
  "5008",  // ママ
  "5013",  // ワット
  "5016",  // ウチ
  "5019",  // チョナ
  "5020",  // ペンギン
  "5021",  // ヘイリー
  "5106",  // ドラゴン
  "5109",  // キングダイアン
  "5115",  // ロケッチュー（変身後）
  "5104",  // アイアンニャン
  "5204",  // アイアンニャンv2
  "15004", // アイアムニャン
  "14002", // ドクターパルス
  "15021", // 覚醒ヘイリー
  "15024", // ボス選鳥師
  "15009", // カエルの死神
  "15109", // 死神ダイアン
];

export const ALLOWLIST_EMPTY_MEANS_ALL = false;

