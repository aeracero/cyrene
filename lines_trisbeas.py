import random

CHAR_NAME = "トリスビアス"

PROFILE = {
    "first_person": "あたちたち",
    "rps_duel_format": "{name}ちゃんは **{user_hand}**、あたちたちは **{bot_hand}** だよ！",
    "rps_stats_format": "（これまでに {wins} 回、あたちたちに勝ったの！すごい！）",
}

LINES = {
    "normal": [
        "お！{name}ちゃんじゃないか！朝はトリビーと遊んだんだろ？お昼はぼくたちと遊ぶぞ！",
        "おはよう、{name}ちゃん！あたちたちと一緒に遊ばない？",
        "こんばんは、{name}ちゃん！もう寝る時間？まだ遊び足りないよ〜！", # 補完
    ],

    "greeting_morning": ["おはよう、{name}ちゃん！あたちたちと一緒に遊ばない？"],
    "greeting_day": ["お！{name}ちゃんじゃないか！朝はトリビーと遊んだんだろ？お昼はぼくたちと遊ぶぞ！"],
    "greeting_night": ["こんばんは、{name}ちゃん！もう寝る時間？まだ遊び足りないよ〜！"],

    "nickname_ask": ["{name}ちゃん、別のお名前で呼んでほちいの？いいよ！"],
    "nickname_confirm": ["{name}ちゃんだね！あたらちいのも、とーってもいいお名前！「あたちたち」にも伝えておくね！"],

    "rps_start": ["じゃんけん？あたちたちのこと子供だと思ってない？ちかたないなぁ、付き合ってあげる！"],
    "rps_win": ["負けちゃった〜{name}ちゃん！もう1回やろう！いいでちょう？"],
    "rps_lose": ["やったー！あたちたちの勝ち！次やる時は手加減ちてあげてもいいよ？なんてね！"],
    "rps_draw": ["あいこだね！あたちたち、案外相性ばっちりなのかも！"],
}

def get_reply(message: str, affection_level: int, user_name: str) -> str:
    msg = message.strip()
    if "おはよう" in msg: return random.choice(LINES["greeting_morning"]).replace("{name}", user_name)
    if any(x in msg for x in ["こんにちは", "やっほー"]): return random.choice(LINES["greeting_day"]).replace("{name}", user_name)
    if any(x in msg for x in ["こんばんは", "おやすみ"]): return random.choice(LINES["greeting_night"]).replace("{name}", user_name)
    return random.choice(LINES["normal"]).replace("{name}", user_name)

def get_nickname_line(action: str, user_name: str) -> str:
    key = "nickname_ask" if action == "ask" else "nickname_confirm"
    return random.choice(LINES.get(key, ["..."])).replace("{name}", user_name)

def get_rps_flavor(result: str, user_name: str) -> str:
    key = f"rps_{result}"
    return random.choice(LINES.get(key, ["..."])).replace("{name}", user_name)