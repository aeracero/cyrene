# kimera_game.py
import random
import re
import math
import kimera_core as core
import database as db
import logic
import kimera_data as data
from config import PRIMARY_ADMIN_ID # 管理者ID読み込み

# --- 状態定義 ---
STATE_MENU = "menu"
STATE_SHOP = "shop"
STATE_BATTLE_SELECT = "battle_select"
STATE_BATTLE_WILD = "battle_wild"
STATE_BATTLE_TRAINER = "battle_trainer"
STATE_BATTLE_CHALLENGE = "battle_challenge"
STATE_BATTLE_PVP_LOBBY = "battle_pvp_lobby"
STATE_BATTLE_PVP = "battle_pvp"
STATE_BOX = "box_menu"
STATE_EQUIP = "equip_menu"

# サブステート
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
    # 初期状態は「ノーマルモード」としてセッション開始
    KIMERA_SESSIONS[user_id] = {
        "state": STATE_MENU, 
        "context": {},
        "is_hard_mode": False 
    }
    # データをロードしてキャッシュ（存在チェック）
    core.get_user_data(user_id, hard_mode=False)

def end_session(user_id):
    if user_id in KIMERA_SESSIONS:
        if KIMERA_SESSIONS[user_id]["state"] == STATE_BATTLE_PVP_LOBBY:
            to_del = [k for k, v in PVP_CHALLENGES.items() if v == user_id]
            for k in to_del:
                del PVP_CHALLENGES[k]
        del KIMERA_SESSIONS[user_id]

# --- バトル用ヘルパー関数群（ロジック追加部分） ---

def _init_battle_context(session, enemy_party, enemy_name, stage=None, potions=0):
    """バトル開始時のコンテキスト初期化（アビリティ用変数の設定）"""
    session["context"] = {
        "enemy_party": enemy_party,
        "enemy_name": enemy_name,
        "stage": stage,
        "sub_state": BATTLE_SUB_MAIN,
        "potions": potions,
        "turn_count": 0,
        # フィールド状態
        "field_effects": {
            "icarun": {"p1": False, "p2": False}, # ヒアシンシア: イカルン
            "kyurene_ghost": {"p1": False, "p2": False}, # キュレネ: ゴースト化
            "embers": {"p1": 0, "p2": 0}, # ファイノン: 火種
            "remembrance": {"p1": 0, "p2": 0}, # キュレネ: 追憶
            "aglaia_speed": {"p1": 0, "p2": 0}, # アグライア: 加速バトン
        },
        "logs": []
    }
    # 各個体のバトル用一時ステータス初期化
    _init_chimera_battle_states(session, "p1")
    _init_chimera_battle_states(session, "p2")

def _init_chimera_battle_states(session, side):
    """各キメラの戦闘時一時データをリセット"""
    user_id = [k for k, v in KIMERA_SESSIONS.items() if v == session][0] # 逆引き（簡易）
    ud = core.get_user_data(user_id, hard_mode=session.get("is_hard_mode", False))
    
    party = ud["party"] if side == "p1" else session["context"]["enemy_party"]
    
    for c in party:
        c["battle_state"] = {
            "revived": False, # メデイモス復活
            "barrier_hp": 0,  # 丹恒バリア
            "submission_prep": False, # ケリュドラ屈服準備
            "rocket": False, # トリスビアスロケット
            "oblivion_cd": 0, # 三月なのか忘却CD
            "form": None # 変身
        }
        # キュレネ初期スタック (追憶)
        base = data.BASE_CHIMERAS[c["base_id"]]
        if base["name"] == "キュヌレ":
            session["context"]["field_effects"]["remembrance"][side] = 24

def _calculate_damage(attacker, defender, move_id, session):
    """タイプ相性・特性込みのダメージ計算"""
    move = data.MOVES[move_id]
    base_atk = data.BASE_CHIMERAS[attacker["base_id"]]
    base_def = data.BASE_CHIMERAS[defender["base_id"]]
    
    # 1. 威力
    power = move["power"]
    if move["category"] == "Status": return 0
    
    # 2. ステータス (ランク補正は core.calculate_stat_with_stage が必要だが簡易実装)
    # ※ 本来はランク補正関数を使うべき場所
    a_stat = attacker["stats"]["atk"] if move["category"] == "Physical" else attacker["stats"]["spa"]
    d_stat = defender["stats"]["def"] if move["category"] == "Physical" else defender["stats"]["spd"]
    
    # 火傷補正
    if attacker.get("status_condition") == "burn" and move["category"] == "Physical":
        a_stat = int(a_stat * 0.5)

    # 3. ダメージ計算
    dmg = int(math.floor(math.floor(math.floor(2 * attacker["level"] / 5 + 2) * power * a_stat / d_stat) / 50) + 2)
    
    # 4. タイプ相性
    type_eff = 1.0
    if move["type"] in data.TYPE_CHART:
        eff_dict = data.TYPE_CHART[move["type"]]
        if base_def["type"] in eff_dict:
            type_eff = eff_dict[base_def["type"]]
    
    dmg = int(dmg * type_eff)
    
    # 5. 屈服補正 (攻撃側が屈服状態)
    if attacker.get("status_condition") == "submission":
        dmg = int(dmg * 0.75)

    # 6. ランダム幅
    dmg = int(dmg * random.uniform(0.85, 1.0))
    if dmg < 1: dmg = 1

    # 半減の実
    if core.check_resist_berry(defender, move["type"]):
        dmg = int(dmg * 0.5)
        defender["held_item"] = None
        session["context"]["logs"].append(f"半減の実が {defender['nickname']} を守ったわ♪")

    return dmg, type_eff

def _apply_status_effect(target, status_name, session):
    """状態異常付与"""
    if target.get("status_condition"): return False
    target["status_condition"] = status_name
    s_name = data.STATUS_CONDITIONS.get(status_name, {}).get("name", status_name)
    session["context"]["logs"].append(f"{target['nickname']} は {s_name} になっちゃったわ！")
    return True

