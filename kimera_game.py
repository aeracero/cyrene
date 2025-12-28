# kimera_game.py
import random
import re
import kimera_core as core
import kimera_data as data

# --- 状態定義 ---
STATE_MENU = "menu"
STATE_SHOP = "shop"
STATE_BATTLE_SELECT = "battle_select"
STATE_BATTLE_WILD = "battle_wild"      # 野生
STATE_BATTLE_TRAINER = "battle_trainer" # CPU
STATE_BATTLE_PVP_LOBBY = "battle_pvp_lobby" # PvP相手待ち
STATE_BATTLE_PVP = "battle_pvp"       # PvP戦闘中

# 戦闘中のサブステート
BATTLE_SUB_MAIN = "main"    # コマンド選択
BATTLE_SUB_ITEM = "item"    # 道具選択
BATTLE_SUB_SWITCH = "switch"# 入れ替え選択
BATTLE_SUB_FORCE_SWITCH = "force_switch" # 瀕死時の強制入れ替え
BATTLE_SUB_WAIT = "wait"    # 相手の入力待ち

KIMERA_SESSIONS = {}
PVP_CHALLENGES = {} # {target_id: challenger_id}
PVP_BATTLES = {}    # {battle_id: battle_data}

def get_session(user_id):
    return KIMERA_SESSIONS.get(user_id)

def start_session(user_id):
    core.get_user_data(user_id) # 初期化
    KIMERA_SESSIONS[user_id] = {"state": STATE_MENU, "context": {}}

def end_session(user_id):
    if user_id in KIMERA_SESSIONS:
        # PvPロビー待ちなら削除
        if KIMERA_SESSIONS[user_id]["state"] == STATE_BATTLE_PVP_LOBBY:
            to_del = [k for k, v in PVP_CHALLENGES.items() if v == user_id]
            for k in to_del: del PVP_CHALLENGES[k]
        
        del KIMERA_SESSIONS[user_id]

# --- メニュー ---
def handle_menu(user_id, content):
    session = KIMERA_SESSIONS[user_id]
    
    if "バトル" in content:
        session["state"] = STATE_BATTLE_SELECT
        return (
            "どのゾーンに行く？\n"
            "1. **確保ゾーン** (野生のキメラを捕まえる)\n"
            "2. **レベル上げゾーン** (黄金裔CPUと戦う)\n"
            "3. **対戦ゾーン** (他のプレイヤーと対戦)"
        ), []
    
    if "編成" in content:
        ud = core.get_user_data(user_id)
        party_txt = "\n".join([f"{i+1}. {c['nickname']} (Lv.{c['level']})" for i, c in enumerate(ud['party'])])
        return f"【現在のパーティ】\n{party_txt}\n\n※入れ替え機能は作成中よ♪", []

    if "詳細" in content:
        ud = core.get_user_data(user_id)
        if not ud['party']: return "キメラを持ってないみたいね…", []
        chimera = ud['party'][0]
        stats_txt = core.get_chimera_display_stats(chimera)
        return f"【先頭のキメラ詳細】\n{stats_txt}", []

    if "ショップ" in content:
        session["state"] = STATE_SHOP
        items = data.ITEMS
        ud = core.get_user_data(user_id)
        shop_list = []
        for key, val in items.items():
            shop_list.append(f"・**{val['name']}**: {val['price']}G ({val['desc']})")
        
        return (
            f"【ショップ】 (所持金: {ud['money']}G)\n" + "\n".join(shop_list) +
            "\n\n『モンスターボールを買う』のように言ってね。戻るなら『戻る』よ。"
        ), []

    return "『バトル』『編成』『キメラ詳細』『ショップ』の中から選んでね♪", []

# --- ショップ処理 ---
def handle_shop(user_id, content):
    session = KIMERA_SESSIONS[user_id]
    
    if "戻る" in content:
        session["state"] = STATE_MENU
        return "メニューに戻るわね。", []

    target_key = None
    for key, val in data.ITEMS.items():
        if val["name"] in content:
            target_key = key
            break
    
    if target_key:
        item = data.ITEMS[target_key]
        price = item["price"]
        ud = core.get_user_data(user_id)
        
        if ud["money"] >= price:
            ud["money"] -= price
            ud["items"][target_key] = ud["items"].get(target_key, 0) + 1
            core.save_user_data(user_id, ud)
            return f"**{item['name']}** を購入したわ♪ (残金: {ud['money']}G)\n他には？", []
        else:
            return f"お金が足りないみたい… (所持金: {ud['money']}G, 必要: {price}G)", []
            
    return "商品名がわからないわ。正しく入力してちょうだい。", []

