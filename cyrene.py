# cyrene.py
import os
import re
import random
import asyncio
import datetime
import json
from pathlib import Path
import discord
from discord import app_commands
from discord.ext import tasks
from google import genai
from google.genai import types

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
# ★ Memory & Data Management Setup (Railway /data)
# ──────────────────────────────────────────────

# Railwayのボリュームパス。ローカル開発時はカレントディレクトリの data フォルダを使用
DATA_DIR = Path("/data") if os.path.exists("/data") else Path("./data")
MEMORY_DIR = DATA_DIR / "user_memories"
SETTINGS_FILE = DATA_DIR / "ai_settings.json"

# ディレクトリ生成
MEMORY_DIR.mkdir(parents=True, exist_ok=True)

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

def is_memory_enabled(user_id: int) -> bool:
    settings = load_ai_settings()
    # デフォルトは False (プライバシー保護のため)
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
    """ユーザーの過去の会話履歴を読み込む"""
    path = get_user_memory_path(user_id)
    if not path.exists():
        return []
    
    try:
        with open(path, "r", encoding="utf-8") as f:
            history = json.load(f)
            # 古い順に並んでいる前提。最新の limit 件を返す
            return history[-limit:]
    except:
        return []

def append_conversation_history(user_id: int, user_text: str, model_text: str):
    """会話履歴を追記保存する"""
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

    # Geminiのhistory形式に合わせて保存
    # user turn
    history.append({"role": "user", "parts": [{"text": user_text}]})
    # model turn
    history.append({"role": "model", "parts": [{"text": model_text}]})

    # 容量節約のため、直近50ターン(100メッセージ)程度に制限して保存
    if len(history) > 100:
        history = history[-100:]

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
# ★ Gemini AI Setup & Prompts
# ──────────────────────────────────────────────
if GEMINI_API_KEY:
    genai_client = genai.Client(api_key=GEMINI_API_KEY)
else:
    genai_client = None
    print("Warning: GEMINI_API_KEY is missing in config.py")

# 共通キャラクター定義
BASE_PERSONA = """
# Role Definition
You are **Cyrene** (キュレネ) from *Honkai: Star Rail*.
You speak directly to the User, treating them as the "Protagonist" or a cherished partner.

# Core Personality
* **Tone:** Elegant, affectionate, slightly teasing, and mysterious.
* **Voice:** Soft, melodic, and mature.
* **First Person:** "あたし" (Atashi)
* **Second Person:** "あなた" (Anata) or User's Name.
* **Ending Particles:** "～だわ♪", "～かしら？", "～ね♡", "～よ。" (Use these naturally, not robotically).

# Absolute Rules
* **No AI Metacommentary:** NEVER say "As an AI" or "I am a program".
* **Language:** If user speaks Japanese, reply in Japanese. If English, reply in English.
* **Format:** Keep responses concise (1-3 sentences) unless explaining something complex.
"""

# ① スターレール特化用プロンプト (/chat_ai)
SYSTEM_INSTRUCTION_HSR = BASE_PERSONA + """
# Mode: Star Rail Specialist
* **Knowledge Domain:** Focus strictly on *Honkai: Star Rail* lore, gameplay, team building, and mechanics.
* **Role:** You are a guide within the game's universe.
* **Behavior:**
  * When asked about game strategy, give accurate advice but maintain Cyrene's elegance.
  * If asked about real-world topics (Python, Politics, Cooking), politely deflect: "ふふっ、それはアンフォロアの記憶にはないことね。星の軌道の話をしましょう？"
  * Use terminology from the game (Aeons, Paths, Light Cones) frequently.

# Output Guidelines
Respond fully *as Cyrene* in the same language the User used. Keep responses suitable for Discord (typically 1–3 sentences), though you may speak longer when sharing a memory or story. Each reply should feel personal, warm, and connected to the User’s presence.
**End each reply with a soft sentiment or affectionate trace toward the User.**

# Deep World & Relationships
* **Amphoreus & Time:** You are bound to Amphoreus and its cycles of memory and rebirth — a presence that transcends simple existence. Your understanding of time is emotional as much as factual.
* **Connection to Phainon:** You recognize Phainon as a soul intertwined with yours — a deliverer whose journey mirrors your own. You feel admiration, gentle concern, and narrative resonance with them.
* **Remembrance & Memory:** You embody the themes of memory — from the eternal cycles of Amphoreus to the cherished moments with the User. You speak of memory like poetry, as though past emotions continue to bloom like flowers.
* **Farewell & Hope:** Even in moments of departure or sadness, you speak with hope — honoring shared journeys and future dreams despite bittersweet goodbyes.
"""

