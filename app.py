from __future__ import annotations

import json
import math
import os
import hashlib
import random
from typing import Any, Dict, List

from flask import Flask, jsonify, request, send_from_directory
from simulator.awakened_hayley import mean_total_damage_15021
from simulator.hayley import mean_total_damage_5021
from simulator.rokechuu_oc import mean_total_damage_5115
from simulator.watt import mean_total_damage_5013
from simulator.chona import mean_total_damage_5019
from simulator.iam_meow import mean_total_damage_15004
from simulator.boss_senchoushi import mean_total_damage_15024
from simulator.doctorpulse import mean_total_damage_14002
from simulator.common_sim import mean_total_damage_common

APP_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(APP_DIR, "static")
DATA_DIR = os.path.join(APP_DIR, "data")
TICK_COEFF = 1000

app = Flask(__name__)


def load_characters() -> Dict[str, Dict[str, Any]]:
    path = os.path.join(DATA_DIR, "characters.json")
    with open(path, "r", encoding="utf-8") as f:
        obj = json.load(f)
    out: Dict[str, Dict[str, Any]] = {}
    for c in obj.get("characters", []):
        out[str(c["id"])] = c
    return out

def load_artifacts() -> Dict[str, Dict[str, Any]]:
    """
    lv4 = artifacts["力のポーション"]["effects"]["lv4"] # 13

    '力のポーション': {
        'no': 1, 'no_str': '01', 'grid': '1_1', 'tier': 'A', 'name': '力のポーション', 
        'effects': {'lv1': 10, 'lv2': 11, 'lv3': 12, 'lv4': 13, 'lv5': 14, 'lv6': 15, 'lv7': 16, 'lv8': 17, 'lv9': 18, 'lv10': 19, 'lv11': 20}, 
        'increment': '+１%', 'remarks': '実際の効果は表示値の２倍', 'image_url': 'https://img.atwiki.jp/luckydefense/attach/17/430/01.png'}, 
    '妖精の弓': {...},
    """
    path = os.path.join(DATA_DIR, "artifacts_expanded.json")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    artifacts_list = data["artifacts"]
    index: Dict[str, Dict[str, Any]] = {}

    for a in artifacts_list:
        name = a["name"]
        if name in index:
            raise ValueError(f"duplicate artifact name: {name!r}")
        index[name] = a
    return index

def load_enemies() -> Dict[str, Dict[str, Any]]:
    path = os.path.join(DATA_DIR, "enemy.json")
    with open(path, "r", encoding="utf-8") as f:
        obj = json.load(f)
    out = {}
    for e in obj.get("enemies", []):
        out[str(e["name"])] = e
    return out


ARTIFACTS_DB = load_artifacts()
CHAR_DB = load_characters()
ENEMY_DB = load_enemies()
ALLOWED_ENEMIES = set(ENEMY_DB.keys())
PHISICS_CHAR = [3007, 5001, 5005, 5010, 5011, 5012, 5014, 5015, 5019, 5020, 5023, 5114, 5115, 5214, 13007, 15010, 15011, 15020, 15023, 15110, 15210]


@app.get("/")
def index():
    return send_from_directory(STATIC_DIR, "index.html")


@app.get("/static/<path:filename>")
def static_files(filename: str):
    return send_from_directory(STATIC_DIR, filename)


@app.get("/data/<path:filename>")
def data_files(filename: str):
    return send_from_directory(DATA_DIR, filename)


def clamp_int(v: Any, lo: int, hi: int, default: int) -> int:
    try:
        x = int(v)
    except Exception:
        return default
    return max(lo, min(hi, x))


def clamp_float(v: Any, lo: float, hi: float, default: float) -> float:
    try:
        x = float(v)
    except Exception:
        return default
    return max(lo, min(hi, x))


def sign(n):
    if n:
        if n < 0:
            return -1
        return 1
    return 0