# --- バトル選択 ---
def handle_battle_select(user_id, content):
    session = KIMERA_SESSIONS[user_id]
    
    # 1. 野生
    if "確保" in content or "1" in content:
        wild_base = random.choice(list(data.BASE_CHIMERAS.keys()))
        wild_chimera = core.create_chimera_instance(wild_base, level=3)
        session["state"] = STATE_BATTLE_WILD
        session["context"] = {"enemy": wild_chimera, "sub_state": BATTLE_SUB_MAIN}
        return (
            f"草むらから 野生の **{wild_chimera['nickname']}** (Lv.{wild_chimera['level']}) が飛び出してきた！\n"
            "どうする？ 『戦う』 『道具』 『入れ替え』 『逃げる』"
        ), []

    # 2. CPU
    if "レベル上げ" in content or "2" in content:
        cpu_base = random.choice(list(data.BASE_CHIMERAS.keys()))
        cpu_chimera = core.create_chimera_instance(cpu_base, level=5)
        session["state"] = STATE_BATTLE_TRAINER
        session["context"] = {"enemy": cpu_chimera, "sub_state": BATTLE_SUB_MAIN}
        return (
            f"黄金裔の幻影が現れた！ **{cpu_chimera['nickname']}** (Lv.{cpu_chimera['level']}) を繰り出してきたわ！\n"
            "どうする？ 『戦う』 『道具』 『入れ替え』 『逃げる』"
        ), []

    # 3. PvP
    if "対戦" in content or "3" in content:
        # 既に自分が誰かに挑まれているか確認
        challenger_id = PVP_CHALLENGES.get(user_id)
        if challenger_id:
            # 挑戦を受ける
            return _initiate_pvp_battle(challenger_id, user_id)
        
        session["state"] = STATE_BATTLE_PVP_LOBBY
        return (
            "【対戦ゾーン】\n"
            "誰と戦う？ 対戦したい相手をメンションしてね。\n"
            "(例: `@相手の名前`)\n\n"
            "※相手も『キメラと遊びたい』でゲームを始めている必要があるわ。"
        ), []
        
    return "『確保』『レベル上げ』『対戦』から選んでちょうだい。", []

# --- PvP ロビー処理 ---
def handle_pvp_lobby(user_id, content):
    # メンションからID抽出
    m = re.search(r"<@!?(\d+)>", content)
    if m:
        target_id = int(m.group(1))
        if target_id == user_id:
            return "自分とは戦えないわよ。", []
        
        # 挑戦状を登録
        PVP_CHALLENGES[target_id] = user_id
        
        return (
            f"<@{target_id}> に挑戦状を送ったわ！\n"
            "相手が『対戦』を選んで承認するのを待っててね。\n"
            "(待ちきれないなら『キャンセル』と言って)"
        ), [(target_id, f"**{user_id}** から対戦を申し込まれたわ！\n受けるなら『キメラと遊びたい』→『バトル』→『対戦』を選んで！")]

    if "キャンセル" in content:
        KIMERA_SESSIONS[user_id]["state"] = STATE_BATTLE_SELECT
        # 登録削除
        to_del = [k for k, v in PVP_CHALLENGES.items() if v == user_id]
        for k in to_del: del PVP_CHALLENGES[k]
        return "対戦待ちをキャンセルしたわ。", []

    return "対戦したい相手をメンションしてね。", []

