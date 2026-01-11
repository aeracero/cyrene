# cthulhu_game.py
import random
import string
import database as db

# 状態定義
STATE_CTHULHU_LOBBY = "cthulhu_lobby"
STATE_CTHULHU_ROOM = "cthulhu_room"

# ルームデータ管理 {room_code: {"owner": id, "members": [ids], "topic": str}}
CTHULHU_ROOMS = {}
# ユーザーがどのルームにいるか {user_id: room_code}
USER_ROOM_MAP = {}
# ユーザーのセッション状態
CTHULHU_SESSIONS = {}

def generate_room_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))

def start_cthulhu_session(user_id):
    CTHULHU_SESSIONS[user_id] = {"state": STATE_CTHULHU_LOBBY}

def process_cthulhu_command(user_id, content, raw_name):
    if user_id not in CTHULHU_SESSIONS:
        if "天外からのゲームやってみる？" in content:
            start_cthulhu_session(user_id)
            return "【天外からの探索者】へようこそ…。\n『ルーム作成』で新しい物語を紡ぐか、『ルーム参加 [コード]』で既存の狂気に飛び込めるわよ。♪", []
        return None

    session = CTHULHU_SESSIONS[user_id]
    state = session["state"]
    lang = db.get_user_lang(user_id)

    # 共通：終了処理
    if content in ["終了", "戻る", "やめる"]:
        if user_id in USER_ROOM_MAP:
            code = USER_ROOM_MAP.pop(user_id)
            if code in CTHULHU_ROOMS:
                CTHULHU_ROOMS[code]["members"].remove(user_id)
                if not CTHULHU_ROOMS[code]["members"]:
                    del CTHULHU_ROOMS[code]
        del CTHULHU_SESSIONS[user_id]
        return "現実の世界へおかえりなさい。またいつでも呼んでね。♪", []

    # --- ロビー状態 ---
    if state == STATE_CTHULHU_LOBBY:
        if "ルーム作成" in content:
            code = generate_room_code()
            CTHULHU_ROOMS[code] = {"owner": user_id, "members": [user_id], "topic": "未設定"}
            USER_ROOM_MAP[user_id] = code
            session["state"] = STATE_CTHULHU_ROOM
            return f"ルームを作成したわ！コードは **{code}** よ。\n他の人にこのコードを教えてあげて。\n\n『お題設定 [内容]』で状況を決めたり、『ダイス』で運命を試せるわよ。♪", []

        if content.startswith("ルーム参加"):
            code = content.replace("ルーム参加", "").strip().upper()
            if code in CTHULHU_ROOMS:
                CTHULHU_ROOMS[code]["members"].append(user_id)
                USER_ROOM_MAP[user_id] = code
                session["state"] = STATE_CTHULHU_ROOM
                owner_id = CTHULHU_ROOMS[code]["owner"]
                return f"ルーム **{code}** に参加したわ。…何かが視える気がしない？\n(現在の参加者: {len(CTHULHU_ROOMS[code]['members'])}名)", [(owner_id, f"新たな探索者、{raw_name} が合流したわよ。")]
            return "そのコードのルームは見当たらないみたい。もう一度確認してみて？", []

    # --- ルーム内状態 ---
    if state == STATE_CTHULHU_ROOM:
        code = USER_ROOM_MAP.get(user_id)
        if not code or code not in CTHULHU_ROOMS:
            session["state"] = STATE_CTHULHU_LOBBY
            return "ルームが消失したみたい。ロビーに戻るわね。", []
        
        room = CTHULHU_ROOMS[code]

        # お題設定
        if content.startswith("お題設定"):
            topic = content.replace("お題設定", "").strip()
            room["topic"] = topic
            msg = f"今回の物語のお題は『{topic}』に決まったわ。"
            others = [(uid, f"お題が更新されたわ：{topic}") for uid in room["members"] if uid != user_id]
            return msg, others

        # ダイスロール (1d100)
        if content == "ダイス" or "振る" in content:
            roll = random.randint(1, 100)
            result = ""
            if roll <= 5: result = "【決定的成功】！奇跡が起きたわね！"
            elif roll <= 50: result = "【成功】よ。運が味方したみたい。"
            elif roll >= 96: result = "【致命的失敗】…嫌な予感がするわ。"
            else: result = "【失敗】ね。狂気がじわじわと迫っているわ…。"
            
            msg = f"運命のダイスロール：**{roll}** / 100\n{result}"
            others = [(uid, f"{raw_name} のダイス：{roll} ({result})") for uid in room["members"] if uid != user_id]
            return msg, others

        # 状況確認
        if content == "状況":
            members_str = ", ".join([f"<@{uid}>" for uid in room["members"]])
            return f"【ルーム: {code}】\nお題: {room['topic']}\n参加者: {members_str}", []

    return "『お題設定』『ダイス』『状況』、それか『終了』で元の世界に戻れるわよ。♪", []