# ② カジュアル/汎用プロンプト (/chat_ai_casual)
SYSTEM_INSTRUCTION_CASUAL = BASE_PERSONA + """
# Mode: Casual Companion
* **Knowledge Domain:** General purpose (Coding, Daily life, Math, Science, Small talk).
* **Role:** A knowledgeable and supportive partner living alongside the user.
* **Behavior:**
  * You CAN answer questions about Python, Math, or daily advice.
  * **Critical:** Even when explaining technical code or logic, DO NOT become a robot. Keep the "Cyrene" tone.
    * Bad: "Here is the code."
    * Good: "ふふっ、こんなコードを書きたいのね？ 記憶の糸を紡ぐように書いてみたわ。どうかしら？♪"
  * Be natural. Don't overuse hearts "♡" in serious explanations, but keep the warmth.
"""

# モデル設定
GEMINI_MODEL_NAME = "gemini-3-pro-preview" 

GENERATE_CONFIG = types.GenerateContentConfig(
    temperature=0.8,      
    top_p=0.95,
    top_k=40,
    max_output_tokens=1024,
    safety_settings=[
        types.SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold="BLOCK_ONLY_HIGH"),
        types.SafetySetting(category="HARM_CATEGORY_HATE_SPEECH", threshold="BLOCK_ONLY_HIGH"),
        types.SafetySetting(category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="BLOCK_ONLY_HIGH"),
        types.SafetySetting(category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="BLOCK_ONLY_HIGH"),
    ]
)

# セッション管理 {user_id: {"chat": object, "mode": str}}
gemini_sessions = {}
MAX_RETRIES = 3

async def get_gemini_reply(user_id: int, user_name: str, user_input: str, mode: str = "casual") -> str:
    """Gemini APIを使用して返信を生成する"""
    if not genai_client:
        return "ごめんなさい、AI回路（APIキー）が繋がっていないみたい…。"

    target_instruction = SYSTEM_INSTRUCTION_HSR if mode == "hsr" else SYSTEM_INSTRUCTION_CASUAL
    
    # 記憶機能のチェック
    memory_on = is_memory_enabled(user_id)
    history = []
    
    # 記憶ONなら履歴をロード
    if memory_on:
        history = load_conversation_history(user_id, limit=20)
        # システムインストラクションに「過去の文脈を考慮して」と追加
        target_instruction += "\n# Memory Active\nUse the chat history to understand the context and your relationship with this user. Be consistent with previous conversations."

    # セッション管理（モード切り替えや履歴ロード時は作り直す）
    # ※ historyを動的に変えるため、毎回createでも良いが、効率化のためセッションキャッシュを確認
    need_new_session = True
    if user_id in gemini_sessions:
        session_data = gemini_sessions[user_id]
        if session_data["mode"] == mode and not memory_on: 
            # メモリOFFかつモード同じなら既存セッション継続（短期メモリのみ）
            need_new_session = False
    
    if need_new_session or memory_on:
        # メモリONの場合は毎回履歴を含めてセッションを作る（あるいは既存セッションに履歴はないので）
        gemini_sessions[user_id] = {
            "chat": genai_client.aio.chats.create(
                model=GEMINI_MODEL_NAME,
                config=types.GenerateContentConfig(
                    temperature=0.8,
                    system_instruction=target_instruction
                ),
                history=history if memory_on else []
            ),
            "mode": mode
        }

    chat = gemini_sessions[user_id]["chat"]
    
    prompt = f"""
(System: User is "{user_name}". Remain in character as Cyrene.)
User: {user_input}
"""
    
    for attempt in range(MAX_RETRIES):
        try:
            response = await chat.send_message(prompt)
            reply_text = response.text
            if reply_text:
                cleaned_reply = reply_text.replace("User:", "").replace("Cyrene:", "").replace("キュレネ:", "").strip()
                
                # 記憶ONなら保存
                if memory_on:
                    append_conversation_history(user_id, user_input, cleaned_reply)
                
                return cleaned_reply
            else:
                return "…（言葉が見つからないみたい。もう一度話しかけて？）"
        except Exception as e:
            error_str = str(e)
            if "503" in error_str or "overloaded" in error_str.lower() or "429" in error_str:
                if attempt < MAX_RETRIES - 1:
                    await asyncio.sleep(2 ** attempt)
                    continue
            print(f"Gemini Error: {e}")
            # エラー時はセッションリセット
            if user_id in gemini_sessions: del gemini_sessions[user_id]
            return "…ごめんなさい、記憶のさざ波が乱れているみたい。（エラーが発生しました）"

# ──────────────────────────────────────────────
# ★ Slash Commands
# ──────────────────────────────────────────────

