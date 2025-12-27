# special_unlocks.py
import json
from pathlib import Path

# =====================
# 永続保存ディレクトリ（Railwayの /data）
# =====================
DATA_DIR = Path("/data")
DATA_DIR.mkdir(exist_ok=True)

FILE = DATA_DIR / "special_unlocks.json"

DATA_DIR = Path("/data")
DATA_DIR.mkdir(parents=True, exist_ok=True)

MYURION_FILE = DATA_DIR / "myurion_mode.json"

# =====================
# デフォルト状態
# =====================
_DEFAULT_STATE = {
    "janken_wins": 0,          # じゃんけん勝利数
    "nanoka_unlocked": False,  # 三月なのか 解放済み
    "danheng_stage1": False,   # 荒笛ラインを引いた
    "danheng_unlocked": False, # 丹恒 解放済み
}

def set_all_myurion_enabled(value: bool = True):
    data = _load_all()
    for uid, state in data.items():
        state["myurion_enabled"] = bool(value)
        data[uid] = state
    _save_all(data)

def load_myurion_data() -> dict:
    """ミュリオンモード用データを読み込み {user_id(str): {...}}"""
    if not MYURION_FILE.exists():
        return {}
    try:
        data = json.loads(MYURION_FILE.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return {}
        return data
    except Exception:
        return {}


def save_myurion_data(data: dict):
    """ミュリオンモード用データを保存"""
    MYURION_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


def set_all_myurion_enabled(enabled: bool = True):
    """
    全ユーザーのミュリオンモード ON/OFF をまとめて切り替える。
    - enabled=True なら全員「有効」
    - enabled=False なら全員「無効」
    """
    data = load_myurion_data()
    for uid, st in data.items():
        if not isinstance(st, dict):
            st = {}
        st.setdefault("unlocked", False)

        st["enabled"] = bool(enabled)
        # 全体ONする場合は、まだ未解放でも強制的に解放扱いにする
        if enabled and not st["unlocked"]:
            st["unlocked"] = True

        data[uid] = st

    save_myurion_data(data)


# =====================
# 内部ユーティリティ
# =====================
def _load_all() -> dict:
    if not FILE.exists():
        return {}
    try:
        return json.loads(FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_all(data: dict) -> None:
    FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _get_state_for(user_id: int) -> dict:
    data = _load_all()
    key = str(user_id)

    state = data.get(key, {})
    merged = _DEFAULT_STATE.copy()
    merged.update(state)

    return merged


def _set_state_for(user_id: int, state: dict) -> None:
    data = _load_all()
    data[str(user_id)] = state
    _save_all(data)


# =====================
# じゃんけん勝利数
# =====================
def inc_janken_win(user_id: int) -> int:
    """勝利数を+1 → 保存 → 現在値を返す"""
    state = _get_state_for(user_id)
    state["janken_wins"] = int(state.get("janken_wins", 0)) + 1
    _set_state_for(user_id, state)
    return state["janken_wins"]


def get_janken_wins(user_id: int) -> int:
    return int(_get_state_for(user_id).get("janken_wins", 0))


# =====================
# 三月なのか 解放
# =====================
def is_nanoka_unlocked(user_id: int) -> bool:
    return bool(_get_state_for(user_id).get("nanoka_unlocked", False))


def set_nanoka_unlocked(user_id: int, value: bool = True) -> None:
    state = _get_state_for(user_id)
    state["nanoka_unlocked"] = bool(value)
    _set_state_for(user_id, state)


# =====================
# 丹恒 ステップ1（荒笛ライン）
# =====================
def has_danheng_stage1(user_id: int) -> bool:
    return bool(_get_state_for(user_id).get("danheng_stage1", False))



def mark_danheng_stage1(user_id: int) -> None:
    state = _get_state_for(user_id)
    state["danheng_stage1"] = True
    _set_state_for(user_id, state)


# =====================
# 丹恒 解放フラグ
# =====================
def is_danheng_unlocked(user_id: int) -> bool:
    return bool(_get_state_for(user_id).get("danheng_unlocked", False))


def set_danheng_unlocked(user_id: int, value: bool = True) -> None:
    state = _get_state_for(user_id)
    state["danheng_unlocked"] = bool(value)
    _set_state_for(user_id, state)
