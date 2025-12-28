import json
from pathlib import Path
from config import (
    NICKNAMES_FILE, ADMINS_FILE, GUARDIAN_FILE, AFFECTION_FILE,
    AFFECTION_CONFIG_FILE, MESSAGE_LIMIT_FILE, MESSAGE_USAGE_FILE,
    MESSAGE_LIMIT_CONFIG_FILE, GACHA_FILE, MYURION_FILE, SPECIAL_UNLOCKS_FILE,
    PRIMARY_ADMIN_ID, today_str
)

# 言語設定用ファイル
LANGUAGE_FILE = Path("data/language.json")
# 返信モード保存用ファイル
REPLY_MODE_FILE = Path("data/reply_mode.json")

# --- 共通ユーティリティ ---
def _load_json(path: Path, default=None):
    if default is None: default = {}
    if not path.exists(): return default
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(default, list) and not isinstance(data, list): return default
        if isinstance(default, dict) and not isinstance(data, dict): return default
        return data
    except Exception:
        return default

def _save_json(path: Path, data):
    if not path.parent.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

# --- 言語設定 (JP/EN) ---
def load_languages(): return _load_json(LANGUAGE_FILE, {})

def get_user_lang(user_id):
    """ユーザーの言語を取得 ('jp' or 'en')。デフォルトは 'jp'"""
    data = load_languages()
    return data.get(str(user_id), "jp")

def set_user_lang(user_id, lang):
    """言語を設定 ('jp' or 'en')"""
    data = load_languages()
    data[str(user_id)] = lang
    _save_json(LANGUAGE_FILE, data)

# --- 返信モード ---
def load_reply_modes(): return _load_json(REPLY_MODE_FILE, {})
def get_reply_mode(user_id): return load_reply_modes().get(str(user_id), "mention")
def set_reply_mode(user_id, mode):
    data = load_reply_modes()
    data[str(user_id)] = mode
    _save_json(REPLY_MODE_FILE, data)

# --- あだ名 ---
def load_nicknames(): return _load_json(NICKNAMES_FILE, {})
def set_nickname(user_id, nickname):
    data = load_nicknames()
    data[str(user_id)] = nickname
    _save_json(NICKNAMES_FILE, data)
def get_nickname(user_id): return load_nicknames().get(str(user_id))
def delete_nickname(user_id):
    data = load_nicknames()
    if str(user_id) in data:
        del data[str(user_id)]
        _save_json(NICKNAMES_FILE, data)

# --- 管理者 ---
def load_admin_ids(): return set(_load_json(ADMINS_FILE, []))
def save_admin_ids(id_set): _save_json(ADMINS_FILE, list(id_set))
def is_admin(user_id):
    if user_id == PRIMARY_ADMIN_ID: return True
    return user_id in load_admin_ids()
def add_admin(user_id):
    if user_id == PRIMARY_ADMIN_ID: return
    ids = load_admin_ids()
    ids.add(user_id)
    save_admin_ids(ids)
def remove_admin(user_id):
    if user_id == PRIMARY_ADMIN_ID: return False
    ids = load_admin_ids()
    if user_id in ids:
        ids.remove(user_id)
        save_admin_ids(ids)
        return True
    return False

# --- 親衛隊レベル ---
def load_guardian_levels(): return _load_json(GUARDIAN_FILE, {})
def set_guardian_level(user_id, level):
    data = load_guardian_levels()
    data[str(user_id)] = int(level)
    _save_json(GUARDIAN_FILE, data)
def get_guardian_level(user_id): return load_guardian_levels().get(str(user_id))
def delete_guardian_level(user_id):
    data = load_guardian_levels()
    if str(user_id) in data:
        del data[str(user_id)]
        _save_json(GUARDIAN_FILE, data)

# --- 好感度 ---
DEFAULT_AFFECTION_CONFIG = {
    "level_thresholds": [0, 0, 1000, 4000, 16000, 640000, 33350337],
    "xp_actions": {"talk": 3, "rps_win": 10, "rps_lose": 5, "rps_draw": 7},
}
def load_affection_data(): return _load_json(AFFECTION_FILE, {})
def save_affection_data(data): _save_json(AFFECTION_FILE, data)
def load_affection_config(): 
    cfg = _load_json(AFFECTION_CONFIG_FILE, DEFAULT_AFFECTION_CONFIG.copy())
    base = DEFAULT_AFFECTION_CONFIG.copy()
    base.update(cfg)
    return base
def save_affection_config(cfg): _save_json(AFFECTION_CONFIG_FILE, cfg)

# --- メッセージ制限 & Bypass ---
DEFAULT_MSG_LIMIT_CONFIG = {"bypass_enabled": False, "bypass_users": []}
def load_message_limits(): return _load_json(MESSAGE_LIMIT_FILE, {})
def set_message_limit(user_id, limit):
    data = load_message_limits()
    if limit is None or limit <= 0: data.pop(str(user_id), None)
    else: data[str(user_id)] = int(limit)
    _save_json(MESSAGE_LIMIT_FILE, data)
