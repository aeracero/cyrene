# kimera_game.py
import random
import kimera_core as core
import kimera_data as data
import database as db

# --- 状態定数 ---
STATE_MENU = "menu"
STATE_BATTLE_SELECT = "battle_select"
STATE_BATTLE_WILD = "battle_wild"   # 確保
STATE_BATTLE_TRAINER = "battle_trainer" # レベル上げ
STATE_BATTLE_PVP = "battle_pvp"

# ユーザーの一時的な対話状態を保持（Discordのステート管理用）
# {user_id: {"state": "...", "context": {...}}}
KIMERA_SESSIONS = {}

def get_session(user_id):
    return KIMERA_SESSIONS.get(user_id)

def start_session(user_id):
    KIMERA_SESSIONS[user_id] = {"state": STATE_MENU, "context": {}}
    # ユーザーデータ初期化チェック
    core.get_user_data(user_id)

def end_session(user_id):
    if user_id in KIMERA_SESSIONS:
        del KIMERA_SESSIONS[user_id]

# --- メインメニュー処理 ---
def handle_menu(user_id, content):
    """メニュー選択の処理"""
    if "バトル" in content:
        KIMERA_SESSIONS[user_id]["state"] = STATE_BATTLE_SELECT
        return (
            "どのゾーンに行く？\n"
            "1. **確保ゾーン** (野生のキメラを捕まえる)\n"
            "2. **レベル上げゾーン** (黄金裔CPUと戦う)\n"
            "3. **対戦ゾーン** (他のプレイヤーと対戦)"
        )
    
    if "編成" in content:
        ud = core.get_user_data(user_id)
        party_txt = "\n".join([f"{i+1}. {c['nickname']} (Lv.{c['level']})" for i, c in enumerate(ud['party'])])
        return (
            f"【現在のパーティ】\n{party_txt}\n\n"
            "入れ替える場合は『ボックス』、順番を変えるなら『並び替え』と言ってね。"
        )

    if "詳細" in content or "キメラ詳細" in content:
        ud = core.get_user_data(user_id)
        # 先頭のキメラを表示
        if not ud['party']: return "キメラを持ってないみたいね…"
        chimera = ud['party'][0]
        stats_txt = core.get_chimera_display_stats(chimera)
        return f"【先頭のキメラ詳細】\n{stats_txt}\n\n『持ち物変更』や『技確認』もできるわよ。"

    if "ショップ" in content:
        items = data.ITEMS
        shop_list = "\n".join([f"・{v['name']}: {v['price']}G - {v['desc']}" for k, v in items.items()])
        ud = core.get_user_data(user_id)
        return f"【ショップ】 (所持金: {ud['money']}G)\n{shop_list}\n\n『〇〇を買う』と言ってね。"

    return "『バトル』『編成』『キメラ詳細』『ショップ』の中から選んでね♪"

# --- バトル選択処理 ---
def handle_battle_select(user_id, content):
    session = KIMERA_SESSIONS[user_id]
    
    if "確保" in content or "1" in content:
        # 野生エンカウント生成
        wild_base = random.choice(list(data.BASE_CHIMERAS.keys()))
        wild_chimera = core.create_chimera_instance(wild_base, level=3) # 低レベル
        
        session["state"] = STATE_BATTLE_WILD
        session["context"]["enemy"] = wild_chimera
        session["context"]["turn"] = 1
        
        return (
            f"草むらから 野生の **{wild_chimera['nickname']}** (Lv.{wild_chimera['level']}) が飛び出してきた！\n"
            "『戦う』 『道具』 『逃げる』"
        )

    if "レベル上げ" in content or "2" in content:
        # CPU生成 (黄金裔の誰か)
        cpu_base = random.choice(list(data.BASE_CHIMERAS.keys()))
        cpu_chimera = core.create_chimera_instance(cpu_base, level=5) # 適正レベル
        
        session["state"] = STATE_BATTLE_TRAINER
        session["context"]["enemy"] = cpu_chimera
        session["context"]["turn"] = 1

        return (
            f"黄金裔の幻影が現れた！ **{cpu_chimera['nickname']}** (Lv.{cpu_chimera['level']}) を繰り出してきたわ！\n"
            "『戦う』 『入れ替え』 『逃げる』"
        )

    if "対戦" in content or "3" in content:
        # 未実装
        session["state"] = STATE_MENU
        return "対戦機能はまだ準備中よ。ロビーに戻るわね♪"

    return "『確保』『レベル上げ』『対戦』から選んでちょうだい。"

