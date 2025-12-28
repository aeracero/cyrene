# kimera_game.py
import random
import kimera_core as core
import kimera_data as data

# --- 状態定義 ---
STATE_MENU = "menu"
STATE_SHOP = "shop"
STATE_BATTLE_SELECT = "battle_select"
STATE_BATTLE_WILD = "battle_wild"
STATE_BATTLE_TRAINER = "battle_trainer"
STATE_BATTLE_PVP = "battle_pvp"

# 戦闘中のサブステート
BATTLE_SUB_MAIN = "main"    # コマンド選択
BATTLE_SUB_ITEM = "item"    # 道具選択
BATTLE_SUB_SWITCH = "switch"# 入れ替え選択

KIMERA_SESSIONS = {}

def get_session(user_id):
    return KIMERA_SESSIONS.get(user_id)

def start_session(user_id):
    core.get_user_data(user_id) # 初期化保証
    KIMERA_SESSIONS[user_id] = {"state": STATE_MENU, "context": {}}

def end_session(user_id):
    if user_id in KIMERA_SESSIONS:
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
            "3. **対戦ゾーン** (準備中)"
        )
    
    if "編成" in content:
        ud = core.get_user_data(user_id)
        party_txt = "\n".join([f"{i+1}. {c['nickname']} (Lv.{c['level']})" for i, c in enumerate(ud['party'])])
        return f"【現在のパーティ】\n{party_txt}\n\n※入れ替え機能は作成中よ♪"

    if "詳細" in content:
        ud = core.get_user_data(user_id)
        if not ud['party']: return "キメラを持ってないみたいね…"
        chimera = ud['party'][0]
        stats_txt = core.get_chimera_display_stats(chimera)
        return f"【先頭のキメラ詳細】\n{stats_txt}"

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
        )

    return "『バトル』『編成』『キメラ詳細』『ショップ』の中から選んでね♪"

# --- ショップ処理 ---
def handle_shop(user_id, content):
    session = KIMERA_SESSIONS[user_id]
    
    if "戻る" in content:
        session["state"] = STATE_MENU
        return "メニューに戻るわね。"

    # アイテム名の照合
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
            # ここでも直接 ud を操作して保存する形に統一
            ud["money"] -= price
            ud["items"][target_key] = ud["items"].get(target_key, 0) + 1
            core.save_user_data(user_id, ud)
            
            return f"**{item['name']}** を購入したわ♪ (残金: {ud['money']}G)\n他には？"
        else:
            return f"お金が足りないみたい… (所持金: {ud['money']}G, 必要: {price}G)"
            
    return "商品名がわからないわ。正しく入力してちょうだい。"

# --- バトル選択 ---
def handle_battle_select(user_id, content):
    session = KIMERA_SESSIONS[user_id]
    
    if "確保" in content or "1" in content:
        wild_base = random.choice(list(data.BASE_CHIMERAS.keys()))
        wild_chimera = core.create_chimera_instance(wild_base, level=3)
        
        session["state"] = STATE_BATTLE_WILD
        session["context"] = {"enemy": wild_chimera, "sub_state": BATTLE_SUB_MAIN}
        
        return (
            f"草むらから 野生の **{wild_chimera['nickname']}** (Lv.{wild_chimera['level']}) が飛び出してきた！\n"
            "どうする？ 『戦う』 『道具』 『入れ替え』 『逃げる』"
        )

    if "レベル上げ" in content or "2" in content:
        cpu_base = random.choice(list(data.BASE_CHIMERAS.keys()))
        cpu_chimera = core.create_chimera_instance(cpu_base, level=5)
        
        session["state"] = STATE_BATTLE_TRAINER
        session["context"] = {"enemy": cpu_chimera, "sub_state": BATTLE_SUB_MAIN}

        return (
            f"黄金裔の幻影が現れた！ **{cpu_chimera['nickname']}** (Lv.{cpu_chimera['level']}) を繰り出してきたわ！\n"
            "どうする？ 『戦う』 『道具』 『入れ替え』 『逃げる』"
        )
        
    return "『確保』『レベル上げ』から選んでちょうだい。"

