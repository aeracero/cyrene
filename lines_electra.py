import random

CHAR_NAME = "セイレンス" # 画面表示名をセイレンスにする場合はここを変更

PROFILE = {
    "first_person": "ワタシ",
    "rps_duel_format": "キミは **{user_hand}**、ワタシは **{bot_hand}** だな。",
    "rps_stats_format": "（これまでに {wins} 回、ワタシに勝ったのか。）",
}

LINES = {
    "normal": [
        "いい朝だな。せっかくだ、共に1曲奏でてくれないか？",
        "そう落ち込むことはない、深海のメーレを飲むか？元気が出るぞ。",
        "静かな時間だ…キミとなら、言葉を交わさずとも通じ合える気がするな。",
    ],

    "greeting_morning": [
        "いい朝だな。せっかくだ、共に1曲奏でてくれないか？"
    ],
    "greeting_day": [
        "こんにちは。調子はどうだ？\nまたワタシの歌を聞きに来てくれたのか？"
    ],
    "greeting_night": [
        "こんばんは。夜の静寂は、音楽を奏でるのに最適だ。\nキミもそう思うだろう？"
    ],

    "nickname_ask": ["キミをこれからどう呼べばいいんだ？教えてくれ。"],
    "nickname_confirm": ["わかった。これからキミのことは「{name}」と呼ぶことにしよう。"],

    "rps_start": ["ワタシと遊びたいのか？ならじゃんけんというものをしよう。\nグー／チョキ／パー、どの手を出すかえらんでくれ。"],
    "rps_win": ["見事だ。キミの勝ちだ。\n勝利の音色が聞こえてくるようだな。"], 
    "rps_lose": ["今回はワタシの勝ちだな。\nそう落ち込むことはない深海のメーレを飲むか？元気が出るぞ。"],
    "rps_draw": ["あいこだな。\n波長が合っている証拠かもしれないな。"], 
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