# --- PvP バトル初期化 ---
def _initiate_pvp_battle(p1_id, p2_id):
    # 挑戦状削除
    if p2_id in PVP_CHALLENGES: del PVP_CHALLENGES[p2_id]

    battle_id = f"pvp_{p1_id}_{p2_id}"
    
    # バトルデータ作成
    PVP_BATTLES[battle_id] = {
        "p1": p1_id, "p2": p2_id,
        "actions": {}, # {uid: {"type": "move", "value": "scratch"}}
        "turn": 1
    }

    # セッション更新
    for uid in [p1_id, p2_id]:
        if uid not in KIMERA_SESSIONS: start_session(uid) # 念のため
        sess = KIMERA_SESSIONS[uid]
        sess["state"] = STATE_BATTLE_PVP
        sess["context"] = {
            "battle_id": battle_id,
            "sub_state": BATTLE_SUB_MAIN
        }

    # 互いのパーティ先頭を取得
    ud1 = core.get_user_data(p1_id)
    ud2 = core.get_user_data(p2_id)
    c1 = ud1["party"][0]
    c2 = ud2["party"][0]

    msg1 = f"対戦開始！ 相手は **{c2['nickname']}** (Lv.{c2['level']}) よ！\nどうする？ 『戦う』 『道具』 『入れ替え』"
    msg2 = f"対戦開始！ 相手は **{c1['nickname']}** (Lv.{c1['level']}) よ！\nどうする？ 『戦う』 『道具』 『入れ替え』"

    # p2 (自分) へのメッセージ, p1 (相手) へのメッセージ
    return msg2, [(p1_id, msg1)]

# --- PvP アクション処理 ---
def handle_pvp_action(user_id, content):
    session = KIMERA_SESSIONS[user_id]
    ctx = session["context"]
    battle_id = ctx["battle_id"]
    battle = PVP_BATTLES.get(battle_id)
    
    if not battle:
        session["state"] = STATE_MENU
        return "対戦は終了しているみたい。", []

    ud = core.get_user_data(user_id)
    player_chimera = ud['party'][0]
    
    sub = ctx.get("sub_state", BATTLE_SUB_MAIN)

    if sub == BATTLE_SUB_WAIT:
        return "相手の入力を待っているわ…少し待ってね。", []

    # コマンド選択
    if sub == BATTLE_SUB_MAIN:
        if "降参" in content or "逃" in content:
            # 降参処理
            return _resolve_pvp_end(battle, loser_id=user_id)

        if "戦" in content:
            moves_txt = " / ".join([f"{data.MOVES[m]['name']}" for m in player_chimera["moves"]])
            return f"どの技を使う？\n[{moves_txt}]", []

        # 技選択
        selected_move = None
        for mid in player_chimera["moves"]:
            if data.MOVES[mid]["name"] in content:
                selected_move = mid
                break
        
        if selected_move:
            # アクション登録
            battle["actions"][user_id] = {"type": "move", "value": selected_move}
            ctx["sub_state"] = BATTLE_SUB_WAIT
            return _check_pvp_turn_ready(battle)

        return "コマンドを選んで。『戦う』『降参』などよ。（道具・入れ替えはPvPでは制限中）", []

    return "...", []

def _check_pvp_turn_ready(battle):
    p1 = battle["p1"]
    p2 = battle["p2"]
    
    # 両方の入力が揃ったか？
    if p1 in battle["actions"] and p2 in battle["actions"]:
        return _resolve_pvp_turn(battle)
    else:
        return "入力を受け付けたわ。相手を待っているわね。", []

