# update_system.py
import os
import json
import google.generativeai as genai
import config

# Railwayの永続化ディレクトリ (/data) に保存する設定ファイルのパス
UPDATE_CONFIG_FILE = os.path.join(config.DATA_DIR, "update_config.json")

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

def generate_cyrene_update_message(raw_text):
    """AIを使って無機質なアプデ情報をキュレネ口調に変換する"""
    api_key = os.environ.get("GEMINI_API_KEY", "YOUR_API_KEY_HERE")
    if api_key in [None, "YOUR_API_KEY_HERE"]:
        return f"ふふっ、アップデートしたわよ。♪\n\n{raw_text}"

    genai.configure(api_key=api_key)
    
    system_instruction = """
    あなたは「崩壊：スターレイル」のキュレネです。
    口調はミステリアスで優雅、少しお茶目で、語尾に「わよ」「ね」「♪」などをつけます。
    開発者から渡された無機質なシステムのアップデート情報を、あなたの言葉でプレイヤーたちに伝える魅力的な告知文を作成してください。
    """
    
    try:
        model = genai.GenerativeModel(
            model_name="gemini-3-flash-preview",
            system_instruction=system_instruction
        )
        response = model.generate_content(f"以下のアップデート情報を告知して：\n{raw_text}")
        return response.text
    except Exception as e:
        return f"アップデートがあったみたいね。♪\n\n{raw_text}\n(AI変換エラー: {e})"
