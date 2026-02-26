export const el = {
  partyList: document.getElementById("partyList"),
  btnAddMember: document.getElementById("btnAddMember"),

  enemyMode: document.getElementById("enemyMode"),
  enemyWave: document.getElementById("enemyWave"),
  enemyGroup: document.getElementById("enemyGroup"),

  // common (主要バフ)
  allRelicLv: document.getElementById("allRelicLv"),
  mythEnhanceLv: document.getElementById("mythEnhanceLv"),
  atkBuffPct: document.getElementById("atkBuffPct"),
  manaRegenBuffPct: document.getElementById("manaRegenBuffPct"),
  speedBuffPct: document.getElementById("speedBuffPct"),
  defDown: document.getElementById("defDown"),
  coins: document.getElementById("coins"),
  coinsPreview: document.getElementById("coinsPreview"),

  // relic levels
  moneyGunLv: document.getElementById("moneyGunLv"),
  powerPotionLv: document.getElementById("powerPotionLv"),
  fairyBowLv: document.getElementById("fairyBowLv"),
  greatSwordLv: document.getElementById("greatSwordLv"),
  secretBookLv: document.getElementById("secretBookLv"),
  bambaDollLv: document.getElementById("bambaDollLv"),
  batLv: document.getElementById("batLv"),
  wizardHatLv: document.getElementById("wizardHatLv"),
  bombLv: document.getElementById("bombLv"),
  oldBookLv: document.getElementById("oldBookLv"),
  sageYogurtLv: document.getElementById("sageYogurtLv"),
  magicGauntletLv: document.getElementById("magicGauntletLv"),

  // pets
  pet1: document.getElementById("pet1"),
  pet1Level: document.getElementById("pet1Level"),
  pet2: document.getElementById("pet2"),
  pet2Level: document.getElementById("pet2Level"),
  pet3: document.getElementById("pet3"),
  pet3Level: document.getElementById("pet3Level"),

  // other buffs
  guildBlessing: document.getElementById("guildBlessing"),
  unitLevelSumBuff: document.getElementById("unitLevelSumBuff"),
  petLevelSum: document.getElementById("petLevelSum"),

  // blob figures
  blobFigureName1: document.getElementById("blobFigureName1"),
  blobFigureValue1: document.getElementById("blobFigureValue1"),
  blobFigureName2: document.getElementById("blobFigureName2"),
  blobFigureValue2: document.getElementById("blobFigureValue2"),
  blobFigureName3: document.getElementById("blobFigureName3"),
  blobFigureValue3: document.getElementById("blobFigureValue3"),
  blobFigureName4: document.getElementById("blobFigureName4"),
  blobFigureValue4: document.getElementById("blobFigureValue4"),
  blobFigureName5: document.getElementById("blobFigureName5"),
  blobFigureValue5: document.getElementById("blobFigureValue5"),

  // details
  durationSec: document.getElementById("durationSec"),
  trials: document.getElementById("trials"),
  seed: document.getElementById("seed"),
  seedRandomize: document.getElementById("seedRandomize"),
  f32lock: document.getElementById("f32lock"),

  btnCalc: document.getElementById("btnCalc"),
  autoRecalc: document.getElementById("autoRecalc"),

  totalValue: document.getElementById("totalValue"),
  calcStatus: document.getElementById("calcStatus"),
  logFormula: document.getElementById("logFormula"),
  log: document.getElementById("log"),
  multiplier: document.getElementById("multiplier"),

  // enemies
  enemyHpText: document.getElementById("enemyHpText"),
  enemyHpBar: document.getElementById("enemyHpBar"),
  enemyHpPct: document.getElementById("enemyHpPct"),
  enemyHpDetail: document.getElementById("enemyHpDetail"),
};

export const RELIC_KEYS = [
  "moneyGunLv",
  "powerPotionLv",
  "fairyBowLv",
  "greatSwordLv",
  "secretBookLv",
  "bambaDollLv",
  "batLv",
  "wizardHatLv",
  "bombLv",
  "oldBookLv",
  "sageYogurtLv",
  "magicGauntletLv",
];

export const RELIC_SELECTS = [
  "moneyGunLv",
  "powerPotionLv",
  "fairyBowLv",
  "greatSwordLv",
  "secretBookLv",
  "bambaDollLv",
  "batLv",
  "wizardHatLv",
  "bombLv",
  "oldBookLv",
  "sageYogurtLv",
  "magicGauntletLv",
].map(k => el[k]).filter(Boolean);



export const BLOB_FIGURE_NAME_SELECTS = [
  "blobFigureName1",
  "blobFigureName2",
  "blobFigureName3",
  "blobFigureName4",
  "blobFigureName5",
].map(k => el[k]).filter(Boolean);

export const BLOB_FIGURE_VALUE_SELECTS = [
  "blobFigureValue1",
  "blobFigureValue2",
  "blobFigureValue3",
  "blobFigureValue4",
  "blobFigureValue5",
].map(k => el[k]).filter(Boolean);

export const PET_NAME_SELECTS = [
  "pet1",
  "pet2",
  "pet3",
].map(k => el[k]).filter(Boolean);

export const PET_LEVEL_SELECTS = [
  "pet1Level",
  "pet2Level",
  "pet3Level",
].map(k => el[k]).filter(Boolean);
