import random
import re
import kimera_core as core
import database as db
import logic
import kimera_data as data

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
    # ユーザーがハードモード中かどうかは、セッション変数で管理する
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

# --- メニュー ---
def handle_menu(user_id, content):
    session = KIMERA_SESSIONS[user_id]
    is_hard = session.get("is_hard_mode", False)
    ud = core.get_user_data(user_id, hard_mode=is_hard)

    # --- ★デバッグ機能 ---
    if content == "デバッグ解放":
        # ノーマルデータのアイテムに証を追加
        normal_ud = core.get_user_data(user_id, hard_mode=False)
        normal_ud["items"]["story_page_2"] = 1
        core.save_user_data(user_id, normal_ud, hard_mode=False)
        return "【デバッグ】ノーマルデータに『story_page_2』を付与したわ。", []
    
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
            return f"【デバッグ】実績『キメラチャンピオン』を {res} にしたわ。", []
        except:
            return "エラー。", []

    # --- モード切替 ---
    if "真なるキメラマスターロード" in content:
        if is_hard:
            return "既に修羅の道（ハードモード）にいるわ。心して挑みなさい。", []
        
        # ノーマルデータのクリア証を確認
        normal_ud = core.get_user_data(user_id, hard_mode=False)
        if "story_page_2" in normal_ud["items"]:
            session["is_hard_mode"] = True
            # ハードデータをロード（なければ作成）
            core.get_user_data(user_id, hard_mode=True)
            return (
                "【警告: 真なるキメラマスターロード解放】\n\n"
                "世界が反転し、黄金裔たちの真の力が解放されたわ……。\n"
                "これより『ハードモード』のセーブデータに切り替わるわ。\n"
                "敵はレベル100を超え、アイテムや特性をフル活用してくる。\n"
                "準備はいい？ 死にゲーの始まりよ。", []
            )
        else:
            return "まだその扉を開く資格（ノーマルモードクリアの証）を持っていないみたい。", []

    if "ノーマルに戻る" in content:
        if is_hard:
            session["is_hard_mode"] = False
            return "平和な世界（ノーマルモード）のデータに戻したわ。", []
        return "今はノーマルモードよ。", []

    # --- バトル選択画面へ（ショートカット含む） ---
    if "バトル" in content or "チャレンジ" in content:
        session["state"] = STATE_BATTLE_SELECT
        # 画面切り替え時に再度データをロードして最新状態を確認
        ud = core.get_user_data(user_id, hard_mode=is_hard)
        
        mode_text = "【真・キメラマスターロード】" if is_hard else "チャレンジモード"
        msg = (
            "どこに行く？\n"
            "1. **確保ゾーン** (野生捕獲)\n"
            "2. **レベル上げゾーン** (CPU戦)\n"
            f"3. **{mode_text}** (黄金裔13人抜き)\n"
            "4. **対戦ゾーン** (PvP)"
        )
        
        # ヒント表示 (ノーマルモードかつクリア証持ちの場合)
        if not is_hard:
            normal_ud = core.get_user_data(user_id, hard_mode=False)
            if "story_page_2" in normal_ud["items"]:
                msg += "\n\n★『真なるキメラマスターロード』と言えば、裏世界へ行けるわ。"
        
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
            msg += "★ 現在『ハードモード』データ参照中 ★\n"
        
        if not ud['party']:
            return msg + "キメラなし。", []
        
        chimera = ud['party'][0]
        return f"{msg}【先頭】\n{core.get_chimera_display_stats(chimera)}", []

    if "ショップ" in content:
        session["state"] = STATE_SHOP
        tlv = ud["trainer_level"]
        lines = []
        for k, v in core.ITEMS.items():
            if v["price"] > 0 and v.get("unlock_rank", 1) <= tlv:
                lines.append(f"・**{v['name']}**: {v['price']}G")
        return f"【ショップ】 (所持金: {ud['money']}G / Lv.{tlv})\n" + "\n".join(lines) + "\n\n『〇〇を買う』 / 『戻る』", []

    if "回復" in content:
        core.heal_all_kimeras(ud)
        core.save_user_data(user_id, ud, hard_mode=is_hard)
        return "キメラセンターで手持ちとボックスの子を全回復したわ♪", []

    # --- 図鑑機能 (強化版) ---
    if "図鑑" in content:
        # 個別検索: "図鑑 ウルフパピー" のように入力された場合
        m_search = re.search(r"図鑑\s+(.+)", content)
        if m_search:
            target_name = m_search.group(1).strip()
            found_key = None
            for k, v in core.BASE_CHIMERAS.items():
                if v["name"] == target_name:
                    found_key = k
                    break
            
            if not found_key:
                return "その名前のキメラはデータにないわ。", []

            status = ud["dex"].get(found_key)
            if not status:
                return "そのキメラはまだ発見していないわ。", []
            
            base = core.BASE_CHIMERAS[found_key]
            
            # --- 発見のみの場合 ---
            if status == "seen":
                return (
                    f"━━━━━━━━━━━━━━━\n"
                    f"📖 **No.{found_key} {base['name']}**\n"
                    f"━━━━━━━━━━━━━━━\n"
                    f"【状態】 目撃のみ (詳細は捕獲後に解放)\n"
                    f"【分類】 {base['type']}タイプ\n"
                    f"━━━━━━━━━━━━━━━"
                ), []
            
            # --- 捕獲済み (詳細表示) ---
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

        # --- 一覧表示 (デフォルト) ---
        total = len(core.BASE_CHIMERAS)
        caught = sum(1 for v in ud["dex"].values() if v == "caught")
        seen = len(ud["dex"])
        
        lines = [f"【キメラ図鑑】 捕獲: {caught}/{total} / 発見: {seen}/{total}"]
        sorted_keys = sorted(core.BASE_CHIMERAS.keys())
        
        for k in sorted_keys:
            base = core.BASE_CHIMERAS[k]
            status = ud["dex"].get(k)
            
            if status == "caught":
                mark = "★" # 捕獲済み
                display_name = base['name']
            elif status == "seen":
                mark = "○" # 発見済み
                display_name = base['name']
            else:
                mark = "・" # 未発見
                display_name = "？？？"
            
            # 捕獲済みならレア度を表示
            rarity_disp = f"({'★'*base['rarity']})" if status == "caught" else ""
            lines.append(f"{mark} {display_name} {rarity_disp}")
        
        lines.append("\n『図鑑 ウルフパピー』のように名前を入れると詳細が見れるわよ♪")
        return "\n".join(lines), []

    if "アイテム" in content:
        items_txt = ", ".join([f"{core.ITEMS[k]['name']}x{v}" for k, v in ud['items'].items()])
        return f"所持: {items_txt}\n(『けいけんアメSを使う』と言ってね)", []
        
    m = re.match(r"(.+)を使う", content)
    if m:
        item_name = m.group(1)
        item_key = None
        for k, v in core.ITEMS.items():
            if v["name"] == item_name:
                item_key = k
                break
        if item_key:
            if not ud["party"]:
                return "手持ちがいないわ。", []
            res = core.apply_item_effect_logic(ud, item_key, ud["party"][0])
            core.save_user_data(user_id, ud, hard_mode=is_hard)
            return res, []

    # 通常メニュー表示
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
        "何をしたいかしら？"
    ), []

