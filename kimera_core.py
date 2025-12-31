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
            "dex": {}, # {base_id: "caught" or "seen"}
            "battle_state": None
        }
        starter = create_chimera_instance(random.choice(list(BASE_CHIMERAS.keys())), level=5)
        initial_data["party"].append(starter)
        register_dex(initial_data, starter["base_id"], caught=True)
        save_user_data(user_id, initial_data)
        return initial_data

    try:
        data = json.loads(file_path.read_text(encoding="utf-8"))
        # マイグレーション
        if "items" not in data: data["items"] = {}
        if "money" not in data: data["money"] = 1000
        if "box" not in data: data["box"] = []
        if "trainer_level" not in data: data["trainer_level"] = 1
        if "trainer_xp" not in data: data["trainer_xp"] = 0
        if "challenge_stage" not in data: data["challenge_stage"] = 1
        if "titles" not in data: data["titles"] = []
        if "dex" not in data: data["dex"] = {}
        return data
    except Exception:
        return {"party": [], "box": [], "items": {}, "money": 0, "dex": {}}

def save_user_data(user_id, user_data):
    file_path = _get_user_file_path(user_id)
    file_path.write_text(json.dumps(user_data, ensure_ascii=False, indent=2), encoding="utf-8")

# --- 図鑑登録 ---
def register_dex(ud, base_id, caught=False):
    if base_id not in BASE_CHIMERAS: return
    current = ud["dex"].get(base_id)
    
    if caught:
        ud["dex"][base_id] = "caught"
    elif current != "caught":
        ud["dex"][base_id] = "seen"

# --- パーティ・回復 ---
def heal_all_kimeras(ud):
    for c in ud["party"]:
        c["current_hp"] = c["stats"]["max_hp"]
    # ボックス内も回復しておく
    for c in ud["box"]:
        c["current_hp"] = c["stats"]["max_hp"]

def swap_party_box(ud, party_idx, box_idx):
    if 0 <= party_idx < len(ud["party"]) and 0 <= box_idx < len(ud["box"]):
        ud["party"][party_idx], ud["box"][box_idx] = ud["box"][box_idx], ud["party"][party_idx]
        return True
    return False

def move_party_to_box(ud, party_idx):
    # 手持ちが1体のときは預けられない
    if len(ud["party"]) <= 1: return False
    if 0 <= party_idx < len(ud["party"]):
        target = ud["party"].pop(party_idx)
        ud["box"].append(target)
        return True
    return False

def move_box_to_party(ud, box_idx):
    if len(ud["party"]) >= 3: return False # 手持ち最大3
    if 0 <= box_idx < len(ud["box"]):
        target = ud["box"].pop(box_idx)
        ud["party"].append(target)
        return True
    return False

# --- アイテム効果 (データ操作のみ) ---
def apply_item_effect_logic(ud, item_key, target_chimera):
    item = ITEMS.get(item_key)
    if not item or ud["items"].get(item_key, 0) <= 0: return "持っていないわ。"

    msg = ""
    consumed = False

    if item["effect_type"] == "heal":
        if target_chimera["current_hp"] >= target_chimera["stats"]["max_hp"]:
            return "元気いっぱいよ。"
        target_chimera["current_hp"] = min(target_chimera["stats"]["max_hp"], target_chimera["current_hp"] + item["value"])
        msg = f"{target_chimera['nickname']} は回復した！"
        consumed = True

    elif item["effect_type"] == "exp":
        if target_chimera["level"] >= 100: return "レベルMAXよ。"
        target_chimera["xp"] += item["value"]
        msg = f"{target_chimera['nickname']} に経験値 {item['value']} をあげた！"
        while target_chimera["xp"] >= target_chimera["next_xp"] and target_chimera["level"] < 100:
            msg += "\n" + level_up_chimera(target_chimera)
        consumed = True

    if consumed:
        ud["items"][item_key] -= 1
        if ud["items"][item_key] <= 0: del ud["items"][item_key]
        return msg
    
    return "使えないわ。"

# --- キメラ計算 ---
def calculate_stat(base, level, is_hp=False):
    val = math.floor((base * 2 * level) / 100)
    if is_hp:
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
        "rarity": base.get("rarity", 1)
    }

def get_chimera_display_stats(instance):
    base = BASE_CHIMERAS[instance["base_id"]]
    s = instance["stats"]
    moves_txt = ", ".join([MOVES[m]["name"] for m in instance["moves"]])
    item_txt = ITEMS[instance["held_item"]]["name"] if instance.get("held_item") else "なし"
    rarity_star = "★" * base.get("rarity", 1)
    
    return (
        f"**{instance['nickname']}** (Lv.{instance['level']}) {rarity_star}\n"
        f"種類: {base['name']} / {base['type']}\n"
        f"HP: {instance['current_hp']}/{s['max_hp']}\n"
        f"攻:{s['atk']} 防:{s['def']} 特攻:{s['spa']} 特防:{s['spd']} 素:{s['spe']}\n"
        f"技: {moves_txt}\n"
        f"Exp: {instance['xp']}/{instance['next_xp']}"
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
    instance["current_hp"] = instance["stats"]["max_hp"] # 全快
    
    msg = f"**{instance['nickname']}** は Lv.{instance['level']} になった！"
    
    new_move = base["learnset"].get(instance["level"])
    if new_move:
        if len(instance["moves"]) < 4:
            instance["moves"].append(new_move)
            msg += f"\n『{MOVES[new_move]['name']}』を覚えた！"
        else:
            forgot = instance["moves"].pop(0)
            instance["moves"].append(new_move)
            msg += f"\n『{MOVES[forgot]['name']}』を忘れて『{MOVES[new_move]['name']}』を覚えた！"
    return msg

def migrate_old_data():
    old_path = DATA_DIR / "kimera_save.json"
    if not old_path.exists(): return "ファイルなし"
    try:
        all_data = json.loads(old_path.read_text(encoding="utf-8"))
        c = 0
        for uid, d in all_data.items():
            save_user_data(uid, d)
            c += 1
        old_path.rename(DATA_DIR / "kimera_save.json.bak")
        return f"移行完了: {c}件"
    except Exception as e:
        return f"エラー: {e}"