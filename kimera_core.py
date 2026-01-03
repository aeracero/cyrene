import json
import random
import math
from pathlib import Path
from kimera_data import BASE_CHIMERAS, MOVES, ITEMS

DATA_DIR = Path("/data")
DATA_DIR.mkdir(parents=True, exist_ok=True)

# --- データ管理 ---

def _get_user_file_path(user_id, hard_mode=False):
    suffix = "_hard" if hard_mode else ""
    return DATA_DIR / f"kimera_user_{user_id}{suffix}.json"

def get_user_data(user_id, hard_mode=False):
    file_path = _get_user_file_path(user_id, hard_mode)
    
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
        # ハードモードは少し強い状態でスタートできないと詰む
        starter_lv = 5 if not hard_mode else 10
        starter = create_chimera_instance(random.choice(list(BASE_CHIMERAS.keys())), level=starter_lv)
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
        if "trainer_xp" not in data: data["trainer_xp"] = 0
        if "challenge_stage" not in data: data["challenge_stage"] = 1
        if "dex" not in data: data["dex"] = {}
        data["is_hard_mode"] = hard_mode # フラグ補完
        return data
    except Exception:
        return {"party": [], "box": [], "items": {}, "money": 0, "dex": {}, "is_hard_mode": hard_mode}

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
    for c in ud["party"]:
        c["current_hp"] = c["stats"]["max_hp"]
    for c in ud["box"]:
        c["current_hp"] = c["stats"]["max_hp"]

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

# --- アイテム効果 (消耗品) ---
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

    elif item["effect_type"] == "exp":
        if target_chimera["level"] >= 100 and not ud.get("is_hard_mode", False): return "レベルMAXよ。" # ハードは上限突破可
        if target_chimera["level"] >= 200: return "これ以上は育たないわ。"

        target_chimera["xp"] += item["value"]
        msg = f"{target_chimera['nickname']} に経験値 {item['value']} をあげた！"
        while target_chimera["xp"] >= target_chimera["next_xp"]:
            msg += "\n" + level_up_chimera(target_chimera, is_hard_mode=ud.get("is_hard_mode", False))
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
    
    # HP装備の場合、現在HPも比率で増やす
    if item_data["effect_type"] == "equip_hp":
         target["current_hp"] = min(target["stats"]["max_hp"], int(target["current_hp"] * item_data["value"]))

    return f"{target['nickname']} に {item_data['name']} を持たせたわ！"

def unequip_item_logic(ud, party_idx):
    if not (0 <= party_idx < len(ud["party"])): return "指定したキメラがいないわ。"
    target = ud["party"][party_idx]
    
    old_item = target.get("held_item")
    if not old_item: return "何も持っていないわ。"
    
    # HP装備を外す場合、最大HPが下がるので現在HPも調整
    item_data = ITEMS.get(old_item)
    
    ud["items"][old_item] = ud["items"].get(old_item, 0) + 1
    target["held_item"] = None
    
    update_chimera_stats(target)
    if target["current_hp"] > target["stats"]["max_hp"]:
        target["current_hp"] = target["stats"]["max_hp"]

    return f"{target['nickname']} から道具を預かったわ。"

# --- キメラ計算 ---
def calculate_base_stat(base_val, level, is_hp=False):
    """素のステータス計算"""
    val = math.floor((base_val * 2 * level) / 100)
    if is_hp:
        return int(val * 2.5 + level * 5 + 100)
    else:
        return int(val + 5)

