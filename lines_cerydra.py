import random

CHAR_NAME = "ケリュドラ"

# ★ キャラクター設定（一人称や語尾）
PROFILE = {
    "first_person": "僕",
    "rps_tail": "だな。",  # じゃんけん結果の末尾など
}

LINES = {
    "normal": [
        "楽にしてくれ。今日は天気が良い…一局どうだ？",
        "市場が騒がしいな…民が多いのは良い事だが、多すぎるのも困りものだ。{name}卿はどう考える？",
        "今日は宴会の予定があるのだ。{name}卿も剣旗卿と共にメーレを嗜んでみないか？",
        "「炎冠」、「独裁官」、「女皇」、「総帥」、「カイザー」…さまざまな異名があるが、お前は本当の名で呼ぶがいい——ケリュドラ、と",
        "駒には敵か味方かの2つしかないが、宇宙には黒と白だけでなく、多彩な色が存在する。オンパロスの終点は、銀河の旅路の始まりにすぎないのだ。いつか必ずや、遥かなる星々の彼方へと到達してみせよう。",
    ],
    # 好感度ボイス
    "high_l1": ["楽にしてくれ。今日は天気が良い…一局どうだ？"],
    "high_l2": ["市場が騒がしいな…民が多いのは良い事だが、多すぎるのも困りものだ。{name}卿はどう考える？"],
    "high_l3": ["今日は宴会の予定があるのだ。{name}卿も剣旗卿と共にメーレを嗜んでみないか？"],
    "high_l4": ["ふふ…{name}卿といると、時間を忘れそうになるな。"],
    "high_l5": ["ここまで付き合ってくれるとはな。{name}卿には、僕も本気で向き合わねばならないな。"],
    "high_l6": ["勝利の女神も運命卿も、もしかしたら{name}卿の味方なのかもしれないな…ふっ、悪くない。"],

    # あだ名関連
    "nickname_ask": ["ほう…僕の名付けよりも良い案があるのだな。言ってみろ。"],
    "nickname_confirm": ["良いでは無いか。今日からキミは{name}卿だな。"],

    # じゃんけん
    "rps_start": ["じゃんけんとは{name}卿も童心に帰る事があるのだな。チェスの相手もいないし良いだろう。"],
    "rps_win": [
        "どうやら勝利の女神は今回限りは僕に微笑まなかったようだな。だが次こそは勝ってみせるぞ。",
        "中々運が良いではないか{name}卿。今なら駿足卿との賭けにも勝てるのではないか？",
        "…運だけというのも面白くないだろう？どうだ{name}卿、チェスに興味は？",
    ],
    "rps_draw": [
        "ほう…白と黒だけでは面白くないが、決着がつかないというのももどかしいものだ。",
        "僕と同じ考えを持つとは賢いではないか{name}卿。",
        "勝敗がつかないか…なら次の戦いに備えるまでだ。",
    ],
    "rps_lose": [
        "どうした{name}卿？まさか僕が運命卿の力を借りたとでも思っているのか？",
        "やはり勝利の女神は僕に微笑んでいるようだ。過去も今も、未来さえも変わらずな。",
        "どうだ{name}卿。金織卿ですら、この僕には一回も勝てなかったんだぞ？",
    ],
}

def _pick_high_affection_line(affection_level: int) -> str | None:
    """好感度レベルに応じた重み付け抽選"""
    if affection_level <= 0: return None
    # LINESの中から high_l1, high_l2... を探す
    valid_tiers = []
    for k in LINES.keys():
        if k.startswith("high_l"):
            try:
                lv = int(k.replace("high_l", ""))
                if lv <= affection_level: valid_tiers.append(lv)
            except: pass
    
    if not valid_tiers: return None
    
    # 重み計算: 10 + (Lv * 10)
    weights = [10 + (t * 10) for t in valid_tiers]
    selected_tier = random.choices(valid_tiers, weights=weights, k=1)[0]
    return random.choice(LINES[f"high_l{selected_tier}"])

# 修正: user_name 引数を追加し、replace で名前を埋め込み
def get_reply(message: str, affection_level: int, user_name: str) -> str:
    # 抽選ロジック: Lv1~2:10%, Lv3:60%, Lv4~:70% で好感度ボイス
    high_prob = 0.1
    if affection_level == 3: high_prob = 0.6
    elif affection_level >= 4: high_prob = 0.7

    # メッセージが空（メンションのみ）、挨拶、甘える等の場合に判定
    msg_check = message.strip() == "" or any(x in message for x in ["こんにちは", "おはよう", "甘えて"])
    
    line = None
    if msg_check and random.random() < high_prob:
        line = _pick_high_affection_line(affection_level)
    
    if not line:
        line = random.choice(LINES["normal"])

    # ここで {name} を置き換えます
    return line.replace("{name}", user_name)

# 修正: user_name 引数を追加
def get_nickname_line(action: str, user_name: str) -> str:
    key = "nickname_ask" if action == "ask" else "nickname_confirm"
    line = random.choice(LINES.get(key, ["..."]))
    return line.replace("{name}", user_name)

# 修正: user_name 引数を追加
def get_rps_flavor(result: str, user_name: str) -> str:
    key = f"rps_{result}"
    line = random.choice(LINES.get(key, ["..."]))
    return line.replace("{name}", user_name)