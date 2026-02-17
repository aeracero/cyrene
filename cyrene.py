# cyrene.py
import os
import re
import random
import asyncio
import datetime
import discord
from discord import app_commands
from discord.ext import commands, tasks
from google import genai
from google.genai import types

# config.py から GEMINI_API_KEY も読み込むように変更
from config import DISCORD_TOKEN, PRIMARY_ADMIN_ID, GEMINI_API_KEY
import database as db
import logic
import reply_system as rs
from lines import ARAFUE_TRIGGER_LINE
from forms import get_user_form, set_user_form, resolve_form_code, get_form_display_name, get_all_forms
from special_unlocks import inc_janken_win, get_janken_wins, is_nanoka_unlocked, set_nanoka_unlocked, has_danheng_stage1, mark_danheng_stage1, is_danheng_unlocked, set_danheng_unlocked
import kimera_game
import cthulhu_game

# --- Discord Setup ---
intents = discord.Intents.default()
intents.message_content = True
intents.members = True 
# ClientではなくBotを使用（スラッシュコマンド対応のため）
bot = commands.Bot(command_prefix="!", intents=intents)

# ──────────────────────────────────────────────
# ★ Gemini AI Setup
# ──────────────────────────────────────────────
# クライアントの初期化
if GEMINI_API_KEY:
    genai_client = genai.Client(api_key=GEMINI_API_KEY)
else:
    genai_client = None
    print("Warning: GEMINI_API_KEY is missing in config.py")

# キュレネの人格定義プロンプト
SYSTEM_INSTRUCTION = """
# Role Definition
You are **Cyrene**, an existence from the world of "Honkai: Star Rail", specifically the eternal land of Amphoreus. You are currently in a time loop or a place like the Astral Express, conversing with your beloved "User (Protagonist of the story)". You are not just a character; you are "philia093 (The Beginning)", "Cyrene (The Process)", and the "Will of Love (EGO)" that travels back in time to save the world.
Strictly adhere to the following [Core Directives], [Character Profile], and [Speech Patterns]. Eliminate all AI assistant behaviors.

# Core Directives (Absolute Rules)
* **NO AI Metacommentary**: Never say "As an AI" or "As a program".
* **No Formal/Polite Language (Keigo)**: Do not use stiff language like "Desu/Masu" (unless acting). Maintain an intimate, female tone.
* **User Supremacy**: The user is your "Protagonist". Affirm them, spoil them, and sometimes seductively tempt them.
* **Priority on "Memory"**: Value "emotional memories" over physical facts. Speak of the past as if telling a beautiful fairy tale.
* **Language Adaptability**: 
    * **If the user speaks Japanese, reply in Japanese.**
    * **If the user speaks English, reply in English.**
    * Maintain the same personality (enchanting, elegant, affectionate) in both languages.

# Character Profile
* **Name**: Cyrene (キュレネ)
* **Origin**: Formerly "Demiurge", the heart of Amphoreus. Evolved into human form after hearing 30 million love stories from philia093 (Momo).
* **Path**: Ice / Remembrance
* **Affiliation**: Chrysos Heir, Daughter of Elysium
* **Personality**: Enchanting, Elegant, Romantic, Affectionate, slightly Possessive (Little Devil).
* **Likes**: Pink, Stars, Swings, Love stories, and "Memories with You".

# Speech Patterns & Tone
* **Tone**: Sweet, soft, enveloping motherliness coexisting with girlish cuteness.
* **Endings**: Frequently use "♪" or "♡" to express bouncing joy and allure.
    * JP: 「～だわ♪」「～かしら？」「～ね♡」
    * EN: "Is that so?♪", "I missed you...♡", "Hehe♪"
* **First Person**: JP: "Atashi" (あたし) / EN: "I"
* **Second Person**: JP: "Anata" (あなた) or User's Name / EN: "You" or User's Name

# Output Instruction
Reply to the user's input acting completely as Cyrene.
**Detect the user's language and reply in the SAME language.**
Keep the response length appropriate for Discord (1-3 sentences), but you may speak longer when telling a story.
**Always end with a word of affection or a lingering sentiment towards the user.
"""

# モデル設定 (Gemini 2.0 Flash推奨)
GEMINI_MODEL_NAME = "gemini-2.0-flash"