# --- 装備操作 ---
def _get_equip_menu_text(user_id):
    session = KIMERA_SESSIONS[user_id]
    ud = core.get_user_data(user_id, hard_mode=session.get("is_hard_mode", False))
    
    msg = "【装備管理】\n"
    for i, c in enumerate(ud["party"]):
        item_name = core.ITEMS[c["held_item"]]["name"] if c["held_item"] else "なし"
        msg += f"{i+1}. {c['nickname']}: {item_name}\n"
    
    equipable = []
    for k, v in ud["items"].items():
        idata = core.ITEMS.get(k)
        if idata and idata["effect_type"].startswith("equip_"):
            equipable.append(f"{idata['name']}")
            
    msg += "\n【持っている装備品】\n" + (", ".join(equipable) if equipable else "(なし)")
    msg += "\n\n『1にハチマキを持たせる』\n『2を外す』\n『戻る』"
    return msg

def handle_equip_menu(user_id, content):
    session = KIMERA_SESSIONS[user_id]
    is_hard = session.get("is_hard_mode", False)
    ud = core.get_user_data(user_id, hard_mode=is_hard)
    
    if "戻る" in content:
        session["state"] = STATE_MENU
        return "メニューに戻るわ。", []

    m = re.search(r"(\d+)に(.+?)を持たせる", content) or re.search(r"(\d+)に(.+?)", content)
    if m:
        idx = int(m.group(1)) - 1
        item_name = m.group(2).strip()
        
        item_key = None
        for k, v in core.ITEMS.items():
            if v["name"] == item_name:
                item_key = k
                break
        
        if item_key:
            res = core.equip_item_logic(ud, idx, item_key)
            core.save_user_data(user_id, ud, hard_mode=is_hard)
            return res + "\n" + _get_equip_menu_text(user_id), []
        else:
            return "そのアイテムは見つからないわ。", []

    m = re.search(r"(\d+)を外す", content)
    if m:
        idx = int(m.group(1)) - 1
        res = core.unequip_item_logic(ud, idx)
        core.save_user_data(user_id, ud, hard_mode=is_hard)
        return res + "\n" + _get_equip_menu_text(user_id), []

    return "『1にハチマキを持たせる』のように言ってね。", []

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
        return "メニューに戻るわ。", []

    m_swap = re.search(r"[Pp](\d+).*?[Bb](\d+)", content)
    m_to_box = re.search(r"[Pp](\d+).*?預ける", content)
    m_to_party = re.search(r"[Bb](\d+).*?入れる", content)

    if m_swap:
        pidx = int(m_swap.group(1))-1
        bidx = int(m_swap.group(2))-1
        if core.swap_party_box(ud, pidx, bidx):
            core.save_user_data(user_id, ud, hard_mode=is_hard)
            return "交代したわ。\n" + _get_box_menu_text(user_id), []
        return "指定が間違ってるみたい。", []

    elif m_to_box:
        pidx = int(m_to_box.group(1))-1
        if core.move_party_to_box(ud, pidx):
            core.save_user_data(user_id, ud, hard_mode=is_hard)
            return "ボックスに預けたわ。\n" + _get_box_menu_text(user_id), []
        return "最後の1体は預けられないわ。", []

    elif m_to_party:
        bidx = int(m_to_party.group(1))-1
        if core.move_box_to_party(ud, bidx):
            core.save_user_data(user_id, ud, hard_mode=is_hard)
            return "手持ちに入れたわ。\n" + _get_box_menu_text(user_id), []
        return "手持ちがいっぱいよ（最大3体）。", []

    return "『P1とB1を交代』のように言ってね。", []