def _resolve_pvp_turn(battle):
    p1, p2 = battle["p1"], battle["p2"]
    act1, act2 = battle["actions"][p1], battle["actions"][p2]
    
    ud1 = core.get_user_data(p1)
    ud2 = core.get_user_data(p2)
    c1 = ud1["party"][0]
    c2 = ud2["party"][0]
    
    # 行動順決定 (素早さ)
    # 同速ならランダム
    speed1 = c1["stats"]["spe"]
    speed2 = c2["stats"]["spe"]
    
    if speed1 > speed2:
        order = [(p1, c1, act1, p2, c2), (p2, c2, act2, p1, c1)]
    elif speed2 > speed1:
        order = [(p2, c2, act2, p1, c1), (p1, c1, act1, p2, c2)]
    else:
        if random.random() < 0.5:
            order = [(p1, c1, act1, p2, c2), (p2, c2, act2, p1, c1)]
        else:
            order = [(p2, c2, act2, p1, c1), (p1, c1, act1, p2, c2)]
            
    # ターン処理実行
    logs = []
    
    for actor_id, actor_c, act, target_id, target_c in order:
        if actor_c["current_hp"] <= 0: continue # 既に倒れていたら動けない
        
        if act["type"] == "move":
            mid = act["value"]
            mdata = data.MOVES[mid]
            
            # ダメージ計算
            if mdata["category"] == "Physical":
                dmg = int(mdata["power"] * (actor_c["stats"]["atk"] / target_c["stats"]["def"]) / 2)
            else:
                dmg = int(mdata["power"] * (actor_c["stats"]["spa"] / target_c["stats"]["spd"]) / 2)
            
            # 乱数
            dmg = int(dmg * random.uniform(0.85, 1.0))
            if dmg < 1: dmg = 1
            
            target_c["current_hp"] -= dmg
            logs.append(f"**{actor_c['nickname']}** の {mdata['name']}！ {target_c['nickname']} に {dmg} のダメージ！")
            
            if target_c["current_hp"] <= 0:
                target_c["current_hp"] = 0
                logs.append(f"**{target_c['nickname']}** は倒れた！")
                
    # ターン終了後の状態リセット
    battle["actions"] = {}
    
    # ログ結合
    full_log = "\n".join(logs)
    
    # 決着判定
    loser = None
    if c1["current_hp"] <= 0 and c2["current_hp"] <= 0:
        # 引き分け（両者敗北扱いか、速度負けか…今回は引き分け）
        core.save_user_data(p1, ud1)
        core.save_user_data(p2, ud2)
        _end_pvp(battle)
        msg = f"{full_log}\n\n相打ちね！ 引き分けよ！"
        return msg, [(p1, msg)] # p1へのメッセージはextra_msgsではなくreturn値で処理したいが、呼び出し元がp1かp2かわからない
        # 呼び出し元が自分(この関数をトリガーした人)に対して返り値、相手にはextra

    if c1["current_hp"] <= 0: loser = p1
    elif c2["current_hp"] <= 0: loser = p2
    
    if loser:
        core.save_user_data(p1, ud1)
        core.save_user_data(p2, ud2)
        _end_pvp(battle)
        
        winner = p2 if loser == p1 else p1
        msg = f"{full_log}\n\n勝負あり！ <@{winner}> の勝利よ！"
        
        # 状態リセット
        KIMERA_SESSIONS[p1]["state"] = STATE_MENU
        KIMERA_SESSIONS[p2]["state"] = STATE_MENU
        KIMERA_SESSIONS[p1]["context"]["sub_state"] = BATTLE_SUB_MAIN
        KIMERA_SESSIONS[p2]["context"]["sub_state"] = BATTLE_SUB_MAIN
        
        # ここで呼び出し元を判別できないため、両方にextraで送る形にする（空return）
        return "", [(p1, msg), (p2, msg)]

    # 続行
    core.save_user_data(p1, ud1)
    core.save_user_data(p2, ud2)
    
    # 両者の状態をMainに戻す
    KIMERA_SESSIONS[p1]["context"]["sub_state"] = BATTLE_SUB_MAIN
    KIMERA_SESSIONS[p2]["context"]["sub_state"] = BATTLE_SUB_MAIN
    
    msg_next = f"{full_log}\n\n次のターンよ！ どうする？"
    return "", [(p1, msg_next), (p2, msg_next)]

def _resolve_pvp_end(battle, loser_id):
    p1, p2 = battle["p1"], battle["p2"]
    winner_id = p2 if loser_id == p1 else p1
    
    _end_pvp(battle)
    
    msg = f"<@{loser_id}> が降参したわ。\n<@{winner_id}> の勝利よ！"
    
    KIMERA_SESSIONS[p1]["state"] = STATE_MENU
    KIMERA_SESSIONS[p2]["state"] = STATE_MENU
    
    return "", [(p1, msg), (p2, msg)]

def _end_pvp(battle):
    # バトル削除
    target_k = None
    for k, v in PVP_BATTLES.items():
        if v == battle: target_k = k
    if target_k: del PVP_BATTLES[target_k]


