# cyrene.py
import os
import re
import json
import random
from pathlib import Path

import discord
from dotenv import load_dotenv

from lines import get_cyrene_reply, get_rps_line  # ★ 好感度対応版（第2引数: affection_level）

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
client = discord.Client(intents=intents)

# =====================
# データ保存用ディレクトリ（Railway volume: /data）
# =====================
DATA_DIR = Path("/data")
DATA_DIR.mkdir(parents=True, exist_ok=True)

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

# ★ デフォルト設定（ここを書き換えれば初期値を変えられる）
DEFAULT_AFFECTION_CONFIG = {
    # 各レベルに必要な累積経験値（インデックス = レベル）
    # 例: Lv1:0, Lv2:1000, Lv3:4000, Lv4:16000, Lv5:640000, Lv6:33350337
    "level_thresholds": [0, 1000, 4000, 16000, 640000, 33350337],
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
        # 足りないキーがあってもデフォルトで補完
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
    # インデックス = レベル として扱う（1スタート）
    for lv in range(1, len(thresholds)):
        need = thresholds[lv]
        if xp >= need:
            level = lv
        else:
            break
    return max(1, level)


def get_user_affection(user_id: int) -> tuple[int, int]:
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
    # レベルアップ演出をするならここで判定してもOK（今回はログだけ）
    # old_level = get_level_from_xp(xp - delta, load_affection_config())
    # new_level = get_level_from_xp(xp, load_affection_config())
    # if new_level > old_level:
    #     print(f"[AFFECTION] user {user_id} leveled up {old_level} -> {new_level} ({reason})")

# =====================
# 会話状態管理
# =====================
waiting_for_nickname = set()          # 新規あだ名入力待ち
waiting_for_rename = set()            # あだ名変更入力待ち
admin_data_mode = set()               # データ管理モード中のユーザー
waiting_for_admin_add = set()         # 管理者追加で @待ち
waiting_for_admin_remove = set()      # 管理者削除で @待ち
waiting_for_rps_choice = set()        # じゃんけんの手入力待ち
waiting_for_guardian_level = {}       # {管理者ID: レベルを設定する対象ユーザーID}

# =====================
# 起動
# =====================
@client.event
async def on_ready():
    print(f"ログイン成功: {client.user} ({client.user.id})")

# =====================
# じゃんけん用ヘルパ
# =====================
JANKEN_HANDS = ["グー", "チョキ", "パー"]


def parse_hand(text: str) -> str | None:
    if "グー" in text:
        return "グー"
    if "チョキ" in text:
        return "チョキ"
    if "パー" in text:
        return "パー"
    return None


def judge_janken(user_hand: str, bot_hand: str) -> str:
    """
    ユーザーとbotの手から
    'win' / 'lose' / 'draw' のいずれかを返す
    """
    if user_hand == bot_hand:
        return "draw"
    win = (
        (user_hand == "グー" and bot_hand == "チョキ") or
        (user_hand == "チョキ" and bot_hand == "パー") or
        (user_hand == "パー" and bot_hand == "グー")
    )
    return "win" if win else "lose"

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
    is_mentioned = client.user in message.mentions

    # どのモードでもない＋メンションもない → 完全無視
    if not (is_mentioned or is_waiting_nick or is_waiting_admin or is_waiting_rps or is_admin_mode or is_waiting_guardian):
        return

    # メンション（bot本人）だけ削除したテキスト
    content = re.sub(rf"<@!?{client.user.id}>", "", message.content).strip()

    # あだ名と表示名
    nickname = get_nickname(user_id)
    name = nickname if nickname else message.author.display_name

    # =====================
    # ✅ 親衛隊レベル数値入力待ち
    # =====================
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
            if member is None:
                try:
                    member = await message.guild.fetch_member(target_id)
                except Exception:
                    member = None

        display = member.display_name if member else f"ID: {target_id}"

        del waiting_for_guardian_level[user_id]

        await message.channel.send(
            f"{message.author.mention} {display} の親衛隊レベルを **Lv.{level_val}** に設定したわ♪"
        )
        return

    # =====================
    # ✅ じゃんけんの手入力待ち
    # =====================
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

        waiting_for_rps_choice.discard(user_id)

        await message.channel.send(
            f"{message.author.mention} {name} は **{hand}**、あたしは **{bot_hand}** よ。\n{flavor}"
        )

        # ★ じゃんけんの結果に応じて好感度XP付与
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

    # =====================
    # ✅ 管理者追加の @ 待ち
    # =====================
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

    # =====================
    # ✅ 管理者削除の @ 待ち
    # =====================
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

    # =====================
    # ✅ あだ名入力待ち（新規登録）
    # =====================
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

    # =====================
    # ✅ あだ名入力待ち（変更）
    # =====================
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

    # =====================
    # ⭐ データ管理モード中のコマンド
    # =====================
    if user_id in admin_data_mode:
        if "データ管理終了" in content:
            admin_data_mode.discard(user_id)
            await message.channel.send(
                f"{message.author.mention} データ管理モードを終了するわ。また必要になったら呼んでね。"
            )
            return

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
                    if member is None:
                        try:
                            member = await message.guild.fetch_member(uid_int)
                        except Exception:
                            member = None

                if member:
                    lines.append(f"- {member.display_name} (ID: {uid_str}) → {nick}")
                else:
                    lines.append(f"- ID: {uid_str} → {nick}")

            await message.channel.send("\n".join(lines))
            return

        # ★ 親衛隊レベル編集メニュー
        if "親衛隊レベル編集" in content:
            await message.channel.send(
                f"{message.author.mention} 親衛隊レベルをどうしたい？\n"
                "- `親衛隊レベル確認` … 全員のレベル一覧を表示\n"
                "- `親衛隊レベル設定 @ユーザー` … 特定ユーザーのレベルを設定/変更（あとで数字を聞くわ）\n"
                "- `親衛隊レベル削除 @ユーザー` … 特定ユーザーのレベルを削除\n"
                "- `データ管理終了` … モード終了"
            )
            return

        # ★ 親衛隊レベル一覧（管理者用）
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
                    if member is None:
                        try:
                            member = await message.guild.fetch_member(uid_int)
                        except Exception:
                            member = None

                if member:
                    lines.append(f"- {member.display_name} (ID: {uid_str}) → Lv.{lv}")
                else:
                    lines.append(f"- ID: {uid_str} → Lv.{lv}")

            await message.channel.send("\n".join(lines))
            return

        # ★ 親衛隊レベル設定（管理者用）: @指定 → 次の発言でレベル数値を入力
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

        # ★ 親衛隊レベル削除（管理者用）
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

        # ★ 好感度設定編集メニュー
        if "好感度編集" in content:
            await message.channel.send(
                f"{message.author.mention} 好感度の設定をどうする？\n"
                "- `好感度設定確認` … レベル閾値とアクションごとのXPを表示\n"
                "- `好感度アクション設定 アクション名 数値` … 例: `好感度アクション設定 talk 5`\n"
                "- `好感度レベル設定 レベル 数値` … 例: `好感度レベル設定 3 80`（Lv.3に必要なXPを80に）\n"
                "- `データ管理終了` … モード終了"
            )
            return

        # ★ 好感度設定確認
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

        # ★ 好感度アクション設定
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

        # ★ 好感度レベル設定
        if content.startswith("好感度レベル設定"):
            parts = content.split()
            if len(parts) < 3:
                await message.channel.send(
                    f"{message.author.mention} `好感度レベル設定 レベル 数値` の形で教えて？\n"
                    "例: `好感度レベル設定 3 80`"
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
            # リストを必要な長さまで伸ばす
            while len(thresholds) <= lv:
                thresholds.append(thresholds[-1] + 10)
            thresholds[lv] = xp_need
            cfg["level_thresholds"] = thresholds
            save_affection_config(cfg)

            await message.channel.send(
                f"{message.author.mention} Lv.{lv} に必要なXPを **{xp_need}** に設定したわ。"
            )
            return

        if "管理者編集" in content:
            await message.channel.send(
                f"{message.author.mention} 管理者をどうしたい？\n"
                "- `管理者追加` … 新しく管理者を追加\n"
                "- `管理者削除` … 既存の管理者を外す\n"
                "- `データ管理終了` … モード終了"
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

        await message.channel.send(
            f"{message.author.mention} ごめんね、そのコマンドはまだ知らないの…。\n"
            "いま使えるのは\n"
            "- `ニックネーム確認`\n"
            "- `管理者編集`\n"
            "- `親衛隊レベル編集`\n"
            "- `好感度編集`\n"
            "- `データ管理終了`\n"
            "あたりね。"
        )
        return

    # =====================
    # ⭐ データ管理モードに入る
    # =====================
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
            "- `データ管理終了` でこのモードを終わるわ。"
        )
        return

    # =====================
    # ⭐ 一般ユーザー用：自分の親衛隊レベル確認
    # =====================
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

    # =====================
    # ⭐ 一般ユーザー用：好感度チェック
    # =====================
    if content in ["好感度", "好感度チェック", "キュレネ好感度"]:
        xp, level_val = get_user_affection(user_id)
        cfg = load_affection_config()
        thresholds = cfg.get("level_thresholds", [0])
        # 次のレベルまで
        if level_val + 1 < len(thresholds):
            next_xp = thresholds[level_val + 1]
            remain = max(0, next_xp - xp)
            msg = (
                f"あなたの好感度は **Lv.{level_val}** で、累計 **{xp} XP** ね♪\n"
                f"次のLv.{level_val + 1} までは、あと **{remain} XP** 必要よ。"
            )
        else:
            msg = (
                f"あなたの好感度は **Lv.{level_val}**（累計 {xp} XP）よ♪\n"
                "これ以上は数えなくてもいいくらい、十分仲良しってことかしら？"
            )
        await message.channel.send(f"{message.author.mention} {msg}")
        return

    # =====================
    # あだ名登録（開始）
    # =====================
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

    # =====================
    # あだ名変更（開始）
    # =====================
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

    # =====================
    # あだ名削除
    # =====================
    if content.startswith("あだ名削除"):
        delete_nickname(user_id)
        waiting_for_nickname.discard(user_id)
        waiting_for_rename.discard(user_id)
        await message.channel.send(
            f"{message.author.mention} わかったわ。元の呼び方に戻すわね。"
        )
        return

    # =====================
    # ⭐ じゃんけん開始コマンド
    # =====================
    if "じゃんけん" in content:
        # 一発指定（例: じゃんけん グー）
        hand = parse_hand(content)
        if hand:
            bot_hand = random.choice(JANKEN_HANDS)
            result = judge_janken(hand, bot_hand)
            flavor = get_rps_line(result)
            await message.channel.send(
                f"{message.author.mention} {name} は **{hand}**、あたしは **{bot_hand}** よ。\n{flavor}"
            )

            # 好感度XP付与
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

        # 手はまだ → 手入力待ちモードへ
        waiting_for_rps_choice.add(user_id)
        await message.channel.send(
            f"{message.author.mention} じゃんけんをしましょう♪ グー / チョキ / パー、どれにするかしら？"
        )
        return

    # =====================
    # メンションのみ（本文なし）
    # =====================
    if content == "":
        xp, level_val = get_user_affection(user_id)
        reply = get_cyrene_reply("", level_val)
        await message.channel.send(f"{message.author.mention} {reply}")

        # 好感度XP（会話）付与
        cfg = load_affection_config()
        delta = int(cfg.get("xp_actions", {}).get("talk", 0))
        add_affection_xp(user_id, delta, reason="talk")
        return

    # =====================
    # 通常応答
    # =====================
    xp, level_val = get_user_affection(user_id)
    reply = get_cyrene_reply(content, level_val)
    await message.channel.send(f"{message.author.mention} {name}、{reply}")

    # 好感度XP（会話）付与
    cfg = load_affection_config()
    delta = int(cfg.get("xp_actions", {}).get("talk", 0))
    add_affection_xp(user_id, delta, reason="talk")

# =====================
# 実行
# =====================
client.run(DISCORD_TOKEN)
