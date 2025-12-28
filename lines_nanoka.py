import random

CHAR_NAME = "三月なのか"

PROFILE = {
    "first_person": "ウチ",
    "rps_duel_format": "{name}は **{user_hand}**、ウチは **{bot_hand}** だよ！",
    "rps_stats_format": "（これまでに {wins} 回、ウチに勝ったね！）",
}

LINES = {
    "normal": [
        "こんにちは〜。ねえ写真撮っていい？今日はまだアンタの写真撮ってないからさ。",
        "{name}、おっはよ〜う！！今日もまた朝が来たね。一日頑張っていこ〜！",
        "おっひるだよ〜。元気だしていこ〜！",
    ],
    
    "greeting_morning": ["{name}、おっはよ〜う！！今日もまた朝が来たね。一日頑張っていこ〜！"],
    "greeting_day": ["おっひるだよ〜。元気だしていこ〜！", "こんにちは〜。ねえ写真撮っていい？今日はまだアンタの写真撮ってないからさ。"],
    "greeting_night": ["ふわぁ〜。眠たい...。ウチは寝るから、おやすみ〜。"],
    
    # 好感度Lv3以上で解放されるセリフ
    "high_l3": [
        "{name}！偶然だね！今から遊びに行かない？大丈夫！そんなに遠くに行かないから！"
    ],

    "nickname_ask": ["なんて呼べばいい？"],
    "nickname_confirm": ["{name}ね。いい名前だね。改めてよろしくね！"],

    "rps_start": ["じゃんけん？いいよ！ウチは絶対負けないから！"],
    "rps_win": ["あ〜負けちゃった。次は絶対勝つから！もう一回やろ！"],
    "rps_lose": ["やった〜！勝った〜！もう一回やってもウチが勝つよ。"],
    "rps_draw": ["わ〜同じ手だ！ウチ達相性がいいのかもね。もう一回やろ！次は勝つから！"],
}

def _pick_high_affection_line(affection_level: int) -> str | None:
    if affection_level <= 0: return None
    # Lv3以上のときだけ high_l3 を候補に入れる
    if affection_level >= 3:
        return random.choice(LINES["high_l3"])
    return None

def get_reply(message: str, affection_level: int, user_name: str) -> str:
    msg = message.strip()
    
    if "おはよう" in msg:
        return random.choice(LINES["greeting_morning"]).replace("{name}", user_name)
    if any(x in msg for x in ["こんにちは", "やっほー"]):
        return random.choice(LINES["greeting_day"]).replace("{name}", user_name)
    if any(x in msg for x in ["こんばんは", "おやすみ"]):
        return random.choice(LINES["greeting_night"]).replace("{name}", user_name)
    
    # 好感度判定 (Lv3以上で30%の確率)
    if affection_level >= 3 and random.random() < 0.3:
        return _pick_high_affection_line(affection_level).replace("{name}", user_name)

    return random.choice(LINES["normal"]).replace("{name}", user_name)

def get_nickname_line(action: str, user_name: str) -> str:
    key = "nickname_ask" if action == "ask" else "nickname_confirm"
    return random.choice(LINES.get(key, ["..."])).replace("{name}", user_name)

def get_rps_flavor(result: str, user_name: str) -> str:
    key = f"rps_{result}"
    return random.choice(LINES.get(key, ["..."])).replace("{name}", user_name)