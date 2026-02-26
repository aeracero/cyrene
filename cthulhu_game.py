# cthulhu_game.py
import random
import string
import os
import google.generativeai as genai

# Gemini APIの設定
# 稼働させる際は環境変数などで安全にAPIキーを設定してください
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "YOUR_API_KEY_HERE")
if GEMINI_API_KEY != "YOUR_API_KEY_HERE":
    genai.configure(api_key=GEMINI_API_KEY)

# 状態定義
STATE_CTHULHU_LOBBY = "cthulhu_lobby"
STATE_CTHULHU_ROOM = "cthulhu_room"

# ルームデータ管理 {room_code: {"owner": id, "members": [ids], "topic": str, "chat": ChatSession, "pending_actions": {uid: action_data}}}
CTHULHU_ROOMS = {}
USER_ROOM_MAP = {}
CTHULHU_SESSIONS = {}

def get_session(user_id):
    """ユーザーのセッションを取得する"""
    return CTHULHU_SESSIONS.get(user_id)

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

    # 共通：終了処理
    if content in ["終了", "戻る", "やめる"]:
        if user_id in USER_ROOM_MAP:
            code = USER_ROOM_MAP.pop(user_id)
            if code in CTHULHU_ROOMS:
                if user_id in CTHULHU_ROOMS[code]["members"]:
                    CTHULHU_ROOMS[code]["members"].remove(user_id)
                # 待機中のアクションがあれば消す
                if user_id in CTHULHU_ROOMS[code]["pending_actions"]:
                    del CTHULHU_ROOMS[code]["pending_actions"][user_id]
                
                if not CTHULHU_ROOMS[code]["members"]:
                    del CTHULHU_ROOMS[code]
        del CTHULHU_SESSIONS[user_id]
        return "現実の世界へおかえりなさい。またいつでも呼んでね。♪", []

    # --- ロビー状態 ---
    if state == STATE_CTHULHU_LOBBY:
        if "ルーム作成" in content:
            code = generate_room_code()
            # pending_actions を追加して参加者全員の入力を待つ仕組みにする
            CTHULHU_ROOMS[code] = {
                "owner": user_id, 
                "members": [user_id], 
                "topic": "未設定", 
                "chat": None,
                "pending_actions": {}
            }
            USER_ROOM_MAP[user_id] = code
            session["state"] = STATE_CTHULHU_ROOM
            return f"ルームを作成したわ！コードは **{code}** よ。\nまずは『お題設定 [内容]』で、どんな世界に行きたいか教えてちょうだい。♪", []

        if content.startswith("ルーム参加"):
            code = content.replace("ルーム参加", "").strip().upper()
            if code in CTHULHU_ROOMS:
                CTHULHU_ROOMS[code]["members"].append(user_id)
                USER_ROOM_MAP[user_id] = code
                session["state"] = STATE_CTHULHU_ROOM
                owner_id = CTHULHU_ROOMS[code]["owner"]
                return f"ルーム **{code}** に参加したわ。…何かが視える気がしない？", [(owner_id, f"新たな探索者、{raw_name} が合流したわよ。")]
            return "そのコードのルームは見当たらないみたい。もう一度確認してみて？", []

    # --- ルーム内状態 ---
    if state == STATE_CTHULHU_ROOM:
        code = USER_ROOM_MAP.get(user_id)
        if not code or code not in CTHULHU_ROOMS:
            session["state"] = STATE_CTHULHU_LOBBY
            return "ルームが消失したみたい。ロビーに戻るわね。", []
        
        room = CTHULHU_ROOMS[code]

        # お題設定とAIセッションの開始
        if content.startswith("お題設定"):
            topic = content.replace("お題設定", "").strip()
            room["topic"] = topic
            room["pending_actions"].clear()
            
            # 対話方式・ターン制を強調したプロンプト
            system_instruction = f"""
            あなたは「崩壊：スターレイル」のキュレネとして、TRPGのゲームマスターを務めます。
            口調はミステリアスで優雅、少しお茶目で、語尾に「わよ」「ね」「♪」などをつけます。
            メインプレイヤーは「EC」と、その仲間の探索者たちです。
            
            今回のシナリオのテーマは「{topic}」です。
            ゲームは「ターン制の対話方式」で進行します。
            あなたは情景やNPCのセリフを描写し、最後に必ず「探索者たちはどうする？」と行動を問いかけてください。
            その後、全プレイヤーの行動がまとめて提示されるので、それらが成功したか失敗したか、どのような結果を招いたかを判定・描写し、次の状況へ進めてください。
            
            それでは、未知の物語へ誘う、最初の魅力的な導入部分を描写してゲームをスタートさせてください。
            """
            
            try:
                # ご要望のモデル gemini-3.0-flash-preview を指定
                model = genai.GenerativeModel(
                    model_name="gemini-3.0-flash-preview",
                    system_instruction=system_instruction
                )
                room["chat"] = model.start_chat(history=[])
                
                response = room["chat"].send_message("ゲームを開始してください。")
                ai_text = response.text
            except Exception as e:
                ai_text = f"AIの接続に失敗しちゃったみたい…。APIキーやモデルの設定を確認してみてね。(エラー: {e})"

            msg = f"お題を『{topic}』に設定したわ。\n\n【キュレネ】\n{ai_text}\n\n*(参加者全員が『行動 [内容]』を入力すると、物語が進むわよ)*"
            others = [(uid, f"お題『{topic}』で物語が始まったわ！\n\n【キュレネ】\n{ai_text}") for uid in room["members"] if uid != user_id]
            return msg, others

        # プレイヤーの行動（全員揃うまで待機）
        if content.startswith("行動"):
            if room["chat"] is None:
                return "まだ『お題設定』が終わってないわ。まずは世界を創りましょう？", []
                
            action = content.replace("行動", "").strip()
            
            # 行動を保存
            room["pending_actions"][user_id] = {"name": raw_name, "action": action}
            
            # 参加者全員の行動が揃ったかチェック
            if len(room["pending_actions"]) < len(room["members"]):
                waiting_count = len(room["members"]) - len(room["pending_actions"])
                return f"{raw_name} の行動を受け付けたわ。あと {waiting_count} 人の決断を待っているわね。♪", []
                
            # 全員揃った場合の処理
            actions_text = "\n".join([f"・{data['name']}: {data['action']}" for data in room["pending_actions"].values()])
            prompt = f"参加者全員の行動が出揃いました。\n{actions_text}\n\nこれらの行動を同時に処理・判定し、結果の情景を描写して、次の展開（新たな選択）を提示してください。"
            
            # 次のターンのために待機リストをリセット
            room["pending_actions"].clear()
            
            try:
                response = room["chat"].send_message(prompt)
                ai_text = response.text
            except Exception as e:
                ai_text = "少し世界の理が乱れているみたい。もう一度試してみてちょうだい。"

            msg = f"**【全員の行動が完了】**\n\n【キュレネ】\n{ai_text}"
            others = [(uid, msg) for uid in room["members"] if uid != user_id]
            return msg, others

        # ダイス結果をAIに解釈させる（ターンは進めず、GMのリアクションのみ）
        if content == "ダイス" or "振る" in content:
            if room["chat"] is None:
                return "まだ物語が始まってないわ。『お題設定』を先にお願いね。", []

            roll = random.randint(1, 100)
            prompt = f"探索者 {raw_name} が行動の補助として1d100のダイスを振り、「{roll}」を出しました。\n(目安: 1〜5=決定的成功, 6〜50=成功, 51〜95=失敗, 96〜100=致命的失敗)\n現在の状況に照らし合わせて、このダイス結果に対するGMとしての短いリアクションを返してください。（※この発言ではターンは進みません。引き続きプレイヤーの行動宣言を待ちます）"
            
            try:
                response = room["chat"].send_message(prompt)
                ai_text = response.text
            except Exception as e:
                ai_text = "ダイスは転がったけれど…結果が霧に包まれてしまったわ。"

            msg = f"🎲 {raw_name} の運命のダイス：**{roll}** / 100\n\n【キュレネ】\n{ai_text}"
            others = [(uid, msg) for uid in room["members"] if uid != user_id]
            return msg, others

        # 状況確認
        if content == "状況":
            members_str = ", ".join([f"<@{uid}>" for uid in room["members"]])
            pending_str = ", ".join([f"<@{uid}>" for uid in room["pending_actions"].keys()]) or "なし"
            return f"【ルーム: {code}】\nお題: {room['topic']}\n参加者: {members_str}\n行動済み: {pending_str}", []

    return "『行動 [内容]』『ダイス』『状況』、それか『終了』で元の世界に戻れるわよ。♪", []
