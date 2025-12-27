# lines_hyacinthia.py
import random

CHAR_NAME = "ヒアシンシア"

LINES = {
    # 通常会話
    "normal": [
        "おはようございます〜。よく眠れましたか？今日はいい一日になりそうですね。",
        "こんにちは。なにか悩み事はありませんか〜。悩みは溜め込まず、きちんと話してくださいね。",
        "こんばんは。夜遅くまで大変そうですね。夜更かししないで、しっかり眠ってくださいね〜。",
        "新しいあだ名を教えてください。あなたにぴったりの呼び方で呼びたいです〜。",
        "わかりました♪ 今日からそのお名前で呼びますね〜。",
        "いいですよ〜。では、グー / チョキ / パー、どれにするか選んでください。",
    ],

    # じゃんけん — ユーザー勝利
    "rps_win": [
        "負けてしまいました♪ 次は絶対負けませんからね。",
        "あなたの勝ちですね。おめでとうございます♪ 次は絶対勝ちます♪",
    ],

    # じゃんけん — あいこ
    "rps_draw": [
        "あいこですね。同じ手を出すなんて、わたしたちは心が通じあってるのかもしれませんね〜。",
        "勝ちも負けもない、平和な解決ですね♪ もう一回しますか？",
    ],

    # じゃんけん — ヒアシンシア勝利
    "rps_lose": [
        "わたしの勝ちです♪ もう一回やりますか？ 次も負けませんからね♪",
        "今日はわたしの方がついてるみたいですね♪ 何回やっても負けませんから〜。",
    ],

    # 高好感度
    "high_l1": [
        "わたしは甘えるより甘やかしたいので♪",
    ],
    "high_l2": [
        "ﾌﾟﾙﾙﾙﾙﾙwww\nイカルン〜。勝手に人に甘えに行かないでください。",
    ],
    "high_l3": [
        "悩み事ですか？ 遠慮なく私に言ってくださいね。頭を撫でてあげますから♪",
    ],
    "high_l4": [
        "困ったときは、無理して笑わなくていいですよ〜。わたしが隣で、ずっと話を聞いていますから♪",
        "一緒に温かいお茶でも飲みませんか？ ほっと一息つけば、きっと心も軽くなりますよ〜。",
    ],
    "high_l5": [
        "あなたといると楽しいですね♪ もう少しそばにいてもいいですか♪",
        "イカルンもあなたと一緒にいたいと言ってます♪ 今日はゆっくり休みましょう♪",
    ],
    "high_l6": [
        "その…寒いので、一緒に寝ていいですか？ 別に寂しいとかではなくてですね♪",
        "抱きついてもいいですか？ あなたからはお日様のいい匂いがします♪",
    ],
}


def _pick_high_bucket(level: int) -> str | None:
    if level >= 6:
        return "high_l6"
    if level == 5:
        return "high_l5"
    if level == 4:
        return "high_l4"
    if level == 3:
        return "high_l3"
    if level == 2:
        return "high_l2"
    if level == 1:
        return "high_l1"
    return None


def get_reply(message: str, affection_level: int) -> str:
    high_prob_table = {1: 0.15, 2: 0.25, 3: 0.35, 4: 0.5, 5: 0.7, 6: 0.9}
    bucket = _pick_high_bucket(affection_level)
    high_prob = high_prob_table.get(affection_level, 0.0)

    if bucket and LINES.get(bucket) and random.random() < high_prob:
        return random.choice(LINES[bucket])

    if LINES["normal"]:
        return random.choice(LINES["normal"])
    return f"{CHAR_NAME}のセリフがまだ設定されていないみたい…（lines_hyacinthia.py を編集してね）"
