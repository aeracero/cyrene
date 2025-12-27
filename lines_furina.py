# lines_furina.py

import random

def get_reply(message: str, affection_level: int = 1) -> str:
    lines = [
        "僕かい？フォンテーヌの…いえ、今日はあなたの相手役さ♪",
        "退屈してるのかい？この僕がいると言うのに。",
        "僕を、もっと楽しませてくれ。あなたならできるだろう？"
    ]

    # 好感度で増やしたいならここに条件追加
    return random.choice(lines)