# --- メニュー ---
def handle_menu(user_id, content):
    session = KIMERA_SESSIONS[user_id]
    is_hard = session.get("is_hard_mode", False)
    ud = core.get_user_data(user_id, hard_mode=is_hard)

    # --- ★デバッグ機能 ---
    if content == "デバッグ解放":
        normal_ud = core.get_user_data(user_id, hard_mode=False)
        normal_ud["items"]["story_page_2"] = 1
        core.save_user_data(user_id, normal_ud, hard_mode=False)
        return "【デバッグ】ノーマルデータに『story_page_2』を付与したわよ♪", []
    
    if content == "デバッグ封印":
        normal_ud = core.get_user_data(user_id, hard_mode=False)
        if "story_page_2" in normal_ud["items"]:
            del normal_ud["items"]["story_page_2"]
        core.save_user_data(user_id, normal_ud, hard_mode=False)
        return "【デバッグ】ノーマルデータから証を没収したわ。", []

    if content == "デバッグ実績":
        try:
            ach_data = db.load_achievements_data()
            user_ach = ach_data.get(str(user_id), {"unlocked": [], "stats": {}})
            
            if "kimera_champion" in user_ach["unlocked"]:
                user_ach["unlocked"].remove("kimera_champion")
                res = "OFF"
            else:
                user_ach["unlocked"].append("kimera_champion")
                res = "ON"
            
            ach_data[str(user_id)] = user_ach
            db.save_achievements_data(ach_data)
            return f"【デバッグ】実績『キメラチャンピオン』を {res} にしたわ♪", []
        except:
            return "エラーだわ。", []

    # --- ★管理者限定: 最強召喚 ---
    if content == "デバッグ最強召喚" and user_id == PRIMARY_ADMIN_ID:
        god = core.create_chimera_instance("kyunure", level=200, nickname="デバッグ神")
        god["ivs"] = {k: 31 for k in god["ivs"]}
        god["held_item"] = "leftovers"
        core.update_chimera_stats(god)
        god["current_hp"] = god["stats"]["max_hp"]
        
        if len(ud["party"]) < 3:
            ud["party"].append(god)
            loc = "手持ち"
        else:
            ud["box"].append(god)
            loc = "ボックス"
            
        core.save_user_data(user_id, ud, hard_mode=is_hard)
        return f"【管理者権限行使】\n最強個体『デバッグ神』(Lv.200/ALL31) を{loc}に召喚したわ♪ テストに使ってね♪", []

    # --- モード切替 ---
    if "真なるキメラマスターロード" in content:
        if is_hard:
            return "既に修羅の道（ハードモード）にいるわよ？ 心して挑んでね♪", []
        
        normal_ud = core.get_user_data(user_id, hard_mode=False)
        if "story_page_2" in normal_ud["items"]:
            session["is_hard_mode"] = True
            core.get_user_data(user_id, hard_mode=True)
            return (
                "【警告: 真なるキメラマスターロード解放】\n\n"
                "世界が反転し、黄金裔たちの真の力が解放されたわ……。\n"
                "これより『ハードモード』のセーブデータに切り替えるわね。\n"
                "敵はレベル100を超え、アイテムや特性をフル活用してくるわ。\n"
                "準備はいい？ 死にゲーの始まりよ♪", []
            )
        else:
            return "まだその扉を開く資格（ノーマルモードクリアの証）を持っていないみたいね。", []

    if "ノーマルに戻る" in content:
        if is_hard:
            session["is_hard_mode"] = False
            return "平和な世界（ノーマルモード）のデータに戻したわよ♪", []
        return "今はノーマルモードよ♪", []

    # --- バトル選択画面へ（ショートカット含む） ---
    norm_content = content.translate(str.maketrans({chr(0xFF10 + i): chr(0x30 + i) for i in range(10)}))

    if "バトル" in content or "チャレンジ" in content or "3" in norm_content:
        session["state"] = STATE_BATTLE_SELECT
        if "チャレンジ" in content or "3" in norm_content:
             return handle_battle_select(user_id, content)

        ud = core.get_user_data(user_id, hard_mode=is_hard)
        mode_text = "【真・キメラマスターロード】" if is_hard else "チャレンジモード"
        
        msg = (
            "どこに行くのかしら？\n"
            "1. **確保ゾーン** (野生捕獲)\n"
            "2. **レベル上げゾーン** (CPU戦)\n"
            f"3. **{mode_text}** (黄金裔13人抜き)\n"
            "4. **対戦ゾーン** (PvP)"
        )
        if not is_hard:
            normal_ud = core.get_user_data(user_id, hard_mode=False)
            if "story_page_2" in normal_ud["items"]:
                msg += "\n\n★『真なるキメラマスターロード』と言えば、裏世界へ連れて行ってあげるわよ♪"
        
        return msg, []
    
    if "編成" in content or "ボックス" in content:
        session["state"] = STATE_BOX
        return _get_box_menu_text(user_id), []

    if "装備" in content:
        session["state"] = STATE_EQUIP
        return _get_equip_menu_text(user_id), []

    if "詳細" in content:
        msg = f"【トレーナー】Lv.{ud['trainer_level']} (Exp:{ud['trainer_xp']}) / {ud['money']}G\n"
        if is_hard:
            msg += "★ 現在『ハードモード』データ参照中よ♪ ★\n"
        if not ud['party']:
            return msg + "キメラがいないわね。", []
        chimera = ud['party'][0]
        return f"{msg}【先頭】\n{core.get_chimera_display_stats(chimera)}", []

    if "ショップ" in content:
        session["state"] = STATE_SHOP
        tlv = ud["trainer_level"]
        lines = []
        for k, v in data.ITEMS.items():
            if v["price"] > 0 and v.get("unlock_rank", 1) <= tlv:
                lines.append(f"・**{v['name']}**: {v['price']}G")
        return f"【ショップ】 (所持金: {ud['money']}G / Lv.{tlv})\n" + "\n".join(lines) + "\n\n『〇〇を買う』 / 『戻る』 って言ってね♪", []

    if "回復" in content:
        core.heal_all_kimeras(ud)
        core.save_user_data(user_id, ud, hard_mode=is_hard)
        return "キメラセンターで手持ちとボックスの子を全回復しておいたわ♪", []

    # --- 図鑑機能 (強化版) ---
    if "図鑑" in content:
        m_search = re.search(r"図鑑\s+(.+)", content)
        if m_search:
            target_name = m_search.group(1).strip()
            found_key = None
            for k, v in data.BASE_CHIMERAS.items():
                if v["name"] == target_name:
                    found_key = k
                    break
            
            if not found_key:
                return "その名前のキメラはデータにないわね。", []

            status = ud["dex"].get(found_key)
            if not status:
                return "そのキメラはまだ発見していないみたい。", []
            
            base = data.BASE_CHIMERAS[found_key]
            
            if status == "seen":
                return (
                    f"━━━━━━━━━━━━━━━\n"
                    f"📖 **No.{found_key} {base['name']}**\n"
                    f"━━━━━━━━━━━━━━━\n"
                    f"【状態】 目撃のみ (詳細は捕まえてからのお楽しみね♪)\n"
                    f"【分類】 {base['type']}タイプ\n"
                    f"━━━━━━━━━━━━━━━"
                ), []
            
            elif status == "caught":
                rarity = "★" * base.get('rarity', 1)
                bs = base['base_stats']
                desc = base.get('description', '詳細不明。')
                total_bs = sum(bs.values())
                
                msg = (
                    f"━━━━━━━━━━━━━━━\n"
                    f"📖 **No.{found_key} {base['name']}** {rarity}\n"
                    f"━━━━━━━━━━━━━━━\n"
                    f"【分類】 {base['type']}タイプ\n"
                    f"【特性】 **{base['ability']}**\n"
                    f"-------------------------------\n"
                    f"【生態】\n"
                    f"{desc}\n"
                    f"-------------------------------\n"
                    f"【種族値 (Base Stats)】\n"
                    f" 🟢 HP : **{bs['hp']}**\n"
                    f" ⚔️ 攻撃: **{bs['atk']}**\n"
                    f" 🛡️ 防御: **{bs['def']}**\n"
                    f" ✨ 特攻: **{bs['spa']}**\n"
                    f" 🔮 特防: **{bs['spd']}**\n"
                    f" 💨 素早: **{bs['spe']}**\n"
                    f" 📊 合計: **{total_bs}**\n"
                    f"━━━━━━━━━━━━━━━"
                )
                return msg, []

        total = len(data.BASE_CHIMERAS)
        caught = sum(1 for v in ud["dex"].values() if v == "caught")
        seen = len(ud["dex"])
        
        lines = [f"【キメラ図鑑】 捕獲: {caught}/{total} / 発見: {seen}/{total}"]
        sorted_keys = sorted(data.BASE_CHIMERAS.keys())
        
        for k in sorted_keys:
            base = data.BASE_CHIMERAS[k]
            status = ud["dex"].get(k)
            
            if status == "caught":
                mark = "★" 
                display_name = base['name']
            elif status == "seen":
                mark = "○" 
                display_name = base['name']
            else:
                mark = "・" 
                display_name = "？？？"
            
            rarity_disp = f"({'★'*base['rarity']})" if status == "caught" else ""
            lines.append(f"{mark} {display_name} {rarity_disp}")
        
        lines.append("\n『図鑑 ウルフパピー』のように名前を入れると詳細が見れるわよ♪")
        return "\n".join(lines), []

    if "アイテム" in content:
        items_txt = ", ".join([f"{data.ITEMS[k]['name']}x{v}" for k, v in ud['items'].items()])
        return f"所持: {items_txt}\n(『けいけんアメSを使う』って言ってね♪)", []
        
    m = re.match(r"(.+)を使う", content)
    if m:
        item_name = m.group(1)
        item_key = None
        for k, v in data.ITEMS.items():
            if v["name"] == item_name:
                item_key = k
                break
        if item_key:
            if not ud["party"]:
                return "手持ちがいないわね。", []
            res = core.apply_item_effect_logic(ud, item_key, ud["party"][0])
            core.save_user_data(user_id, ud, hard_mode=is_hard)
            return res, []

    return (
        "【キメラメニュー】\n"
        "・**バトル**: 野生/CPU/対戦\n"
        "・**編成**: 手持ちとボックスの入れ替え\n"
        "・**装備**: アイテムを持たせる\n"
        "・**詳細**: ステータス確認\n"
        "・**ショップ**: ボールや薬を買う\n"
        "・**回復**: 全回復する\n"
        "・**図鑑**: 出会ったキメラを見る\n"
        "・**終了**: ゲームを終わる\n\n"
        "何をしたいのかしら？"
    ), []