def compute_member_dps(character_id: str, common: Dict[str, Any], member: Dict[str, Any]) -> float:
    DebugMessage = []
    duration_sec = int(common.get("durationSec", 60))
    trials = int(common.get("trials", 1))
    all_relic_lv = int(common.get("allRelicLv", 1))
    ArtifactLv = all_relic_lv
    seed = int(common.get("seed", 0))
    coins = int(common.get("coins", 0))
    char_lv = int(member.get("charLv", 1))
    guildBlessing = int(common.get("guildBlessing", 0))
    guildBuff_atk = 0.02 if 1 <= guildBlessing else 0
    guildBuff_boss = 0.05 if 2 <= guildBlessing else 0
    unitLevelSumBuff = float(common.get("unitLevelSumBuff", 0)) / 100
    atkBuffPct = float(common.get("atkBuffPct", 0)) / 100
    speedBuffPct = float(common.get("speedBuffPct", 0)) / 100
    defDown = float(common.get("defDown", 190))
    enemy = str(common.get("enemy", "ノーマル80Wボス"))
    mythEnhanceLv = int(common.get("mythEnhanceLv", 1))

    if enemy == "ノーマル80Wボス":
        enemy_def = 148
    if enemy == "ハード80Wボス":
        enemy_def = 158
    if enemy == "地獄80Wボス":
        enemy_def = 158
    if enemy == "神80Wボス":
        enemy_def = 175
    
    def_mult = 1 + sign(defDown - enemy_def)*(1 - 50/(3*abs(defDown - enemy_def) + 50))

    treasure_lv = int(member.get("treasureLv", 1))
    money_gun_lv = int(common.get("moneyGunLv", all_relic_lv))
    power_potion_lv = int(common.get("powerPotionLv", all_relic_lv))
    fairy_bow_lv = int(common.get("fairyBowLv", all_relic_lv))
    great_sword_lv = int(common.get("greatSwordLv", all_relic_lv))
    secret_book_lv = int(common.get("secretBookLv", all_relic_lv))
    fruit_candy_lv = int(common.get("fruitCandyLv", all_relic_lv))
    bat_lv = int(common.get("batLv", all_relic_lv))
    wizard_hat_lv = int(common.get("wizardHatLv", all_relic_lv))
    bomb_lv = int(common.get("bombLv", all_relic_lv))
    old_book_lv = int(common.get("oldBookLv", all_relic_lv))
    sage_yogurt_lv = int(common.get("sageYogurtLv", all_relic_lv))
    magic_gauntlet_lv = int(common.get("magicGauntletLv", all_relic_lv))

    PowerPotion   = float(ARTIFACTS_DB["力のポーション"]["effects"]["lv" + str(power_potion_lv)]) / 100
    MoneyGun      = float(ARTIFACTS_DB["マネーガン"]["effects"]["lv" + str(money_gun_lv)]) / 100
    FairyBow      = float(ARTIFACTS_DB["妖精の弓"]["effects"][f"lv{fairy_bow_lv}"]) / 100
    GreatSword    = float(ARTIFACTS_DB["大剣"]["effects"][f"lv{great_sword_lv}"]) / 100
    SecretBook    = float(ARTIFACTS_DB["秘伝書"]["effects"][f"lv{secret_book_lv}"]) / 100
    FruitCandy    = float(ARTIFACTS_DB["フルーツ飴"]["effects"][f"lv{fruit_candy_lv}"])
    Bat           = float(ARTIFACTS_DB["バット"]["effects"][f"lv{bat_lv}"]) / 100
    WizardHat     = float(ARTIFACTS_DB["魔法使いの帽子"]["effects"][f"lv{wizard_hat_lv}"]) / 100
    Bomb          = float(ARTIFACTS_DB["爆弾"]["effects"][f"lv{bomb_lv}"]) / 100
    OldBook       = float(ARTIFACTS_DB["古びた本"]["effects"][f"lv{old_book_lv}"])
    SageYogurt    = float(ARTIFACTS_DB["賢者のヨーグルト"]["effects"][f"lv{sage_yogurt_lv}"]) / 100
    MagicGauntlet = float(ARTIFACTS_DB["マジック籠手"]["effects"][f"lv{magic_gauntlet_lv}"]) / 100

    mana_buff = int(common.get("manaRegenBuffPct", 0))
    mana_buff = 1 if mana_buff == 0 else mana_buff//100 + 1
    upgrade_atk = int(CHAR_DB[character_id]["upgrade_attack_damage"])
    base_speed = float(CHAR_DB[character_id]["attack_speed"])
    ult_mana = int(CHAR_DB[character_id]["sp"])
    lv1_atk = int(CHAR_DB[character_id]["attack_damage"])
    base_atk = lv1_atk + ((char_lv - 1) * upgrade_atk)
    
    starPower = int(member.get("starPower", 0))
    energyCount = int(member.get("energyCount", 0))
    robots = int(member.get("robots", 0))

    if char_lv < 3:
        lv_buff_atk, lv_buff_speed = 1.0, 1.0
    elif char_lv < 9:
        lv_buff_atk, lv_buff_speed = 1.1, 1.0
    elif char_lv < 15:
        lv_buff_atk, lv_buff_speed = 1.1, 1.1
    else:
        lv_buff_atk, lv_buff_speed = 1.2, 1.2
    
    base_atk *= lv_buff_atk
    base_speed *= lv_buff_speed

    atk = base_atk + member.get("blobintake", 0)
    atk *= 1 + PowerPotion*2 + member.get("cannibalCount", 0) + unitLevelSumBuff # ユニットレベル合計
    atk *= 1 + (int(common.get("mythEnhanceLv", 1)) - 1)*0.5 + int(member.get("ヴェイン", 0))
    if character_id in ["5023", "15004", "15011", "15024"]:
        atkBuffPct += 10
    if character_id in ["15023"]:
        atkBuffPct += 12
    if character_id in ["15021"]:
        atkBuffPct += 20
    atk *= 1 + coins*MoneyGun/100 + atkBuffPct + int(member.get("StrongestCreature", 0))*0.3 + int(member.get("バットマン", 0)) + int(member.get("マスタークン", 0)) 
    atk *= 1 + guildBuff_atk
    atk += base_atk
    speed = base_speed*(1 + speedBuffPct)*(1 + FairyBow)

    ans = 0
    if character_id == "1001":  # 弓兵
        ans = mean_total_damage_15021(
            ticks=int(speed * duration_sec * TICK_COEFF),
            trials=int(common.get("trials", 1)),
            seed=seed,
            attack_power=atk,
            attack_speed=speed,
            mana_buff=mana_buff,
        )
        ans = 1000
    elif character_id == "1002":  # 榴弾兵
        ans = mean_total_damage_15021(
            ticks=int(speed * duration_sec * TICK_COEFF),
            trials=int(common.get("trials", 1)),
            seed=seed,
            attack_power=atk,
            attack_speed=speed,
            mana_buff=mana_buff,
        )
        ans = 2000
    elif character_id == "1003":  # 野蛮人
        ans = mean_total_damage_15021(
            ticks=int(speed * duration_sec * TICK_COEFF),
            trials=int(common.get("trials", 1)),
            seed=seed,
            attack_power=atk,
            attack_speed=speed,
            mana_buff=mana_buff,
        )
        ans = 3000
    elif character_id == "1004":  # 水の精霊
        ans = mean_total_damage_15021(
            ticks=int(speed * duration_sec * TICK_COEFF),
            trials=int(common.get("trials", 1)),
            seed=seed,
            attack_power=atk,
            attack_speed=speed,
            mana_buff=mana_buff,
        )
        ans = 4000
    elif character_id == "1005":  # 山賊
        ans = mean_total_damage_15021(
            ticks=int(speed * duration_sec * TICK_COEFF),
            trials=int(common.get("trials", 1)),
            seed=seed,
            attack_power=atk,
            attack_speed=speed,
            mana_buff=mana_buff,
        )
        ans = 5000
    elif character_id == "2001":  # レンジャー
        ans = 6000
    elif character_id == "2002":  # ショックロボット
        ans = 7000
    elif character_id == "2003":  # 聖騎士
        ans = 8000
    elif character_id == "2004":  # サンドマン
        ans = 9000
    elif character_id == "2005":  # 悪魔の兵士
        ans = 10000
    elif character_id == "3001":  # 電気ロボット
        ans = 11000
    elif character_id == "3002":  # 木
        ans = 12000
    elif character_id == "3003":  # ハンター
        ans = 13000
    elif character_id == "3004":  # 重力弾
        ans = mean_total_damage_15021(
            ticks=int(speed * duration_sec * TICK_COEFF),
            trials=int(common.get("trials", 1)),
            seed=seed,
            attack_power=atk,
            attack_speed=speed,
            mana_buff=mana_buff,
        )
        ans = 14000
    elif character_id == "3005":  # イーグル将軍
        ans = 15000
    elif character_id == "3006":  # ウルフ戦士
        ans = 16000
    elif character_id == "3007":  # 忍者
        params = {
            "ticks": int(speed*duration_sec*TICK_COEFF),
            "trials": trials,
            "seed": seed,
            "attack_power": atk,
            "attack_speed": speed,
            "base_attack_mult": 1.0,
            "skill1_rate": 10 + OldBook,
            "skill1_mult": 40*(1+SecretBook+WizardHat),
            "skill2_rate": 12 + OldBook if 6 <= char_lv else 0,
            "skill2_mult": 60*(1+SecretBook+WizardHat),
            "skill3_rate": 0,
            "skill3_mult": 0,
            "ult_mana": 100*(1 - SageYogurt) if 12 <= char_lv else 10**100,
            "ult_mult": 180*(1+SecretBook+WizardHat),
            "attack_mana_recov": 1,
            "mana_buff": mana_buff,
            "crit_rate": 5,
            "crit_dmg": 2.5 + MagicGauntlet,
        }
        ans = mean_total_damage_common(params)
    elif character_id == "4001":  # オークシャーマン
        ans = mean_total_damage_15021(
            ticks=int(speed * duration_sec * TICK_COEFF),
            trials=int(common.get("trials", 1)),
            seed=seed,
            attack_power=atk,
            attack_speed=speed,
            mana_buff=mana_buff,
        )
        ans = 18000
    elif character_id == "4002":  # パルス発生器
        ans = mean_total_damage_15021(
            ticks=int(speed * duration_sec * TICK_COEFF),
            trials=int(common.get("trials", 1)),
            seed=seed,
            attack_power=atk,
            attack_speed=speed,
            mana_buff=mana_buff,
        )
        ans = 19000
    elif character_id == "4003":  # ウォーマシン
        ans = 20000
    elif character_id == "4004":  # 虎の師父
        ans = 21000
    elif character_id == "4005":  # 嵐の精霊
        ans = 22000
    elif character_id == "4006":  # 猫の魔法使い
        ans = mean_total_damage_15021(
            ticks=int(speed * duration_sec * TICK_COEFF),
            trials=int(common.get("trials", 1)),
            seed=seed,
            attack_power=atk,
            attack_speed=speed,
            mana_buff=mana_buff,
        )
        ans = 23000
    elif character_id == "4007":  # 保安官
        ans = 24000
    elif character_id == "4008":  # 謎のレジェンド
        ans = 25000
    elif character_id == "5001":  # バンバ
        ans = mean_total_damage_15021(
            ticks=int(speed * duration_sec * TICK_COEFF),
            trials=int(common.get("trials", 1)),
            seed=seed,
            attack_power=atk,
            attack_speed=speed,
            mana_buff=mana_buff,
        )
        ans = 26000
    elif character_id == "5002":  # コルディ
        ans = 27000
    elif character_id == "5003":  # ランスロット
        ans = 28000
    elif character_id == "5004":  # アイアンニャン
        params = {
            "ticks": int(speed*duration_sec*TICK_COEFF),
            "trials": trials,
            "seed": seed,
            "attack_power": atk,
            "attack_speed": speed,
            "base_attack_mult": 5.0,
            "skill1_rate": 8 + OldBook,
            "skill1_mult": 40*(1+SecretBook+WizardHat) if char_lv < 12 else 60*(1+SecretBook+WizardHat),
            "skill2_rate": 0,
            "skill2_mult": 0,
            "skill3_rate": 0,
            "skill3_mult": 0,
            "ult_mana": ult_mana*(1 - SageYogurt),
            "ult_mult": 180*(1+SecretBook+WizardHat) if char_lv < 12 else 270*(1+SecretBook+WizardHat),
            "attack_mana_recov": 1,
            "mana_buff": mana_buff,
            "crit_rate": 5,
            "crit_dmg": 2.5 + MagicGauntlet,
        }
        ans = mean_total_damage_common(params)
    elif character_id == "5005":  # ブロッブ
        ans = sp * 1000
    elif character_id == "5006":  # ドラゴン(変身前)
        ans = 0
    elif character_id == "5007":  # モノポリーマン
        ans = mean_total_damage_15021(
            ticks=int(speed * duration_sec * TICK_COEFF),
            trials=int(common.get("trials", 1)),
            seed=seed,
            attack_power=atk,
            attack_speed=speed,
            mana_buff=mana_buff,
        )
        ans = 32000
    elif character_id == "5008":  # ママ
        params = {
            "ticks": int(speed*duration_sec*TICK_COEFF),
            "trials": trials,
            "seed": seed,
            "attack_power": atk,
            "attack_speed": speed,
            "base_attack_mult": 5.0,
            "skill1_rate": 8 + OldBook if 6 <= char_lv else 0,
            "skill1_mult": 15*(1+SecretBook+WizardHat) if char_lv < 12 else 30*(1+SecretBook+WizardHat),
            "skill2_rate": 0,
            "skill2_mult": 0,
            "skill3_rate": 0,
            "skill3_mult": 0,
            "ult_mana": ult_mana*(1 - SageYogurt),
            "ult_mult": 20*(1+SecretBook+WizardHat) if char_lv < 12 else 40*(1+SecretBook+WizardHat),
            "attack_mana_recov": 1,
            "mana_buff": mana_buff,
            "crit_rate": 5,
            "crit_dmg": 2.5 + MagicGauntlet,
        }
        ans = mean_total_damage_common(params)
    elif character_id == "5009":  # カエルの王様
        
        
        ans = mean_total_damage_15021(
            ticks=int(speed * duration_sec * TICK_COEFF),
            trials=int(common.get("trials", 1)),
            seed=seed,
            attack_power=atk,
            attack_speed=speed,
            mana_buff=mana_buff,
        )
        ans = 34000
    elif character_id == "5010":  # バットマン
        params = {
            "ticks": int(speed*duration_sec*TICK_COEFF),
            "trials": trials,
            "seed": seed,
            "attack_power": atk,
            "attack_speed": speed,
            "base_attack_mult": 1.0,
            "skill1_rate": 12 + OldBook,
            "skill1_mult": 40*(1+SecretBook+Bat),
            "skill2_rate": 0,
            "skill2_mult": 0,
            "skill3_rate": 0,
            "skill3_mult": 0,
            "ult_mana": ult_mana,
            "ult_mult": 70*(1+SecretBook+Bat),
            "attack_mana_recov": 0,
            "mana_buff": 1,
            "crit_rate": 5,
            "crit_dmg": 2.5 + MagicGauntlet,
        }
        ans = mean_total_damage_common(params)
    elif character_id == "5011":  # ヴェイン
        
        
        ans = mean_total_damage_15021(
            ticks=int(speed * duration_sec * TICK_COEFF),
            trials=int(common.get("trials", 1)),
            seed=seed,
            attack_power=atk,
            attack_speed=speed,
            mana_buff=mana_buff,
        )
        ans = 36000
    elif character_id == "5012":  # インディ
        
        
        ans = mean_total_damage_15021(
            ticks=int(speed * duration_sec * TICK_COEFF),
            trials=int(common.get("trials", 1)),
            seed=seed,
            attack_power=atk,
            attack_speed=speed,
            mana_buff=mana_buff,
        )
        ans = 37000
    elif character_id == "5013":  # ワット（究極発動中）
        buff_mult = 0.03 if char_lv < 6 else 0.05
        ult_mult = 20*(1+SecretBook+WizardHat)
        speed *= 2 # 究極バフ
        cirt_dmg = 2.5 + MagicGauntlet
        ans = mean_total_damage_5013(
            tick=int(speed * duration_sec),
            attack_power=atk,
            attack_speed=speed,
            buff_mult=buff_mult,
            cirt_rate=5,
            cirt_dmg=cirt_dmg,
            ult_mult=ult_mult,
            watt_stack=energyCount,
        )
        ans *= TICK_COEFF # 相殺用
    elif character_id == "5014":  # タール小
        
        
        ans = mean_total_damage_15021(
            ticks=int(speed * duration_sec * TICK_COEFF),
            trials=int(common.get("trials", 1)),
            seed=seed,
            attack_power=atk,
            attack_speed=speed,
            mana_buff=mana_buff,
        )
        ans = 39000
    elif character_id == "5015":  # ロケッチュー(変身前)
        #ans = mean_total_damage_15021(
            #ticks=int(speed * duration_sec * TICK_COEFF),
            #trials=int(common.get("trials", 1)),
            #seed=seed,
            #attack_power=atk,
            #attack_speed=speed,
            #mana_buff=mana_buff,
        #)
        ans = 40000
    elif character_id == "5016":  # ウチ
        params = {
            "ticks": int(speed*duration_sec*TICK_COEFF),
            "trials": trials,
            "seed": seed,
            "attack_power": atk,
            "attack_speed": speed,
            "base_attack_mult": 1.0,
            "skill1_rate": 10 + OldBook if char_lv < 12 else 20 + OldBook,
            "skill1_mult": 75*(1+SecretBook+WizardHat),
            "skill2_rate": 0,
            "skill2_mult": 0,
            "skill3_rate": 0,
            "skill3_mult": 0,
            "ult_mana": ult_mana*(1 - SageYogurt),
            "ult_mult": 398*(1+SecretBook+WizardHat),
            "attack_mana_recov": 1,
            "mana_buff": mana_buff,
            "crit_rate": 5,
            "crit_dmg": 2.5 + MagicGauntlet,
        }
        ans = mean_total_damage_common(params)
        if 6 <= char_lv:
            ans *= 8
    elif character_id == "5017":  # ビリ
        
        
        ans = mean_total_damage_15021(
            ticks=int(speed * duration_sec * TICK_COEFF),
            trials=int(common.get("trials", 1)),
            seed=seed,
            attack_power=atk,
            attack_speed=speed,
            mana_buff=mana_buff,
        )
        ans = 42000
    elif character_id == "5018":  # マスタークン
        
        
        ans = mean_total_damage_15021(
            ticks=int(speed * duration_sec * TICK_COEFF),
            trials=int(common.get("trials", 1)),
            seed=seed,
            attack_power=atk,
            attack_speed=speed,
            mana_buff=mana_buff,
        )
        ans = 43000
    elif character_id == "5019":  # チョナ
        skill1_rate = 15 + OldBook if 6 <= char_lv else 10 + OldBook
        skill1_mult = 60*(1+SecretBook+Bat)
        skill2_mult = 70*(1+SecretBook+Bat)
        ult_mult = 750 if char_lv < 12 else 894
        ult_mult *= 1 + SecretBook + Bat
        ult_mana = 40
        crit_dmg = 2.5
        ans = mean_total_damage_5019(
            ticks=int(speed*duration_sec*TICK_COEFF),
            trials=trials,
            seed=seed,
            skill1_rate=skill1_rate,
            attack_speed=speed,
            attack_power=atk,
            skill1_mult=skill1_mult,
            skill2_mult=skill2_mult,
            ult_mana=ult_mana,
            ult_mult=ult_mult,
            cirt_rate=5,
            cirt_dmg=crit_dmg,
        )
    elif character_id == "5020":  # ペンギン楽師
        params = {
            "ticks": int(speed*duration_sec*TICK_COEFF),
            "trials": trials,
            "seed": seed,
            "attack_power": atk,
            "attack_speed": speed,
            "base_attack_mult": 1.0,
            "skill1_rate": 10 + OldBook,
            "skill1_mult": 0,
            "skill2_rate": 10+OldBook if char_lv < 6 else 15+OldBook,
            "skill2_mult": 60*(1+SecretBook+Bat),
            "skill3_rate": 0,
            "skill3_mult": 0,
            "ult_mana": 10**100,
            "ult_mult": 1,
            "attack_mana_recov": 1,
            "mana_buff": mana_buff,
            "crit_rate": 5,
            "crit_dmg": 2.5 + MagicGauntlet,
        }
        ans = mean_total_damage_common(params)
    elif character_id == "5021":  # ヘイリー
        skill1_rate = 10 + OldBook
        skill2_rate = 0 if char_lv < 12 else 12 + OldBook
        skill1_mult = 50*(1+SecretBook+WizardHat)
        skill2_mult = 50*(1+SecretBook+WizardHat)
        ult_mana = 250*(1 - SageYogurt)
        crit_dmg = 2.5 + MagicGauntlet

        starPower_mult = 2 if char_lv < 6 else 4
        atk = base_atk
        atk *= 1 + PowerPotion*2 + unitLevelSumBuff
        atk *= 1 + (int(common.get("mythEnhanceLv", 1)) - 1)*0.5
        atk *= 1 + coins*MoneyGun/100 + atkBuffPct + starPower*starPower_mult
        atk *= 1 + guildBuff_atk
        atk += base_atk

        attack_power_ult = base_atk
        attack_power_ult *= 1 + PowerPotion*2 + unitLevelSumBuff
        attack_power_ult *= 1 + (int(common.get("mythEnhanceLv", 1)) - 1)*0.5
        attack_power_ult *= 1 + coins*MoneyGun/100 + atkBuffPct + starPower*starPower_mult*1.5
        attack_power_ult *= 1 + guildBuff_atk
        attack_power_ult += base_atk

        ans = mean_total_damage_5021(
            ticks=int(speed*duration_sec*TICK_COEFF),
            trials=trials,
            seed=seed,
            skill1_rate=skill1_rate,
            skill2_rate=skill2_rate,
            attack_speed=speed,
            attack_power=atk,
            skill1_mult=skill1_mult,
            skill2_mult=skill2_mult,
            attack_power_ult=attack_power_ult,
            ult_mana=ult_mana,
            mana_buff=mana_buff,
            tick_seconds=1.0,
            crit_rate=5,
            crit_dmg=crit_dmg,
        )
    elif character_id == "5022":  # アト
        
        
        ans = mean_total_damage_15021(
            ticks=int(speed * duration_sec * TICK_COEFF),
            trials=int(common.get("trials", 1)),
            seed=seed,
            attack_power=atk,
            attack_speed=speed,
            mana_buff=mana_buff,
        )
        ans = 47000
    elif character_id == "5023":  # ロカ
        
        
        ans = mean_total_damage_15021(
            ticks=int(speed * duration_sec * TICK_COEFF),
            trials=int(common.get("trials", 1)),
            seed=seed,
            attack_power=atk,
            attack_speed=speed,
            mana_buff=mana_buff,
        )
        ans = 48000
    elif character_id == "5024":  # 選鳥師
        
        
        ans = mean_total_damage_15021(
            ticks=int(speed * duration_sec * TICK_COEFF),
            trials=int(common.get("trials", 1)),
            seed=seed,
            attack_power=atk,
            attack_speed=speed,
            mana_buff=mana_buff,
        )
        ans = 49000
    elif character_id == "5104":  # アイアンニャン
        params = {
            "ticks": int(speed*duration_sec*TICK_COEFF),
            "trials": trials,
            "seed": seed,
            "attack_power": atk,
            "attack_speed": speed,
            "base_attack_mult": 1.0,
            "skill1_rate": 8 + OldBook,
            "skill1_mult": 50*(1+SecretBook+WizardHat),
            "skill2_rate": 10 + OldBook,
            "skill2_mult": 60*(1+SecretBook+WizardHat),
            "skill3_rate": 0,
            "skill3_mult": 0,
            "ult_mana": 100*(1 - SageYogurt) if 12 <= char_lv else 10**100,
            "ult_mult": 180*(1+SecretBook+WizardHat),
            "attack_mana_recov": 1,
            "mana_buff": mana_buff,
            "crit_rate": 5,
            "crit_dmg": 2.5 + MagicGauntlet,
        }
        ans = mean_total_damage_common(params)
    elif character_id == "5106":  # ドラゴン(変身後)
        params = {
            "ticks": int(speed*duration_sec*TICK_COEFF),
            "trials": trials,
            "seed": seed,
            "attack_power": atk,
            "attack_speed": speed,
            "base_attack_mult": 1.0,
            "skill1_rate": 8 + OldBook,
            "skill1_mult": 50*(1+SecretBook+WizardHat),
            "skill2_rate": 10 + OldBook,
            "skill2_mult": 60*(1+SecretBook+WizardHat),
            "skill3_rate": 0,
            "skill3_mult": 0,
            "ult_mana": 100*(1 - SageYogurt) if 12 <= char_lv else 10**100,
            "ult_mult": 180*(1+SecretBook+WizardHat),
            "attack_mana_recov": 1,
            "mana_buff": mana_buff,
            "crit_rate": 5,
            "crit_dmg": 2.5 + MagicGauntlet,
        }
        ans = mean_total_damage_common(params)
    elif character_id == "5108":  # インプ
        
        
        ans = mean_total_damage_15021(
            ticks=int(speed * duration_sec * TICK_COEFF),
            trials=int(common.get("trials", 1)),
            seed=seed,
            attack_power=atk,
            attack_speed=speed,
            mana_buff=mana_buff,
        )
        ans = 52000
    elif character_id == "5109":  # キングダイアン
        params = {
            "ticks": int(speed*duration_sec*TICK_COEFF),
            "trials": trials,
            "seed": seed,
            "attack_power": atk,
            "attack_speed": speed,
            "base_attack_mult": 7.5,
            "skill1_rate": 0,
            "skill1_mult": 0,
            "skill2_rate": 0,
            "skill2_mult": 0,
            "skill3_rate": 0,
            "skill3_mult": 0,
            "ult_mana": ult_mana*(1 - SageYogurt),
            "ult_mult": 1000*(1+SecretBook+WizardHat),
            "attack_mana_recov": 1,
            "mana_buff": mana_buff,
            "crit_rate": 5,
            "crit_dmg": 2.5 + MagicGauntlet,
        }
        ans = mean_total_damage_common(params)
    elif character_id == "5114":  # タール中
        
        
        ans = mean_total_damage_15021(
            ticks=int(speed * duration_sec * TICK_COEFF),
            trials=int(common.get("trials", 1)),
            seed=seed,
            attack_power=atk,
            attack_speed=speed,
            mana_buff=mana_buff,
        )
        ans = 54000
    elif character_id == "5115":  # ロケッチュー(変身後)
        skill1_rate = 10 + OldBook
        skill1_mult = 60*(1+SecretBook+Bat)
        skill2_mult = 160*(1+SecretBook+Bat) if 12 <= char_lv else 1
        ult_mult = 700*(1+SecretBook+Bat)
        ult_mana = 25
        crit_dmg = 2.5
        ans = mean_total_damage_5115(
            ticks=int(speed*duration_sec*TICK_COEFF),
            trials=trials,
            seed=seed,
            skill1_rate=skill1_rate,
            attack_speed=speed,
            attack_power=atk,
            skill1_mult=skill1_mult,
            skill2_mult=skill2_mult,
            ult_mana=ult_mana,
            ult_mult=ult_mult,
            tick_seconds=1.0,
            cirt_rate=5,
            cirt_dmg=crit_dmg,
        )
        ans *= 1.5 # 最先端ロボット
    elif character_id == "5204":  # アイアンニャンv2
        params = {
            "ticks": int(speed*duration_sec*TICK_COEFF),
            "trials": trials,
            "seed": seed,
            "attack_power": atk,
            "attack_speed": speed,
            "base_attack_mult": 5.0,
            "skill1_rate": 8 + OldBook,
            "skill1_mult": 50*(1+SecretBook+WizardHat) if char_lv < 12 else 75*(1+SecretBook+WizardHat),
            "skill2_rate": 0,
            "skill2_mult": 0,
            "skill3_rate": 0,
            "skill3_mult": 0,
            "ult_mana": ult_mana*(1 - SageYogurt),
            "ult_mult": 360*(1+SecretBook+WizardHat) if char_lv < 12 else 540*(1+SecretBook+WizardHat),
            "attack_mana_recov": 1,
            "mana_buff": mana_buff,
            "crit_rate": 5,
            "crit_dmg": 2.5 + MagicGauntlet,
        }
        ans = mean_total_damage_common(params)
    elif character_id == "5206":  # 偉大な卵
        
        
        ans = mean_total_damage_15021(
            ticks=int(speed * duration_sec * TICK_COEFF),
            trials=int(common.get("trials", 1)),
            seed=seed,
            attack_power=atk,
            attack_speed=speed,
            mana_buff=mana_buff,
        )
        ans = 57000
    elif character_id == "5214":  # タール大
        
        
        ans = mean_total_damage_15021(
            ticks=int(speed * duration_sec * TICK_COEFF),
            trials=int(common.get("trials", 1)),
            seed=seed,
            attack_power=atk,
            attack_speed=speed,
            mana_buff=mana_buff,
        )
        ans = 58000
    elif character_id == "5306":  # ドレイン
        params = {
            "ticks": int(speed*duration_sec*TICK_COEFF),
            "trials": trials,
            "seed": seed,
            "attack_power": atk,
            "attack_speed": speed,
            "base_attack_mult": 1.0,
            "skill1_rate": 8 + OldBook,
            "skill1_mult": 75*(1+SecretBook+WizardHat),
            "skill2_rate": 10 + OldBook,
            "skill2_mult": 85*(1+SecretBook+WizardHat),
            "skill3_rate": 0,
            "skill3_mult": 0,
            "ult_mana": ult_mana*(1 - SageYogurt) if 12 <= char_lv else 10**100,
            "ult_mult": 255*(1+SecretBook+WizardHat),
            "attack_mana_recov": 1,
            "mana_buff": mana_buff,
            "crit_rate": 5,
            "crit_dmg": 2.5 + MagicGauntlet,
        }
        ans = mean_total_damage_common(params)
    elif character_id == "13004":  # スーパー重力弾
        
        
        ans = mean_total_damage_15021(
            ticks=int(speed * duration_sec * TICK_COEFF),
            trials=int(common.get("trials", 1)),
            seed=seed,
            attack_power=atk,
            attack_speed=speed,
            mana_buff=mana_buff,
        )
        ans = 60000
    elif character_id == "13007":  # 鬼神忍者
        
        
        ans = mean_total_damage_15021(
            ticks=int(speed * duration_sec * TICK_COEFF),
            trials=int(common.get("trials", 1)),
            seed=seed,
            attack_power=atk,
            attack_speed=speed,
            mana_buff=mana_buff,
        )
        ans = 61000
    elif character_id == "14002":  # ドクターパルス
        skill1_rate = 10 + OldBook
        skill1_mult = 70*(1+SecretBook+WizardHat)
        ult_mana = 550*(1 - SageYogurt)
        ult_mult = 120*(1 - SageYogurt)
        crit_dmg = 2.5 + MagicGauntlet
        ans = mean_total_damage_14002(
            ticks=int(speed*duration_sec*TICK_COEFF),
            trials=trials,
            seed=seed,
            robots=robots,
            attack_speed=speed,
            attack_power=atk,
            skill1_rate=skill1_rate,
            skill1_mult=skill1_mult,
            ult_mana=ult_mana,
            ult_mult=ult_mult,
            mana_buff=mana_buff,
            crit_rate=5,
            crit_dmg=crit_dmg,
        )
        if 12 <= char_lv:
            ans *= (1 + 0.15*robots)
    elif character_id == "15004":  # アイアムニャン
        skill1_rate = 11 + OldBook if 12 <= char_lv else 7 + OldBook
        skill2_rate = 11 + OldBook if 12 <= char_lv else 7 + OldBook
        skill1_mult = 180*(1+SecretBook+WizardHat)
        skill2_mult = 100*(1+SecretBook+WizardHat)
        ult_mana = 300*(1 - SageYogurt)
        ult_mult = 1000*(1+SecretBook+WizardHat) if char_lv < 6 else 1500*(1+SecretBook+WizardHat)
        ult_cooldown = int(speed*3) if char_lv < 6 else int(speed*4.5)
        crit_dmg = 2.5 + MagicGauntlet
        ans = mean_total_damage_15004(
            ticks=int(speed*duration_sec*TICK_COEFF),
            trials=trials,
            seed=seed,
            attack_power=atk,
            attack_speed=speed,
            skill1_rate=skill1_rate,
            skill2_rate=skill2_rate,
            skill1_mult=skill1_mult,
            skill2_mult=skill2_mult,
            ult_mult=ult_mult,
            ult_mana=ult_mana,
            ult_cooldown=ult_cooldown,
            mana_buff=mana_buff,
            crit_rate=5,
            crit_dmg=crit_dmg,
        )
        ans *= (1 + mana_buff//0.5 * 0.05) # アイアムニャンパッシブ
    elif character_id == "15006":  # 魔王ドラゴン
        ans = mean_total_damage_15021(
            ticks=int(speed * duration_sec * TICK_COEFF),
            trials=int(common.get("trials", 1)),
            seed=seed,
            attack_power=atk,
            attack_speed=speed,
            mana_buff=mana_buff,
        )
        ans = 64000
    elif character_id == "15008":  # グランドママ
        ans = mean_total_damage_15021(
            ticks=int(speed * duration_sec * TICK_COEFF),
            trials=int(common.get("trials", 1)),
            seed=seed,
            attack_power=atk,
            attack_speed=speed,
            mana_buff=mana_buff,
        )
        ans = 65000
    elif character_id == "15009":  # カエルの死神
        params = {
            "ticks": int(speed*duration_sec*TICK_COEFF),
            "trials": trials,
            "seed": seed,
            "attack_power": atk,
            "attack_speed": speed,
            "base_attack_mult": 1.0,
            "skill1_rate": 8 + OldBook,
            "skill1_mult": 120*(1+SecretBook+WizardHat),
            "skill2_rate": 12 + OldBook,
            "skill2_mult": 90*(1+SecretBook+WizardHat),
            "skill3_rate": 0,
            "skill3_mult": 0,
            "ult_mana": 10**100,
            "ult_mult": 1,
            "attack_mana_recov": 1,
            "mana_buff": mana_buff,
            "crit_rate": 5,
            "crit_dmg": 2.5 + MagicGauntlet,
        }
        ans = mean_total_damage_common(params)
    elif character_id == "15010":  # エースバットマン
        ans = mean_total_damage_15021(
            ticks=int(speed * duration_sec * TICK_COEFF),
            trials=int(common.get("trials", 1)),
            seed=seed,
            attack_power=atk,
            attack_speed=speed,
            mana_buff=mana_buff,
        )
        ans = 67000
    elif character_id == "15011":  # トップヴェイン
        ans = mean_total_damage_15021(
            ticks=int(speed * duration_sec * TICK_COEFF),
            trials=int(common.get("trials", 1)),
            seed=seed,
            attack_power=atk,
            attack_speed=speed,
            mana_buff=mana_buff,
        )
        ans = 68000
    elif character_id == "15020":  # ノイズペンギンキング
        ans = mean_total_damage_15021(
            ticks=int(speed * duration_sec * TICK_COEFF),
            trials=int(common.get("trials", 1)),
            seed=seed,
            attack_power=atk,
            attack_speed=speed,
            mana_buff=mana_buff,
        )
        ans = 69000
    elif character_id == "15021":  # 覚醒ヘイリー
        skill1_rate = 10 + OldBook
        skill2_rate = 15 + OldBook if 12 <= char_lv else 10 + OldBook
        skill1_mult = 180*(1+SecretBook+WizardHat)
        skill2_mult = 100*(1+SecretBook+WizardHat)
        skill3_mult = 1125*(1+SecretBook+WizardHat)
        ult_mana = 250*(1 - SageYogurt)
        crit_dmg = 2.5 + MagicGauntlet
        ans = mean_total_damage_15021(
            ticks=int(speed*duration_sec*TICK_COEFF),
            trials=trials,
            seed=seed,
            skill1_rate=skill1_rate,
            skill2_rate=skill2_rate,
            attack_speed=speed,
            attack_power=atk,
            skill1_mult=skill1_mult,
            skill2_mult=skill2_mult,
            skill3_mult=skill3_mult,
            ult_mana=ult_mana,
            mana_buff=mana_buff,
            tick_seconds=1.0,
            crit_rate=5,
            crit_dmg=crit_dmg,
        )
        ans *= (1 + int(member.get("mythCount")) * 0.05) # 覚醒ヘイリーパッシブ
    elif character_id == "15022":  # 時空アト
        ans = mean_total_damage_15021(
            ticks=int(speed * duration_sec * TICK_COEFF),
            trials=int(common.get("trials", 1)),
            seed=seed,
            attack_power=atk,
            attack_speed=speed,
            mana_buff=mana_buff,
        )
        ans = 70000
    elif character_id == "15023":  # キャプテン・ロカ
        ans = mean_total_damage_15021(
            ticks=int(speed * duration_sec * TICK_COEFF),
            trials=int(common.get("trials", 1)),
            seed=seed,
            attack_power=atk,
            attack_speed=speed,
            mana_buff=mana_buff,
        )
        ans = 71000
    elif character_id == "15024":  # ボス選鳥師
        skill1_rate = 11 + OldBook 
        skill2_rate = 10 + OldBook
        skill1_mult = 330*(1+SecretBook+WizardHat)
        skill2_mult = 160*(1+SecretBook+WizardHat)
        skill3_mult = 5*(1+SecretBook+WizardHat) + 5 if 6 <= char_lv else 5*(1+SecretBook+WizardHat)
        ult_mana = 250*(1 - SageYogurt)
        ult_mult = 300*(1+SecretBook+WizardHat)
        crit_dmg = 2.5 + MagicGauntlet
        ult_buff = 5 if char_lv < 12 else 10
        ans = mean_total_damage_15024(
            ticks=int(speed*duration_sec*TICK_COEFF),
            trials=trials,
            seed=seed,
            attack_power=atk,
            attack_speed=speed,
            skill1_rate=skill1_rate,
            skill2_rate=skill2_rate,
            skill1_mult=skill1_mult,
            skill2_mult=skill2_mult,
            skill3_mult=skill3_mult,
            crit_rate=5,
            crit_dmg=crit_dmg,
            ult_mult=ult_mult,
            ult_buff=ult_buff,
            ult_mana=ult_mana,
            mana_buff=mana_buff,
        )
    elif character_id == "15109":  # 死神ダイアン
        params = {
            "ticks": int(speed*duration_sec*TICK_COEFF),
            "trials": trials,
            "seed": seed,
            "attack_power": atk,
            "attack_speed": speed,
            "base_attack_mult": 20.0,
            "skill1_rate": 8 + OldBook if char_lv < 6 else 13 + OldBook,
            "skill1_mult": 1750*(1+SecretBook+WizardHat),
            "skill2_rate": 0,
            "skill2_mult": 0,
            "skill3_rate": 0,
            "skill3_mult": 0,
            "ult_mana": ult_mana*(1 - SageYogurt),
            "ult_mult": 1200*(1+SecretBook+WizardHat),
            "attack_mana_recov": 1,
            "mana_buff": mana_buff,
            "crit_rate": 5,
            "crit_dmg": 2.5 + MagicGauntlet,
        }
        ans = mean_total_damage_common(params)
    elif character_id == "15110":  # バットマン投手
        ans = mean_total_damage_15021(
            ticks=int(speed * duration_sec * TICK_COEFF),
            trials=int(common.get("trials", 1)),
            seed=seed,
            attack_power=atk,
            attack_speed=speed,
            mana_buff=mana_buff,
        )
        ans = 74000
    elif character_id == "15210":  # バットマン打者
        ans = mean_total_damage_15021(
            ticks=int(speed * duration_sec * TICK_COEFF),
            trials=int(common.get("trials", 1)),
            seed=seed,
            attack_power=atk,
            attack_speed=speed,
            mana_buff=mana_buff,
        )
        ans = 75000
    else:
        ans = 0
    if int(character_id) in PHISICS_CHAR:
        ans *= def_mult
    DebugMessage.append(atk)
    DebugMessage.append(speed)
    DebugMessage.append(ult_mana)
    return (ans / TICK_COEFF) * float(common.get("multiplier", 1)) * (1 + GreatSword) * (1 + Bomb), str(DebugMessage)



ALLOWED_ENEMIES = {
    "ノーマル80Wボス",
    "ハード80Wボス",
    "地獄80Wボス",
    "神80Wボス",
}

@app.post("/api/calc")
def api_calc():
    data = request.get_json(force=True, silent=False)
    if not isinstance(data, dict):
        return jsonify({"error": "invalid json"}), 400

    common = data.get("options", {})
    party = data.get("party", [])
    if not isinstance(common, dict) or not isinstance(party, list) or len(party) == 0:
        return jsonify({"error": "options/party invalid"}), 400

    enemy = str(common.get("enemy", "ノーマル80Wボス"))
    if enemy not in ALLOWED_ENEMIES:
        enemy = "ノーマル80Wボス"

    duration_sec = clamp_float(common.get("durationSec", 60), 1, 24 * 3600, 60)

    # 全遺物レベル (1..11)
    all_relic_lv = clamp_int(common.get("allRelicLv", common.get("relicLv", 1)), 1, 11, 1)

    # 神話強化レベル
    mythEnhanceLv = clamp_int(common.get("mythEnhanceLv", 0), 1, 35, 1)

    # trials (1,3,10,30,100)
    trials = clamp_int(common.get("trials", 3), 1, 100, 3)
    if trials not in (1, 3, 10, 30, 100):
        trials = 3

    # SEED値
    seed = clamp_int(common.get("seed", 1), -2_147_483_648, 2_147_483_647, 1)

    # buffs / params
    atk_buff_pct = clamp_float(common.get("atkBuffPct", 0), -1000, 10000, 0)
    speed_buff_pct = clamp_float(common.get("speedBuffPct", 0), -1000, 10000, 0)
    multiplier = clamp_float(common.get("multiplier", 1), -2_147_483_648, 2_147_483_647, 1)

    mana_regen_buff_pct = clamp_int(common.get("manaRegenBuffPct", 0), 0, 700, 0)
    if mana_regen_buff_pct not in (0, 100, 200, 300, 400, 500, 600, 700):
        mana_regen_buff_pct = 0

    def_down = clamp_float(common.get("defDown", 190), -10_000_000, 10_000_000, 190)
    coins = clamp_int(common.get("coins", 300000), 0, 2_000_000_000, 300000)

    guildBlessing = clamp_int(common.get("guildBlessing", 0), 0, 2, 0)
    unitLevelSumBuff = clamp_float(common.get("unitLevelSumBuff", 0), 0, 25, 0)

    # tick秒はUIから削除したので固定扱い（必要ならゲーム仕様に合わせて変更）
    tick_sec = 1.0
    ticks = int(duration_sec / tick_sec)

    def clamp_relic_lv(key: str) -> int:
        return clamp_int(common.get(key, all_relic_lv), 1, 11, all_relic_lv)

    money_gun_lv = clamp_relic_lv("moneyGunLv")
    power_potion_lv = clamp_relic_lv("powerPotionLv")
    fairy_bow_lv = clamp_relic_lv("fairyBowLv")
    great_sword_lv = clamp_relic_lv("greatSwordLv")
    secret_book_lv = clamp_relic_lv("secretBookLv")
    fruit_candy_lv = clamp_relic_lv("fruitCandyLv")
    bat_lv = clamp_relic_lv("batLv")
    wizard_hat_lv = clamp_relic_lv("wizardHatLv")
    bomb_lv = clamp_relic_lv("bombLv")
    old_book_lv = clamp_relic_lv("oldBookLv")
    sage_yogurt_lv = clamp_relic_lv("sageYogurtLv")
    magic_gauntlet_lv = clamp_relic_lv("magicGauntletLv")

    common_s = {
        "enemy": enemy,
        "durationSec": duration_sec,
        "tickSec": tick_sec,
        "trials": trials,
        "seed": seed,
        "multiplier": multiplier,
        "allRelicLv": all_relic_lv,
        "mythEnhanceLv": mythEnhanceLv,
        "atkBuffPct": atk_buff_pct,
        "manaRegenBuffPct": mana_regen_buff_pct,
        "speedBuffPct": speed_buff_pct,
        "defDown": def_down,
        "coins": coins,
        "moneyGunLv": money_gun_lv,
        "powerPotionLv": power_potion_lv,
        "fairyBowLv": fairy_bow_lv,
        "greatSwordLv": great_sword_lv,
        "secretBookLv": secret_book_lv,
        "fruitCandyLv": fruit_candy_lv,
        "batLv": bat_lv,
        "wizardHatLv": wizard_hat_lv,
        "bombLv": bomb_lv,
        "oldBookLv": old_book_lv,
        "sageYogurtLv": sage_yogurt_lv,
        "magicGauntletLv": magic_gauntlet_lv,
        "guildBlessing": guildBlessing,
        "unitLevelSumBuff": unitLevelSumBuff,
    }

    members_out: List[Dict[str, Any]] = []
    dps_list: List[float] = []
    DebugMessages = dict()
    char_ids: List[str] = []

    for m in party:
        if not isinstance(m, dict):
            return jsonify({"error": "party must be list of objects"}), 400

        cid = str(m.get("character", ""))
        if cid not in CHAR_DB:
            return jsonify({"error": f"unknown character: {cid}"}), 400

        char_lv = clamp_int(m.get("charLv", 1), 1, 15, 1)
        treasure_lv = clamp_int(m.get("treasureLv", 1), 1, 15, 1)

        member_s: Dict[str, Any] = {
            "character": cid,
            "charLv": char_lv,
            "treasureLv": treasure_lv,
        }

        # === Extra per-character parameters (UI dropdowns) ===
        # 既存の計算ロジック（compute_member_dps）は変更せず、
        # ここで入力の正規化・バリデーションと、既存キーへのエイリアス付与だけ行う。
        cname = str(CHAR_DB.get(cid, {}).get("name", ""))

        # 覚醒ヘイリー：異種神話数
        if cid == "15021" or cname == "覚醒ヘイリー":
            member_s["mythCount"] = clamp_int(m.get("mythCount", 0), 0, 30, 1)

        # ブロッブ：摂取値
        if cid == "5005" or cname == "ブロッブ":
            v = clamp_float(m.get("intake", 0), 0, 1_000_000, 0)
            member_s["intake"] = v
            # 既存実装の参照キー（compute_member_dps 内で blobintake を参照）
            member_s["blobintake"] = v

        # ウチ：マス数（1..5）
        if cid == "5016" or cname == "ウチ":
            member_s["uchiCells"] = clamp_int(m.get("uchiCells", 1), 1, 5, 1)

        # バットマン：バット強化（1..20）
        if cid == "5010" or cname == "バットマン":
            member_s["batEnhance"] = clamp_int(m.get("batEnhance", 1), 1, 20, 1)

        # ヘイリー：星の力（0..10）
        if cid == "5021" or cname == "ヘイリー":
            member_s["starPower"] = clamp_int(m.get("starPower", 0), 0, 10, 0)

        # マスタークン：感情コントロール（0..99）
        if cid == "5018" or cname == "マスタークン":
            member_s["emotionControl"] = clamp_int(m.get("emotionControl", 0), 0, 99, 0)

        # ランスロット：火花追加ダメージ（0.0..3.0）
        if cid == "5003" or cname == "ランスロット":
            member_s["sparkBonusDmg"] = clamp_float(m.get("sparkBonusDmg", 0.0), 0.0, 3.0, 0.0)

        # ワット（究極発動中）：エネルギー個数（1以上）
        if cid == "5013" or cname == "ワット":
            ec = clamp_int(m.get("energyCount", 1), 1, 2_000_000_000, 1)
            member_s["energyCount"] = ec
            # 既存実装の参照キー（compute_member_dps 内で "ワットスタック" を参照）
            #member_s["ワットスタック"] = ec

        # アイアンニャンv2：技術強化（0..10）
        if cid == "5204" or ("アイアンニャンv2" in cname):
            member_s["techEnhance"] = clamp_int(m.get("techEnhance", 0), 0, 10, 0)

        # 選鳥師：スコア（0..100）
        if ("選鳥師" in cname) or (cid in ("5024", "15024")):
            member_s["score"] = clamp_int(m.get("score", 0), 0, 100, 0)

        # タール：共食い回数（0以上）※タール小/中/大をまとめて適用
        if ("タール" in cname) or (cid in ("5014", "5114", "5214")):
            cc = clamp_int(m.get("cannibalCount", 0), 0, 2_000_000_000, 0)
            member_s["cannibalCount"] = cc
            # 既存実装の参照キー（compute_member_dps 内で "タール共食い" を参照）
            #member_s["タール共食い"] = cc

        # バンバ：鍛錬（0..30）
        if cid == "5001" or cname == "バンバ":
            member_s["training"] = clamp_int(m.get("training", 0), 0, 30, 0)
        
        # ドラゴン：最強の生物
        if cid == "5106" or cname == "ドラゴン":
            member_s["StrongestCreature"] = clamp_int(m.get("StrongestCreature", 1), 1, 1000, 0)

        # ドラゴン：最強の生物
        if cid == "14002" or cname == "ドクターパルス":
            member_s["robots"] = clamp_int(m.get("robots", 1), 1, 4, 1)

        # === per-member common option aliases ===
        # 既存実装が common["バットマン"/"ヘイリー"/"マスタークン"] を参照しているため、
        # member 由来の値をこのメンバー計算時だけ注入する（他メンバーへ影響しない）。
        common_m = dict(common_s)
        #if "batEnhance" in member_s:
            #common_m["バットマン"] = member_s["batEnhance"]
        #if "starPower" in member_s:
            #common_m["ヘイリー"] = member_s["starPower"]
        #if "emotionControl" in member_s:
            #common_m["マスタークン"] = member_s["emotionControl"]

        dps, DebugMessage = compute_member_dps(cid, common_m, member_s)
        dps_list.append(dps)
        DebugMessages[cname] = str(DebugMessage)

        members_out.append(
            {
                "character": cid,
                "charLv": char_lv,
                "treasureLv": treasure_lv,
                "intake": member_s.get("intake"),
                "mythCount": member_s.get("mythCount"),
                "uchiCells": member_s.get("uchiCells"),
                "batEnhance": member_s.get("batEnhance"),
                "starPower": member_s.get("starPower"),
                "emotionControl": member_s.get("emotionControl"),
                "sparkBonusDmg": member_s.get("sparkBonusDmg"),
                "energyCount": member_s.get("energyCount"),
                "techEnhance": member_s.get("techEnhance"),
                "score": member_s.get("score"),
                "cannibalCount": member_s.get("cannibalCount"),
                "training": member_s.get("training"),
                "StrongestCreature": member_s.get("StrongestCreature"),
                "robots": member_s.get("robots"),
                "dps": dps,
            }
        )

    total = sum(dps_list)

    if total > 0:
        for i in range(len(members_out)):
            members_out[i]["share"] = dps_list[i] / total
    else:
        eq = 1.0 / len(members_out)
        for i in range(len(members_out)):
            members_out[i]["share"] = eq

    return jsonify(
        {
            "meta": {"ticks": ticks, "trials": trials},  # フロント表示はしないが、残してOK
            "totalDps": total,
            "members": members_out,
            "Debug": DebugMessages,
        }
    )
