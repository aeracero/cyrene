# kimera_game.py
import random
import re
import kimera_core as core
import kimera_data as data
import database as db

# --- 状態定義 ---
STATE_MENU = "menu"
STATE_SHOP = "shop"
STATE_BATTLE_SELECT = "battle_select"
STATE_BATTLE_WILD = "battle_wild"
STATE_BATTLE_TRAINER = "battle_trainer"
STATE_BATTLE_CHALLENGE = "battle_challenge"
STATE_BATTLE_PVP_LOBBY = "battle_pvp_lobby"
STATE_BATTLE_PVP = "battle_pvp"

# 戦闘中のサブステート
BATTLE_SUB_MAIN = "main"
BATTLE_SUB_ITEM = "item"
BATTLE_SUB_SWITCH = "switch"
BATTLE_SUB_FORCE_SWITCH = "force_switch"
BATTLE_SUB_WAIT = "wait"

KIMERA_SESSIONS = {}
PVP_CHALLENGES = {}
PVP_BATTLES = {}

def get_session(user_id):
    return KIMERA_SESSIONS.get(user_id)

def start_session(user_id):
    core.get_user_data(user_id)
    KIMERA_SESSIONS[user_id] = {"state": STATE_MENU, "context": {}}

def end_session(user_id):
    if user_id in KIMERA_SESSIONS:
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
            "1. **確保ゾーン** (野生のキメラ捕獲)\n"
            "2. **レベル上げゾーン** (CPU戦)\n"
            "3. **チャレンジモード** (黄金裔13人抜き)\n"
            "4. **対戦ゾーン** (プレイヤー対戦)"
        ), []
    
    if "編成" in content:
        ud = core.get_user_data(user_id)
        p_txt = "\n".join([f"{i+1}. {c['nickname']} (Lv.{c['level']})" for i, c in enumerate(ud['party'])])
        return f"【現在のパーティ】\n{p_txt}\n\n(T-Lv.{ud['trainer_level']})", []

    if "詳細" in content:
        ud = core.get_user_data(user_id)
        if not ud['party']: return "キメラを持ってないわ。", []
        chimera = ud['party'][0]
        return f"【先頭】\n{core.get_chimera_display_stats(chimera)}", []

    if "ショップ" in content:
        session["state"] = STATE_SHOP
        ud = core.get_user_data(user_id)
        tlv = ud["trainer_level"]
        lines = []
        for k, v in data.ITEMS.items():
            if v["price"] > 0 and v.get("unlock_rank", 1) <= tlv:
                lines.append(f"・**{v['name']}**: {v['price']}G")
        return f"【ショップ】 (所持金: {ud['money']}G / T-Lv.{tlv})\n" + "\n".join(lines) + "\n\n『〇〇を買う』 / 『戻る』", []

    if "アイテム" in content:
        ud = core.get_user_data(user_id)
        items_txt = ", ".join([f"{data.ITEMS[k]['name']}x{v}" for k, v in ud['items'].items()])
        return f"所持アイテム: {items_txt}\n(使う場合は『けいけんアメSを使う』と言ってね)", []
        
    m = re.match(r"(.+)を使う", content)
    if m:
        item_name = m.group(1)
        item_key = None
        for k, v in data.ITEMS.items():
            if v["name"] == item_name: item_key = k
        if item_key:
            ud = core.get_user_data(user_id)
            if not ud["party"]: return "使う相手がいないわ。", []
            res = core.use_item_effect(user_id, item_key, ud["party"][0])
            return res, []

    return "『バトル』『編成』『詳細』『ショップ』『アイテム』から選んでね。", []

# --- ショップ ---
def handle_shop(user_id, content):
    session = KIMERA_SESSIONS[user_id]
    if "戻る" in content:
        session["state"] = STATE_MENU
        return "メニューに戻るわ。", []
    
    target_key = None
    for k, v in data.ITEMS.items():
        if v["name"] in content: target_key = k
    
    if target_key:
        ud = core.get_user_data(user_id)
        item = data.ITEMS[target_key]
        if item.get("unlock_rank", 1) > ud["trainer_level"]:
            return "今のトレーナーレベルではまだ買えない商品よ。", []
        if ud["money"] >= item["price"]:
            ud["money"] -= item["price"]
            ud["items"][target_key] = ud["items"].get(target_key, 0) + 1
            core.save_user_data(user_id, ud)
            return f"**{item['name']}** を購入したわ。(残: {ud['money']}G)", []
        else:
            return "お金が足りないわ。", []
    return "商品名を入力してね。", []

