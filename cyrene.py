# cyrene.py
import os
import re
import discord
from dotenv import load_dotenv
from lines import get_cyrene_reply
from pathlib import Path

env_path = Path(__file__).with_name(".env")
load_dotenv(dotenv_path=env_path, override=True)

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "").strip()

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f"ログイン成功: {client.user}")

CYRENE_ROLE_ID = 1453039819650498592  # ロールID（<@&...> の数字）

@client.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    my_id = client.user.id

    # ① Bot本人メンション判定
    mentioned_bot = (
        client.user in message.mentions
        or f"<@{my_id}>" in message.content
        or f"<@!{my_id}>" in message.content
    )

    # ② ロールメンション判定
    mentioned_role = f"<@&{CYRENE_ROLE_ID}>" in message.content

    # ③ どちらでもなければ無視
    if not (mentioned_bot or mentioned_role):
        return

    # ④ メンション部分を削除
    content = message.content
    content = re.sub(rf"<@!?{my_id}>", "", content)
    content = re.sub(rf"<@&{CYRENE_ROLE_ID}>", "", content)
    content = content.strip()

    # ⑤ 中身が空なら空文字（lines.py 側で waiting 扱い）
    if not content:
        content = ""

    reply = get_cyrene_reply(content)
    await message.channel.send(reply)


client.run(DISCORD_TOKEN)
