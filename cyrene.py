# cyrene.py
import os
import re
import json
import random
from pathlib import Path
from datetime import datetime, timedelta, timezone

import discord
from dotenv import load_dotenv

from lines import get_cyrene_reply, get_rps_line, ARAFUE_TRIGGER_LINE  # 好感度対応版: 第2引数にレベル
from forms import (
    get_user_form,
    set_user_form,
    get_all_forms,
    set_all_forms,
    resolve_form_code,
    resolve_form_spec,
    get_form_display_name,
)

from lines_aglaia import get_reply as get_aglaia_reply
from lines_trisbeas import get_reply as get_trisbeas_reply
from lines_anaxagoras import get_reply as get_anaxagoras_reply
from lines_hyacinthia import get_reply as get_hyacinthia_reply
from lines_medimos import get_reply as get_medimos_reply
from lines_sepharia import get_reply as get_sepharia_reply
from lines_castoris import get_reply as get_castoris_reply
from lines_phainon_kasreina import get_reply as get_phainon_kasreina_reply
from lines_electra import get_reply as get_electra_reply
from lines_cerydra import get_reply as get_cerydra_reply
from lines_nanoka import get_reply as get_nanoka_reply
from lines_danheng import get_reply as get_danheng_reply

from special_unlocks import (
    inc_janken_win,
    get_janken_wins,
    is_nanoka_unlocked,
    set_nanoka_unlocked,
    has_danheng_stage1,
    mark_danheng_stage1,
    is_danheng_unlocked,
    set_danheng_unlocked,
)


# =====================
# 環境変数
# =====================
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "").strip()
if not DISCORD_TOKEN:
    raise RuntimeError("DISCORD_TOKEN is not set")

# ★ 最初のメイン管理者（あなたのID）
PRIMARY_ADMIN_ID = 916106297190019102  # 必要なら自分のIDに変更

# =====================
# Discord
# =====================
intents = discord.Intents.default()
intents.message_content = True
# 特権インテント（members/presences）は要求しない
client = discord.Client(intents=intents)

# =====================
# データ保存用ディレクトリ（Railway volume: /data）
# =====================
DATA_DIR = Path("/data")
DATA_DIR.mkdir(parents=True, exist_ok=True)

JST = timezone(timedelta(hours=9))


def today_str() -> str:
    """JST基準の日付文字列（YYYY-MM-DD）"""
    return datetime.now(JST).date().isoformat()

# =====================
# あだ名保存（永続: /data/nicknames.json）
# =====================
DATA_FILE = DATA_DIR / "nicknames.json"


def load_data():
    if not DATA_FILE.exists():
        return {}
    try:
        return json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_data(data):
    DATA_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


def set_nickname(user_id, nickname):
    data = load_data()
    data[str(user_id)] = nickname
    save_data(data)


def delete_nickname(user_id):
    data = load_data()
    if str(user_id) in data:
        del data[str(user_id)]
        save_data(data)


def get_nickname(user_id):
    data = load_data()
    return data.get(str(user_id))

# =====================
# 管理者保存（永続: /data/admins.json）
# =====================
ADMINS_FILE = DATA_DIR / "admins.json"


def load_admin_ids():
    if not ADMINS_FILE.exists():
        return set()
    try:
        raw = json.loads(ADMINS_FILE.read_text(encoding="utf-8"))
        if isinstance(raw, list):
            ids = set()
            for v in raw:
                try:
                    ids.add(int(v))
                except Exception:
                    continue
            return ids
        return set()
    except Exception:
        return set()