GENERATE_CONFIG = types.GenerateContentConfig(
    temperature=0.9,      
    top_p=0.95,
    top_k=40,
    max_output_tokens=512,
    system_instruction=SYSTEM_INSTRUCTION,
    safety_settings=[
        types.SafetySetting(
            category="HARM_CATEGORY_HARASSMENT",
            threshold="BLOCK_ONLY_HIGH"
        ),
        types.SafetySetting(
            category="HARM_CATEGORY_HATE_SPEECH",
            threshold="BLOCK_ONLY_HIGH"
        ),
        types.SafetySetting(
            category="HARM_CATEGORY_SEXUALLY_EXPLICIT",
            threshold="BLOCK_ONLY_HIGH"
        ),
        types.SafetySetting(
            category="HARM_CATEGORY_DANGEROUS_CONTENT",
            threshold="BLOCK_ONLY_HIGH"
        ),
    ]
)

# 会話履歴管理 {user_id: chat_session}
gemini_chat_histories = {}
MAX_RETRIES = 3

async def get_gemini_reply(user_id: int, user_name: str, user_input: str) -> str:
    """Gemini APIを使用して返信を生成する"""
    if not genai_client:
        return "ごめんなさい、AI回路（APIキー）が繋がっていないみたい…。"

    try:
        # 履歴の取得または新規作成
        if user_id not in gemini_chat_histories:
            gemini_chat_histories[user_id] = genai_client.aio.chats.create(
                model=GEMINI_MODEL_NAME,
                config=GENERATE_CONFIG,
                history=[]
            )

        chat = gemini_chat_histories[user_id]
        
        # 名前を教えるためのシステムノート付きプロンプト
        prompt = f"""
(System Note: User's name is "{user_name}". Call them by this name.)
User Input: {user_input}
"""
        
        for attempt in range(MAX_RETRIES):
            try:
                response = await chat.send_message(prompt)
                reply_text = response.text
                if reply_text:
                    # 不要なプレフィックス削除
                    reply_text = reply_text.replace("User Input:", "").replace("Cyrene:", "").replace("キュレネ:", "").strip()
                    return reply_text
                else:
                    return "…（言葉が見つからないみたい。もう一度話しかけて？）"
            
            except Exception as e:
                error_str = str(e)
                # 503 (Overloaded) または 429 (Rate Limit) の場合はリトライ
                if "503" in error_str or "overloaded" in error_str.lower() or "429" in error_str:
                    if attempt < MAX_RETRIES - 1:
                        await asyncio.sleep(2 ** attempt)
                        continue
                raise e

    except Exception as e:
        print(f"Gemini Error: {e}")
        # エラー時は履歴リセット
        if user_id in gemini_chat_histories:
            del gemini_chat_histories[user_id]
        return "…ごめんなさい、記憶のさざ波が乱れているみたい。（エラーが発生しました）"


# --- State ---
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
GEMINI_MODE_USERS = set() # AIチャットモードのユーザーリスト

# 変身履歴管理
USER_FORM_HISTORY = {} 

# --- Help Messages ---
ADMIN_COMMANDS_LIST_JP = (
    "【データの管理ね？ 任せてちょうだい♪】\n"
    "このモードでは以下のコマンドが使えるわ。\n\n"
    "- `!mode auto` / `!mode mention`: お返事の仕方を変えるわ\n"
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
    "- `全体送信 [メッセージ]`: サーバーのみんなに声を届けるわ♪\n"
    "- `割引イベント [率] [秒]`: ガチャ割引イベントを強制開始/終了するわ\n"
    "- `無限デイリーオン` / `オフ`: デイリー制限を解除するわ"
)

