# kimera_core.py
import json
import random
import math
from pathlib import Path
from kimera_data import BASE_CHIMERAS, MOVES, ITEMS, TYPES, TYPE_CHART

# データ保存ディレクトリ
DATA_DIR = Path("/data")
DATA_DIR.mkdir(parents=True, exist_ok=True)

# --- データ管理 (セーブデータ分離対応) ---

def _get_user_file_path(user_id, hard_mode=False):
    """モードに応じたファイルパスを返す"""
    suffix = "_hard" if hard_mode else ""
    return DATA_DIR / f"kimera_user_{user_id}{suffix}.json"

def get_user_data(user_id, hard_mode=False):
    """
    ユーザーデータを取得する。
    """
    file_path = _get_user_file_path(user_id, hard_mode)
    
    # 新規作成（ファイルがない場合）
    if not file_path.exists():
        initial_data = {
            "party": [],
            "box": [],
            "items": {"monster_ball": 5, "potion": 1} if not hard_mode else {"monster_ball": 3, "potion": 1},
            "money": 3000 if not hard_mode else 1000,
            "trainer_xp": 0,
            "trainer_level": 1,
            "challenge_stage": 1,
            "titles": [],
            "dex": {},
            "battle_state": None,
            "is_hard_mode": hard_mode
        }
        
        starter_lv = 5 if not hard_mode else 10
        starter_base = random.choice(list(BASE_CHIMERAS.keys()))
        starter = create_chimera_instance(starter_base, level=starter_lv)
        
        initial_data["party"].append(starter)
        register_dex(initial_data, starter["base_id"], caught=True)
        
        save_user_data(user_id, initial_data, hard_mode)
        return initial_data

    try:
        data = json.loads(file_path.read_text(encoding="utf-8"))
        # マイグレーション
        if "items" not in data: data["items"] = {}
        if "money" not in data: data["money"] = 1000
        if "box" not in data: data["box"] = []
        if "trainer_level" not in data: data["trainer_level"] = 1
        if "challenge_stage" not in data: data["challenge_stage"] = 1
        if "dex" not in data: data["dex"] = {}
        data["is_hard_mode"] = hard_mode
        return data
    except Exception:
        return get_user_data(user_id, hard_mode)

def save_user_data(user_id, user_data, hard_mode=False):
    file_path = _get_user_file_path(user_id, hard_mode)
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
    for c in ud["party"] + ud["box"]:
        c["current_hp"] = c["stats"]["max_hp"]
        c["status_condition"] = None
        c["stat_stages"] = {"atk": 0, "def": 0, "spa": 0, "spd": 0, "spe": 0}
        c["battle_state"] = {} # バトル中の一時状態クリア
        c["form"] = None # 変身解除

def swap_party_box(ud, party_idx, box_idx):
    if 0 <= party_idx < len(ud["party"]) and 0 <= box_idx < len(ud["box"]):
        ud["party"][party_idx], ud["box"][box_idx] = ud["box"][box_idx], ud["party"][party_idx]
        return True
    return False

def move_party_to_box(ud, party_idx):
    if len(ud["party"]) <= 1: return False
    if 0 <= party_idx < len(ud["party"]):
        target = ud["party"].pop(party_idx)
        ud["box"].append(target)
        return True
    return False

def move_box_to_party(ud, box_idx):
    if len(ud["party"]) >= 3: return False
    if 0 <= box_idx < len(ud["box"]):
        target = ud["box"].pop(box_idx)
        ud["party"].append(target)
        return True
    return False