def save_admin_ids(id_set):
    ADMINS_FILE.write_text(
        json.dumps(list(id_set), ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


def is_admin(user_id):
    if user_id == PRIMARY_ADMIN_ID:
        return True
    return user_id in load_admin_ids()


def add_admin(user_id):
    if user_id == PRIMARY_ADMIN_ID:
        return
    ids = load_admin_ids()
    ids.add(user_id)
    save_admin_ids(ids)


def remove_admin(user_id):
    if user_id == PRIMARY_ADMIN_ID:
        return False
    ids = load_admin_ids()
    if user_id in ids:
        ids.remove(user_id)
        save_admin_ids(ids)
        return True
    return False

# =====================
# 親衛隊レベル保存（永続: /data/guardian_levels.json）
# =====================
GUARDIAN_FILE = DATA_DIR / "guardian_levels.json"


def load_guardian_levels() -> dict:
    """親衛隊レベルの dict を読み込む {user_id(str): level(int)}"""
    if not GUARDIAN_FILE.exists():
        return {}
    try:
        data = json.loads(GUARDIAN_FILE.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return {}
        return data
    except Exception:
        return {}


def save_guardian_levels(data: dict):
    """親衛隊レベル dict を保存"""
    GUARDIAN_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


def set_guardian_level(user_id: int, level: int):
    """指定ユーザーの親衛隊レベルを設定/更新"""
    data = load_guardian_levels()
    data[str(user_id)] = int(level)
    save_guardian_levels(data)


def get_guardian_level(user_id: int):
    """指定ユーザーの親衛隊レベルを取得。なければ None"""
    data = load_guardian_levels()
    return data.get(str(user_id))


def delete_guardian_level(user_id: int):
    """指定ユーザーの親衛隊レベルを削除"""
    data = load_guardian_levels()
    if str(user_id) in data:
        del data[str(user_id)]
        save_guardian_levels(data)

# =====================
# 好感度データ保存（永続: /data/affection.json）
# =====================
AFFECTION_FILE = DATA_DIR / "affection.json"


def load_affection_data() -> dict:
    """{user_id(str): {"xp": int}}"""
    if not AFFECTION_FILE.exists():
        return {}
    try:
        data = json.loads(AFFECTION_FILE.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return {}
        return data
    except Exception:
        return {}


def save_affection_data(data: dict):
    AFFECTION_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

# =====================
# 好感度設定（閾値 & アクションごとの経験値）
# =====================
AFFECTION_CONFIG_FILE = DATA_DIR / "affection_config.json"

# ★ デフォルト設定
DEFAULT_AFFECTION_CONFIG = {
    # 各レベルに必要な累積経験値（インデックス = レベル）
    "level_thresholds": [0, 0, 1000, 4000, 16000, 640000, 33350337],
    # 各アクションで獲得する経験値
    "xp_actions": {
        "talk": 3,
        "rps_win": 10,
        "rps_lose": 5,
        "rps_draw": 7,
    },
}


def load_affection_config() -> dict:
    """好感度設定を読み込み（なければデフォルトを書き出す）"""
    if not AFFECTION_CONFIG_FILE.exists():
        save_affection_config(DEFAULT_AFFECTION_CONFIG)
        return DEFAULT_AFFECTION_CONFIG.copy()
    try:
        data = json.loads(AFFECTION_CONFIG_FILE.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return DEFAULT_AFFECTION_CONFIG.copy()
        cfg = DEFAULT_AFFECTION_CONFIG.copy()
        cfg.update(data)
        if "level_thresholds" not in cfg or not isinstance(cfg["level_thresholds"], list):
            cfg["level_thresholds"] = DEFAULT_AFFECTION_CONFIG["level_thresholds"]
        if "xp_actions" not in cfg or not isinstance(cfg["xp_actions"], dict):
            cfg["xp_actions"] = DEFAULT_AFFECTION_CONFIG["xp_actions"]
        return cfg
    except Exception:
        return DEFAULT_AFFECTION_CONFIG.copy()


def save_affection_config(cfg: dict):
    AFFECTION_CONFIG_FILE.write_text(
        json.dumps(cfg, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


def get_level_from_xp(xp: int, cfg: dict) -> int:
    """累積XPからレベルを算出"""
    thresholds = cfg.get("level_thresholds", [0])
    if len(thresholds) <= 1:
        return 1
    level = 1
    for lv in range(1, len(thresholds)):
        need = thresholds[lv]
        if xp >= need:
            level = lv
        else:
            break
    return max(1, level)


def get_user_affection(user_id: int):
    """(xp, level) を返す"""
    cfg = load_affection_config()
    data = load_affection_data()
    info = data.get(str(user_id), {})
    xp = int(info.get("xp", 0))
    level = get_level_from_xp(xp, cfg)
    return xp, level


def add_affection_xp(user_id: int, delta: int, reason: str = ""):
    """好感度XPを加算（マイナスもOK・0以下は0にクリップ）"""
    if delta == 0:
        return
    data = load_affection_data()
    info = data.get(str(user_id), {})
    xp = int(info.get("xp", 0))
    xp = max(0, xp + delta)
    info["xp"] = xp
    data[str(user_id)] = info
    save_affection_data(data)

# =====================
# メッセージ制限（回数/日）
# =====================
MESSAGE_LIMIT_FILE = DATA_DIR / "message_limits.json"
MESSAGE_USAGE_FILE = DATA_DIR / "message_usage.json"
MESSAGE_LIMIT_CONFIG_FILE = DATA_DIR / "message_limit_config.json"

DEFAULT_MESSAGE_LIMIT_CONFIG = {
    "bypass_enabled": False,
    "allow_bypass_grant": False,
    "bypass_users": [],
}


def load_message_limits() -> dict:
    if not MESSAGE_LIMIT_FILE.exists():
        return {}
    try:
        data = json.loads(MESSAGE_LIMIT_FILE.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return {}
        return data
    except Exception:
        return {}


def save_message_limits(data: dict):
    MESSAGE_LIMIT_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


def get_message_limit(user_id: int):
    data = load_message_limits()
    val = data.get(str(user_id))
    if val is None:
        return None
    try:
        return int(val)
    except Exception:
        return None


def set_message_limit(user_id: int, limit: int):
    data = load_message_limits()
    if limit is None or limit <= 0:
        data.pop(str(user_id), None)
    else:
        data[str(user_id)] = int(limit)
    save_message_limits(data)


def delete_message_limit(user_id: int):
    set_message_limit(user_id, 0)


def load_message_usage() -> dict:
    if not MESSAGE_USAGE_FILE.exists():
        return {}
    try:
        data = json.loads(MESSAGE_USAGE_FILE.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return {}
        return data
    except Exception:
        return {}


def save_message_usage(data: dict):
    MESSAGE_USAGE_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


def get_message_usage(user_id: int):
    """(date_str, count) を返す。日付が変わっていれば count=0 扱い"""
    data = load_message_usage()
    info = data.get(str(user_id))
    today = today_str()
    if not info or not isinstance(info, dict):
        return today, 0
    date = info.get("date", today)
    try:
        count = int(info.get("count", 0))
    except Exception:
        count = 0
    if date != today:
        return today, 0
    return today, max(0, count)


def increment_message_usage(user_id: int) -> int:
    data = load_message_usage()
    today = today_str()
    info = data.get(str(user_id), {})
    date = info.get("date", today)
    try:
        count = int(info.get("count", 0))
    except Exception:
        count = 0

    if date != today:
        count = 0
    count += 1

    info["date"] = today
    info["count"] = count
    data[str(user_id)] = info
    save_message_usage(data)
    return count


def is_over_message_limit(user_id: int) -> bool:
    limit = get_message_limit(user_id)
    if limit is None or limit <= 0:
        return False
    _, count = get_message_usage(user_id)
    return count >= limit


def load_message_limit_config() -> dict:
    if not MESSAGE_LIMIT_CONFIG_FILE.exists():
        save_message_limit_config(DEFAULT_MESSAGE_LIMIT_CONFIG)
        return DEFAULT_MESSAGE_LIMIT_CONFIG.copy()
    try:
        data = json.loads(MESSAGE_LIMIT_CONFIG_FILE.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return DEFAULT_MESSAGE_LIMIT_CONFIG.copy()
        cfg = DEFAULT_MESSAGE_LIMIT_CONFIG.copy()
        cfg.update(data)
        if "bypass_users" not in cfg or not isinstance(cfg["bypass_users"], list):
            cfg["bypass_users"] = []
        return cfg
    except Exception:
        return DEFAULT_MESSAGE_LIMIT_CONFIG.copy()


def save_message_limit_config(cfg: dict):
    MESSAGE_LIMIT_CONFIG_FILE.write_text(
        json.dumps(cfg, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


def can_bypass_message_limit(user_id: int) -> bool:
    """このユーザーがメッセージ制限を無視できるか"""
    if is_admin(user_id):
        return True

    cfg = load_message_limit_config()
    if not cfg.get("bypass_enabled", False):
        return False

    bypass_users = cfg.get("bypass_users", [])
    bypass_set = {str(uid) for uid in bypass_users}
    return str(user_id) in bypass_set

# =====================
# 会話状態管理
# =====================
waiting_for_nickname = set()
waiting_for_rename = set()
admin_data_mode = set()
waiting_for_admin_add = set()
waiting_for_admin_remove = set()
waiting_for_rps_choice = set()
waiting_for_guardian_level = {}   # {管理者ID: 対象ユーザーID}
waiting_for_msg_limit = {}        # {管理者ID: 対象ユーザーID}
waiting_for_transform_code = set()  # 自分の変身コード入力待ちユーザー

# =====================
# 起動
# =====================
@client.event
async def on_ready():
    print(f"ログイン成功: {client.user} ({client.user.id})")

# =====================
# じゃんけん
# =====================
JANKEN_HANDS = ["グー", "チョキ", "パー"]


def parse_hand(text: str):
    if "グー" in text:
        return "グー"
    if "チョキ" in text:
        return "チョキ"
    if "パー" in text:
        return "パー"
    return None


def judge_janken(user_hand: str, bot_hand: str) -> str:
    if user_hand == bot_hand:
        return "draw"
    win = (
        (user_hand == "グー" and bot_hand == "チョキ") or
        (user_hand == "チョキ" and bot_hand == "パー") or
        (user_hand == "パー" and bot_hand == "グー")
    )
    return "win" if win else "lose"


def generate_reply_for_form(form_key: str, message: str, affection_level: int) -> str:
    """
    変身状態（黄金裔/開拓者）に応じて返答を切り替える。
    - 各フォームは lines_◯◯.py の get_reply を使う
    - 未定義 or 不明なフォームキーの場合はキュレネにフォールバック
    """
    if form_key == "aglaia":
        return get_aglaia_reply(message, affection_level)
    if form_key == "trisbeas":
        return get_trisbeas_reply(message, affection_level)
    if form_key == "anaxagoras":
        return get_anaxagoras_reply(message, affection_level)
    if form_key == "hyacinthia":
        return get_hyacinthia_reply(message, affection_level)
    if form_key == "medimos":
        return get_medimos_reply(message, affection_level)
    if form_key == "sepharia":
        return get_sepharia_reply(message, affection_level)
    if form_key == "castoris":
        return get_castoris_reply(message, affection_level)
    if form_key == "phainon_kasreina":
        return get_phainon_kasreina_reply(message, affection_level)
    if form_key == "electra":
        return get_electra_reply(message, affection_level)
    if form_key == "cerydra":
        return get_cerydra_reply(message, affection_level)
    if form_key == "nanoka":
        return get_nanoka_reply(message, affection_level)
    if form_key == "danheng":
        return get_danheng_reply(message, affection_level)

    # キュレネ（デフォルト）
    try:
        # 好感度対応版（message, affection_level 両方取る版）に対応
        return get_cyrene_reply(message, affection_level)
    except TypeError:
        # 古い lines.py（message だけ取る版）の場合でも落ちないようフォールバック
        return get_cyrene_reply(message)

# =====================
# メッセージ処理
# =====================
@client.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    user_id = message.author.id

    # 状態フラグ
    is_waiting_nick = (user_id in waiting_for_nickname) or (user_id in waiting_for_rename)
    is_waiting_admin = (user_id in waiting_for_admin_add) or (user_id in waiting_for_admin_remove)
    is_waiting_rps = (user_id in waiting_for_rps_choice)
    is_admin_mode = user_id in admin_data_mode
    is_waiting_guardian = user_id in waiting_for_guardian_level
    is_waiting_limit = user_id in waiting_for_msg_limit
    is_waiting_transform = user_id in waiting_for_transform_code
    is_mentioned = client.user in message.mentions

    # どのモードでもない＋メンションもない → 無視
    if not (is_mentioned or is_waiting_nick or is_waiting_admin or is_waiting_rps
            or is_admin_mode or is_waiting_guardian or is_waiting_limit or is_waiting_transform):
        return

    # 本文（botメンションを除去）
    content = re.sub(rf"<@!?{client.user.id}>", "", message.content).strip()

    nickname = get_nickname(user_id)
    name = nickname if nickname else message.author.display_name

    admin_flag = is_admin(user_id)

    # 現在のフォーム
    current_form = get_user_form(user_id)
    current_form_name = get_form_display_name(current_form)

    # ===== メッセージ制限チェック =====
    if not admin_flag and not can_bypass_message_limit(user_id):
        # 変身コード入力中は制限チェックをスキップしてもいいかな、と判断
        if not is_waiting_transform:
            if is_over_message_limit(user_id):
                await message.channel.send(
                    f"{message.author.mention} ごめんね、今日はここまでにしておきましょう？\n"
                    "また明日、ゆっくりお話ししましょ♪"
                )
                return
            increment_message_usage(user_id)

    # ===== 自分の変身コード入力待ち =====
    # ===== 自分の変身コード入力待ち =====
    if user_id in waiting_for_transform_code:
        text = content if content else message.content.strip()

        # ★ 特別ルート：三月なのか / 長夜月
        if "なのになってみて" in text:
            # コード待ち状態は一度解除
            waiting_for_transform_code.discard(user_id)

            if not is_nanoka_unlocked(user_id):
                await message.channel.send(
                    f"{message.author.mention} ごめんね、その姿になるにはまだ条件が足りないみたい…。\n"
                    "まずは、あたしとのじゃんけんに何度も勝ってみて？ それからもう一度お願いしてくれる？"
                )
                return

            set_user_form(user_id, "nanoka")
            await message.channel.send(
                f"{message.author.mention} 今日から、あたしは「三月なのか / 長夜月」の姿でもあなたと一緒にいられるわ♪"
            )
            return

        # ★ 特別ルート：丹恒
        if "たんたんになってみて" in text:
            # コード待ち状態は一度解除
            waiting_for_transform_code.discard(user_id)

            if not is_danheng_unlocked(user_id):
                await message.channel.send(
                    f"{message.author.mention} その姿になるには、まだ鍵が足りないみたい…。\n"
                    "あの荒笛のことを、もっとよく知ってみて？ きっと道が開けるわ。"
                )
                return

            set_user_form(user_id, "danheng")
            await message.channel.send(
                f"{message.author.mention} …わかった。今日は彼の姿で、あなたと共に歩こう。\n"
                "無茶だけはしないでね。あなたを守る役目は、ちゃんと果たしたいから。"
            )
            return

        # ↓ ここからは「ふつうの変身コード」として扱う
        code = text.replace(" ", "").replace("　", "")
        form_key = resolve_form_code(code)

        if not form_key:
            await message.channel.send(
                f"{message.author.mention} そのコードでは変身できないみたい…。\n"
                "アグライアなら `KaLos618`、トリスビアスなら `HapLotes405` みたいに、"
                "もう一度正しい変身コードを教えてくれる？"
            )
            return

        set_user_form(user_id, form_key)
        waiting_for_transform_code.discard(user_id)

        form_name = get_form_display_name(form_key)
        await message.channel.send(
            f"{message.author.mention} 分かったわ、今からあたしは **{form_name}** として振る舞うわ♪"
        )
        return


    # ===== 親衛隊レベル数値入力待ち =====
    if user_id in waiting_for_guardian_level:
        target_id = waiting_for_guardian_level[user_id]
        text = content if content else message.content.strip()
        nums = re.findall(r"(-?\d+)", text)
        if not nums:
            await message.channel.send(
                f"{message.author.mention} 親衛隊レベルは数字で教えて？ 例えば `3` みたいにね。"
            )
            return

        level_val = int(nums[0])
        set_guardian_level(target_id, level_val)

        member = None
        if message.guild:
            member = message.guild.get_member(target_id)

        display = member.display_name if member else f"ID: {target_id}"

        del waiting_for_guardian_level[user_id]

        await message.channel.send(
            f"{message.author.mention} {display} の親衛隊レベルを **Lv.{level_val}** に設定したわ♪"
        )
        return

    # ===== メッセージ制限の数値入力待ち =====
    if user_id in waiting_for_msg_limit:
        target_id = waiting_for_msg_limit[user_id]
        text = content if content else message.content.strip()
        nums = re.findall(r"(-?\d+)", text)
        if not nums:
            await message.channel.send(
                f"{message.author.mention} 1日に何回までにするか、数字で教えて？\n"
                "例えば `20` って送ってくれれば、1日20回までにするわ♪\n"
                "`0` 以下なら制限なしに戻すわ。"
            )
            return

        limit_val = int(nums[0])
        set_message_limit(target_id, limit_val)

        member = None
        if message.guild:
            member = message.guild.get_member(target_id)

        display = member.display_name if member else f"ID: {target_id}"

        del waiting_for_msg_limit[user_id]

        if limit_val <= 0:
            await message.channel.send(
                f"{message.author.mention} {display} のメッセージ制限を解除したわ。"
            )
        else:
            await message.channel.send(
                f"{message.author.mention} {display} は 1日 **{limit_val} 回** までお話しできるように設定したわ♪"
            )
        return

    # ===== じゃんけんの手入力待ち =====
    if user_id in waiting_for_rps_choice:
        text = content if content else message.content.strip()
        hand = parse_hand(text)
        if not hand:
            await message.channel.send(
                f"{message.author.mention} グー / チョキ / パー のどれかで教えて？"
            )
            return

        bot_hand = random.choice(JANKEN_HANDS)
        result = judge_janken(hand, bot_hand)
        flavor = get_rps_line(result)

        # ★ 勝ったら勝利数カウント
        if result == "win":
            wins = inc_janken_win(user_id)
        else:
            wins = get_janken_wins(user_id)

        waiting_for_rps_choice.discard(user_id)

        await message.channel.send(
            f"{message.author.mention} {name} は **{hand}**、あたしは **{bot_hand}** よ。\n"
            f"{flavor}\n"
            f"（これまでに {wins} 回、あたしに勝ってるわ♡）"
        )

        cfg = load_affection_config()
        xp_actions = cfg.get("xp_actions", {})
        if result == "win":
            delta = int(xp_actions.get("rps_win", 0))
        elif result == "lose":
            delta = int(xp_actions.get("rps_lose", 0))
        else:
            delta = int(xp_actions.get("rps_draw", 0))
        add_affection_xp(user_id, delta, reason=f"rps_{result}")
        return

    # ===== 管理者追加/削除の @ 待ち =====
    if user_id in waiting_for_admin_add:
        targets = [m for m in message.mentions if m.id != client.user.id]
        if not targets:
            await message.channel.send(
                f"{message.author.mention} 管理者にしたい人を `@ユーザー` で教えて？"
            )
            return
        target = targets[0]
        add_admin(target.id)
        waiting_for_admin_add.discard(user_id)
        await message.channel.send(
            f"{message.author.mention} {target.display_name} を管理者に追加したわ♪"
        )
        return

    if user_id in waiting_for_admin_remove:
        targets = [m for m in message.mentions if m.id != client.user.id]
        if not targets:
            await message.channel.send(
                f"{message.author.mention} 管理者から外したい人を `@ユーザー` で教えて？"
            )
            return
        target = targets[0]
        ok = remove_admin(target.id)
        waiting_for_admin_remove.discard(user_id)

        if ok:
            await message.channel.send(
                f"{message.author.mention} {target.display_name} を管理者から外したわ。"
            )
        else:
            await message.channel.send(
                f"{message.author.mention} その人は管理者じゃないか、メイン管理者だから外せないみたい。"
            )
        return

    # ===== あだ名入力待ち =====
    if user_id in waiting_for_nickname:
        new_name = content if content else message.content.strip()
        if not new_name:
            await message.channel.send(
                f"{message.author.mention} もう一度、呼び名を教えて？"
            )
            return
        set_nickname(user_id, new_name)
        waiting_for_nickname.discard(user_id)
        await message.channel.send(
            f"{message.author.mention} ふふ…これからは「{new_name}」って呼ぶわね♪"
        )
        return

    if user_id in waiting_for_rename:
        new_name = content if content else message.content.strip()
        if not new_name:
            await message.channel.send(
                f"{message.author.mention} 新しい呼び名、もう一度教えて？"
            )
            return
        set_nickname(user_id, new_name)
        waiting_for_rename.discard(user_id)
        await message.channel.send(
            f"{message.author.mention} 了解♪ 今日から「{new_name}」よ。"
        )
        return

    # ===== データ管理モード中 =====
    if user_id in admin_data_mode:
        # データ管理終了
        if "データ管理終了" in content:
            admin_data_mode.discard(user_id)
            await message.channel.send(
                f"{message.author.mention} データ管理モードを終了するわ。また必要になったら呼んでね。"
            )
            return

        # ニックネーム確認
        if "ニックネーム確認" in content:
            data = load_data()
            if not data:
                await message.channel.send(
                    f"{message.author.mention} まだ登録されているあだ名はないみたい。"
                )
                return
            lines = ["【あだ名一覧】"]
            for uid_str, nick in data.items():
                try:
                    uid_int = int(uid_str)
                except Exception:
                    uid_int = None
                member = None
                if message.guild and uid_int is not None:
                    member = message.guild.get_member(uid_int)
                if member:
                    lines.append(f"- {member.display_name} (ID: {uid_str}) → {nick}")
                else:
                    lines.append(f"- ID: {uid_str} → {nick}")
            await message.channel.send("\n".join(lines))
            return

        # 親衛隊レベル編集メニュー
        if "親衛隊レベル編集" in content:
            await message.channel.send(
                f"{message.author.mention} 親衛隊レベルをどうしたい？\n"
                "- `親衛隊レベル確認` … 全員のレベル一覧を表示\n"
                "- `親衛隊レベル設定 @ユーザー` … 特定ユーザーのレベルを設定/変更\n"
                "- `親衛隊レベル削除 @ユーザー` … 特定ユーザーのレベルを削除\n"
                "- `データ管理終了` … モード終了"
            )
            return

        # 親衛隊レベル確認
        if content == "親衛隊レベル確認":
            levels = load_guardian_levels()
            if not levels:
                await message.channel.send(
                    f"{message.author.mention} まだ親衛隊レベルは誰も登録されていないみたい。"
                )
                return
            lines = ["【親衛隊レベル一覧】"]
            for uid_str, lv in levels.items():
                try:
                    uid_int = int(uid_str)
                except Exception:
                    uid_int = None
                member = None
                if message.guild and uid_int is not None:
                    member = message.guild.get_member(uid_int)
                if member:
                    lines.append(f"- {member.display_name} (ID: {uid_str}) → Lv.{lv}")
                else:
                    lines.append(f"- ID: {uid_str} → Lv.{lv}")
            await message.channel.send("\n".join(lines))
            return

        # 親衛隊レベル設定
        if content.startswith("親衛隊レベル設定"):
            targets = [m for m in message.mentions if m.id != client.user.id]
            if not targets:
                await message.channel.send(
                    f"{message.author.mention} 誰のレベルを設定するか、`@ユーザー` を付けて教えて？\n"
                    "例: `親衛隊レベル設定 @ユーザー`"
                )
                return
            target = targets[0]
            waiting_for_guardian_level[user_id] = target.id
            await message.channel.send(
                f"{message.author.mention} {target.display_name} の親衛隊レベルをいくつにする？ 数字で教えてね。\n"
                "例えば `3` みたいに送ってくれればいいわ♪"
            )
            return

        # 親衛隊レベル削除
        if content.startswith("親衛隊レベル削除"):
            targets = [m for m in message.mentions if m.id != client.user.id]
            if not targets:
                await message.channel.send(
                    f"{message.author.mention} 誰のレベルを消すか、`@ユーザー` を付けて教えて？\n"
                    "例: `親衛隊レベル削除 @ユーザー`"
                )
                return
            target = targets[0]
            delete_guardian_level(target.id)
            await message.channel.send(
                f"{message.author.mention} {target.display_name} の親衛隊レベルを削除したわ。"
            )
            return

        # 好感度編集メニュー
        if "好感度編集" in content:
            await message.channel.send(
                f"{message.author.mention} 好感度の設定をどうする？\n"
                "- `好感度設定確認` … レベル閾値とアクションごとのXPを表示\n"
                "- `好感度アクション設定 アクション名 数値` … 例: `好感度アクション設定 talk 5`\n"
                "- `好感度レベル設定 レベル 数値` … 例: `好感度レベル設定 3 4000`\n"
                "- `データ管理終了` … モード終了"
            )
            return

        # 好感度設定確認
        if "好感度設定確認" in content:
            cfg = load_affection_config()
            thresholds = cfg.get("level_thresholds", [])
            xp_actions = cfg.get("xp_actions", {})
            lines = ["【好感度設定】", "〈レベル閾値（累積XP）〉"]
            for lv, xp_need in enumerate(thresholds):
                lines.append(f"- Lv.{lv}: {xp_need} XP")
            lines.append("\n〈アクション別XP〉")
            for k, v in xp_actions.items():
                lines.append(f"- {k}: {v} XP")
            await message.channel.send("\n".join(lines))
            return

        # 好感度アクション設定
        if content.startswith("好感度アクション設定"):
            parts = content.split()
            if len(parts) < 3:
                await message.channel.send(
                    f"{message.author.mention} `好感度アクション設定 アクション名 数値` の形で教えて？\n"
                    "例: `好感度アクション設定 talk 5`"
                )
                return
            action_name = parts[1]
            try:
                xp_val = int(parts[2])
            except ValueError:
                await message.channel.send(
                    f"{message.author.mention} XP は数字でお願いね。"
                )
                return
            cfg = load_affection_config()
            xp_actions = cfg.get("xp_actions", {})
            xp_actions[action_name] = xp_val
            cfg["xp_actions"] = xp_actions
            save_affection_config(cfg)
            await message.channel.send(
                f"{message.author.mention} アクション `{action_name}` のXPを **{xp_val}** に設定したわ。"
            )
            return

        # 好感度レベル設定
        if content.startswith("好感度レベル設定"):
            parts = content.split()
            if len(parts) < 3:
                await message.channel.send(
                    f"{message.author.mention} `好感度レベル設定 レベル 数値` の形で教えて？\n"
                    "例: `好感度レベル設定 3 4000`"
                )
                return
            try:
                lv = int(parts[1])
                xp_need = int(parts[2])
            except ValueError:
                await message.channel.send(
                    f"{message.author.mention} レベルもXPも数字でお願いね。"
                )
                return
            cfg = load_affection_config()
            thresholds = cfg.get("level_thresholds", [0])
            while len(thresholds) <= lv:
                thresholds.append(thresholds[-1] + 10)
            thresholds[lv] = xp_need
            cfg["level_thresholds"] = thresholds
            save_affection_config(cfg)
            await message.channel.send(
                f"{message.author.mention} Lv.{lv} に必要なXPを **{xp_need}** に設定したわ。"
            )
            return

        # メッセージ制限編集メニュー
        if "メッセージ制限編集" in content:
            await message.channel.send(
                f"{message.author.mention} メッセージ制限をどうする？\n"
                "- `メッセージ制限確認` … 制限が設定されているユーザー一覧\n"
                "- `メッセージ制限設定 @ユーザー` … その人の1日あたり上限回数を設定\n"
                "- `メッセージ制限削除 @ユーザー` … その人の制限を解除\n"
                "- `データ管理終了` … モード終了"
            )
            return

        # メッセージ制限確認
        if content == "メッセージ制限確認":
            limits = load_message_limits()
            if not limits:
                await message.channel.send(
                    f"{message.author.mention} まだメッセージ制限は誰にも設定されていないみたい。"
                )
                return
            lines = ["【メッセージ制限一覧（1日あたり）】"]
            for uid_str, limit in limits.items():
                try:
                    uid_int = int(uid_str)
                except Exception:
                    uid_int = None
                member = None
                if message.guild and uid_int is not None:
                    member = message.guild.get_member(uid_int)
                if member:
                    lines.append(f"- {member.display_name} (ID: {uid_str}) → {limit} 回/日")
                else:
                    lines.append(f"- ID: {uid_str} → {limit} 回/日")
            await message.channel.send("\n".join(lines))
            return

        # メッセージ制限設定
        if content.startswith("メッセージ制限設定"):
            targets = [m for m in message.mentions if m.id != client.user.id]
            if not targets:
                await message.channel.send(
                    f"{message.author.mention} 誰の制限を設定するか、`@ユーザー` を付けて教えて？\n"
                    "例: `メッセージ制限設定 @ユーザー`"
                )
                return
            target = targets[0]
            waiting_for_msg_limit[user_id] = target.id
            await message.channel.send(
                f"{message.author.mention} {target.display_name} は1日に何回までお話しできるようにする？\n"
                "数字だけ送ってくれればいいわ♪ `0` 以下なら制限なしに戻すわ。"
            )
            return

        # メッセージ制限削除
        if content.startswith("メッセージ制限削除"):
            targets = [m for m in message.mentions if m.id != client.user.id]
            if not targets:
                await message.channel.send(
                    f"{message.author.mention} 誰の制限を解除するか、`@ユーザー` を付けて教えて？\n"
                    "例: `メッセージ制限削除 @ユーザー`"
                )
                return
            target = targets[0]
            delete_message_limit(target.id)
            await message.channel.send(
                f"{message.author.mention} {target.display_name} のメッセージ制限を解除したわ。"
            )
            return

        # メッセージ制限bypass系（前回実装ずみ）
        if "メッセージ制限bypass編集" in content:
            if user_id != PRIMARY_ADMIN_ID:
                await message.channel.send(
                    f"{message.author.mention} ごめんね、この設定はいちばん上の管理者専用なの。"
                )
                return
            await message.channel.send(
                f"{message.author.mention} メッセージ制限のbypass設定をどうする？\n"
                "- `メッセージ制限bypass確認`\n"
                "- `メッセージ制限bypass全体オン` / `メッセージ制限bypass全体オフ`\n"
                "- `メッセージ制限bypass付与許可オン` / `メッセージ制限bypass付与許可オフ`\n"
                "- `メッセージ制限bypass付与 @ユーザー`\n"
                "- `メッセージ制限bypass削除 @ユーザー`\n"
                "- `データ管理終了`"
            )
            return

        if content == "メッセージ制限bypass確認":
            if user_id != PRIMARY_ADMIN_ID:
                await message.channel.send(
                    f"{message.author.mention} ごめんね、この確認もメイン管理者だけができるの。"
                )
                return
            cfg = load_message_limit_config()
            lines = [
                "【メッセージ制限bypass設定】",
                f"- bypass機能全体: {'ON' if cfg.get('bypass_enabled', False) else 'OFF'}",
                f"- 他ユーザーへの付与許可: {'ON' if cfg.get('allow_bypass_grant', False) else 'OFF'}",
                "",
                "〈bypassを持っているユーザー〉",
            ]
            bypass_users = cfg.get("bypass_users", [])
            if not bypass_users:
                lines.append("- （まだ誰にも付与されていないみたい）")
            else:
                for uid in bypass_users:
                    try:
                        uid_int = int(uid)
                    except Exception:
                        uid_int = None
                    member = None
                    if message.guild and uid_int is not None:
                        member = message.guild.get_member(uid_int)
                    if member:
                        lines.append(f"- {member.display_name} (ID: {uid})")
                    else:
                        lines.append(f"- ID: {uid}")
            await message.channel.send("\n".join(lines))
            return

        if content == "メッセージ制限bypass全体オン":
            if user_id != PRIMARY_ADMIN_ID:
                await message.channel.send(
                    f"{message.author.mention} これはメイン管理者専用のスイッチなの。"
                )
                return
            cfg = load_message_limit_config()
            cfg["bypass_enabled"] = True
            save_message_limit_config(cfg)
            await message.channel.send(
                f"{message.author.mention} メッセージ制限bypass機能を **ON** にしたわ。"
            )
            return

        if content == "メッセージ制限bypass全体オフ":
            if user_id != PRIMARY_ADMIN_ID:
                await message.channel.send(
                    f"{message.author.mention} これはメイン管理者専用のスイッチなの。"
                )
                return
            cfg = load_message_limit_config()
            cfg["bypass_enabled"] = False
            save_message_limit_config(cfg)
            await message.channel.send(
                f"{message.author.mention} メッセージ制限bypass機能を **OFF** にしたわ。"
            )
            return

        if content == "メッセージ制限bypass付与許可オン":
            if user_id != PRIMARY_ADMIN_ID:
                await message.channel.send(
                    f"{message.author.mention} これを変えられるのはメイン管理者だけよ。"
                )
                return
            cfg = load_message_limit_config()
            cfg["allow_bypass_grant"] = True
            save_message_limit_config(cfg)
            await message.channel.send(
                f"{message.author.mention} 他の人にbypassを付与できるようにしたわ。"
            )
            return

        if content == "メッセージ制限bypass付与許可オフ":
            if user_id != PRIMARY_ADMIN_ID:
                await message.channel.send(
                    f"{message.author.mention} これを変えられるのはメイン管理者だけよ。"
                )
                return
            cfg = load_message_limit_config()
            cfg["allow_bypass_grant"] = False
            save_message_limit_config(cfg)
            await message.channel.send(
                f"{message.author.mention} これからは新しくbypassを配ることはできなくなるわ。"
            )
            return

        if content.startswith("メッセージ制限bypass付与"):
            if user_id != PRIMARY_ADMIN_ID:
                await message.channel.send(
                    f"{message.author.mention} ごめんね、bypassを配れるのはメイン管理者だけなの。"
                )
                return
            cfg = load_message_limit_config()
            if not cfg.get("bypass_enabled", False):
                await message.channel.send(
                    f"{message.author.mention} いまはbypass機能自体がOFFになっているみたい。\n"
                    "`メッセージ制限bypass全体オン` で有効化してから試してね。"
                )
                return
            if not cfg.get("allow_bypass_grant", False):
                await message.channel.send(
                    f"{message.author.mention} いまは「他の人にbypassを付与できない」設定になっているわ。\n"
                    "`メッセージ制限bypass付与許可オン` にしてからやってみて？"
                )
                return
            targets = [m for m in message.mentions if m.id != client.user.id]
            if not targets:
                await message.channel.send(
                    f"{message.author.mention} 誰にbypassを付与するか、`@ユーザー` を付けて教えて？\n"
                    "例: `メッセージ制限bypass付与 @ユーザー`"
                )
                return
            target = targets[0]
            cfg = load_message_limit_config()
            bypass_users = cfg.get("bypass_users", [])
            sid = str(target.id)
            if sid not in bypass_users:
                bypass_users.append(sid)
            cfg["bypass_users"] = bypass_users
            save_message_limit_config(cfg)
            await message.channel.send(
                f"{message.author.mention} {target.display_name} にメッセージ制限bypassを付与したわ。"
            )
            return

        if content.startswith("メッセージ制限bypass削除"):
            if user_id != PRIMARY_ADMIN_ID:
                await message.channel.send(
                    f"{message.author.mention} ごめんね、bypassの管理はメイン管理者だけなの。"
                )
                return
            targets = [m for m in message.mentions if m.id != client.user.id]
            if not targets:
                await message.channel.send(
                    f"{message.author.mention} 誰からbypassを外すか、`@ユーザー` を付けて教えて？\n"
                    "例: `メッセージ制限bypass削除 @ユーザー`"
                )
                return
            target = targets[0]
            cfg = load_message_limit_config()
            bypass_users = cfg.get("bypass_users", [])
            sid = str(target.id)
            if sid in bypass_users:
                bypass_users.remove(sid)
            cfg["bypass_users"] = bypass_users
            save_message_limit_config(cfg)
            await message.channel.send(
                f"{message.author.mention} {target.display_name} からメッセージ制限bypassを外したわ。"
            )
            return

        # 変身管理メニュー
        if "変身管理" in content:
            await message.channel.send(
                f"{message.author.mention} 変身の設定をどうする？\n"
                "- `変身一覧確認` … 誰がどの黄金裔（開拓者）を使っているか一覧表示\n"
                "- `変身編集一人 @ユーザー コードまたは名前` … その人のフォームを変更\n"
                "- `変身編集全体 コードまたは名前` … 全員のフォームを一括変更（メイン管理者のみ）\n"
                "- `データ管理終了` … モード終了\n"
                "※ コードは KaLos618, HapLotes405 などの変身コードよ。"
            )
            return

        # 変身一覧確認
        if content == "変身一覧確認":
            forms = get_all_forms()
            if not forms:
                await message.channel.send(
                    f"{message.author.mention} まだ誰も別の黄金裔には変身していないみたい。\n"
                    "みんな基本はキュレネのままね。"
                )
                return
            lines = ["【変身中の一覧】"]
            for uid_str, form_key in forms.items():
                try:
                    uid_int = int(uid_str)
                except Exception:
                    uid_int = None
                member = None
                if message.guild and uid_int is not None:
                    member = message.guild.get_member(uid_int)
                display_user = member.display_name if member else f"ID: {uid_str}"
                form_name = get_form_display_name(form_key)
                lines.append(f"- {display_user} → {form_name}")
            await message.channel.send("\n".join(lines))
            return

        # 変身編集一人
        if content.startswith("変身編集一人"):
            targets = [m for m in message.mentions if m.id != client.user.id]
            if not targets:
                await message.channel.send(
                    f"{message.author.mention} 誰を変身させるか、`@ユーザー` を付けて教えて？\n"
                    "例: `変身編集一人 @ユーザー KaLos618`"
                )
                return
            target = targets[0]
            tmp = content.replace("変身編集一人", "", 1)
            tmp = re.sub(rf"<@!?{target.id}>", "", tmp).strip()

            form_spec = tmp
            if not form_spec:
                form_key = "cyrene"
            else:
                form_key = resolve_form_spec(form_spec)

            if not form_key:
                await message.channel.send(
                    f"{message.author.mention} その黄金裔のコードや名前は知らないみたい…。\n"
                    "もう一度確認して教えてくれる？"
                )
                return

            set_user_form(target.id, form_key)
            form_name = get_form_display_name(form_key)
            await message.channel.send(
                f"{message.author.mention} {target.display_name} を **{form_name}** に変身させておいたわ♪"
            )
            return

        # 変身編集全体（メイン管理者限定）
        if content.startswith("変身編集全体"):
            if user_id != PRIMARY_ADMIN_ID:
                await message.channel.send(
                    f"{message.author.mention} ごめんね、全体の変身を変える権限はメイン管理者だけなの。"
                )
                return
            tmp = content.replace("変身編集全体", "", 1).strip()
            form_spec = tmp
            if not form_spec:
                form_key = "cyrene"
            else:
                form_key = resolve_form_spec(form_spec)

            if not form_key:
                await message.channel.send(
                    f"{message.author.mention} その黄金裔のコードや名前は知らないみたい…。\n"
                    "もう一度確認して教えてくれる？"
                )
                return

            set_all_forms(form_key)
            form_name = get_form_display_name(form_key)
            await message.channel.send(
                f"{message.author.mention} 登録されているみんなのフォームを、全部 **{form_name}** に揃えておいたわ♪"
            )
            return

        # 管理者編集メニュー（既存）
        if "管理者編集" in content:
            await message.channel.send(
                f"{message.author.mention} 管理者をどうしたい？\n"
                "- `管理者追加`\n"
                "- `管理者削除`\n"
                "- `データ管理終了`"
            )
            return

        if "管理者追加" in content:
            waiting_for_admin_add.add(user_id)
            await message.channel.send(
                f"{message.author.mention} 誰を管理者として追加する？ `@ユーザー` で教えてね。"
            )
            return

        if "管理者削除" in content:
            waiting_for_admin_remove.add(user_id)
            await message.channel.send(
                f"{message.author.mention} 誰を管理者から外す？ `@ユーザー` で教えてね。"
            )
            return

        # 不明コマンド
        await message.channel.send(
            f"{message.author.mention} ごめんね、そのコマンドはまだ知らないの…。\n"
            "いま使えるのは\n"
            "- `ニックネーム確認`\n"
            "- `管理者編集`\n"
            "- `親衛隊レベル編集`\n"
            "- `好感度編集`\n"
            "- `メッセージ制限編集`\n"
            "- `メッセージ制限bypass編集`（メイン管理者専用）\n"
            "- `変身管理`\n"
            "- `データ管理終了`\n"
            "あたりね。"
        )
        return

    # ===== データ管理モードへ入る =====
    if content == "データ管理":
        if not is_admin(user_id):
            await message.channel.send(
                f"{message.author.mention} ごめんね、このモードは管理者専用なの。"
            )
            return
        admin_data_mode.add(user_id)
        await message.channel.send(
            f"{message.author.mention} データ管理モードに入ったわ。\n"
            "何を確認したい？\n"
            "- `ニックネーム確認`\n"
            "- `管理者編集`\n"
            "- `親衛隊レベル編集`\n"
            "- `好感度編集`\n"
            "- `メッセージ制限編集`\n"
            "- `メッセージ制限bypass編集`（メイン管理者専用）\n"
            "- `変身管理`\n"
            "- `データ管理終了`"
        )
        return

    # ===== 一般：親衛隊レベル確認 =====
    if content in ["親衛隊レベル", "親衛隊レベル確認"]:
        level_val = get_guardian_level(user_id)
        if level_val is None:
            await message.channel.send(
                f"{message.author.mention} まだ親衛隊レベルは登録されていないみたい。\n"
                "そのうち誰かがレベルを付けてくれるかもね？"
            )
        else:
            await message.channel.send(
                f"{message.author.mention} あなたの親衛隊レベルは **Lv.{level_val}** よ♪"
            )
        return

    # ===== 一般：好感度確認 =====
    if content in ["好感度", "好感度チェック", "キュレネ好感度"]:
        xp, level_val = get_user_affection(user_id)
        cfg = load_affection_config()
        thresholds = cfg.get("level_thresholds", [0])
        if level_val + 1 < len(thresholds):
            next_xp = thresholds[level_val + 1]
            remain = max(0, next_xp - xp)
            msg_text = (
                f"あなたの好感度は **Lv.{level_val}** で、累計 **{xp} XP** ね♪\n"
                f"次のLv.{level_val + 1} までは、あと **{remain} XP** 必要よ。"
            )
        else:
            msg_text = (
                f"あなたの好感度は **Lv.{level_val}**（累計 {xp} XP）よ♪\n"
                "これ以上は数えなくてもいいくらい、十分仲良しってことかしら？"
            )
        await message.channel.send(f"{message.author.mention} {msg_text}")
        return

    # ===== 一般：自分の変身状態確認 =====
    if content in ["変身状態", "今の姿", "今のフォーム"]:
        await message.channel.send(
            f"{message.author.mention} 今のあたしは **{current_form_name}** としてあなたと話してるわ♪"
        )
        return

    # ===== 一般：変身開始 =====
    if content == "変身":
        waiting_for_transform_code.add(user_id)
        await message.channel.send(
            f"{message.author.mention} ふふっ、変身したいのね？\n"
            "アグライアなら `KaLos618`、トリスビアスなら `HapLotes405` みたいに、変身コードを教えて？"
        )
        return

    # ===== 特別トリガー：開拓者フォーム =====
    # =====================
    # 変身コマンド：三月なのか / 長夜月
    # =====================
    if "なのになってみて" in content:
        if not is_nanoka_unlocked(user_id):
            await message.channel.send(
                f"{message.author.mention} ごめんね、その姿になるにはまだ条件が足りないみたい…。\n"
                "まずは、あたしとのじゃんけんに何度も勝ってみて？ それからもう一度お願いしてくれる？"
            )
            return

        set_user_form(user_id, "nanoka")
        await message.channel.send(
            f"{message.author.mention} 今日から、あたしは「三月なのか / 長夜月」の姿でもあなたと一緒にいられるわ♪"
        )
        return


    # =====================
    # 変身コマンド：丹恒
    # =====================
    if "たんたんになってみて" in content:
        if not is_danheng_unlocked(user_id):
            await message.channel.send(
                f"{message.author.mention} その姿になるには、まだ鍵が足りないみたい…。\n"
                "あの荒笛のことを、もっとよく知ってみて？ きっと道が開けるわ。"
            )
            return

        set_user_form(user_id, "danheng")
        await message.channel.send(
            f"{message.author.mention} …わかった。今日は彼の姿で、あなたと共に歩こう。\n"
            "無茶だけはしないでね。あなたを守る役目は、ちゃんと果たしたいから。"
        )
        return

    # ===== あだ名系 =====
    if content.startswith("あだ名登録"):
        new_name = content.replace("あだ名登録", "", 1).strip()
        if not new_name:
            waiting_for_nickname.add(user_id)
            await message.channel.send(
                f"{message.author.mention} あたし、どう呼べばいいの？"
            )
            return
        set_nickname(user_id, new_name)
        await message.channel.send(
            f"{message.author.mention} ふふ…これからは「{new_name}」って呼ぶわね♪"
        )
        return

    if content.startswith("あだ名変更"):
        new_name = content.replace("あだ名変更", "", 1).strip()
        if not new_name:
            waiting_for_rename.add(user_id)
            await message.channel.send(
                f"{message.author.mention} 新しい呼び名、教えて？"
            )
            return
        set_nickname(user_id, new_name)
        await message.channel.send(
            f"{message.author.mention} 了解♪ 今日から「{new_name}」よ。"
        )
        return

    if content.startswith("あだ名削除"):
        delete_nickname(user_id)
        waiting_for_nickname.discard(user_id)
        waiting_for_rename.discard(user_id)
        await message.channel.send(
            f"{message.author.mention} わかったわ。元の呼び方に戻すわね。"
        )
        return

    # ===== じゃんけん開始 =====
    if "じゃんけん" in content:
        # 一発指定（例: じゃんけん グー）
        hand = parse_hand(content)
        if hand:
            bot_hand = random.choice(JANKEN_HANDS)
            result = judge_janken(hand, bot_hand)
            flavor = get_rps_line(result)

            # ★ 勝利カウント
            if result == "win":
                wins = inc_janken_win(user_id)
            else:
                wins = get_janken_wins(user_id)

            await message.channel.send(
                f"{message.author.mention} {name} は **{hand}**、あたしは **{bot_hand}** よ。\n"
                f"{flavor}\n"
                f"（これまでに {wins} 回、あたしに勝ってるわ♡）"
            )

            cfg = load_affection_config()
            xp_actions = cfg.get("xp_actions", {})
            if result == "win":
                delta = int(xp_actions.get("rps_win", 0))
            elif result == "lose":
                delta = int(xp_actions.get("rps_lose", 0))
            else:
                delta = int(xp_actions.get("rps_draw", 0))
            add_affection_xp(user_id, delta, reason=f"rps_{result}")
            return

        waiting_for_rps_choice.add(user_id)
        await message.channel.send(
            f"{message.author.mention} じゃんけんをしましょう♪ グー / チョキ / パー、どれにするかしら？"
        )
        return

    # ===== メンションだけのとき =====
    if content == "":
        xp, level_val = get_user_affection(user_id)
        reply = generate_reply_for_form(current_form, "", level_val)
        await message.channel.send(f"{message.author.mention} {reply}")
        cfg = load_affection_config()
        delta = int(cfg.get("xp_actions", {}).get("talk", 0))
        add_affection_xp(user_id, delta, reason="talk")
        return

    # =====================
    # 特殊解放トリガー：三月なのか
    # じゃんけん勝利数 5回以上 ＋ 「記憶は流れ星を待ってる」
    # =====================
    if "記憶は流れ星を待ってる" in content or "記憶は流れ星を待っている" in content:
        base_reply = get_cyrene_reply(content)

        unlocked_now = False
        wins = get_janken_wins(user_id)
        if wins >= 5 and not is_nanoka_unlocked(user_id):
            set_nanoka_unlocked(user_id, True)
            unlocked_now = True

        extra = ""
        if unlocked_now:
            extra = (
                "\n\n三月なのかの解放条件を達成したわ！\n"
                "『なのになってみて』って言ってみない？"
            )

        await message.channel.send(
            f"{message.author.mention} {name}、{base_reply}{extra}"
        )
        return
    
        # =====================
    # 特殊解放トリガー：丹恒
    # ステップ1達成 + コード SkoPeo365
    # =====================
    if "SkoPeo365" in content:
        if has_danheng_stage1(user_id) and not is_danheng_unlocked(user_id):
            set_danheng_unlocked(user_id, True)
            await message.channel.send(
                f"{message.author.mention} 丹恒の解放条件を達成したわ！\n"
                "『たんたんになってみて』って言ってみない？"
            )
        elif is_danheng_unlocked(user_id):
            await message.channel.send(
                f"{message.author.mention} そのコードはもう使われているわ。\n"
                "いつでも『たんたんになってみて』って言えば、彼の姿になれるわよ♪"
            )
        else:
            await message.channel.send(
                f"{message.author.mention} ん…まだ何かが足りないみたい。\n"
                "まずは『みんなについて教えて』ってお願いして、彼のことをちゃんと知ってみない？"
            )
        return


    # ===== 通常応答 =====
    xp, level_val = get_user_affection(user_id)

    # 変身状態に応じた返事を生成（キュレネ・黄金裔・開拓者）
    reply = generate_reply_for_form(current_form, content, level_val)

    # ★ 丹恒解放ステップ1チェック
    # キュレネとして話していて、なおかつ荒笛トリガー台詞を引き当てたときだけフラグON
    if current_form == "cyrene" and ARAFUE_TRIGGER_LINE in reply:
        mark_danheng_stage1(user_id)

    await message.channel.send(f"{message.author.mention} {name}、{reply}")

    # 好感度XP加算（会話）
    cfg = load_affection_config()
    delta = int(cfg.get("xp_actions", {}).get("talk", 0))
    add_affection_xp(user_id, delta, reason="talk")


# 実行
client.run(DISCORD_TOKEN)