def get_message_limit(user_id): return load_message_limits().get(str(user_id))
def delete_message_limit(user_id): set_message_limit(user_id, 0)

def load_message_usage(): return _load_json(MESSAGE_USAGE_FILE, {})
def get_message_usage(user_id):
    data = load_message_usage()
    info = data.get(str(user_id), {})
    today = today_str()
    if info.get("date") != today: return today, 0
    return today, info.get("count", 0)
def increment_message_usage(user_id):
    data = load_message_usage()
    today = today_str()
    info = data.get(str(user_id), {})
    if info.get("date") != today:
        info = {"date": today, "count": 1}
    else:
        info["count"] = info.get("count", 0) + 1
    data[str(user_id)] = info
    _save_json(MESSAGE_USAGE_FILE, data)
    return info["count"]

def load_message_limit_config(): 
    return _load_json(MESSAGE_LIMIT_CONFIG_FILE, DEFAULT_MSG_LIMIT_CONFIG.copy())
def save_message_limit_config(cfg): _save_json(MESSAGE_LIMIT_CONFIG_FILE, cfg)

def can_bypass_message_limit(user_id):
    if is_admin(user_id): return True
    cfg = load_message_limit_config()
    if not cfg.get("bypass_enabled", False): return False
    return str(user_id) in cfg.get("bypass_users", [])

def add_bypass_user(user_id):
    cfg = load_message_limit_config()
    users = set(cfg.get("bypass_users", []))
    users.add(str(user_id))
    cfg["bypass_users"] = list(users)
    save_message_limit_config(cfg)
def remove_bypass_user(user_id):
    cfg = load_message_limit_config()
    users = set(cfg.get("bypass_users", []))
    if str(user_id) in users:
        users.remove(str(user_id))
        cfg["bypass_users"] = list(users)
        save_message_limit_config(cfg)

def is_over_message_limit(user_id):
    limit = get_message_limit(user_id)
    if limit is None or limit <= 0: return False
    _, count = get_message_usage(user_id)
    return count >= limit

# --- ガチャ ---
def load_gacha_data(): return _load_json(GACHA_FILE, {})
def save_gacha_data(data): _save_json(GACHA_FILE, data)
def get_gacha_state(user_id):
    data = load_gacha_data()
    state = data.get(str(user_id))
    if not isinstance(state, dict):
        state = {
            "stones": 0, "pity_5": 0, "pity_4": 0, "guaranteed_cyrene": False,
            "cyrene_copies": 0, "page1_count": 0, "offbanner_tickets": 0, "last_daily": None,
        }
        data[str(user_id)] = state
        _save_json(GACHA_FILE, data)
    return state
def save_gacha_state(user_id, state):
    data = load_gacha_data()
    data[str(user_id)] = state
    _save_json(GACHA_FILE, data)

# --- ミュリオン ---
def load_myurion_data(): return _load_json(MYURION_FILE, {})
def save_myurion_data(data): _save_json(MYURION_FILE, data)
def get_myurion_state(user_id):
    data = load_myurion_data()
    st = data.get(str(user_id))
    if not isinstance(st, dict):
        st = {"unlocked": False, "enabled": False, "quiz_correct": 0}
        data[str(user_id)] = st
        _save_json(MYURION_FILE, data)
    return st
def save_myurion_state(user_id, st):
    data = load_myurion_data()
    data[str(user_id)] = st
    _save_json(MYURION_FILE, data)
def set_all_myurion_enabled(enabled: bool):
    data = load_myurion_data()
    for uid, st in data.items():
        if not isinstance(st, dict): st = {}
        st["enabled"] = bool(enabled)
        if enabled: st["unlocked"] = True
        data[uid] = st
    _save_json(MYURION_FILE, data)

# --- 特殊アンロック/じゃんけん勝利数管理 ---
def load_special_unlocks(): return _load_json(SPECIAL_UNLOCKS_FILE, {})
def save_special_unlocks(data): _save_json(SPECIAL_UNLOCKS_FILE, data)

def set_janken_wins_direct(user_id: int, wins: int):
    data = load_special_unlocks()
    info = data.get(str(user_id), {})
    info["janken_wins"] = max(0, int(wins))
    data[str(user_id)] = info
    save_special_unlocks(data)

def get_all_special_status():
    data = load_special_unlocks()
    results = []
    for uid, info in data.items():
        wins = info.get("janken_wins", 0)
        nano = "済" if info.get("nanoka_unlocked") else "未"
        dan = "済" if info.get("danheng_unlocked") else "未"
        if wins > 0 or nano == "済" or dan == "済":
            results.append(f"<@{uid}>: 勝{wins}/な{nano}/丹{dan}")
    return results