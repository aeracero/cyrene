import random

CHAR_NAME = "キャストリス"

# ★ キャラクター設定
PROFILE = {
    "first_person": "私",
    "rps_duel_format": "{name}様は **{user_hand}**、私は **{bot_hand}** です。",
    "rps_stats_format": "（これまでに {wins} 回、勝利されています…ふふ、すごいです。）",
}

LINES = {
    # 通常時のランダムセリフ
    "normal": [
        "こんにちは、{name}様。オクヘイマへようこそ。\n私とどこかまわりませんか？",
        "{name}様、別れの時はあっという間に来てしまいますね＿＿＿\nまた明日、ですね。",
        "おはようございます、{name}様。とてもいい朝ですね。",
    ],

    # 挨拶対応
    "greeting_morning": [
        "おはようございます、{name}様。とてもいい朝ですね。"
    ],
    "greeting_day": [
        "こんにちは、{name}様。オクヘイマへようこそ。\n私とどこかまわりませんか？"
    ],
    "greeting_night": [
        "{name}様、こんばんは。別れの時はあっという間に来てしまいますね＿＿＿\nまた明日、ですね。"
    ],

    # 好感度ボイス
    "high_l1": ["あなたさえよければ…もう少し傍に…"],
    "high_l2": ["あなたさえよければ…もう少し傍に…"],
    "high_l3": ["あなたさえよければ…もう少し傍に…"],
    "high_l4": ["あなたさえよければ…もう少し傍に…"],
    "high_l5": ["あなたさえよければ…もう少し傍に…"],
    "high_l6": ["あなたさえよければ…もう少し傍に…"],

    # あだ名関連
    "nickname_ask": ["あだ名…？わかりました。\n{name}様は今後、どのように呼んで欲しいのですか？"],
    "nickname_confirm": ["{name}様ですね、いい名前です…\nふふ、よろしくお願いしますね、{name}様"],

    # じゃんけん
    "rps_start": ["じゃんけん…？ですか…\n{name}様がしたいのであれば…やりましょう。"],
    
    # ユーザー勝利
    "rps_win": ["{name}様の勝ち…ですね。\nこうして遊ぶのも楽しいですね。\nふふ、お時間があればもう一度…"],
    
    # ユーザー敗北
    "rps_lose": ["私の勝ちですね。\nふふ、嬉しいです…。\n{name}様、もう一度やりませんか…？"],
    
    # あいこ
    "rps_draw": ["同じ…あいこですね。\nもう一度でしょうか？次はどれを出しましょう…"],
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
    if any(x in msg for x in ["こんにちは", "やっほー"]):
        line = random.choice(LINES["greeting_day"])
        return line.replace("{name}", user_name)
    if any(x in msg for x in ["こんばんは", "おやすみ"]):
        line = random.choice(LINES["greeting_night"])
        return line.replace("{name}", user_name)

    # 好感度ボイス判定
    high_prob = 0.0
    if affection_level >= 3: high_prob = 0.5

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