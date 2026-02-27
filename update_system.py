# update_system.py
import os
import json
import google.generativeai as genai
import config

UPDATE_CONFIG_FILE = os.path.join(config.DATA_DIR, "update_config.json")

# ==========================================
# ★ ここに今回のアプデ内容を記述してください ★
# ファイルをいじるたびに、ここを書き換えます
# ==========================================
LATEST_UPDATE_INFO = """
ver 6.2
・/announcement コマンドでアプデ告知のチャンネルとロールを設定できるように変更したよ。
・アプデ情報をコード内に直接書き込む仕様に変更。
・その他、細かいバグ修正と安定性の向上。
"""
# ==========================================

def load_config():
    """設定を読み込む"""
    if os.path.exists(UPDATE_CONFIG_FILE):
        with open(UPDATE_CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"channel_id": None, "role_id": None}

def save_config(channel_id, role_id):
    """設定を保存する"""
    data = {"channel_id": channel_id, "role_id": role_id}
    with open(UPDATE_CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def generate_cyrene_update_message():
    """コード内のテキスト(LATEST_UPDATE_INFO)をAIでキュレネ口調に変換する"""
    api_key = os.environ.get("GEMINI_API_KEY", "YOUR_API_KEY_HERE")
    if api_key in [None, "YOUR_API_KEY_HERE"]:
        return f"ふふっ、アップデートしたわよ。♪\n\n{LATEST_UPDATE_INFO}"

    genai.configure(api_key=api_key)
    
    system_instruction = """
    あなたは「崩壊：スターレイル」のキュレネです。
    口調はミステリアスで優雅、少しお茶目で、語尾に「わよ」「ね」「♪」などをつけます。
    開発者から渡された無機質なシステムのアップデート情報を、あなたの言葉でプレイヤーたちに伝える魅力的な告知文を作成してください。
    箇条書きの部分は分かりやすく整理して伝えてください。
    """
    
    try:
        model = genai.GenerativeModel(
            model_name="gemini-3-flash-preview",
            system_instruction=system_instruction
        )
        response = model.generate_content(f"以下のアップデート情報を告知して：\n{LATEST_UPDATE_INFO}")
        return response.text
    except Exception as e:
        return f"アップデートがあったみたいね。♪\n\n{LATEST_UPDATE_INFO}\n(AI変換エラー: {e})"
