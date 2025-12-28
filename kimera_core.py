# kimera_core.py
import json
import random
import math
from pathlib import Path
from kimera_data import BASE_CHIMERAS, MOVES, ITEMS

# データ保存パス
DATA_DIR = Path("/data")
DATA_DIR.mkdir(parents=True, exist_ok=True)
KIMERA_SAVE_FILE = DATA_DIR / "kimera_save.json"

# --- データ管理クラス ---

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
        # 新規ユーザー初期化
        data[uid] = {
            "party": [],      # 手持ち（最大3体）
            "box": [],        # 預かり所
            "items": {},      # 所持アイテム {item_id: count}
            "money": 1000,    # 所持金
            "battle_state": None # 戦闘中かどうか
        }
        # 初期キメラを1体ランダムで付与
        starter = create_chimera_instance(random.choice(list(BASE_CHIMERAS.keys())), level=5)
        data[uid]["party"].append(starter)
        save_kimera_data(data)
    return data[uid]

def save_user_data(user_id, user_data):
    data = load_kimera_data()
    data[str(user_id)] = user_data
    save_kimera_data(data)

# --- キメラ生成とステータス計算 ---

def calculate_stat(base, level, is_hp=False):
    # ポケモン風の簡易計算式
    # (Base * 2 * Level / 100) + (Level + 10)  (HPの場合)
    # (Base * 2 * Level / 100) + 5             (他)
    # ※個体値・努力値は今回は省略
    val = math.floor((base * 2 * level) / 100)
    if is_hp:
        return val + level + 10
    else:
        return val + 5

def create_chimera_instance(base_id, level=5, nickname=None):
    base = BASE_CHIMERAS.get(base_id)
    if not base: return None
    
    # 技の初期習得
    moves = []
    for lv, mid in base["learnset"].items():
        if lv <= level:
            moves.append(mid)
    # 4つまで
    moves = moves[-4:]

    # ステータス計算
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
        "id": random.randint(100000, 999999), # ユニークID
        "base_id": base_id,
        "nickname": nickname or base["name"],
        "level": level,
        "xp": 0,
        "next_xp": level * 100, # 必要経験値（簡易）
        "current_hp": stats["max_hp"],
        "stats": stats,
        "moves": moves,
        "held_item": None,
        "friendship": 0
    }

def get_chimera_display_stats(instance):
    """詳細表示用のテキストを生成"""
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
    """レベルアップ処理"""
    instance["level"] += 1
    instance["xp"] = 0
    instance["next_xp"] = instance["level"] * 100
    
    base = BASE_CHIMERAS[instance["base_id"]]
    bs = base["base_stats"]
    
    # ステータス再計算
    instance["stats"]["max_hp"] = calculate_stat(bs["hp"], instance["level"], is_hp=True)
    instance["stats"]["atk"] = calculate_stat(bs["atk"], instance["level"])
    instance["stats"]["def"] = calculate_stat(bs["def"], instance["level"])
    instance["stats"]["spa"] = calculate_stat(bs["spa"], instance["level"])
    instance["stats"]["spd"] = calculate_stat(bs["spd"], instance["level"])
    instance["stats"]["spe"] = calculate_stat(bs["spe"], instance["level"])
    
    # 新技習得チェック
    new_move = base["learnset"].get(instance["level"])
    msg = f"{instance['nickname']}はレベル{instance['level']}になった！"
    
    if new_move:
        if len(instance["moves"]) < 4:
            instance["moves"].append(new_move)
            msg += f"\n『{MOVES[new_move]['name']}』を覚えた！"
        else:
            msg += f"\n『{MOVES[new_move]['name']}』を覚えたいけど、技がいっぱいだ…"
            
    return msg