# --- バトル選択 ---
def handle_battle_select(user_id, content):
    session = KIMERA_SESSIONS[user_id]
    ud = core.get_user_data(user_id)
    tlv = ud["trainer_level"]

    if "確保" in content or "1" in content:
        wild_base = random.choice(list(data.BASE_CHIMERAS.keys()))
        w_lv = max(1, tlv + random.randint(0, 2))
        wild = core.create_chimera_instance(wild_base, level=w_lv)
        session["state"] = STATE_BATTLE_WILD
        session["context"] = {
            "enemy_party": [wild],
            "enemy_name": "野生のキメラ",
            "sub_state": BATTLE_SUB_MAIN
        }
        return f"草むらから 野生の **{wild['nickname']}** (Lv.{wild['level']}) が飛び出してきた！\nどうする？ 『戦う』『道具』『入れ替え』『逃げる』", []

    if "レベル上げ" in content or "2" in content:
        cpu_base = random.choice(list(data.BASE_CHIMERAS.keys()))
        c_lv = max(5, tlv + random.randint(0, 5))
        cpu_c = core.create_chimera_instance(cpu_base, level=c_lv)
        session["state"] = STATE_BATTLE_TRAINER
        session["context"] = {
            "enemy_party": [cpu_c],
            "enemy_name": "黄金裔の幻影",
            "sub_state": BATTLE_SUB_MAIN
        }
        return f"黄金裔の幻影が現れた！ **{cpu_c['nickname']}** (Lv.{cpu_c['level']}) を繰り出してきた！", []

    if "チャレンジ" in content or "3" in content:
        stage = ud.get("challenge_stage", 1)
        if stage > 13: return "チャレンジモードはすべてクリア済みよ！素晴らしいわ♪", []
        
        t_data = data.CHALLENGE_TRAINERS.get(stage)
        if not t_data: return "準備中よ。", []
        
        enemy_party = []
        for p in t_data["party"]:
            enemy_party.append(core.create_chimera_instance(p["base_id"], p["level"]))
        
        session["state"] = STATE_BATTLE_CHALLENGE
        session["context"] = {
            "enemy_party": enemy_party,
            "enemy_name": t_data["name"],
            "stage": stage,
            "sub_state": BATTLE_SUB_MAIN
        }
        start_msg = t_data.get("dialogue_start", "勝負よ！")
        first = enemy_party[0]
        return (
            f"【チャレンジモード Stage {stage}】\n"
            f"**{t_data['name']}**: 「{start_msg}」\n"
            f"相手は **{first['nickname']}** (Lv.{first['level']}) を繰り出してきた！"
        ), []

    if "対戦" in content or "4" in content:
        challenger = PVP_CHALLENGES.get(user_id)
        if challenger: return _initiate_pvp_battle(challenger, user_id)
        session["state"] = STATE_BATTLE_PVP_LOBBY
        return "対戦相手の「名前」を入力して招待してね。", []

    return "モードを選んでちょうだい。", []

