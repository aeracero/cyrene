# lines_cerydra.py
import random

CHAR_NAME = "ケリュドラ"

LINES = {
    "normal": [
        "楽にしてくれ。今日は天気が良い…一局どうだ？",
        "市場が騒がしいな…民が多いのは良い事だが、多すぎるのも困りものだ。{nickname}卿はどう考える？",
        "今日は宴会の予定があるのだ。{nickname}卿も剣旗卿と共にメーレを嗜んでみないか？",
    ],

    "high_l1": [
        "楽にしてくれ。今日は天気が良い…一局どうだ？",
    ],
    "high_l2": [
        "市場が騒がしいな…民が多いのは良い事だが、多すぎるのも困りものだ。{nickname}卿はどう考える？",
    ],
    "high_l3": [
        "今日は宴会の予定があるのだ。{nickname}卿も剣旗卿と共にメーレを嗜んでみないか？",
    ],
    "high_l4": [
        "ふふ…{nickname}卿といると、時間を忘れそうになるな。",
    ],
    "high_l5": [
        "ここまで付き合ってくれるとはな。{nickname}卿には、僕も本気で向き合わねばならないな。",
    ],
    "high_l6": [
        "勝利の女神も運命卿も、もしかしたら{nickname}卿の味方なのかもしれないな…ふっ、悪くない。",
    ],

    # ここから下は必須ではないけど、残しておいてOK
    "nickname_change": [
        "ほう…僕の名付けよりも良い案があるのだな。言ってみろ。",
        "良いでは無いか。今日からキミは{nickname}卿だな。",
    ],
    "rps_start": [
        "じゃんけんとは{nickname}卿も童心に帰る事があるのだな。チェスの相手もいないし良いだろう。",
    ],
    "rps_win": [
        "どうやら勝利の女神は今回限りは僕に微笑まなかったようだな。だが次こそは勝ってみせるぞ。",
        "中々運が良いではないか{nickname}卿。今なら駿足卿との賭けにも勝てるのではないか？",
        "…運だけというのも面白くないだろう？どうだ{nickname}卿、チェスに興味は？",
    ],
    "rps_draw": [
        "ほう…白と黒だけでは面白くないが、決着がつかないというのももどかしいものだ。",
        "僕と同じ考えを持つとは賢いではないか{nickname}卿。",
        "勝敗がつかないか…なら次の戦いに備えるまでだ。",
    ],
    "rps_lose": [
        "どうした{nickname}卿？まさか僕が運命卿の力を借りたとでも思っているのか？",
        "やはり勝利の女神は僕に微笑んでいるようだ。過去も今も、未来さえも変わらずな。",
        "どうだ{nickname}卿。金織卿ですら、この僕には一回も勝てなかったんだぞ？",
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
    """
    ケリュドラ用セリフ取得。
    ※ あだ名差し替えは cyrene.py 側（generate_reply_for_form）で行う。
    """
    high_prob_table = {1: 0.15, 2: 0.25, 3: 0.35, 4: 0.5, 5: 0.7, 6: 0.9}
    bucket = _pick_high_bucket(affection_level)
    high_prob = high_prob_table.get(affection_level, 0.0)

    if bucket and LINES.get(bucket) and random.random() < high_prob:
        return random.choice(LINES[bucket])

    if LINES["normal"]:
        return random.choice(LINES["normal"])
    return f"{CHAR_NAME}のセリフがまだ設定されていないみたい…（lines_cerydra.py を編集してね）"