# --- バトルアクション ---
def handle_battle_action(user_id, content):
    session = KIMERA_SESSIONS[user_id]
    ctx = session["context"]
    enemy = ctx["enemy"]
    ud = core.get_user_data(user_id)
    player_chimera = ud['party'][0] # 先頭

    sub = ctx.get("sub_state", BATTLE_SUB_MAIN)

    # === メインコマンド選択 ===
    if sub == BATTLE_SUB_MAIN:
        if "逃" in content:
            end_session(user_id)
            return "戦闘から逃げ出したわ。安全第一ね♪"

        if "道具" in content:
            ctx["sub_state"] = BATTLE_SUB_ITEM
            # 所持アイテム一覧を表示
            items_list = []
            for k, count in ud["items"].items():
                if count > 0:
                    iname = data.ITEMS[k]["name"]
                    items_list.append(f"・{iname} (x{count})")
            if not items_list:
                ctx["sub_state"] = BATTLE_SUB_MAIN
                return "道具を何も持っていないわ！\nどうする？ 『戦う』 『入れ替え』 『逃げる』"
            return f"どの道具を使う？\n" + "\n".join(items_list) + "\n(キャンセルなら『戻る』)"

        if "入れ替え" in content:
            ctx["sub_state"] = BATTLE_SUB_SWITCH
            party_list = []
            for i, c in enumerate(ud["party"]):
                status = "瀕死" if c["current_hp"] <= 0 else f"{c['current_hp']}/{c['stats']['max_hp']}"
                party_list.append(f"{i+1}. {c['nickname']} (Lv.{c['level']}) [{status}]")
            return "誰と入れ替える？番号で教えてね。\n" + "\n".join(party_list) + "\n(キャンセルなら『戻る』)"

        if "戦" in content:
            moves_txt = " / ".join([f"{data.MOVES[m]['name']}" for m in player_chimera["moves"]])
            return f"どの技を使う？\n[{moves_txt}]"

        # 技名入力判定（攻撃処理）
        selected_move = None
        for mid in player_chimera["moves"]:
            if data.MOVES[mid]["name"] in content:
                selected_move = mid
                break
        
        if selected_move:
            return execute_turn(user_id, session, player_chimera, enemy, selected_move, ud)
            
        return "コマンドがわからないわ。『戦う』『道具』『入れ替え』『逃げる』を選んで？"

    # === 道具選択画面 ===
    elif sub == BATTLE_SUB_ITEM:
        if "戻る" in content:
            ctx["sub_state"] = BATTLE_SUB_MAIN
            return "どうする？ 『戦う』 『道具』 『入れ替え』 『逃げる』"
        
        # アイテム特定
        target_item = None
        for k in ud["items"]:
            if data.ITEMS[k]["name"] in content:
                target_item = k
                break
        
        if target_item:
            return use_item_in_battle(user_id, session, target_item, ud, player_chimera, enemy)

        return "その道具は持っていないみたい。名前を正しく入力してね。"

    # === 入れ替え選択画面 ===
    elif sub == BATTLE_SUB_SWITCH:
        if "戻る" in content:
            ctx["sub_state"] = BATTLE_SUB_MAIN
            return "どうする？ 『戦う』 『道具』 『入れ替え』 『逃げる』"
        
        try:
            # 数字判定（全角対応）
            idx = int(content.translate(str.maketrans({chr(0xFF01 + i): chr(0x21 + i) for i in range(94)}))) - 1
            if 0 <= idx < len(ud["party"]):
                target = ud["party"][idx]
                if target["current_hp"] <= 0:
                    return f"{target['nickname']} は瀕死で戦えないわ。"
                if target == player_chimera:
                    return "その子はもう出ているわよ。"
                
                # 入れ替え実行
                ud["party"][0], ud["party"][idx] = ud["party"][idx], ud["party"][0]
                core.save_user_data(user_id, ud)
                ctx["sub_state"] = BATTLE_SUB_MAIN
                
                # 入れ替えはターン消費（敵の攻撃を受ける）
                return f"戻れ、{player_chimera['nickname']}！ 行け、{target['nickname']}！\n" + \
                       enemy_attack_phase(user_id, session, target, enemy, ud)
            else:
                return "その番号のキメラはいないわ。"
        except ValueError:
            return "番号で教えてちょうだい。"

    return "エラーが発生したみたい。一度『終了』してリセットしましょうか。"

# --- ターン処理ロジック ---
def execute_turn(user_id, session, player, enemy, move_id, ud):
    # プレイヤーの攻撃
    move_data = data.MOVES[move_id]
    
    # 命中判定（簡易）
    if random.randint(1, 100) > move_data["accuracy"]:
        msg = f"{player['nickname']} の {move_data['name']}！\nしかし攻撃は外れた！"
    else:
        # ダメージ計算
        if move_data["category"] == "Physical":
            raw = move_data["power"] * (player["stats"]["atk"] / enemy["stats"]["def"])
        else:
            raw = move_data["power"] * (player["stats"]["spa"] / enemy["stats"]["spd"])
        
        # アイテム補正
        if player["held_item"] == "power_band" and move_data["category"] == "Physical":
            raw *= 1.1

        damage = int(raw / 2 * random.uniform(0.85, 1.0))
        if damage < 1: damage = 1

        enemy["current_hp"] -= damage
        msg = f"{player['nickname']} の {move_data['name']}！\n相手に {damage} のダメージ！"

    # 敵ダウン判定
    if enemy["current_hp"] <= 0:
        enemy["current_hp"] = 0
        msg += f"\n相手の {enemy['nickname']} は倒れた！ 勝利よ♪"
        
        # 経験値
        xp_gain = enemy["level"] * 15
        player["xp"] += xp_gain
        msg += f"\n{xp_gain} の経験値を獲得！"
        if player["xp"] >= player["next_xp"]:
            msg += core.level_up_chimera(player)
            
        # お金 (修正箇所: 直接 ud を操作する)
        money_gain = enemy["level"] * 50
        ud["money"] += money_gain
        msg += f"\n賞金 {money_gain}G を手に入れたわ。"

        core.save_user_data(user_id, ud)
        end_session(user_id)
        return msg + "\n\nメニューに戻るわね。"

    # 敵の反撃
    msg += "\n" + enemy_attack_phase(user_id, session, player, enemy, ud)
    return msg

