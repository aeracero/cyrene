# config.py
import os
from pathlib import Path
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

# 環境変数の読み込み
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "").strip()
if not DISCORD_TOKEN:
    raise RuntimeError("DISCORD_TOKEN is not set")

# 管理者設定
PRIMARY_ADMIN_ID = 916106297190019102  # あなたのID

# ディレクトリ設定
DATA_DIR = Path("/data")
DATA_DIR.mkdir(parents=True, exist_ok=True)

# ファイルパス
NICKNAMES_FILE = DATA_DIR / "nicknames.json"
ADMINS_FILE = DATA_DIR / "admins.json"
GUARDIAN_FILE = DATA_DIR / "guardian_levels.json"
AFFECTION_FILE = DATA_DIR / "affection.json"
AFFECTION_CONFIG_FILE = DATA_DIR / "affection_config.json"
MESSAGE_LIMIT_FILE = DATA_DIR / "message_limits.json"
MESSAGE_USAGE_FILE = DATA_DIR / "message_usage.json"
MESSAGE_LIMIT_CONFIG_FILE = DATA_DIR / "message_limit_config.json"
GACHA_FILE = DATA_DIR / "gacha.json"
MYURION_FILE = DATA_DIR / "myurion_mode.json"
SPECIAL_UNLOCKS_FILE = DATA_DIR / "special_unlocks.json"

# タイムゾーン
JST = timezone(timedelta(hours=9))

def today_str() -> str:
    """JST基準の日付文字列（YYYY-MM-DD）"""
    return datetime.now(JST).date().isoformat()