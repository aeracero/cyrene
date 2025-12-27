# cyrene.py
from email.mime import message
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
from lines_furina import get_reply as get_furina_reply
from lines_momo import get_reply as get_momo_reply

from special_unlocks import (
    inc_janken_win,
    get_janken_wins,
    is_nanoka_unlocked,
    set_all_myurion_enabled,
    set_nanoka_unlocked,
    has_danheng_stage1,
    mark_danheng_stage1,
    is_danheng_unlocked,
    set_danheng_unlocked,
)

from lines_cerydra import (
    get_reply as get_cerydra_reply,
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
SPECIAL_UNLOCKS_FILE = DATA_DIR / "special_unlocks.json"

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

MYURION_SYLLABLES = ["ミュ", "ミュウ", "ミュミュ", "ミュイー"]


def to_myurion_text(body: str) -> str:
    """
    日本語テキストをミュウリオン語に変換。
    改行・句読点は残して、それ以外の文字をミュ～に変える。
    """
    result = []
    for ch in body:
        # 改行はそのまま
        if ch in "\r\n":
            result.append(ch)
            continue
        # スペースはそのまま
        if ch.isspace():
            result.append(ch)
            continue
        # 記号系はそのまま
        if ch in "。、！？…,.!?「」『』()（）[]【】:：;；/｜|\\-—ー♪☆★":
            result.append(ch)
            continue
        # それ以外はミュ化
        result.append(random.choice(MYURION_SYLLABLES))
    return "".join(result)


def apply_myurion_filter(user_id: int, text: str) -> str:
    """
    先頭のメンション部分は残して、その後ろだけミュウリオン語にする。
    ミュリオンモードがOFFのときは text をそのまま返す。
    """
    if not is_myurion_enabled(user_id):
        return text

    m = re.match(r"^(<@!?\d+>)(.*)$", text, flags=re.DOTALL)
    if not m:
        return to_myurion_text(text)

    mention = m.group(1)
    body = m.group(2)
    return mention + to_myurion_text(body)


async def send_myu(message: discord.Message, user_id: int, text: str):
    """
    返信用ヘルパー。
    ミュリオンモード中なら本文をミュ語化して送信する。
    OFFなら、そのまま普通の日本語で送られる。
    """
    text = apply_myurion_filter(user_id, text)
    await message.channel.send(text)


def get_user_affection(user_id: int):
    """(xp, level) を返す"""
    cfg = load_affection_config()
    data = load_affection_data()
    info = data.get(str(user_id), {})
    xp = int(info.get("xp", 0))
    level = get_level_from_xp(xp, cfg)
    return xp, level


def get_cyrene_affection_multiplier(user_id: int) -> float:
    """
    ガチャで引いたキュレネの枚数に応じて好感度倍率を返す。
    1体ごとに +0.2倍、最大 2.4倍。
    （0枚 → 1.0, 1枚 → 1.2, ..., 7枚(=6凸) 以上 → 2.4）
    """
    try:
        state = get_gacha_state(user_id)
    except Exception:
        return 1.0

    copies = int(state.get("cyrene_copies", 0))
    mult = 1.0 + 0.2 * copies
    if mult > 2.4:
        mult = 2.4
    return mult

import math  # ファイルの先頭 import 群にこれが無ければ追加してOK


def calc_main_5star_rate(pity_5: int) -> float:
    """
    メイン星5（キュレネ or すり抜け）確率。
    基本 0.06% (=0.0006)、75連付近から徐々に上昇、90連目で確定。
    pity_5 は「最後にメイン星5を引いてからの回数」。
    """
    base = 0.0006  # 0.06%
    # 0〜73: 固定
    if pity_5 <= 73:
        return base
    # 74〜88: 緩やかに上昇
    if pity_5 < 89:
        # 74 〜 88 の 15ステップで base → 1.0 に近づける
        step = pity_5 - 73  # 1〜15
        max_step = 15
        return min(1.0, base + (1.0 - base) * (step / max_step))
    # 89 以上（=90連目以降）は確定
    return 1.0


def format_gacha_rates() -> str:
    """ガチャ排出確率説明用テキスト"""
    lines = [
        "【ガチャ排出率（概略）】",
        "・メイン星5（キュレネ or すり抜け）: 基本 0.06%（75連付近から徐々に確率上昇、90連で確定）",
        "・星4: 基本 24%（10連ごとに少なくとも1回は星4以上が確定）",
        "・星3: その他",
        "",
        "・特別枠 星5『失われた紡がれた物語のページその１（??? その1）』: 常時 0.06%（天井なし・メイン星5の天井には影響しない）",
        "",
        "【キュレネのピックアップ】",
        "・メイン星5取得時、50%でキュレネ、50%ですり抜け。",
        "・一度すり抜けたあとは、次のメイン星5がキュレネ確定（確定天井）。",
        "",
        "【キュレネの凸と好感度】",
        "・ガチャでキュレネを1体引くごとに、好感度取得XP倍率が +0.2倍。",
        "・倍率は最大 2.4倍まで上昇するわ♪",
    ]
    return "\n".join(lines)


def format_gacha_status(user_id: int) -> str:
    """ガチャメニュー表示用のステータス文字列"""
    state = get_gacha_state(user_id)
    stones = int(state.get("stones", 0))
    pity_5 = int(state.get("pity_5", 0))
    pity_4 = int(state.get("pity_4", 0))
    guaranteed = bool(state.get("guaranteed_cyrene", False))
    cyrene_copies = int(state.get("cyrene_copies", 0))
    page1_count = int(state.get("page1_count", 0))
    offbanner_tickets = int(state.get("offbanner_tickets", 0))
    mult = get_cyrene_affection_multiplier(user_id)

    lines = [
        "【キュレネガチャメニュー】",
        f"・現在の所持石: {stones} 個",
        f"・キュレネの所持枚数: {cyrene_copies} 枚（好感度倍率: x{mult:.1f}）",
        f"・失われた紡がれた物語のページその１(??? その1): {page1_count} 枚",
        f"・すり抜け10連交換チケット: {offbanner_tickets} 枚",
        "",
        f"・メイン星5天井カウント: {pity_5} 連",
        f"・星4天井カウント: {pity_4} 連",
        f"・次のメイン星5: {'キュレネ確定' if guaranteed else '50%でキュレネ'}",
        "",
        "【操作方法】",
        "・`単発ガチャ` … 石160個で1回",
        "・`１０連ガチャ` または `10連ガチャ` … 石1600個で10回",
        "・`チケット１０連` … すり抜けチケット1枚で10連（石消費なし）",
        "・`ガチャ説明` … 排出率や仕様の詳細を見る",
    ]
    return "\n".join(lines)


def perform_gacha_pulls(user_id: int, num_pulls: int, use_ticket: bool = False) -> tuple[bool, str]:
    """
    実際にガチャを num_pulls 回まわす。
    use_ticket=True のときは石を消費せず、すり抜けチケットを1枚消費する10連専用。
    戻り値: (成功したか, メッセージ文字列)
    """
    if num_pulls <= 0:
        return False, "ガチャ回数が変みたい…もう一度お願いして？"

    state = get_gacha_state(user_id)

    # コストチェック
    if use_ticket:
        if num_pulls != 10:
            return False, "チケットは10連専用みたい。"
        tickets = int(state.get("offbanner_tickets", 0))
        if tickets <= 0:
            return False, "すり抜け交換チケットが足りないみたい…。"
        state["offbanner_tickets"] = tickets - 1
        cost_str = "（すり抜けチケット1枚消費）"
    else:
        cost = 160 * num_pulls if num_pulls == 1 else 1600
        stones = int(state.get("stones", 0))
        if stones < cost:
            return False, f"石が足りないみたい…。必要: {cost}個 / 所持: {stones}個"
        state["stones"] = stones - cost
        cost_str = f"（石 {cost} 個消費）"

    pity_5 = int(state.get("pity_5", 0))
    pity_4 = int(state.get("pity_4", 0))
    guaranteed = bool(state.get("guaranteed_cyrene", False))

    results = []
    page_hits = 0
    cyrene_hit = 0
    offbanner_hit = 0

    for i in range(num_pulls):
        # 特別枠：ページその１（天井非対象・確率固定 0.06%）
        page_got = False
        if random.random() < 0.0006:  # 0.06%
            state["page1_count"] = int(state.get("page1_count", 0)) + 1
            page_hits += 1
            page_got = True

        # メイン星5 抽選
        main5_rate = calc_main_5star_rate(pity_5)
        got_main5 = random.random() < main5_rate

        if got_main5:
            pity_5 = 0
            pity_4 = 0

            # キュレネ or すり抜け判定
            if guaranteed or (random.random() < 0.5):
                # キュレネ
                state["cyrene_copies"] = int(state.get("cyrene_copies", 0)) + 1
                guaranteed = False
                cyrene_hit += 1
                pull_text = "★5【キュレネ】"
            else:
                # すり抜け → チケット付与
                state["offbanner_tickets"] = int(state.get("offbanner_tickets", 0)) + 1
                guaranteed = True
                offbanner_hit += 1
                pull_text = "★5【すり抜け（10連チケット獲得）】"

            if page_got:
                pull_text += " ＋ ★5【??? その1】（失われた紡がれた物語のページその１）"
        else:
            # 星5を引けなかった場合 → 星4 or 星3
            pity_5 += 1
            # 星4判定（10連天井）
            got_4 = False
            if pity_4 >= 9:
                got_4 = True
            else:
                if random.random() < 0.24:  # 24%
                    got_4 = True

            if got_4:
                pity_4 = 0
                pull_text = "★4"
            else:
                pity_4 += 1
                pull_text = "★3"

            if page_got:
                # メイン結果は★3/★4のまま、ページは「おまけ」として表示
                pull_text += " ＋ ★5【??? その1】（失われた紡がれた物語のページその１）"

        results.append(pull_text)

    # 状態を保存
    state["pity_5"] = pity_5
    state["pity_4"] = pity_4
    state["guaranteed_cyrene"] = guaranteed
    save_gacha_state(user_id, state)

    # メッセージ整形
    header = f"{cost_str}\n今回の結果は……\n"
    body_lines = []
    for idx, r in enumerate(results, start=1):
        body_lines.append(f"{idx}回目: {r}")

    summary = []
    if cyrene_hit:
        summary.append(f"★5キュレネ: {cyrene_hit} 枚")
    if offbanner_hit:
        summary.append(f"★5すり抜け: {offbanner_hit} 回（チケット {offbanner_hit} 枚獲得）")
    if page_hits:
        summary.append(f"★5ページ(??? その1): {page_hits} 枚")

    if not summary:
        summary_text = "今回は★5は来なかったみたい…。でも、次はもっといい結果になるかもね？"
    else:
        summary_text = " / ".join(summary)

    footer = (
        "\n\n" + summary_text +
        f"\n\n現在の石: {state['stones']} 個 / すり抜けチケット: {state['offbanner_tickets']} 枚"
    )

    return True, header + "\n".join(body_lines) + footer


def add_affection_xp(user_id: int, delta: int, reason: str = ""):
    """好感度XPを加算（マイナスもOK・0以下は0にクリップ）
    キュレネ凸数に応じて、プラスのXPのみ倍率補正をかける。
    """
    if delta == 0:
        return

    # ★ キュレネ凸による好感度倍率
    if delta > 0:
        mult = get_cyrene_affection_multiplier(user_id)
        if mult != 1.0:
            delta = int(delta * mult)
            if delta < 1:
                delta = 1

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
# ガチャ用データ保存（永続: /data/gacha.json）
# =====================
GACHA_FILE = DATA_DIR / "gacha.json"


def load_gacha_data() -> dict:
    """ガチャ全体データを読み込み {user_id(str): state(dict)}"""
    if not GACHA_FILE.exists():
        return {}
    try:
        data = json.loads(GACHA_FILE.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return {}
        return data
    except Exception:
        return {}


def save_gacha_data(data: dict):
    """ガチャ全体データを保存"""
    GACHA_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


def get_gacha_state(user_id: int) -> dict:
    """
    ユーザーごとのガチャ状態を取得/初期化
    {
    "stones": int,
    "pity_5": int,              # メイン星5の天井カウント
    "pity_4": int,              # 星4天井カウント
    "guaranteed_cyrene": bool,  # すり抜け後のキュレネ確定フラグ
    "cyrene_copies": int,       # ガチャから引いたキュレネの枚数
    "page1_count": int,         # 失われたページその1 の枚数
    "offbanner_tickets": int,   # すり抜け10連交換チケット枚数
    "last_daily": str | None,   # "YYYY-MM-DD"
    }
    """
    data = load_gacha_data()
    state = data.get(str(user_id))
    if not isinstance(state, dict):
        state = {
            "stones": 0,
            "pity_5": 0,
            "pity_4": 0,
            "guaranteed_cyrene": False,
            "cyrene_copies": 0,
            "page1_count": 0,
            "offbanner_tickets": 0,
            "last_daily": None,
        }
        data[str(user_id)] = state
        save_gacha_data(data)
    return state


def grant_daily_stones(user_id: int, amount: int = 16000) -> tuple[bool, int, str]:
    """
    デイリー石を付与。
    戻り値: (付与できたか, 現在の石, メッセージ用理由)
    """
    state = get_gacha_state(user_id)
    today = today_str()
    last = state.get("last_daily")

    if last == today:
        # すでに受け取り済み
        return False, state.get("stones", 0), "今日はもうデイリーを受け取っているみたい。"

    state["stones"] = int(state.get("stones", 0)) + amount
    state["last_daily"] = today
    save_gacha_state(user_id, state)
    return True, state["stones"], f"今日のデイリー報酬として {amount} 個の石を用意しておいたわ♪"


def save_gacha_state(user_id: int, state: dict):
    data = load_gacha_data()
    data[str(user_id)] = state
    save_gacha_data(data)

# =====================
# ミュリオンモード保存（永続: /data/myurion_mode.json）
# =====================
MYURION_FILE = DATA_DIR / "myurion_mode.json"


def load_myurion_data() -> dict:
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
    MYURION_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


def get_myurion_state(user_id: int) -> dict:
    """
    {
    "unlocked": bool,      # ミュリオンモード解放済みか
    "enabled": bool,       # 現在ミュリオンモード中か
    "quiz_correct": int,   # 累計正解数（開放前）
    }
    """
    data = load_myurion_data()
    st = data.get(str(user_id))
    if not isinstance(st, dict):
        st = {
            "unlocked": False,
            "enabled": False,
            "quiz_correct": 0,
        }
        data[str(user_id)] = st
        save_myurion_data(data)
    return st

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
        # まだキーが無い場合も一応補完
        st.setdefault("unlocked", False)

        st["enabled"] = bool(enabled)
        # 全体ONのときは、まだ未解放でも強制的に解放扱いにしてあげる
        if enabled and not st["unlocked"]:
            st["unlocked"] = True

        data[uid] = st

    save_myurion_data(data)


def save_myurion_state(user_id: int, st: dict):
    data = load_myurion_data()
    data[str(user_id)] = st
    save_myurion_data(data)


def is_myurion_unlocked(user_id: int) -> bool:
    st = get_myurion_state(user_id)
    return bool(st.get("unlocked", False))


def is_myurion_enabled(user_id: int) -> bool:
    st = get_myurion_state(user_id)
    return bool(st.get("enabled", False))


def set_myurion_enabled(user_id: int, enabled: bool):
    st = get_myurion_state(user_id)
    st["enabled"] = bool(enabled)
    if enabled and not st.get("unlocked", False):
        st["unlocked"] = True
    save_myurion_state(user_id, st)


def add_myurion_correct(user_id: int) -> int:
    """クイズ正解数を+1して返す（開放後はカウントだけ増える感じ）"""
    st = get_myurion_state(user_id)
    st["quiz_correct"] = int(st.get("quiz_correct", 0)) + 1
    save_myurion_state(user_id, st)
    return st["quiz_correct"]

# =====================
# ミュリオンクイズ状態
# =====================
# { user_id: { "question": dict, "options": list[str], "correct_index": int } }
MYURION_QUIZ_STATE = {}

MYURION_QUESTIONS = [
    {
        "q": "ミュミュ、ミミュミュミュミュウミュミュウミー",
        "choices": [
            "ミュウミーミミュミミュミュ",
            "ミミュミュウミーミーミュウミュウミミ",
            "ミュウミみミュみミミュミュミュミュウ",
            "ミュウミュミュミュミュウ",
        ],
        "answer_index": 0,
    },
    {
        "q": "ミュウミュミュミュウミュミュミュウウミュウ？",
        "choices": [
            "ミュウミミミュミュミュミュウミ",
            "ミュウーミミュミュミュウミュウ",
            "ミュウミュウミュミュミュミュミュ",
            "ミミミュミュミュムミュウミミミュ",
        ],
        "answer_index": 1,
    },
    {
        "q": "ミュミュミミュウミュユミミュミュウ？",
        "choices": [
            "ミュウミュミュミュミュ、ミーミュユミュミュウ",
            "ミミュミュミーミーミュ。ミュミュミーミュミュ",
            "ミュウミュミュミュウ。ミュウミーみミュミュウ",
            "ミュウ。",
        ],
        "answer_index": 0,
    },
    {
        "q": "ミュミュミュミュミューーミュウミュウミュウミュウミュウ？",
        "choices": [
            "ミュウミュユミュミュミューミュウミュウミュウミュウ",
            "ミュウ。ミミュミュミュミーミミュミュミュミュミュウ",
            "ミミミュミュミュミュウ",
            "ミュウミュミュミュミュミュミュミュミュミュミュ",
        ],
        "answer_index": 1,
    },
    {
        "q": "ミュミュミュミュウミュウミュウミュウミュウミュウミュウミュウ？",
        "choices": [
            "ミュウ!",
            "ミュウ?",
            "ミュウ。",
            "ミュウ♪",
        ],
        "answer_index": 0,
    },
]


def parse_myurion_answer(text: str) -> int | None:
    """
    ユーザーの返答から 1〜4 のどれを選んだかを判定。
    """
    # 全角半角両対応
    if any(ch in text for ch in ["1", "１"]):
        return 1
    if any(ch in text for ch in ["2", "２"]):
        return 2
    if any(ch in text for ch in ["3", "３"]):
        return 3
    if any(ch in text for ch in ["4", "４"]):
        return 4
    return None


async def send_myurion_question(message: discord.Message, user_id: int, correct_count: int):
    """
    新しいミュリオンクイズを1問出題。
    """
    q = random.choice(MYURION_QUESTIONS)
    # 選択肢をシャッフル
    indexed = list(enumerate(q["choices"]))
    random.shuffle(indexed)

    # シャッフル後の正解の位置を特定
    correct_original_idx = q["answer_index"]
    correct_index = None
    for new_idx, (orig_idx, _) in enumerate(indexed):
        if orig_idx == correct_original_idx:
            correct_index = new_idx
            break

    # 1〜4 の表示用に変換
    options_text_lines = []
    for i, (_, choice_text) in enumerate(indexed, start=1):
        options_text_lines.append(f"{i}. {choice_text}")

    body = (
        f"ミュミュミュ…（現在 {correct_count} / 3 問正解ミュ）\n"
        f"{q['q']}\n"
        "ミュミュ…好きな番号を選んでミュ（1〜4のどれかを送ってミュ）\n\n"
        + "\n".join(options_text_lines)
    )

    MYURION_QUIZ_STATE[user_id] = {
        "question": q,
        "options": [c for _, c in indexed],
        "correct_index": correct_index,  # 0〜3
    }

    await send_myu(
        message,
        user_id,
        f"{message.author.mention} {body}"
    )


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

# ★ メイン管理者用：次のじゃんけんを確定勝利にするフラグ
FORCE_RPS_WIN_NEXT = set()  # user_id を一時的に入れておく


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

def get_rps_prompt_for_form(form_key: str, name: str) -> str:
    """
    フォームごとの「じゃんけんしよ〜」の誘い文句。
    必要に応じて他キャラもここに追加してOK。
    """
    # ヒアシンシア
    if form_key == "hyacinthia":
        return "いいですよ〜。では、グー / チョキ / パー、どれにするか選んでください。"

    # ケリュドラ
    if form_key == "cerydra":
        base_lines = [
            "じゃんけんか。{nickname}卿も童心に帰ることがあるのだな。良いだろう、一局付き合おう。",
            "暇つぶしには悪くないな。{nickname}卿、グー / チョキ / パー、好きな手を選ぶといい。",
        ]
        # {nickname} → 実際の呼び名(name) に置き換え
        import random
        return random.choice(base_lines).replace("{nickname}", name)

    # ここに他キャラ用を足していけばOK
    # if form_key == "aglaia":
    #     return "さ、じゃんけんといきましょうか。グー / チョキ / パー、どれを出します？"

    # デフォルト（キュレネ口調）
    return "じゃんけんをしましょう♪ グー / チョキ / パー、どれにするかしら？"



def get_rps_flavor_for_form(form_key: str, result: str, name: str) -> str:
    """
    勝ち / 負け / あいこ のリアクションをフォーム別に出し分ける。
    未定義のフォームは従来通り get_rps_line(result) を使う。
    """
    if form_key == "hyacinthia":
        if result == "win":
            return "ふふ、お見事です〜。あなたの勝ちですね。もう一回、いきますか？"
        elif result == "lose":
            return "あら、今回はわたしの勝ちみたいですね〜。でも次はどうなるでしょう？"
        else:  # draw
            return "おや、あいこですね〜。もう一度、やってみましょうか。"

    if form_key == "cerydra":
        # ケリュドラ用じゃんけんセリフ（{nickname}→name に差し替え）
        if result == "win":
            candidates = [
                f"どうやら勝利の女神は今回限りは僕に微笑まなかったようだな。だが次こそは勝ってみせるぞ。",
                f"中々運が良いではないか{name}卿。今なら駿足卿との賭けにも勝てるのではないか？",
                f"…運だけというのも面白くないだろう？どうだ{name}卿、チェスに興味は？",
            ]
        elif result == "lose":
            candidates = [
                f"どうした{name}卿？まさか僕が運命卿の力を借りたとでも思っているのか？",
                "やはり勝利の女神は僕に微笑んでいるようだ。過去も今も、未来さえも変わらずな。",
                f"どうだ{name}卿。金織卿ですら、この僕には一回も勝てなかったんだぞ？",
            ]
        else:  # draw
            candidates = [
                "ほう…白と黒だけでは面白くないが、決着がつかないというのももどかしいものだ。",
                f"僕と同じ考えを持つとは賢いではないか{name}卿。",
                "勝敗がつかないか…なら次の戦いに備えるまでだ。",
            ]
        return random.choice(candidates)

    # デフォルト（キュレネのじゃんけん用セリフ）
    return get_rps_line(result)





def format_rps_result_message(
    form_key: str,
    name: str,
    user_hand: str,
    bot_hand: str,
    flavor: str,
    wins: int,
) -> str:
    # デフォルトはキュレネ
    self_pronoun = "あたし"
    tail = "わ♡"  # 語尾

    if form_key == "hyacinthia":
        self_pronoun = "わたし"
        tail = "よ♪"

    if form_key == "cerydra":
        self_pronoun = "僕"
        tail = "だな。"

    return (
        f"{name} は **{user_hand}**、{self_pronoun}は **{bot_hand}** だ。\n"
        f"{flavor}\n"
        f"（これまでに {wins} 回、{self_pronoun}に勝っている{tail}）"
    )




def get_bot_hand_against(user_hand: str, force_win: bool = False) -> str:
    """
    force_win = True のときは、必ずユーザーが勝つ手を返す。
    それ以外はランダム。
    """
    if not force_win:
        return random.choice(JANKEN_HANDS)

    # ユーザーに勝たせる（bot は負けの手を出す）
    if user_hand == "グー":
        return "チョキ"
    if user_hand == "チョキ":
        return "パー"
    if user_hand == "パー":
        return "グー"
    # 万が一よく分からない値が来たらランダム
    return random.choice(JANKEN_HANDS)


def judge_janken(user_hand: str, bot_hand: str) -> str:
    if user_hand == bot_hand:
        return "draw"
    win = (
        (user_hand == "グー" and bot_hand == "チョキ") or
        (user_hand == "チョキ" and bot_hand == "パー") or
        (user_hand == "パー" and bot_hand == "グー")
    )
    return "win" if win else "lose"


async def handle_danheng_special_code(message: discord.Message, user_id: int, content: str):
    """
    丹恒の特殊解放コード（SkoPeo365 / skepeo365 系）を処理するハンドラ。
    - 荒笛ステップ1達成済みなら、丹恒を解放してメッセージ
    - 既に解放済みなら、その旨を案内
    - 未達成なら、「みんなについて教えて」を促す
    - 変身コード入力待ち状態だった場合は一旦解除
    """
    # 変身コード入力待ちだったら解除
    waiting_for_transform_code.discard(user_id)

    # まだ special_unlocks のステップ1を踏んでいないかどうか判定
    if has_danheng_stage1(user_id) and not is_danheng_unlocked(user_id):
        # ★ ここで special_unlocks.py 経由で解放状態を書き込み（/data 側にも保存）
        set_danheng_unlocked(user_id, True)
        await send_myu(
            message,
            user_id,
            f"{message.author.mention} 丹恒の解放条件を達成したわ！\n"
            "『たんたんになってみて』って言ってみない？"
        )
        return

    if is_danheng_unlocked(user_id):
        # すでに解放済み
        await send_myu(
            message,
            user_id,
            f"{message.author.mention} そのコードはもう使われているわ。\n"
            "いつでも『たんたんになってみて』って言えば、彼の姿になれるわよ♪"
        )
        return

    # まだステップ1を踏んでいない場合
    await send_myu(
        message,
        user_id,
        f"{message.author.mention} ん…まだ何かが足りないみたい。\n"
        "まずは『みんなについて教えて』ってお願いして、彼のことをちゃんと知ってみない？"
    )


def generate_reply_for_form(
    form_key: str,
    message_text: str,
    affection_level: int,
    user_id: int,
    name: str,
) -> str:
    """
    変身状態（黄金裔/開拓者）に応じて返答を切り替える。
    - 各フォームは lines_◯◯.py の get_reply を使う
    - 未定義 or 不明なフォームキーの場合はキュレネにフォールバック
    - セリフ中の「プレースホルダ（あだ名など）」を name で置き換える
    """

    # まずは各キャラのセリフ生成
    if form_key == "aglaia":
        base = get_aglaia_reply(message_text, affection_level)
    elif form_key == "trisbeas":
        base = get_trisbeas_reply(message_text, affection_level)
    elif form_key == "anaxagoras":
        base = get_anaxagoras_reply(message_text, affection_level)
    elif form_key == "hyacinthia":
        base = get_hyacinthia_reply(message_text, affection_level)
    elif form_key == "medimos":
        base = get_medimos_reply(message_text, affection_level)
    elif form_key == "sepharia":
        base = get_sepharia_reply(message_text, affection_level)
    elif form_key == "castoris":
        base = get_castoris_reply(message_text, affection_level)
    elif form_key == "phainon_kasreina":
        base = get_phainon_kasreina_reply(message_text, affection_level)
    elif form_key == "electra":
        base = get_electra_reply(message_text, affection_level)
    elif form_key == "cerydra":
        # ★ ケリュドラだけ user_id も渡す
        base = get_cerydra_reply(message_text, affection_level, user_id)
    elif form_key == "nanoka":
        base = get_nanoka_reply(message_text, affection_level)
    elif form_key == "danheng":
        base = get_danheng_reply(message_text, affection_level)
    elif form_key == "furina":
        base = get_furina_reply(message_text, affection_level)
    else:
        # キュレネ（デフォルト）
        try:
            base = get_cyrene_reply(message_text, affection_level)
        except TypeError:
            base = get_cyrene_reply(message_text)

    # ─────────────────────
    # ここで「あだ名」置き換え
    # ─────────────────────
    if name:
        # 「あだ名」 形式
        base = base.replace("「あだ名」", f"「{name}」")
        # あだ名 だけ書いてあるパターン
        base = base.replace("あだ名", name)
        # もし {nickname} を使っているキャラがいればそっちも対応
        base = base.replace("{nickname}", name)

    return base



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
    is_myurion_quiz = user_id in MYURION_QUIZ_STATE

    # どのモードでもない＋メンションもない → 無視
    if not (is_mentioned or is_waiting_nick or is_waiting_admin or is_waiting_rps
            or is_admin_mode or is_waiting_guardian or is_waiting_limit or is_waiting_transform
            or is_myurion_quiz):
        return

    # 本文（botメンションを除去）
    content = re.sub(rf"<@!?{client.user.id}>", "", message.content).strip()

    nickname = get_nickname(user_id)
    name = nickname if nickname else message.author.display_name

    admin_flag = is_admin(user_id)

    # 現在のフォーム
    current_form = get_user_form(user_id)
    current_form_name = get_form_display_name(current_form)

    # ===== 全体ミュリオンモード（メイン管理者限定） =====
    if content == "全体ミュリオンモード":
        if user_id != PRIMARY_ADMIN_ID:
            await message.channel.send(
                f"{message.author.mention} ごめんね、この操作はメイン管理者だけができるの。"
            )
            return

        set_all_myurion_enabled(True)

        await message.channel.send(
            f"{message.author.mention} サーバーのみんなを **ミュリオンモード** にしたわ！\n"
            "ミュミュミュウ〜♪"
        )
        return

    # ===== 全体ミュリオン解除（メイン管理者限定） =====
    if content == "全体ミュリオン解除":
        if user_id != PRIMARY_ADMIN_ID:
            await message.channel.send(
                f"{message.author.mention} ごめんね、この操作はメイン管理者だけができるの。"
            )
            return

        set_all_myurion_enabled(False)

        await message.channel.send(
            f"{message.author.mention} サーバーのみんなのミュリオンモードを解除したわ。\n"
            "しばらくは普通の言葉でお話ししましょ♪"
        )
        return



    # ===== ミュリオンクイズ回答中 =====
    if is_myurion_quiz:
        # 先に本体からメンションを除いたテキストを取る
        text = content if content else message.content.strip()

        ans = parse_myurion_answer(text)
        if ans is None:
            await send_myu(
                message,
                user_id,
                f"{message.author.mention} ミュミュ？ 1〜4の番号で答えてほしいミュ。"
            )
            return

        state = MYURION_QUIZ_STATE.get(user_id, {})
        correct_idx = state.get("correct_index", 0)  # 0〜3
        # ユーザーの選択は 1〜4 → 0〜3 に変換
        if ans - 1 == correct_idx:
            # 正解
            total = add_myurion_correct(user_id)
            if total >= 3 and not is_myurion_unlocked(user_id):
                # ★ ここでミュリオンモード開放 & 自動ON
                st = get_myurion_state(user_id)
                st["unlocked"] = True
                st["enabled"] = True
                save_myurion_state(user_id, st)

                MYURION_QUIZ_STATE.pop(user_id, None)

                await send_myu(
                    message,
                    user_id,
                    f"{message.author.mention} ミュイーー！！ 3問正解ミュ！\n"
                    "ミュリオンモードが開放されたミュ！ これからは、あたしの返事がミュウリオン語になるミュ～♪\n"
                    "（もし元の言葉に戻したくなったら `ミュリオンモードオフ` って言ってミュ）"
                )
                return
            else:
                MYURION_QUIZ_STATE.pop(user_id, None)
                await send_myu(
                    message,
                    user_id,
                    f"{message.author.mention} ミュミュ♪ 正解ミュ！ 今 {total}/3 問正解ミュ！\n"
                    "もう一度「ミュウ、ミュミュミュウミュウ、ミュイー」って言えば、次の問題に挑戦できるミュ！"
                )
                return
        else:
            # 不正解 → 状態はリセット
            MYURION_QUIZ_STATE.pop(user_id, None)
            await send_myu(
                message,
                user_id,
                f"{message.author.mention} ミュウ…残念ミュ。今回はハズレミュ。\n"
                "また「ミュウ、ミュミュミュウミュウ、ミュイー」って言って再挑戦してミュ！"
            )
            return

    # ===== ミュリオンモード：クイズ開始 =====
    if "ミュウ、ミュミュミュウミュウ、ミュイー" in content:
        st = get_myurion_state(user_id)
        if st.get("unlocked", False):
            # もう開放済みなら、ONにしてあげる
            st["enabled"] = True
            save_myurion_state(user_id, st)
            await send_myu(
                message,
                user_id,
                f"{message.author.mention} ミュミュ♪ ミュリオンモードはもう開放済みミュ。\n"
                "今からまたミュウリオン語でお話しするミュ～！"
            )
            return

        # まだ未開放 → クイズ開始
        correct_count = int(st.get("quiz_correct", 0))
        await send_myu(
            message,
            user_id,
            f"{message.author.mention} ミュミュミュ…ミュリオンへの扉を開きたいミュ？\n"
            "これからミュミュな三択…じゃなくて四択クイズを出すミュ！\n"
            "3問正解したらミュリオンモード解放ミュ～♪"
        )
        await send_myurion_question(message, user_id, correct_count)
        return

    # ===== ミュリオンモード ON/OFF トグル =====
    if content in ["ミュリオンモードオン", "ミュリオンモード", "ミュリオンオン"]:
        st = get_myurion_state(user_id)
        if not st.get("unlocked", False):
            await send_myu(
                message,
                user_id,
                f"{message.author.mention} まだミュリオンモードの扉は開いていないみたい…。\n"
                "「ミュウ、ミュミュミュウミュウ、ミュイー」って唱えて、クイズに挑戦してみない？"
            )
            return
        st["enabled"] = True
        save_myurion_state(user_id, st)
        await send_myu(
            message,
            user_id,
            f"{message.author.mention} ミュミュ♪ ミュリオンモード起動ミュ～！"
        )
        return

    if content in ["ミュリオンモードオフ", "ミュリオン解除", "ミュリオンオフ"]:
        st = get_myurion_state(user_id)
        if not st.get("enabled", False):
            # OFFの案内は普通の言葉でOK
            await message.channel.send(
                f"{message.author.mention} いまは普通の言葉で話しているみたいよ？"
            )
            return
        st["enabled"] = False
        save_myurion_state(user_id, st)
        # ここだけは絶対にミュ語にならないよう、直接 send
        await message.channel.send(
            f"{message.author.mention} 了解♪ いったんミュウリオン語はお休みして、普通の言葉に戻るわね。"
        )
        return

    # ===== メイン管理者専用：じゃんけん確定勝利スイッチ =====
    # 「愛は、永遠に」を送ると、次の自分のじゃんけんだけ確定勝利
    if user_id == PRIMARY_ADMIN_ID and "愛は、永遠に" in content:
        FORCE_RPS_WIN_NEXT.add(user_id)
        await send_myu(
            message,
            user_id,
            f"{message.author.mention} ふふっ、次のじゃんけんは……あなたの勝ちが約束されてるわ♡"
        )
        return

    # =====================
    # 特殊解放トリガー：丹恒（コード SkoPeo365 / skepeo365）
    # ※ スペース・大文字小文字をゆるく吸収
    # =====================
    normalized = re.sub(r"\s+", "", content).lower()
    if "skopeo365" in normalized or "skepeo365" in normalized:
        await handle_danheng_special_code(message, user_id, content)
        return

    # ===== 自分の変身コード入力待ち =====
    if user_id in waiting_for_transform_code:
        text = content if content else message.content.strip()

        # ★ 特別ルート：三月なのか / 長夜月
        if "なのになってみて" in text:
            # コード待ち状態は一度解除
            waiting_for_transform_code.discard(user_id)

            if not is_nanoka_unlocked(user_id):
                await send_myu(
                    message,
                    user_id,
                    f"{message.author.mention} ごめんね、その姿になるにはまだ条件が足りないみたい…。\n"
                    "まずは、あたしとのじゃんけんに何度も勝ってみて？ それからもう一度お願いしてくれる？"
                )
                return

            set_user_form(user_id, "nanoka")
            await send_myu(
                message,
                user_id,
                f"{message.author.mention} 今日から、あたしは「三月なのか / 長夜月」の姿でもあなたと一緒にいられるわ♪"
            )
            return

        # ★ 特別ルート：丹恒
        if "たんたんになってみて" in text:
            # コード待ち状態は一度解除
            waiting_for_transform_code.discard(user_id)

            if not is_danheng_unlocked(user_id):
                await send_myu(
                    message,
                    user_id,
                    f"{message.author.mention} その姿になるには、まだ鍵が足りないみたい…。\n"
                    "あの荒笛のことを、もっとよく知ってみて？ きっと道が開けるわ。"
                )
                return

            set_user_form(user_id, "danheng")
            await send_myu(
                message,
                user_id,
                f"{message.author.mention} …わかった。今日は彼の姿で、あなたと共に歩こう。\n"
                "無茶だけはしないでね。あなたを守る役目は、ちゃんと果たしたいから。"
            )
            return

        # ↓ ここからは「ふつうの変身コード」として扱う
        code = text.replace(" ", "").replace("　", "")
        form_key = resolve_form_code(code)

        if not form_key:
            await send_myu(
                message,
                user_id,
                f"{message.author.mention} そのコードでは変身できないみたい…。\n"
                "アグライアなら `KaLos618`、トリスビアスなら `HapLotes405` みたいに、"
                "もう一度正しい変身コードを教えてくれる？"
            )
            return

        set_user_form(user_id, form_key)
        waiting_for_transform_code.discard(user_id)

        form_name = get_form_display_name(form_key)
        await send_myu(
            message,
            user_id,
            f"{message.author.mention} 分かったわ、今からあたしは **{form_name}** として振る舞うわ♪"
        )
        return

    # ===== 親衛隊レベル数値入力待ち =====
    if user_id in waiting_for_guardian_level:
        target_id = waiting_for_guardian_level[user_id]
        text = content if content else message.content.strip()
        nums = re.findall(r"(-?\d+)", text)
        if not nums:
            await send_myu(
                message,
                user_id,
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

        await send_myu(
            message,
            user_id,
            f"{message.author.mention} {display} の親衛隊レベルを **Lv.{level_val}** に設定したわ♪"
        )
        return

    # ===== メッセージ制限の数値入力待ち =====
    if user_id in waiting_for_msg_limit:
        target_id = waiting_for_msg_limit[user_id]
        text = content if content else message.content.strip()
        nums = re.findall(r"(-?\d+)", text)
        if not nums:
            await send_myu(
                message,
                user_id,
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
            await send_myu(
                message,
                user_id,
                f"{message.author.mention} {display} のメッセージ制限を解除したわ。"
            )
        else:
            await send_myu(
                message,
                user_id,
                f"{message.author.mention} {display} は 1日 **{limit_val} 回** までお話しできるように設定したわ♪"
            )
        return

    # ===== じゃんけんの手入力待ち =====
    if user_id in waiting_for_rps_choice:
        text = content if content else message.content.strip()
        hand = parse_hand(text)
        if not hand:
            await send_myu(
                message,
                user_id,
                f"{message.author.mention} グー / チョキ / パー のどれかで教えて？"
            )
            return
        # メイン管理者用：次のじゃんけん確定勝利フラグ確認
        force_win = user_id in FORCE_RPS_WIN_NEXT

        # ボットの手を決定（force_win=True のときは必ずユーザーが勝つ手）
        bot_hand = get_bot_hand_against(hand, force_win=force_win)

        # 勝敗判定（force_win のときは強制的に勝ちにしておく）
        if force_win:
            result = "win"
            FORCE_RPS_WIN_NEXT.discard(user_id)  # 1回使ったら解除
        else:
            result = judge_janken(hand, bot_hand)

        # フォームに応じたじゃんけんセリフ
        flavor = get_rps_flavor_for_form(current_form, result, name)

        # ★ 勝ったら勝利数カウント
        if result == "win":
            wins = inc_janken_win(user_id)
        else:
            wins = get_janken_wins(user_id)

        waiting_for_rps_choice.discard(user_id)

        result_text = format_rps_result_message(
            current_form,
            name,
            hand,
            bot_hand,
            flavor,
            wins,
        )

        await send_myu(
            message,
            user_id,
            f"{message.author.mention} {result_text}"
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
            await send_myu(
                message,
                user_id,
                f"{message.author.mention} 管理者にしたい人を `@ユーザー` で教えて？"
            )
            return
        target = targets[0]
        add_admin(target.id)
        waiting_for_admin_add.discard(user_id)
        await send_myu(
            message,
            user_id,
            f"{message.author.mention} {target.display_name} を管理者に追加したわ♪"
        )
        return

    if user_id in waiting_for_admin_remove:
        targets = [m for m in message.mentions if m.id != client.user.id]
        if not targets:
            await send_myu(
                message,
                user_id,
                f"{message.author.mention} 管理者から外したい人を `@ユーザー` で教えて？"
            )
            return
        target = targets[0]
        ok = remove_admin(target.id)
        waiting_for_admin_remove.discard(user_id)

        if ok:
            await send_myu(
                message,
                user_id,
                f"{message.author.mention} {target.display_name} を管理者から外したわ。"
            )
        else:
            await send_myu(
                message,
                user_id,
                f"{message.author.mention} その人は管理者じゃないか、メイン管理者だから外せないみたい。"
            )
        return

    # ===== あだ名入力待ち =====
    if user_id in waiting_for_nickname:
        new_name = content if content else message.content.strip()
        if not new_name:
            await send_myu(
                message,
                user_id,
                f"{message.author.mention} もう一度、呼び名を教えて？"
            )
            return
        set_nickname(user_id, new_name)
        waiting_for_nickname.discard(user_id)
        await send_myu(
            message,
            user_id,
            f"{message.author.mention} ふふ…これからは「{new_name}」って呼ぶわね♪"
        )
        return

    if user_id in waiting_for_rename:
        new_name = content if content else message.content.strip()
        if not new_name:
            await send_myu(
                message,
                user_id,
                f"{message.author.mention} 新しい呼び名、もう一度教えて？"
            )
            return
        set_nickname(user_id, new_name)
        waiting_for_rename.discard(user_id)
        await send_myu(
            message,
            user_id,
            f"{message.author.mention} 了解♪ 今日から「{new_name}」よ。"
        )
        return

    # ===== データ管理モード中 =====
    if user_id in admin_data_mode:
        # データ管理終了
        if "データ管理終了" in content:
            admin_data_mode.discard(user_id)
            await send_myu(
                message,
                user_id,
                f"{message.author.mention} データ管理モードを終了するわ。また必要になったら呼んでね。"
            )
            return

        # ニックネーム確認
        if "ニックネーム確認" in content:
            data = load_data()
            if not data:
                await send_myu(
                    message,
                    user_id,
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
            await send_myu(
                message,
                user_id,
                "\n".join(lines)
            )
            return

        # ===== 全体ミュリオンモード（メイン管理者限定） =====
        if content == "全体ミュリオンモード":
            if user_id != PRIMARY_ADMIN_ID:
                await message.channel.send(
                    f"{message.author.mention} ごめんね、この操作はメイン管理者だけができるの。"
                )
                return

            set_all_myurion_enabled(True)

            await message.channel.send(
                f"{message.author.mention} サーバーのみんなを **ミュリオンモード** にしたわ！\n"
                "ミュミュミュウ〜♪"
            )
            return

        # ===== 全体ミュリオン解除（メイン管理者限定） =====
        if content == "全体ミュリオン解除":
            if user_id != PRIMARY_ADMIN_ID:
                await message.channel.send(
                    f"{message.author.mention} ごめんね、この操作はメイン管理者だけができるの。"
                )
                return

            set_all_myurion_enabled(False)
            await message.channel.send(
                f"{message.author.mention} サーバーのみんなのミュリオンモードを解除したわ。\n"
                "通常言語に戻るわよ♪"
            )
            return
        
        # 親衛隊レベル編集メニュー
        if "親衛隊レベル編集" in content:
            await send_myu(
                message,
                user_id,
                f"{message.author.mention} 親衛隊レベルをどうしたい？\n"
                "- `親衛隊レベル確認` … 全員のレベル一覧を表示\n"
                "- `親衛隊レベル設定 @ユーザー` … 特定ユーザーのレベルを設定/変更\n"
                "- `親衛隊レベル削除 @ユーザー` … 特定ユーザーのレベルを削除\n"
                "- `データ管理終了`"
            )
            return

        # 親衛隊レベル確認
        if content == "親衛隊レベル確認":
            levels = load_guardian_levels()
            if not levels:
                await send_myu(
                    message,
                    user_id,
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
            await send_myu(
                message,
                user_id,
                "\n".join(lines)
            )
            return

        # 親衛隊レベル設定
        if content.startswith("親衛隊レベル設定"):
            targets = [m for m in message.mentions if m.id != client.user.id]
            if not targets:
                await send_myu(
                    message,
                    user_id,
                    f"{message.author.mention} 誰のレベルを設定するか、`@ユーザー` を付けて教えて？\n"
                    "例: `親衛隊レベル設定 @ユーザー`"
                )
                return
            target = targets[0]
            waiting_for_guardian_level[user_id] = target.id
            await send_myu(
                message,
                user_id,
                f"{message.author.mention} {target.display_name} の親衛隊レベルをいくつにする？ 数字で教えてね。\n"
                "例えば `3` みたいに送ってくれればいいわ♪"
            )
            return

        # 親衛隊レベル削除
        if content.startswith("親衛隊レベル削除"):
            targets = [m for m in message.mentions if m.id != client.user.id]
            if not targets:
                await send_myu(
                    message,
                    user_id,
                    f"{message.author.mention} 誰のレベルを消すか、`@ユーザー` を付けて教えて？\n"
                    "例: `親衛隊レベル削除 @ユーザー`"
                )
                return
            target = targets[0]
            delete_guardian_level(target.id)
            await send_myu(
                message,
                user_id,
                f"{message.author.mention} {target.display_name} の親衛隊レベルを削除したわ。"
            )
            return

        # 好感度編集メニュー
        if "好感度編集" in content:
            await send_myu(
                message,
                user_id,
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
            await send_myu(
                message,
                user_id,
                "\n".join(lines)
            )
            return

        # 好感度アクション設定
        if content.startswith("好感度アクション設定"):
            parts = content.split()
            if len(parts) < 3:
                await send_myu(
                    message,
                    user_id,
                    f"{message.author.mention} `好感度アクション設定 アクション名 数値` の形で教えて？\n"
                    "例: `好感度アクション設定 talk 5`"
                )
                return
            action_name = parts[1]
            try:
                xp_val = int(parts[2])
            except ValueError:
                await send_myu(
                    message,
                    user_id,
                    f"{message.author.mention} XP は数字でお願いね。"
                )
                return
            cfg = load_affection_config()
            xp_actions = cfg.get("xp_actions", {})
            xp_actions[action_name] = xp_val
            cfg["xp_actions"] = xp_actions
            save_affection_config(cfg)
            await send_myu(
                message,
                user_id,
                f"{message.author.mention} アクション `{action_name}` のXPを **{xp_val}** に設定したわ。"
            )
            return

        # 好感度レベル設定
        if content.startswith("好感度レベル設定"):
            parts = content.split()
            if len(parts) < 3:
                await send_myu(
                    message,
                    user_id,
                    f"{message.author.mention} `好感度レベル設定 レベル 数値` の形で教えて？\n"
                    "例: `好感度レベル設定 3 4000`"
                )
                return
            try:
                lv = int(parts[1])
                xp_need = int(parts[2])
            except ValueError:
                await send_myu(
                    message,
                    user_id,
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
            await send_myu(
                message,
                user_id,
                f"{message.author.mention} Lv.{lv} に必要なXPを **{xp_need}** に設定したわ。"
            )
            return

        # メッセージ制限編集メニュー
        if "メッセージ制限編集" in content:
            await send_myu(
                message,
                user_id,
                f"{message.author.mention} メッセージ制限をどうする？\n"
                "- `メッセージ制限確認` … 制限が設定されているユーザー一覧\n"
                "- `メッセージ制限設定 @ユーザー` … その人の1日あたり上限回数を設定\n"
                "- `メッセージ制限削除 @ユーザー` … その人の制限を解除\n"
                "- `メッセージ制限bypass編集`（メイン管理者専用）\n"
                "- `変身管理`\n"
                "- `データ管理終了`"
            )
            return

        # メッセージ制限確認
        if content == "メッセージ制限確認":
            limits = load_message_limits()
            if not limits:
                await send_myu(
                    message,
                    user_id,
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
            await send_myu(
                message,
                user_id,
                "\n".join(lines)
            )
            return

        # メッセージ制限設定
        if content.startswith("メッセージ制限設定"):
            targets = [m for m in message.mentions if m.id != client.user.id]
            if not targets:
                await send_myu(
                    message,
                    user_id,
                    f"{message.author.mention} 誰の制限を設定するか、`@ユーザー` を付けて教えて？\n"
                    "例: `メッセージ制限設定 @ユーザー`"
                )
                return
            target = targets[0]
            waiting_for_msg_limit[user_id] = target.id
            await send_myu(
                message,
                user_id,
                f"{message.author.mention} {target.display_name} は1日に何回までお話しできるようにする？\n"
                "数字だけ送ってくれればいいわ♪ `0` 以下なら制限なしに戻すわ。"
            )
            return

        # メッセージ制限削除
        if content.startswith("メッセージ制限削除"):
            targets = [m for m in message.mentions if m.id != client.user.id]
            if not targets:
                await send_myu(
                    message,
                    user_id,
                    f"{message.author.mention} 誰の制限を解除するか、`@ユーザー` を付けて教えて？\n"
                    "例: `メッセージ制限削除 @ユーザー`"
                )
                return
            target = targets[0]
            delete_message_limit(target.id)
            await send_myu(
                message,
                user_id,
                f"{message.author.mention} {target.display_name} のメッセージ制限を解除したわ。"
            )
            return

        # メッセージ制限bypass系
        if "メッセージ制限bypass編集" in content:
            if user_id != PRIMARY_ADMIN_ID:
                await send_myu(
                    message,
                    user_id,
                    f"{message.author.mention} ごめんね、この設定はいちばん上の管理者専用なの。"
                )
                return
            await send_myu(
                message,
                user_id,
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
                await send_myu(
                    message,
                    user_id,
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
            await send_myu(
                message,
                user_id,
                "\n".join(lines)
            )
            return

        if content == "メッセージ制限bypass全体オン":
            if user_id != PRIMARY_ADMIN_ID:
                await send_myu(
                    message,
                    user_id,
                    f"{message.author.mention} これはメイン管理者専用のスイッチなの。"
                )
                return
            cfg = load_message_limit_config()
            cfg["bypass_enabled"] = True
            save_message_limit_config(cfg)
            await send_myu(
                message,
                user_id,
                f"{message.author.mention} メッセージ制限bypass機能を **ON** にしたわ。"
            )
            return

        if content == "メッセージ制限bypass全体オフ":
            if user_id != PRIMARY_ADMIN_ID:
                await send_myu(
                    message,
                    user_id,
                    f"{message.author.mention} これはメイン管理者専用のスイッチなの。"
                )
                return
            cfg = load_message_limit_config()
            cfg["bypass_enabled"] = False
            save_message_limit_config(cfg)
            await send_myu(
                message,
                user_id,
                f"{message.author.mention} メッセージ制限bypass機能を **OFF** にしたわ。"
            )
            return

        if content == "メッセージ制限bypass付与許可オン":
            if user_id != PRIMARY_ADMIN_ID:
                await send_myu(
                    message,
                    user_id,
                    f"{message.author.mention} これを変えられるのはメイン管理者だけよ。"
                )
                return
            cfg = load_message_limit_config()
            cfg["allow_bypass_grant"] = True
            save_message_limit_config(cfg)
            await send_myu(
                message,
                user_id,
                f"{message.author.mention} 他の人にbypassを付与できるようにしたわ。"
            )
            return

        if content == "メッセージ制限bypass付与許可オフ":
            if user_id != PRIMARY_ADMIN_ID:
                await send_myu(
                    message,
                    user_id,
                    f"{message.author.mention} これを変えられるのはメイン管理者だけよ。"
                )
                return
            cfg = load_message_limit_config()
            cfg["allow_bypass_grant"] = False
            save_message_limit_config(cfg)
            await send_myu(
                message,
                user_id,
                f"{message.author.mention} これからは新しくbypassを配ることはできなくなるわ。"
            )
            return

        if content.startswith("メッセージ制限bypass付与"):
            if user_id != PRIMARY_ADMIN_ID:
                await send_myu(
                    message,
                    user_id,
                    f"{message.author.mention} ごめんね、bypassを配れるのはメイン管理者だけなの。"
                )
                return
            cfg = load_message_limit_config()
            if not cfg.get("bypass_enabled", False):
                await send_myu(
                    message,
                    user_id,
                    f"{message.author.mention} いまはbypass機能自体がOFFになっているみたい。\n"
                    "`メッセージ制限bypass全体オン` で有効化してから試してね。"
                )
                return
            if not cfg.get("allow_bypass_grant", False):
                await send_myu(
                    message,
                    user_id,
                    f"{message.author.mention} いまは「他の人にbypassを付与できない」設定になっているわ。\n"
                    "`メッセージ制限bypass付与許可オン` にしてからやってみて？"
                )
                return
            targets = [m for m in message.mentions if m.id != client.user.id]
            if not targets:
                await send_myu(
                    message,
                    user_id,
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
            await send_myu(
                message,
                user_id,
                f"{message.author.mention} {target.display_name} にメッセージ制限bypassを付与したわ。"
            )
            return

        if content.startswith("メッセージ制限bypass削除"):
            if user_id != PRIMARY_ADMIN_ID:
                await send_myu(
                    message,
                    user_id,
                    f"{message.author.mention} ごめんね、bypassの管理はメイン管理者だけなの。"
                )
                return
            targets = [m for m in message.mentions if m.id != client.user.id]
            if not targets:
                await send_myu(
                    message,
                    user_id,
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
            await send_myu(
                message,
                user_id,
                f"{message.author.mention} {target.display_name} からメッセージ制限bypassを外したわ。"
            )
            return

        # じゃんけん勝利数を任意回数増やす（管理者用）
        if content.startswith("じゃんけん勝利数追加"):
            if user_id != PRIMARY_ADMIN_ID:
                await send_myu(
                    message,
                    user_id,
                    f"{message.author.mention} ごめんね、この操作はメイン管理者だけができるの。"
                )
                return
            # 例: 「じゃんけん勝利数追加 @ユーザー 5」
            targets = [m for m in message.mentions if m.id != client.user.id]
            if not targets:
                await send_myu(
                    message,
                    user_id,
                    f"{message.author.mention} 誰の勝利数を増やすか、`@ユーザー` を付けて教えて？\n"
                    "例: `じゃんけん勝利数追加 @ユーザー 5`"
                )
                return

            target = targets[0]

            # メンション表記を抜いたテキストから数字だけ抜き出す
            plain = re.sub(r"<@!?\d+>", "", content)
            nums = re.findall(r"(-?\d+)", plain)
            if not nums:
                await send_myu(
                    message,
                    user_id,
                    f"{message.author.mention} いくつ増やすか、最後に数字も書いてほしいな。\n"
                    "例: `じゃんけん勝利数追加 @ユーザー 5`"
                )
                return

            delta = int(nums[-1])
            if delta <= 0:
                await send_myu(
                    message,
                    user_id,
                    f"{message.author.mention} ごめんね、0以下は増やせないの。正の数字で教えて？"
                )
                return

            # delta 回だけ勝利数をインクリメント
            for _ in range(delta):
                inc_janken_win(target.id)

            wins = get_janken_wins(target.id)
            await send_myu(
                message,
                user_id,
                f"{message.author.mention} {target.display_name} のじゃんけん勝利数を **{delta} 回** 増やしたわ。\n"
                f"いまは合計 **{wins} 回** 勝っていることになっているわよ。"
            )
            return

        # 好感度XPを直接増減させる（管理者用）
        if content.startswith("好感度XP追加"):
            if user_id != PRIMARY_ADMIN_ID:
                await send_myu(
                    message,
                    user_id,
                    f"{message.author.mention} ごめんね、この操作はメイン管理者だけができるの。"
                )
                return

            # 例: 「好感度XP追加 @ユーザー 1000」 / 「好感度XP追加 @ユーザー -500」
            targets = [m for m in message.mentions if m.id != client.user.id]
            if not targets:
                await send_myu(
                    message,
                    user_id,
                    f"{message.author.mention} 誰のXPをいじるか、`@ユーザー` を付けて教えて？\n"
                    "例: `好感度XP追加 @ユーザー 1000`"
                )
                return

            target = targets[0]

            # メンション表記を抜いてから数字だけ拾う
            plain = re.sub(r"<@!?\d+>", "", content)
            nums = re.findall(r"(-?\d+)", plain)
            if not nums:
                await send_myu(
                    message,
                    user_id,
                    f"{message.author.mention} どれくらい増やす（または減らす）か、数字も書いてほしいな。\n"
                    "例: `好感度XP追加 @ユーザー 1000`"
                )
                return

            delta = int(nums[-1])

            # 好感度XPを加算（マイナスもOK。内部で0未満にはならない）
            add_affection_xp(target.id, delta, reason="admin_adjust")

            xp, level_val = get_user_affection(target.id)
            await send_myu(
                message,
                user_id,
                f"{message.author.mention} {target.display_name} の好感度XPを **{delta}** だけ調整したわ。\n"
                f"いまの状態は **Lv.{level_val} / {xp} XP** になっているわよ。"
            )
            return

        # 変身管理メニュー
        if "変身管理" in content:
            await send_myu(
                message,
                user_id,
                f"{message.author.mention} 変身の設定をどうする？\n"
                "- `変身一覧確認` … 誰がどの黄金裔（開拓者）を使っているか一覧表示\n"
                "- `変身編集一人 @ユーザー コードまたは名前` … その人のフォームを変更\n"
                "- `変身編集全体 コードまたは名前` … 全員のフォームを一括変更（メイン管理者のみ）\n"
                "- `変身解放状況確認` … 三月なのか／丹恒の解放状況を一覧表示（メイン管理者専用）\n"
                "- `データ管理終了` … モード終了\n"
                "※ コードは KaLos618, HapLotes405 などの変身コードよ。"
            )
            return

        # 変身一覧確認
        if content == "変身一覧確認":
            forms = get_all_forms()
            if not forms:
                await send_myu(
                    message,
                    user_id,
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
            await send_myu(
                message,
                user_id,
                "\n".join(lines)
            )
            return

        # 変身編集一人
        if content.startswith("変身編集一人"):
            targets = [m for m in message.mentions if m.id != client.user.id]
            if not targets:
                await send_myu(
                    message,
                    user_id,
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
                await send_myu(
                    message,
                    user_id,
                    f"{message.author.mention} その黄金裔のコードや名前は知らないみたい…。\n"
                    "もう一度確認して教えてくれる？"
                )
                return

            set_user_form(target.id, form_key)
            form_name = get_form_display_name(form_key)
            await send_myu(
                message,
                user_id,
                f"{message.author.mention} {target.display_name} を **{form_name}** に変身させておいたわ♪"
            )
            return

        # 変身編集全体（メイン管理者限定）
        if content.startswith("変身編集全体"):
            if user_id != PRIMARY_ADMIN_ID:
                await send_myu(
                    message,
                    user_id,
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
                await send_myu(
                    message,
                    user_id,
                    f"{message.author.mention} その黄金裔のコードや名前は知らないみたい…。\n"
                    "もう一度確認して教えてくれる？"
                )
                return

            set_all_forms(form_key)
            form_name = get_form_display_name(form_key)
            await send_myu(
                message,
                user_id,
                f"{message.author.mention} 登録されているみんなのフォームを、全部 **{form_name}** に揃えておいたわ♪"
            )
            return

        # 変身解放状況確認（メイン管理者専用）
        if content == "変身解放状況確認":
            if user_id != PRIMARY_ADMIN_ID:
                await send_myu(
                    message,
                    user_id,
                    f"{message.author.mention} ごめんね、この確認ができるのは一番上の管理者だけなの。"
                )
                return

            # /data/special_unlocks.json を読み込み
            if not SPECIAL_UNLOCKS_FILE.exists():
                await send_myu(
                    message,
                    user_id,
                    f"{message.author.mention} まだ特別な解放データは保存されていないみたい。"
                )
                return

            try:
                raw = json.loads(SPECIAL_UNLOCKS_FILE.read_text(encoding="utf-8"))
            except Exception:
                await send_myu(
                    message,
                    user_id,
                    f"{message.author.mention} 解放データの読み込みに失敗しちゃったみたい…ごめんね。"
                )
                return

            if not isinstance(raw, dict) or not raw:
                await send_myu(
                    message,
                    user_id,
                    f"{message.author.mention} いまのところ、特別な解放状況は登録されていないみたい。"
                )
                return

            lines = ["【変身解放状況】"]
            for uid_str, state in raw.items():
                try:
                    uid_int = int(uid_str)
                except Exception:
                    uid_int = None

                member = None
                if message.guild and uid_int is not None:
                    member = message.guild.get_member(uid_int)

                user_display = member.display_name if member else f"ID: {uid_str}"

                jwins = int(state.get("janken_wins", 0))
                nanoka = "解放済み" if state.get("nanoka_unlocked") else "未解放"
                d_stage1 = "達成済み" if state.get("danheng_stage1") else "未達成"
                danh = "解放済み" if state.get("danheng_unlocked") else "未解放"

                lines.append(
                    f"- {user_display}\n"
                    f"  ・じゃんけん勝利数: {jwins}\n"
                    f"  ・三月なのか: {nanoka}\n"
                    f"  ・丹恒ステップ1(荒笛): {d_stage1}\n"
                    f"  ・丹恒: {danh}"
                )

            await send_myu(
                message,
                user_id,
                "\n".join(lines)
            )
            return

        # 管理者編集メニュー（既存）
        if "管理者編集" in content:
            await send_myu(
                message,
                user_id,
                f"{message.author.mention} 管理者をどうしたい？\n"
                "- `管理者追加`\n"
                "- `管理者削除`\n"
                "- `データ管理終了`"
            )
            return

        if "管理者追加" in content:
            waiting_for_admin_add.add(user_id)
            await send_myu(
                message,
                user_id,
                f"{message.author.mention} 誰を管理者として追加する？ `@ユーザー` で教えてね。"
            )
            return

        if "管理者削除" in content:
            waiting_for_admin_remove.add(user_id)
            await send_myu(
                message,
                user_id,
                f"{message.author.mention} 誰を管理者から外す？ `@ユーザー` で教えてね。"
            )
            return

        # 不明コマンド
        await send_myu(
            message,
            user_id,
            f"{message.author.mention} ごめんね、そのコマンドはまだ知らないの…。\n"
            "いま使えるのは\n"
            "- `ニックネーム確認`\n"
            "- `管理者編集`\n"
            "- `親衛隊レベル編集`\n"
            "- `好感度編集`\n"
            "- `メッセージ制限編集`\n"
            "- `メッセージ制限bypass編集`（メイン管理者専用）\n"
            "- `変身管理`\n"
            "- `変身解放状況確認`（メイン管理者専用）\n"
            "- `データ管理終了`\n"
            "あたりね。"
        )
        return

    if content == "データ管理":
        if not is_admin(user_id):
            await send_myu(
                message,
                user_id,
                f"{message.author.mention} ごめんね、このモードは管理者専用なの。"
            )
            return
        admin_data_mode.add(user_id)
        await send_myu(
            message,
            user_id,
            f"{message.author.mention} データ管理モードに入ったわ。\n"
            "何を確認したい？\n"
            "- `ニックネーム確認`\n"
            "- `管理者編集`\n"
            "- `親衛隊レベル編集`\n"
            "- `好感度編集`\n"
            "- `好感度XP追加`\n"
            "- `じゃんけん勝利数追加`\n"
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
            await send_myu(
                message,
                user_id,
                f"{message.author.mention} まだ親衛隊レベルは登録されていないみたい。\n"
                "そのうち誰かがレベルを付けてくれるかもね？"
            )
        else:
            await send_myu(
                message,
                user_id,
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
        await send_myu(
            message,
            user_id,
            f"{message.author.mention} {msg_text}"
        )
        return

    # ===== 一般：自分の変身状態確認 =====
    if content in ["変身状態", "今の姿", "今のフォーム"]:
        await send_myu(
            message,
            user_id,
            f"{message.author.mention} 今のあたしは **{current_form_name}** としてあなたと話してるわ♪"
        )
        return

    # ===== 一般：変身開始 =====
    if content == "変身":
        waiting_for_transform_code.add(user_id)
        await send_myu(
            message,
            user_id,
            f"{message.author.mention} ふふっ、変身したいのね？\n"
            "アグライアなら `KaLos618`、トリスビアスなら `HapLotes405` みたいに、変身コードを教えて？"
        )
        return

    # =====================
    # 変身コマンド：三月なのか / 長夜月
    # =====================
    if "なのになってみて" in content:
        if not is_nanoka_unlocked(user_id):
            await send_myu(
                message,
                user_id,
                f"{message.author.mention} ごめんね、その姿になるにはまだ条件が足りないみたい…。\n"
                "まずは、あたしとのじゃんけんに何度も勝ってみて？ それからもう一度お願いしてくれる？"
            )
            return

        set_user_form(user_id, "nanoka")
        await send_myu(
            message,
            user_id,
            f"{message.author.mention} 今日から、あたしは「三月なのか / 長夜月」の姿でもあなたと一緒にいられるわ♪"
        )
        return

    # =====================
    # 変身コマンド：丹恒
    # =====================
    if "たんたんになってみて" in content:
        if not is_danheng_unlocked(user_id):
            await send_myu(
                message,
                user_id,
                f"{message.author.mention} その姿になるには、まだ鍵が足りないみたい…。\n"
                "あの荒笛のことを、もっとよく知ってみて？ きっと道が開けるわ。"
            )
            return

        set_user_form(user_id, "danheng")
        await send_myu(
            message,
            user_id,
            f"{message.author.mention} …わかった。今日は彼の姿で、あなたと共に歩こう。\n"
            "無茶だけはしないでね。あなたを守る役目は、ちゃんと果たしたいから。"
        )
        return

    # ===== デイリー石受け取り =====
    if content in ["デイリーを受け取りたい", "デイリー受け取りたい", "デイリー受け取り"]:
        ok, stones, reason = grant_daily_stones(user_id)
        if ok:
            await send_myu(
                message,
                user_id,
                f"{message.author.mention} {reason}\n"
                f"今の所持石は **{stones} 個** になったわ♪"
            )
        else:
            await send_myu(
                message,
                user_id,
                f"{message.author.mention} {reason}\n"
                f"今の所持石は **{stones} 個** のままよ。"
            )
        return

    # ===== ガチャメニュー表示 =====
    if content in ["ガチャをしたい", "ガチャしたい", "ガチャメニュー"]:
        status_text = format_gacha_status(user_id)
        await send_myu(
            message,
            user_id,
            f"{message.author.mention} {status_text}"
        )
        return

    # ===== ガチャ説明（排出率） =====
    if content in ["ガチャ説明", "ガチャ排出確率", "ガチャ確率"]:
        await send_myu(
            message,
            user_id,
            f"{message.author.mention} {format_gacha_rates()}"
        )
        return

    # ===== 単発ガチャ =====
    if content in ["単発ガチャ", "単発", "1連ガチャ", "１連ガチャ"]:
        ok, text = perform_gacha_pulls(user_id, 1, use_ticket=False)
        await send_myu(
            message,
            user_id,
            f"{message.author.mention} {text}"
        )
        return

    # ===== 10連ガチャ（石消費） =====
    if content in ["１０連ガチャ", "10連ガチャ", "10連", "１０連"]:
        ok, text = perform_gacha_pulls(user_id, 10, use_ticket=False)
        await send_myu(
            message,
            user_id,
            f"{message.author.mention} {text}"
        )
        return

    # ===== 10連ガチャ（すり抜けチケット使用） =====
    if content in ["チケット１０連", "チケット10連", "すり抜け１０連", "すり抜け10連"]:
        ok, text = perform_gacha_pulls(user_id, 10, use_ticket=True)
        await send_myu(
            message,
            user_id,
            f"{message.author.mention} {text}"
        )
        return

    # ===== あだ名系 =====
    if content.startswith("あだ名登録"):
        new_name = content.replace("あだ名登録", "", 1).strip()
        if not new_name:
            waiting_for_nickname.add(user_id)
            await send_myu(
                message,
                user_id,
                f"{message.author.mention} あたし、どう呼べばいいの？"
            )
            return
        set_nickname(user_id, new_name)
        await send_myu(
            message,
            user_id,
            f"{message.author.mention} ふふ…これからは「{new_name}」って呼ぶわね♪"
        )
        return

    if content.startswith("あだ名変更"):
        new_name = content.replace("あだ名変更", "", 1).strip()
        if not new_name:
            waiting_for_rename.add(user_id)
            await send_myu(
                message,
                user_id,
                f"{message.author.mention} 新しい呼び名、教えて？"
            )
            return
        set_nickname(user_id, new_name)
        await send_myu(
            message,
            user_id,
            f"{message.author.mention} 了解♪ 今日から「{new_name}」よ。"
        )
        return

    if content.startswith("あだ名削除"):
        delete_nickname(user_id)
        waiting_for_nickname.discard(user_id)
        waiting_for_rename.discard(user_id)
        await send_myu(
            message,
            user_id,
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

            # フォームに応じたじゃんけんセリフ（勝ち/負け/あいこ）
            flavor = get_rps_flavor_for_form(current_form, result, name)

            # ★ 勝利カウント
            if result == "win":
                wins = inc_janken_win(user_id)
            else:
                wins = get_janken_wins(user_id)

            result_text = format_rps_result_message(
                current_form,
                name,
                hand,
                bot_hand,
                flavor,
                wins,
            )

            await send_myu(
                message,
                user_id,
                f"{message.author.mention} {result_text}"
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

        # 手をあとで選ぶパターン
        waiting_for_rps_choice.add(user_id)
        prompt = get_rps_prompt_for_form(current_form, name)
        await send_myu(
            message,
            user_id,
            f"{message.author.mention} {prompt}"
        )
        return


    # ===== メンションだけのとき =====
    if content == "":
        xp, level_val = get_user_affection(user_id)
        reply = generate_reply_for_form(current_form, "", level_val, user_id, name)
        await send_myu(
            message,
            user_id,
            f"{message.author.mention} {reply}"
        )
        cfg = load_affection_config()
        delta = int(cfg.get("xp_actions", {}).get("talk", 0))
        add_affection_xp(user_id, delta, reason="talk")
        return
    # =====================
    # 特殊解放トリガー：三月なのか
    # じゃんけん勝利数 307回以上 ＋ 「記憶は流れ星を待ってる」
    # =====================
    if "記憶は流れ星を待ってる" in content or "記憶は流れ星を待っている" in content:
        xp, lv = get_user_affection(user_id)
        base_reply = generate_reply_for_form(current_form, content, lv, user_id, name)

        unlocked_now = False
        wins = get_janken_wins(user_id)
        if wins >= 307 and not is_nanoka_unlocked(user_id):
            set_nanoka_unlocked(user_id, True)
            unlocked_now = True

        extra = ""
        if unlocked_now:
            extra = (
                "\n\n三月なのかの解放条件を達成したわ！\n"
                "『なのになってみて』って言ってみない？"
            )
        await send_myu(
            message,
            user_id,
            f"{message.author.mention} {base_reply}{extra}"
        )
        return

    # ===== 通常応答 =====
    xp, level_val = get_user_affection(user_id)

    # 変身状態に応じた返事を生成（キュレネ・黄金裔・開拓者）
    reply = generate_reply_for_form(current_form, content, level_val, user_id, name)

    # ★ 丹恒解放ステップ1チェック
    if current_form == "cyrene" and ARAFUE_TRIGGER_LINE in reply:
        mark_danheng_stage1(user_id)

    await send_myu(
        message,
        user_id,
        f"{message.author.mention} {reply}"
    )
    # 好感度XP加算（会話）
    cfg = load_affection_config()
    delta = int(cfg.get("xp_actions", {}).get("talk", 0))
    add_affection_xp(user_id, delta, reason="talk")



# 実行
client.run(DISCORD_TOKEN)
