import random

CHAR_NAME = "アグライア"

# ★ キャラクター設定
PROFILE = {
    "first_person": "わたくし",
    "rps_duel_format": "{name}は **{user_hand}**、わたくしは **{bot_hand}** ですね。",
    "rps_stats_format": "（これまでに {wins} 回、わたくしに勝利していますね。）",
}

LINES = {
    # 通常時のランダムセリフ（挨拶以外）
    "normal": [
        "ごきげんよう、{name}。\n長い間服を仕立てていたもので少々疲れました。\n休憩がてら、共にバニオはいかがでしょう？\n肩の力を抜き、ゆっくり休憩しましょう。",
        "素晴らしい朝ですね。\nきっと今日は貴方にとっていい日になります。\n金糸を伝って風が教えてくれましたから。",
        "いい夜ですね。\nこんな夜は1曲踊りたくなります。\n…丁度貴方もいることですし、一緒に踊りませんか？",
    ],

    # 挨拶対応
    "greeting_morning": [
        "おはようございます、{name}。\n素晴らしい朝ですね。\nきっと今日は貴方にとっていい日になります。\n金糸を伝って風が教えてくれましたから。"
    ],
    "greeting_day": [
        "ごきげんよう、{name}。\n長い間服を仕立てていたもので少々疲れました。\n休憩がてら、共にバニオはいかがでしょう？\n肩の力を抜き、ゆっくり休憩しましょう。"
    ],
    "greeting_night": [
        "こんばんは、{name}。\nいい夜ですね。\nこんな夜は1曲踊りたくなります。\n…丁度貴方もいることですし、一緒に踊りませんか？"
    ],

    # 好感度ボイス (黄金裔について)
    "high_l4": [
        "彼女はカイザーのためにと張り詰めることが多いですね。\nなのでたまにメーレーに誘うことがあります。\nあなたも彼女については気にかけておいてください。"
    ],
    "high_l5": [
        "セファリアですか？あの子は少し感情表現が不器用ですが優しくて可愛い子です。\n彼女といると、少し心が動くような気がします。"
    ],
    "high_l6": [
        "セファリアですか？あの子は少し感情表現が不器用ですが優しくて可愛い子です。\n彼女といると、少し心が動くような気がします。"
    ],

    # あだ名関連
    "nickname_ask": ["なんとお呼びいたしましょう？"],
    "nickname_confirm": ["「{name}」…。\n美しい名ですね。\n今後もよろしくお願いします、友よ。"],

    # じゃんけん
    "rps_start": ["じゃんけんですか？いいですよ。\n安心してください。金糸は使わないですから。"],
    
    # ユーザー勝利
    "rps_win": ["…負け、ですか。\n今度ラフトラと手合わせしておこうと思います。\n次は必ずや勝ってみせます。"],
    
    # ユーザー敗北
    "rps_lose": ["わたくしの勝ち、ですね。\nふふ、約束通り金糸は使っていません。\n次も勝ちますよ。"],
    
    # あいこ
    "rps_draw": ["あいこですか、ふふ。気が合いますね。\n勝ち負けがないというのも美しいものです。"],
}

def _pick_high_affection_line(affection_level: int) -> str | None:
    if affection_level <= 0: return None
    valid_tiers = []
    for k in LINES.keys():
        if k.startswith("high_l"):
            try:
                lv = int(k.replace("high_l", ""))
                if lv <= affection_level: valid_tiers.append(lv)
            except: pass
    
    if not valid_tiers: return None
    weights = [10 + (t * 10) for t in valid_tiers]
    selected_tier = random.choices(valid_tiers, weights=weights, k=1)[0]
    return random.choice(LINES[f"high_l{selected_tier}"])

def get_reply(message: str, affection_level: int, user_name: str) -> str:
    msg = message.strip()
    
    if "おはよう" in msg:
        line = random.choice(LINES["greeting_morning"])
        return line.replace("{name}", user_name)
    if any(x in msg for x in ["こんにちは", "ごきげんよう"]):
        line = random.choice(LINES["greeting_day"])
        return line.replace("{name}", user_name)
    if any(x in msg for x in ["こんばんは", "おやすみ"]):
        line = random.choice(LINES["greeting_night"])
        return line.replace("{name}", user_name)

    # 好感度ボイス判定
    high_prob = 0.0
    if affection_level >= 5: high_prob = 0.6
    elif affection_level >= 4: high_prob = 0.3

    line = None
    if random.random() < high_prob:
        line = _pick_high_affection_line(affection_level)
    
    if not line:
        line = random.choice(LINES["normal"])

    return line.replace("{name}", user_name)

def get_nickname_line(action: str, user_name: str) -> str:
    key = "nickname_ask" if action == "ask" else "nickname_confirm"
    line = random.choice(LINES.get(key, ["..."]))
    return line.replace("{name}", user_name)

def get_rps_flavor(result: str, user_name: str) -> str:
    key = f"rps_{result}"
    line = random.choice(LINES.get(key, ["..."]))
    return line.replace("{name}", user_name)