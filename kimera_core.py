# kimera_core.py
import json
import random
import math
from pathlib import Path
from kimera_data import BASE_CHIMERAS, MOVES, ITEMS

# データ保存ディレクトリ（Railwayの永続化ボリューム）
DATA_DIR = Path("/data")
DATA_DIR.mkdir(parents=True, exist_ok=True)

# --- データ管理 (個別ファイル方式) ---

def _get_user_file_path(user_id):
    """ユーザーIDごとのファイルパスを生成"""
    return DATA_DIR / f"kimera_user_{user_id}.json"

def get_user_data(user_id):
    """指定ユーザーのデータを個別のJSONファイルから読み込む"""
    file_path = _get_user_file_path(user_id)
    
    # ファイルが存在しない場合は新規作成（初期データ）
    if not file_path.exists():
        initial_data = {
            "party": [],
            "box": [],
            "items": {"monster_ball": 5, "potion": 1}, # 初期アイテム
            "money": 3000,
            "battle_state": None
        }
        # 初期キメラ付与
        starter = create_chimera_instance(random.choice(list(BASE_CHIMERAS.keys())), level=5)
        initial_data["party"].append(starter)
        
        # 保存して返す
        save_user_data(user_id, initial_data)
        return initial_data

    # ファイルが存在する場合は読み込み
    try:
        data = json.loads(file_path.read_text(encoding="utf-8"))
        
        # データ構造の不足分を補完（アップデート時のエラー防止）
        if "items" not in data: data["items"] = {}
        if "money" not in data: data["money"] = 1000
        if "box" not in data: data["box"] = []
        
        return data
    except Exception:
        # 読み込みエラー時は初期データを返す（安全策）
        return {
            "party": [], "box": [], "items": {}, "money": 0, "battle_state": None
        }

def save_user_data(user_id, user_data):
    """指定ユーザーのデータを個別のJSONファイルに保存する"""
    file_path = _get_user_file_path(user_id)
    file_path.write_text(json.dumps(user_data, ensure_ascii=False, indent=2), encoding="utf-8")

# --- アイテム・金銭管理ヘルパー ---
# kimera_game.py から呼び出されるショートカット関数群

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

# --- キメラ生成・計算ロジック ---

def calculate_stat(base, level, is_hp=False):
    val = math.floor((base * 2 * level) / 100)
    if is_hp:
        return val + level + 10
    else:
        return val + 5

def create_chimera_instance(base_id, level=5, nickname=None):
    base = BASE_CHIMERAS.get(base_id)
    if not base: return None
    
    # 技構成
    moves = []
    for lv, mid in base["learnset"].items():
        if lv <= level:
            moves.append(mid)
    if not moves: moves = ["tackle"]
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
    
    # ステータス更新
    instance["stats"]["max_hp"] = calculate_stat(bs["hp"], instance["level"], is_hp=True)
    instance["stats"]["atk"] = calculate_stat(bs["atk"], instance["level"])
    instance["stats"]["def"] = calculate_stat(bs["def"], instance["level"])
    instance["stats"]["spa"] = calculate_stat(bs["spa"], instance["level"])
    instance["stats"]["spd"] = calculate_stat(bs["spd"], instance["level"])
    instance["stats"]["spe"] = calculate_stat(bs["spe"], instance["level"])
    
    # HPも全快させる（レベルアップボーナス）
    instance["current_hp"] = instance["stats"]["max_hp"]
    
    new_move = base["learnset"].get(instance["level"])
    msg = f"\n**{instance['nickname']}** はレベル{instance['level']}になった！"
    
    if new_move:
        if len(instance["moves"]) < 4:
            instance["moves"].append(new_move)
            msg += f"\n『{MOVES[new_move]['name']}』を覚えた！"
        else:
            msg += f"\n『{MOVES[new_move]['name']}』を覚えたいけど、技がいっぱいだ…"
            
    return msg

# --- データ移行用関数 (kimera_core.pyの末尾に追加) ---
def migrate_old_data():
    """古い kimera_save.json を読み込み、ユーザーごとの個別ファイルに分割保存する"""
    old_path = DATA_DIR / "kimera_save.json"
    
    # 古いファイルがない、または既にバックアップ済みの場合は何もしない
    if not old_path.exists():
        return "古いデータファイル(kimera_save.json)が見つかりません。移行は不要か、既に完了しています。"

    try:
        # 古いデータを一括読み込み
        all_data = json.loads(old_path.read_text(encoding="utf-8"))
        count = 0

        for user_id, user_data in all_data.items():
            # 新しい保存関数を使って個別ファイルに書き出し
            # (注意: 既に新しい形式で遊んでデータがある場合は上書きされます)
            save_user_data(user_id, user_data)
            count += 1

        # 古いファイルをリネームしてバックアップにする（二重実行防止）
        old_path.rename(DATA_DIR / "kimera_save.json.bak")
        
        return f"成功: {count}人分のデータを個別ファイルに移行しました！\n古いファイルは 'kimera_save.json.bak' に変更しました。"
    
    except Exception as e:
        return f"エラー: データの移行中に問題が発生しました。\n{e}"