# --- 配合 (Breeding) ---
def breed_chimeras(parent1, parent2):
    """
    2体の親から新しいキメラ(Lv1)を生成する。
    ベースはparent1(母親役)を継承、個体値は両親の平均+ランダム変異。
    """
    base_id = parent1["base_id"]
    
    # 個体値遺伝: 両親の平均 + ランダム(-2~+2)
    new_ivs = {}
    for k in ["hp", "atk", "def", "spa", "spd", "spe"]:
        p1_iv = parent1.get("ivs", {}).get(k, 15)
        p2_iv = parent2.get("ivs", {}).get(k, 15)
        avg = (p1_iv + p2_iv) // 2
        mutation = random.randint(-2, 4) # 少し良くなりやすい
        new_iv = max(0, min(31, avg + mutation))
        new_ivs[k] = new_iv
        
    child = create_chimera_instance(base_id, level=1)
    child["ivs"] = new_ivs
    update_chimera_stats(child)
    child["current_hp"] = child["stats"]["max_hp"]
    
    return child

# --- アイテム効果 ---
def apply_item_effect_logic(ud, item_key, target_chimera):
    item = ITEMS.get(item_key)
    if not item or ud["items"].get(item_key, 0) <= 0: return "持っていないわ。"

    msg = ""
    consumed = False

    if item["effect_type"] == "heal":
        if target_chimera["current_hp"] >= target_chimera["stats"]["max_hp"]:
            return "元気いっぱいよ。"
        old_hp = target_chimera["current_hp"]
        target_chimera["current_hp"] = min(target_chimera["stats"]["max_hp"], target_chimera["current_hp"] + item["value"])
        recov = target_chimera["current_hp"] - old_hp
        msg = f"{target_chimera['nickname']} の体力が {recov} 回復した！"
        consumed = True

    elif item["effect_type"] == "heal_status":
        status_to_heal = item.get("status")
        current_status = target_chimera.get("status_condition")
        
        if not current_status:
             return "健康そのものよ。"
             
        if status_to_heal == "all" or status_to_heal == current_status:
            target_chimera["status_condition"] = None
            msg = f"{target_chimera['nickname']} の状態異常が治ったわ！"
            consumed = True
        else:
            return "その薬じゃ治らないみたい。"

    elif item["effect_type"] == "exp":
        is_hard = ud.get("is_hard_mode", False)
        limit = 200 if is_hard else 100
        if target_chimera["level"] >= limit: return "これ以上は育たないわ。"

        exp_val = item["value"]
        if is_hard: exp_val = int(exp_val * 0.1)

        target_chimera["xp"] += exp_val
        msg = f"{target_chimera['nickname']} に経験値 {exp_val} をあげた！"
        while target_chimera["xp"] >= target_chimera["next_xp"]:
            msg += "\n" + level_up_chimera(target_chimera, is_hard_mode=is_hard)
        consumed = True

    if consumed:
        ud["items"][item_key] -= 1
        if ud["items"][item_key] <= 0: del ud["items"][item_key]
        return msg
    
    return "使えないわ。"

# --- 装備ロジック ---
def equip_item_logic(ud, party_idx, item_key):
    if not (0 <= party_idx < len(ud["party"])): return "指定したキメラがいないわ。"
    if ud["items"].get(item_key, 0) <= 0: return "そのアイテムは持っていないわ。"
    
    target = ud["party"][party_idx]
    item_data = ITEMS.get(item_key)
    if not item_data or not item_data["effect_type"].startswith("equip_"):
        return "それは装備できないアイテムよ。"

    old_item = target.get("held_item")
    if old_item:
        ud["items"][old_item] = ud["items"].get(old_item, 0) + 1
    
    ud["items"][item_key] -= 1
    if ud["items"][item_key] <= 0: del ud["items"][item_key]
    
    target["held_item"] = item_key
    update_chimera_stats(target)
    
    if item_data["effect_type"] == "equip_hp":
         target["current_hp"] = min(target["stats"]["max_hp"], int(target["current_hp"] * item_data["value"]))

    return f"{target['nickname']} に {item_data['name']} を持たせたわ！"