# --- バトルアクション (PvE) ---
def handle_battle_action(user_id, content):
    session = KIMERA_SESSIONS[user_id]
    if session["state"] == STATE_BATTLE_PVP: return handle_pvp_action(user_id, content)

    ctx = session["context"]
    ud = core.get_user_data(user_id)
    
    enemy_party = ctx["enemy_party"]
    enemy = next((c for c in enemy_party if c["current_hp"] > 0), None)
    
    player = ud['party'][0]

    if not enemy:
        return _resolve_pve_win(user_id, session, ud)

    sub = ctx.get("sub_state", BATTLE_SUB_MAIN)

    if sub == BATTLE_SUB_MAIN:
        if "逃" in content:
            if session["state"] == STATE_BATTLE_CHALLENGE: return "チャレンジモードからは逃げられないわ！", []
            end_session(user_id)
            return "逃げ出したわ。", []
        if "道具" in content:
            ctx["sub_state"] = BATTLE_SUB_ITEM
            items = [f"{data.ITEMS[k]['name']}x{v}" for k, v in ud['items'].items()]
            return f"道具: {', '.join(items)}\n(戻るなら『戻る』)", []
        if "入れ替え" in content:
            ctx["sub_state"] = BATTLE_SUB_SWITCH
            return "誰と入れ替える？(番号)\n" + _generate_party_list(ud), []
        if "戦" in content:
            moves = [data.MOVES[m]['name'] for m in player["moves"]]
            return f"技: {', '.join(moves)}", []

        sel_move = None
        for m in player["moves"]:
            if data.MOVES[m]["name"] in content: sel_move = m
        if sel_move:
            return _execute_pve_turn(user_id, session, player, enemy, sel_move, ud)

        return "どうする？", []

    elif sub == BATTLE_SUB_ITEM:
        if "戻る" in content:
            ctx["sub_state"] = BATTLE_SUB_MAIN
            return "どうする？", []
        
        sel_item = None
        for k, v in data.ITEMS.items():
            if v["name"] in content: sel_item = k
        if sel_item:
            return use_item_in_battle(user_id, session, sel_item, ud, player, enemy), []
        return "アイテム名を入力してね。", []

    elif sub == BATTLE_SUB_SWITCH:
        if "戻る" in content:
            ctx["sub_state"] = BATTLE_SUB_MAIN
            return "どうする？", []
        
        res = _try_switch_member(user_id, content, ud, player, allow_cancel=True)
        if res["success"]:
            ctx["sub_state"] = BATTLE_SUB_MAIN
            target = res["target"]
            msg = f"行け、{target['nickname']}！\n"
            msg += _enemy_attack_phase(user_id, session, target, enemy, ud)
            return msg, []
        return res["msg"], []

    elif sub == BATTLE_SUB_FORCE_SWITCH:
        res = _try_switch_member(user_id, content, ud, player, allow_cancel=False)
        if res["success"]:
            ctx["sub_state"] = BATTLE_SUB_MAIN
            return f"頼んだわよ、{res['target']['nickname']}！\nどうする？", []
        return res["msg"], []

    return "エラー。", []

# --- PvE ターン処理 ---
def _execute_pve_turn(user_id, session, player, enemy, move_id, ud):
    mdata = data.MOVES[move_id]
    dmg = int(mdata["power"] * (player["stats"]["atk"] / enemy["stats"]["def"]) * 0.4 * random.uniform(0.85, 1.0))
    if dmg < 1: dmg = 1
    
    enemy["current_hp"] -= dmg
    msg = f"{player['nickname']} の {mdata['name']}！ {dmg} ダメージ！"
    
    # セーブ（敵HP減少）
    core.save_user_data(user_id, ud)
    
    if enemy["current_hp"] <= 0:
        enemy["current_hp"] = 0
        msg += f"\n相手の {enemy['nickname']} は倒れた！"
        
        xp = (enemy["level"] * 20) + random.randint(0, enemy["level"] * 10)
        player["xp"] += xp
        if player["xp"] >= player["next_xp"]:
            msg += "\n" + core.level_up_chimera(player)
        
        # セーブ（経験値獲得）
        core.save_user_data(user_id, ud)
        
        ctx = session["context"]
        next_enemy = next((c for c in ctx["enemy_party"] if c["current_hp"] > 0), None)
        
        if next_enemy:
            msg += f"\n相手は **{next_enemy['nickname']}** (Lv.{next_enemy['level']}) を繰り出した！"
            return msg, []
        else:
            return _resolve_pve_win(user_id, session, ud)

    msg += "\n" + _enemy_attack_phase(user_id, session, player, enemy, ud)
    return msg, []