# --- バトル処理 (簡易版) ---
def handle_battle_action(user_id, content):
    session = KIMERA_SESSIONS[user_id]
    ctx = session["context"]
    enemy = ctx["enemy"]
    ud = core.get_user_data(user_id)
    player_chimera = ud['party'][0] # 先頭

    # 逃げる
    if "逃" in content:
        end_session(user_id)
        return "戦闘から逃げ出したわ。安全第一ね♪"

    # 戦う (技選択)
    if "戦" in content:
        moves_txt = " / ".join([f"{data.MOVES[m]['name']}" for m in player_chimera["moves"]])
        return f"どの技を使う？\n[{moves_txt}]"
    
    # 技名入力判定
    selected_move = None
    for mid in player_chimera["moves"]:
        if data.MOVES[mid]["name"] in content:
            selected_move = mid
            break
    
    if selected_move:
        # ダメージ計算 (超簡易)
        move_data = data.MOVES[selected_move]
        damage = int(move_data["power"] * (player_chimera["stats"]["atk"] / enemy["stats"]["def"]) / 2)
        if move_data["category"] == "Special":
            damage = int(move_data["power"] * (player_chimera["stats"]["spa"] / enemy["stats"]["spd"]) / 2)
        
        # 乱数
        damage = int(damage * random.uniform(0.85, 1.0))
        if damage < 1: damage = 1

        enemy["current_hp"] -= damage
        msg = f"{player_chimera['nickname']} の {move_data['name']}！\n相手に {damage} のダメージ！"

        if enemy["current_hp"] <= 0:
            msg += f"\n相手の {enemy['nickname']} は倒れた！\n勝利よ♪"
            # 経験値処理
            xp_gain = enemy["level"] * 10
            player_chimera["xp"] += xp_gain
            msg += f"\n{xp_gain} の経験値を獲得！"
            
            if player_chimera["xp"] >= player_chimera["next_xp"]:
                lvl_msg = core.level_up_chimera(player_chimera)
                msg += f"\n{lvl_msg}"
            
            # 確保モードなら捕獲処理を入れる場所だが今回は倒したら終わり
            if session["state"] == STATE_BATTLE_WILD and "捕まえる" in content: # 本来は道具で捕獲
                pass 

            core.save_user_data(user_id, ud)
            end_session(user_id)
            return msg + "\n\nメニューに戻るわね。"

        # 敵の攻撃 (反撃)
        enemy_move_id = random.choice(enemy["moves"])
        e_move = data.MOVES[enemy_move_id]
        e_dmg = 10 # 敵の計算は省略して固定か乱数で
        player_chimera["current_hp"] -= e_dmg
        
        msg += f"\n\n相手の {enemy['nickname']} の {e_move['name']}！\n{player_chimera['nickname']} に {e_dmg} のダメージ！"
        msg += f"\n(残りHP: {player_chimera['current_hp']}/{player_chimera['stats']['max_hp']})"

        if player_chimera["current_hp"] <= 0:
            msg += f"\n\n{player_chimera['nickname']} は倒れてしまった…目の前が真っ暗になったわ。"
            player_chimera["current_hp"] = player_chimera["stats"]["max_hp"] # 簡易回復
            core.save_user_data(user_id, ud)
            end_session(user_id)
            return msg

        return msg

    # 確保モード限定: ボールを投げる (アイテム概念の簡易版)
    if session["state"] == STATE_BATTLE_WILD and ("ボール" in content or "確保" in content or "捕" in content):
        catch_rate = 50 # %
        if random.randint(1, 100) <= catch_rate:
            if len(ud["party"]) < 3:
                ud["party"].append(enemy)
                msg_loc = "手持ち"
            else:
                ud["box"].append(enemy)
                msg_loc = "ボックス"
            
            enemy["current_hp"] = enemy["stats"]["max_hp"] # 回復してあげる
            core.save_user_data(user_id, ud)
            end_session(user_id)
            return f"やった！ {enemy['nickname']} を捕まえたわ！\n{msg_loc}に送ったわよ♪"
        else:
            return "ああっ！ ボールから抜け出されたわ！"

    return "コマンドがわからないわ。『戦う』か『逃げる』を選んで？"

# --- 統合ハンドラ ---
def process_kimera_command(user_id, content):
    """Discordからの入力を状態で振り分ける"""
    session = get_session(user_id)
    
    if not session:
        if "キメラと遊びたい" in content:
            start_session(user_id)
            return "あら、キメラたちと遊びたいの？いいわよ♪\n何をしたいかしら？\n\n『バトル』 『編成』 『キメラ詳細』 『ショップ』"
        return None

    # 中断コマンド
    if content == "終了" or content == "やめる":
        end_session(user_id)
        return "キメラとの遊びはおしまいね。また遊びましょ♪"

    state = session["state"]
    
    if state == STATE_MENU:
        return handle_menu(user_id, content)
    
    elif state == STATE_BATTLE_SELECT:
        return handle_battle_select(user_id, content)
    
    elif state in [STATE_BATTLE_WILD, STATE_BATTLE_TRAINER, STATE_BATTLE_PVP]:
        return handle_battle_action(user_id, content)
        
    return None