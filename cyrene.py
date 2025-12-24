# cyrene.py
import os
import re
import json
from pathlib import Path

import discord
from dotenv import load_dotenv

from lines import get_cyrene_reply

# ===== env =====
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "").strip()
if not DISCORD_TOKEN:
    raise RuntimeError("DISCORD_TOKEN is not set")

# ===== nicknames =====
DATA_FILE = Path("nicknames.json")

def load_data():
    if not DATA_FILE.exists():
        return {}
    try:
        return json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}

def save_data(data):
    DATA_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

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

# ===== discord =====
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

def strip_bot_mention(text: str, bot_id: int) -> str:
    # <@id> と <@!id> を削除
    return re.sub(rf"<@!?{bot_id}>", "", text).strip()

def is_mention_to_me(message: discord.Message) -> bool:
    # ロールメンション等で反応しない（bot本人へのメンションのみ）
    return (client.user is not None) and (client.user in message.mentions)

@client.event
async def on_ready():
    print(f"ログイン成功: {client.user} ({client.user.id})")

@client.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    if not is_mention_to_me(message):
        return

    content = strip_bot_mention(message.content, client.user.id)

    # ログ（必要なら）
    print(f"RECV: {message.author}({message.author.id}) content='{content}' raw='{message.content}'")

    user_id = message.author.id
    nickname = get_nickname(user_id)
    name = nickname if nickname else message.author.display_name

    # 返信は「必ず1回だけ」送る
    reply_text = None

    # ========= あだ名コマンド =========
    # 形式:
    #   あだ名登録 〇〇
    #   あだ名変更 〇〇
    #   あだ名削除
    if content.startswith("あだ名登録"):
        new_name = content.replace("あだ名登録", "", 1).strip()
        if not new_name:
            reply_text = f"{message.author.mention} あたし、どう呼べばいいの？"
        else:
            set_nickname(user_id, new_name)
            reply_text = f"{message.author.mention} ふふ…これからは「{new_name}」って呼ぶわね♪"

    elif content.startswith("あだ名変更"):
        new_name = content.replace("あだ名変更", "", 1).strip()
        if not new_name:
            reply_text = f"{message.author.mention} 新しい呼び名、教えて？"
        else:
            set_nickname(user_id, new_name)
            reply_text = f"{message.author.mention} 了解♪ 今日から「{new_name}」よ。"

    elif content.startswith("あだ名削除"):
        delete_nickname(user_id)
        reply_text = f"{message.author.mention} わかったわ。元の呼び方に戻すわね。"

    # ========= 通常応答 =========
    else:
        # 「何も書かなかった時」は waiting だけ
        if content == "":
            cy = get_cyrene_reply("")
            reply_text = f"{message.author.mention} {name}、{cy}"
        else:
            cy = get_cyrene_reply(content)
            reply_text = f"{message.author.mention} {name}、{cy}"

    # ここで1回だけ送信
    if reply_text is not None:
        await message.channel.send(reply_text)

client.run(DISCORD_TOKEN)
