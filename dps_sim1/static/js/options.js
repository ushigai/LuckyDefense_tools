import { el } from "./dom.js";

export function collectOptions() {
  const readPet = (nameSel, levelSel) => {
    const id = String(nameSel?.value ?? "");
    const name = String(nameSel?.selectedOptions?.[0]?.textContent ?? "");
    const level = Number(levelSel?.value || 1);
    return { id, name, level };
  };

  const pets = [
    readPet(el.pet1, el.pet1Level),
    readPet(el.pet2, el.pet2Level),
    readPet(el.pet3, el.pet3Level),
  ].filter(p => p.id !== "");

  const firstPet = pets[0] ?? null;

  return {
    enemy: String(el.enemy.value),

    allRelicLv: Number(el.allRelicLv.value),
    mythEnhanceLv: Number(el.mythEnhanceLv.value || 0),
    atkBuffPct: Number(el.atkBuffPct.value || 0),
    manaRegenBuffPct: Number(el.manaRegenBuffPct.value || 0),
    speedBuffPct: Number(el.speedBuffPct.value || 0),
    defDown: Number(el.defDown.value || 190),
    coins: Number(el.coins.value || 300000),

    moneyGunLv: Number(el.moneyGunLv.value || el.allRelicLv.value || 1),
    powerPotionLv: Number(el.powerPotionLv.value || el.allRelicLv.value || 1),
    fairyBowLv: Number(el.fairyBowLv.value || el.allRelicLv.value || 1),
    greatSwordLv: Number(el.greatSwordLv.value || el.allRelicLv.value || 1),
    secretBookLv: Number(el.secretBookLv.value || el.allRelicLv.value || 1),
    bambaDollLv: Number(el.bambaDollLv.value || el.allRelicLv.value || 1),
    batLv: Number(el.batLv.value || el.allRelicLv.value || 1),
    wizardHatLv: Number(el.wizardHatLv.value || el.allRelicLv.value || 1),
    bombLv: Number(el.bombLv.value || el.allRelicLv.value || 1),
    oldBookLv: Number(el.oldBookLv.value || el.allRelicLv.value || 1),
    sageYogurtLv: Number(el.sageYogurtLv.value || el.allRelicLv.value || 1),
    magicGauntletLv: Number(el.magicGauntletLv.value || el.allRelicLv.value || 1),

    pet1: String(el.pet1.value),
    pet1Level: Number(el.pet1Level.value || 1),
    pet2: String(el.pet2.value),
    pet2Level: Number(el.pet2Level.value || 1),
    pet3: String(el.pet3.value),
    pet3Level: Number(el.pet3Level.value || 1),
    pets,
    pet: firstPet,
    guildBlessing: String(el.guildBlessing.value),
    unitLevelSumBuff: String(el.unitLevelSumBuff.value),
    petLevelSum: String(el.petLevelSum.value),

    durationSec: Number(el.durationSec.value),
    trials: Number(el.trials.value),
    seed: Number(el.seed.value),
    multiplier: Number(el.multiplier.value || 1),
  };
}
