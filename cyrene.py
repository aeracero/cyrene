import os
import re
import json
from pathlib import Path
import discord
from dotenv import load_dotenv
from lines import get_cyrene_reply

# =====================
# 環境変数読み込み
# =====================
load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
if not DISCORD_TOKEN:
    raise RuntimeError("DISCORD_TOKEN is not set")

# =====================
# Discord 設定
# =====================
intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)

# =====================
# あだ名保存（JSON）
# =====================
NICKNAME_FILE = Path("nicknames.json")

def load_nicknames():
    if not NICKNAME_FILE.exists():
        return {}
    return json.loads(NICKNAME_FILE.read_text(encoding="utf-8"))

def save_nicknames(data):
    NICKNAME_FILE.write_text(
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

# =====================
# 起動時
# =====================
@client.event
async def on_ready():
    print(f"ログイン成功: {client.user}")

# =====================
# メッセージ受信
# =====================
@client.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    # ログ（Render Logs で確認できる）
    print(f"RECV from {message.author} ({message.author.id}): {message.content!r}")

    # Botへのメンション検出
    if client.user and client.user in message.mentions:
        # メンション部分を削除
        content = re.sub(rf"<@!?{client.user.id}>", "", message.content).strip()

        # ==========
        # あだ名登録
        # ==========
        if content.startswith("あだ名登録"):
            nickname = content.replace("あだ名登録", "").strip()

            if nickname == "":
                await message.channel.send(
                    f"{message.author.mention} あたし、どう呼べばいいの？"
                )
                return

            set_nickname(message.author.id, nickname)
            await message.channel.send(
                f"{message.author.mention} ふふ…これからは「{nickname}」って呼ぶわね♪"
            )
            return

        # ==========
        # 通常返信
        # ==========
        nickname = get_nickname(message.author.id)
        name = nickname if nickname else message.author.display_name

        reply = get_cyrene_reply(content)

        await message.channel.send(
            f"{message.author.mention} {name}、{reply}"
        )

# =====================
# 起動
# =====================
client.run(DISCORD_TOKEN)
