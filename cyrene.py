# cyrene.py
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
# ニックネーム保存
# =====================
DATA_FILE = Path("nicknames.json")

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

def set_nickname(user_id: int, nickname: str):
    data = load_data()
    data[str(user_id)] = nickname
    save_data(data)

def delete_nickname(user_id: int):
    data = load_data()
    if str(user_id) in data:
        del data[str(user_id)]
        save_data(data)

def get_nickname(user_id: int):
    return load_data().get(str(user_id))

# =====================
# Discord
# =====================
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

def strip_bot_mention(text: str, bot_id: int) -> str:
    return re.sub(rf"<@!?{bot_id}>", "", text).strip()

def is_mention_to_me(message: discord.Message) -> bool:
    return client.user is not None and client.user in message.mentions

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

    # bot本人へのメンション以外は無視
    if not is_mention_to_me(message):
        return

    content = strip_bot_mention(message.content, client.user.id)

    user_id = message.author.id
    nickname = get_nickname(user_id)
    call_name = nickname if nickname else message.author.display_name

    # =====================
    # 返信文は必ず1つだけ作る
    # =====================
    reply_text = None

    # -------- あだ名登録 --------
    if content.startswith("あだ名登録"):
        new_name = content.replace("あだ名登録", "", 1).strip()
        if not new_name:
            reply_text = f"{message.author.mention} あたし、どう呼べばいいの？"
        else:
            set_nickname(user_id, new_name)
            reply_text = f"{message.author.mention} ふふ…これからは「{new_name}」って呼ぶわね♪"

    # -------- あだ名変更 --------
    elif content.startswith("あだ名変更"):
        new_name = content.replace("あだ名変更", "", 1).strip()
        if not new_name:
            reply_text = f"{message.author.mention} 新しい呼び名、教えて？"
        else:
            set_nickname(user_id, new_name)
            reply_text = f"{message.author.mention} 了解♪ 今日から「{new_name}」よ。"

    # -------- あだ名削除 --------
    elif content.startswith("あだ名削除"):
        delete_nickname(user_id)
        reply_text = f"{message.author.mention} わかったわ。元の呼び方に戻すわね。"

    # -------- @だけ（内容なし） --------
    elif content == "":
        cy = get_cyrene_reply("")
        reply_text = f"{message.author.mention} {call_name}、{cy}"

    # -------- 通常会話 --------
    else:
        cy = get_cyrene_reply(content)
        reply_text = f"{message.author.mention} {call_name}、{cy}"

    # =====================
    # 送信（必ず1回）
    # =====================
    if reply_text:
        await message.channel.send(reply_text)

# =====================
# 実行
# =====================
client.run(DISCORD_TOKEN)