# --- 通常バトルアクション (野生/CPU) ---
# ※既存の handle_battle_action を修正して、return (msg, []) の形にする
def handle_battle_action(user_id, content):
    session = KIMERA_SESSIONS[user_id]
    ctx = session["context"]
    
    # PvP判定
    if session["state"] == STATE_BATTLE_PVP:
        return handle_pvp_action(user_id, content)

    enemy = ctx["enemy"]
    ud = core.get_user_data(user_id)
    player_chimera = ud['party'][0]
    sub = ctx.get("sub_state", BATTLE_SUB_MAIN)

    # === メインコマンド ===
    if sub == BATTLE_SUB_MAIN:
        if "逃" in content:
            end_session(user_id)
            return "戦闘から逃げ出したわ。安全第一ね♪", []

        if "道具" in content:
            ctx["sub_state"] = BATTLE_SUB_ITEM
            items_list = []
            for k, count in ud["items"].items():
                if count > 0:
                    iname = data.ITEMS[k]["name"]
                    items_list.append(f"・{iname} (x{count})")
            if not items_list:
                ctx["sub_state"] = BATTLE_SUB_MAIN
                return "道具を何も持っていないわ！\nどうする？ 『戦う』 『入れ替え』 『逃げる』", []
            return f"どの道具を使う？\n" + "\n".join(items_list) + "\n(キャンセルなら『戻る』)", []

        if "入れ替え" in content:
            ctx["sub_state"] = BATTLE_SUB_SWITCH
            party_list = _generate_party_list(ud)
            return "誰と入れ替える？番号で教えてね。\n" + party_list + "\n(キャンセルなら『戻る』)", []

        if "戦" in content:
            moves_txt = " / ".join([f"{data.MOVES[m]['name']}" for m in player_chimera["moves"]])
            return f"どの技を使う？\n[{moves_txt}]", []

        selected_move = None
        for mid in player_chimera["moves"]:
            if data.MOVES[mid]["name"] in content:
                selected_move = mid
                break
        
        if selected_move:
            return execute_turn(user_id, session, player_chimera, enemy, selected_move, ud), []
            
        return "コマンドがわからないわ。『戦う』『道具』『入れ替え』『逃げる』を選んで？", []

    # === 道具選択 ===
    elif sub == BATTLE_SUB_ITEM:
        if "戻る" in content:
            ctx["sub_state"] = BATTLE_SUB_MAIN
            return "どうする？ 『戦う』 『道具』 『入れ替え』 『逃げる』", []
        
        target_item = None
        for k in ud["items"]:
            if data.ITEMS[k]["name"] in content:
                target_item = k
                break
        
        if target_item:
            return use_item_in_battle(user_id, session, target_item, ud, player_chimera, enemy), []

        return "その道具は持っていないみたい。名前を正しく入力してね。", []

    # === 入れ替え選択 ===
    elif sub == BATTLE_SUB_SWITCH:
        if "戻る" in content:
            ctx["sub_state"] = BATTLE_SUB_MAIN
            return "どうする？ 『戦う』 『道具』 『入れ替え』 『逃げる』", []
        
        res = _try_switch_member(user_id, content, ud, player_chimera, allow_cancel=True)
        if res["success"]:
            target = res["target"]
            ctx["sub_state"] = BATTLE_SUB_MAIN
            msg = f"戻れ、{player_chimera['nickname']}！ 行け、{target['nickname']}！\n"
            msg += enemy_attack_phase(user_id, session, target, enemy, ud)
            return msg, []
        else:
            return res["msg"], []

    # === 強制入れ替え ===
    elif sub == BATTLE_SUB_FORCE_SWITCH:
        res = _try_switch_member(user_id, content, ud, player_chimera, allow_cancel=False)
        if res["success"]:
            target = res["target"]
            ctx["sub_state"] = BATTLE_SUB_MAIN
            return f"行け、{target['nickname']}！\n頼んだわよ！\n\nどうする？ 『戦う』 『道具』 『入れ替え』 『逃げる』", []
        else:
            return res["msg"], []

    return "エラーが発生したみたい。一度『終了』してリセットしましょうか。", []

