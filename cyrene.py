import os
import re
import discord
from dotenv import load_dotenv
from lines import get_cyrene_reply

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
if not DISCORD_TOKEN:
    raise RuntimeError("DISCORD_TOKEN is not set")

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f"ログイン成功: {client.user}")

@client.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    # ログ（Renderで確認可能）
    print(f"RECV from {message.author} ({message.author.id}): {message.content!r}")

    # Botへのメンション検出
    if client.user and client.user in message.mentions:
        # メンション部分を削除
        content = re.sub(rf"<@!?{client.user.id}>", "", message.content).strip()

        reply = get_cyrene_reply(content)

        # @したユーザーを認識して返信
        await message.channel.send(
            f"{message.author.mention} {reply}"
        )

client.run(DISCORD_TOKEN)