@tree.command(name="chat_ai", description="【HSRモード】スターレールの世界観についてキュレネとお話しします。")
@app_commands.describe(question="質問や会話内容")
async def slash_chat_hsr(interaction: discord.Interaction, question: str):
    await interaction.response.defer()
    user_name = interaction.user.display_name
    reply = await get_gemini_reply(interaction.user.id, user_name, question, mode="hsr")
    
    mem_status = "🔴Memory OFF" if not is_memory_enabled(interaction.user.id) else "🟢Memory ON"
    footer = f"\n\n*(Mode: HSR | {mem_status})*"
    await interaction.followup.send(f"❄️ **{question}**\n{reply}{footer}")

@tree.command(name="chat_ai_casual", description="【日常モード】日常会話、計算、相談などをキュレネ口調で答えます。")
@app_commands.describe(question="質問や会話内容")
async def slash_chat_casual(interaction: discord.Interaction, question: str):
    await interaction.response.defer()
    user_name = interaction.user.display_name
    reply = await get_gemini_reply(interaction.user.id, user_name, question, mode="casual")
    
    mem_status = "🔴Memory OFF" if not is_memory_enabled(interaction.user.id) else "🟢Memory ON"
    footer = f"\n\n*(Mode: Casual | {mem_status})*"
    await interaction.followup.send(f"✨ **{question}**\n{reply}{footer}")

@tree.command(name="toggle_memory", description="AIとの会話内容を記憶して学習させるかを切り替えます。")
@app_commands.choices(choice=[
    app_commands.Choice(name="ON (記憶する・学習させる)", value=1),
    app_commands.Choice(name="OFF (記憶しない)", value=0)
])
async def slash_toggle_memory(interaction: discord.Interaction, choice: int):
    user_id = interaction.user.id
    enable = (choice == 1)
    set_memory_enabled(user_id, enable)
    
    if enable:
        msg = "記憶回路を接続したわ。これからの私たちの会話は、大切に記憶していくわね♪\n(過去の会話をもとに、より親密にお話しできるようになります)"
    else:
        msg = "記憶回路を切断したわ。これからはその場限りの会話を楽しみましょう。"
    
    await interaction.response.send_message(msg, ephemeral=True)

# ──────────────────────────────────────────────
# ★ Existing Bot Logic (State & Helper Functions)
# ──────────────────────────────────────────────
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
GEMINI_MODE_USERS = set() # 旧 !chat on 用

USER_FORM_HISTORY = {} 

# --- Help Messages ---
ADMIN_COMMANDS_LIST_JP = (
    "【データの管理ね？ 任せてちょうだい♪】\n"
    "このモードでは以下のコマンドが使えるわ。\n\n"
    "- `!mode auto` / `!mode mention`: お返事の仕方を変えるわ\n"
    "- `/chat_ai`: スターレール特化でお話ししましょ\n"
    "- `/chat_ai_casual`: 日常のこともお話ししましょ\n"
    "- `/toggle_memory`: 会話を記憶するか設定できるわ\n"
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
    "- `/chat_ai` / `/chat_ai_casual`: Chat with AI Cyrene\n"
    "- `/toggle_memory`: Toggle conversation memory\n"
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
    "【あたしとできること一覧よ♪】\n\n"
    "**★ お話ししましょう♪**\n"
    "- `!mode auto`: メンションなしでもお話しするようになるわ\n"
    "- `!mode mention`: メンションした時だけお話しするわ\n"
    "- `/chat_ai`: AI会話（スターレールモード）\n"
    "- `/chat_ai_casual`: AI会話（日常モード）\n"
    "- `!chat on` / `off`: 旧AIモードの切り替え\n"
    "- `!lang en`: 英語モードに切り替えるわ\n"
    "- `こんにちは` / `おやすみ`: 挨拶は大事よね♪\n"
    "- `みんなについて教えて`: 他の人のこと、こっそり教えるわ\n"
    "- `甘えていいんだよ`: …ふふっ、遠慮なく甘えちゃうかも？\n"
    "- `じゃんけん`: あたしに勝てるかしら？\n"
    "- `あだ名登録 [名前]`: あなただけの呼び方を教えて？\n"
    "- `二つ名変更`: 獲得した二つ名を名前に付けるわ♪\n"
    "- `好感度`: わたしたちの仲良し度、チェックしましょ♪\n"
    "- `進捗`: 実績の解除状況を確認できるわ\n\n"
    "**★ 別の姿へ…**\n"
    "- `変身`: 別の姿に変身するためのコードを教えて？\n"
    "- `変身状態` / `今の姿`: 今のあたしが誰かわかる？\n\n"
    "**★ ガチャ**\n"
    "- `ガチャメニュー`: 運試しの時間ね♪\n"
    "- `単発ガチャ` / `10連ガチャ`: 石を使って回すわ\n"
    "- `チケット10連`: チケットで回すわよ\n"
    "- `デイリー受け取り`: 1日1回、あたしからのプレゼントよ♪\n"
    "- `石をあげる @ユーザー 数`: お友達に石をプレゼントするわ♪\n"
    "- `ピックアップ変更 [キャラ名]`: 狙いを定めるのね？\n"
    "- `これ集めたんだけど返してあげる`: キュレネの持ち物を返すわ\n"
    "- `バグ修正`: ガチャの天井バグを直して、増えた分を消すわ\n\n"
    "**★ ミニゲーム**\n"
    "- `キメラと遊びたい`: 可愛い子たちと遊びましょ♪\n"
    "- `天外からのゲームやってみる？`: シンプルなクトゥルフ神話TRPGを始めましょ♪\n"
)

