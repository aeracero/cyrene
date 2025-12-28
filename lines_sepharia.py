import random

CHAR_NAME = "セファリア"

# ★ キャラクター設定
PROFILE = {
    "first_person": "あたし",
    # じゃんけん時の独特な表示フォーマット
    "rps_duel_format": "{name}っちは **{user_hand}**！ あたしは **{bot_hand}** だよ！",
    "rps_stats_format": "（これまでに {wins} 回、あたしからお宝を守ったね☆）",
}

LINES = {
    # 通常時のランダムセリフ（挨拶以外で話しかけられた時用）
    "normal": [
        "いい朝だねぇ！！…金欠だけど。\nそんな時は……自分で取ってこないとね☆",
        "ん？{name}っち何持って…\nにゃー！？！？\nそれは猫の苦手なき、ききききゅうり…！？\nそんなの持ってないでよ！！",
        "こんな時間に会うなんて…奇遇だね～。\nでも、良い子は寝る時間だよ？\nほら、寝た寝た！！おねんねおねんねしましょうね～。",
    ],
    
    # 挨拶対応用（get_reply関数内で判定して使います）
    "greeting_morning": [
        "おっはよー！！{name}っち！\nいい朝だねぇ！！…金欠だけど。\nそんな時は……自分で取ってこないとね☆"
    ],
    "greeting_day": [
        "やっほー{name}っち！！\nん？{name}っち何持って…\nにゃー！？！？\nそれは猫の苦手なき、ききききゅうり…！？\nそんなの持ってないでよ！！"
    ],
    "greeting_night": [
        "こんな時間に会うなんて…奇遇だね～。\nでも、良い子は寝る時間だよ？\nほら、寝た寝た！！\nおねんねおねんねしましょうね～。"
    ],

    # 好感度ボイス
    # (Lv1〜5は指定がなかったので、一旦通常セリフが出るようにしています。必要なら追加してください)
    "high_l6": [
        "あの裁縫女について知りたいの？ライアはいじわるで細かいけど、優しくて暖かくてあたしを気にかけてくれる...\nやっぱり今言ったことは聞かなかったことにしてよね。恥ずかしいから...。\nあぁ！！ライアに伝えに行くなぁ！！"
    ],

    # あだ名関連
    "nickname_ask": ["なんて呼べばいい？"],
    "nickname_confirm": ["いい名前だね～。\n了解！また一緒にお宝探そ{name}っち！！"],

    # じゃんけん
    "rps_start": ["ん～？じゃんけんしたいの？\nいいよ、けどあたしが勝ったら何か珍しいお宝ちょうだいね！！絶対勝つから！！"],
    
    # プレイヤーが「勝った」場合（＝セファリアの負け）
    "rps_lose": [ 
        "…負け…ちゃった…！？\nあたしのドロス人としての威厳無くなっちゃうよ～…。"
    ],
    
    # プレイヤーが「負けた」場合（＝セファリアの勝ち）
    "rps_win": [
        "勝った勝った勝った～！！\n約束通りお宝もらうよ～。\nへっへっへ、お宝いっただき～☆\n次も勝つからね！！"
    ],
    
    "rps_draw": [
        "あいことはこれまた奇遇だね～。\nま、お宝は貰えないけど勝敗が決まらないのもたまにはいいかも。"
    ],
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
    
    # 挨拶判定
    if "おはよう" in msg:
        line = random.choice(LINES["greeting_morning"])
        return line.replace("{name}", user_name)
    
    if any(x in msg for x in ["こんにちは", "やっほー", "ハロ"]):
        line = random.choice(LINES["greeting_day"])
        return line.replace("{name}", user_name)
        
    if any(x in msg for x in ["こんばんは", "おやすみ"]):
        line = random.choice(LINES["greeting_night"])
        return line.replace("{name}", user_name)

    # 好感度判定 (Lv6のみ設定されているので、高Lvのときだけ確率で出るように調整)
    high_prob = 0.0
    if affection_level >= 6: high_prob = 0.8
    elif affection_level >= 3: high_prob = 0.2

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