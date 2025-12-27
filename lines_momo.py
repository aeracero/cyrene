# lines_momo.py
import random

def get_reply(message: str, affection_level: int = 1) -> str:
    lines = [
        "……ん。呼んだ？",
        "小さい“昔のあたし”だけど、ちゃんと一緒にいるよ。",
        "ねぇ、離れないで。……今はまだ、それだけでいい。"
    ]
    return random.choice(lines)
