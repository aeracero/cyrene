# lines_cerydra.py
import random

CHAR_NAME = "ケリュドラ"

LINES = {
    "normal": [
        "楽にしてくれ。今日は天気が良い…一局どうだ？",
        "市場が騒がしいな…民が多いのは良い事だが、多すぎるのも困りものだ。{nickname}卿はどう考える？",
        "今日は宴会の予定があるのだ。{nickname}卿も剣旗卿と共にメーレを嗜んでみないか？",
    ],

    # 高好感度
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

    # あだ名変更関連（必要なら使う用）
    "nickname_change": [
        "ほう…僕の名付けよりも良い案があるのだな。言ってみろ。",
        "良いでは無いか。今日からキミは{nickname}卿だな。",
    ],

    # じゃんけん開始
    "rps_start": [
        "じゃんけんか。{nickname}卿も童心に帰ることがあるのだな。良いだろう、一局付き合おう。",
        "暇つぶしには悪くないな。{nickname}卿、グー / チョキ / パー、好きな手を選ぶといい。",
    ],

    # ユーザー勝ち
    "rps_win": [
        "どうやら勝利の女神は今回限りは僕に微笑まなかったようだな。だが次こそは勝ってみせるぞ。",
        "中々運が良いではないか、{nickname}卿。今なら駿足卿との賭けにも勝てるのではないか？",
        "…運だけというのも面白くないだろう？ どうだ、{nickname}卿。チェスに興味は？",
    ],

    # あいこ
    "rps_draw": [
        "ほう…白と黒だけでは面白くないが、決着がつかないというのももどかしいものだ。",
        "僕と同じ考えを持つとは賢いではないか、{nickname}卿。",
        "勝敗がつかないか…なら次の戦いに備えるまでだ。",
    ],

    # ユーザー負け
    "rps_lose": [
        "どうした、{nickname}卿？ まさか僕が運命卿の力を借りたとでも思っているのか？",
        "やはり勝利の女神は僕に微笑んでいるようだ。過去も今も、未来さえも変わらずな。",
        "どうだ、{nickname}卿。金織卿ですら、この僕には一回も勝てなかったんだぞ？",
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
    通常会話用（ヒアシンシアと同じインターフェース）
    """
    high_prob_table = {1: 0.15, 2: 0.25, 3: 0.35, 4: 0.5, 5: 0.7, 6: 0.9}
    bucket = _pick_high_bucket(affection_level)
    high_prob = high_prob_table.get(affection_level, 0.0)

    # 高好感度セリフ抽選
    if bucket and LINES.get(bucket) and random.random() < high_prob:
        return random.choice(LINES[bucket])

    # 通常セリフ
    if LINES["normal"]:
        return random.choice(LINES["normal"])

    return f"{CHAR_NAME}のセリフがまだ設定されていないみたい…（lines_cerydra.py を編集してね）"


def get_rps_start_line() -> str:
    """
    じゃんけん開始のセリフ（ケリュドラ用）
    """
    arr = LINES.get("rps_start") or []
    if not arr:
        return "じゃんけんか。良いだろう、一局だけ付き合おう。"
    return random.choice(arr)


def get_rps_result_line(result: str) -> str:
    """
    じゃんけん結果（win/draw/lose）に応じたセリフ（ケリュドラ用）
    """
    if result == "win":
        key = "rps_win"
    elif result == "lose":
        key = "rps_lose"
    else:
        key = "rps_draw"

    arr = LINES.get(key) or []
    if not arr:
        return "ふ…この勝敗も、いつか語り草になるかもしれないな。"
    return random.choice(arr)
