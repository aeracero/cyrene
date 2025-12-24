import json
from pathlib import Path

FILE = Path("nicknames.json")

def load_nicknames():
    if not FILE.exists():
        return {}
    return json.loads(FILE.read_text(encoding="utf-8"))

def save_nicknames(data):
    FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

def set_nickname(user_id: int, nickname: str):
    data = load_nicknames()
    data[str(user_id)] = nickname
    save_nicknames(data)

def get_nickname(user_id: int):
    data = load_nicknames()
    return data.get(str(user_id))