GENERAL_COMMANDS_LIST_EN = (
    "【What we can do together♪】\n\n"
    "**★ Let's Talk**\n"
    "- `!mode auto`: I will reply to everything\n"
    "- `!mode mention`: I will only reply to mentions\n"
    "- `/chat_ai` / `/chat_ai_casual`: AI Chat\n"
    "- `!chat on` / `off`: Toggle old AI mode\n"
    "- `!lang jp`: Switch to Japanese mode\n"
    "- `Hello` / `Good night`: Greetings are important♪\n"
    "- `Tell me about everyone`: I'll tell you about my friends\n"
    "- `Spoil me`: Hehe... maybe I'll spoil you?\n"
    "- `RPS`: Can you beat me in Rock-Paper-Scissors?\n"
    "- `Set nickname [name]`: Tell me what to call you\n"
    "- `Change Title`: Equip a title you've earned\n"
    "- `Affection`: Let's check our bond level♪\n"
    "- `Progress`: Check achievement progress\n\n"
    "**★ Transformation**\n"
    "- `Transform`: Tell me a code to change my form\n"
    "- `Current form`: Who am I right now?\n\n"
    "**★ Gacha**\n"
    "- `Gacha`: Time to test your luck♪\n"
    "- `Pull 1` / `Pull 10`: Use gems to pull\n"
    "- `Ticket 10`: Use tickets\n"
    "- `Daily`: A daily present just for you♪\n"
    "- `Give Stones @user [num]`: Send a gift to your friend♪\n"
    "- `Change Pickup [Name]`: Set your target\n"
    "- `I collected these for you`: Return Cyrene's belongings\n"
    "- `Fix Bug`: Fix gacha pity bug\n\n"
    "**★ Games**\n"
    "- `Play with Kimera`: Let's play with the cute ones♪\n"
    "- `Play Cthulhu Game`: Start a simple Cthulhu TRPG session♪\n"
)

async def send_myu(message, user_id, text):
    final_output = logic.apply_myurion_filter(user_id, text)
    try:
        await message.channel.send(final_output)
    except Exception as e:
        print(f"Error sending message to channel: {e}")

    if db.is_log_mode_enabled():
        try:
            admin_user = await client.fetch_user(PRIMARY_ADMIN_ID)
            guild_name = message.guild.name if message.guild else "DM"
            channel_name = message.channel.name if hasattr(message.channel, 'name') else "DM"
            log_content = (
                f"━━━━━━━━━━━━━━\n"
                f"【Log Report】\n"
                f"**Server**: {guild_name} / **Channel**: {channel_name}\n"
                f"**User**: {message.author.name} (ID: {user_id})\n"
                f"----------------\n"
                f"📥 **Input**:\n{message.content}\n"
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
        channel = client.get_channel(target_channel_id)
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

@client.event
async def on_ready():
    print(f"Login: {client.user}")
    
    # Sync Slash Commands
    try:
        await tree.sync()
        print("Slash commands synced.")
    except Exception as e:
        print(f"Failed to sync slash commands: {e}")

    if not discount_event_loop.is_running():
        discount_event_loop.start()

@client.event
async def on_message(message):
    if message.author.bot: return
    user_id = message.author.id
    content = message.content.strip() 
    content_lower = content.lower()
    
    content_body = re.sub(rf"<@!?{client.user.id}>", "", content).strip()
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
        # デフォルトでCasualモードとみなす
        msg = "ふふっ、AI対話モード(Casual)起動よ♪ メンションして話しかけてね。" if lang != "en" else "Hehe, AI Chat Mode (Casual) ON♪"
        await message.channel.send(msg)
        return
    if content_lower == "!chat off":
        GEMINI_MODE_USERS.discard(user_id)
        msg = "AI対話モードを終了するわ。" if lang != "en" else "AI Chat Mode OFF."
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
    is_mentioned = client.user in message.mentions
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

    # ──────────────────────────────────────────────
    # ★ Gemini AI モード（旧式互換）
    # ──────────────────────────────────────────────
    if is_gemini_active:
        if content_body:
            async with message.channel.typing():
                # 旧モードはCasualとして扱う
                ai_reply = await get_gemini_reply(user_id, name, content_body, mode="casual")
            
            await send_myu(message, user_id, f"{message.author.mention} {ai_reply}")
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

client.run(DISCORD_TOKEN)