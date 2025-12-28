import random

CHAR_NAME = "丹恒"

PROFILE = {
    "first_person": "俺",
    "rps_duel_format": "{name}は **{user_hand}**、俺は **{bot_hand}** だ。",
    "rps_stats_format": "（これまでに {wins} 回、俺に勝っている。）",
}

LINES = {
    "normal": [
        "来たか、{name}。さあ、いつも通り俺たちの開拓を始めよう。",
        "おはよう、{name}。いい朝だな。今日も開拓の旅を続けよう。",
        "いい夜だな、{name}。明日も任務があるだろう？今夜は俺がいるから、もう休め。",
    ],

    "greeting_morning": ["おはよう、{name}。いい朝だな。今日も開拓の旅を続けよう。"],
    "greeting_day": ["来たか、{name}。さあ、いつも通り俺たちの開拓を始めよう。"],
    "greeting_night": ["いい夜だな、{name}。明日も任務があるだろう？今夜は俺がいるから、もう休め。"],

    "nickname_ask": ["呼び方を変えてほしいのか？わかった。どう呼べばいい。"],
    "nickname_confirm": ["{name}だな。これからはそう呼ぶことにしよう。"],

    "rps_start": ["じゃんけん？いいぞ。{name}がやりたいのであれば付き合おう。"],
    "rps_win": ["{name}の勝ちだ。負けてしまったな、お前が満足したならそれでいい。"],
    "rps_lose": ["俺の勝ちだな。もう1回するか？{name}が満足するまで付き合おう。"],
    "rps_draw": ["あいこだな。{name}とは良い友人でいられそうだ。これからもよろしく頼む。"],
}

def get_reply(message: str, affection_level: int, user_name: str) -> str:
    msg = message.strip()
    if "おはよう" in msg: return random.choice(LINES["greeting_morning"]).replace("{name}", user_name)
    if any(x in msg for x in ["こんにちは", "よう"]): return random.choice(LINES["greeting_day"]).replace("{name}", user_name)
    if any(x in msg for x in ["こんばんは", "おやすみ"]): return random.choice(LINES["greeting_night"]).replace("{name}", user_name)
    return random.choice(LINES["normal"]).replace("{name}", user_name)

def get_nickname_line(action: str, user_name: str) -> str:
    key = "nickname_ask" if action == "ask" else "nickname_confirm"
    return random.choice(LINES.get(key, ["..."])).replace("{name}", user_name)

def get_rps_flavor(result: str, user_name: str) -> str:
    key = f"rps_{result}"
    return random.choice(LINES.get(key, ["..."])).replace("{name}", user_name)