export const el = {
  partyList: document.getElementById("partyList"),
  btnAddMember: document.getElementById("btnAddMember"),

  enemy: document.getElementById("enemy"),

  // common (主要バフ)
  allRelicLv: document.getElementById("allRelicLv"),
  mythEnhanceLv: document.getElementById("mythEnhanceLv"),
  atkBuffPct: document.getElementById("atkBuffPct"),
  manaRegenBuffPct: document.getElementById("manaRegenBuffPct"),
  speedBuffPct: document.getElementById("speedBuffPct"),
  defDown: document.getElementById("defDown"),
  coins: document.getElementById("coins"),

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
  pet2: document.getElementById("pet2"),
  pet3: document.getElementById("pet3"),

  // other buffs
  guildBlessing: document.getElementById("guildBlessing"),
  unitLevelSumBuff: document.getElementById("unitLevelSumBuff"),
  petLevelSum: document.getElementById("petLevelSum"),

  // details
  durationSec: document.getElementById("durationSec"),
  trials: document.getElementById("trials"),
  seed: document.getElementById("seed"),

  btnCalc: document.getElementById("btnCalc"),
  autoRecalc: document.getElementById("autoRecalc"),

  totalValue: document.getElementById("totalValue"),
  calcStatus: document.getElementById("calcStatus"),
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

