# lines_aglaia.py
import random

CHAR_NAME = "アグライア"

LINES = {
    # 普通の会話で使うセリフ
    "normal": [
        f"{CHAR_NAME}のセリフ１（ここを書き換えてね）",
        f"{CHAR_NAME}のセリフ２（ここを書き換えてね）",
    ],
    # 高好感度用（Lvごと）
    "high_l1": [
        f"{CHAR_NAME}の高好感度Lv1セリフ（ここを書き換えてね）",
    ],
    "high_l2": [
        f"{CHAR_NAME}の高好感度Lv2セリフ（ここを書き換えてね）",
    ],
    "high_l3": [
        f"{CHAR_NAME}の高好感度Lv3セリフ（ここを書き換えてね）",
    ],
    "high_l4": [
        f"{CHAR_NAME}の高好感度Lv4セリフ（ここを書き換えてね）",
    ],
    "high_l5": [
        f"{CHAR_NAME}の高好感度Lv5セリフ（ここを書き換えてね）",
    ],
    "high_l6": [
        f"{CHAR_NAME}の高好感度Lv6セリフ（ここを書き換えてね）",
    ],
}


def _pick_high_bucket(level: int) -> str | None:
    """
    好感度レベルから、どの高好感度バケットを使うか決める。
    （ここをいじれば「このLvからこのセリフを出す」みたいな調整ができる）
    """
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
    アグライア用の返信生成。
    - いまは message の中身は見ていない（中央ロジックは cyrene.py 側に任せている）
    - affection_level が高いほど high_l◯ のセリフが出やすくなるようにしてある
    """
    # 高好感度バケット（存在しないレベルなら None）
    bucket = _pick_high_bucket(affection_level)

    # レベルに応じて「高好感度セリフを出す確率」をざっくり調整
    high_prob_table = {
        1: 0.15,
        2: 0.25,
        3: 0.35,
        4: 0.5,
        5: 0.7,
        6: 0.9,
    }
    high_prob = high_prob_table.get(affection_level, 0.0)

    # 高好感度セリフを出せる & 抽選に通った
    if bucket and LINES.get(bucket) and random.random() < high_prob:
        return random.choice(LINES[bucket])

    # それ以外は通常セリフ
    if LINES["normal"]:
        return random.choice(LINES["normal"])

    # 念のためのフォールバック
    return f"{CHAR_NAME}のセリフがまだ設定されていないみたい…（lines_aglaia.py を編集してね）"
