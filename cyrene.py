# cyrene.py（これを1回コピペでOK）
import os
import re
import json
from pathlib import Path

import discord
from dotenv import load_dotenv

from lines import get_cyrene_reply

# =====================
# 環境変数
# =====================
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "").strip()
if not DISCORD_TOKEN:
    raise RuntimeError("DISCORD_TOKEN is not set")

# =====================
# Discord
# =====================
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

# =====================
# あだ名保存（永続: nicknames.json）
# =====================
DATA_FILE = Path("nicknames.json")

def load_data() -> dict:
    if not DATA_FILE.exists():
        return {}
    try:
        return json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except Exception:
        # 壊れてたら初期化（落ちないように）
        return {}

def save_data(data: dict) -> None:
    DATA_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

def set_nickname(user_id: int, nickname: str) -> None:
    data = load_data()
    data[str(user_id)] = nickname
    save_data(data)

def delete_nickname(user_id: int) -> None:
    data = load_data()
    if str(user_id) in data:
        del data[str(user_id)]
        save_data(data)

def get_nickname(user_id: int) -> str | None:
    return load_data().get(str(user_id))

# =====================
# あだ名入力待ち（会話状態）
# =====================
waiting_for_nickname: set[int] = set()
waiting_for_rename: set[int] = set()

# =====================
# 起動
# =====================
@client.event
async def on_ready():
    print(f"ログイン成功: {client.user} ({client.user.id})")

# =====================
# メッセージ処理
# =====================
@client.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    # bot本人へのメンション以外は無視（ロールメンション対策）
    if not client.user or client.user not in message.mentions:
        return

    # メンション削除（botのみ）
    content = re.sub(rf"<@!?{client.user.id}>", "", message.content).strip()

    user_id = message.author.id
    nickname = get_nickname(user_id)
    name = nickname if nickname else message.author.display_name  # 表示名はそのまま（重複させない）

    # =====================
    # ✅ あだ名入力待ち（登録）
    # =====================
    if user_id in waiting_for_nickname:
        new_name = content.strip()
        if not new_name:
            await message.channel.send(f"{message.author.mention} もう一度、呼び名を教えて？")
            return

        set_nickname(user_id, new_name)
        waiting_for_nickname.discard(user_id)

        await message.channel.send(f"{message.author.mention} ふふ…これからは「{new_name}」って呼ぶわね♪")
        return

    # =====================
    # ✅ あだ名入力待ち（変更）
    # =====================
    if user_id in waiting_for_rename:
        new_name = content.strip()
        if not new_name:
            await message.channel.send(f"{message.author.mention} 新しい呼び名、もう一度教えて？")
            return

        set_nickname(user_id, new_name)
        waiting_for_rename.discard(user_id)

        await message.channel.send(f"{message.author.mention} 了解♪ 今日から「{new_name}」よ。")
        return

    # =====================
    # あだ名登録（開始）
    # =====================
    if content.startswith("あだ名登録"):
        # 形式: あだ名登録 <名前> も許可
        new_name = content.replace("あだ名登録", "", 1).strip()
        if not new_name:
            waiting_for_nickname.add(user_id)
            await message.channel.send(f"{message.author.mention} あたし、どう呼べばいいの？")
            return

        set_nickname(user_id, new_name)
        await message.channel.send(f"{message.author.mention} ふふ…これからは「{new_name}」って呼ぶわね♪")
        return

    # =====================
    # あだ名変更（開始）
    # =====================
    if content.startswith("あだ名変更"):
        new_name = content.replace("あだ名変更", "", 1).strip()
        if not new_name:
            waiting_for_rename.add(user_id)
            await message.channel.send(f"{message.author.mention} 新しい呼び名、教えて？")
            return

        set_nickname(user_id, new_name)
        await message.channel.send(f"{message.author.mention} 了解♪ 今日から「{new_name}」よ。")
        return

    # =====================
    # あだ名削除
    # =====================
    if content.startswith("あだ名削除"):
        delete_nickname(user_id)
        waiting_for_nickname.discard(user_id)
        waiting_for_rename.discard(user_id)
        await message.channel.send(f"{message.author.mention} わかったわ。元の呼び方に戻すわね。")
        return

    # =====================
    # 何も書かなかった時は waiting だけ
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
