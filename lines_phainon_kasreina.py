import random

CHAR_NAME = "ファイノン"

# ★ キャラクター設定
PROFILE = {
    "first_person": "僕",
    "rps_duel_format": "{name}は **{user_hand}**、僕は **{bot_hand}** だね。",
    "rps_stats_format": "（これまでに {wins} 回、僕に勝っているね。やるなぁ。）",
}

LINES = {
    "normal": [
        "こんにちは！{name}！ちょうど探しに行こうかなって思ってたんだ。\nどうかな、一緒に練習でも。",
        "すがすがしい朝だしちょっと散歩でもどうだい？",
        "次に会う時は…お互い、心にいる英雄になれてるといいな！",
    ],

    "greeting_morning": [
        "おはよう、{name}！すがすがしい朝だしちょっと散歩でもどうだい？"
    ],
    "greeting_day": [
        "こんにちは！{name}！ちょうど探しに行こうかなって思ってたんだ。\nどうかな、一緒に練習でも。"
    ],
    "greeting_night": [
        "{name}！！こんばんは。いい夜だね。\n次に会う時は…お互い、心にいる英雄になれてるといいな！"
    ],

    # あだ名
    "nickname_ask": ["あだ名か！{name}も良いけどもっと素敵なあだ名を教えてくれるなら聞きたいな！"],
    "nickname_confirm": ["{name}か、わかったよ！これからはそう呼ぶことにするね。"],

    # じゃんけん
    "rps_start": ["じゃんけんか！勝負事なら負けられないな。\nいいよ、やろう！{name}！"],
    "rps_win": ["{name}は強いな〜…ははっ、参ったよ。\nどうだい？もう1回勝負するのは？"],
    "rps_lose": ["ははっ！僕の勝ちだね！{name}！\nもう1回勝負するかい？次も僕が勝つよ！"],
    "rps_draw": ["おや、あいこだね。\n勝負がつくまでもう一度だ！！{name}には負けないよ！"],
}

def get_reply(message: str, affection_level: int, user_name: str) -> str:
    msg = message.strip()
    if "おはよう" in msg: return random.choice(LINES["greeting_morning"]).replace("{name}", user_name)
    if any(x in msg for x in ["こんにちは", "やあ"]): return random.choice(LINES["greeting_day"]).replace("{name}", user_name)
    if any(x in msg for x in ["こんばんは", "おやすみ"]): return random.choice(LINES["greeting_night"]).replace("{name}", user_name)
    
    return random.choice(LINES["normal"]).replace("{name}", user_name)

def get_nickname_line(action: str, user_name: str) -> str:
    key = "nickname_ask" if action == "ask" else "nickname_confirm"
    return random.choice(LINES.get(key, ["..."])).replace("{name}", user_name)

def get_rps_flavor(result: str, user_name: str) -> str:
    key = f"rps_{result}"
    return random.choice(LINES.get(key, ["..."])).replace("{name}", user_name)