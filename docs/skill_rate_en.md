# Skill Activation Chance Calculation Formula
Note: This is based on hooks into Photon Quantum's internal parameters, so confidence is high, but it may still be wrong.

## Conclusion
- First, add all of the following:
    - Displayed Skill Activation Chance
    - Artifact "Old Book"
    - Treasure "Lucky Charm" or the unit's Exclusive Treasure
    - Passive skills
    - Bread Blob
- Then, if Giga Chad's Enhanced Signal buff is active, multiply the value after all additions by `1.05`.

> Skill Activation Chance for Mythic or higher units increases by 5%.

## Example
For Master Kun's Fire Claw with Exclusive Treasure Lv11, artifact Lv10, and Bread Blob 1.97%:

```
Skill Activation Chance = displayed Skill Activation Chance + Artifact "Old Book" + Treasure "Lucky Charm" | Exclusive Treasure + passive skills + Bread Blob
Skill Activation Chance =                           8.00% +             1.90% +                                      5.00% +             0% +      1.97%
Skill Activation Chance = 16.87%
```

If Giga Chad's Enhanced Signal is active, it becomes `16.87%*1.05 = 17.7135%`.

## Exception
Probably due to an implementation bug, Graviton's Skill Activation Chance is calculated abnormally low.

Normal: `displayed Skill Activation Chance + artifact + additive total of other buffs`
Graviton: `displayed Skill Activation Chance + artifact + (additive total of other buffs / 100)`

Therefore, for example, equipping Lucky Charm on Graviton does nothing, the Skill Activation Chance increase portion of the Exclusive Treasure also does nothing, and Bread Blob and the Lv6 trait also do nothing. For some reason, only the artifact is not divided by 100. I have already reported this issue to the game operators, so hopefully it will be fixed in the future.
