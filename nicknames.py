import json
from pathlib import Path

# ─────────────────────────
# データ保存先設定（Railway volume）
# ─────────────────────────
# Railway の Volume が /data にマウントされている前提
DATA_DIR = Path("/data")
DATA_DIR.mkdir(parents=True, exist_ok=True)

FILE = DATA_DIR / "nicknames.json"


def load_nicknames():
    """ニックネームの dict を読み込む"""
    if not FILE.exists():
        return {}
    try:
        return json.loads(FILE.read_text(encoding="utf-8"))
    except Exception:
        # 壊れたときでも bot が落ちないようにする
        return {}


def save_nicknames(data: dict):
    """ニックネームの dict を保存する"""
    FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def set_nickname(user_id: int, nickname: str):
    """ユーザーのあだ名を登録/更新"""
    data = load_nicknames()
    data[str(user_id)] = nickname
    save_nicknames(data)


def delete_nickname(user_id: int):
    """ユーザーのあだ名を削除"""
    data = load_nicknames()
    if str(user_id) in data:
        del data[str(user_id)]
        save_nicknames(data)


def get_nickname(user_id: int):
    """ユーザーのあだ名を取得。なければ None"""
    data = load_nicknames()
    return data.get(str(user_id))


def get_all_nicknames() -> dict:
    """データ管理モード用：全ユーザーのあだ名 dict を返す"""
    return load_nicknames()