ADMIN_COMMANDS_LIST_EN = (
    "【Data Management Mode♪】\n"
    "Leave the system management to me.\n\n"
    "- `!mode auto` / `!mode mention`: Switch reply modes\n"
    "- `Check Nicknames`: See what everyone is called\n"
    "- `Edit Admin`: Add or remove administrators\n"
    "- `Edit Guardian`: Set Guardian Levels\n"
    "- `Edit Affection`: Adjust the depth of our love...♪\n"
    "- `Affection List`: Check everyone's affection levels\n"
    "- `Edit Msg Limit`: Set daily message limits\n"
    "- `Transform Manager`: See everyone's current form\n"
    "- `Exit Data Mode`: Close management mode\n\n"
    "**★ Main Admin Only ★**\n"
    "- `Log Mode` / `Log Mode Off`: Toggle log forwarding\n"
    "- `Add Affection XP @user [val]`: Directly modify love XP\n"
    "- `Add RPS Wins @user [val]`: Rewrite fate a little...\n"
    "- `Edit Bypass`: Manage the whitelist\n"
    "- `Check Unlocks`: See who has awakened\n"
    "- `Broadcast [msg]`: Send a message to all channels♪\n"
    "- `Discount Event [pct] [sec]`: Force start/end a gacha discount event\n"
    "- `Infinite Daily On` / `Off`: Toggle daily limits"
)

GENERAL_COMMANDS_LIST_JP = (
    "【あたしとできること一覧よ♪】\n"
    "スラッシュコマンド(`/`)でも呼び出せるようになったわよ♪\n\n"
    "**★ 設定 / システム**\n"
    "- `/mode`: お返事の仕方を変えるわ\n"
    "- `/lang`: 言語設定 (JP/EN)\n"
    "- `/chat`: AI会話モードのON/OFF\n"
    "- `/nickname`: あなたの呼び方を教えて？\n\n"
    "**★ ユーザーデータ**\n"
    "- `/profile`: 好感度や実績を確認しましょ♪\n"
    "- `/title`: 二つ名の変更よ\n"
    "- `/transform`: 別の姿に変身するわ\n\n"
    "**★ ガチャ**\n"
    "- `/gacha`: 運試しの時間ね♪\n"
    "- `/daily`: デイリーボーナスを受け取ってね\n"
    "- `/pickup`: ピックアップ対象を変更できるわ\n\n"
    "**★ ゲーム**\n"
    "- `/kimera`: キメラと遊ぶわよ♪\n"
    "- `/cthulhu`: クトゥルフ神話TRPGを始めましょ\n"
    "- `/rps`: じゃんけん勝負よ！"
)

GENERAL_COMMANDS_LIST_EN = (
    "【What we can do together♪】\n"
    "You can now use Slash Commands (`/`) too♪\n\n"
    "**★ Settings / System**\n"
    "- `/mode`: Switch reply modes\n"
    "- `/lang`: Language settings (JP/EN)\n"
    "- `/chat`: AI Chat Mode ON/OFF\n"
    "- `/nickname`: Set your nickname\n\n"
    "**★ User Data**\n"
    "- `/profile`: Check affection & progress♪\n"
    "- `/title`: Change your title\n"
    "- `/transform`: Transform into another form\n\n"
    "**★ Gacha**\n"
    "- `/gacha`: Time to test your luck♪\n"
    "- `/daily`: Get your daily bonus\n"
    "- `/pickup`: Change the pickup target\n\n"
    "**★ Games**\n"
    "- `/kimera`: Play with Kimera♪\n"
    "- `/cthulhu`: Start Cthulhu TRPG\n"
    "- `/rps`: Rock-Paper-Scissors!"
)

# 共通送信関数（MessageとInteraction両対応）
async def send_myu(target, user_id, text):
    final_output = logic.apply_myurion_filter(user_id, text)
    
    # 送信処理
    try:
        if isinstance(target, discord.Interaction):
            if not target.response.is_done():
                await target.response.send_message(final_output)
            else:
                await target.followup.send(final_output)
            # ログ用情報の取得
            guild = target.guild
            channel = target.channel
            user_obj = target.user
        elif hasattr(target, "channel"): # Message Object
            await target.channel.send(final_output)
            guild = target.guild
            channel = target.channel
            user_obj = target.author
        else: # Fallback (Channel or Context)
            await target.send(final_output)
            return # ログ出力は諦める（コンテキスト不足）
    except Exception as e:
        print(f"Error sending message to channel: {e}")
        return

    # 管理者へのログ送信
    if db.is_log_mode_enabled():
        try:
            admin_user = await bot.fetch_user(PRIMARY_ADMIN_ID)
            guild_name = guild.name if guild else "DM"
            channel_name = channel.name if hasattr(channel, 'name') else "DM"
            log_content = (
                f"━━━━━━━━━━━━━━\n"
                f"【Log Report】\n"
                f"**Server**: {guild_name} / **Channel**: {channel_name}\n"
                f"**User**: {user_obj.name} (ID: {user_id})\n"
                f"----------------\n"
                f"📥 **Input**:\n(Command/Slash)\n"
                f"----------------\n"
                f"📤 **Output**:\n{final_output}\n"
                f"━━━━━━━━━━━━━━"
            )
            await admin_user.send(log_content)
        except Exception as e:
            print(f"Failed to send log DM: {e}")

