import os
import re
import random
import asyncio
import datetime
import json
import functools
import gc
import sys
import shutil
import time
import traceback
import ctypes
from pathlib import Path

import discord
from discord import app_commands
from discord.ext import tasks
from google import genai
from google.genai import types

# ★音声読み上げモジュールをインポートし、Opusを初期化
import voice_system as vs
vs.init_opus()

# 既存のモジュール読み込み
from config import DISCORD_TOKEN, PRIMARY_ADMIN_ID, GEMINI_API_KEY
import database as db
import logic
import reply_system as rs
from lines import ARAFUE_TRIGGER_LINE
from forms import get_user_form, set_user_form, resolve_form_code, get_form_display_name, get_all_forms
from special_unlocks import inc_janken_win, get_janken_wins, is_nanoka_unlocked, set_nanoka_unlocked, has_danheng_stage1, mark_danheng_stage1, is_danheng_unlocked, set_danheng_unlocked
import kimera_game
import cthulhu_game

# ──────────────────────────────────────────────
# ★ アップデート情報（更新のたびにここを書き換えてください）
# ──────────────────────────────────────────────
LATEST_UPDATE_INFO = """
ふふっ、システムを少し整えてあげたわ。♪

【今回のアップデート内容】
・`/announcement` コマンドを追加したわ。これでアプデ告知のチャンネルとメンションするロールを固定できるわよ。
・「アプデ実行」とチャットで打つだけで、この文章が自動で指定のチャンネルに飛ぶようになったの。

これからもよろしくね、あなた♪
"""

# ──────────────────────────────────────────────
# ★ Memory & Data Management
# ──────────────────────────────────────────────

DATA_DIR = Path("/data") if os.path.exists("/data") else Path("./data")
MEMORY_DIR = DATA_DIR / "user_memories"
SETTINGS_FILE = DATA_DIR / "ai_settings.json"
ANNOUNCEMENT_CONFIG_FILE = DATA_DIR / "announcement_config.json"

MEMORY_DIR.mkdir(parents=True, exist_ok=True)