def update_chimera_stats(instance):
    """レベル、装備、特性に基づいてステータスを最終決定する"""
    base = BASE_CHIMERAS[instance["base_id"]]
    bs = base["base_stats"]
    lv = instance["level"]
    ability = base["ability"]
    
    # 1. 素のステータス
    s = {
        "max_hp": calculate_base_stat(bs["hp"], lv, True),
        "atk": calculate_base_stat(bs["atk"], lv),
        "def": calculate_base_stat(bs["def"], lv),
        "spa": calculate_base_stat(bs["spa"], lv),
        "spd": calculate_base_stat(bs["spd"], lv),
        "spe": calculate_base_stat(bs["spe"], lv),
    }
    
    # 2. 装備補正・特性補正(静的)
    held = instance.get("held_item")
    
    # 特性: 闘争心(攻撃UP), 大地獣(防御UP), 水流/ロケット/盗みの天才(素早さUP), 最愛(全UP)
    if ability == "闘争心": s["atk"] = int(s["atk"] * 1.1)
    if ability == "大地獣": s["def"] = int(s["def"] * 1.1)
    if ability in ["水流", "ロケット", "盗みの天才"]: s["spe"] = int(s["spe"] * 1.1)
    if ability == "最愛":
         for k in s: s[k] = int(s[k] * 1.1)

    if held and held in ITEMS:
        item_data = ITEMS[held]
        effect = item_data.get("effect_type", "")
        val = item_data.get("value", 1.0)
        
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
        "stats": {},
        "moves": moves,
        "held_item": held_item,
        "friendship": 0,
        "rarity": base.get("rarity", 1)
    }
    update_chimera_stats(instance)
    instance["current_hp"] = instance["stats"]["max_hp"]
    return instance

def get_chimera_display_stats(instance):
    base = BASE_CHIMERAS[instance["base_id"]]
    s = instance["stats"]
    moves_txt = ", ".join([MOVES[m]["name"] for m in instance["moves"]])
    item_txt = ITEMS[instance["held_item"]]["name"] if instance.get("held_item") else "なし"
    rarity_star = "★" * base.get("rarity", 1)
    
    return (
        f"**{instance['nickname']}** (Lv.{instance['level']}) {rarity_star}\n"
        f"種類: {base['name']} / {base['type']}\n"
        f"特性: {base['ability']} / **持ち物**: {item_txt}\n"
        f"HP: {instance['current_hp']}/{s['max_hp']}\n"
        f"攻:{s['atk']} 防:{s['def']} 特攻:{s['spa']} 特防:{s['spd']} 素:{s['spe']}\n"
        f"技: {moves_txt}\n"
        f"Exp: {instance['xp']}/{instance['next_xp']}"
    )

def level_up_chimera(instance, is_hard_mode=False):
    # レベル上限: ノーマル100, ハード200
    limit = 200 if is_hard_mode else 100
    if instance["level"] >= limit: return ""
    
    instance["level"] += 1
    instance["xp"] = max(0, instance["xp"] - instance["next_xp"])
    instance["next_xp"] = instance["level"] * 100
    
    base = BASE_CHIMERAS[instance["base_id"]]
    old_hp_rate = instance["current_hp"] / instance["stats"]["max_hp"] if instance["stats"]["max_hp"] > 0 else 0
    
    update_chimera_stats(instance)
    
    # ハードモードではレベルアップ時の全回復なし（割合維持）
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

# --- 戦闘用ロジック ---
def check_survival_item(chimera, damage):
    """きあいのタスキ発動判定"""
    if chimera["current_hp"] == chimera["stats"]["max_hp"] and damage >= chimera["current_hp"]:
        held = chimera.get("held_item")
        if held == "focus_sash":
            chimera["held_item"] = None # 消費
            return True
    return False

def check_resist_berry(chimera, damage_type):
    """半減実判定 (簡易実装: 効果抜群なら発動)"""
    held = chimera.get("held_item")
    if held == "resist_berry":
        # 本来はタイプ相性計算が必要だが、簡易的にランダムまたは常に発動させるのはバランス崩壊
        # ここでは「ダメージが最大HPの50%を超える」場合に発動とする
        if 0 < chimera["current_hp"]:
             # 後ほどBattle側で判定しやすいよう、ここでは判定のみ
             pass
    return False