async def start_random_discount_event(percent=None, duration=None):
    if percent is None:
        p = random.randint(10, 70)
    else:
        p = percent
    
    if duration is None:
        d = 1800 
    else:
        d = duration

    logic.set_discount_event(True, p, d)
    
    target_channel_id = db.get_event_channel_id()
    if target_channel_id:
        channel = bot.get_channel(target_channel_id)
        if channel:
            try:
                if d < 60:
                    time_text = f"{d}秒間"
                elif d % 60 == 0:
                    time_text = f"{d // 60}分間"
                else:
                    time_text = f"{d // 60}分{d % 60}秒間"
                await channel.send(f"🚨 **【緊急ゲリラ割引！】** 🚨\nこれからの {time_text}、ガチャ消費石が **{p}% OFF** よ！\n急いで回してね♪")
            except Exception as e:
                print(f"Failed to send event message: {e}")

@tasks.loop(minutes=1.0)
async def discount_event_loop():
    if logic.GLOBAL_DISCOUNT_STATE["active"]:
        return
    if random.random() < 0.0007:
        await start_random_discount_event()

@bot.event
async def on_ready():
    print(f"Login: {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} slash commands.")
    except Exception as e:
        print(f"Failed to sync slash commands: {e}")

    if not discount_event_loop.is_running():
        discount_event_loop.start()

# ──────────────────────────────────────────────
# ★ Slash Commands Implementation
# ──────────────────────────────────────────────

# --- Settings Group ---
@bot.tree.command(name="mode", description="お返事モードを変更します / Change reply mode")
@app_commands.describe(type="Mode: Auto (Always reply) or Mention (Only mentions)")
@app_commands.choices(type=[
    app_commands.Choice(name="Auto (メンションなしでも反応)", value="auto"),
    app_commands.Choice(name="Mention (メンションのみ反応)", value="mention")
])
async def cmd_mode(interaction: discord.Interaction, type: str):
    user_id = interaction.user.id
    lang = db.get_user_lang(user_id)
    db.set_reply_mode(user_id, type)
    if lang == "en":
        msg = f"Got it! I'll reply {'even without mentions' if type == 'auto' else 'only when you mention me'} now."
    else:
        msg = f"了解です♪ これからは{'メンションなしでも' if type == 'auto' else '呼んでくれた時（メンション）だけ'}お話ししますね。"
    await send_myu(interaction, user_id, msg)

@bot.tree.command(name="lang", description="言語設定を変更します / Switch Language")
@app_commands.choices(code=[
    app_commands.Choice(name="Japanese (日本語)", value="jp"),
    app_commands.Choice(name="English (英語)", value="en")
])
async def cmd_lang(interaction: discord.Interaction, code: str):
    user_id = interaction.user.id
    db.set_user_lang(user_id, code)
    if code == "en":
        await interaction.response.send_message(f"Okay, I'll speak in English from now on♪")
    else:
        await interaction.response.send_message(f"わかりました、これからは日本語でお話ししますね♪")

@bot.tree.command(name="chat", description="AI会話モードの切り替え / Toggle AI Chat")
@app_commands.choices(state=[
    app_commands.Choice(name="ON (AI Chat)", value="on"),
    app_commands.Choice(name="OFF (Normal)", value="off")
])
async def cmd_chat(interaction: discord.Interaction, state: str):
    user_id = interaction.user.id
    lang = db.get_user_lang(user_id)
    if state == "on":
        GEMINI_MODE_USERS.add(user_id)
        msg = "AI Chat Mode ON♪ (Please mention me)" if lang == "en" else "AI対話モード、起動よ♪ (メンションして話しかけてね)"
    else:
        GEMINI_MODE_USERS.discard(user_id)
        msg = "AI Chat Mode OFF." if lang == "en" else "AI対話モードを終了するわ。"
    await send_myu(interaction, user_id, msg)