def _enemy_attack_phase(user_id, session, player, enemy, ud):
    emove = data.MOVES[random.choice(enemy["moves"])]
    dmg = int(emove["power"] * (enemy["stats"]["atk"] / player["stats"]["def"]) * 0.4 * random.uniform(0.85, 1.0))
    if dmg < 1: dmg = 1
    
    player["current_hp"] -= dmg
    msg = f"敵の {enemy['nickname']} の {emove['name']}！ {dmg} ダメージ！ (残HP: {player['current_hp']})"
    
    if player["current_hp"] <= 0:
        player["current_hp"] = 0
        core.save_user_data(user_id, ud)
        msg += f"\n{player['nickname']} は倒れた！"
        
        if any(c["current_hp"] > 0 for c in ud["party"]):
            session["context"]["sub_state"] = BATTLE_SUB_FORCE_SWITCH
            msg += "\n次は誰を出す？\n" + _generate_party_list(ud)
        else:
            lost = int(ud["money"] * 0.1)
            ud["money"] -= lost
            for c in ud["party"]: c["current_hp"] = c["stats"]["max_hp"]
            core.save_user_data(user_id, ud)
            end_session(user_id)
            msg += f"\n手持ちが全滅したわ… (所持金 -{lost}G)"
    else:
        core.save_user_data(user_id, ud)
        
    return msg

def _resolve_pve_win(user_id, session, ud):
    msg = "勝利よ！\n"
    base_money = 100
    trainer_xp = 50
    
    if session["state"] == STATE_BATTLE_CHALLENGE:
        st = session["context"]["stage"]
        t_data = data.CHALLENGE_TRAINERS[st]
        msg += f"\n**{t_data['name']}**: 「{t_data.get('dialogue_win', '見事だ…')}」\n"
        ud["challenge_stage"] = st + 1
        base_money = st * 1000
        trainer_xp = st * 200
        
        if st == 13:
            if "story_page_2" not in ud["items"]:
                ud["items"]["story_page_2"] = 1
                msg += "\n【重要】『失われし紡がれた物語のページその2』を手に入れたわ！\n"
            if db.unlock_achievement(user_id, "kimera_champion"):
                msg += "\n🏆 実績解除: **【キメラチャンピオン】**\n二つ名獲得: **【ポ◯モンマスターの】**\n"

    ud["money"] += base_money
    lv_up, now_lv = core.add_trainer_xp(user_id, trainer_xp)
    
    msg += f"賞金 {base_money}G と トレーナーXP {trainer_xp} を獲得！"
    if lv_up: msg += f"\nトレーナーレベルが {now_lv} に上がったわ！"
    
    end_session(user_id)
    return msg + "\nメニューに戻るわね。", []

# --- 共通ヘルパー ---
def _generate_party_list(ud):
    return "\n".join([f"{i+1}. {c['nickname']} ({c['current_hp']}/{c['stats']['max_hp']})" for i, c in enumerate(ud['party'])])

def _try_switch_member(user_id, content, ud, current, allow_cancel):
    try:
        idx = int(content.translate(str.maketrans({chr(0xFF01 + i): chr(0x21 + i) for i in range(94)}))) - 1
        if 0 <= idx < len(ud["party"]):
            target = ud["party"][idx]
            if target["current_hp"] <= 0: return {"success": False, "msg": "その子は瀕死よ。"}
            if target == current and allow_cancel: return {"success": False, "msg": "もう出ているわ。"}
            ud["party"][0], ud["party"][idx] = ud["party"][idx], ud["party"][0]
            core.save_user_data(user_id, ud)
            return {"success": True, "target": target}
    except: pass
    return {"success": False, "msg": "番号で指定してね。"}

