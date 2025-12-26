# cyrene.py
import os
import re
import json
import random
from pathlib import Path

import discord
from dotenv import load_dotenv

from lines import get_cyrene_reply, get_rps_line  # ★ ここで追加

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
# 会話状態管理
# =====================
waiting_for_nickname = set()      # 新規あだ名入力待ち
waiting_for_rename = set()        # あだ名変更入力待ち
admin_data_mode = set()           # データ管理モード中のユーザー
waiting_for_admin_add = set()     # 管理者追加で @待ち
waiting_for_admin_remove = set()  # 管理者削除で @待ち
waiting_for_rps_choice = set()    # じゃんけんの手入力待ち

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
    is_mentioned = client.user in message.mentions

    # どのモードでもない＋メンションもない → 完全無視
    if not (is_mentioned or is_waiting_nick or is_waiting_admin or is_waiting_rps or is_admin_mode):
        return

    # メンション（bot本人）だけ削除したテキスト
    content = re.sub(rf"<@!?{client.user.id}>", "", message.content).strip()

    # あだ名と表示名
    nickname = get_nickname(user_id)
    name = nickname if nickname else message.author.display_name

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

                if member:
                    lines.append(f"- {member.display_name} (ID: {uid_str}) → {nick}")
                else:
                    lines.append(f"- 不明ユーザー (ID: {uid_str}) → {nick}")

            await message.channel.send("\n".join(lines))
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
            "- `管理者追加`\n"
            "- `管理者削除`\n"
            "- `データ管理終了`\n"
            "よ。"
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
            "- `データ管理終了` でこのモードを終わるわ。"
        )
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
        reply = get_cyrene_reply("")
        await message.channel.send(f"{message.author.mention} {reply}")
        return

    # =====================
    # 通常応答
    # =====================
    reply = get_cyrene_reply(content)
    await message.channel.send(f"{message.author.mention} {name}、{reply}")

# =====================
# 実行
# =====================
client.run(DISCORD_TOKEN)