# --- 内部ヘルパー (既存のまま) ---
def _generate_party_list(ud):
    party_list = []
    for i, c in enumerate(ud["party"]):
        status = "瀕死" if c["current_hp"] <= 0 else f"{c['current_hp']}/{c['stats']['max_hp']}"
        party_list.append(f"{i+1}. {c['nickname']} (Lv.{c['level']}) [{status}]")
    return "\n".join(party_list)

def _try_switch_member(user_id, content, ud, current_chimera, allow_cancel=True):
    try:
        # 全角数字対応
        idx = int(content.translate(str.maketrans({chr(0xFF01 + i): chr(0x21 + i) for i in range(94)}))) - 1
        if 0 <= idx < len(ud["party"]):
            target = ud["party"][idx]
            if target["current_hp"] <= 0:
                return {"success": False, "msg": f"{target['nickname']} は瀕死で戦えないわ。"}
            if target == current_chimera and allow_cancel:
                return {"success": False, "msg": "その子はもう出ているわよ。"}
            
            ud["party"][0], ud["party"][idx] = ud["party"][idx], ud["party"][0]
            core.save_user_data(user_id, ud)
            return {"success": True, "target": target}
        else:
            return {"success": False, "msg": "その番号のキメラはいないわ。"}
    except ValueError:
        return {"success": False, "msg": "番号で教えてちょうだい。"}

# --- ターン処理 (既存のまま) ---
def execute_turn(user_id, session, player, enemy, move_id, ud):
    move_data = data.MOVES[move_id]
    
    if random.randint(1, 100) > move_data["accuracy"]:
        msg = f"{player['nickname']} の {move_data['name']}！\nしかし攻撃は外れた！"
    else:
        if move_data["category"] == "Physical":
            raw = move_data["power"] * (player["stats"]["atk"] / enemy["stats"]["def"])
        else:
            raw = move_data["power"] * (player["stats"]["spa"] / enemy["stats"]["spd"])
        
        if player["held_item"] == "power_band" and move_data["category"] == "Physical":
            raw *= 1.1

        damage = int(raw / 2 * random.uniform(0.85, 1.0))
        if damage < 1: damage = 1

        enemy["current_hp"] -= damage
        msg = f"{player['nickname']} の {move_data['name']}！\n相手に {damage} のダメージ！"

    if enemy["current_hp"] <= 0:
        enemy["current_hp"] = 0
        msg += f"\n相手の {enemy['nickname']} は倒れた！ 勝利よ♪"
        
        xp_gain = enemy["level"] * 15
        player["xp"] += xp_gain
        msg += f"\n{xp_gain} の経験値を獲得！"
        if player["xp"] >= player["next_xp"]:
            msg += core.level_up_chimera(player)
            
        money_gain = enemy["level"] * 50
        ud["money"] += money_gain
        msg += f"\n賞金 {money_gain}G を手に入れたわ。"

        core.save_user_data(user_id, ud)
        end_session(user_id)
        return msg + "\n\nメニューに戻るわね。"

    msg += "\n" + enemy_attack_phase(user_id, session, player, enemy, ud)
    return msg

def enemy_attack_phase(user_id, session, player, enemy, ud):
    enemy_move_id = random.choice(enemy["moves"])
    e_move = data.MOVES[enemy_move_id]
    
    if e_move["category"] == "Physical":
        raw = e_move["power"] * (enemy["stats"]["atk"] / player["stats"]["def"])
    else:
        raw = e_move["power"] * (enemy["stats"]["spa"] / player["stats"]["spd"])
    
    dmg = int(raw / 2 * random.uniform(0.85, 1.0))
    if dmg < 1: dmg = 1

    player["current_hp"] -= dmg
    msg = f"相手の {enemy['nickname']} の {e_move['name']}！\n{player['nickname']} に {dmg} のダメージ！"
    msg += f" (残りHP: {player['current_hp']}/{player['stats']['max_hp']})"

    if player["current_hp"] <= 0:
        player["current_hp"] = 0
        core.save_user_data(user_id, ud)
        
        msg += f"\n\n{player['nickname']} は倒れてしまった…！"
        
        alive_exists = any(c["current_hp"] > 0 for c in ud["party"])
        
        if alive_exists:
            session["context"]["sub_state"] = BATTLE_SUB_FORCE_SWITCH
            party_list = _generate_party_list(ud)
            msg += "\nまだ戦える仲間がいるわ！ 次は誰を出す？\n" + party_list
            return msg
        else:
            lost_money = int(ud["money"] * 0.1)
            ud["money"] -= lost_money
            if ud["money"] < 0: ud["money"] = 0
            
            for c in ud["party"]:
                c["current_hp"] = c["stats"]["max_hp"]
            
            core.save_user_data(user_id, ud)
            end_session(user_id)
            msg += f"\n\n手持ちのキメラが全滅してしまったわ…\n目の前が真っ暗になった！\n(所持金を {lost_money}G 失い、キメラセンターで回復しました)"
            return msg

    core.save_user_data(user_id, ud)
    return msg