# --- アイテム使用 (戦闘中) ---
def use_item_in_battle(user_id, session, item_key, ud, player, enemy):
    item = data.ITEMS[item_key]
    
    if item["effect_type"] == "capture":
        if session["state"] != STATE_BATTLE_WILD: return "人のキメラは捕まえられないわ！"
        core.remove_item(user_id, item_key, 1)
        
        rate = ((1 - (enemy["current_hp"]/enemy["stats"]["max_hp"])) * 0.8 + 0.4) * item["value"]
        if random.random() < rate:
            enemy["current_hp"] = enemy["stats"]["max_hp"]
            if len(ud["party"]) < 3: ud["party"].append(enemy)
            else: ud["box"].append(enemy)
            core.save_user_data(user_id, ud)
            end_session(user_id)
            return f"やった！ {enemy['nickname']} を捕まえたわ！"
        else:
            return "ボールから抜け出された！\n" + _enemy_attack_phase(user_id, session, player, enemy, ud)

    elif item["effect_type"] == "heal":
        core.remove_item(user_id, item_key, 1)
        player["current_hp"] = min(player["stats"]["max_hp"], player["current_hp"] + item["value"])
        core.save_user_data(user_id, ud)
        return f"回復したわ！\n" + _enemy_attack_phase(user_id, session, player, enemy, ud)

    return "今は使えないわ。"

# --- PvP ロビー ---
def handle_pvp_lobby(user_id, content):
    m = re.search(r"<@!?(\d+)>", content)
    if m:
        target_id = int(m.group(1))
        if target_id == user_id: return "自分とは戦えないわよ。", []
        PVP_CHALLENGES[target_id] = user_id
        return f"<@{target_id}> に挑戦状を送ったわ！", [(target_id, f"**{user_id}** から挑戦状！")]
    if "キャンセル" in content:
        end_session(user_id)
        return "キャンセルしたわ。", []
    return "相手を指名してね。", []

# ★★★ 修正: 引数名 p1, p2 に統一 ★★★
def _initiate_pvp_battle(p1, p2):
    if p2 in PVP_CHALLENGES: del PVP_CHALLENGES[p2]
    battle_id = f"pvp_{p1}_{p2}"
    PVP_BATTLES[battle_id] = {"p1": p1, "p2": p2, "actions": {}, "turn": 1}
    for uid in [p1, p2]:
        if uid not in KIMERA_SESSIONS: start_session(uid)
        sess = KIMERA_SESSIONS[uid]
        sess["state"] = STATE_BATTLE_PVP
        sess["context"] = {"battle_id": battle_id, "sub_state": BATTLE_SUB_MAIN}
    ud1 = core.get_user_data(p1); ud2 = core.get_user_data(p2)
    c1 = ud1["party"][0]; c2 = ud2["party"][0]
    msg1 = f"対戦開始！ 相手は **{c2['nickname']}** (Lv.{c2['level']}) よ！\nどうする？ 『戦う』 『降参』"
    msg2 = f"対戦開始！ 相手は **{c1['nickname']}** (Lv.{c1['level']}) よ！\nどうする？ 『戦う』 『降参』"
    return msg2, [(p1, msg1)]

# --- PvP アクション ---
def handle_pvp_action(user_id, content):
    session = KIMERA_SESSIONS[user_id]
    ctx = session["context"]
    battle = PVP_BATTLES.get(ctx["battle_id"])
    if not battle:
        session["state"] = STATE_MENU
        return "終了しているわ。", []
    
    ud = core.get_user_data(user_id)
    player_chimera = ud['party'][0]
    sub = ctx.get("sub_state", BATTLE_SUB_MAIN)

    if sub == BATTLE_SUB_WAIT:
        return "相手の入力を待っているわ…少し待ってね。", []

    if sub == BATTLE_SUB_MAIN:
        if "降参" in content or "逃" in content:
            return _resolve_pvp_end(battle, loser_id=user_id)

        if "戦" in content:
            moves_txt = " / ".join([f"{data.MOVES[m]['name']}" for m in player_chimera["moves"]])
            return f"どの技を使う？\n[{moves_txt}]", []

        selected_move = None
        for mid in player_chimera["moves"]:
            if data.MOVES[mid]["name"] in content:
                selected_move = mid
                break
        
        if selected_move:
            battle["actions"][user_id] = {"type": "move", "value": selected_move}
            ctx["sub_state"] = BATTLE_SUB_WAIT
            return _check_pvp_turn_ready(battle)

        return "コマンドを選んで。『戦う』『降参』などよ。", []
    return "...", []