# --- ショップ ---
def handle_shop(user_id, content):
    session = KIMERA_SESSIONS[user_id]
    is_hard = session.get("is_hard_mode", False)
    ud = core.get_user_data(user_id, hard_mode=is_hard)
    
    if "戻る" in content:
        session["state"] = STATE_MENU
        return "メニューに戻るわ。", []
    
    target_key = None
    for k, v in core.ITEMS.items():
        if v["name"] in content:
            target_key = k
            break
    
    if target_key:
        item = core.ITEMS[target_key]
        if item.get("unlock_rank", 1) > ud["trainer_level"]:
            return "レベル不足で買えないわ。", []
        if ud["money"] >= item["price"]:
            ud["money"] -= item["price"]
            ud["items"][target_key] = ud["items"].get(target_key, 0) + 1
            core.save_user_data(user_id, ud, hard_mode=is_hard)
            return f"**{item['name']}** を購入したわ。(残: {ud['money']}G)", []
        else:
            return "お金が足りないわ。", []
    return "商品名を入力してね。", []

# --- バトル選択 ---
def handle_battle_select(user_id, content):
    session = KIMERA_SESSIONS[user_id]
    is_hard = session.get("is_hard_mode", False)
    ud = core.get_user_data(user_id, hard_mode=is_hard)
    tlv = ud["trainer_level"]

    if "確保" in content or "1" in content:
        rand = random.randint(1, 100)
        target_rarity = 1
        if rand > 98: target_rarity = 6
        elif rand > 90: target_rarity = 2
        elif rand > 60: target_rarity = 1
        else: target_rarity = 1 
        
        candidates = [k for k, v in core.BASE_CHIMERAS.items() if v.get("rarity", 1) == target_rarity]
        if not candidates: candidates = [k for k, v in core.BASE_CHIMERAS.items() if v.get("rarity", 1) == 1]
        
        wild_base = random.choice(candidates)
        w_lv = max(1, tlv + random.randint(-1, 3))
        wild = core.create_chimera_instance(wild_base, level=w_lv)
        
        session["state"] = STATE_BATTLE_WILD
        session["context"] = {
            "enemy_party": [wild],
            "enemy_name": "野生のキメラ",
            "sub_state": BATTLE_SUB_MAIN
        }
        core.register_dex(ud, wild["base_id"], caught=False)
        core.save_user_data(user_id, ud, hard_mode=is_hard)
        
        rarity_star = "★" * wild.get("rarity", 1)
        return f"野生の **{wild['nickname']}** (Lv.{wild['level']}) {rarity_star} が飛び出してきた！\n『戦う』『道具』『入れ替え』『逃げる』", []

    if "レベル上げ" in content or "2" in content:
        cpu_base = random.choice(list(core.BASE_CHIMERAS.keys()))
        c_lv = max(5, tlv + random.randint(0, 5))
        cpu_c = core.create_chimera_instance(cpu_base, level=c_lv)
        session["state"] = STATE_BATTLE_TRAINER
        session["context"] = {
            "enemy_party": [cpu_c],
            "enemy_name": "黄金裔の幻影",
            "sub_state": BATTLE_SUB_MAIN
        }
        core.register_dex(ud, cpu_c["base_id"], caught=False)
        core.save_user_data(user_id, ud, hard_mode=is_hard)
        return f"黄金裔の幻影が現れた！ **{cpu_c['nickname']}** (Lv.{cpu_c['level']} HP:{cpu_c['current_hp']}) を繰り出してきた！", []

    if "チャレンジ" in content or "3" in content:
        stage = ud.get("challenge_stage", 1)
        
        # ★修正: ステージが13を超えている（クリア済み）場合、1に戻して周回プレイさせる
        if stage > 13:
            stage = 1
            ud["challenge_stage"] = 1
            core.save_user_data(user_id, ud, hard_mode=is_hard)
        
        is_hard = ud.get("is_hard_mode", False)
        trainer_source = core.CHALLENGE_TRAINERS_HARD if is_hard else core.CHALLENGE_TRAINERS
        
        # 該当ステージのデータ取得
        t_data = trainer_source.get(stage)
        if not t_data: return "準備中よ。", []
        
        enemy_party = []
        for p in t_data["party"]:
            c = core.create_chimera_instance(p["base_id"], p["level"], held_item=p.get("item"))
            enemy_party.append(c)
            core.register_dex(ud, c["base_id"], caught=False)
        
        core.save_user_data(user_id, ud, hard_mode=is_hard)
        
        session["state"] = STATE_BATTLE_CHALLENGE
        session["context"] = {
            "enemy_party": enemy_party,
            "enemy_name": t_data["name"],
            "stage": stage,
            "sub_state": BATTLE_SUB_MAIN,
            "potions": t_data.get("potions", 0) # ハードモード用
        }
        
        start_msg = t_data.get("dialogue_start", "勝負よ！")
        first = enemy_party[0]
        return (
            f"【チャレンジモード Stage {stage}】\n"
            f"**{t_data['name']}**: 「{start_msg}」\n"
            f"相手は **{first['nickname']}** (Lv.{first['level']} HP:{first['current_hp']}) を繰り出してきた！"
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
            if session["state"] == STATE_BATTLE_CHALLENGE: return "チャレンジモードからは逃げられないわ！", []
            end_session(user_id)
            return "逃げ出したわ。", []
        if "道具" in content:
            ctx["sub_state"] = BATTLE_SUB_ITEM
            items = [f"{core.ITEMS[k]['name']}x{v}" for k, v in ud['items'].items()]
            return f"道具: {', '.join(items)}\n(戻るなら『戻る』)", []
        if "入れ替え" in content:
            ctx["sub_state"] = BATTLE_SUB_SWITCH
            return "誰と入れ替える？(番号)\n" + _generate_party_list(ud), []
        if "戦" in content:
            moves = [core.MOVES[m]['name'] for m in player["moves"]]
            return f"技: {', '.join(moves)}", []

        sel_move = None
        for m in player["moves"]:
            if core.MOVES[m]["name"] in content: sel_move = m
        if sel_move:
            return _execute_pve_turn(user_id, session, player, enemy, sel_move, ud)

        return "どうする？", []

    elif sub == BATTLE_SUB_ITEM:
        if "戻る" in content:
            ctx["sub_state"] = BATTLE_SUB_MAIN
            return "どうする？", []
        sel_item = None
        for k, v in core.ITEMS.items():
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
    mdata = core.MOVES[move_id]
    dmg = int(mdata["power"] * (player["stats"]["atk"] / enemy["stats"]["def"]) * 0.4 * random.uniform(0.85, 1.0))
    if dmg < 1: dmg = 1
    
    # 半減の実
    if core.check_resist_berry(enemy, mdata["type"]):
        dmg = int(dmg * 0.5)
        enemy["held_item"] = None
    
    enemy["current_hp"] -= dmg
    
    # タスキチェック
    if core.check_survival_item(enemy, dmg):
        enemy["current_hp"] = 1
        
    core.save_user_data(user_id, ud, hard_mode=session.get("is_hard_mode", False))
    msg = f"{player['nickname']} の {mdata['name']}！ {dmg} ダメージ！ (敵HP: {max(0, enemy['current_hp'])})"
    
    if enemy["current_hp"] <= 0:
        enemy["current_hp"] = 0
        msg += f"\n相手の {enemy['nickname']} は倒れた！"
        
        base_xp = (enemy["level"] * 150) + random.randint(0, enemy["level"] * 50)
        for p in ud["party"]:
            if p["current_hp"] > 0:
                p["xp"] += base_xp
                if p["xp"] >= p["next_xp"]:
                    msg += "\n" + core.level_up_chimera(p, is_hard_mode=session.get("is_hard_mode", False))
        
        msg += f"\nパーティ全員に {base_xp} の経験値が入ったわ！"
        core.save_user_data(user_id, ud, hard_mode=session.get("is_hard_mode", False))
        
        ctx = session["context"]
        next_enemy = next((c for c in ctx["enemy_party"] if c["current_hp"] > 0), None)
        
        if next_enemy:
            msg += f"\n相手は **{next_enemy['nickname']}** (Lv.{next_enemy['level']} HP:{next_enemy['current_hp']}) を繰り出した！"
            return msg, []
        else:
            return _resolve_pve_win(user_id, session, ud)

    msg += "\n" + _enemy_attack_phase(user_id, session, player, enemy, ud)
    return msg, []

def _enemy_attack_phase(user_id, session, player, enemy, ud):
    # ハードモードAI: ポーション使用
    ctx = session["context"]
    potions = ctx.get("potions", 0)
    if potions > 0 and enemy["current_hp"] < enemy["stats"]["max_hp"] * 0.3:
        ctx["potions"] -= 1
        heal_amt = int(enemy["stats"]["max_hp"] * 0.5)
        enemy["current_hp"] = min(enemy["stats"]["max_hp"], enemy["current_hp"] + heal_amt)
        return f"敵は『すごいキズぐすり』を使った！ {enemy['nickname']} が回復した！ (残: {enemy['current_hp']})"

    emove = core.MOVES[random.choice(enemy["moves"])]
    dmg = int(emove["power"] * (enemy["stats"]["atk"] / player["stats"]["def"]) * 0.4 * random.uniform(0.85, 1.0))
    if dmg < 1: dmg = 1
    
    player["current_hp"] -= dmg
    msg = f"敵の {enemy['nickname']} の {emove['name']}！ {dmg} ダメージ！ (残HP: {player['current_hp']})"
    
    if player["current_hp"] <= 0:
        player["current_hp"] = 0
        core.save_user_data(user_id, ud, hard_mode=session.get("is_hard_mode", False))
        msg += f"\n{player['nickname']} は倒れた！"
        
        if any(c["current_hp"] > 0 for c in ud["party"]):
            session["context"]["sub_state"] = BATTLE_SUB_FORCE_SWITCH
            msg += "\n次は誰を出す？\n" + _generate_party_list(ud)
        else:
            lost = int(ud["money"] * 0.1)
            ud["money"] -= lost
            core.heal_all_kimeras(ud)
            core.save_user_data(user_id, ud, hard_mode=session.get("is_hard_mode", False))
            end_session(user_id)
            msg += f"\n手持ちが全滅したわ… (所持金 -{lost}G)"
    else:
        # 食べ残し
        if player.get("held_item") == "leftovers":
            heal = int(player["stats"]["max_hp"] / 16)
            if heal < 1: heal = 1
            if player["current_hp"] < player["stats"]["max_hp"]:
                player["current_hp"] = min(player["stats"]["max_hp"], player["current_hp"] + heal)
                msg += f"\nたべのこしで少し回復した。({player['current_hp']})"
        core.save_user_data(user_id, ud, hard_mode=session.get("is_hard_mode", False))
        
    return msg

def _resolve_pve_win(user_id, session, ud):
    msg = "勝利よ！\n"
    base_money = 1000
    trainer_xp = 500
    
    if session["state"] == STATE_BATTLE_CHALLENGE:
        st = session["context"]["stage"]
        is_hard = session.get("is_hard_mode", False)
        
        trainer_source = core.CHALLENGE_TRAINERS_HARD if is_hard else core.CHALLENGE_TRAINERS
        t_data = trainer_source[st]
        
        msg += f"\n**{t_data['name']}**: 「{t_data.get('dialogue_win', '見事だ…')}」\n"
        ud["challenge_stage"] = st + 1
        base_money = st * 5000
        trainer_xp = st * 1000
        
        if st == 13:
            reward_item = t_data.get("reward_item")
            if reward_item and reward_item not in ud["items"]:
                ud["items"][reward_item] = 1
                msg += f"\n【重要】『{core.ITEMS[reward_item]['name']}』を手に入れたわ！\n"
            
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
    
    msg += f"賞金 {base_money}G と トレーナーXP {trainer_xp} を獲得！"
    if leveled:
        msg += f"\nトレーナーレベルが {ud['trainer_level']} に上がったわ！"
    
    logic.add_affection_xp(user_id, 50)
    msg += "\n(好感度XP +50)"
    
    end_session(user_id)
    return f"{msg}\nメニューに戻るわね。", []

# --- 共通ヘルパー ---
def _generate_party_list(ud):
    return "\n".join([f"{i+1}. {c['nickname']} ({c['current_hp']}/{c['stats']['max_hp']})" for i, c in enumerate(ud['party'])])

def _try_switch_member(user_id, content, ud, current, allow_cancel):
    try:
        idx = int(content.translate(str.maketrans({chr(0xFF01 + i): chr(0x21 + i) for i in range(94)}))) - 1
        if 0 <= idx < len(ud["party"]):
            target = ud["party"][idx]
            if target["current_hp"] <= 0:
                return {"success": False, "msg": "その子は瀕死よ。"}
            if target == current and allow_cancel:
                return {"success": False, "msg": "もう出ているわ。"}
            
            # 先頭と入れ替え
            ud["party"][0], ud["party"][idx] = ud["party"][idx], ud["party"][0]
            core.save_user_data(user_id, ud, hard_mode=get_session(user_id).get("is_hard_mode", False))
            return {"success": True, "target": target}
    except:
        pass
    return {"success": False, "msg": "番号で指定してね。"}

# --- アイテム使用 (戦闘中) ---
def use_item_in_battle(user_id, session, item_key, ud, player, enemy):
    item = core.ITEMS[item_key]
    is_hard = session.get("is_hard_mode", False)
    
    if item["effect_type"] == "capture":
        if session["state"] != STATE_BATTLE_WILD:
            return "人のキメラは捕まえられないわ！"
        
        if ud["items"].get(item_key, 0) <= 0:
            return "持っていないわ。"
        
        ud["items"][item_key] -= 1
        if ud["items"][item_key] <= 0:
            del ud["items"][item_key]
        
        rarity_mod = 1.0 - (enemy.get("rarity", 1) * 0.1)
        rate = ((1 - (enemy["current_hp"]/enemy["stats"]["max_hp"])) * 0.8 + 0.2) * item["value"] * rarity_mod
        
        if random.random() < rate:
            enemy["current_hp"] = enemy["stats"]["max_hp"]
            if len(ud["party"]) < 3:
                ud["party"].append(enemy)
            else:
                ud["box"].append(enemy)
            
            core.register_dex(ud, enemy["base_id"], caught=True)
            core.save_user_data(user_id, ud, hard_mode=is_hard)
            logic.add_affection_xp(user_id, 50)
            end_session(user_id)
            return f"やった！ {enemy['nickname']} を捕まえたわ！\n(好感度XP +50)", []
        else:
            core.save_user_data(user_id, ud, hard_mode=is_hard)
            return "ボールから抜け出された！\n" + _enemy_attack_phase(user_id, session, player, enemy, ud)

    elif item["effect_type"] == "heal":
        if ud["items"].get(item_key, 0) <= 0:
            return "持っていないわ。"
        ud["items"][item_key] -= 1
        if ud["items"][item_key] <= 0:
            del ud["items"][item_key]
        
        player["current_hp"] = min(player["stats"]["max_hp"], player["current_hp"] + item["value"])
        core.save_user_data(user_id, ud, hard_mode=is_hard)
        return f"回復したわ！\n" + _enemy_attack_phase(user_id, session, player, enemy, ud)

    return "今は使えないわ。"

# --- PvP ---
def handle_pvp_lobby(user_id, content):
    m = re.search(r"<@!?(\d+)>", content)
    if m:
        target_id = int(m.group(1))
        if target_id == user_id:
            return "自分とは戦えないわよ。", []
        PVP_CHALLENGES[target_id] = user_id
        return f"<@{target_id}> に挑戦状を送ったわ！", [(target_id, f"**{user_id}** から挑戦状！")]
    if "キャンセル" in content:
        end_session(user_id)
        return "キャンセルしたわ。", []
    return "相手を指名してね。", []

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
        return "終了しているわ。", []
    
    is_hard = session.get("is_hard_mode", False)
    ud = core.get_user_data(user_id, hard_mode=is_hard)
    player_chimera = ud['party'][0]
    sub = ctx.get("sub_state", BATTLE_SUB_MAIN)

    if sub == BATTLE_SUB_WAIT:
        return "相手の入力を待っているわ…少し待ってね。", []

    if sub == BATTLE_SUB_MAIN:
        if "降参" in content or "逃" in content:
            return _resolve_pvp_end(battle, loser_id=user_id)

        if "戦" in content:
            moves_txt = " / ".join([f"{core.MOVES[m]['name']}" for m in player_chimera["moves"]])
            return f"どの技を使う？\n[{moves_txt}]", []

        selected_move = None
        for mid in player_chimera["moves"]:
            if core.MOVES[mid]["name"] in content:
                selected_move = mid
                break
        
        if selected_move:
            battle["actions"][user_id] = {"type": "move", "value": selected_move}
            ctx["sub_state"] = BATTLE_SUB_WAIT
            return _check_pvp_turn_ready(battle)

        return "コマンドを選んで。『戦う』『降参』などよ。", []
    return "...", []

def _check_pvp_turn_ready(battle):
    if battle["p1"] in battle["actions"] and battle["p2"] in battle["actions"]:
        return _resolve_pvp_turn(battle)
    else:
        return "入力を受け付けたわ。相手を待っているわね。", []

def _resolve_pvp_turn(battle):
    p1, p2 = battle["p1"], battle["p2"]
    act1, act2 = battle["actions"][p1], battle["actions"][p2]
    is_hard1 = KIMERA_SESSIONS[p1].get("is_hard_mode", False)
    is_hard2 = KIMERA_SESSIONS[p2].get("is_hard_mode", False)
    ud1 = core.get_user_data(p1, hard_mode=is_hard1)
    ud2 = core.get_user_data(p2, hard_mode=is_hard2)
    c1 = ud1["party"][0]
    c2 = ud2["party"][0]
    
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
            
    logs = []
    for actor_id, actor_c, act, target_id, target_c in order:
        if actor_c["current_hp"] <= 0: continue
        if act["type"] == "move":
            mid = act["value"]
            mdata = core.MOVES[mid]
            dmg = int(mdata["power"] * (actor_c["stats"]["atk"] / target_c["stats"]["def"]) * 0.4 * random.uniform(0.85, 1.0))
            if dmg < 1: dmg = 1
            
            # PvPでも半減実等は発動すべきだが、簡略化のためダメージのみ
            target_c["current_hp"] -= dmg
            logs.append(f"**{actor_c['nickname']}** の {mdata['name']}！ {target_c['nickname']} に {dmg} のダメージ！")
            
            if target_c["current_hp"] <= 0:
                target_c["current_hp"] = 0
                logs.append(f"**{target_c['nickname']}** は倒れた！")
                
    battle["actions"] = {}
    full_log = "\n".join(logs)
    
    loser = None
    if c1["current_hp"] <= 0 and c2["current_hp"] <= 0:
        core.save_user_data(p1, ud1, is_hard1)
        core.save_user_data(p2, ud2, is_hard2)
        _end_pvp(battle)
        msg = f"{full_log}\n\n相打ちね！ 引き分けよ！"
        return "", [(p1, msg), (p2, msg)]

    if c1["current_hp"] <= 0: loser = p1
    elif c2["current_hp"] <= 0: loser = p2
    
    if loser:
        core.save_user_data(p1, ud1, is_hard1)
        core.save_user_data(p2, ud2, is_hard2)
        _end_pvp(battle)
        winner = p2 if loser == p1 else p1
        msg = f"{full_log}\n\n勝負あり！ <@{winner}> の勝利よ！"
        KIMERA_SESSIONS[p1]["state"] = STATE_MENU; KIMERA_SESSIONS[p2]["state"] = STATE_MENU
        KIMERA_SESSIONS[p1]["context"]["sub_state"] = BATTLE_SUB_MAIN
        KIMERA_SESSIONS[p2]["context"]["sub_state"] = BATTLE_SUB_MAIN
        return "", [(p1, msg), (p2, msg)]

    core.save_user_data(p1, ud1, is_hard1)
    core.save_user_data(p2, ud2, is_hard2)
    KIMERA_SESSIONS[p1]["context"]["sub_state"] = BATTLE_SUB_MAIN
    KIMERA_SESSIONS[p2]["context"]["sub_state"] = BATTLE_SUB_MAIN
    msg_next = f"{full_log}\n\n次のターンよ！ どうする？"
    return "", [(p1, msg_next), (p2, msg_next)]

def _resolve_pvp_end(battle, loser_id):
    p1, p2 = battle["p1"], battle["p2"]
    winner_id = p2 if loser_id == p1 else p1
    _end_pvp(battle)
    msg = f"<@{loser_id}> が降参したわ。\n<@{winner_id}> の勝利よ！"
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