# --- 装備操作 ---
def _get_equip_menu_text(user_id):
    session = KIMERA_SESSIONS[user_id]
    ud = core.get_user_data(user_id, hard_mode=session.get("is_hard_mode", False))
    
    msg = "【装備管理】\n"
    for i, c in enumerate(ud["party"]):
        item_name = data.ITEMS[c["held_item"]]["name"] if c["held_item"] else "なし"
        msg += f"{i+1}. {c['nickname']}: {item_name}\n"
    
    equipable = []
    for k, v in ud["items"].items():
        idata = data.ITEMS.get(k)
        if idata and idata["effect_type"].startswith("equip_"):
            equipable.append(f"{idata['name']}")
            
    msg += "\n【持っている装備品】\n" + (", ".join(equipable) if equipable else "(なし)")
    msg += "\n\n『1にハチマキを持たせる』『2を外す』\n『戻る』"
    return msg

def handle_equip_menu(user_id, content):
    session = KIMERA_SESSIONS[user_id]
    is_hard = session.get("is_hard_mode", False)
    ud = core.get_user_data(user_id, hard_mode=is_hard)
    
    if "戻る" in content:
        session["state"] = STATE_MENU
        return "メニューに戻るわね♪", []

    m = re.search(r"(\d+)に(.+?)を持たせる", content) or re.search(r"(\d+)に(.+?)", content)
    if m:
        idx = int(m.group(1)) - 1
        item_name = m.group(2).strip()
        item_key = next((k for k, v in data.ITEMS.items() if v["name"] == item_name), None)
        
        if item_key:
            res = core.equip_item_logic(ud, idx, item_key)
            core.save_user_data(user_id, ud, hard_mode=is_hard)
            return res + "\n" + _get_equip_menu_text(user_id), []
        else:
            return "そのアイテムは見つからないわね。", []

    m = re.search(r"(\d+)を外す", content)
    if m:
        idx = int(m.group(1)) - 1
        res = core.unequip_item_logic(ud, idx)
        core.save_user_data(user_id, ud, hard_mode=is_hard)
        return res + "\n" + _get_equip_menu_text(user_id), []

    return "『1にハチマキを持たせる』のように言ってね♪", []

# --- ボックス操作 ---
def _get_box_menu_text(user_id):
    session = KIMERA_SESSIONS[user_id]
    ud = core.get_user_data(user_id, hard_mode=session.get("is_hard_mode", False))
    
    msg = "【パーティ】\n"
    for i, c in enumerate(ud['party']):
        msg += f"P{i+1}: {c['nickname']} (Lv.{c['level']})\n"
    
    msg += "\n【ボックス】\n"
    if ud['box']:
        for i, c in enumerate(ud['box']):
            msg += f"B{i+1}: {c['nickname']} (Lv.{c['level']})\n"
    else:
        msg += "(空っぽ)"
        
    msg += "\n『P1とB1を交代』 『P2を預ける』 『B1を入れる』 『戻る』"
    return msg