def enemy_attack_phase(user_id, session, player, enemy, ud):
    enemy_move_id = random.choice(enemy["moves"])
    e_move = data.MOVES[enemy_move_id]
    
    # ダメージ計算（敵）
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
        
        # パーティにまだ生き残りがいるか？
        alive = [c for c in ud["party"] if c["current_hp"] > 0]
        if alive:
            # 自動入れ替え待ち状態にしてもいいが、簡易的にここで終了
            end_session(user_id)
            return msg + f"\n\n{player['nickname']} は倒れてしまった…！\n勝負に負けてしまったわ。キメラセンターで休ませてあげましょ。"
        else:
            end_session(user_id)
            return msg + "\n\n手持ちのキメラが全滅してしまったわ…目の前が真っ暗になった。"

    core.save_user_data(user_id, ud)
    return msg

# --- アイテム使用処理 ---
def use_item_in_battle(user_id, session, item_key, ud, player, enemy):
    item_data = data.ITEMS[item_key]
    ctx = session["context"]

    # 1. 捕獲アイテム（モンスターボール等）
    if item_data["effect_type"] == "capture":
        if session["state"] != STATE_BATTLE_WILD:
            return "人のキメラにボールを投げるのは泥棒よ！"
        
        # 消費 (修正: 直接操作)
        ud["items"][item_key] -= 1
        if ud["items"][item_key] <= 0:
            del ud["items"][item_key]
        
        # 捕獲計算 (HPが減っているほど確率アップ)
        hp_rate = enemy["current_hp"] / enemy["stats"]["max_hp"]
        catch_chance = ((1 - hp_rate) * 80 + 20) * item_data["value"] # 簡易式
        
        msg = f"{item_data['name']} を投げた！"
        if random.randint(0, 100) < catch_chance:
            if len(ud["party"]) < 3:
                ud["party"].append(enemy)
                loc = "手持ち"
            else:
                ud["box"].append(enemy)
                loc = "ボックス"
            
            enemy["current_hp"] = enemy["stats"]["max_hp"] # 回復
            core.save_user_data(user_id, ud)
            end_session(user_id)
            return f"{msg}\nやった！ **{enemy['nickname']}** を捕まえたわ！\n{loc}に送ったわよ♪"
        else:
            # 失敗したら敵のターン
            ctx["sub_state"] = BATTLE_SUB_MAIN
            return f"{msg}\nああっ！ ボールから抜け出されたわ！\n" + enemy_attack_phase(user_id, session, player, enemy, ud)

    # 2. 回復アイテム
    elif item_data["effect_type"] == "heal":
        if player["current_hp"] >= player["stats"]["max_hp"]:
            return "その子はもう元気いっぱいよ。"
        
        # 消費 (修正: 直接操作)
        ud["items"][item_key] -= 1
        if ud["items"][item_key] <= 0:
            del ud["items"][item_key]

        heal_val = item_data["value"]
        player["current_hp"] += heal_val
        if player["current_hp"] > player["stats"]["max_hp"]:
            player["current_hp"] = player["stats"]["max_hp"]
            
        core.save_user_data(user_id, ud)
        ctx["sub_state"] = BATTLE_SUB_MAIN
        
        # 敵のターンへ
        return f"{item_data['name']} を使った。\n{player['nickname']} のHPが回復したわ！\n" + \
               enemy_attack_phase(user_id, session, player, enemy, ud)

    # 3. その他（戦闘中に使えないもの）
    else:
        return "それは今使えないみたい。"

# --- 統合ハンドラ ---
def process_kimera_command(user_id, content):
    session = get_session(user_id)
    
    if not session:
        if "キメラと遊びたい" in content:
            start_session(user_id)
            return "あら、キメラたちと遊びたいの？いいわよ♪\n何をしたいかしら？\n\n『バトル』 『編成』 『キメラ詳細』 『ショップ』"
        return None

    if content == "終了" or content == "やめる":
        end_session(user_id)
        return "キメラとの遊びはおしまいね。また遊びましょ♪"

    state = session["state"]
    
    if state == STATE_MENU:
        return handle_menu(user_id, content)
    
    elif state == STATE_SHOP:
        return handle_shop(user_id, content)
    
    elif state == STATE_BATTLE_SELECT:
        return handle_battle_select(user_id, content)
    
    elif state in [STATE_BATTLE_WILD, STATE_BATTLE_TRAINER, STATE_BATTLE_PVP]:
        return handle_battle_action(user_id, content)
        
    return None