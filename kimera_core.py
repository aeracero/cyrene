# kimera_core.py
import json
import random
import math
from pathlib import Path
from kimera_data import BASE_CHIMERAS, MOVES, ITEMS

DATA_DIR = Path("/data")
DATA_DIR.mkdir(parents=True, exist_ok=True)

# --- データ管理 ---

def _get_user_file_path(user_id):
    return DATA_DIR / f"kimera_user_{user_id}.json"

def get_user_data(user_id):
    file_path = _get_user_file_path(user_id)
    
    if not file_path.exists():
        initial_data = {
            "party": [],
            "box": [],
            "items": {"monster_ball": 5, "potion": 1},
            "money": 3000,
            "trainer_xp": 0,
            "trainer_level": 1,
            "challenge_stage": 1,
            "titles": [],
            "battle_state": None
        }
        starter = create_chimera_instance(random.choice(list(BASE_CHIMERAS.keys())), level=5)
        initial_data["party"].append(starter)
        save_user_data(user_id, initial_data)
        return initial_data

    try:
        data = json.loads(file_path.read_text(encoding="utf-8"))
        # データマイグレーション
        if "items" not in data: data["items"] = {}
        if "money" not in data: data["money"] = 1000
        if "box" not in data: data["box"] = []
        if "trainer_level" not in data: data["trainer_level"] = 1
        if "trainer_xp" not in data: data["trainer_xp"] = 0
        if "challenge_stage" not in data: data["challenge_stage"] = 1
        if "titles" not in data: data["titles"] = []
        return data
    except Exception:
        return {"party": [], "box": [], "items": {}, "money": 0}

def save_user_data(user_id, user_data):
    file_path = _get_user_file_path(user_id)
    file_path.write_text(json.dumps(user_data, ensure_ascii=False, indent=2), encoding="utf-8")

# --- トレーナーレベル管理 ---
def add_trainer_xp(user_id, xp_amount):
    ud = get_user_data(user_id)
    ud["trainer_xp"] += xp_amount
    
    leveled_up = False
    while ud["trainer_xp"] >= ud["trainer_level"] * 500:
        ud["trainer_xp"] -= ud["trainer_level"] * 500
        ud["trainer_level"] += 1
        leveled_up = True
        
    save_user_data(user_id, ud)
    return leveled_up, ud["trainer_level"]

# --- アイテム管理 ---
def add_item(user_id, item_key, count=1):
    ud = get_user_data(user_id)
    ud["items"][item_key] = ud["items"].get(item_key, 0) + count
    save_user_data(user_id, ud)

def remove_item(user_id, item_key, count=1):
    ud = get_user_data(user_id)
    if ud["items"].get(item_key, 0) >= count:
        ud["items"][item_key] -= count
        if ud["items"][item_key] <= 0: del ud["items"][item_key]
        save_user_data(user_id, ud)
        return True
    return False

def use_item_effect(user_id, item_key, target_chimera):
    ud = get_user_data(user_id)
    item = ITEMS.get(item_key)
    if not item or ud["items"].get(item_key, 0) <= 0: return "そのアイテムは持っていないわ。"

    msg = ""
    consumed = False

    if item["effect_type"] == "heal":
        if target_chimera["current_hp"] >= target_chimera["stats"]["max_hp"]:
            return "その子はもう元気いっぱいよ。"
        target_chimera["current_hp"] = min(target_chimera["stats"]["max_hp"], target_chimera["current_hp"] + item["value"])
        msg = f"{target_chimera['nickname']} のHPが回復したわ！"
        consumed = True

    elif item["effect_type"] == "exp":
        if target_chimera["level"] >= 100:
            return "その子はもうレベルMAXよ！"
        
        target_chimera["xp"] += item["value"]
        msg = f"{target_chimera['nickname']} に {item['value']} の経験値を与えたわ！"
        
        while target_chimera["xp"] >= target_chimera["next_xp"] and target_chimera["level"] < 100:
            lvl_msg = level_up_chimera(target_chimera)
            msg += f"\n{lvl_msg}"
            
        consumed = True

    if consumed:
        remove_item(user_id, item_key, 1)
        save_user_data(user_id, ud)
        return msg
    
    return "そのアイテムは今は使えないみたい。"

# --- キメラ生成・計算 ---
def calculate_stat(base, level, is_hp=False):
    # 基本計算式: (種族値 * 2 * レベル) / 100
    val = math.floor((base * 2 * level) / 100)
    
    if is_hp:
        # ★修正: HP計算式を大幅強化してワンパン防止
        # 旧: val * 1.5 + level * 2 + 50
        # 新: val * 2.5 + level * 5 + 100
        return int(val * 2.5 + level * 5 + 100)
    else:
        return int(val + 5)