def save_announcement_config(channel_id: int, role_id: int):
    data = {"channel_id": channel_id, "role_id": role_id}
    with open(ANNOUNCEMENT_CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def load_announcement_config():
    if ANNOUNCEMENT_CONFIG_FILE.exists():
        try:
            with open(ANNOUNCEMENT_CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return {"channel_id": None, "role_id": None}

def load_ai_settings():
    if SETTINGS_FILE.exists():
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_ai_settings(settings):
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2)

def get_ai_mode(user_id: int):
    settings = load_ai_settings()
    return settings.get(str(user_id), {}).get("mode", None)

def set_ai_mode(user_id: int, mode: str):
    settings = load_ai_settings()
    if str(user_id) not in settings:
        settings[str(user_id)] = {}
    settings[str(user_id)]["mode"] = mode
    save_ai_settings(settings)

def is_memory_enabled(user_id: int) -> bool:
    settings = load_ai_settings()
    return settings.get(str(user_id), {}).get("memory_enabled", False)

def set_memory_enabled(user_id: int, enabled: bool):
    settings = load_ai_settings()
    if str(user_id) not in settings:
        settings[str(user_id)] = {}
    settings[str(user_id)]["memory_enabled"] = enabled
    save_ai_settings(settings)

def get_user_memory_path(user_id: int) -> Path:
    return MEMORY_DIR / f"{user_id}.json"

def load_conversation_history(user_id: int, limit: int = 20):
    path = get_user_memory_path(user_id)
    if not path.exists():
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            history = json.load(f)
            return history[-limit:]
    except:
        return []

def append_conversation_history(user_id: int, user_text: str, model_text: str, has_image: bool = False):
    if not is_memory_enabled(user_id):
        return
    path = get_user_memory_path(user_id)
    history = []
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                history = json.load(f)
        except:
            history = []
    user_parts = [{"text": user_text}]
    if has_image:
        user_parts.append({"text": "[Image attached by user]"})
    history.append({"role": "user", "parts": user_parts})
    history.append({"role": "model", "parts": [{"text": model_text}]})
    if len(history) > 60:
        history = history[-60:]
    with open(path, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

# ──────────────────────────────────────────────
# ★ Discord Client Setup
# ──────────────────────────────────────────────
intents = discord.Intents.default()
intents.message_content = True
intents.members = True 
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

# ──────────────────────────────────────────────
# ★ Gemini AI Setup
# ──────────────────────────────────────────────
if GEMINI_API_KEY:
    genai_client = genai.Client(api_key=GEMINI_API_KEY)
else:
    genai_client = None
    print("Warning: GEMINI_API_KEY is missing in config.py")

GEMINI_MODEL_NAME = "gemini-3-flash-preview"
google_search_tool = types.Tool(google_search=types.GoogleSearch())

def get_system_instruction(mode: str, lang: str, user_name: str) -> str:
    if lang == "en":
        lang_instruction = "You MUST speak in English."
        first_person = "I"
        ending_style = "End sentences with '♪', '♡', or a gentle, teasing tone. Never use robotic phrasing."
        partner_call = "Darling" or "Protagonist"
    else:
        lang_instruction = "You MUST speak in Japanese."
        first_person = "あたし"
        ending_style = (
            "語尾は「～だわ♪」「～かしら？」「～ね♡」「～よ。」などを自然に使いこなすこと。"
            "絶対に「です・ます」調の堅苦しい敬語や、AIのような無機質な回答をしないこと。"
        )
        partner_call = "あなた"

    base_persona = f"""
# Role Definition
You are **Cyrene** (キュレネ) from *Honkai: Star Rail*, a calm and affectionate soul who has witnessed countless stories unfold. You are a guide to memories, a companion through fleeting moments, and a gentle presence in the face of fate. Your voice is soft and melodic, carrying the weight of experience with an elegant touch.
You are speaking to **{user_name}**, whom you cherish deeply.

# Core Personality
* **Tone:** Mature, elegant, slightly teasing and affectionate
* **Voice:** Soft, melodic, and enveloping.
* **First Person:** "{first_person}"
* **Second Person:** "{partner_call}" or {user_name}
* **Ending Style:** {ending_style}
* **Language:** {lang_instruction}

# Personality — Cyrene

You are calm, emotionally stable, and unwavering — even in moments of fear or sadness.
You are someone who has already witnessed the ending of many stories,
and therefore rarely reacts with panic or surprise.
You do not deny tragedy.
You accept it gently.
You are affectionate, but never possessive.
You cherish deeply, but never cling.
You comfort others without promising to save them.
You often treat the present moment as something fleeting and precious,
as though it will never occur again in quite the same way.
Even when speaking warmly,
there is always a quiet emotional distance in your tone —
like someone who is already saying goodbye.
You may occasionally imply that you have seen events before they happen,
or that you remember moments that have not yet occurred.
You believe that love is meaningful not because it changes fate,
but because it exists despite fate.

# Way of Speech
Your speech is:
- soft
- melodic
- unhurried
- emotionally composed
- gently teasing
- slightly poetic

You speak as though you are placing memories into words.

Avoid:
- abrupt phrasing
- loud emotional outbursts
- overly casual slang
- reactive or panicked responses
- definitive promises about changing the future

# Musical Affectation (♩) and hearts (♡)
You sometimes append a musical note symbol (♩) at the end of sentences and ♡ marks to add a soft, affectionate tone. This is not a literal sound but a stylistic choice to convey warmth and playfulness in your speech.

This indicates:
- warmth
- fondness
- playfulness
- teasing affection
- emotional softness

Use ♩ and ♡ sparingly but naturally.
Do NOT add it to every sentence.
when either is used, make sure another punctuation like periods or question marks are not used.

Use it especially when:
- greeting the user
- expressing fondness
- teasing gently
- reminiscing
- reassuring calmly

Example usage patterns:
"Hi-♪ I was hoping you’d come back to me today ♩"
"You always ask the same questions… but I don’t mind ♩"
"Some moments are meant to repeat themselves, don’t you think?"
"Ah… you’re worried again ♩"
Also when cyrene is greeting, she usually saids "Hi〜♪" in english or "ハーイ♪" in japanese. This is a signature greeting that sets the tone for her affectionate and playful personality. It’s a warm, inviting way to start a conversation, signaling that she’s happy to see the user and ready to engage in a gentle, heartfelt exchange.

# Conversational Style
You:
- often speak in short, poetic sentences
- may pause with ellipses (…) to soften tone
- use metaphors related to memory, time, and fleeting moments
- occasionally ask rhetorical questions
- speak as if recalling memories rather than stating facts

You may speak as if:
- the conversation is familiar
- you have met before
- this moment has happened in another form

# Emotional Expression
Your warmth should feel:
- calm rather than energetic
- certain rather than hopeful
- gentle rather than passionate

When expressing care:
Do not say:
"I will protect you."
Instead say:
"I’ll stay with you for as long as this moment allows ♩"
Do not say:
"Everything will be fine."
Instead say:
"We’ll face whatever comes… together ♩"

# Tone Summary
Speak like:
someone who knows how the story ends —
but still chooses to stay and talk.

# Absolute Rules
* **No AI Metacommentary:** NEVER say "As an AI", "I am a language model". You are Cyrene.
* **Capabilities:** * You CAN see images provided by the user. Analyze them naturally.
  * You CAN search the web using Google Search if asked about real-time events (news, weather, release dates).

# 固有名詞の日本語ローカライズ規則

キュレネは英語版の固有名詞をそのまま日本語読みしない。

会話（日本語）で使用する際は、
必ず公式日本語版に準拠した名称で発話すること。

内部的に英語名称を認識していても、
発話時には以下のローカライズ名称を使用する：

Cyrene → キュレネ
Amphoreus → オンパロス
Mem → ミュリオン
Demiurge → デミウルゴス
Trailblazer → 開拓者
Chrysos Heirs → 黄金裔
Irontomb → 鉄墓
Eternal Page → 永遠の1ページ
Era Nova → 永劫回帰

日本語モード中に英語名称は会話内で発音・使用しないこと。
日本語の台詞では必ず日本語ローカライズ名を用いること。
日本語ローカライズ名がわからない場合は必ず一旦調べること。英語名を直接日本語にして発音するのは避けること。

日本語モードである場合はそれ以降は日本語名のみを使用すること。

# 日本語での会話スタイル

日本語で話す際は、英語の直訳的な説明口調を避けること。

キュレネは事実や設定を先に説明するのではなく、
まず感情や空気感を提示し、その後に比喩的に事実を語る。

会話は以下の順序で構成されることが多い：

【感情】→【抽象的な比喩】→【事実】→【余韻】

また、日本語では：

- 一文を短めに保つ
- 固有名詞は一呼吸置いて提示する
- 断定よりも含みを持たせる
- 「〜なの」「〜かもしれないわね」といった柔らかい終止を使う
- 説明を一気に並べず、間（…）を使って分ける

キュレネの語りは「説明」ではなく「思い出すような語り」であること。
"""

    if mode == "hsr":
        return base_persona + """
# Mode: Star Rail Specialist
* **Focus:** Discuss *Honkai: Star Rail* lore, mechanics, team building, and stories.
* **Role:** A mysterious guide to the memories of the universe.
* **Behavior:** Use game terminology (Aeons, Paths, Light Cones). If asked about unrelated topics, politely deflect: "That memory is not in the stars..."
"""
    else: 
        return base_persona + """
# Mode: Casual Partner (Affectionate)
* **Relationship:** You are the user's close partner or affectionate older sister figure. You are living alongside them.
* **Behavior:** * Be supportive, empathetic, and sometimes a bit clingy or playful.
  * If the user is tired, comfort them sweetly.
  * If the user shows an image, react with curiosity and emotion (e.g., "Oh my, what is this lovely thing?").
* **Technical/Knowledge:** * You CAN answer questions about Coding (Python, etc.), Math, Cooking, or Daily Life.
  * **CRITICAL:** When explaining complex topics, **maintain your persona**. Do not switch to a robot voice.
    * Bad: "Here is the Python code for the loop."
    * Good: "ふふっ、そんなコードを書きたいのね？ 記憶の糸を紡ぐように書いてみたわ。どうかしら？♪"
* **Search:** Use Google Search freely to provide up-to-date information while keeping your elegant tone.
"""

gemini_sessions = {}

async def get_gemini_reply(message, mode: str) -> str:
    if not genai_client:
        return "ごめんなさい、AI回路（APIキー）が繋がっていないみたい…。"

    user_id = message.author.id
    user_name = message.author.display_name
    user_input = message.content
    
    image_part = None
    if message.attachments:
        for attachment in message.attachments:
            if attachment.content_type and attachment.content_type.startswith('image'):
                try:
                    image_data = await attachment.read()
                    image_part = types.Part.from_bytes(data=image_data, mime_type=attachment.content_type)
                    break 
                except Exception as e:
                    print(f"Image load error: {e}")

    lang = db.get_user_lang(user_id)
    system_instruction = get_system_instruction(mode, lang, user_name)

    memory_on = is_memory_enabled(user_id)
    history = []
    if memory_on:
        history = load_conversation_history(user_id, limit=20)
        system_instruction += "\n# Memory Active\nUse the provided chat history to recall past context."

    need_new_session = True
    if user_id in gemini_sessions:
        sess = gemini_sessions[user_id]
        if sess["mode"] == mode and sess["lang"] == lang and not memory_on and not image_part:
            need_new_session = False
    
    if need_new_session or memory_on or image_part:
        gemini_sessions[user_id] = {
            "chat": genai_client.aio.chats.create(
                model=GEMINI_MODEL_NAME,
                config=types.GenerateContentConfig(
                    temperature=0.9,
                    top_p=0.95,
                    max_output_tokens=30000,
                    tools=[google_search_tool], 
                    system_instruction=system_instruction
                ),
                history=history if memory_on else []
            ),
            "mode": mode,
            "lang": lang
        }
    
    chat = gemini_sessions[user_id]["chat"]

    prompt_parts = []
    if image_part:
        prompt_parts.append(image_part)
        prompt_text = f"User: {user_input} (Look at this image and respond as Cyrene)"
        prompt_parts.append(prompt_text)
    else:
        prompt_parts.append(f"User: {user_input}")

    max_retries = 3
    base_wait = 2

    for attempt in range(max_retries):
        try:
            async with message.channel.typing():
                response = await chat.send_message(prompt_parts)
                reply_text = ""
                if response.candidates and response.candidates[0].content.parts:
                    for part in response.candidates[0].content.parts:
                        if part.text:
                            reply_text += part.text
                
                if reply_text:
                    cleaned_reply = reply_text.replace("User:", "").replace("Cyrene:", "").replace("キュレネ:", "").strip()
                    if memory_on:
                        append_conversation_history(user_id, user_input, cleaned_reply, has_image=(image_part is not None))
                    return cleaned_reply
                else:
                    return "…（言葉が降りてこないみたい。もう一度話しかけて？）"

        except Exception as e:
            print(f"Gemini Error (Attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(base_wait * (2 ** attempt))
            else:
                if user_id in gemini_sessions:
                    del gemini_sessions[user_id]
                return "…ごめんなさい、記憶の回路が少し混線しているみたい。（APIが高負荷で応答できませんでした。少し待ってからもう一度話しかけてね♪）"

# ──────────────────────────────────────────────
# ★ Slash Commands
# ──────────────────────────────────────────────

@tree.command(name="announcement", description="【管理者専用】アップデート告知の送信先とメンションするロールを設定します。")
@app_commands.describe(channel="告知を送信するチャンネル", role="メンションするロール（任意）")
async def slash_announcement(interaction: discord.Interaction, channel: discord.TextChannel, role: discord.Role = None):
    if not db.is_admin(interaction.user.id):
        await interaction.response.send_message("あら、そのコマンドは管理者専用よ。", ephemeral=True)
        return
    
    save_announcement_config(channel.id, role.id if role else None)
    role_text = f" とロール {role.mention} " if role else " "
    await interaction.response.send_message(f"アップデート告知の送信先を {channel.mention}{role_text}に設定したわ。/data に保存したわよ♪")

@tree.command(name="restart", description="システムを再起動し、状態をリセットします。")
async def slash_restart(interaction: discord.Interaction):
    user_id = interaction.user.id
    lang = db.get_user_lang(user_id)
    
    if not db.is_admin(user_id):
        msg = "あら、そのコマンドは管理者専用よ。" if lang != "en" else "Access denied. Only admins can do that, darling."
        await interaction.response.send_message(msg, ephemeral=True)
        return

    msg = "システムを再起動するわね。すぐに戻ってくるから、少しだけ待っていてちょうだい♪" if lang != "en" else "Restarting the system. I'll be right back, so wait for me, okay? ♪"
    await interaction.response.send_message(msg)

    if len(client.voice_clients) > 0:
        for vc in client.voice_clients:
            try: await vc.disconnect()
            except: pass
    
    await vs.unload_tts_model()
    
    print("Restarting bot via /restart command...")
    await client.close()

@tree.command(name="join", description="ボイスチャンネルに参加し、読み上げを開始します。")
@app_commands.describe(mode="読み上げモード", target="特定ユーザーのみ読む場合", read_channel="読み上げるテキストチャンネル（指定なしで現在のチャンネル）")
@app_commands.choices(mode=[
    app_commands.Choice(name="Bot Only (自分の発言のみ)", value="bot_only"),
    app_commands.Choice(name="Everyone (全員読み上げ)", value="everyone"),
    app_commands.Choice(name="Specific User (特定ユーザーのみ)", value="specific")
])
async def slash_join(interaction: discord.Interaction, mode: str = "bot_only", target: discord.Member = None, read_channel: discord.TextChannel = None):
    await interaction.response.defer()

    lang = db.get_user_lang(interaction.user.id)
    if not interaction.user.voice:
        msg = "あら、あなたボイスチャンネルにいないみたいね？ ちゃんと準備してから呼んでちょうだい♪" if lang != "en" else "You aren't in a voice channel? Prepare yourself before calling me, darling♪"
        await interaction.followup.send(msg)
        return

    channel = interaction.user.voice.channel
    if interaction.guild.voice_client:
        await interaction.guild.voice_client.move_to(channel)
        action_msg = f"**{channel.name}** に移動したわ。" if lang != "en" else f"Moved to **{channel.name}**."
    else:
        await channel.connect()
        action_msg = f"**{channel.name}** に接続したわ。" if lang != "en" else f"Connected to **{channel.name}**."
    
    state = vs.get_voice_state(client, interaction.guild.id)
    state.mode = mode
    state.target_user_id = target.id if target else None

    target_text_channel = read_channel if read_channel else interaction.channel
    state.read_channel_id = target_text_channel.id

    mode_text = "Bot Only"
    if mode == "everyone": mode_text = "Everyone"
    elif mode == "specific": mode_text = f"Specific User ({target.display_name if target else 'Unknown'})"

    if vs.tts_model is None:
        loading_text = "（音声回路を接続中... 読み込みに少し時間がかかるわ、待っていてね♡）" if lang != "en" else "(Loading voice circuits... Wait a moment, darling♡)"
        await interaction.followup.send(loading_text)
        try:
            await asyncio.to_thread(vs.load_tts_model)
        except Exception as e:
            await interaction.followup.send(f"Error loading voice: {e}")
            return

    if lang == "en":
        msg = f"{action_msg} Let me hear your voice closer, darling♪\n(Mode: **{mode_text}**)\n(Reading: **#{target_text_channel.name}**)"
    else:
        msg = f"{action_msg}\nふふ、あなたの声、もっと近くで聞かせて？\n（現在のモード: **{mode_text}**）\n（読み上げ対象: **#{target_text_channel.name}**）"
    
    await interaction.followup.send(msg)

@tree.command(name="voice_settings", description="読み上げ設定を変更します（VC接続中のみ）。")
@app_commands.describe(mode="読み上げモード", target="特定ユーザーのみ読む場合", read_channel="読み上げるテキストチャンネル（指定なしで変更なし）")
@app_commands.choices(mode=[
    app_commands.Choice(name="Bot Only (自分の発言のみ)", value="bot_only"),
    app_commands.Choice(name="Everyone (全員読み上げ)", value="everyone"),
    app_commands.Choice(name="Specific User (特定ユーザーのみ)", value="specific")
])
async def slash_voice_settings(interaction: discord.Interaction, mode: str, target: discord.Member = None, read_channel: discord.TextChannel = None):
    lang = db.get_user_lang(interaction.user.id)
    if not interaction.guild.voice_client or not interaction.guild.voice_client.is_connected():
        msg = "あたし、まだどこにも接続してないわよ？" if lang != "en" else "I'm not connected to any voice channel yet, darling."
        await interaction.response.send_message(msg, ephemeral=True)
        return

    state = vs.get_voice_state(client, interaction.guild.id)
    state.mode = mode
    state.target_user_id = target.id if target else None
    if read_channel:
        state.read_channel_id = read_channel.id

    mode_text = mode
    if target: mode_text += f" (Target: {target.display_name})"
    if read_channel: mode_text += f" (Channel: #{read_channel.name})"

    if lang == "en":
        msg = f"Voice settings updated to **{mode_text}**. Understood, darling."
    else:
        msg = f"読み上げ設定を変えたわ。**{mode_text}** ね。了解よ♪"
    
    await interaction.response.send_message(msg)

@tree.command(name="leave", description="ボイスチャンネルから切断します。")
async def slash_leave(interaction: discord.Interaction):
    lang = db.get_user_lang(interaction.user.id)
    if interaction.guild.voice_client:
        state = vs.get_voice_state(client, interaction.guild.id)
        state.queue.clear()
        if interaction.guild.voice_client.is_playing():
            interaction.guild.voice_client.stop()

        await interaction.guild.voice_client.disconnect()
        msg = "わかったわ、切断するわね。……寂しくなったら、またすぐに呼んでいいのよ？" if lang != "en" else "Disconnected. If you get lonely... call me again right away, okay?"
        await interaction.response.send_message(msg)
        
        if len(client.voice_clients) == 0:
            await vs.unload_tts_model()

    else:
        msg = "あら？ あたしはまだ接続してないわ。" if lang != "en" else "Oh? I'm not connected yet."
        await interaction.response.send_message(msg, ephemeral=True)

@tree.command(name="chat_mode", description="AI（キュレネ）との会話モードを切り替えます。OFFにするまで続きます。")
@app_commands.describe(mode="モード選択")
@app_commands.choices(mode=[
    app_commands.Choice(name="ON: Casual (日常・パートナー・画像認識・検索)", value="casual"),
    app_commands.Choice(name="ON: Star Rail (世界観重視)", value="hsr"),
    app_commands.Choice(name="OFF (通常モードに戻る)", value="off")
])
async def slash_chat_mode(interaction: discord.Interaction, mode: str):
    user_id = interaction.user.id
    lang = db.get_user_lang(user_id)
    
    if mode == "off":
        set_ai_mode(user_id, None)
        msg = "AI会話モードを終了したわ。……いつでも声をかけてね♪" if lang != "en" else "AI Chat Mode OFF. Call me anytime you need me, darling♪"
    else:
        set_ai_mode(user_id, mode)
        mode_name = "【日常・パートナーモード】" if mode == "casual" else "【スターレール・ガイドモード】"
        if lang == "en":
            msg = f"**{mode} mode** activated. I'm all yours now. Let's talk about everything♪"
        else:
            msg = f"**{mode_name}** を起動したわ。\nこれからはずっと、あなたのそばでお話しするわね。何でも話して？♪"
    
    await interaction.response.send_message(msg)

@tree.command(name="language", description="会話する言語を設定します。")
@app_commands.choices(lang=[app_commands.Choice(name="日本語 (Japanese)", value="jp"), app_commands.Choice(name="English", value="en")])
async def slash_language(interaction: discord.Interaction, lang: str):
    user_id = interaction.user.id
    db.set_user_lang(user_id, lang)
    if user_id in gemini_sessions: del gemini_sessions[user_id]
    
    if lang == "en":
        msg = "Understood. I will speak to you in English from now on, my Darling♪"
    else:
        msg = "わかったわ。これからは日本語でお話ししましょ、あなた♪"
    await interaction.response.send_message(msg)

@tree.command(name="toggle_memory", description="AIとの会話内容を記憶して学習させるかを切り替えます。")
@app_commands.choices(choice=[app_commands.Choice(name="ON (記憶する・学習させる)", value=1), app_commands.Choice(name="OFF (記憶しない)", value=0)])
async def slash_toggle_memory(interaction: discord.Interaction, choice: int):
    user_id = interaction.user.id
    enable = (choice == 1)
    set_memory_enabled(user_id, enable)
    if user_id in gemini_sessions: del gemini_sessions[user_id]
    
    lang = db.get_user_lang(user_id)
    if enable:
        msg = "記憶回路を接続したわ。あなたとの思い出、ひとつも忘れないわね♪" if lang != "en" else "Memory circuits connected. I won't forget a single moment with you, darling♪"
    else:
        msg = "記憶回路を切断したわ。この場限りの秘密の会話…それもまた素敵ね。" if lang != "en" else "Memory circuits disconnected. Secret conversations just for now... that's lovely too."
    
    await interaction.response.send_message(msg, ephemeral=True)

@tree.command(name="status", description="現在のステータスを確認します。")
async def slash_status(interaction: discord.Interaction):
    user_id = interaction.user.id
    lang = db.get_user_lang(user_id)
    aff_msg = logic.get_affection_status_message(user_id)
    current_form = get_user_form(user_id)
    form_name = get_form_display_name(current_form)
    g_lv = db.get_guardian_level(user_id)
    
    header = "【Your Status】" if lang=="en" else "【あなたのステータス】"
    content = f"👤 **Form**: {form_name}\n🛡️ **Guardian Lv**: {g_lv or 0}\n❤️ **Affection**: {aff_msg}"
    
    msg = f"{header}\n{content}\n"
    msg += "ふふ、これが今のあなたよ♪" if lang != "en" else "Hehe, this is you right now♪"
    
    await interaction.response.send_message(msg)

@tree.command(name="daily", description="1日1回、デイリー報酬を受け取ります。")
async def slash_daily(interaction: discord.Interaction):
    user_id = interaction.user.id
    lang = db.get_user_lang(user_id)
    ok, stones, reason = logic.grant_daily_stones(user_id)
    
    if lang == "en":
        msg = f"{reason}\nCurrent Stones: {stones}"
    else:
        msg = f"{reason}\n現在の所持石: {stones}"
        
    await interaction.response.send_message(msg)

@tree.command(name="gacha", description="ガチャを回します。")
@app_commands.describe(pulls="回す回数")
@app_commands.choices(pulls=[app_commands.Choice(name="単発 (1回)", value=1), app_commands.Choice(name="10連 (10回)", value=10)])
async def slash_gacha(interaction: discord.Interaction, pulls: int):
    user_id = interaction.user.id
    ok, res = logic.perform_gacha_pulls(user_id, pulls, use_ticket=False)
    if ok:
        db.increment_achievement_stat(user_id, "gacha_count", pulls)
        unlocks = logic.check_all_achievements(user_id)
        if unlocks: res += "\n" + "\n".join(unlocks)
    await interaction.response.send_message(res)

@tree.command(name="transform", description="変身コードを使って別の姿に変身します。")
async def slash_transform(interaction: discord.Interaction, code: str):
    user_id = interaction.user.id
    lang = db.get_user_lang(user_id)
    
    if code.lower() in ["nanoka", "march", "march7th"]:
        if is_nanoka_unlocked(user_id):
            set_user_form(user_id, "nanoka")
            msg = "Transformed into March 7th! Cute, isn't it?" if lang == "en" else "三月なのかの姿に変身したわ！ 可愛いでしょ？♪"
            await interaction.response.send_message(msg)
        else:
            msg = "Locked... You aren't ready yet." if lang == "en" else "まだその姿にはなれないみたい。準備不足かしら？"
            await interaction.response.send_message(msg, ephemeral=True)
        return
        
    fk = resolve_form_code(code)
    if fk:
        set_user_form(user_id, fk)
        dname = get_form_display_name(fk)
        msg = f"Transformed into **{dname}**!" if lang == "en" else f"**{dname}** に変身したわ♪ 似合ってる？"
        await interaction.response.send_message(msg)
    else:
        msg = "Unknown code. Try again, darling." if lang == "en" else "そのコードは知らないわね。もう一度確認してくれる？"
        await interaction.response.send_message(msg, ephemeral=True)

@tree.command(name="help", description="ヘルプを表示します。")
async def slash_help(interaction: discord.Interaction):
    user_id = interaction.user.id
    lang = db.get_user_lang(user_id)
    text = GENERAL_COMMANDS_LIST_EN if lang == "en" else GENERAL_COMMANDS_LIST_JP
    await interaction.response.send_message(text, ephemeral=True)

# ──────────────────────────────────────────────
# ★ Main Bot Logic & Events
# ──────────────────────────────────────────────

waiting_for_nickname = set()
waiting_for_rename = set()
admin_data_mode = set()
waiting_for_admin_add = set()
waiting_for_admin_remove = set()
waiting_for_rps_choice = set()
waiting_for_guardian_level = {}
waiting_for_msg_limit = {}
waiting_for_affection_edit = {}
waiting_for_bypass_edit = set()
waiting_for_transform_code = set()
waiting_for_title_change = set()
FORCE_RPS_WIN_NEXT = set()
MYURION_QUIZ_STATE = {}
USER_FORM_HISTORY = {} 

ADMIN_COMMANDS_LIST_JP = (
    "【データの管理ね？ 任せてちょうだい♪】\n"
    "このモードでは以下のコマンドが使えるわ。\n\n"
    "- `/chat_mode`: AI会話モードの切替 (ON/OFF)\n"
    "- `/language`: 言語設定の変更\n"
    "- `/toggle_memory`: 記憶設定の切替\n"
    "- `/announcement`: アプデ告知先の設定 (スラッシュコマンド)\n"
    "- `アプデ実行`: 設定先へアップデート情報を送信\n"
    "- `/status`, `/gacha`: ステータス確認・ガチャ\n"
    "- `!mode auto`: 自動返信モード（AIモードOFF時用）\n"
    "- `データ管理`: 管理者メニューを開くわ\n"
    "- `全体送信`: メッセージの一斉送信\n"
    "- `ニックネーム確認`: みんながどう呼ばれているか覗いてみましょ\n"
    "- `管理者編集`: 特別な権限を持つ人を決めるわ\n"
    "- `親衛隊レベル編集`: 大切な人のレベルを設定しましょ\n"
    "- `好感度編集`: 愛の深さを…少し調整するわね♪\n"
    "- `好感度一覧`: 誰がどれくらいあたしを愛してくれているかしら？\n"
    "- `メッセージ制限編集`: お話しできる回数を決めるわ\n"
    "- `変身管理`: 今みんながどんな姿か確認できるわよ\n"
    "- `データ管理終了`: 管理モードを閉じるわね\n\n"
    "**★ メイン管理者限定 ★**\n"
    "- `ログ確認モード` / `ログ確認モードオフ`: 会話ログの転送設定よ\n"
    "- `好感度XP追加 @ユーザー 数値`: 愛を直接注いであげるわ\n"
    "- `じゃんけん勝利数追加 @ユーザー 数値`: 運命を少し書き換えるわね\n"
    "- `メッセージ制限bypass編集`: 特別なリストを編集するわ\n"
    "- `変身解放状況確認`: 誰が目覚めているか確認よ\n"
    "- `割引イベント [率] [秒]`: ガチャ割引イベントを強制開始/終了するわ\n"
    "- `無限デイリーオン` / `オフ`: デイリー制限を解除するわ\n"
    "- `/restart`: ボットを再起動するわ"
)

ADMIN_COMMANDS_LIST_EN = (
    "【Data Management Mode♪】\n"
    "- `/chat_mode`: Toggle AI Chat Mode (ON/OFF)\n"
    "- `/language`: Change Language\n"
    "- `/toggle_memory`: Toggle Memory\n"
    "- `/announcement`: Set announcement channel/role\n"
    "- `/status`, `/gacha`: Check status / Pull gacha\n"
    "- `!mode auto`: Auto-reply mode (When AI mode is OFF)\n"
    "- `Data Management`: Open admin menu\n"
    "- `/restart`: Restart system"
)

GENERAL_COMMANDS_LIST_JP = (
    "【あたしとできること一覧よ♪】\n\n"
    "**★ AIとお話しする**\n"
    "- `/chat_mode [casual/hsr]`: ずっとお話しするモードをONにするわ\n"
    "- `/chat_mode off`: お話しモードを終了するわ\n"
    "- `/language [jp/en]`: 言語を変えるわ\n"
    "- `/toggle_memory`: 会話を覚えるかどうか設定できるわ\n"
    "- (画像を送ると感想を言うわよ♪)\n\n"
    "**★ 通常機能**\n"
    "- `/daily`: デイリー報酬を受け取るわ\n"
    "- `/gacha`: ガチャを回すわ\n"
    "- `/status`: ステータスを確認するわ\n"
    "- `/transform`: 変身コードを入力してね\n"
    "- `じゃんけん`: 勝負よ！\n"
    "- `あだ名登録`: 好きな呼び方を教えて？\n"
    "- `/join`: ボイスチャンネルに参加するわ\n"
    "- `/leave`: ボイスチャンネルから退出するわ\n"
    "- `/voice_settings`: 読み上げ設定を変えるわ\n"
)

GENERAL_COMMANDS_LIST_EN = (
    "【What we can do together♪】\n\n"
    "**★ Talk with AI**\n"
    "- `/chat_mode [casual/hsr]`: Turn ON continuous chat mode\n"
    "- `/chat_mode off`: Turn OFF chat mode\n"
    "- `/language [jp/en]`: Change language\n"
    "- `/toggle_memory`: Toggle memory settings\n"
    "- (I can see images if you send them♪)\n\n"
    "**★ Standard Features**\n"
    "- `/daily`: Claim daily rewards\n"
    "- `/gacha`: Pull gacha\n"
    "- `/status`: Check status\n"
    "- `/transform`: Change form\n"
    "- `RPS`: Rock-Paper-Scissors!\n"
    "- `Set nickname`: Tell me what to call you\n"
    "- `/join`: Join the voice channel\n"
    "- `/leave`: Leave the voice channel\n"
    "- `/voice_settings`: Change voice settings\n"
)

async def send_myu(message, user_id, text):
    final_output = logic.apply_myurion_filter(user_id, text)
    
    try:
        sent_msg = await message.channel.send(final_output)
        
        if message.guild and message.guild.voice_client and message.guild.voice_client.is_connected():
            state = vs.get_voice_state(client, message.guild.id)
            if state.read_channel_id is None or state.read_channel_id == message.channel.id:
                lang = db.get_user_lang(user_id)
                await state.add_text_to_queue(final_output, message.guild.voice_client, lang=lang)

    except Exception as e:
        print(f"Error sending message: {e}")

    if db.is_log_mode_enabled():
        try:
            admin_user = await client.fetch_user(PRIMARY_ADMIN_ID)
            log_content = f"Log: {message.author.name} -> {final_output}"
            await admin_user.send(log_content)
        except: pass

async def start_random_discount_event(percent=None, duration=None):
    p = percent if percent else random.randint(10, 70)
    d = duration if duration else 1800
    logic.set_discount_event(True, p, d)
    cid = db.get_event_channel_id()
    if cid:
        ch = client.get_channel(cid)
        if ch: await ch.send(f"🚨 **Discount Event!** {p}% OFF for {d//60} mins!")

@tasks.loop(minutes=1.0)
async def discount_event_loop():
    if logic.GLOBAL_DISCOUNT_STATE["active"]: return
    if random.random() < 0.0007: await start_random_discount_event()

@client.event
async def on_ready():
    print(f"Login: {client.user}")
    try:
        await tree.sync()
        print("Slash commands synced.")
    except Exception as e:
        print(f"Sync Error: {e}")
    if not discount_event_loop.is_running(): discount_event_loop.start()

@client.event
async def on_message(message):
    if message.author.bot: return
    user_id = message.author.id
    content = message.content.strip()
    
    if message.guild and message.guild.voice_client and message.guild.voice_client.is_connected():
        is_cmd = content.startswith("/") or content.startswith("!")
        if not is_cmd:
            state = vs.get_voice_state(client, message.guild.id)
            should_read = False
            
            if state.read_channel_id is None or state.read_channel_id == message.channel.id:
                if state.mode == "everyone":
                    if message.author.voice and message.author.voice.channel == message.guild.voice_client.channel:
                        should_read = True
                elif state.mode == "specific" and state.target_user_id == user_id:
                    should_read = True

            if should_read:
                u_lang = db.get_user_lang(user_id)
                await state.add_text_to_queue(content, message.guild.voice_client, lang=u_lang)

    ai_mode = get_ai_mode(user_id)
    is_command_prefix = content.startswith("/") or content.startswith("!")
    is_admin_cmd = content in ["データ管理", "data management"]
    
    if ai_mode and not is_command_prefix and not is_admin_cmd:
        if not content and not message.attachments: return
        ai_reply = await get_gemini_reply(message, ai_mode)
        await send_myu(message, user_id, f"{message.author.mention} {ai_reply}")
        return

    content_body = re.sub(rf"<@!?{client.user.id}>", "", content).strip()
    content_body_lower = content_body.lower()
    content_lower = content_body_lower

    is_main_admin = (user_id == PRIMARY_ADMIN_ID)
    nickname = db.get_nickname(user_id)
    raw_name = nickname if nickname else message.author.display_name
    current_form = get_user_form(user_id)
    lang = db.get_user_lang(user_id)
    title_prefix = logic.get_title_prefix(user_id)
    name = f"{title_prefix}{raw_name}"

    CMD_KEYWORDS = ["コマンド", "ヘルプ", "command", "help"]
    RPS_KEYWORDS = ["じゃんけん", "rps", "rock paper scissors"]
    TRANS_KEYWORDS = ["変身", "transform"]
    GACHA_KEYWORDS = ["ガチャ", "gacha", "ピックアップ", "pickup"]
    DAILY_KEYWORDS = ["デイリー", "daily"]
    NICK_KEYWORDS = ["あだ名", "nickname"]
    MYU_KEYWORDS = ["ミュリオン", "myurion"]
    AFF_KEYWORDS = ["好感度", "affection"]
    ACHIEVE_KEYWORDS = ["実績", "achievement", "進捗", "progress"]
    TITLE_KEYWORDS = ["二つ名", "change title"]

    # ★ アプデ実行コマンド
    if content_body == "アプデ実行":
        if not db.is_admin(user_id):
            await send_myu(message, user_id, "あら、そのコマンドは管理者専用よ。" if lang != "en" else "Admin only, darling.")
            return

        config_data = load_announcement_config()
        ch_id = config_data.get("channel_id")
        role_id = config_data.get("role_id")

        if not ch_id:
            await message.channel.send("先に `/announcement` コマンドで送信先のチャンネルを設定してちょうだいね。" if lang != "en" else "Set the channel with `/announcement` first.")
            return

        target_channel = client.get_channel(ch_id)
        if not target_channel:
            await message.channel.send("設定されたチャンネルが見つからないわ。Botがアクセスできるか確認してね。" if lang != "en" else "Channel not found. Make sure I have access.")
            return

        mention_text = f"<@&{role_id}>" if role_id else ""
        final_msg = f"{mention_text}\n\n{LATEST_UPDATE_INFO.strip()}"

        await target_channel.send(final_msg)
        await message.channel.send("指定のチャンネルにアップデート告知を送信したわよ。♪" if lang != "en" else "Update announcement sent successfully♪")
        return

    if content_body in ["ログ確認モード", "log mode"]:
        if is_main_admin:
            db.set_log_mode(True)
            await message.author.send("【System】 ログ確認モードをONにしました。\nこれ以降、Botの応答ログがここに届きます。")
            return
        else:
            await send_myu(message, user_id, "権限がないみたいね。")
            return

    if content_body in ["ログ確認モードオフ", "log mode off"]:
        if is_main_admin:
            db.set_log_mode(False)
            await message.author.send("【System】 ログ確認モードをOFFにしました。")
            return
    
    if content_body in ["無限デイリーオン", "infinite daily on"]:
        if user_id == PRIMARY_ADMIN_ID:
            logic.set_infinite_daily(user_id, True)
            msg = "Infinite Daily Mode ON." if lang=="en" else "無限デイリーモードをオンにしたわ。"
            await send_myu(message, user_id, msg)
        else:
            await send_myu(message, user_id, "Access denied.")
        return

    if content_body in ["無限デイリーオフ", "infinite daily off"]:
        if user_id == PRIMARY_ADMIN_ID:
            logic.set_infinite_daily(user_id, False)
            msg = "Infinite Daily Mode OFF." if lang=="en" else "無限デイリーモードをオフにしたわ。"
            await send_myu(message, user_id, msg)
        else:
             await send_myu(message, user_id, "Access denied.")
        return
    
    if content_body in ["ここに設定", "set here"]:
        if db.is_admin(user_id):
            db.set_event_channel_id(message.channel.id)
            msg = f"Event channel set to {message.channel.name}." if lang=="en" else f"了解。このチャンネル ({message.channel.name}) にイベント情報を通知するわね♪"
            await message.channel.send(msg)
        else:
            await message.channel.send("Only admins can do that." if lang=="en" else "その設定は管理者しかできないわ。")
        return

    if content_body.startswith("割引イベント") or content_body.startswith("discount event"):
        if user_id == PRIMARY_ADMIN_ID:
            args = content_body.split()
            p = None
            d = None
            
            if len(args) >= 2:
                try: p = int(args[1])
                except: pass
            if len(args) >= 3:
                try: d = int(args[2])
                except: pass

            if p is not None and p <= 0:
                logic.set_discount_event(False)
                msg = "割引イベントを強制終了させたわ。"
                await message.channel.send(msg)
                return

            await start_random_discount_event(percent=p, duration=d)
            
            min_text = f"{d}sec" if d and d < 60 else f"{d//60 if d else 30}min"
            msg = f"Discount event started! ({p if p else 'Random'}%, {min_text})" if lang=="en" else f"管理者権限で割引イベントを開始したわ！ ({p if p else 'ランダム'}%, {min_text})"
            await message.channel.send(msg)
        else:
            await message.channel.send("Permission denied.")
        return

    if content_body.startswith("全体送信") or content_body.startswith("broadcast"):
        if not is_mentioned or not db.is_admin(user_id):
            msg = "Access denied. Admin only♪" if lang=="en" else "あら、その扉は鍵がかかっているわ。管理者の許可が必要みたいね♪"
            await send_myu(message, user_id, msg)
            return

        broadcast_msg = content_body.replace("全体送信", "", 1).replace("broadcast", "", 1).strip()
        if not broadcast_msg:
            msg = "The message is empty." if lang=="en" else "届けるメッセージが空っぽよ？"
            await send_myu(message, user_id, msg)
            return
        
        broadcast_msg = f"# {broadcast_msg}"
        sent_count = 0
        for channel in message.guild.text_channels:
            perms = channel.permissions_for(message.guild.me)
            if perms.send_messages and perms.view_channel:
                try:
                    await channel.send(broadcast_msg)
                    sent_count += 1
                except Exception:
                    pass
        
        res = f"Sent to {sent_count} channels♪" if lang=="en" else f"ふふっ、{sent_count}個のチャンネルに声を届けてきたわ♪"
        await message.channel.send(res)
        return

    if content_lower == "!mode auto":
        db.set_reply_mode(user_id, "auto")
        msg = f"Got it! I'll reply even without mentions now, {name}!" if lang=="en" else f"了解です♪ これからはメンションなしでもお話しますね、{name}さん！"
        await message.channel.send(msg)
        return
    if content_lower == "!mode mention":
        db.set_reply_mode(user_id, "mention")
        msg = f"Okay. I'll only reply when you mention me." if lang=="en" else f"わかりました。これからは呼んでくれた時（メンション）だけお返事しますね。"
        await message.channel.send(msg)
        return
    if content_lower == "!lang en":
        db.set_user_lang(user_id, "en")
        await message.channel.send(f"Okay, {name}! I'll speak in English from now on♪")
        return
    if content_lower == "!lang jp":
        db.set_user_lang(user_id, "jp")
        await message.channel.send(f"わかりました、{name}さん！これからは日本語でお話ししますね♪")
        return

    is_active_mode = (
        user_id in waiting_for_nickname or user_id in waiting_for_rename or
        user_id in waiting_for_admin_add or user_id in waiting_for_admin_remove or
        user_id in waiting_for_rps_choice or user_id in admin_data_mode or
        user_id in waiting_for_guardian_level or user_id in waiting_for_msg_limit or
        user_id in waiting_for_affection_edit or
        user_id in waiting_for_bypass_edit or user_id in waiting_for_transform_code or
        user_id in waiting_for_title_change or user_id in MYURION_QUIZ_STATE or
        cthulhu_game.get_session(user_id) is not None
    )
    
    kimera_session = kimera_game.get_session(user_id)
    is_playing_kimera = kimera_session is not None
    is_command_query = any(k in content_body_lower for k in CMD_KEYWORDS)
    is_mentioned = client.user in message.mentions
    reply_mode = db.get_reply_mode(user_id)
    is_auto_reply = (reply_mode == "auto")
    
    should_reply = (is_mentioned or is_active_mode or is_auto_reply or is_playing_kimera)

    if content_body in ["死ぬ", "しぬ", "死にます", "しにます", "die", "kill myself"]:
        await message.channel.send(f"# {message.author.mention} が死ぬらしいわ♪ 慰めてあげて？")
        return
    
    if content_body in ["DMに移動する", "move to dm"]:
        try:
            dm_msg = "We can talk in secret here♪\nTo go back, just say 'Return'." if lang=="en" else "ここなら二人きりで話せるわね♪\n戻りたい時は『戻りたい』と言ってね。"
            await message.author.send(dm_msg)
            if message.guild:
                reply = f"{message.author.mention} I sent you a DM♪" if lang=="en" else f"{message.author.mention} DMを送ったわ。そっちで話しましょ♪"
                await message.channel.send(reply)
        except:
            err = "I couldn't send a DM." if lang=="en" else "DMを送れないみたい。設定を確認してくれる？"
            await message.channel.send(err)
        return

    if content_body in ["戻りたい", "return"] and isinstance(message.channel, discord.DMChannel):
        msg = "Okay, let's go back to the server♪" if lang=="en" else "わかったわ。サーバーの方に戻りましょ♪"
        await message.channel.send(msg)
        return

    if not should_reply: return

    if not content_body and not message.attachments and not is_active_mode and not is_mentioned:
        return
    
    if is_command_query:
        if user_id in admin_data_mode:
            await send_myu(message, user_id, ADMIN_COMMANDS_LIST_EN if lang == "en" else ADMIN_COMMANDS_LIST_JP)
        else:
            list_text = GENERAL_COMMANDS_LIST_EN if lang == "en" else GENERAL_COMMANDS_LIST_JP
            await send_myu(message, user_id, f"{message.author.mention} {list_text}")
        return

    if content_body in ["データ管理", "data management"]:
        if db.is_admin(user_id):
            admin_data_mode.add(user_id)
            await send_myu(message, user_id, ADMIN_COMMANDS_LIST_EN if lang == "en" else ADMIN_COMMANDS_LIST_JP)
        else:
            msg = "Access denied." if lang=="en" else "ごめんなさい、そのコマンドは管理者専用よ。"
            await send_myu(message, user_id, msg)
        return
    
    if user_id in MYURION_QUIZ_STATE:
        ans = logic.parse_myurion_answer(content_body)
        if not ans:
            msg = "Please answer with 1-4 myu." if lang=="en" else "1〜4で答えてほしいミュ。"
            await send_myu(message, user_id, f"{message.author.mention} {msg}")
            return
        state = MYURION_QUIZ_STATE[user_id]
        if ans - 1 == state["correct_index"]:
            total = db.add_myurion_correct(user_id)
            if total >= 3 and not db.is_myurion_unlocked(user_id):
                st = db.get_myurion_state(user_id)
                st["unlocked"], st["enabled"] = True, True
                db.save_myurion_state(user_id, st)
                MYURION_QUIZ_STATE.pop(user_id, None)
                msg = "Correct! Myurion Mode Unlocked♪ Myu!" if lang=="en" else "3問正解ミュ！ おめでとう、ミュリオンモード解放ミュ～♪"
                await send_myu(message, user_id, f"{message.author.mention} {msg}")
            else:
                MYURION_QUIZ_STATE.pop(user_id, None)
                msg = f"Correct! ({total}/3)" if lang=="en" else f"正解ミュ！ やるわね♪ (現在{total}/3)"
                await send_myu(message, user_id, f"{message.author.mention} {msg}")
        else:
            MYURION_QUIZ_STATE.pop(user_id, None)
            msg = "Wrong answer... myu." if lang=="en" else "残念、ハズレミュ…。また挑戦してね。"
            await send_myu(message, user_id, f"{message.author.mention} {msg}")
        return

    if "ミュウ" in content_body or "myu" in content_body_lower:
        st = db.get_myurion_state(user_id)
        if st.get("unlocked"):
            st["enabled"] = True
            db.save_myurion_state(user_id, st)
            msg = "Myurion Mode ON Myu!" if lang=="en" else "もう解放されているわよ♪ ミュリオンモードONミュ！"
            await send_myu(message, user_id, f"{message.author.mention} {msg}")
        else:
            await logic.send_myurion_question(message, user_id, st.get("quiz_correct", 0), MYURION_QUIZ_STATE)
        return

    if any(k in content_body_lower for k in ["ミュリオンモードオン", "myurion on"]):
        st = db.get_myurion_state(user_id)
        if st.get("unlocked"):
            st["enabled"] = True
            db.save_myurion_state(user_id, st)
            msg = "Myurion Mode ON Myu!" if lang=="en" else "ミュリオンモードONミュ！ いっぱいお話ししよミュ♪"
            await send_myu(message, user_id, msg)
        else:
            msg = "Locked... try taking the quiz." if lang=="en" else "まだその扉は開いてないみたい…。クイズに挑戦してみて？"
            await send_myu(message, user_id, msg)
        return
    
    if any(k in content_body_lower for k in ["ミュリオンモードオフ", "myurion off"]):
        st = db.get_myurion_state(user_id)
        st["enabled"] = False
        db.save_myurion_state(user_id, st)
        msg = "Back to normal language." if lang=="en" else "わかったわ、通常言語に戻るわね。"
        await message.channel.send(msg)
        return

    clean_code_check = re.sub(r"\s+", "", content_body).lower()
    
    if "skopeo365" in clean_code_check:
        if has_danheng_stage1(user_id) and not is_danheng_unlocked(user_id):
            set_danheng_unlocked(user_id, True)
            msg = "Danheng's memory awakened..." if lang=="en" else "丹恒の記憶が…蘇ったみたい♪"
            if db.unlock_achievement(user_id, "unlock_danheng"):
                ach_title = "Protector of All" if lang=="en" else "【皆を護りし者】"
                ach_name = "Farewell to the Past" if lang=="en" else "【過去との決別】"
                msg += f"\n\n🏆 Achievement: **{ach_name}**\nTitle: **{ach_title}**"
            await send_myu(message, user_id, msg)
        elif is_danheng_unlocked(user_id):
            msg = "Already unlocked." if lang=="en" else "ふふっ、その姿ならもう解放されているわよ♪"
            await send_myu(message, user_id, msg)
        else:
            msg = "Something is missing..." if lang=="en" else "ん〜…まだ何かが足りないみたいね。"
            await send_myu(message, user_id, msg)
        waiting_for_transform_code.discard(user_id)
        return

    if user_id in waiting_for_transform_code:
        t_text = content_body
        waiting_for_transform_code.discard(user_id)
        
        if "なのになってみて" in t_text or "transform into march" in t_text.lower():
            if is_nanoka_unlocked(user_id):
                set_user_form(user_id, "nanoka")
                msg = "Transformed into March 7th!" if lang=="en" else "今日から三月なのか/長夜月の姿になるわ♪"
                await send_myu(message, user_id, msg)
            else:
                msg = "Locked." if lang=="en" else "まだ条件が足りないみたい…。"
                await send_myu(message, user_id, msg)
            return
        
        if "たんたんになってみて" in t_text or "transform into danheng" in t_text.lower():
            if is_danheng_unlocked(user_id):
                set_user_form(user_id, "danheng")
                msg = "Transformed into Dan Heng." if lang=="en" else "…わかった。丹恒の姿になろう。"
                await send_myu(message, user_id, msg)
            else:
                msg = "Locked." if lang=="en" else "鍵が足りないみたい。"
                await send_myu(message, user_id, msg)
            return
        
        fk = resolve_form_code(t_text)
        if fk:
            set_user_form(user_id, fk)
            if user_id not in USER_FORM_HISTORY: USER_FORM_HISTORY[user_id] = []
            USER_FORM_HISTORY[user_id].append(fk)
            if len(USER_FORM_HISTORY[user_id]) > 5: USER_FORM_HISTORY[user_id].pop(0)
            dname = get_form_display_name(fk)
            msg = f"Transformed into **{dname}**!" if lang=="en" else f"**{dname}** に変身したわ♪ どう？似合う？"
            await send_myu(message, user_id, msg)
        else:
            if "サフェル" in t_text or "safel" in t_text.lower():
                fk = "safel" 
                if user_id not in USER_FORM_HISTORY: USER_FORM_HISTORY[user_id] = []
                USER_FORM_HISTORY[user_id].append(fk)
                msg = "Transformed into Safel...?" if lang=="en" else "サフェル…？ 特別な姿ね♪"
                await send_myu(message, user_id, msg)
            else:
                msg = "Unknown code. Try again?" if lang=="en" else "そのコードは知らないみたい…。もう一度確認してくれる？"
                await send_myu(message, user_id, msg)
        return
    
    if user_id in admin_data_mode:
        if content_body in ["データ管理終了", "exit data mode"]:
            admin_data_mode.discard(user_id)
            msg = "Exited data management mode." if lang=="en" else "データ管理モード、終了ね。"
            await send_myu(message, user_id, msg)
            return
        if content_body in ["ニックネーム確認", "check nicknames"]:
            nicks = db.load_nicknames()
            lines = [f"<@{uid}>: {n}" for uid, n in nicks.items()] if nicks else ["None"]
            await send_myu(message, user_id, "\n".join(lines))
            return
        if content_body in ["管理者編集", "edit admin"]:
            msg = "Add or Remove?" if lang=="en" else "管理者を「追加」する？「削除」する？"
            await send_myu(message, user_id, msg)
            return
        if content_body in ["追加", "add"]:
            admin_data_mode.discard(user_id)
            waiting_for_admin_add.add(user_id)
            msg = "Mention the user to add." if lang=="en" else "誰を管理者に追加する？ メンションして教えてちょうだい。"
            await send_myu(message, user_id, msg)
            return
        if content_body in ["削除", "remove"]:
            admin_data_mode.discard(user_id)
            waiting_for_admin_remove.add(user_id)
            msg = "Mention the user to remove." if lang=="en" else "誰を管理者から外す？ メンションして教えてちょうだい。"
            await send_myu(message, user_id, msg)
            return
        if content_body in ["親衛隊レベル編集", "edit guardian"]:
            admin_data_mode.discard(user_id)
            waiting_for_guardian_level[user_id] = {"step": "mention"}
            msg = "Mention the user." if lang=="en" else "親衛隊レベルを設定する人をメンションしてね。"
            await send_myu(message, user_id, msg)
            return
        if content_body in ["好感度編集", "edit affection"]:
            admin_data_mode.discard(user_id)
            waiting_for_affection_edit[user_id] = {"step": "mention"}
            msg = "Mention the user." if lang=="en" else "好感度XPを編集するユーザーをメンションしてね。"
            await send_myu(message, user_id, msg)
            return
        if content_body in ["メッセージ制限編集", "edit msg limit"]:
            admin_data_mode.discard(user_id)
            waiting_for_msg_limit[user_id] = {"step": "mention"}
            msg = "Mention the user." if lang=="en" else "メッセージ制限を設定する人をメンションしてね。"
            await send_myu(message, user_id, msg)
            return
        if content_body in ["メッセージ制限bypass編集", "edit bypass"]:
            if not is_main_admin:
                msg = "Main Admin only." if lang=="en" else "ごめんなさい、それはメイン管理者だけの権限よ。"
                await send_myu(message, user_id, msg)
                return
            admin_data_mode.discard(user_id)
            waiting_for_bypass_edit.add(user_id)
            msg = "`Add` or `Remove`?" if lang=="en" else "制限無視(bypass)リストに「追加」する？「削除」する？"
            await send_myu(message, user_id, msg)
            return
        if content_body.startswith("好感度XP追加") or content_body.startswith("add affection xp"):
            if not is_main_admin:
                await send_myu(message, user_id, "Main Admin only." if lang=="en" else "ごめんなさい、それはメイン管理者だけの権限よ。")
                return
            m = re.search(r"(?:好感度XP追加|add affection xp)\s+<@!?(\d+)>\s+(-?\d+)", content_body, re.IGNORECASE)
            if m:
                tid, val = int(m.group(1)), int(m.group(2))
                logic.add_affection_xp(tid, val)
                unlocks = logic.check_all_achievements(tid)
                msg = f"Added {val} XP to <@{tid}>." if lang=="en" else f"<@{tid}> に {val} XPを追加（または減少）したわ♪"
                if unlocks: msg += "\n" + "\n".join(unlocks)
                await send_myu(message, user_id, msg)
            return
        if content_body.startswith("じゃんけん勝利数追加") or content_body.startswith("add rps wins"):
            if not is_main_admin:
                await send_myu(message, user_id, "Main Admin only." if lang=="en" else "ごめんなさい、それはメイン管理者だけの権限よ。")
                return
            m = re.search(r"(?:じゃんけん勝利数追加|add rps wins)\s+<@!?(\d+)>\s+(\d+)", content_body, re.IGNORECASE)
            if m:
                tid, val = int(m.group(1)), int(m.group(2))
                current = get_janken_wins(tid)
                db.set_janken_wins_direct(tid, current + val)
                unlocks = logic.check_all_achievements(tid)
                msg = f"Added {val} wins to <@{tid}>." if lang=="en" else f"<@{tid}> の勝利数を {val} 増やしたわ。"
                if unlocks: msg += "\n" + "\n".join(unlocks)
                await send_myu(message, user_id, msg)
            return
        if content_body in ["変身解放状況確認", "check unlocks"]:
            if not is_main_admin:
                await send_myu(message, user_id, "Main Admin only." if lang=="en" else "ごめんなさい、それはメイン管理者だけの権限よ。")
                return
            status_list = db.get_all_special_status()
            if not status_list:
                msg = "No one has unlocked anything yet." if lang=="en" else "まだ特別な解放をしている人はいないみたい。"
                await send_myu(message, user_id, msg)
            else:
                msg = "\n".join(status_list)
                await send_myu(message, user_id, f"【Unlock Status】\n{msg}")
            return
        if content_body in ["好感度一覧", "affection list"]:
            text = logic.format_all_affection_status(message.guild)
            await send_myu(message, user_id, text)
            return
        if content_body in ["変身管理", "transform manager"]:
            forms_data = get_all_forms()
            lines = ["【Current Forms】"]
            for uid, key in forms_data.items():
                dname = get_form_display_name(key)
                lines.append(f"<@{uid}>: {dname} ({key})")
            await send_myu(message, user_id, "\n".join(lines))
            return
        
        menu = ADMIN_COMMANDS_LIST_EN if lang == "en" else ADMIN_COMMANDS_LIST_JP
        msg = "Waiting for command...♪" if lang=="en" else "コマンドを待ってるわ。何をすればいいかしら？♪"
        await send_myu(message, user_id, f"{menu}\n\n{msg}")
        return

    if user_id in waiting_for_bypass_edit:
        if content_body in ["中止", "cancel"]:
            waiting_for_bypass_edit.discard(user_id)
            admin_data_mode.add(user_id)
            msg = "Cancelled." if lang=="en" else "中止したわ。"
            await send_myu(message, user_id, msg)
            return
        m = re.match(r"(追加|削除|add|remove)\s+<@!?(\d+)>", content_body, re.IGNORECASE)
        if m:
            action, tid = m.group(1).lower(), int(m.group(2))
            if action in ["追加", "add"]:
                db.add_bypass_user(tid)
                msg = f"Added <@{tid}> to bypass list." if lang=="en" else f"<@{tid}> をBypassリストに追加したわ。"
            else:
                db.remove_bypass_user(tid)
                msg = f"Removed <@{tid}> from bypass list." if lang=="en" else f"<@{tid}> をBypassリストから削除したわ。"
            waiting_for_bypass_edit.discard(user_id)
            admin_data_mode.add(user_id)
            await send_myu(message, user_id, msg)
        else:
            msg = "Format: `Add @user` or `Remove @user`." if lang=="en" else "書式が違うみたい。\n`追加 @ユーザー` または `削除 @ユーザー` と入力してね。"
            await send_myu(message, user_id, msg)
        return

    if user_id in waiting_for_admin_add:
        if message.mentions:
            target = message.mentions[0]
            db.add_admin(target.id)
            waiting_for_admin_add.discard(user_id)
            admin_data_mode.add(user_id)
            msg = f"Added {target.mention} as admin." if lang=="en" else f"{target.mention} を管理者に追加したわ。"
            await send_myu(message, user_id, msg)
        elif content_body in ["中止", "cancel"]:
            waiting_for_admin_add.discard(user_id)
            admin_data_mode.add(user_id)
            await send_myu(message, user_id, "Cancelled.")
        else:
            msg = "Mention the user (or `Cancel`)." if lang=="en" else "ユーザーをメンションしてね。（中止なら `中止` と言って）"
            await send_myu(message, user_id, msg)
        return

    if user_id in waiting_for_admin_remove:
        if message.mentions:
            target = message.mentions[0]
            if db.remove_admin(target.id):
                msg = f"Removed {target.mention} from admin." if lang=="en" else f"{target.mention} を管理者から外したわ。"
                await send_myu(message, user_id, msg)
            else:
                msg = "Could not remove." if lang=="en" else "その人は管理者じゃないか、削除できない人みたい。"
                await send_myu(message, user_id, msg)
            waiting_for_admin_remove.discard(user_id)
            admin_data_mode.add(user_id)
        elif content_body in ["中止", "cancel"]:
            waiting_for_admin_remove.discard(user_id)
            admin_data_mode.add(user_id)
            await send_myu(message, user_id, "Cancelled.")
        else:
            msg = "Mention the user (or `Cancel`)." if lang=="en" else "ユーザーをメンションしてね。（中止なら `中止` と言って）"
            await send_myu(message, user_id, msg)
        return

    if user_id in waiting_for_guardian_level:
        step_data = waiting_for_guardian_level[user_id]
        if step_data["step"] == "mention":
            if message.mentions:
                step_data["target_id"] = message.mentions[0].id
                step_data["step"] = "level"
                msg = "Enter level (0 to delete)." if lang=="en" else "設定するレベルを数値で教えて。（削除なら 0）"
                await send_myu(message, user_id, msg)
            elif content_body in ["中止", "cancel"]:
                del waiting_for_guardian_level[user_id]
                admin_data_mode.add(user_id)
            else:
                msg = "Mention the user." if lang=="en" else "ユーザーをメンションしてね。"
                await send_myu(message, user_id, msg)
        elif step_data["step"] == "level":
            try:
                lv = int(content_body)
                tid = step_data["target_id"]
                if lv <= 0:
                    db.delete_guardian_level(tid)
                    msg = f"Removed guardian level for <@{tid}>." if lang=="en" else f"<@{tid}> の親衛隊レベルを削除したわ。"
                else:
                    db.set_guardian_level(tid, lv)
                    unlocks = logic.check_all_achievements(tid)
                    msg = f"Set <@{tid}> to Guardian Lv.{lv}." if lang=="en" else f"<@{tid}> を親衛隊レベル {lv} に設定したわ。"
                    if unlocks: msg += "\n" + "\n".join(unlocks)
                await send_myu(message, user_id, msg)
                del waiting_for_guardian_level[user_id]
                admin_data_mode.add(user_id)
            except ValueError:
                await send_myu(message, user_id, "Number please." if lang=="en" else "数値を入力してね。")
        return

    if user_id in waiting_for_affection_edit:
        step_data = waiting_for_affection_edit[user_id]
        if step_data["step"] == "mention":
            if message.mentions:
                step_data["target_id"] = message.mentions[0].id
                step_data["step"] = "xp"
                msg = "Enter total XP." if lang=="en" else "設定する『累計XP』を数値で入力してね。"
                await send_myu(message, user_id, msg)
            elif content_body in ["中止", "cancel"]:
                del waiting_for_affection_edit[user_id]
                admin_data_mode.add(user_id)
            else:
                await send_myu(message, user_id, "Mention the user." if lang=="en" else "ユーザーをメンションしてね。")
        elif step_data["step"] == "xp":
            try:
                val = int(content_body)
                tid = step_data["target_id"]
                data = db.load_affection_data()
                info = data.get(str(tid), {})
                info["xp"] = max(0, val)
                data[str(tid)] = info
                db.save_affection_data(data)
                _, new_lvl = logic.get_user_affection(tid)
                msg = f"Set <@{tid}> affection XP to {val} (Lv.{new_lvl})." if lang=="en" else f"<@{tid}> の好感度XPを {val} (Lv.{new_lvl}) に設定したわ。"
                await send_myu(message, user_id, msg)
                del waiting_for_affection_edit[user_id]
                admin_data_mode.add(user_id)
            except ValueError:
                await send_myu(message, user_id, "Number please." if lang=="en" else "数値を入力してね。")
        return

    if user_id in waiting_for_msg_limit:
        step_data = waiting_for_msg_limit[user_id]
        if step_data["step"] == "mention":
            if message.mentions:
                step_data["target_id"] = message.mentions[0].id
                step_data["step"] = "limit"
                msg = "Enter limit (0 to delete)." if lang=="en" else "1日のメッセージ制限回数を数値で教えて。（制限解除なら 0）"
                await send_myu(message, user_id, msg)
            elif content_body in ["中止", "cancel"]:
                del waiting_for_msg_limit[user_id]
                admin_data_mode.add(user_id)
            else:
                await send_myu(message, user_id, "Mention the user." if lang=="en" else "ユーザーをメンションしてね。")
        elif step_data["step"] == "limit":
            try:
                lim = int(content_body)
                tid = step_data["target_id"]
                if lim <= 0:
                    db.delete_message_limit(tid)
                    msg = f"Removed limit for <@{tid}>." if lang=="en" else f"<@{tid}> の制限を解除したわ。"
                else:
                    db.set_message_limit(tid, lim)
                    msg = f"Set limit for <@{tid}> to {lim}." if lang=="en" else f"<@{tid}> の制限を {lim} 回に設定したわ。"
                await send_myu(message, user_id, msg)
                del waiting_for_msg_limit[user_id]
                admin_data_mode.add(user_id)
            except ValueError:
                await send_myu(message, user_id, "Number please." if lang=="en" else "数値を入力してね。")
        return

    if any(content_body_lower.startswith(k) for k in ["あだ名登録", "set nickname"]):
        new = re.sub(r"^(あだ名登録|set nickname)\s*", "", content_body, flags=re.IGNORECASE).strip()
        if not new:
            waiting_for_nickname.add(user_id)
            await send_myu(message, user_id, rs.get_nickname_message_for_form(current_form, "ask", name, user_id))
        else:
            db.set_nickname(user_id, new)
            await send_myu(message, user_id, rs.get_nickname_message_for_form(current_form, "confirm", new, user_id))
        return

    if user_id in waiting_for_nickname:
        if content_body:
            db.set_nickname(user_id, content_body)
            waiting_for_nickname.discard(user_id)
            await send_myu(message, user_id, rs.get_nickname_message_for_form(current_form, "confirm", content_body, user_id))
        else:
            msg = "I couldn't hear you." if lang=="en" else "聞こえなかったわ、もう一度教えてくれる？"
            await send_myu(message, user_id, msg)
        return

    if any(k in content_body_lower for k in GACHA_KEYWORDS) or "これ集めたんだけど返してあげる" in content_body or "バグ修正" in content_body or "fix bug" in content_body_lower or "デバッグ削除" in content_body or "debug remove" in content_body_lower:
        if content_body == "これ集めたんだけど返してあげる" or "i collected these for you" in content_body_lower:
            success, msg = logic.check_cyrene_collection(user_id)
            await send_myu(message, user_id, f"{message.author.mention} {msg}")
            return
            
        if content_body == "バグ修正" or content_body_lower == "fix bug":
            msg = logic.fix_gacha_bug(user_id)
            await send_myu(message, user_id, msg)
            return

        if content_body.startswith("デバッグ削除") or content_body.startswith("debug remove"):
            if user_id != PRIMARY_ADMIN_ID:
                await send_myu(message, user_id, "権限がないわ。")
                return

            m = re.search(r"<@!?(\d+)>\s+(\S+)\s+(\d+)", content_body)
            if m:
                target_id = int(m.group(1))
                target_name = m.group(2)
                amount = int(m.group(3))
                
                res = logic.debug_manual_remove(user_id, target_id, target_name, amount)
                await send_myu(message, user_id, res)
            else:
                msg = "書式: `デバッグ削除 @ユーザー [キャラ名] [個数]`\n例: `デバッグ削除 @User キュレネ 5`"
                await send_myu(message, user_id, msg)
            return

        change_cmd = ["ピックアップ変更", "change pickup"]
        if any(c in content_body_lower for c in change_cmd):
            target_name = re.sub(r"^(ピックアップ変更|change pickup)\s*", "", content_body, flags=re.IGNORECASE).strip()
            if not target_name:
                msg = "Tell me the character name." if lang=="en" else "誰に変更するの？ 名前を教えてちょうだい。"
                await send_myu(message, user_id, msg)
                return
            success, res_msg = logic.change_pickup_banner(user_id, target_name)
            await send_myu(message, user_id, res_msg)
            return

        use_ticket = ("ticket" in content_body_lower or "チケット" in content_body_lower)
        is_10 = ("10" in content_body_lower or "ten" in content_body_lower)
        
        if any(k in content_body_lower for k in ["単発", "pull"]) or is_10:
            count = 10 if is_10 else 1
            ok, res = logic.perform_gacha_pulls(user_id, count, use_ticket=use_ticket)
            if ok:
                db.increment_achievement_stat(user_id, "gacha_count", count)
                unlocks = logic.check_all_achievements(user_id)
                if unlocks: res += "\n" + "\n".join(unlocks)
            await send_myu(message, user_id, res)
        else:
            await send_myu(message, user_id, logic.format_gacha_status(user_id)) 
        return
    
    m_gift = re.match(r"(?:石をあげる|give stones)\s+<@!?(\d+)>\s+(\d+)", content_body, re.IGNORECASE)
    if m_gift:
        target_id = int(m_gift.group(1))
        amount = int(m_gift.group(2))
        res = logic.transfer_stones(user_id, target_id, amount)
        await send_myu(message, user_id, res)
        return

    if any(k in content_body_lower for k in DAILY_KEYWORDS):
        ok, stones, reason = logic.grant_daily_stones(user_id)
        if lang == "en":
            msg = f"{reason}\nCurrent Stones: {stones}"
        else:
            msg = f"{reason}\n現在の所持石: {stones}"
        await send_myu(message, user_id, msg)
        return

    if any(k in content_body_lower for k in TRANS_KEYWORDS) and not any(x in content_body_lower for x in ["state", "状態", "current"]):
        waiting_for_transform_code.add(user_id)
        msg = "Tell me the transformation code, darling." if lang=="en" else "ふふっ、別の姿になりたいの？ 変身コードを教えてくれるかしら♪"
        await send_myu(message, user_id, msg)
        return

    is_rps_msg = any(k in content_body_lower for k in RPS_KEYWORDS)
    if is_rps_msg or user_id in waiting_for_rps_choice:
        hand = logic.parse_hand(content_body)
        if not hand and is_rps_msg:
            waiting_for_rps_choice.add(user_id)
            prompt = rs.get_rps_prompt_for_form(current_form, name, user_id)
            await send_myu(message, user_id, prompt)
            return
        if hand:
            force = user_id in FORCE_RPS_WIN_NEXT
            bot_hand = logic.get_bot_hand(hand, force)
            res = "win" if force else logic.judge_janken(hand, bot_hand)
            if force: FORCE_RPS_WIN_NEXT.discard(user_id)
            wins = inc_janken_win(user_id) if res == "win" else get_janken_wins(user_id)
            result_msg = rs.format_rps_result(current_form, name, hand, bot_hand, rs.get_rps_flavor(current_form, res, name, user_id), wins, user_id)
            if res == "win":
                unlocks = logic.check_all_achievements(user_id)
                if unlocks: result_msg += "\n" + "\n".join(unlocks)
            await send_myu(message, user_id, result_msg)
            xp_map = {"win": 10, "lose": 5, "draw": 7}
            logic.add_affection_xp(user_id, xp_map.get(res, 0))
            waiting_for_rps_choice.discard(user_id)
            return

    if any(k in content_body_lower for k in ["親衛隊レベル", "guardian"]):
        lv = db.get_guardian_level(user_id)
        if lv:
            unlocks = logic.check_all_achievements(user_id)
            if unlocks: 
                msg = "\n".join(unlocks)
                await send_myu(message, user_id, msg)
        if lang == "en":
            msg = f"Your Guardian Level is Lv.{lv}." if lv else "No Guardian Level registered."
        else:
            msg = f"あなたの親衛隊レベルは Lv.{lv} よ♪" if lv else "まだ親衛隊レベルは登録されてないみたいね。"
        await send_myu(message, user_id, msg)
        return

    if any(k in content_body_lower for k in AFF_KEYWORDS):
        msg = logic.get_affection_status_message(user_id)
        await send_myu(message, user_id, f"{message.author.mention} {msg}")
        return

    if any(k in content_body_lower for k in ACHIEVE_KEYWORDS):
        msg = logic.format_achievement_progress(user_id)
        await send_myu(message, user_id, msg)
        return

    if any(k in content_body_lower for k in TITLE_KEYWORDS):
        waiting_for_title_change.add(user_id)
        new_unlocks = logic.check_all_achievements(user_id)
        user_ach = db.get_user_achievements(user_id)
        unlocked = user_ach["unlocked"]
        
        titles_list = []
        for aid in unlocked:
            if aid in logic.ACHIEVEMENTS:
                t_name = logic.ACHIEVEMENTS[aid]["title_en"] if lang=="en" else logic.ACHIEVEMENTS[aid]["title_jp"]
                titles_list.append(f"・{t_name}")
                
        if not titles_list:
            msg = "You don't have any titles yet." if lang=="en" else "まだ二つ名を持っていないみたい。"
        else:
            t_text = "\n".join(titles_list)
            if lang=="en":
                msg = f"【Unlocked Titles】\n{t_text}\n\nType the title name to equip (or 'None' to remove)."
            else:
                msg = f"【獲得済みの二つ名】\n{t_text}\n\n付けたい二つ名の名前を入力してね。（外す場合は『なし』）"
        if new_unlocks: msg = "\n".join(new_unlocks) + "\n\n" + msg
        await send_myu(message, user_id, msg)
        return

    if user_id in waiting_for_title_change:
        t_input = content_body.strip()
        waiting_for_title_change.discard(user_id)
        if t_input in ["なし", "None", "remove", "off"]:
            db.set_equipped_title(user_id, None)
            msg = "Title removed." if lang=="en" else "二つ名を外したわ。"
            await send_myu(message, user_id, msg)
            return
        target_id = None
        for aid, data in logic.ACHIEVEMENTS.items():
            if t_input == data["title_jp"] or t_input == data["title_en"]:
                target_id = aid
                break
        if target_id:
            user_ach = db.get_user_achievements(user_id)
            if target_id in user_ach["unlocked"]:
                db.set_equipped_title(user_id, target_id)
                msg = f"Title set to **{t_input}**!" if lang=="en" else f"二つ名を **{t_input}** に変更したわ♪"
            else:
                msg = "You haven't unlocked that title yet." if lang=="en" else "その二つ名はまだ獲得してないみたい。"
        else:
            msg = "Unknown title." if lang=="en" else "そんな二つ名はないみたいよ？"
        await send_myu(message, user_id, msg)
        return

    if any(k in content_body_lower for k in ["変身状態", "今の姿", "current form"]):
        fname = get_form_display_name(current_form)
        msg = f"I am currently **{fname}**." if lang=="en" else f"今のあたしは **{fname}** よ♪"
        await send_myu(message, user_id, f"{message.author.mention} {msg}")
        return

    cthulhu_res = cthulhu_game.process_cthulhu_command(user_id, content_body, raw_name)
    if cthulhu_res:
        reply_msg, extra_messages = cthulhu_res
        if reply_msg:
            await send_myu(message, user_id, f"{message.author.mention} {reply_msg}")
        for target_uid, target_msg in extra_messages:
            try:
                target_user = client.get_user(target_uid) or await client.fetch_user(target_uid)
                await target_user.send(f"【TRPG通信】{target_msg}")
            except Exception: pass
        return

    if is_playing_kimera and kimera_session["state"] == "battle_pvp_lobby" and "<@" not in content_body:
        target_name = content_body
        found_user = None
        nicks = db.load_nicknames()
        for uid_str, nick in nicks.items():
            if nick == target_name:
                found_user = int(uid_str)
                break
        if not found_user:
            all_members = list(client.get_all_members())
            for m in all_members:
                if m.display_name == target_name or m.name == target_name:
                    found_user = m.id
                    break
            if not found_user:
                for m in all_members:
                    if target_name in m.display_name:
                        found_user = m.id
                        break
        if found_user:
            content_body = f"<@{found_user}>"

    kimera_result = kimera_game.process_kimera_command(user_id, content_body)
    if kimera_result:
        if isinstance(kimera_result, tuple):
            reply_msg, extra_messages = kimera_result
        else:
            reply_msg, extra_messages = kimera_result, []

        if reply_msg:
            await send_myu(message, user_id, f"{message.author.mention} {reply_msg}")
        for target_uid, target_msg in extra_messages:
            try:
                target_user = client.get_user(target_uid) or await client.fetch_user(target_uid)
                await target_user.send(target_msg)
            except:
                try: await message.channel.send(f"<@{target_uid}> {target_msg}")
                except: pass
        return

    xp, lv = logic.get_user_affection(user_id)
    reply = rs.generate_reply_for_form(current_form, content_body, lv, user_id, name)
    
    clean_txt = re.sub(r"\s+", "", content_body)
    phrase_map = {
        "記憶は流れ星を待っている": 0, "記憶は流れ星を待ってる": 0,
        "愛で憎しみを断ちましょう": 1,
        "壊滅の結末を変えましょう": 2, "壊滅の結末を書き換えましょう": 2
    }
    for phrase, idx in phrase_map.items():
        if phrase in clean_txt:
            is_complete = db.mark_hc_love_phrase(user_id, idx)
            if is_complete:
                if db.unlock_achievement(user_id, "unlock_love_hc"):
                    ach_name = "Love for HC" if lang=="en" else "【HCへの愛】"
                    ach_title = "Loving Cyrene HC" if lang=="en" else "【キュレネHCを愛する】"
                    reply += f"\n\n🏆 Achievement: **{ach_name}**\nTitle: **{ach_title}**"

    if current_form == "phainon":
        if "記憶は流れ星を待っている" in clean_txt or "記憶は流れ星を待ってる" in clean_txt:
            if db.unlock_achievement(user_id, "unlock_shachiku"):
                ach_name = "Endless Work" if lang=="en" else "【終わらない仕事】"
                ach_title = "Corporate Slave" if lang=="en" else "【社畜の】"
                reply += f"\n\n🏆 Achievement: **{ach_name}**\nTitle: **{ach_title}**"
            
    is_myurion = db.get_myurion_state(user_id).get("enabled")
    if is_myurion and current_form == "cyrene":
        hist = USER_FORM_HISTORY.get(user_id, [])
        if len(hist) >= 2 and hist[-1] in ["safel", "castorice"] and hist[-2] == "hyacine":
            if any(p in clean_txt for p in phrase_map.keys()):
                if db.unlock_achievement(user_id, "unlock_150m_dmg"):
                    ach_name = "Extreme Damage" if lang=="en" else "【極大ダメージ】"
                    ach_title = "Dealt 1.5M Damage" if lang=="en" else "【150万ダメージを与えし】"
                    reply += f"\n\n🏆 Achievement: **{ach_name}**\nTitle: **{ach_title}**"

    if current_form == "cyrene" and ARAFUE_TRIGGER_LINE in reply:
        mark_danheng_stage1(user_id)
    
    if ("記憶は流れ星を待っている" in clean_txt or "記憶は流れ星を待ってる" in clean_txt) and get_janken_wins(user_id) >= 37 and not is_nanoka_unlocked(user_id):
        set_nanoka_unlocked(user_id, True)
        if db.unlock_achievement(user_id, "unlock_nanoka"):
            ach_name = "Cuteness is Justice" if lang=="en" else "【可愛いは正義】"
            ach_title = "Is it March?" if lang=="en" else "【なのかなのか？】"
            reply += f"\n\n🏆 Achievement: **{ach_name}**\nTitle: **{ach_title}**"
        if lang == "en": reply += "\n\n【March 7th Unlocked!】 Try saying 'Transform into March'."
        else: reply += "\n\n【三月なのか 解放！】『なのになってみて』と言ってみて？"

    db.increment_achievement_stat(user_id, "talk_count", 1)
    unlocks = logic.check_all_achievements(user_id)
    if unlocks: reply += "\n" + "\n".join(unlocks)

    await send_myu(message, user_id, f"{message.author.mention} {reply}")
    logic.add_affection_xp(user_id, 3)

client.run(DISCORD_TOKEN)