# --- アイテム使用処理 (既存のまま) ---
def use_item_in_battle(user_id, session, item_key, ud, player, enemy):
    item_data = data.ITEMS[item_key]
    ctx = session["context"]

    if item_data["effect_type"] == "capture":
        if session["state"] != STATE_BATTLE_WILD:
            return "人のキメラにボールを投げるのは泥棒よ！"
        
        ud["items"][item_key] -= 1
        if ud["items"][item_key] <= 0: del ud["items"][item_key]
        
        hp_rate = enemy["current_hp"] / enemy["stats"]["max_hp"]
        catch_chance = ((1 - hp_rate) * 80 + 20) * item_data["value"]
        
        msg = f"{item_data['name']} を投げた！"
        if random.randint(0, 100) < catch_chance:
            if len(ud["party"]) < 3:
                ud["party"].append(enemy)
                loc = "手持ち"
            else:
                ud["box"].append(enemy)
                loc = "ボックス"
            
            enemy["current_hp"] = enemy["stats"]["max_hp"]
            core.save_user_data(user_id, ud)
            end_session(user_id)
            return f"{msg}\nやった！ **{enemy['nickname']}** を捕まえたわ！\n{loc}に送ったわよ♪"
        else:
            ctx["sub_state"] = BATTLE_SUB_MAIN
            return f"{msg}\nああっ！ ボールから抜け出されたわ！\n" + enemy_attack_phase(user_id, session, player, enemy, ud)

    elif item_data["effect_type"] == "heal":
        if player["current_hp"] >= player["stats"]["max_hp"]:
            return "その子はもう元気いっぱいよ。"
        
        ud["items"][item_key] -= 1
        if ud["items"][item_key] <= 0: del ud["items"][item_key]

        heal_val = item_data["value"]
        player["current_hp"] += heal_val
        if player["current_hp"] > player["stats"]["max_hp"]:
            player["current_hp"] = player["stats"]["max_hp"]
            
        core.save_user_data(user_id, ud)
        ctx["sub_state"] = BATTLE_SUB_MAIN
        
        return f"{item_data['name']} を使った。\n{player['nickname']} のHPが回復したわ！\n" + \
               enemy_attack_phase(user_id, session, player, enemy, ud)
    else:
        return "それは今使えないみたい。"

# --- 統合ハンドラ ---
def process_kimera_command(user_id, content):
    session = get_session(user_id)
    
    if not session:
        if "キメラと遊びたい" in content:
            start_session(user_id)
            return "あら、キメラたちと遊びたいの？いいわよ♪\n何をしたいかしら？\n\n『バトル』 『編成』 『キメラ詳細』 『ショップ』", []
        return None

    # ★変更点: 終了ワードを追加
    if content == "終了" or content == "やめる" or content == "もう遊び疲れたよ":
        end_session(user_id)
        return "キメラとの遊びはおしまいね。また遊びましょ♪", []

    state = session["state"]
    
    if state == STATE_MENU:
        return handle_menu(user_id, content)
    elif state == STATE_SHOP:
        return handle_shop(user_id, content)
    elif state == STATE_BATTLE_SELECT:
        return handle_battle_select(user_id, content)
    elif state == STATE_BATTLE_PVP_LOBBY: # 追加: PvP待ち
        return handle_pvp_lobby(user_id, content)
    elif state in [STATE_BATTLE_WILD, STATE_BATTLE_TRAINER, STATE_BATTLE_PVP]:
        return handle_battle_action(user_id, content)
        
    return None