def create_chimera_instance(base_id, level=5, nickname=None):
    base = BASE_CHIMERAS.get(base_id)
    if not base: return None
    
    level = min(100, max(1, level))
    
    moves = []
    for lv, mid in base["learnset"].items():
        if lv <= level: moves.append(mid)
    if not moves: moves = ["tackle"]
    moves = moves[-4:]

    bs = base["base_stats"]
    stats = {
        "max_hp": calculate_stat(bs["hp"], level, True),
        "atk": calculate_stat(bs["atk"], level),
        "def": calculate_stat(bs["def"], level),
        "spa": calculate_stat(bs["spa"], level),
        "spd": calculate_stat(bs["spd"], level),
        "spe": calculate_stat(bs["spe"], level),
    }
    
    return {
        "id": random.randint(100000, 999999),
        "base_id": base_id,
        "nickname": nickname or base["name"],
        "level": level,
        "xp": 0,
        "next_xp": level * 100,
        "current_hp": stats["max_hp"],
        "stats": stats,
        "moves": moves,
        "held_item": None,
        "friendship": 0,
        "rarity": base.get("rarity", 1) # レアリティ保存
    }

def get_chimera_display_stats(instance):
    base = BASE_CHIMERAS[instance["base_id"]]
    s = instance["stats"]
    moves_txt = ", ".join([MOVES[m]["name"] for m in instance["moves"]])
    item_txt = ITEMS[instance["held_item"]]["name"] if instance.get("held_item") else "なし"
    rarity_star = "★" * base.get("rarity", 1)
    
    return (
        f"**名前**: {instance['nickname']} (Lv.{instance['level']}) {rarity_star}\n"
        f"**種類**: {base['name']} / **タイプ**: {base['type']}\n"
        f"**特性**: {base['ability']} / **持ち物**: {item_txt}\n"
        f"**HP**: {instance['current_hp']}/{s['max_hp']}\n"
        f"**攻撃**: {s['atk']} / **防御**: {s['def']}\n"
        f"**特攻**: {s['spa']} / **特防**: {s['spd']} / **速度**: {s['spe']}\n"
        f"**技**: {moves_txt}\n"
        f"**EXP**: {instance['xp']}/{instance['next_xp']}"
    )

def level_up_chimera(instance):
    if instance["level"] >= 100: return ""
    
    instance["level"] += 1
    instance["xp"] = max(0, instance["xp"] - instance["next_xp"])
    instance["next_xp"] = instance["level"] * 100
    
    base = BASE_CHIMERAS[instance["base_id"]]
    bs = base["base_stats"]
    
    instance["stats"]["max_hp"] = calculate_stat(bs["hp"], instance["level"], True)
    instance["stats"]["atk"] = calculate_stat(bs["atk"], instance["level"])
    instance["stats"]["def"] = calculate_stat(bs["def"], instance["level"])
    instance["stats"]["spa"] = calculate_stat(bs["spa"], instance["level"])
    instance["stats"]["spd"] = calculate_stat(bs["spd"], instance["level"])
    instance["stats"]["spe"] = calculate_stat(bs["spe"], instance["level"])
    
    instance["current_hp"] = instance["stats"]["max_hp"]
    
    msg = f"**{instance['nickname']}** はレベル{instance['level']}になった！"
    
    new_move = base["learnset"].get(instance["level"])
    if new_move:
        if len(instance["moves"]) < 4:
            instance["moves"].append(new_move)
            msg += f"\n『{MOVES[new_move]['name']}』を覚えた！"
        else:
            forgot = instance["moves"].pop(0)
            instance["moves"].append(new_move)
            msg += f"\n『{MOVES[forgot]['name']}』を忘れて、『{MOVES[new_move]['name']}』を覚えた！"
            
    return msg

def migrate_old_data():
    old_path = DATA_DIR / "kimera_save.json"
    if not old_path.exists(): return "古いデータファイルが見つかりません。"
    try:
        all_data = json.loads(old_path.read_text(encoding="utf-8"))
        c = 0
        for uid, d in all_data.items():
            save_user_data(uid, d)
            c += 1
        old_path.rename(DATA_DIR / "kimera_save.json.bak")
        return f"成功: {c}件のデータを移行しました。"
    except Exception as e:
        return f"エラー: {e}"