def handle_box_menu(user_id, content):
    session = KIMERA_SESSIONS[user_id]
    is_hard = session.get("is_hard_mode", False)
    ud = core.get_user_data(user_id, hard_mode=is_hard)
    
    if "戻る" in content:
        session["state"] = STATE_MENU
        return "メニューに戻るわね♪", []

    m_swap = re.search(r"[Pp](\d+).*?[Bb](\d+)", content)
    m_to_box = re.search(r"[Pp](\d+).*?預ける", content)
    m_to_party = re.search(r"[Bb](\d+).*?入れる", content)

    if m_swap:
        pidx = int(m_swap.group(1))-1
        bidx = int(m_swap.group(2))-1
        if core.swap_party_box(ud, pidx, bidx):
            core.save_user_data(user_id, ud, hard_mode=is_hard)
            return "交代したわよ♪\n" + _get_box_menu_text(user_id), []
        return "指定が間違ってるみたいね。", []

    elif m_to_box:
        pidx = int(m_to_box.group(1))-1
        if core.move_party_to_box(ud, pidx):
            core.save_user_data(user_id, ud, hard_mode=is_hard)
            return "ボックスに預けたわ♪\n" + _get_box_menu_text(user_id), []
        return "最後の1体は預けられないわよ。", []

    elif m_to_party:
        bidx = int(m_to_party.group(1))-1
        if core.move_box_to_party(ud, bidx):
            core.save_user_data(user_id, ud, hard_mode=is_hard)
            return "手持ちに入れたわよ♪\n" + _get_box_menu_text(user_id), []
        return "手持ちがいっぱいね（最大3体）。", []

    return "『P1とB1を交代』のように言ってね♪", []

# --- ショップ ---
def handle_shop(user_id, content):
    session = KIMERA_SESSIONS[user_id]
    is_hard = session.get("is_hard_mode", False)
    ud = core.get_user_data(user_id, hard_mode=is_hard)
    
    if "戻る" in content:
        session["state"] = STATE_MENU
        return "メニューに戻るわね♪", []
    
    target_key = next((k for k, v in data.ITEMS.items() if v["name"] in content), None)
    
    if target_key:
        item = data.ITEMS[target_key]
        if item.get("unlock_rank", 1) > ud["trainer_level"]:
            return "今のレベルじゃまだ買えないわね。", []
        if ud["money"] >= item["price"]:
            ud["money"] -= item["price"]
            ud["items"][target_key] = ud["items"].get(target_key, 0) + 1
            core.save_user_data(user_id, ud, hard_mode=is_hard)
            return f"**{item['name']}** を購入したわ♪ (残: {ud['money']}G)", []
        else:
            return "お金が足りないみたいね。", []
    return "商品名を入力してね♪", []

# --- バトル選択 ---
def handle_battle_select(user_id, content):
    session = KIMERA_SESSIONS[user_id]
    is_hard = session.get("is_hard_mode", False)
    ud = core.get_user_data(user_id, hard_mode=is_hard)
    tlv = ud["trainer_level"]
    content = content.translate(str.maketrans({chr(0xFF10 + i): chr(0x30 + i) for i in range(10)}))

    if "確保" in content or "1" in content:
        rand = random.randint(1, 100)
        target_rarity = 1
        if rand > 98: target_rarity = 6
        elif rand > 90: target_rarity = 2
        elif rand > 60: target_rarity = 1
        
        candidates = [k for k, v in data.BASE_CHIMERAS.items() if v.get("rarity", 1) == target_rarity]
        if not candidates: candidates = [k for k, v in data.BASE_CHIMERAS.items() if v.get("rarity", 1) == 1]
        
        wild_base = random.choice(candidates)
        w_lv = max(1, tlv + random.randint(-1, 3))
        wild = core.create_chimera_instance(wild_base, level=w_lv)
        
        session["state"] = STATE_BATTLE_WILD
        _init_battle_context(session, [wild], "野生のキメラ")
        
        core.register_dex(ud, wild["base_id"], caught=False)
        core.save_user_data(user_id, ud, hard_mode=is_hard)
        
        rarity_star = "★" * wild.get("rarity", 1)
        return f"野生の **{wild['nickname']}** (Lv.{wild['level']}) {rarity_star} が飛び出してきたわ！\n『戦う』『道具』『入れ替え』『逃げる』", []

    if "レベル上げ" in content or "2" in content:
        cpu_base = random.choice(list(data.BASE_CHIMERAS.keys()))
        c_lv = max(5, tlv + random.randint(0, 5))
        cpu_c = core.create_chimera_instance(cpu_base, level=c_lv)
        session["state"] = STATE_BATTLE_TRAINER
        _init_battle_context(session, [cpu_c], "黄金裔の幻影")
        
        core.register_dex(ud, cpu_c["base_id"], caught=False)
        core.save_user_data(user_id, ud, hard_mode=is_hard)
        return f"黄金裔の幻影が現れたわ！ **{cpu_c['nickname']}** (Lv.{cpu_c['level']} HP:{cpu_c['current_hp']}) を繰り出してきたわよ！", []

    if "チャレンジ" in content or "3" in content:
        stage = ud.get("challenge_stage", 1)
        if stage > 13:
            stage = 1
            ud["challenge_stage"] = 1
            core.save_user_data(user_id, ud, hard_mode=is_hard)
        
        trainer_source = data.CHALLENGE_TRAINERS_HARD if is_hard else data.CHALLENGE_TRAINERS
        t_data = trainer_source.get(stage)
        if not t_data: return "準備中よ。", []
        
        enemy_party = []
        for p in t_data["party"]:
            c = core.create_chimera_instance(p["base_id"], p["level"], held_item=p.get("item"))
            enemy_party.append(c)
            core.register_dex(ud, c["base_id"], caught=False)
        
        core.save_user_data(user_id, ud, hard_mode=is_hard)
        session["state"] = STATE_BATTLE_CHALLENGE
        _init_battle_context(session, enemy_party, t_data["name"], stage=stage, potions=t_data.get("potions", 0))
        
        start_msg = t_data.get("dialogue_start", "勝負よ！")
        first = enemy_party[0]
        return (
            f"【チャレンジモード Stage {stage}】\n"
            f"**{t_data['name']}**: 「{start_msg}」\n"
            f"相手は **{first['nickname']}** (Lv.{first['level']} HP:{first['current_hp']}) を繰り出してきたわ！"
        ), []

    if "対戦" in content or "4" in content:
        challenger = PVP_CHALLENGES.get(user_id)
        if challenger: return _initiate_pvp_battle(challenger, user_id)
        session["state"] = STATE_BATTLE_PVP_LOBBY
        return "対戦相手の「名前」を入力して招待してね♪", []

    return "モードを選んでちょうだい♪", []