def unequip_item_logic(ud, party_idx):
    if not (0 <= party_idx < len(ud["party"])): return "指定したキメラがいないわ。"
    target = ud["party"][party_idx]
    old_item = target.get("held_item")
    if not old_item: return "何も持っていないわ。"
    
    ud["items"][old_item] = ud["items"].get(old_item, 0) + 1
    target["held_item"] = None
    
    update_chimera_stats(target)
    if target["current_hp"] > target["stats"]["max_hp"]:
        target["current_hp"] = target["stats"]["max_hp"]

    return f"{target['nickname']} から道具を預かったわ。"

# --- キメラステータス計算 ---

def generate_ivs():
    return {
        "hp": random.randint(0, 31),
        "atk": random.randint(0, 31),
        "def": random.randint(0, 31),
        "spa": random.randint(0, 31),
        "spd": random.randint(0, 31),
        "spe": random.randint(0, 31)
    }

def calculate_stat(base_val, iv, level, is_hp=False):
    core_val = (base_val * 2) + iv
    val = math.floor((core_val * level) / 100)
    if is_hp:
        return int(val + level + 10)
    else:
        return int(val + 5)

def update_chimera_stats(instance):
    base = BASE_CHIMERAS[instance["base_id"]]
    bs = base["base_stats"]
    lv = instance["level"]
    ability = base["ability"]
    
    if "ivs" not in instance: instance["ivs"] = generate_ivs()
    ivs = instance["ivs"]
    
    # 素のステータス
    s = {
        "max_hp": calculate_stat(bs["hp"], ivs["hp"], lv, True),
        "atk": calculate_stat(bs["atk"], ivs["atk"], lv),
        "def": calculate_stat(bs["def"], ivs["def"], lv),
        "spa": calculate_stat(bs["spa"], ivs["spa"], lv),
        "spd": calculate_stat(bs["spd"], ivs["spd"], lv),
        "spe": calculate_stat(bs["spe"], ivs["spe"], lv),
    }
    
    # 装備・特性補正 (バトル外で計算できるもの)
    if ability == "闘争心": s["atk"] = int(s["atk"] * 1.1)
    if ability == "大地獣": s["def"] = int(s["def"] * 1.1)
    if ability in ["水流", "ロケット", "盗みの天才"]: s["spe"] = int(s["spe"] * 1.1)
    if ability == "最愛":
         for k in s: s[k] = int(s[k] * 1.1)

    held = instance.get("held_item")
    if held and held in ITEMS:
        item_data = ITEMS[held]
        val = item_data.get("value", 1.0)
        effect = item_data.get("effect_type", "")
        
        if effect == "equip_atk": s["atk"] = int(s["atk"] * val)
        if effect == "equip_def": s["def"] = int(s["def"] * val)
        if effect == "equip_spa": s["spa"] = int(s["spa"] * val)
        if effect == "equip_hp": s["max_hp"] = int(s["max_hp"] * val)
    
    instance["stats"] = s
    if instance["current_hp"] > s["max_hp"]:
        instance["current_hp"] = s["max_hp"]

def create_chimera_instance(base_id, level=5, nickname=None, held_item=None):
    base = BASE_CHIMERAS.get(base_id)
    if not base: return None
    level = max(1, level)
    
    moves = []
    for lv, mid in base["learnset"].items():
        if lv <= level: moves.append(mid)
    if not moves: moves = ["tackle"]
    moves = moves[-4:]

    instance = {
        "id": random.randint(100000, 999999),
        "base_id": base_id,
        "nickname": nickname or base["name"],
        "level": level,
        "xp": 0,
        "next_xp": level * 100,
        "current_hp": 0,
        "ivs": generate_ivs(),
        "stats": {},
        "moves": moves,
        "held_item": held_item,
        "friendship": 0,
        "rarity": base.get("rarity", 1),
        
        # 新規追加項目
        "status_condition": None, # poison, paralysis etc.
        "stat_stages": {"atk": 0, "def": 0, "spa": 0, "spd": 0, "spe": 0}, # -6 to +6
        "battle_state": {}, # バトル中の一時的な状態フラグ(スタックなど)
        "form": None, # 変身形態
    }
    update_chimera_stats(instance)
    instance["current_hp"] = instance["stats"]["max_hp"]
    return instance