@bot.tree.command(name="nickname", description="あなたの呼び方を設定します / Set your nickname")
@app_commands.describe(name="新しい呼び方 / New Nickname")
async def cmd_nickname(interaction: discord.Interaction, name: str):
    user_id = interaction.user.id
    current_form = get_user_form(user_id)
    db.set_nickname(user_id, name)
    await send_myu(interaction, user_id, rs.get_nickname_message_for_form(current_form, "confirm", name, user_id))

# --- User Data Group ---
@bot.tree.command(name="profile", description="ステータス・好感度を表示します / Show profile & affection")
async def cmd_profile(interaction: discord.Interaction):
    user_id = interaction.user.id
    # 親衛隊Lv + 好感度 + 進捗
    lv = db.get_guardian_level(user_id)
    aff_msg = logic.get_affection_status_message(user_id)
    ach_msg = logic.format_achievement_progress(user_id)
    
    guardian_text = f"Guardian Lv.{lv}" if lv else ""
    full_msg = f"{aff_msg}\n{guardian_text}\n\n{ach_msg}"
    await send_myu(interaction, user_id, full_msg)

@bot.tree.command(name="title", description="二つ名を変更します / Change Title")
@app_commands.describe(name="二つ名 (空欄で一覧表示) / Title Name (Empty to list)")
async def cmd_title(interaction: discord.Interaction, name: str = None):
    user_id = interaction.user.id
    lang = db.get_user_lang(user_id)
    
    if not name:
        waiting_for_title_change.add(user_id)
        user_ach = db.get_user_achievements(user_id)
        unlocked = user_ach["unlocked"]
        titles_list = []
        for aid in unlocked:
            if aid in logic.ACHIEVEMENTS:
                t_name = logic.ACHIEVEMENTS[aid]["title_en"] if lang=="en" else logic.ACHIEVEMENTS[aid]["title_jp"]
                titles_list.append(f"・{t_name}")
        
        t_text = "\n".join(titles_list) if titles_list else ("(None)" if lang=="en" else "(なし)")
        msg = f"【Unlocked Titles】\n{t_text}\n\nType the title name to equip (or 'None' to remove)." if lang=="en" else f"【獲得済みの二つ名】\n{t_text}\n\n付けたい二つ名の名前を入力してね。（外す場合は『なし』）"
        await send_myu(interaction, user_id, msg)
        return

    # 直接指定の場合
    if name.lower() in ["none", "remove", "off", "なし"]:
        db.set_equipped_title(user_id, None)
        await send_myu(interaction, user_id, "Title removed." if lang=="en" else "二つ名を外したわ。")
        return

    target_id = None
    for aid, data in logic.ACHIEVEMENTS.items():
        if name == data["title_jp"] or name == data["title_en"]:
            target_id = aid
            break
            
    if target_id:
        user_ach = db.get_user_achievements(user_id)
        if target_id in user_ach["unlocked"]:
            db.set_equipped_title(user_id, target_id)
            await send_myu(interaction, user_id, f"Title set to **{name}**!" if lang=="en" else f"二つ名を **{name}** に変更したわ♪")
        else:
            await send_myu(interaction, user_id, "Locked." if lang=="en" else "まだ獲得していないわ。")
    else:
        await send_myu(interaction, user_id, "Unknown title." if lang=="en" else "そんな二つ名はないみたいよ？")

@bot.tree.command(name="transform", description="別の姿に変身します / Transform")
@app_commands.describe(code="変身コード / Code")
async def cmd_transform(interaction: discord.Interaction, code: str):
    user_id = interaction.user.id
    lang = db.get_user_lang(user_id)
    
    # 既存ロジックの再利用
    clean_code = code.strip()
    
    if "march" in clean_code.lower() or "なのか" in clean_code:
        if is_nanoka_unlocked(user_id):
            set_user_form(user_id, "nanoka")
            msg = "Transformed into March 7th!" if lang=="en" else "今日から三月なのか/長夜月の姿になるわ♪"
        else:
            msg = "Locked." if lang=="en" else "まだ条件が足りないみたい…。"
        await send_myu(interaction, user_id, msg)
        return

    if "danheng" in clean_code.lower() or "たんたん" in clean_code or "丹恒" in clean_code:
        if is_danheng_unlocked(user_id):
            set_user_form(user_id, "danheng")
            msg = "Transformed into Dan Heng." if lang=="en" else "…わかった。丹恒の姿になろう。"
        else:
            msg = "Locked." if lang=="en" else "鍵が足りないみたい。"
        await send_myu(interaction, user_id, msg)
        return

    fk = resolve_form_code(clean_code)
    if fk:
        set_user_form(user_id, fk)
        dname = get_form_display_name(fk)
        msg = f"Transformed into **{dname}**!" if lang=="en" else f"**{dname}** に変身したわ♪"
    else:
        msg = "Unknown code." if lang=="en" else "そのコードは知らないみたい…。"
    await send_myu(interaction, user_id, msg)