# --- バトルアクション (PvE) ---
def handle_battle_action(user_id, content):
    session = KIMERA_SESSIONS[user_id]
    if session["state"] == STATE_BATTLE_PVP: return handle_pvp_action(user_id, content)

    ctx = session["context"]
    is_hard = session.get("is_hard_mode", False)
    ud = core.get_user_data(user_id, hard_mode=is_hard)
    
    enemy_party = ctx["enemy_party"]
    enemy = next((c for c in enemy_party if c["current_hp"] > 0), None)
    player = ud['party'][0]

    if not enemy:
        return _resolve_pve_win(user_id, session, ud)

    sub = ctx.get("sub_state", BATTLE_SUB_MAIN)

    if sub == BATTLE_SUB_MAIN:
        if "逃" in content:
            if session["state"] == STATE_BATTLE_CHALLENGE: return "チャレンジモードからは逃げられないわよ！", []
            session["state"] = STATE_MENU
            session["context"] = {}
            return "逃げ出したわ♪\n\n(メニューに戻りました)", []
            
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

        return "どうするの？", []

    elif sub == BATTLE_SUB_ITEM:
        if "戻る" in content:
            ctx["sub_state"] = BATTLE_SUB_MAIN
            return "どうするの？", []
        sel_item = next((k for k, v in data.ITEMS.items() if v["name"] in content), None)
        if sel_item:
            return use_item_in_battle(user_id, session, sel_item, ud, player, enemy), []
        return "アイテム名を入力してね♪", []

    elif sub == BATTLE_SUB_SWITCH:
        if "戻る" in content:
            ctx["sub_state"] = BATTLE_SUB_MAIN
            return "どうするの？", []
        
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

    return "エラーだわ。", []

