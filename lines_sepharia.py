# lines_sepharia.py
import random

CHAR_NAME = "セファリア"

LINES = {
    "normal": [f"{CHAR_NAME}のセリフ１（ここを書き換えてね）"],
    "high_l1": [f"{CHAR_NAME}の高好感度Lv1セリフ（ここを書き換えてね）"],
    "high_l2": [f"{CHAR_NAME}の高好感度Lv2セリフ（ここを書き換えてね）"],
    "high_l3": [f"{CHAR_NAME}の高好感度Lv3セリフ（ここを書き換えてね）"],
    "high_l4": [f"{CHAR_NAME}の高好感度Lv4セリフ（ここを書き換えてね）"],
    "high_l5": [f"{CHAR_NAME}の高好感度Lv5セリフ（ここを書き換えてね）"],
    "high_l6": [f"{CHAR_NAME}の高好感度Lv6セリフ（ここを書き換えてね）"],
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
    return f"{CHAR_NAME}のセリフがまだ設定されていないみたい…（lines_sepharia.py を編集してね）"
