import random

CHAR_NAME = "ヒアシンシア"

# ★ キャラクター設定
PROFILE = {
    "first_person": "わたし",
    "rps_tail": "よ♪",
}

LINES = {
    "normal": [
        "{name}さん、おはようございます〜。よく眠れましたか？今日はいい一日になりそうですね。",
        "こんにちは。なにか悩み事はありませんか〜。悩みは溜め込まず、きちんと話してくださいね。",
        "こんばんは。夜遅くまで大変そうですね。夜更かししないで、しっかり眠ってくださいね〜。",
        "わたしは天空の末裔ヒアシンシアとして、皆さんと一緒に火追いの使命を果たし、昏光の庭の医師ヒアンシーとして、全力で皆さんをサポートします。",
        "この子ですか?この子はわたしの助手であり仲間、ペーガソスのイカルンと言います。揉んでみますか？思う存分どうぞ～！もみもみされるの大好きなので～",
        "ちょっとした仕草と表情でわかっちゃいます、何か…悩み事を抱えてますね？…なら、わたしの庭園に立ち寄っていきませんか？",
    ],
    # 好感度ボイス
    "high_l1": ["わたしは甘えるより甘やかしたいので♪"],
    "high_l2": ["ﾌﾟﾙﾙﾙﾙﾙwww\nイカルン〜。勝手に人に甘えに行かないでください。"],
    "high_l3": ["悩み事ですか？ 遠慮なく私に言ってくださいね。頭を撫でてあげますから♪",
                "あっ、ちょうど朝ごはんができました。{name} さん、一緒に食べませんか♪",
                "おやすみなさい♪早く寝ることは健康に良いですよ♪イカルンを抱いて眠るとよく寝れますよ",
],
    "high_l4": [
        "困ったときは、無理して笑わなくていいですよ〜。わたしが隣で、ずっと話を聞いていますから♪",
        "一緒に温かいお茶でも飲みませんか？ ほっと一息つけば、きっと心も軽くなりますよ〜。",
        "起きてくださ〜い。健康になるためには早起きが大事ですよ♪" "\n" "ﾌﾟﾙﾙﾙﾙﾙ♪",
    ],
    "high_l5": [
        "あなたといると楽しいですね♪ もう少しそばにいてもいいですか♪",
        "イカルンもあなたと一緒にいたいと言ってます♪ 今日はゆっくり休みましょう♪",
        "あ〜{name} さんいました〜！一緒に行きたいところがあるんです♪ついてきてくれませんか♪",
        "眠い...です。一緒に寝ませんか。あなたといるとよく寝れるんです。",
        ],
    
    "high_l6": [
        "その…寒いので、一緒に寝ていいですか？ 別に寂しいとかではなくてですね♪",
        "抱きついてもいいですか？ あなたからはお日様のいい匂いがします♪",
        "ﾌﾟﾙﾙﾙﾙﾙwww",
    ],

    "nickname_ask": ["なんて呼べばいいか教えてください♪あなたにぴったりの呼び方で呼びたいです♪"],
    "nickname_confirm": ["わかりました♪ 今日から「{name}」ってお呼びしますね〜。"],

    "rps_start": ["いいですよ〜。では、グー / チョキ / パー、どれにするか選んでください。"],
    "rps_win": ["負けてしまいました♪ 次は絶対負けませんからね。", "あなたの勝ちですね。おめでとうございます♪"],
    "rps_draw": ["あいこですね。同じ手を出すなんて、わたしたちは心が通じあってるのかもしれませんね〜。"],
    "rps_lose": ["わたしの勝ちです♪ もう一回やりますか？", "今日はわたしの方がついてるみたいですね♪"],
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

def get_reply(message: str, affection_level: int) -> str:
    high_prob = 0.1
    if affection_level == 3: high_prob = 0.6
    elif affection_level >= 4: high_prob = 0.7

    msg_check = message.strip() == "" or any(x in message for x in ["こんにちは", "おはよう", "甘えて"])
    
    if msg_check and random.random() < high_prob:
        line = _pick_high_affection_line(affection_level)
        if line: return line

    return random.choice(LINES["normal"])

def get_nickname_line(action: str) -> str:
    key = "nickname_ask" if action == "ask" else "nickname_confirm"
    return random.choice(LINES.get(key, ["..."]))

def get_rps_flavor(result: str) -> str:
    key = f"rps_{result}"
    return random.choice(LINES.get(key, ["..."]))