# --- PvE ターン処理 (強化版) ---
def _execute_pve_turn(user_id, session, player, enemy, move_id, ud):
    ctx = session["context"]
    ctx["logs"] = [] # ログリセット
    mdata = data.MOVES[move_id]
    
    # 0. 行動不能チェック (麻痺・眠りなど)
    cant_move = False
    sc = player.get("status_condition")
    if sc == "paralysis" and random.random() < 0.25:
        ctx["logs"].append(f"{player['nickname']} は体が痺れて動けないわ！")
        cant_move = True
    elif sc == "sleep":
        if random.random() < 0.33:
            player["status_condition"] = None
            ctx["logs"].append(f"{player['nickname']} は目を覚ましたわ♪")
        else:
            ctx["logs"].append(f"{player['nickname']} はぐうぐう眠っているわね...")
            cant_move = True
    elif sc == "oblivion" and player.get("last_move") == move_id:
        ctx["logs"].append(f"{player['nickname']} は記憶が曖昧でその技が出せないみたい！")
        cant_move = True

    if not cant_move:
        # アビリティ: アグライア (攻撃時加速)
        base_name = data.BASE_CHIMERAS[player["base_id"]]["name"]
        if base_name == "オートミール" and mdata["category"] != "Status":
            player["stat_stages"]["spe"] = min(6, player["stat_stages"]["spe"] + 1)
            ctx["logs"].append("オートミールの速度が上がったわ！")
            
        # 1. ダメージ計算 (タイプ相性・アビリティ込み)
        dmg, type_eff = _calculate_damage(player, enemy, move_id, session)
        if mdata["category"] != "Status":
            enemy["current_hp"] -= dmg
            
            eff_msg = ""
            if type_eff > 1.0: eff_msg = " 効果はばつぐんよ！"
            elif type_eff == 0: eff_msg = " 効果がないみたい..."
            elif type_eff < 1.0: eff_msg = " 効果はいまひとつね..."
            
            ctx["logs"].append(f"{player['nickname']} の {mdata['name']}！{eff_msg} {dmg} ダメージ！")
            
            # タスキチェック
            if core.check_survival_item(enemy, dmg):
                enemy["current_hp"] = 1
                ctx["logs"].append(f"{enemy['nickname']} はきあいのタスキで持ちこたえたわ！")
            
            # アビリティ: キャストリス (反射)
            if data.BASE_CHIMERAS[enemy["base_id"]]["name"] == "チョウチョウケーキ":
                ref = max(1, dmg // 10)
                player["current_hp"] = max(0, player["current_hp"] - ref)
                ctx["logs"].append(f"甘美な誘惑！ {player['nickname']} に {ref} の反射ダメージ！")
                
            # アビリティ: 三月なのか (忘却付与)
            if data.BASE_CHIMERAS[enemy["base_id"]]["name"] == "キャンディーロール":
                 if enemy["battle_state"]["oblivion_cd"] == 0:
                     _apply_status_effect(player, "oblivion", session)
                     enemy["battle_state"]["oblivion_cd"] = 3
        
        else:
            # 変化技の処理
            ctx["logs"].append(f"{player['nickname']} の {mdata['name']}！")
            eff = mdata.get("effect")
            if eff:
                if eff["type"] == "buff":
                    player["stat_stages"][eff["stat"]] = min(6, player["stat_stages"][eff["stat"]] + eff["stage"])
                    ctx["logs"].append(f"{player['nickname']} の能力が上がったわ！")
                elif eff["type"] == "debuff":
                    enemy["stat_stages"][eff["stat"]] = max(-6, enemy["stat_stages"][eff["stat"]] - eff["stage"])
                    ctx["logs"].append(f"{enemy['nickname']} の能力を下げたわ！")
                elif eff["type"] == "status":
                    _apply_status_effect(enemy, eff["status"], session)
                elif eff["type"] == "heal":
                    rec = int(player["stats"]["max_hp"] * eff["percent"])
                    player["current_hp"] = min(player["stats"]["max_hp"], player["current_hp"] + rec)
                    ctx["logs"].append(f"{player['nickname']} は回復したわ♪")

            # アビリティ: ヒアシンシア (イカルン召喚)
            if base_name == "チェリビス":
                ctx["field_effects"]["icarun"]["p1"] = True
                ctx["logs"].append("イカルンが召喚されたわ！ 毎ターン回復してくれるわよ♪")
    
        player["last_move"] = move_id

    # 敵瀕死判定
    if enemy["current_hp"] <= 0:
        return _handle_enemy_faint(user_id, session, ud, enemy)

    # プレイヤー瀕死判定 (反射などで落ちた場合)
    if player["current_hp"] <= 0:
        return _handle_player_faint(user_id, session, ud, player)

    # 敵の反撃
    msg = "\n".join(ctx["logs"]) + "\n"
    msg += _enemy_attack_phase(user_id, session, player, enemy, ud)
    return msg, []

def _enemy_attack_phase(user_id, session, player, enemy, ud):
    ctx = session["context"]
    ctx["logs"] = []
    
    # 0. 敵行動不能チェック
    cant_move = False
    sc = enemy.get("status_condition")
    if sc == "paralysis" and random.random() < 0.25:
        ctx["logs"].append(f"敵の {enemy['nickname']} は痺れて動けないわ！")
        cant_move = True
    elif sc == "sleep":
        if random.random() < 0.33:
            enemy["status_condition"] = None
            ctx["logs"].append(f"敵の {enemy['nickname']} は目を覚ましたわ！")
        else:
            ctx["logs"].append(f"敵の {enemy['nickname']} は眠っているわ...")
            cant_move = True

    if not cant_move:
        # ハードモードAI: ポーション使用
        potions = ctx.get("potions", 0)
        if potions > 0 and enemy["current_hp"] < enemy["stats"]["max_hp"] * 0.3:
            ctx["potions"] -= 1
            heal_amt = int(enemy["stats"]["max_hp"] * 0.5)
            enemy["current_hp"] = min(enemy["stats"]["max_hp"], enemy["current_hp"] + heal_amt)
            ctx["logs"].append(f"敵は『すごいキズぐすり』を使ったわ！ {enemy['nickname']} が回復したわよ！ (残: {enemy['current_hp']})")
        else:
            emove_id = random.choice(enemy["moves"])
            emove = data.MOVES[emove_id]
            
            dmg, type_eff = _calculate_damage(enemy, player, emove_id, session)
            
            if emove["category"] != "Status":
                player["current_hp"] -= dmg
                
                eff_msg = ""
                if type_eff > 1.0: eff_msg = " 効果はばつぐんよ！"
                elif type_eff == 0: eff_msg = " 効果がないみたい..."
                elif type_eff < 1.0: eff_msg = " 効果はいまひとつね..."

                ctx["logs"].append(f"敵の {enemy['nickname']} の {emove['name']}！{eff_msg} {dmg} ダメージ！")
                
                # アビリティ: キャストリス (反射)
                if data.BASE_CHIMERAS[player["base_id"]]["name"] == "チョウチョウケーキ":
                    ref = max(1, dmg // 10)
                    enemy["current_hp"] = max(0, enemy["current_hp"] - ref)
                    ctx["logs"].append(f"甘美な誘惑！ 敵に {ref} の反射ダメージ！")
            else:
                ctx["logs"].append(f"敵の {enemy['nickname']} の {emove['name']}！")
                eff = emove.get("effect")
                if eff and eff["type"] == "status":
                    _apply_status_effect(player, eff["status"], session)
    
    # ターン終了時処理 (イカルン、状態異常ダメ)
    _end_of_turn_effects(session, player, enemy, ud)
    
    core.save_user_data(user_id, ud, hard_mode=session.get("is_hard_mode", False))
    msg = "\n".join(ctx["logs"])
    
    # 瀕死判定
    if player["current_hp"] <= 0:
        return msg + "\n" + _handle_player_faint(user_id, session, ud, player)
    
    if enemy["current_hp"] <= 0:
        return msg + "\n" + _handle_enemy_faint(user_id, session, ud, enemy)
        
    return msg + f"\n(敵HP: {enemy['current_hp']} / 味方HP: {player['current_hp']})"

def _end_of_turn_effects(session, player, enemy, ud):
    ctx = session["context"]
    # イカルン回復
    if ctx["field_effects"]["icarun"]["p1"] and player["current_hp"] > 0:
        rec = int(player["stats"]["max_hp"] * 0.1)
        player["current_hp"] = min(player["stats"]["max_hp"], player["current_hp"] + rec)
        ctx["logs"].append(f"イカルンの光が {player['nickname']} を癒やしてくれたわ♪")

    # 状態異常ダメージ
    for char in [player, enemy]:
        if char["current_hp"] <= 0: continue
        sc = char.get("status_condition")
        if sc == "poison":
            dmg = char["stats"]["max_hp"] // 8
            char["current_hp"] = max(0, char["current_hp"] - dmg)
            ctx["logs"].append(f"{char['nickname']} は毒でダメージを受けたわ！")
        elif sc == "burn":
            dmg = char["stats"]["max_hp"] // 16
            char["current_hp"] = max(0, char["current_hp"] - dmg)
            ctx["logs"].append(f"{char['nickname']} は火傷でダメージを受けたわ！")
        
        if char["battle_state"]["oblivion_cd"] > 0:
            char["battle_state"]["oblivion_cd"] -= 1

def _handle_enemy_faint(user_id, session, ud, enemy):
    enemy["current_hp"] = 0
    # アビリティ: メデイモス (蘇生)
    base_name = data.BASE_CHIMERAS[enemy["base_id"]]["name"]
    if base_name == "ハニーフルーツスープ" and not enemy["battle_state"]["revived"]:
        enemy["current_hp"] = enemy["stats"]["max_hp"] // 2
        enemy["battle_state"]["revived"] = True
        return f"\n相手の {enemy['nickname']} は蘇りの力で復活したわ！"

    msg = f"\n相手の {enemy['nickname']} は倒れたわ！"
    
    # 経験値処理
    xp_mult = 150
    is_hard = session.get("is_hard_mode", False)
    if is_hard: xp_mult = 30
    base_xp = (enemy["level"] * xp_mult) + random.randint(0, enemy["level"] * 10)
    
    for p in ud["party"]:
        if p["current_hp"] > 0:
            p["xp"] += base_xp
            if p["xp"] >= p["next_xp"]:
                msg += "\n" + core.level_up_chimera(p, is_hard_mode=is_hard)
    
    msg += f"\nパーティ全員に {base_xp} の経験値が入ったわよ♪"
    core.save_user_data(user_id, ud, hard_mode=is_hard)
    
    ctx = session["context"]
    next_enemy = next((c for c in ctx["enemy_party"] if c["current_hp"] > 0), None)
    
    if next_enemy:
        _init_chimera_battle_states(session, "p2") # 次の敵の状態初期化
        msg += f"\n相手は **{next_enemy['nickname']}** (Lv.{next_enemy['level']} HP:{next_enemy['current_hp']}) を繰り出してきたわ！"
        return msg, []
    else:
        return _resolve_pve_win(user_id, session, ud)

def _handle_player_faint(user_id, session, ud, player):
    player["current_hp"] = 0
    base_name = data.BASE_CHIMERAS[player["base_id"]]["name"]
    
    # アビリティ: アグライア (バトン)
    if base_name == "オートミール":
        session["context"]["field_effects"]["aglaia_speed"]["p1"] = player["stat_stages"]["spe"]

    msg = f"\n{player['nickname']} は倒れちゃったわ！"
    
    if any(c["current_hp"] > 0 for c in ud["party"]):
        session["context"]["sub_state"] = BATTLE_SUB_FORCE_SWITCH
        msg += "\n次は誰を出す？\n" + _generate_party_list(ud)
    else:
        lost = int(ud["money"] * 0.1)
        ud["money"] -= lost
        core.heal_all_kimeras(ud)
        core.save_user_data(user_id, ud, hard_mode=session.get("is_hard_mode", False))
        
        session["state"] = STATE_MENU
        session["context"] = {}
        msg += f"\n手持ちが全滅しちゃったわね… (所持金 -{lost}G)\n\n(キメラセンターで回復してメニューに戻ったわ♪)"
    
    return msg

def _resolve_pve_win(user_id, session, ud):
    msg = "勝利よ！ 素晴らしいわ♪\n"
    base_money = 1000
    trainer_xp = 500
    
    if session["state"] == STATE_BATTLE_CHALLENGE:
        st = session["context"]["stage"]
        is_hard = session.get("is_hard_mode", False)
        
        trainer_source = data.CHALLENGE_TRAINERS_HARD if is_hard else data.CHALLENGE_TRAINERS
        t_data = trainer_source[st]
        
        win_msg = t_data.get("dialogue_win", "見事だ…")
        msg += f"\n**{t_data['name']}**: 「{win_msg}」\n"
        
        ud["challenge_stage"] = st + 1
        base_money = st * 5000
        trainer_xp = st * 1000
        
        if st == 13:
            reward_item = t_data.get("reward_item")
            if reward_item and reward_item not in ud["items"]:
                ud["items"][reward_item] = 1
                msg += f"\n【重要】『{data.ITEMS[reward_item]['name']}』を手に入れたわ！\n"
            
            ach_key = "kimera_true_master" if is_hard else "kimera_champion"
            if db.unlock_achievement(user_id, ach_key):
                ach_name = data.ACHIEVEMENTS[ach_key]["name_jp"]
                ach_title = data.ACHIEVEMENTS[ach_key]["title_jp"]
                msg += f"\n🏆 実績解除: **【{ach_name}】**\n二つ名獲得: **【{ach_title}】**\n"

    ud["money"] += base_money
    ud["trainer_xp"] += trainer_xp
    
    leveled = False
    while ud["trainer_xp"] >= ud["trainer_level"] * 500:
        ud["trainer_xp"] -= ud["trainer_level"] * 500
        ud["trainer_level"] += 1
        leveled = True
    
    core.save_user_data(user_id, ud, hard_mode=session.get("is_hard_mode", False))
    
    msg += f"賞金 {base_money}G と トレーナーXP {trainer_xp} を獲得したわ！"
    if leveled:
        msg += f"\nトレーナーレベルが {ud['trainer_level']} に上がったわよ♪"
    
    logic.add_affection_xp(user_id, 50)
    msg += "\n(好感度XP +50)"
    
    session["state"] = STATE_MENU
    session["context"] = {}
    
    return f"{msg}\n\n(メニューに戻ったわ。次はどうする？)", []

# --- 共通ヘルパー ---
def _generate_party_list(ud):
    return "\n".join([f"{i+1}. {c['nickname']} ({c['current_hp']}/{c['stats']['max_hp']})" for i, c in enumerate(ud['party'])])

def _try_switch_member(user_id, content, ud, current, allow_cancel):
    try:
        idx = int(content.translate(str.maketrans({chr(0xFF01 + i): chr(0x21 + i) for i in range(94)}))) - 1
        if 0 <= idx < len(ud["party"]):
            target = ud["party"][idx]
            if target["current_hp"] <= 0:
                return {"success": False, "msg": "その子はもう戦えないみたいね……"}
            if target == current and allow_cancel:
                return {"success": False, "msg": "もう出ているわよ？"}
            
            # 先頭と入れ替え
            ud["party"][0], ud["party"][idx] = ud["party"][idx], ud["party"][0]
            
            # アビリティ: アグライア (速度引継ぎ)
            session = KIMERA_SESSIONS[user_id]
            speed_boost = session["context"]["field_effects"]["aglaia_speed"]["p1"]
            if speed_boost > 0:
                target["stat_stages"]["spe"] = min(6, target["stat_stages"]["spe"] + speed_boost)
                session["context"]["field_effects"]["aglaia_speed"]["p1"] = 0
            
            # アビリティ: 丹恒 (バリア)
            if data.BASE_CHIMERAS[target["base_id"]]["name"] == "温厚な竜":
                target["battle_state"]["barrier_hp"] = int(target["stats"]["def"] * 0.6)

            core.save_user_data(user_id, ud, hard_mode=session.get("is_hard_mode", False))
            return {"success": True, "target": target}
    except:
        pass
    return {"success": False, "msg": "番号で指定してね♪"}

# --- アイテム使用 (戦闘中) ---
def use_item_in_battle(user_id, session, item_key, ud, player, enemy):
    item = data.ITEMS[item_key]
    is_hard = session.get("is_hard_mode", False)
    
    if item["effect_type"] == "capture":
        if session["state"] != STATE_BATTLE_WILD:
            return "人のキメラは捕まえちゃダメよ！"
        
        if ud["items"].get(item_key, 0) <= 0:
            return "持っていないわね。"
        
        ud["items"][item_key] -= 1
        if ud["items"][item_key] <= 0:
            del ud["items"][item_key]
        
        rarity_mod = 1.0 - (enemy.get("rarity", 1) * 0.1)
        rate = ((1 - (enemy["current_hp"]/enemy["stats"]["max_hp"])) * 0.8 + 0.2) * item["value"] * rarity_mod
        
        if enemy.get("status_condition"): rate *= 1.5
        if enemy.get("status_condition") == "submission": rate *= 2.0 # 屈服状態ボーナス

        if random.random() < rate:
            enemy["current_hp"] = enemy["stats"]["max_hp"]
            if len(ud["party"]) < 3:
                ud["party"].append(enemy)
            else:
                ud["box"].append(enemy)
            
            core.register_dex(ud, enemy["base_id"], caught=True)
            core.save_user_data(user_id, ud, hard_mode=is_hard)
            logic.add_affection_xp(user_id, 50)
            
            session["state"] = STATE_MENU
            session["context"] = {}
            
            return f"やった！ {enemy['nickname']} を捕まえたわよ♪\n(好感度XP +50)\n\n(メニューに戻りました)", []
        else:
            core.save_user_data(user_id, ud, hard_mode=is_hard)
            msg = "ボールから抜け出されちゃった！\n" + _enemy_attack_phase(user_id, session, player, enemy, ud)
            return msg

    elif item["effect_type"] == "heal":
        if ud["items"].get(item_key, 0) <= 0:
            return "持っていないわね。"
        ud["items"][item_key] -= 1
        if ud["items"][item_key] <= 0:
            del ud["items"][item_key]
        
        player["current_hp"] = min(player["stats"]["max_hp"], player["current_hp"] + item["value"])
        core.save_user_data(user_id, ud, hard_mode=is_hard)
        return f"回復したわ♪\n" + _enemy_attack_phase(user_id, session, player, enemy, ud)

    return "今は使えないわね。"

# --- PvP ---
def handle_pvp_lobby(user_id, content):
    m = re.search(r"<@!?(\d+)>", content)
    if m:
        target_id = int(m.group(1))
        if target_id == user_id:
            return "自分とは戦えないわよ？", []
        PVP_CHALLENGES[target_id] = user_id
        return f"<@{target_id}> に挑戦状を送ったわよ♪", [(target_id, f"**{user_id}** から挑戦状が届いたわ！")]
    if "キャンセル" in content:
        end_session(user_id)
        return "キャンセルしたわ。", []
    return "相手を指名してね♪", []

def _initiate_pvp_battle(p1, p2):
    if p2 in PVP_CHALLENGES: del PVP_CHALLENGES[p2]
    battle_id = f"pvp_{p1}_{p2}"
    PVP_BATTLES[battle_id] = {"p1": p1, "p2": p2, "actions": {}, "turn": 1}
    for uid in [p1, p2]:
        if uid not in KIMERA_SESSIONS: start_session(uid)
        sess = KIMERA_SESSIONS[uid]
        sess["state"] = STATE_BATTLE_PVP
        sess["context"] = {"battle_id": battle_id, "sub_state": BATTLE_SUB_MAIN}
    ud1 = core.get_user_data(p1, hard_mode=KIMERA_SESSIONS[p1].get("is_hard_mode", False))
    ud2 = core.get_user_data(p2, hard_mode=KIMERA_SESSIONS[p2].get("is_hard_mode", False))
    c1 = ud1["party"][0]
    c2 = ud2["party"][0]
    msg1 = f"対戦開始！ 相手は **{c2['nickname']}** (Lv.{c2['level']}) よ！\nどうする？ 『戦う』 『降参』"
    msg2 = f"対戦開始！ 相手は **{c1['nickname']}** (Lv.{c1['level']}) よ！\nどうする？ 『戦う』 『降参』"
    return msg2, [(p1, msg1)]

def handle_pvp_action(user_id, content):
    session = KIMERA_SESSIONS[user_id]
    ctx = session["context"]
    battle = PVP_BATTLES.get(ctx["battle_id"])
    if not battle:
        session["state"] = STATE_MENU
        return "対戦はもう終わっているわ。", []
    
    is_hard = session.get("is_hard_mode", False)
    ud = core.get_user_data(user_id, hard_mode=is_hard)
    player_chimera = ud['party'][0]
    sub = ctx.get("sub_state", BATTLE_SUB_MAIN)

    if sub == BATTLE_SUB_WAIT:
        return "相手の入力を待っているわ…少し待ってね♪", []

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

        return "コマンドを選んでね。『戦う』『降参』などよ♪", []
    return "...", []

def _check_pvp_turn_ready(battle):
    if battle["p1"] in battle["actions"] and battle["p2"] in battle["actions"]:
        return _resolve_pvp_turn(battle)
    else:
        return "入力を受け付けたわ。相手を待っているわね♪", []

def _resolve_pvp_turn(battle):
    # PvPロジック（簡易版） - 本格的なアビリティ対応はPvE側と同様の拡張が必要だが、
    # ユーザー要望に従い「既存コードの延長」で最低限動く状態を維持
    p1, p2 = battle["p1"], battle["p2"]
    act1, act2 = battle["actions"][p1], battle["actions"][p2]
    ud1 = core.get_user_data(p1); ud2 = core.get_user_data(p2)
    c1 = ud1["party"][0]; c2 = ud2["party"][0]
    
    if c1["stats"]["spe"] >= c2["stats"]["spe"]:
        order = [(p1, c1, act1, p2, c2), (p2, c2, act2, p1, c1)]
    else:
        order = [(p2, c2, act2, p1, c1), (p1, c1, act1, p2, c2)]
            
    logs = []
    for actor_id, actor_c, act, target_id, target_c in order:
        if actor_c["current_hp"] <= 0: continue
        if act["type"] == "move":
            mid = act["value"]
            mdata = data.MOVES[mid]
            # 簡易計算 (PvPはアビリティ非対応で一旦実装)
            dmg = int(mdata["power"] * (actor_c["stats"]["atk"] / target_c["stats"]["def"]) * 0.4)
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
        _end_pvp(battle)
        msg = f"{full_log}\n\n相打ちね！ 引き分けよ！"
        return "", [(p1, msg), (p2, msg)]

    if c1["current_hp"] <= 0: loser = p1
    elif c2["current_hp"] <= 0: loser = p2
    
    if loser:
        _end_pvp(battle)
        winner = p2 if loser == p1 else p1
        msg = f"{full_log}\n\n勝負あり！ <@{winner}> の勝利よ♪"
        KIMERA_SESSIONS[p1]["state"] = STATE_MENU; KIMERA_SESSIONS[p2]["state"] = STATE_MENU
        KIMERA_SESSIONS[p1]["context"]["sub_state"] = BATTLE_SUB_MAIN
        KIMERA_SESSIONS[p2]["context"]["sub_state"] = BATTLE_SUB_MAIN
        return "", [(p1, msg), (p2, msg)]

    KIMERA_SESSIONS[p1]["context"]["sub_state"] = BATTLE_SUB_MAIN
    KIMERA_SESSIONS[p2]["context"]["sub_state"] = BATTLE_SUB_MAIN
    msg_next = f"{full_log}\n\n次のターンよ！ どうする？"
    return "", [(p1, msg_next), (p2, msg_next)]

def _resolve_pvp_end(battle, loser_id):
    p1, p2 = battle["p1"], battle["p2"]
    winner_id = p2 if loser_id == p1 else p1
    _end_pvp(battle)
    msg = f"<@{loser_id}> が降参したわ。\n<@{winner_id}> の勝利よ♪"
    KIMERA_SESSIONS[p1]["state"] = STATE_MENU; KIMERA_SESSIONS[p2]["state"] = STATE_MENU
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
            return (
                "あら、キメラたちと遊びたいの？\n"
                "**『バトル』『編成』『装備』『詳細』『ショップ』『回復』『図鑑』『ボックス』**\n"
                "何をしたいかしら？"
            ), []
        return None
    
    if content in ["終了", "やめる", "もう遊び疲れたよ"]:
        end_session(user_id)
        return "また遊びましょ♪", []

    st = session["state"]
    if st == STATE_MENU: return handle_menu(user_id, content)
    elif st == STATE_SHOP: return handle_shop(user_id, content)
    elif st == STATE_BOX: return handle_box_menu(user_id, content)
    elif st == STATE_EQUIP: return handle_equip_menu(user_id, content)
    elif st == STATE_BATTLE_SELECT: return handle_battle_select(user_id, content)
    elif st == STATE_BATTLE_PVP_LOBBY: return handle_pvp_lobby(user_id, content)
    elif st in [STATE_BATTLE_WILD, STATE_BATTLE_TRAINER, STATE_BATTLE_CHALLENGE]: return handle_battle_action(user_id, content)
    elif st == STATE_BATTLE_PVP: return handle_pvp_action(user_id, content)
    
    return None