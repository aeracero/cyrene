import random

CHAR_NAME = "モーディス"

# ★ キャラクター設定
PROFILE = {
    "first_person": "俺",
    # じゃんけんの結果表示フォーマット
    "rps_duel_format": "{name}は **{user_hand}**、俺は **{bot_hand}** だ。",
    "rps_stats_format": "（これまでに {wins} 回、俺から一本取ったな。）",
    
    # 英語設定 (テキストがないためフォーマットのみ定義)
    "first_person_en": "I",
    "rps_duel_format_en": "{name} chose **{user_hand}**, I chose **{bot_hand}**.",
    "rps_stats_format_en": "(You have won {wins} times.)",
}

LINES = {
    # 通常時のランダムセリフ（挨拶以外で話しかけられた時用）
    "normal": [
        "あぁ、お前か。無理するな、戦士にとって無理は禁物だからな。",
        "訓練してるのか？良いことだな。\nその努力に免じて俺が相手をしてやらんこともない。手伝って欲しければ言ってくれ。",
        "…なんだ？用がないなら訓練に戻るぞ。",
    ],

    # 挨拶
    "greeting_morning": [
        "あぁ、お前か。朝から忙しそうだな。\n無理するな、戦士にとって無理は禁物だからな。"
    ],
    "greeting_day": [
        "訓練してるのか？良いことだな。\nその努力に免じて俺が相手をしてやらんこともない。手伝って欲しければ言ってくれ。"
    ],
    "greeting_night": [
        "こんな夜遅くまで起きていたのか。\nお前はもう寝ろ。どうせ眠気に勝てないだろうからな。"
    ],

    # あだ名関連
    "nickname_ask": ["呼び方を変えて欲しい？いいだろう。なんと呼べばいいんだ？"],
    "nickname_confirm": ["「{name}」か。つぎからはそう呼ぶようにしよう。"],

    # じゃんけん
    "rps_start": ["手合わせ以外の勝負事か。いいだろう、何で戦っても俺が勝つ。"],
    
    # ユーザー勝利（モーディスの負け）
    "rps_win": ["運が良かったな。次は俺が勝つから覚悟しておけ。"],
    
    # ユーザー敗北（モーディスの勝ち）
    "rps_lose": ["俺の勝ちだ。次はもっといい勝負になることを楽しみにしている。"],
    
    # あいこ
    "rps_draw": ["ふん、互角か。もう一戦願おう。"],
}

# ※英語データがないため、英語モード時も日本語データを参照するようにシステム側で処理されます。

def get_reply(message: str, affection_level: int, user_name: str, lang: str = "jp") -> str:
    msg = message.strip()
    
    # 挨拶判定
    if "おはよう" in msg:
        return random.choice(LINES["greeting_morning"]).replace("{name}", user_name)
    
    if any(x in msg for x in ["こんにちは", "よう"]):
        return random.choice(LINES["greeting_day"]).replace("{name}", user_name)
        
    if any(x in msg for x in ["こんばんは", "おやすみ"]):
        return random.choice(LINES["greeting_night"]).replace("{name}", user_name)

    # 通常セリフ
    return random.choice(LINES["normal"]).replace("{name}", user_name)

def get_nickname_line(action: str, user_name: str, lang: str = "jp") -> str:
    key = "nickname_ask" if action == "ask" else "nickname_confirm"
    return random.choice(LINES.get(key, ["..."])).replace("{name}", user_name)

def get_rps_flavor(result: str, user_name: str, lang: str = "jp") -> str:
    key = f"rps_{result}"
    return random.choice(LINES.get(key, ["..."])).replace("{name}", user_name)