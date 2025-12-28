# kimera_core.py
import json
import random
import math
from pathlib import Path
from kimera_data import BASE_CHIMERAS, MOVES, ITEMS

DATA_DIR = Path("/data")
DATA_DIR.mkdir(parents=True, exist_ok=True)
KIMERA_SAVE_FILE = DATA_DIR / "kimera_save.json"

# --- データ管理 ---

def load_kimera_data():
    if not KIMERA_SAVE_FILE.exists():
        return {}
    try:
        return json.loads(KIMERA_SAVE_FILE.read_text(encoding="utf-8"))
    except:
        return {}

def save_kimera_data(data):
    KIMERA_SAVE_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

def get_user_data(user_id):
    data = load_kimera_data()
    uid = str(user_id)
    if uid not in data:
        data[uid] = {
            "party": [],
            "box": [],
            "items": {"monster_ball": 5, "potion": 1}, # 初期アイテム
            "money": 3000,
            "battle_state": None
        }
        # 初期キメラ
        starter = create_chimera_instance(random.choice(list(BASE_CHIMERAS.keys())), level=5)
        data[uid]["party"].append(starter)
        save_kimera_data(data)
    
    # データ構造のマイグレーション用（古いデータがある場合のエラー防止）
    if "items" not in data[uid]: data[uid]["items"] = {}
    if "money" not in data[uid]: data[uid]["money"] = 1000
    
    return data[uid]

def save_user_data(user_id, user_data):
    data = load_kimera_data()
    data[str(user_id)] = user_data
    save_kimera_data(data)

# --- アイテム・金銭管理 ---

def add_item(user_id, item_key, count=1):
    ud = get_user_data(user_id)
    cur = ud["items"].get(item_key, 0)
    ud["items"][item_key] = cur + count
    save_user_data(user_id, ud)

def remove_item(user_id, item_key, count=1):
    ud = get_user_data(user_id)
    cur = ud["items"].get(item_key, 0)
    if cur >= count:
        ud["items"][item_key] = cur - count
        if ud["items"][item_key] <= 0:
            del ud["items"][item_key]
        save_user_data(user_id, ud)
        return True
    return False

def has_item(user_id, item_key):
    ud = get_user_data(user_id)
    return ud["items"].get(item_key, 0) > 0

def add_money(user_id, amount):
    ud = get_user_data(user_id)
    ud["money"] += amount
    save_user_data(user_id, ud)

def spend_money(user_id, amount):
    ud = get_user_data(user_id)
    if ud["money"] >= amount:
        ud["money"] -= amount
        save_user_data(user_id, ud)
        return True
    return False

# --- キメラ生成・計算 ---

def calculate_stat(base, level, is_hp=False):
    val = math.floor((base * 2 * level) / 100)
    if is_hp:
        return val + level + 10
    else:
        return val + 5

def create_chimera_instance(base_id, level=5, nickname=None):
    base = BASE_CHIMERAS.get(base_id)
    if not base: return None
    
    moves = []
    for lv, mid in base["learnset"].items():
        if lv <= level:
            moves.append(mid)
    if not moves: moves = ["tackle"] # 最低限の技
    moves = moves[-4:]

    bs = base["base_stats"]
    stats = {
        "max_hp": calculate_stat(bs["hp"], level, is_hp=True),
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
        "friendship": 0
    }

def get_chimera_display_stats(instance):
    base = BASE_CHIMERAS[instance["base_id"]]
    s = instance["stats"]
    moves_txt = ", ".join([MOVES[m]["name"] for m in instance["moves"]])
    item_txt = ITEMS[instance["held_item"]]["name"] if instance["held_item"] else "なし"
    
    return (
        f"**名前**: {instance['nickname']} (Lv.{instance['level']})\n"
        f"**種類**: {base['name']} / **タイプ**: {base['type']}\n"
        f"**特性**: {base['ability']} / **持ち物**: {item_txt}\n"
        f"**HP**: {instance['current_hp']}/{s['max_hp']}\n"
        f"**攻撃**: {s['atk']} / **防御**: {s['def']}\n"
        f"**特攻**: {s['spa']} / **特防**: {s['spd']} / **速度**: {s['spe']}\n"
        f"**技**: {moves_txt}\n"
        f"**EXP**: {instance['xp']}/{instance['next_xp']}"
    )

def level_up_chimera(instance):
    instance["level"] += 1
    instance["xp"] = 0
    instance["next_xp"] = instance["level"] * 100
    
    base = BASE_CHIMERAS[instance["base_id"]]
    bs = base["base_stats"]
    
    instance["stats"]["max_hp"] = calculate_stat(bs["hp"], instance["level"], is_hp=True)
    instance["stats"]["atk"] = calculate_stat(bs["atk"], instance["level"])
    instance["stats"]["def"] = calculate_stat(bs["def"], instance["level"])
    instance["stats"]["spa"] = calculate_stat(bs["spa"], instance["level"])
    instance["stats"]["spd"] = calculate_stat(bs["spd"], instance["level"])
    instance["stats"]["spe"] = calculate_stat(bs["spe"], instance["level"])
    
    new_move = base["learnset"].get(instance["level"])
    msg = f"\n**{instance['nickname']}** はレベル{instance['level']}になった！"
    
    if new_move:
        if len(instance["moves"]) < 4:
            instance["moves"].append(new_move)
            msg += f"\n『{MOVES[new_move]['name']}』を覚えた！"
        else:
            msg += f"\n『{MOVES[new_move]['name']}』を覚えたいけど、技がいっぱいだ…"
            
    return msg