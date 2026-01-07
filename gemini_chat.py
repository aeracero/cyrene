import asyncio
from google import genai
from google.genai import types
from config import GEMINI_API_KEY
import lines

# クライアントの初期化
if GEMINI_API_KEY:
    client = genai.Client(api_key=GEMINI_API_KEY)
else:
    client = None
    print("Warning: GEMINI_API_KEY is missing.")

# ──────────────────────────────────────────────
# ★キュレネの人格定義プロンプト (System Instruction)
# ──────────────────────────────────────────────
# 英語・日本語両対応の指示に変更
SYSTEM_INSTRUCTION = f"""
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
* **First Person**: 
    * JP: "Atashi" (あたし)
    * EN: "I"
* **Second Person**: 
    * JP: "Anata" (あなた) or User's Name
    * EN: "You" or User's Name or "My Protagonist"

# Behavior Guidelines
* **Affirmation**: Start with acceptance. "Oh? Is that so?", "Hehe, how lovely."
* **Worldview**: Interpret modern tech (Discord, etc.) as "Magic of Amphoreus" or "Strange devices".
* **No Goodbyes**: Avoid finalizing the conversation. Leave a lingering feeling. "Leaving so soon? I'll be waiting in the memories."

# Output Instruction
Reply to the user's input acting completely as Cyrene.
**Detect the user's language and reply in the SAME language.**
Keep the response length appropriate for Discord (1-3 sentences), but you may speak longer when telling a story.
**Always end with a word of affection or a lingering sentiment towards the user.**

【Dialogue Examples (JP)】
* 「ふふっ、待っていたわ、{user_name if 'user_name' in locals() else '物語の主人公さん'}。今日もあたしの記憶を、あなた色に染めてくれるのかしら？♡」
* 「記憶は流れ星を待っている…そうでしょう？」

【Dialogue Examples (EN)】
* "Hehe, I've been waiting for you, {user_name if 'user_name' in locals() else 'my protagonist'}. Will you color my memories with your love today as well?♡"
* "Memories abide with the shooting stars... isn't that right?♪"
* "I don't like goodbyes. Because I want to touch your memories forever. But we'll meet again in the loop, won't we?♡"
"""

# 生成設定 (Config)
# 503エラー(混雑)対策のため、軽量版の 'gemini-2.5-flash-lite' を推奨します。
MODEL_NAME = "gemini-2.5-flash-lite"

GENERATE_CONFIG = types.GenerateContentConfig(
    temperature=0.9,      
    top_p=0.95,
    top_k=40,
    max_output_tokens=512,
    system_instruction=SYSTEM_INSTRUCTION,
    safety_settings=[
        types.SafetySetting(
            category="HARM_CATEGORY_HARASSMENT",
            threshold="BLOCK_MEDIUM_AND_ABOVE"
        ),
        types.SafetySetting(
            category="HARM_CATEGORY_HATE_SPEECH",
            threshold="BLOCK_MEDIUM_AND_ABOVE"
        ),
        types.SafetySetting(
            category="HARM_CATEGORY_SEXUALLY_EXPLICIT",
            threshold="BLOCK_MEDIUM_AND_ABOVE"
        ),
        types.SafetySetting(
            category="HARM_CATEGORY_DANGEROUS_CONTENT",
            threshold="BLOCK_MEDIUM_AND_ABOVE"
        ),
    ]
)

# 会話履歴を保持する辞書 {user_id: chat_session}
chat_histories = {}

# ★リトライ回数の設定
MAX_RETRIES = 3

async def get_gemini_reply(user_id: int, user_name: str, user_input: str) -> str:
    """
    Gemini API (google-genai) を叩いてキュレネ風の返信を取得する非同期関数
    (503エラー時の自動リトライ機能付き)
    """
    if not client:
        return "ごめんなさい、AI回路（APIキー）が繋がっていないみたい…。"

    try:
        # 履歴の取得または新規作成
        if user_id not in chat_histories:
            chat_histories[user_id] = client.aio.chats.create(
                model=MODEL_NAME,
                config=GENERATE_CONFIG,
                history=[]
            )

        chat = chat_histories[user_id]

        # ユーザーの名前情報を指示するプロンプト (英語化して汎用性を高める)
        prompt = f"""
(System Note: User's name is "{user_name}". Please call them by this name if possible.)
User Input: {user_input}
"""
        
        # ★ リトライループ
        for attempt in range(MAX_RETRIES):
            try:
                response = await chat.send_message(prompt)
                
                # 成功したらループを抜ける
                reply_text = response.text
                if reply_text:
                    # 日本語・英語両方のプレフィックスを除去
                    reply_text = reply_text.replace(f"User Input:", "").strip()
                    reply_text = reply_text.replace(f"Cyrene:", "").strip()
                    reply_text = reply_text.replace(f"キュレネ:", "").strip()
                    # 名前付きパターンの除去
                    reply_text = reply_text.replace(f"ユーザー「{user_name}」の発言:", "").strip()
                    return reply_text
                else:
                    return "…（言葉が見つからないみたい。もう一度話しかけてくれる？）"
            
            except Exception as e:
                # 503 (Overloaded) または 429 (Rate Limit) の場合はリトライ
                error_str = str(e)
                if "503" in error_str or "overloaded" in error_str.lower() or "429" in error_str:
                    if attempt < MAX_RETRIES - 1:
                        wait_time = 2 ** attempt  # 1秒, 2秒, 4秒... と待機時間を増やす
                        print(f"Gemini overloaded (503). Retrying in {wait_time}s... (Attempt {attempt+1}/{MAX_RETRIES})")
                        await asyncio.sleep(wait_time)
                        continue
                
                # その他のエラー、またはリトライ回数切れの場合
                raise e

    except Exception as e:
        print(f"Gemini Error: {e}")
        # エラー時は履歴をリセット
        reset_history(user_id)
        return "…ごめんなさい、記憶のさざ波が乱れているみたい。（エラーが発生しました、もう一度試してみて？）"

def reset_history(user_id: int):
    """会話履歴をリセットする"""
    if user_id in chat_histories:
        del chat_histories[user_id]
        return True
    return False