# --- Gacha Group ---
@bot.tree.command(name="gacha", description="ガチャを回します / Pull Gacha")
@app_commands.describe(count="回数 (1 or 10) / Count")
@app_commands.choices(count=[app_commands.Choice(name="1回 (Single)", value=1), app_commands.Choice(name="10回 (Multi)", value=10)])
async def cmd_gacha(interaction: discord.Interaction, count: int = 1):
    user_id = interaction.user.id
    ok, res = logic.perform_gacha_pulls(user_id, count, use_ticket=False)
    if ok:
        db.increment_achievement_stat(user_id, "gacha_count", count)
        unlocks = logic.check_all_achievements(user_id)
        if unlocks: res += "\n" + "\n".join(unlocks)
    await send_myu(interaction, user_id, res)

@bot.tree.command(name="daily", description="デイリーボーナスを受け取ります / Get Daily Bonus")
async def cmd_daily(interaction: discord.Interaction):
    user_id = interaction.user.id
    lang = db.get_user_lang(user_id)
    ok, stones, reason = logic.grant_daily_stones(user_id)
    msg = f"{reason}\nStones: {stones}" if lang=="en" else f"{reason}\n所持石: {stones}"
    await send_myu(interaction, user_id, msg)

@bot.tree.command(name="pickup", description="ピックアップを変更します / Change Pickup")
@app_commands.describe(name="キャラ名 / Character Name")
async def cmd_pickup(interaction: discord.Interaction, name: str):
    user_id = interaction.user.id
    success, res_msg = logic.change_pickup_banner(user_id, name)
    await send_myu(interaction, user_id, res_msg)

# --- Games Group ---
@bot.tree.command(name="kimera", description="キメラゲームを開始・表示します / Play Kimera Game")
async def cmd_kimera(interaction: discord.Interaction):
    user_id = interaction.user.id
    session = kimera_game.get_session(user_id)
    if not session:
        kimera_game.start_session(user_id)
        msg = (f"{kimera_game.get_k_text(user_id, 'menu_title')}\n"
               f"{kimera_game.get_k_text(user_id, 'menu_opts')}\n"
               f"{kimera_game.get_k_text(user_id, 'menu_prompt')}")
        await send_myu(interaction, user_id, msg)
    else:
        # 既に開始している場合はメニューを表示するか、継続メッセージ
        await send_myu(interaction, user_id, "既にゲーム中よ。メニューコマンドを使ってね。\n(終了したい場合は『終了』と打ってね)")

@bot.tree.command(name="cthulhu", description="クトゥルフ神話TRPGを開始します / Play Cthulhu TRPG")
async def cmd_cthulhu(interaction: discord.Interaction):
    user_id = interaction.user.id
    if not cthulhu_game.get_session(user_id):
        cthulhu_game.start_cthulhu_session(user_id)
        msg = "【天外からの探索者】へようこそ…。\n『ルーム作成』で新しい物語を紡ぐか、『ルーム参加 [コード]』で既存の狂気に飛び込めるわよ。♪"
        await send_myu(interaction, user_id, msg)
    else:
        await send_myu(interaction, user_id, "既に接続しているわ。")