def get_chimera_display_stats(instance):
    base = BASE_CHIMERAS[instance["base_id"]]
    s = instance["stats"]
    ivs = instance.get("ivs", generate_ivs())
    
    moves_txt = ", ".join([MOVES[m]["name"] for m in instance["moves"]])
    item_txt = ITEMS[instance["held_item"]]["name"] if instance.get("held_item") else "なし"
    rarity_star = "★" * base.get("rarity", 1)
    status_txt = f"[{instance['status_condition']}]" if instance.get('status_condition') else ""
    
    total_iv = sum(ivs.values())
    if total_iv >= 170: rank = "S (神個体)"
    elif total_iv >= 150: rank = "A (素晴らしい)"
    elif total_iv >= 120: rank = "B (相当優秀)"
    elif total_iv >= 90: rank = "C (平均以上)"
    elif total_iv >= 60: rank = "D (平均的)"
    else: rank = "E (平凡)"

    return (
        f"**{instance['nickname']}** (Lv.{instance['level']}) {rarity_star} {status_txt}\n"
        f"種類: {base['name']} / {base['type']}\n"
        f"特性: {base['ability']} / 持ち物: {item_txt}\n"
        f"才能ランク: **{rank}** (合計{total_iv})\n"
        f"----------------\n"
        f"HP: {instance['current_hp']}/{s['max_hp']} (IV:{ivs['hp']})\n"
        f"攻:{s['atk']}({ivs['atk']}) 防:{s['def']}({ivs['def']})\n"
        f"特攻:{s['spa']}({ivs['spa']}) 特防:{s['spd']}({ivs['spd']})\n"
        f"素:{s['spe']}({ivs['spe']})\n"
        f"----------------\n"
        f"技: {moves_txt}\n"
        f"Exp: {instance['xp']}/{instance['next_xp']}"
    )

def level_up_chimera(instance, is_hard_mode=False):
    limit = 200 if is_hard_mode else 100
    if instance["level"] >= limit: return ""
    
    instance["level"] += 1
    instance["xp"] = max(0, instance["xp"] - instance["next_xp"])
    
    base_req = 100
    if is_hard_mode: base_req = 300
    instance["next_xp"] = instance["level"] * base_req
    
    base = BASE_CHIMERAS[instance["base_id"]]
    old_hp_rate = instance["current_hp"] / instance["stats"]["max_hp"] if instance["stats"]["max_hp"] > 0 else 0
    
    update_chimera_stats(instance)
    
    if is_hard_mode:
        instance["current_hp"] = int(instance["stats"]["max_hp"] * old_hp_rate)
        hp_msg = ""
    else:
        instance["current_hp"] = instance["stats"]["max_hp"]
        hp_msg = " (全回復)"
    
    msg = f"**{instance['nickname']}** は Lv.{instance['level']} になった！{hp_msg}"
    
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

# --- 戦闘用ロジック ---
def calculate_type_effectiveness(move_type, defender_type):
    """タイプ相性倍率を返す"""
    if move_type in TYPE_CHART and defender_type in TYPE_CHART[move_type]:
        return TYPE_CHART[move_type][defender_type]
    return 1.0

def calculate_stat_with_stage(stat_value, stage):
    """ランク補正後のステータスを計算 (-6 ~ +6)"""
    if stage >= 0:
        return int(stat_value * (2 + stage) / 2)
    else:
        return int(stat_value * 2 / (2 + abs(stage)))

def check_survival_item(chimera, damage):
    if chimera["current_hp"] == chimera["stats"]["max_hp"] and damage >= chimera["current_hp"]:
        held = chimera.get("held_item")
        if held == "focus_sash":
            chimera["held_item"] = None
            return True
    return False

def check_resist_berry(chimera, damage_type):
    held = chimera.get("held_item")
    if held == "resist_berry":
        # ここで本来は相性計算が必要だが、簡易的に発動フラグだけ返す
        return True 
    return False