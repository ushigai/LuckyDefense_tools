# クリティカル確率の計算式
注意：photon quantumの内部パラメータをhookしているので確度は高いけど、もしかしたら間違えてるかも

## 結論
クリティカル確率は以下を全て加算したもの

```
- 全キャラ共通の基礎値5%
- キャラ固有バフ（全体に適用されるわけではなく各キャラごと個別に適用）
    - 野蛮人パッシブ
    - 保安官パッシブ
    - アイアンニャン専用財宝
    - バットマン専用財宝
    - 鬼神忍者Lv12パッシブ
    - ロカパッシブ
- ペット
    - ドラ爺
    - ペット合計レベル480
- 不滅猫魔
    - マナ究極スキルをもつ魔法キャラのみが対象
    - ショックロボット、猫の魔法使い、チャドは魔法キャラだがマナ究極スキルを持たないので非対象
    - モノポリー、タールはバフ自体はかかるが魔法ダメージを与えるスキルがないので実質非対象
- ルーン
- 遺物バンバ人形の1/100
- ドラゴンブロッブ
```

以下のバフの計算式は不明
```
- 神の石
- 無限モードのバフ
- ノイズキングペンギン
```

## 具体例
バンバ人形Lv9、ブロッブなし、ペットドラ爺Lv14、ペットレベル合計260の山賊のクリティカル確率は以下の通り
```
クリティカル確率 = 基礎値 + キャラ固有バフ + ペット + ルーン + バンバ人形 + ブロッブ
クリティカル確率% = 5% + 0% + (4%+0%) + 0% + 0.036% + 0%
クリティカル確率% = 9.036%
```

バンバ人形Lv11、ドラゴンブロッブ4.9%、ペットドラ爺Lv34、ペットレベル合計500、鬼神忍者Lv12、神話精密のルーン
```
クリティカル確率 = 基礎値 + キャラ固有バフ + ペット + ルーン + バンバ人形 + ブロッブ
クリティカル確率% = 5% + 15% + (7%+2%) + 3% + 0.040% + 4.9%
クリティカル確率% = 36.940%
```

## ロカパッシブについて
先ほどの計算式中のロカパッシブについては以下のように計算できる。

```
ロカパッシブ% = (敵の距離/7)*30%
```

敵との距離について、参考までに以下のようなキャラ射程を参照されたい
- 射程7.0：ロカ、ウチ
- 射程4.0：遠距離キャラ（e.g. ショックロボット、猫の魔法使い、重力弾など…）
- 射程2.1：近距離キャラ（e.g. 電気ロボット、バットマン、ランスロットなど…）

---

<details>
<summary>以下雑記</summary>

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


検証根拠:
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

全66件で (CriticalChance.RawValue - baseCritRaw) % 30 == 0 を満たしていて、ratio = distance / range; bonus = ratio * 30 のQuantumFP計算と一致しています。
```

</details>
