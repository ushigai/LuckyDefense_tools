# CRIT Rate Calculation Formula
Note: This is based on hooks into Photon Quantum's internal parameters, so confidence is high, but it may still be wrong.

## Conclusion
CRIT Rate is the sum of all of the following:

```
- Shared base value for all characters: 5%
- Character-specific buffs (not applied globally; applied individually per character)
    - Barbarian passive
    - Sheriff passive
    - Iron Meow Exclusive Treasure
    - Bat Man Exclusive Treasure
    - Ghost Ninja Lv12 passive
    - Roka passive
- Pets
    - Drago
    - Total pet level 480
- Great Kitty Mage
    - Only Magic DMG characters with a mana-based ULT are eligible
    - Shock Robot, Kitty Mage, and Chad are Magic DMG characters, but they do not have mana-based ULT skills, so they are not eligible
    - Monopoly Man and Tar receive the buff itself, but they have no skill that deals Magic DMG, so in practice it has no effect
- Runes
- Artifact Bomba Doll value / 100
- Dragon Blob
```

The formulas for the following buffs are unknown:

```
- Divine Stone
- Endless Mode buffs
- Noisy Penguin Musician
```

## Examples
For a Bandit with Bomba Doll Lv9, no Dragon Blob, pet Drago Lv14, and total pet level 260, the CRIT Rate is as follows:

```
CRIT Rate = base value + character-specific buffs + pets + runes + Bomba Doll + Blob
CRIT Rate% = 5% + 0% + (4%+0%) + 0% + 0.036% + 0%
CRIT Rate% = 9.036%
```

For Bomba Doll Lv11, Dragon Blob 4.9%, pet Drago Lv34, total pet level 500, Ghost Ninja Lv12, and a Mythic Rune of Precision:

```
CRIT Rate = base value + character-specific buffs + pets + runes + Bomba Doll + Blob
CRIT Rate% = 5% + 15% + (7%+2%) + 3% + 0.040% + 4.9%
CRIT Rate% = 36.940%
```

## About Roka's Passive
The Roka passive in the formula above can be calculated as follows.

```
Roka passive% = (enemy distance / 7) * 30%
```

For reference when thinking about distance to the enemy, see character ranges such as:

- Range 7.0: Roka, Lazy Taoist
- Range 4.0: ranged characters (e.g. Shock Robot, Kitty Mage, Graviton, etc.)
- Range 2.1: melee characters (e.g. Electro Robot, Bat Man, Lancelot, etc.)

---

<details>
<summary>Notes below</summary>

```
baseCritRaw = floor((Status_CriticalChance.BaseValue + Increase) * Multiply / 65536)

rangeRaw = 7 * 65536
maxBonusRaw = 30 * 65536
ratioRaw = clamp(floor(distanceRaw * 65536 / rangeRaw), 0, 65536)
bonusRaw = floor(ratioRaw * maxBonusRaw / 65536)
effectiveCritRaw = baseCritRaw + bonusRaw
effectiveCritPercent = effectiveCritRaw / 65536

baseCritRaw = floor((Status_CriticalChance.BaseValue + Increase) * Multiply / 65536)
rangeRaw = Status_AttackRangeRaw
maxBonusRaw = Percent2 * 65536
ratioRaw = clamp(floor(distanceRaw * 65536 / rangeRaw), 0, 65536)
bonusRaw = floor(ratioRaw * maxBonusRaw / 65536)
effectiveCriticalChanceRaw = baseCritRaw + bonusRaw
effectiveCriticalChancePercent = effectiveCriticalChanceRaw / 65536


Verification basis:
P0 frame 18704:
  baseRaw=592182  critRaw=2346792
  bonusRaw=1754610 = 58487 * 30
  crit=35.809204%

P0 frame 19640:
  baseRaw=592182  critRaw=2555112
  bonusRaw=1962930 = 65431 * 30
  crit=38.987915%

P1 frame 15340:
  baseRaw=690748  critRaw=1161778
  bonusRaw=471030 = 15701 * 30
  crit=17.727325%

P1 frame 17681:
  baseRaw=690748  critRaw=1353418
  bonusRaw=662670 = 22089 * 30
  crit=20.651520%

All 66 samples satisfy (CriticalChance.RawValue - baseCritRaw) % 30 == 0, and match the QuantumFP calculation where ratio = distance / range and bonus = ratio * 30.
```

</details>