def _check_pvp_turn_ready(battle):
    p1, p2 = battle["p1"], battle["p2"]
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
    
    speed1 = c1["stats"]["spe"]
    speed2 = c2["stats"]["spe"]
    
    if speed1 > speed2: order = [(p1, c1, act1, p2, c2), (p2, c2, act2, p1, c1)]
    elif speed2 > speed1: order = [(p2, c2, act2, p1, c1), (p1, c1, act1, p2, c2)]
    else:
        if random.random() < 0.5: order = [(p1, c1, act1, p2, c2), (p2, c2, act2, p1, c1)]
        else: order = [(p2, c2, act2, p1, c1), (p1, c1, act1, p2, c2)]
            
    logs = []
    for actor_id, actor_c, act, target_id, target_c in order:
        if actor_c["current_hp"] <= 0: continue
        if act["type"] == "move":
            mid = act["value"]
            mdata = data.MOVES[mid]
            if mdata["category"] == "Physical":
                dmg = int(mdata["power"] * (actor_c["stats"]["atk"] / target_c["stats"]["def"]) / 2)
            else:
                dmg = int(mdata["power"] * (actor_c["stats"]["spa"] / target_c["stats"]["spd"]) / 2)
            dmg = int(dmg * random.uniform(0.85, 1.0))
            if dmg < 1: dmg = 1
            
            target_c["current_hp"] -= dmg
            logs.append(f"**{actor_c['nickname']}** の {mdata['name']}！ {target_c['nickname']} に {dmg} のダメージ！")
            if target_c["current_hp"] <= 0:
                target_c["current_hp"] = 0
                logs.append(f"**{target_c['nickname']}** は倒れた！")
                
    battle["actions"] = {}
    full_log = "\n".join(logs)
    
    loser = None
    if c1["current_hp"] <= 0 and c2["current_hp"] <= 0:
        core.save_user_data(p1, ud1)
        core.save_user_data(p2, ud2)
        _end_pvp(battle)
        msg = f"{full_log}\n\n相打ちね！ 引き分けよ！"
        return "", [(p1, msg), (p2, msg)]

    if c1["current_hp"] <= 0: loser = p1
    elif c2["current_hp"] <= 0: loser = p2
    
    if loser:
        core.save_user_data(p1, ud1)
        core.save_user_data(p2, ud2)
        _end_pvp(battle)
        winner = p2 if loser == p1 else p1
        msg = f"{full_log}\n\n勝負あり！ <@{winner}> の勝利よ！"
        KIMERA_SESSIONS[p1]["state"] = STATE_MENU
        KIMERA_SESSIONS[p2]["state"] = STATE_MENU
        KIMERA_SESSIONS[p1]["context"]["sub_state"] = BATTLE_SUB_MAIN
        KIMERA_SESSIONS[p2]["context"]["sub_state"] = BATTLE_SUB_MAIN
        return "", [(p1, msg), (p2, msg)]

    core.save_user_data(p1, ud1)
    core.save_user_data(p2, ud2)
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
    target_k = None
    for k, v in PVP_BATTLES.items():
        if v == battle: target_k = k
    if target_k: del PVP_BATTLES[target_k]

# --- 統合ハンドラ ---
def process_kimera_command(user_id, content):
    session = get_session(user_id)
    if not session:
        if "キメラと遊びたい" in content:
            start_session(user_id)
            return "あら、キメラたちと遊びたいの？", []
        return None
    
    if content in ["終了", "やめる", "もう遊び疲れたよ"]:
        end_session(user_id)
        return "また遊びましょ♪", []

    st = session["state"]
    if st == STATE_MENU: return handle_menu(user_id, content)
    elif st == STATE_SHOP: return handle_shop(user_id, content)
    elif st == STATE_BATTLE_SELECT: return handle_battle_select(user_id, content)
    elif st == STATE_BATTLE_PVP_LOBBY: return handle_pvp_lobby(user_id, content)
    elif st in [STATE_BATTLE_WILD, STATE_BATTLE_TRAINER, STATE_BATTLE_CHALLENGE]: return handle_battle_action(user_id, content)
    elif st == STATE_BATTLE_PVP: return handle_pvp_action(user_id, content)
    
    return None