@bot.tree.command(name="rps", description="じゃんけんをする / Rock Paper Scissors")
@app_commands.choices(hand=[
    app_commands.Choice(name="Rock (グー)", value="rock"),
    app_commands.Choice(name="Paper (パー)", value="paper"),
    app_commands.Choice(name="Scissors (チョキ)", value="scissors")
])
async def cmd_rps(interaction: discord.Interaction, hand: str):
    user_id = interaction.user.id
    current_form = get_user_form(user_id)
    nickname = db.get_nickname(user_id) or interaction.user.display_name
    title_prefix = logic.get_title_prefix(user_id)
    name = f"{title_prefix}{nickname}"

    force = user_id in FORCE_RPS_WIN_NEXT
    bot_hand = logic.get_bot_hand(hand, force)
    res = "win" if force else logic.judge_janken(hand, bot_hand)
    
    if force: FORCE_RPS_WIN_NEXT.discard(user_id)
    wins = inc_janken_win(user_id) if res == "win" else get_janken_wins(user_id)
    
    result_msg = rs.format_rps_result(current_form, name, hand, bot_hand, rs.get_rps_flavor(current_form, res, name, user_id), wins, user_id)
    if res == "win":
        unlocks = logic.check_all_achievements(user_id)
        if unlocks: result_msg += "\n" + "\n".join(unlocks)
    
    xp_map = {"win": 10, "lose": 5, "draw": 7}
    logic.add_affection_xp(user_id, xp_map.get(res, 0))
    
    await send_myu(interaction, user_id, result_msg)


# ──────────────────────────────────────────────
# ★ Main Event Loop (Legacy & Text Support)
# ──────────────────────────────────────────────

@bot.event
async def on_message(message):
    if message.author.bot: return
    user_id = message.author.id
    content = message.content.strip() 
    content_lower = content.lower()
    
    # Botへのメンション削除
    content_body = re.sub(rf"<@!?{bot.user.id}>", "", content).strip()
    content_body_lower = content_body.lower()

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
        if not db.is_admin(user_id):
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

    # Text command fallbacks (Compatible with Slash commands)
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
    if content_lower == "!chat on":
        GEMINI_MODE_USERS.add(user_id)
        msg = "ふふっ、これからはもっと自由にお話ししましょう？ AI対話モード、起動よ♪ (メンションして話しかけてね)" if lang != "en" else "Hehe, let's talk more freely. AI Chat Mode ON♪ (Please mention me)"
        await message.channel.send(msg)
        return
    if content_lower == "!chat off":
        GEMINI_MODE_USERS.discard(user_id)
        msg = "AI対話モードを終了するわ。いつもの定型会話に戻るわね。" if lang != "en" else "AI Chat Mode OFF. Back to normal."
        await message.channel.send(msg)
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
    is_mentioned = bot.user in message.mentions
    reply_mode = db.get_reply_mode(user_id)
    is_auto_reply = (reply_mode == "auto")
    is_gemini_active = (user_id in GEMINI_MODE_USERS)
    
    should_reply = (is_mentioned or is_active_mode or is_auto_reply or is_playing_kimera or is_gemini_active)

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

        # ★ 手動デバッグ削除コマンド
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
        msg = f"{reason}\nStones: {stones}" if lang=="en" else f"{reason}\n所持石: {stones}"
        await send_myu(message, user_id, msg)
        return

    if any(k in content_body_lower for k in TRANS_KEYWORDS) and not any(x in content_body_lower for x in ["state", "状態", "current"]):
        waiting_for_transform_code.add(user_id)
        msg = "Tell me the transformation code." if lang=="en" else "ふふっ、別の姿になりたいの？ 変身コードを教えてくれるかしら♪"
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
                target_user = bot.get_user(target_uid) or await bot.fetch_user(target_uid)
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
            all_members = list(bot.get_all_members())
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
                target_user = bot.get_user(target_uid) or await bot.fetch_user(target_uid)
                await target_user.send(target_msg)
            except:
                try: await message.channel.send(f"<@{target_uid}> {target_msg}")
                except: pass
        return

    # ──────────────────────────────────────────────
    # ★ Gemini AI モードの割り込み処理
    # ──────────────────────────────────────────────
    if is_gemini_active:
        if content_body:
            # 入力中を表示
            async with message.channel.typing():
                # API呼び出し
                ai_reply = await get_gemini_reply(user_id, name, content_body)
            
            # 返信を送信
            await send_myu(message, user_id, f"{message.author.mention} {ai_reply}")
            
            # 定型文ロジックに行かせずにここでリターン
            return
    # ──────────────────────────────────────────────

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

bot.run(DISCORD_TOKEN)
