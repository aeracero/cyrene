# config.py
import os
from pathlib import Path
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

# 環境変数の読み込み
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "").strip()
# ★追加: Gemini APIキー
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()

if not DISCORD_TOKEN:
    # ローカル実行時などのために空文字許容、あるいはエラー送出
    # raise RuntimeError("DISCORD_TOKEN is not set")
    pass

# 管理者設定
PRIMARY_ADMIN_ID = 916106297190019102  # あなたのID

# ディレクトリ設定 (Railwayの永続ボリューム /data を使用)
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

# ★追加: これらが未定義だったためリセットされていました
LANGUAGE_FILE = DATA_DIR / "language.json"
REPLY_MODE_FILE = DATA_DIR / "reply_mode.json"
ACHIEVEMENTS_FILE = DATA_DIR / "achievements.json"  # 二つ名・実績

# ★追加: ログ確認モードの状態保存用
LOG_MODE_FILE = DATA_DIR / "log_mode.json"

# タイムゾーン
JST = timezone(timedelta(hours=9))

def today_str() -> str:
    """JST基準の日付文字列（YYYY-MM-DD）"""
    return datetime.now(JST).date().isoformat()