# kimera_game.py
import random
import re
import math
import kimera_core as core
import database as db
import logic
import kimera_data as data
from config import PRIMARY_ADMIN_ID

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
STATE_MOVE_MANAGE = "move_manage"

# サブステート
BATTLE_SUB_MAIN = "main"
BATTLE_SUB_ITEM = "item"
BATTLE_SUB_SWITCH = "switch"
BATTLE_SUB_FORCE_SWITCH = "force_switch"
BATTLE_SUB_WAIT = "wait"

KIMERA_SESSIONS = {}
PVP_CHALLENGES = {}
PVP_BATTLES = {}

# --- テキスト辞書 (Localization) ---
# 日本語(jp)をデフォルトとして定義
GAME_TEXT = {
    # Menu
    "menu_title": {"jp": "【キメラメニュー】", "en": "【Kimera Menu】"},
    "menu_opts": {
        "jp": "・**バトル**: 野生/CPU/対戦\n・**編成**: 手持ちとボックスの入れ替え\n・**装備**: アイテムを持たせる\n・**技**: 技の入れ替え\n・**詳細**: ステータス確認\n・**ショップ**: ボールや薬を買う\n・**回復**: 全回復する\n・**図鑑**: 出会ったキメラを見る\n・**終了**: ゲームを終わる\n",
        "en": "・**Battle**: Wild/CPU/PvP\n・**Party**: Manage Team & Box\n・**Equip**: Equip Items\n・**Moves**: Manage Moves\n・**Status**: Check Stats\n・**Shop**: Buy Items\n・**Heal**: Full Restore\n・**Dex**: Pokedex\n・**Exit**: Quit Game\n"
    },
    "menu_prompt": {"jp": "何をしたいのかしら？", "en": "What would you like to do?"},
    "healed": {"jp": "キメラセンターで手持ちとボックスの子を全回復しておいたわ♪", "en": "I healed all your Kimeras in your party and box at the Center♪"},
    
    # Move Manage
    "move_title": {"jp": "【技管理】 (対象: {name})", "en": "【Move Management】 ({name})"},
    "move_list": {"jp": "現在の技: {current}\n習得可能: {learned}\n\n『1を覚える』『1を忘れる』『1を忘れて2を覚える』のように言ってね。\n(戻るなら『戻る』)", "en": "Current: {current}\nLearned: {learned}\nSay 'Learn 1', 'Forget 1', or 'Forget 1 Learn 2'."},
    "move_changed": {"jp": "{out} を忘れて {in_} を覚えたわ！", "en": "Forgot {out} and learned {in_}!"},
    "move_learned": {"jp": "{in_} を覚えたわ！", "en": "Learned {in_}!"},
    "move_forgot": {"jp": "{out} を忘れたわ。", "en": "Forgot {out}."},
    
    "items_list": {"jp": "所持: {items}\n(『けいけんアメSを使う』って言ってね♪)", "en": "Owned: {items}\n(Say 'Use exp candy S' to use)"},
    "no_items_to_use": {"jp": "手持ちがいないわね。", "en": "You don't have any Kimeras in your party."},
    
    # Shop
    "shop_welcome": {"jp": "【ショップ】 (所持金: {money}G / Lv.{level})\n{items}\n\n『〇〇を買う』 / 『戻る』 って言ってね♪", "en": "【Shop】 (Money: {money}G / Lv.{level})\n{items}\n\nSay 'Buy [Item Name]' or 'Back'♪"},
    "shop_bought": {"jp": "**{item}** を購入したわ♪ (残: {money}G)", "en": "Bought **{item}**♪ (Rem: {money}G)"},
    "shop_no_money": {"jp": "お金が足りないみたいね。", "en": "You don't have enough money."},
    "shop_low_level": {"jp": "今のレベルじゃまだ買えないわね。", "en": "You need a higher level to buy that."},
    
    # Box & Equip
    "box_title": {"jp": "【パーティ & ボックス】", "en": "【Party & Box】"},
    "box_empty": {"jp": "(空っぽ)", "en": "(Empty)"},
    "box_cmds": {"jp": "『P1とB1を交代』 『P2を預ける』 『B1を入れる』 『戻る』", "en": "'Swap P1 B1', 'Store P2', 'Take B1', 'Back'"},
    "equip_title": {"jp": "【装備管理】", "en": "【Equipment Management】"},
    "equip_none": {"jp": "(なし)", "en": "(None)"},
    "equip_cmds": {"jp": "『1にハチマキを持たせる』『2を外す』\n『戻る』", "en": "'Equip Band to 1', 'Unequip 2'\n'Back'"},
    
    # Status & Dex
    "status_trainer": {"jp": "【トレーナー】Lv.{lv} (Exp:{xp}) / {money}G", "en": "【Trainer】Lv.{lv} (Exp:{xp}) / {money}G"},
    "dex_seen": {"jp": "【状態】 目撃のみ (詳細は捕まえてからのお楽しみね♪)", "en": "【Status】 Seen (Catch it to see details♪)"},
    
    # Battle Selection
    "battle_select_title": {"jp": "どこに行くのかしら？", "en": "Where would you like to go?"},
    "battle_opts": {
        "jp": "1. **確保ゾーン** (野生捕獲)\n2. **レベル上げゾーン** (CPU戦)\n3. **{mode_text}** (黄金裔13人抜き)\n4. **対戦ゾーン** (PvP)",
        "en": "1. **Catch Zone** (Wild)\n2. **Training Zone** (CPU)\n3. **{mode_text}** (Challenge)\n4. **PvP Zone** (Versus)"
    },
    "hard_mode_warning": {
        "jp": "【警告: 真なるキメラマスターロード解放】\n\n世界が反転し、黄金裔たちの真の力が解放されたわ……。\nこれより『ハードモード』のセーブデータに切り替えるわね。\n敵は神の個体値を持ち、全力で牙を剥くわ。\n準備はいい？ 死にゲーの始まりよ♪",
        "en": "【Warning: True Kimera Master Road Unlocked】\n\nSwitching to 'Hard Mode'. Enemies use full power with max stats.\nPrepare for death♪"
    },
    
    # Battle Events
    "wild_appear": {"jp": "野生の **{name}** (Lv.{lv}) {star} が飛び出してきたわ！\n(とてつもない殺気を感じる…！)\n『戦う』『道具』『入れ替え』『逃げる』", "en": "A wild **{name}** (Lv.{lv}) {star} appeared!\n(It looks super strong!)\n'Fight', 'Bag', 'Switch', 'Run'"},
    "trainer_appear": {"jp": "黄金裔の幻影が現れたわ！ **{name}** (Lv.{lv}) を繰り出してきたわよ！", "en": "A Golden Phantom appeared! Sent out **{name}** (Lv.{lv})!"},
    "challenge_start": {"jp": "【チャレンジモード Stage {stage}】\n**{name}**: 「{msg}」\n相手は **{poke}** (Lv.{lv}) を繰り出してきたわ！", "en": "【Challenge Mode Stage {stage}】\n**{name}**: \"{msg}\"\nOpponent sent out **{poke}** (Lv.{lv})!"},
    "pvp_start": {"jp": "対戦開始！ 相手は **{name}** (Lv.{lv}) よ！\nどうする？ 『戦う』 『降参』", "en": "PvP Start! Opponent is **{name}** (Lv.{lv})!\nWhat will you do? 'Fight', 'Surrender'"},
    
    # Battle Actions
    "cmd_prompt": {"jp": "どうするの？", "en": "What will you do?"},
    "cmd_bag": {"jp": "道具: {items}\n(戻るなら『戻る』)", "en": "Bag: {items}\n(Say 'Back' to return)"},
    "cmd_switch": {"jp": "誰と入れ替える？(番号)\n{party}", "en": "Switch with whom? (Number)\n{party}"},
    "cmd_moves": {"jp": "技: {moves}", "en": "Moves: {moves}"},
    "run_success": {"jp": "逃げ出したわ♪\n\n(メニューに戻りました)", "en": "Got away safely♪\n\n(Returned to menu)"},
    "run_fail": {"jp": "チャレンジモードからは逃げられないわよ！", "en": "You can't run from a Challenge Battle!"},
    
    # Battle Logs
    "log_hit": {"jp": "{atkr} の {move}！{eff} {dmg} ダメージ！", "en": "{atkr} used {move}!{eff} {dmg} damage!"},
    "log_stat": {"jp": "{atkr} の {move}！", "en": "{atkr} used {move}!"},
    "log_recharge": {"jp": "{name} は反動で動けない！", "en": "{name} must recharge!"},
    "log_recoil": {"jp": "{name} は反動を受けた！", "en": "{name} took recoil damage!"},
    "eff_super": {"jp": " 効果はばつぐんよ！", "en": " It's super effective!"},
    "eff_not": {"jp": " 効果はいまひとつね...", "en": " It's not very effective..."},
    "eff_none": {"jp": " 効果がないみたい...", "en": " It had no effect..."},
    "status_ailment": {"jp": "{name} は {stat} になっちゃったわ！", "en": "{name} became {stat}!"},
    "buff": {"jp": "{name} の能力が上がったわ！", "en": "{name}'s stats rose!"},
    "debuff": {"jp": "{name} の能力を下げたわ！", "en": "{name}'s stats fell!"},
    "fainted": {"jp": "\n{name} は倒れたわ！", "en": "\n{name} fainted!"},
    "win_pve": {"jp": "勝利よ！ 素晴らしいわ♪\n賞金 {money}G と トレーナーXP {xp} を獲得したわ！", "en": "You won! Wonderful♪\nEarned {money}G and {xp} Trainer XP!"},
    "lose_pve": {"jp": "\n手持ちが全滅しちゃったわね… (所持金 -{lost}G)\n\n(キメラセンターで回復してメニューに戻ったわ♪)", "en": "\nYou have no more Kimeras... (Money -{lost}G)\n\n(Healed at the Center and returned to menu♪)"},
    "catch_success": {"jp": "やった！ {name} を捕まえたわよ♪\n(捕獲したので通常の強さに戻りました)\n(好感度XP +50)\n\n(メニューに戻りました)", "en": "Yay! You caught {name}♪\n(Stats normalized)\n(Affection XP +50)\n\n(Returned to menu)"},
    "catch_fail": {"jp": "ボールから抜け出されちゃった！", "en": "It broke free!"},
    
    # Errors/Misc
    "err_no_item": {"jp": "持っていないわね。", "en": "You don't have that."},
    "err_cant_use": {"jp": "今は使えないわね。", "en": "You can't use that now."},
    "err_full_party": {"jp": "手持ちがいっぱいね（最大3体）。", "en": "Your party is full (Max 3)."},
    "err_invalid": {"jp": "指定が間違ってるみたいね。", "en": "Invalid selection."},

    # Battle Logs (More)
    "log_oblivion": {"jp": "{name} は技の使い方をド忘れしちゃった！", "en": "{name} forgot how to use that move!"},
    "log_reflect": {"jp": "反射！ {dmg} のダメージ！", "en": "Reflect damage! {dmg}"},
    "log_hp_display": {"jp": "(相手HP: {ehp} / 自分HP: {php})", "en": "(Enemy HP: {ehp} / Player HP: {php})"},
    "log_paralyzed_cant_move": {"jp": "{name} は痺れて動けない！", "en": "{name} is paralyzed!"},
    "log_woke_up": {"jp": "{name} は目を覚ました！", "en": "{name} woke up!"},
    "log_sleeping": {"jp": "{name} は眠っている...", "en": "{name} is sleeping..."},
    "log_poison_hurt": {"jp": "{name} は毒に蝕まれている！", "en": "{name} is hurt by poison!"},
    "log_burn_hurt": {"jp": "{name} は火傷でダメージを受けた！", "en": "{name} is hurt by burn!"},
    "log_hung_on": {"jp": "{name} はタスキで持ちこたえた！", "en": "{name} hung on with Sash!"},
    "log_potion": {"jp": "相手は回復薬を使った！ {name} の体力が回復！", "en": "Enemy used Potion! {name} healed!"},
    "log_icarun_start": {"jp": "イカルンが召喚された！ 毎ターン回復するわよ！", "en": "Icarun summoned! Healing every turn!"},
    "log_icarun_heal": {"jp": "イカルンが {name} を回復した！", "en": "Icarun healed {name}!"},
    "log_synergy_start": {"jp": "【共鳴】『{syn}』が発動！ {eff}", "en": "【Synergy】'{syn}' activated! {eff}"},
    "log_synergy_heal": {"jp": "【共鳴】『{syn}』の効果で回復した！", "en": "【Synergy】Healed by '{syn}'!"},
    "log_revived": {"jp": "\n{name} は復活したわ！", "en": "\n{name} revived!"},
    "log_self_heal": {"jp": "{name} は回復した！", "en": "{name} healed!"},
    
    "win_level_up": {"jp": "\nトレーナーレベルが {lv} に上がったわ！", "en": "\nTrainer Level Up -> {lv}!"},
    "win_aff_xp": {"jp": "\n(好感度XP +50)", "en": "\n(Affection XP +50)"},
    "battle_select_back": {"jp": "メニューに戻ったわ。", "en": "Back to menu."},
}

def get_k_text(user_id, key, **kwargs):
    # バグ対策: 強制的にJPをデフォルトとする
    lang = db.get_user_lang(user_id)
    if not lang or lang == "en": lang = "jp"
    
    text_map = GAME_TEXT.get(key, {})
    # キーが見つからない場合や、jpがない場合のフォールバックを強化
    tmpl = text_map.get(lang, text_map.get("jp", ""))
    if not tmpl and "jp" in text_map: tmpl = text_map["jp"]
    
    return tmpl.format(**kwargs)

def get_session(user_id):
    return KIMERA_SESSIONS.get(user_id)

def start_session(user_id):
    KIMERA_SESSIONS[user_id] = {
        "state": STATE_MENU, 
        "context": {},
        "is_hard_mode": False 
    }
    core.get_user_data(user_id, hard_mode=False)

def end_session(user_id):
    if user_id in KIMERA_SESSIONS:
        if KIMERA_SESSIONS[user_id]["state"] == STATE_BATTLE_PVP_LOBBY:
            to_del = [k for k, v in PVP_CHALLENGES.items() if v == user_id]
            for k in to_del:
                del PVP_CHALLENGES[k]
        del KIMERA_SESSIONS[user_id]

# --- バトル用ヘルパー関数群 ---

def _init_battle_context(session, enemy_party, enemy_name, stage=None, potions=0, ud=None):
    session["context"] = {
        "enemy_party": enemy_party,
        "enemy_name": enemy_name,
        "stage": stage,
        "sub_state": BATTLE_SUB_MAIN,
        "potions": potions,
        "turn_count": 0,
        "field_effects": {
            "icarun": {"p1": False, "p2": False},
            "kyurene_ghost": {"p1": False, "p2": False},
            "embers": {"p1": 0, "p2": 0},
            "remembrance": {"p1": 0, "p2": 0},
            "aglaia_speed": {"p1": 0, "p2": 0},
        },
        "active_synergies": {"p1": [], "p2": []},
        "logs": []
    }
    
    if ud:
        _init_chimera_battle_states(session, "p1", ud=ud)
        _apply_team_synergies(session, "p1", ud["party"])
    else:
        pass

    _init_chimera_battle_states(session, "p2", enemy_party=enemy_party)

def _init_chimera_battle_states(session, side, ud=None, enemy_party=None):
    party = []
    if side == "p1":
        if ud: party = ud["party"]
    else:
        party = enemy_party if enemy_party else session["context"]["enemy_party"]
    
    for c in party:
        c["battle_state"] = {
            "revived": False,
            "barrier_hp": 0,
            "submission_prep": False,
            "rocket": False,
            "oblivion_cd": 0,
            "recharge": False,
            "choice_lock": None,
            "form": None
        }
        # ステータスランク初期化
        c["stat_stages"] = {"atk": 0, "def": 0, "spa": 0, "spd": 0, "spe": 0, "acc": 0, "eva": 0}
        
        base = data.BASE_CHIMERAS[c["base_id"]]
        if base["name"] == "キュヌレ":
            session["context"]["field_effects"]["remembrance"][side] = 24

def _apply_team_synergies(session, side, party):
    active_keys = []
    base_ids = [c["base_id"] for c in party]
    
    user_id = [k for k, v in KIMERA_SESSIONS.items() if v == session][0] if side == "p1" else None

    for key, syn in data.TEAM_SYNERGIES.items():
        required = syn["members"]
        if all(mid in base_ids for mid in required):
            active_keys.append(key)
            eff = syn["effect"]
            
            if eff["type"] == "buff_start":
                for c in party:
                    for stat, stage in eff["stats"].items():
                        c["stat_stages"][stat] = min(6, c["stat_stages"][stat] + stage)
                
                if user_id:
                    log = get_k_text(user_id, "log_synergy_start", syn=syn['name'], eff="能力が上がった！")
                    session["context"]["logs"].append(log)
            
            elif eff["type"] == "regen":
                if user_id:
                    log = get_k_text(user_id, "log_synergy_start", syn=syn['name'], eff="毎ターン回復する！")
                    session["context"]["logs"].append(log)

    session["context"]["active_synergies"][side] = active_keys

def _calculate_damage(attacker, defender, move_id, session):
    move = data.MOVES[move_id]
    is_burn = attacker.get("status_condition") == "burn"
    power = move["power"]
    if move["category"] == "Status": return 0, 1.0
    
    meff = move.get("effect", {})
    if meff.get("type") == "conditional_power":
        cond = meff["condition"]
        mult = meff["multiplier"]
        target_status = defender.get("status_condition")
        
        match = False
        if cond == "poison" and target_status == "poison": match = True
        elif cond == "any_status" and target_status is not None: match = True
        
        if match: power = int(power * mult)

    def get_stage_mult(stage):
        return max(2, 2 + stage) / max(2, 2 - stage)
    
    if move["category"] == "Physical":
        a_stat = int(attacker["stats"]["atk"] * get_stage_mult(attacker["stat_stages"]["atk"]))
        d_stat = int(defender["stats"]["def"] * get_stage_mult(defender["stat_stages"]["def"]))
        if is_burn: a_stat = int(a_stat * 0.5)
        if attacker.get("held_item") == "choice_band": a_stat = int(a_stat * 1.5)
            
    else:
        a_stat = int(attacker["stats"]["spa"] * get_stage_mult(attacker["stat_stages"]["spa"]))
        d_stat = int(defender["stats"]["spd"] * get_stage_mult(defender["stat_stages"]["spd"]))
        if attacker.get("held_item") == "choice_specs": a_stat = int(a_stat * 1.5)

    if d_stat < 1: d_stat = 1
    
    dmg = int(math.floor(math.floor(math.floor(2 * attacker["level"] / 5 + 2) * power * a_stat / d_stat) / 50) + 2)
    
    base_def = data.BASE_CHIMERAS[defender["base_id"]]
    type_eff = 1.0
    if move["type"] in data.TYPE_CHART:
        eff_dict = data.TYPE_CHART[move["type"]]
        if base_def["type"] in eff_dict:
            type_eff = eff_dict[base_def["type"]]
    
    dmg = int(dmg * type_eff)
    
    if attacker.get("status_condition") == "submission":
        dmg = int(dmg * 0.75)

    dmg = int(dmg * random.uniform(0.85, 1.0))
    if dmg < 1: dmg = 1

    if attacker.get("held_item") == "life_orb": dmg = int(dmg * 1.3)
    if attacker.get("held_item") == "expert_belt" and type_eff > 1.0: dmg = int(dmg * 1.2)
    if core.check_resist_berry(defender, move["type"]):
        dmg = int(dmg * 0.5)
        defender["held_item"] = None
        
    return dmg, type_eff

def _apply_status_effect(target, status_name, session, user_id):
    if target.get("status_condition"): return False
    target["status_condition"] = status_name
    s_name = data.STATUS_CONDITIONS.get(status_name, {}).get("name", status_name) 
    
    log = get_k_text(user_id, "status_ailment", name=target['nickname'], stat=s_name)
    session["context"]["logs"].append(log)
    return True

# --- メニュー処理 ---
def handle_menu(user_id, content):
    session = KIMERA_SESSIONS[user_id]
    is_hard = session.get("is_hard_mode", False)
    ud = core.get_user_data(user_id, hard_mode=is_hard)
    lang = db.get_user_lang(user_id)

    # --- Debug ---
    if content == "デバッグ解放":
        normal_ud = core.get_user_data(user_id, hard_mode=False)
        normal_ud["items"]["story_page_2"] = 1
        core.save_user_data(user_id, normal_ud, hard_mode=False)
        return "【Debug】 Added 'story_page_2'.", []
    
    if content == "デバッグ封印":
        normal_ud = core.get_user_data(user_id, hard_mode=False)
        if "story_page_2" in normal_ud["items"]: del normal_ud["items"]["story_page_2"]
        core.save_user_data(user_id, normal_ud, hard_mode=False)
        return "【Debug】 Removed 'story_page_2'.", []

    if content == "デバッグ最強召喚" and user_id == PRIMARY_ADMIN_ID:
        god = core.create_chimera_instance("kyunure", level=200, nickname="DebugGod")
        god["ivs"] = {k: 31 for k in god["ivs"]}
        god["held_item"] = "life_orb"
        core.update_chimera_stats(god)
        god["current_hp"] = god["stats"]["max_hp"]
        if len(ud["party"]) < 3: ud["party"].append(god)
        else: ud["box"].append(god)
        core.save_user_data(user_id, ud, hard_mode=is_hard)
        return "【Admin】 Summoned 'DebugGod' (Lv.200).", []

    # --- Mode Switch ---
    if "真なるキメラマスターロード" in content:
        if is_hard: return "既にハードモードよ。", []
        normal_ud = core.get_user_data(user_id, hard_mode=False)
        if "story_page_2" in normal_ud["items"]:
            session["is_hard_mode"] = True
            core.get_user_data(user_id, hard_mode=True)
            return get_k_text(user_id, "hard_mode_warning"), []
        else:
            return "まだその資格はないみたい。", []

    if "ノーマルに戻る" in content:
        if is_hard:
            session["is_hard_mode"] = False
            return "平和な世界（ノーマルモード）のデータに戻したわよ♪", []
        return "既にノーマルモードよ。", []

    # --- Menu Navigation ---
    norm_content = content.translate(str.maketrans({chr(0xFF10 + i): chr(0x30 + i) for i in range(10)}))
    c_lower = content.lower()

    if "技" in content or "moves" in c_lower:
        session["state"] = STATE_MOVE_MANAGE
        return _get_move_manage_text(user_id), []

    if "バトル" in content or "battle" in c_lower or "3" in norm_content:
        session["state"] = STATE_BATTLE_SELECT
        if "チャレンジ" in content or "3" in norm_content:
             return handle_battle_select(user_id, content)
        
        mode_text = "【真・キメラマスターロード】" if is_hard else "チャレンジモード"
        msg = f"{get_k_text(user_id, 'battle_select_title')}\n{get_k_text(user_id, 'battle_opts', mode_text=mode_text)}"
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
        base_msg = get_k_text(user_id, "status_trainer", lv=ud['trainer_level'], xp=ud['trainer_xp'], money=ud['money'])
        if is_hard: base_msg += "\n★ Hard Mode ★\n"
        if not ud['party']: return base_msg + get_k_text(user_id, "no_items_to_use"), []
        chimera = ud['party'][0]
        return f"{base_msg}【Lead】\n{core.get_chimera_display_stats(chimera)}", []

    if "ショップ" in content:
        session["state"] = STATE_SHOP
        tlv = ud["trainer_level"]
        lines = []
        for k, v in data.ITEMS.items():
            if v["price"] > 0 and v.get("unlock_rank", 1) <= tlv:
                lines.append(f"・**{v['name']}**: {v['price']}G")
        return get_k_text(user_id, "shop_welcome", money=ud['money'], level=tlv, items="\n".join(lines)), []

    if "回復" in content:
        core.heal_all_kimeras(ud)
        core.save_user_data(user_id, ud, hard_mode=is_hard)
        return get_k_text(user_id, "healed"), []

    if "図鑑" in content:
        m_search = re.search(r"(?:図鑑|dex)\s+(.+)", content, re.IGNORECASE)
        if m_search:
            target_name = m_search.group(1).strip()
            found_key = None
            for k, v in data.BASE_CHIMERAS.items():
                if v["name"] == target_name or v.get("name_en", "").lower() == target_name.lower():
                    found_key = k
                    break
            
            if not found_key: return "その名前のキメラはデータにないわね。", []

            status = ud["dex"].get(found_key)
            if not status: return "そのキメラはまだ発見していないみたい。", []
            
            base = data.BASE_CHIMERAS[found_key]
            
            if status == "seen":
                return f"📖 **No.{found_key} {base['name']}**\n{get_k_text(user_id, 'dex_seen')}", []
            
            elif status == "caught":
                rarity = "★" * base.get('rarity', 1)
                bs = base['base_stats']
                desc = base.get('description', 'No Data.')
                total_bs = sum(bs.values())
                
                msg = (
                    f"━━━━━━━━━━━━━━━\n"
                    f"📖 **No.{found_key} {base['name']}** {rarity}\n"
                    f"━━━━━━━━━━━━━━━\n"
                    f"Type: {base['type']}\n"
                    f"Ability: **{base['ability']}**\n"
                    f"-------------------------------\n"
                    f"{desc}\n"
                    f"-------------------------------\n"
                    f"HP:{bs['hp']} Atk:{bs['atk']} Def:{bs['def']} SpA:{bs['spa']} SpD:{bs['spd']} Spe:{bs['spe']} (Total:{total_bs})\n"
                    f"━━━━━━━━━━━━━━━"
                )
                return msg, []

        total = len(data.BASE_CHIMERAS)
        caught = sum(1 for v in ud["dex"].values() if v == "caught")
        seen = len(ud["dex"])
        
        lines = [f"【Dex】 Caught: {caught}/{total} / Seen: {seen}/{total}"]
        for k in sorted(data.BASE_CHIMERAS.keys()):
            base = data.BASE_CHIMERAS[k]
            status = ud["dex"].get(k)
            if status == "caught": mark = "★"; dname = base['name']
            elif status == "seen": mark = "○"; dname = base['name']
            else: mark = "・"; dname = "？？？"
            lines.append(f"{mark} {dname}")
        
        return "\n".join(lines) + "\n『図鑑 ウルフパピー』のように名前を入れると詳細が見れるわよ♪", []

    if "アイテム" in content:
        items_txt = ", ".join([f"{data.ITEMS[k]['name']}x{v}" for k, v in ud['items'].items()])
        return get_k_text(user_id, "items_list", items=items_txt), []
        
    m = re.match(r"(.+)(?:を使う| use)", content, re.IGNORECASE)
    if m:
        item_name = m.group(1).replace("use ", "").strip()
        item_key = next((k for k, v in data.ITEMS.items() if v["name"] == item_name), None)
        if item_key:
            if not ud["party"]: return get_k_text(user_id, "no_items_to_use"), []
            res = core.apply_item_effect_logic(ud, item_key, ud["party"][0])
            core.save_user_data(user_id, ud, hard_mode=is_hard)
            return res, []

    return f"{get_k_text(user_id, 'menu_title')}\n{get_k_text(user_id, 'menu_opts')}\n{get_k_text(user_id, 'menu_prompt')}", []

# --- 技管理メニュー ---
def _get_move_manage_text(user_id):
    session = KIMERA_SESSIONS[user_id]
    ud = core.get_user_data(user_id, hard_mode=session.get("is_hard_mode", False))
    if not ud["party"]: return get_k_text(user_id, "no_items_to_use")
    
    c = ud["party"][0]
    current = ", ".join([f"[{i+1}]{data.MOVES[m]['name']}" for i, m in enumerate(c["moves"])])
    
    available = [m for m in c["learned_moves"] if m not in c["moves"]]
    learned = ", ".join([f"[{i+1}]{data.MOVES[m]['name']}" for i, m in enumerate(available)]) if available else "(なし)"
    
    return get_k_text(user_id, "move_title", name=c['nickname']) + "\n" + get_k_text(user_id, "move_list", current=current, learned=learned)

def handle_move_manage(user_id, content):
    session = KIMERA_SESSIONS[user_id]
    ud = core.get_user_data(user_id, hard_mode=session.get("is_hard_mode", False))
    if "戻る" in content:
        session["state"] = STATE_MENU
        return get_k_text(user_id, "menu_prompt"), []

    c = ud["party"][0]
    available = [m for m in c["learned_moves"] if m not in c["moves"]]

    m_swap_forget = re.search(r"(\d+)(?:を忘れて| forget)", content)
    m_swap_learn = re.search(r"(\d+)(?:を覚える| learn)", content)
    
    m_learn_only = re.search(r"(\d+)(?:を覚える| learn)", content)
    m_forget_only = re.search(r"(\d+)(?:を忘れる| forget)", content)

    # 1. 入れ替え
    if m_swap_forget and m_swap_learn:
        f_idx = int(m_swap_forget.group(1)) - 1
        l_idx = int(m_swap_learn.group(1)) - 1
        
        if 0 <= f_idx < len(c["moves"]) and 0 <= l_idx < len(available):
            forget_move = c["moves"][f_idx]
            learn_move = available[l_idx]
            c["moves"][f_idx] = learn_move
            core.save_user_data(user_id, ud, hard_mode=session.get("is_hard_mode", False))
            msg = get_k_text(user_id, "move_changed", out=data.MOVES[forget_move]['name'], in_=data.MOVES[learn_move]['name'])
            return msg + "\n\n" + _get_move_manage_text(user_id), []
        else:
            return "指定された番号が正しくないわ。", []

    # 2. 覚える
    elif m_learn_only and not m_swap_forget:
        l_idx = int(m_learn_only.group(1)) - 1
        if 0 <= l_idx < len(available):
            if len(c["moves"]) < 4:
                learn_move = available[l_idx]
                c["moves"].append(learn_move)
                core.save_user_data(user_id, ud, hard_mode=session.get("is_hard_mode", False))
                msg = get_k_text(user_id, "move_learned", in_=data.MOVES[learn_move]['name'])
                return msg + "\n\n" + _get_move_manage_text(user_id), []
            else:
                return "技がいっぱいで覚えられないわ。忘れる技も指定してね（例: 1を忘れて2を覚える）。", []
        else:
             return "指定された番号の技は習得リストにないわ。", []

    # 3. 忘れる
    elif m_forget_only:
        f_idx = int(m_forget_only.group(1)) - 1
        if 0 <= f_idx < len(c["moves"]):
            if len(c["moves"]) > 1:
                forgot_move = c["moves"].pop(f_idx)
                core.save_user_data(user_id, ud, hard_mode=session.get("is_hard_mode", False))
                msg = get_k_text(user_id, "move_forgot", out=data.MOVES[forgot_move]['name'])
                return msg + "\n\n" + _get_move_manage_text(user_id), []
            else:
                return "全ての技を忘れることはできないわ（最低1つは必要よ）。", []
        else:
             return "指定された番号の技は持っていないわ。", []
    
    return "『1を忘れて2を覚える』、『1を覚える』、『1を忘れる』のように指定してね。", []

# --- 装備操作 ---
def _get_equip_menu_text(user_id):
    session = KIMERA_SESSIONS[user_id]
    ud = core.get_user_data(user_id, hard_mode=session.get("is_hard_mode", False))
    
    msg = get_k_text(user_id, "equip_title") + "\n"
    for i, c in enumerate(ud["party"]):
        item_name = data.ITEMS[c["held_item"]]["name"] if c["held_item"] else get_k_text(user_id, "equip_none")
        msg += f"{i+1}. {c['nickname']}: {item_name}\n"
    
    equipable = []
    for k, v in ud["items"].items():
        idata = data.ITEMS.get(k)
        if idata and idata["effect_type"].startswith("equip_"):
            equipable.append(f"{idata['name']}")
            
    msg += "\n" + (", ".join(equipable) if equipable else get_k_text(user_id, "equip_none"))
    msg += "\n\n" + get_k_text(user_id, "equip_cmds")
    return msg

def handle_equip_menu(user_id, content):
    session = KIMERA_SESSIONS[user_id]
    is_hard = session.get("is_hard_mode", False)
    ud = core.get_user_data(user_id, hard_mode=is_hard)
    
    if "戻る" in content:
        session["state"] = STATE_MENU
        return get_k_text(user_id, "menu_prompt"), []

    m = re.search(r"(\d+)(?:に| )(.+?)(?:を持たせる| equip)", content, re.IGNORECASE)
    if m:
        idx = int(m.group(1)) - 1
        item_name = m.group(2).strip()
        item_key = next((k for k, v in data.ITEMS.items() if v["name"] == item_name), None)
        if item_key:
            res = core.equip_item_logic(ud, idx, item_key)
            core.save_user_data(user_id, ud, hard_mode=is_hard)
            return res + "\n" + _get_equip_menu_text(user_id), []
        else:
            return get_k_text(user_id, "err_no_item"), []

    m = re.search(r"(\d+)(?:を外す| unequip)", content, re.IGNORECASE)
    if m:
        idx = int(m.group(1)) - 1
        res = core.unequip_item_logic(ud, idx)
        core.save_user_data(user_id, ud, hard_mode=is_hard)
        return res + "\n" + _get_equip_menu_text(user_id), []

    return get_k_text(user_id, "equip_cmds"), []

# --- ボックス操作 ---
def _get_box_menu_text(user_id):
    session = KIMERA_SESSIONS[user_id]
    ud = core.get_user_data(user_id, hard_mode=session.get("is_hard_mode", False))
    
    msg = get_k_text(user_id, "box_title") + "\n【Party】\n"
    for i, c in enumerate(ud['party']):
        msg += f"P{i+1}: {c['nickname']} (Lv.{c['level']})\n"
    
    msg += "\n【Box】\n"
    if ud['box']:
        for i, c in enumerate(ud['box']):
            msg += f"B{i+1}: {c['nickname']} (Lv.{c['level']})\n"
    else:
        msg += get_k_text(user_id, "box_empty")
        
    msg += "\n" + get_k_text(user_id, "box_cmds")
    return msg

def handle_box_menu(user_id, content):
    session = KIMERA_SESSIONS[user_id]
    is_hard = session.get("is_hard_mode", False)
    ud = core.get_user_data(user_id, hard_mode=is_hard)
    
    if "戻る" in content:
        session["state"] = STATE_MENU
        return get_k_text(user_id, "menu_prompt"), []

    m_swap = re.search(r"[Pp](\d+).*?[Bb](\d+)", content)
    m_to_box = re.search(r"[Pp](\d+).*?(?:預ける|store)", content, re.IGNORECASE)
    m_to_party = re.search(r"[Bb](\d+).*?(?:入れる|take)", content, re.IGNORECASE)

    if m_swap:
        pidx = int(m_swap.group(1))-1
        bidx = int(m_swap.group(2))-1
        if core.swap_party_box(ud, pidx, bidx):
            core.save_user_data(user_id, ud, hard_mode=is_hard)
            return "交代したわ！\n" + _get_box_menu_text(user_id), []
        return get_k_text(user_id, "err_invalid"), []

    elif m_to_box:
        pidx = int(m_to_box.group(1))-1
        if core.move_party_to_box(ud, pidx):
            core.save_user_data(user_id, ud, hard_mode=is_hard)
            return "ボックスに預けたわ。\n" + _get_box_menu_text(user_id), []
        return "最後の1匹は預けられないわ！", []

    elif m_to_party:
        bidx = int(m_to_party.group(1))-1
        if core.move_box_to_party(ud, bidx):
            core.save_user_data(user_id, ud, hard_mode=is_hard)
            return "手持ちに加えたわ！\n" + _get_box_menu_text(user_id), []
        return get_k_text(user_id, "err_full_party"), []

    return get_k_text(user_id, "box_cmds"), []

# --- ショップ ---
def handle_shop(user_id, content):
    session = KIMERA_SESSIONS[user_id]
    is_hard = session.get("is_hard_mode", False)
    ud = core.get_user_data(user_id, hard_mode=is_hard)
    
    if "戻る" in content:
        session["state"] = STATE_MENU
        return get_k_text(user_id, "menu_prompt"), []
    
    matches = [k for k, v in data.ITEMS.items() if v["name"] in content]
    target_key = max(matches, key=lambda k: len(data.ITEMS[k]["name"])) if matches else None
    
    if target_key:
        item = data.ITEMS[target_key]
        if item.get("unlock_rank", 1) > ud["trainer_level"]:
            return get_k_text(user_id, "shop_low_level"), []
        if ud["money"] >= item["price"]:
            ud["money"] -= item["price"]
            ud["items"][target_key] = ud["items"].get(target_key, 0) + 1
            core.save_user_data(user_id, ud, hard_mode=is_hard)
            return get_k_text(user_id, "shop_bought", item=item['name'], money=ud['money']), []
        else:
            return get_k_text(user_id, "shop_no_money"), []
    return "『〇〇を買う』と言ってね。", []

# --- バトル選択 ---
def handle_battle_select(user_id, content):
    session = KIMERA_SESSIONS[user_id]
    is_hard = session.get("is_hard_mode", False)
    ud = core.get_user_data(user_id, hard_mode=is_hard)
    tlv = ud["trainer_level"]
    content = content.translate(str.maketrans({chr(0xFF10 + i): chr(0x30 + i) for i in range(10)}))

    # --- ハードモード切替 ---
    if "真なるキメラマスターロード" in content:
        if is_hard: return "既にハードモードよ。", []
        normal_ud = core.get_user_data(user_id, hard_mode=False)
        if "story_page_2" in normal_ud["items"]:
            session["is_hard_mode"] = True
            core.get_user_data(user_id, hard_mode=True)
            # 修正: 状態をメインメニューに戻す
            session["state"] = STATE_MENU
            return get_k_text(user_id, "hard_mode_warning") + "\n\n(メニューに戻りました)", []
        else:
            return "まだその資格はないみたい。", []

    if "戻る" in content:
        session["state"] = STATE_MENU
        return get_k_text(user_id, "battle_select_back") + "\n" + get_k_text(user_id, "menu_prompt"), []

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
        
        mult_hp = 3.0 if not is_hard else 5.0
        mult_st = 1.5 if not is_hard else 2.0
        wild["stats"]["max_hp"] = int(wild["stats"]["max_hp"] * mult_hp)
        for k in ["atk", "def", "spa", "spd", "spe"]:
            wild["stats"][k] = int(wild["stats"][k] * mult_st)
        wild["current_hp"] = wild["stats"]["max_hp"]
        
        session["state"] = STATE_BATTLE_WILD
        _init_battle_context(session, [wild], "Wild Kimera", ud=ud)
        core.register_dex(ud, wild["base_id"], caught=False)
        core.save_user_data(user_id, ud, hard_mode=is_hard)
        
        rarity_star = "★" * wild.get("rarity", 1)
        return get_k_text(user_id, "wild_appear", name=wild['nickname'], lv=wild['level'], star=rarity_star), []

    if "レベル上げ" in content or "2" in content:
        cpu_base = random.choice(list(data.BASE_CHIMERAS.keys()))
        c_lv = max(5, tlv + random.randint(0, 5))
        cpu_c = core.create_chimera_instance(cpu_base, level=c_lv)
        session["state"] = STATE_BATTLE_TRAINER
        _init_battle_context(session, [cpu_c], "Phantom", ud=ud)
        
        core.register_dex(ud, cpu_c["base_id"], caught=False)
        core.save_user_data(user_id, ud, hard_mode=is_hard)
        return get_k_text(user_id, "trainer_appear", name=cpu_c['nickname'], lv=cpu_c['level']), []

    if "チャレンジ" in content or "3" in content:
        stage = ud.get("challenge_stage", 1)
        if stage > 14:
            stage = 1
            ud["challenge_stage"] = 1
            core.save_user_data(user_id, ud, hard_mode=is_hard)
        
        trainer_source = data.CHALLENGE_TRAINERS_HARD if is_hard else data.CHALLENGE_TRAINERS
        t_data = trainer_source.get(stage)
        if not t_data: return "準備中よ。", []
        
        enemy_party = []
        for p in t_data["party"]:
            iv_val = 31 if is_hard else None
            c = core.create_chimera_instance(p["base_id"], p["level"], held_item=p.get("item"), fixed_iv=iv_val)
            core.update_chimera_stats(c)
            c["current_hp"] = c["stats"]["max_hp"]
            enemy_party.append(c)
            core.register_dex(ud, c["base_id"], caught=False)
        
        core.save_user_data(user_id, ud, hard_mode=is_hard)
        session["state"] = STATE_BATTLE_CHALLENGE
        _init_battle_context(session, enemy_party, t_data["name"], stage=stage, potions=t_data.get("potions", 0), ud=ud)
        
        start_msg = t_data.get("dialogue_start", "Start!")
        first = enemy_party[0]
        return get_k_text(user_id, "challenge_start", stage=stage, name=t_data['name'], msg=start_msg, poke=first['nickname'], lv=first['level']), []

    if "対戦" in content or "4" in content:
        challenger = PVP_CHALLENGES.get(user_id)
        if challenger: return _initiate_pvp_battle(challenger, user_id)
        session["state"] = STATE_BATTLE_PVP_LOBBY
        return "対戦相手をメンションしてね。", []

    return get_k_text(user_id, "battle_select_title"), []

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

    if "battle_state" not in player:
        _init_chimera_battle_states(session, "p1", ud=ud)
        player = ud['party'][0]
        
    if not enemy: return _resolve_pve_win(user_id, session, ud)

    sub = ctx.get("sub_state", BATTLE_SUB_MAIN)

    if sub == BATTLE_SUB_MAIN:
        if "逃" in content:
            if session["state"] == STATE_BATTLE_CHALLENGE: return get_k_text(user_id, "run_fail"), []
            session["state"] = STATE_MENU
            session["context"] = {}
            return get_k_text(user_id, "run_success"), []
            
        if "道具" in content:
            ctx["sub_state"] = BATTLE_SUB_ITEM
            items = [f"{data.ITEMS[k]['name']}x{v}" for k, v in ud['items'].items()]
            return get_k_text(user_id, "cmd_bag", items=", ".join(items)), []
        if "入れ替え" in content:
            ctx["sub_state"] = BATTLE_SUB_SWITCH
            return get_k_text(user_id, "cmd_switch", party=_generate_party_list(ud)), []
        if "戦" in content:
            moves = [data.MOVES[m]['name'] for m in player["moves"]]
            return get_k_text(user_id, "cmd_moves", moves=", ".join(moves)), []

        matched_moves = [m for m in player["moves"] if data.MOVES[m]["name"] in content]
        if matched_moves:
            sel_move = max(matched_moves, key=lambda m: len(data.MOVES[m]["name"]))
            
            # こだわりロック
            locked = player["battle_state"].get("choice_lock")
            if locked and sel_move != locked:
                return f"こだわりアイテムの効果で『{data.MOVES[locked]['name']}』しか出せない！", []
            
            held = player.get("held_item")
            if held in ["choice_band", "choice_specs"] and not locked:
                player["battle_state"]["choice_lock"] = sel_move

            return _execute_pve_turn(user_id, session, player, enemy, sel_move, ud)

        return get_k_text(user_id, "cmd_prompt"), []

    elif sub == BATTLE_SUB_ITEM:
        if "戻る" in content:
            ctx["sub_state"] = BATTLE_SUB_MAIN
            return get_k_text(user_id, "cmd_prompt"), []
            
        matches = [k for k, v in data.ITEMS.items() if v["name"] in content]
        sel_item = max(matches, key=lambda k: len(data.ITEMS[k]["name"])) if matches else None
        
        if sel_item:
            return use_item_in_battle(user_id, session, sel_item, ud, player, enemy), []
        return "アイテムを選んでね。", []

    elif sub == BATTLE_SUB_SWITCH:
        if "戻る" in content:
            ctx["sub_state"] = BATTLE_SUB_MAIN
            return get_k_text(user_id, "cmd_prompt"), []
        
        res = _try_switch_member(user_id, content, ud, player, allow_cancel=True)
        if res["success"]:
            ctx["sub_state"] = BATTLE_SUB_MAIN
            target = res["target"]
            # スイッチ時は戦闘状態リセット
            if "battle_state" in target: target["battle_state"]["choice_lock"] = None
            if "stat_stages" not in target:
                 target["battle_state"] = {
                    "revived": False, "barrier_hp": 0, "submission_prep": False,
                    "rocket": False, "oblivion_cd": 0, "recharge": False, "choice_lock": None, "form": None
                }
                 target["stat_stages"] = {"atk": 0, "def": 0, "spa": 0, "spd": 0, "spe": 0, "acc": 0, "eva": 0}

            msg = f"ゆけっ！ {target['nickname']}！\n"
            msg += _enemy_attack_phase(user_id, session, target, enemy, ud)
            return msg, []
        return res["msg"], []

    elif sub == BATTLE_SUB_FORCE_SWITCH:
        res = _try_switch_member(user_id, content, ud, player, allow_cancel=False)
        if res["success"]:
            ctx["sub_state"] = BATTLE_SUB_MAIN
            target = res["target"]
            if "battle_state" in target: target["battle_state"]["choice_lock"] = None
            if "stat_stages" not in target:
                 target["battle_state"] = {
                    "revived": False, "barrier_hp": 0, "submission_prep": False,
                    "rocket": False, "oblivion_cd": 0, "recharge": False, "choice_lock": None, "form": None
                }
                 target["stat_stages"] = {"atk": 0, "def": 0, "spa": 0, "spd": 0, "spe": 0, "acc": 0, "eva": 0}

            return f"ゆけっ！ {target['nickname']}！\n{get_k_text(user_id, 'cmd_prompt')}", []
        return res["msg"], []

    return get_k_text(user_id, "err_invalid"), []

# --- PvE ターン処理 ---
def _execute_pve_turn(user_id, session, player, enemy, move_id, ud):
    ctx = session["context"]
    ctx["logs"] = []
    mdata = data.MOVES[move_id]
    
    cant_move = False
    if player["battle_state"].get("recharge"):
        ctx["logs"].append(get_k_text(user_id, "log_recharge", name=player['nickname']))
        player["battle_state"]["recharge"] = False
        cant_move = True

    sc = player.get("status_condition")
    if not cant_move and sc == "paralysis" and random.random() < 0.25:
        ctx["logs"].append(get_k_text(user_id, "log_paralyzed_cant_move", name=player['nickname']))
        cant_move = True
    elif not cant_move and sc == "sleep":
        if random.random() < 0.33:
            player["status_condition"] = None
            ctx["logs"].append(get_k_text(user_id, "log_woke_up", name=player['nickname']))
        else:
            ctx["logs"].append(get_k_text(user_id, "log_sleeping", name=player['nickname']))
            cant_move = True
    elif sc == "oblivion" and player.get("last_move") == move_id:
        ctx["logs"].append(get_k_text(user_id, "log_oblivion", name=player['nickname']))
        cant_move = True

    if not cant_move:
        base_name = data.BASE_CHIMERAS[player["base_id"]]["name"]
        if base_name == "オートミール" and mdata["category"] != "Status":
            player["stat_stages"]["spe"] = min(6, player["stat_stages"]["spe"] + 1)
            ctx["logs"].append(get_k_text(user_id, "buff", name="オートミール"))
            
        dmg, type_eff = _calculate_damage(player, enemy, move_id, session)
        if mdata["category"] != "Status":
            enemy["current_hp"] -= dmg
            
            eff_msg = ""
            if type_eff > 1.0: eff_msg = get_k_text(user_id, "eff_super")
            elif type_eff == 0: eff_msg = get_k_text(user_id, "eff_none")
            elif type_eff < 1.0: eff_msg = get_k_text(user_id, "eff_not")
            
            ctx["logs"].append(get_k_text(user_id, "log_hit", atkr=player['nickname'], move=mdata['name'], eff=eff_msg, dmg=dmg))
            
            if player.get("held_item") == "life_orb":
                recoil_orb = max(1, player["stats"]["max_hp"] // 10)
                player["current_hp"] = max(0, player["current_hp"] - recoil_orb)
                ctx["logs"].append("命の珠の反動を受けた！")

            if core.check_survival_item(enemy, dmg):
                enemy["current_hp"] = 1
                ctx["logs"].append(get_k_text(user_id, "log_hung_on", name=enemy['nickname']))
            
            if data.BASE_CHIMERAS[enemy["base_id"]]["name"] == "チョウチョウケーキ":
                ref = max(1, dmg // 10)
                player["current_hp"] = max(0, player["current_hp"] - ref)
                ctx["logs"].append(get_k_text(user_id, "log_reflect", dmg=ref))
                
            if data.BASE_CHIMERAS[enemy["base_id"]]["name"] == "キャンディーロール":
                 if enemy["battle_state"]["oblivion_cd"] == 0:
                     _apply_status_effect(player, "oblivion", session, user_id)
                     enemy["battle_state"]["oblivion_cd"] = 3
                     
            if mdata.get("effect", {}).get("type") == "recoil":
                recoil = int(dmg * mdata["effect"]["percent"])
                player["current_hp"] = max(0, player["current_hp"] - recoil)
                ctx["logs"].append(get_k_text(user_id, "log_recoil", name=player['nickname']))
                
            if mdata.get("effect", {}).get("type") == "recharge":
                player["battle_state"]["recharge"] = True

            if mdata.get("effect", {}).get("type") == "debuff_self":
                stat = mdata["effect"]["stat"]
                player["stat_stages"][stat] = max(-6, player["stat_stages"][stat] - mdata["effect"]["stage"])
                ctx["logs"].append(get_k_text(user_id, "debuff", name=player['nickname']))

        else:
            ctx["logs"].append(get_k_text(user_id, "log_stat", atkr=player['nickname'], move=mdata['name']))
            eff = mdata.get("effect")
            if eff:
                if eff["type"] == "buff":
                    player["stat_stages"][eff["stat"]] = min(6, player["stat_stages"][eff["stat"]] + eff["stage"])
                    ctx["logs"].append(get_k_text(user_id, "buff", name=player['nickname']))
                elif eff["type"] == "debuff":
                    enemy["stat_stages"][eff["stat"]] = max(-6, enemy["stat_stages"][eff["stat"]] - eff["stage"])
                    ctx["logs"].append(get_k_text(user_id, "debuff", name=enemy['nickname']))
                elif eff["type"] == "status":
                    _apply_status_effect(enemy, eff["status"], session, user_id)
                elif eff["type"] == "heal":
                    rec = int(player["stats"]["max_hp"] * eff["percent"])
                    player["current_hp"] = min(player["stats"]["max_hp"], player["current_hp"] + rec)
                    ctx["logs"].append(get_k_text(user_id, "log_self_heal", name=player['nickname']))

            if base_name == "チェリビス":
                ctx["field_effects"]["icarun"]["p1"] = True
                ctx["logs"].append(get_k_text(user_id, "log_icarun_start"))
    
        player["last_move"] = move_id

    if enemy["current_hp"] <= 0: return _handle_enemy_faint(user_id, session, ud, enemy)
    if player["current_hp"] <= 0: return _handle_player_faint(user_id, session, ud, player)

    msg = "\n".join(ctx["logs"]) + "\n"
    msg += _enemy_attack_phase(user_id, session, player, enemy, ud)
    return msg, []

def _enemy_attack_phase(user_id, session, player, enemy, ud):
    ctx = session["context"]
    ctx["logs"] = []
    is_hard = ud.get("is_hard_mode", False)
    
    if enemy["battle_state"].get("recharge"):
        ctx["logs"].append(get_k_text(user_id, "log_recharge", name=f"Enemy {enemy['nickname']}"))
        enemy["battle_state"]["recharge"] = False
        _end_of_turn_effects(session, player, enemy, ud, user_id)
        msg = "\n".join(ctx["logs"])
        return msg + f"\n" + get_k_text(user_id, "log_hp_display", ehp=enemy['current_hp'], php=player['current_hp'])
    
    cant_move = False
    sc = enemy.get("status_condition")
    if sc == "paralysis" and random.random() < 0.25:
        ctx["logs"].append(get_k_text(user_id, "log_paralyzed_cant_move", name=f"Enemy {enemy['nickname']}"))
        cant_move = True
    elif sc == "sleep":
        if random.random() < 0.33:
            enemy["status_condition"] = None
            ctx["logs"].append(get_k_text(user_id, "log_woke_up", name=f"Enemy {enemy['nickname']}"))
        else:
            ctx["logs"].append(get_k_text(user_id, "log_sleeping", name=f"Enemy {enemy['nickname']}"))
            cant_move = True

    if not cant_move:
        potions = ctx.get("potions", 0)
        heal_threshold = 0.5 if is_hard else 0.3
        
        if potions > 0 and enemy["current_hp"] < enemy["stats"]["max_hp"] * heal_threshold:
            ctx["potions"] -= 1
            heal_amt = int(enemy["stats"]["max_hp"] * (0.8 if is_hard else 0.5))
            enemy["current_hp"] = min(enemy["stats"]["max_hp"], enemy["current_hp"] + heal_amt)
            ctx["logs"].append(get_k_text(user_id, "log_potion", name=enemy['nickname']))
        else:
            emove_id = random.choice(enemy["moves"])
            emove = data.MOVES[emove_id]
            
            dmg, type_eff = _calculate_damage(enemy, player, emove_id, session)
            
            if emove["category"] != "Status":
                player["current_hp"] -= dmg
                eff_msg = ""
                if type_eff > 1.0: eff_msg = get_k_text(user_id, "eff_super")
                elif type_eff == 0: eff_msg = get_k_text(user_id, "eff_none")
                elif type_eff < 1.0: eff_msg = get_k_text(user_id, "eff_not")

                ctx["logs"].append(get_k_text(user_id, "log_hit", atkr=f"Enemy {enemy['nickname']}", move=emove['name'], eff=eff_msg, dmg=dmg))
                
                if emove.get("effect", {}).get("type") == "recoil":
                    recoil = int(dmg * emove["effect"]["percent"])
                    enemy["current_hp"] = max(0, enemy["current_hp"] - recoil)
                    ctx["logs"].append(get_k_text(user_id, "log_recoil", name=enemy['nickname']))

                if emove.get("effect", {}).get("type") == "recharge":
                    enemy["battle_state"]["recharge"] = True

                if data.BASE_CHIMERAS[player["base_id"]]["name"] == "チョウチョウケーキ":
                    ref = max(1, dmg // 10)
                    enemy["current_hp"] = max(0, enemy["current_hp"] - ref)
                    ctx["logs"].append(get_k_text(user_id, "log_reflect", dmg=ref))
            else:
                ctx["logs"].append(get_k_text(user_id, "log_stat", atkr=f"Enemy {enemy['nickname']}", move=emove['name']))
                eff = emove.get("effect")
                if eff and eff["type"] == "status":
                    _apply_status_effect(player, eff["status"], session, user_id)
    
    _end_of_turn_effects(session, player, enemy, ud, user_id)
    core.save_user_data(user_id, ud, hard_mode=is_hard)
    msg = "\n".join(ctx["logs"])
    
    if player["current_hp"] <= 0: return msg + "\n" + _handle_player_faint(user_id, session, ud, player)
    if enemy["current_hp"] <= 0: return msg + "\n" + _handle_enemy_faint(user_id, session, ud, enemy)
        
    return msg + f"\n" + get_k_text(user_id, "log_hp_display", ehp=enemy['current_hp'], php=player['current_hp'])

def _end_of_turn_effects(session, player, enemy, ud, user_id):
    ctx = session["context"]
    
    active = ctx["active_synergies"]["p1"]
    for key in active:
        eff = data.TEAM_SYNERGIES[key]["effect"]
        if eff["type"] == "regen" and player["current_hp"] > 0:
            rec = int(player["stats"]["max_hp"] * eff["percent"])
            player["current_hp"] = min(player["stats"]["max_hp"], player["current_hp"] + rec)
            ctx["logs"].append(get_k_text(user_id, "log_synergy_heal", syn=data.TEAM_SYNERGIES[key]['name']))

    if ctx["field_effects"]["icarun"]["p1"] and player["current_hp"] > 0:
        rec = int(player["stats"]["max_hp"] * 0.1)
        player["current_hp"] = min(player["stats"]["max_hp"], player["current_hp"] + rec)
        ctx["logs"].append(get_k_text(user_id, "log_icarun_heal", name=player['nickname']))

    for char in [player, enemy]:
        if char["current_hp"] <= 0: continue
        sc = char.get("status_condition")
        if sc == "poison":
            dmg = char["stats"]["max_hp"] // 8
            char["current_hp"] = max(0, char["current_hp"] - dmg)
            ctx["logs"].append(get_k_text(user_id, "log_poison_hurt", name=char['nickname']))
        elif sc == "burn":
            dmg = char["stats"]["max_hp"] // 16
            char["current_hp"] = max(0, char["current_hp"] - dmg)
            ctx["logs"].append(get_k_text(user_id, "log_burn_hurt", name=char['nickname']))
        
        if "battle_state" in char and char["battle_state"].get("oblivion_cd", 0) > 0:
            char["battle_state"]["oblivion_cd"] -= 1

def _handle_enemy_faint(user_id, session, ud, enemy):
    enemy["current_hp"] = 0
    base_name = data.BASE_CHIMERAS[enemy["base_id"]]["name"]
    if base_name == "ハニーフルーツスープ" and not enemy["battle_state"]["revived"]:
        enemy["current_hp"] = enemy["stats"]["max_hp"] // 2
        enemy["battle_state"]["revived"] = True
        return get_k_text(user_id, "log_revived", name=f"Enemy {enemy['nickname']}")

    msg = get_k_text(user_id, "fainted", name=f"Enemy {enemy['nickname']}")
    
    xp_mult = 150
    is_hard = session.get("is_hard_mode", False)
    if is_hard: xp_mult = 30
    base_xp = (enemy["level"] * xp_mult) + random.randint(0, enemy["level"] * 10)
    
    for p in ud["party"]:
        if p["current_hp"] > 0:
            p["xp"] += base_xp
            if p["xp"] >= p["next_xp"]:
                msg += "\n" + core.level_up_chimera(p, is_hard_mode=is_hard)
    
    msg += f"\nParty gained {base_xp} XP!"
    core.save_user_data(user_id, ud, hard_mode=is_hard)
    
    ctx = session["context"]
    next_enemy = next((c for c in ctx["enemy_party"] if c["current_hp"] > 0), None)
    
    if next_enemy:
        _init_chimera_battle_states(session, "p2")
        msg += f"\nEnemy sent out **{next_enemy['nickname']}** (Lv.{next_enemy['level']})!"
        return msg, []
    else:
        return _resolve_pve_win(user_id, session, ud)

def _handle_player_faint(user_id, session, ud, player):
    player["current_hp"] = 0
    base_name = data.BASE_CHIMERAS[player["base_id"]]["name"]
    if base_name == "オートミール":
        session["context"]["field_effects"]["aglaia_speed"]["p1"] = player["stat_stages"]["spe"]

    msg = get_k_text(user_id, "fainted", name=player['nickname'])
    
    if any(c["current_hp"] > 0 for c in ud["party"]):
        session["context"]["sub_state"] = BATTLE_SUB_FORCE_SWITCH
        msg += "\n" + get_k_text(user_id, "cmd_switch", party=_generate_party_list(ud))
    else:
        lost = int(ud["money"] * 0.1)
        ud["money"] -= lost
        core.heal_all_kimeras(ud)
        core.save_user_data(user_id, ud, hard_mode=session.get("is_hard_mode", False))
        
        session["state"] = STATE_MENU
        session["context"] = {}
        msg += get_k_text(user_id, "lose_pve", lost=lost)
    
    return msg

def _resolve_pve_win(user_id, session, ud):
    msg = ""
    base_money = 1000
    trainer_xp = 500
    is_hard = session.get("is_hard_mode", False)
    
    if session["state"] == STATE_BATTLE_CHALLENGE:
        st = session["context"]["stage"]
        trainer_source = data.CHALLENGE_TRAINERS_HARD if is_hard else data.CHALLENGE_TRAINERS
        t_data = trainer_source[st]
        
        win_msg = t_data.get("dialogue_win", "Well done...")
        msg += f"\n**{t_data['name']}**: \"{win_msg}\"\n"
        
        ud["challenge_stage"] = st + 1
        base_money = st * 5000
        trainer_xp = st * 1000
        
        if st == 13:
            reward_item = t_data.get("reward_item")
            if reward_item and reward_item not in ud["items"]:
                ud["items"][reward_item] = 1
                msg += f"\n『{data.ITEMS[reward_item]['name']}』を手に入れた！\n"
        
        if st == 14:
             reward_title = t_data.get("reward_title", "制作者泣かせ")
             msg += f"\n🏆 称号獲得: **{reward_title}**\n"
             if reward_title not in ud["titles"]: ud["titles"].append(reward_title)

    ud["money"] += base_money
    ud["trainer_xp"] += trainer_xp
    
    leveled = False
    while ud["trainer_xp"] >= ud["trainer_level"] * 500:
        ud["trainer_xp"] -= ud["trainer_level"] * 500
        ud["trainer_level"] += 1
        leveled = True
    
    core.save_user_data(user_id, ud, hard_mode=is_hard)
    
    msg += get_k_text(user_id, "win_pve", money=base_money, xp=trainer_xp)
    if leveled: msg += get_k_text(user_id, "win_level_up", lv=ud['trainer_level'])
    
    logic.add_affection_xp(user_id, 50)
    msg += get_k_text(user_id, "win_aff_xp")
    
    session["state"] = STATE_MENU
    session["context"] = {}
    
    return msg + "\n\n" + get_k_text(user_id, "menu_prompt"), []

# --- 共通ヘルパー ---
def _generate_party_list(ud):
    return "\n".join([f"{i+1}. {c['nickname']} ({c['current_hp']}/{c['stats']['max_hp']})" for i, c in enumerate(ud['party'])])

def _try_switch_member(user_id, content, ud, current, allow_cancel):
    try:
        m = re.search(r'\d+', content)
        if m:
            idx = int(m.group(0)) - 1
            if 0 <= idx < len(ud["party"]):
                target = ud["party"][idx]
                if target["current_hp"] <= 0: return {"success": False, "msg": "そのキメラは戦えないわ！"}
                if target == current and allow_cancel: return {"success": False, "msg": "既に出ているわ！"}
                
                ud["party"][0], ud["party"][idx] = ud["party"][idx], ud["party"][0]
                
                session = KIMERA_SESSIONS[user_id]
                speed_boost = session["context"]["field_effects"]["aglaia_speed"]["p1"]
                if speed_boost > 0:
                    if "stat_stages" not in target: target["stat_stages"] = {"atk":0,"def":0,"spa":0,"spd":0,"spe":0,"acc":0,"eva":0}
                    target["stat_stages"]["spe"] = min(6, target["stat_stages"]["spe"] + speed_boost)
                    session["context"]["field_effects"]["aglaia_speed"]["p1"] = 0
                
                if data.BASE_CHIMERAS[target["base_id"]]["name"] == "温厚な竜":
                    if "battle_state" not in target: target["battle_state"] = {}
                    target["battle_state"]["barrier_hp"] = int(target["stats"]["def"] * 0.6)

                core.save_user_data(user_id, ud, hard_mode=session.get("is_hard_mode", False))
                return {"success": True, "target": target}
    except:
        pass
    return {"success": False, "msg": "番号を指定してね。"}

# --- アイテム使用 (戦闘中) ---
def use_item_in_battle(user_id, session, item_key, ud, player, enemy):
    item = data.ITEMS[item_key]
    is_hard = session.get("is_hard_mode", False)
    
    if item["effect_type"] == "capture":
        if session["state"] != STATE_BATTLE_WILD: return get_k_text(user_id, "err_cant_use")
        if ud["items"].get(item_key, 0) <= 0: return get_k_text(user_id, "err_no_item")
        
        ud["items"][item_key] -= 1
        if ud["items"][item_key] <= 0: del ud["items"][item_key]
        
        rarity_mod = 1.0 - (enemy.get("rarity", 1) * 0.1)
        rate = ((1 - (enemy["current_hp"]/enemy["stats"]["max_hp"])) * 0.8 + 0.2) * item["value"] * rarity_mod
        
        if enemy.get("status_condition"): rate *= 1.5
        if enemy.get("status_condition") == "submission": rate *= 2.0

        if random.random() < rate:
            core.update_chimera_stats(enemy)
            enemy["current_hp"] = enemy["stats"]["max_hp"]
            
            if len(ud["party"]) < 3: ud["party"].append(enemy)
            else: ud["box"].append(enemy)
            
            core.register_dex(ud, enemy["base_id"], caught=True)
            core.save_user_data(user_id, ud, hard_mode=is_hard)
            logic.add_affection_xp(user_id, 50)
            
            session["state"] = STATE_MENU
            session["context"] = {}
            return get_k_text(user_id, "catch_success", name=enemy['nickname']), []
        else:
            core.save_user_data(user_id, ud, hard_mode=is_hard)
            session["context"]["sub_state"] = BATTLE_SUB_MAIN
            msg = get_k_text(user_id, "catch_fail") + "\n"
            msg += _enemy_attack_phase(user_id, session, player, enemy, ud)
            return msg

    elif item["effect_type"] == "heal":
        if ud["items"].get(item_key, 0) <= 0: return get_k_text(user_id, "err_no_item")
        ud["items"][item_key] -= 1
        if ud["items"][item_key] <= 0: del ud["items"][item_key]
        
        player["current_hp"] = min(player["stats"]["max_hp"], player["current_hp"] + item["value"])
        core.save_user_data(user_id, ud, hard_mode=is_hard)
        
        session["context"]["sub_state"] = BATTLE_SUB_MAIN
        msg = f"回復したわ！\n"
        msg += _enemy_attack_phase(user_id, session, player, enemy, ud)
        return msg

    return get_k_text(user_id, "err_cant_use")

# --- PvP ---
def handle_pvp_lobby(user_id, content):
    m = re.search(r"<@!?(\d+)>", content)
    if m:
        target_id = int(m.group(1))
        if target_id == user_id: return "自分とは戦えないわ。", []
        PVP_CHALLENGES[target_id] = user_id
        return f"<@{target_id}> に挑戦状を送ったわ！", [(target_id, f"**{user_id}** から挑戦状が届いたわよ！")]
    if "キャンセル" in content:
        end_session(user_id)
        return "キャンセルしたわ。", []
    return "相手をメンションしてね。", []

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
    c1 = ud1["party"][0]; c2 = ud2["party"][0]
    
    msg1 = get_k_text(p1, "pvp_start", name=c2['nickname'], lv=c2['level'])
    msg2 = get_k_text(p2, "pvp_start", name=c1['nickname'], lv=c1['level'])
    return msg2, [(p1, msg1)]

def handle_pvp_action(user_id, content):
    session = KIMERA_SESSIONS[user_id]
    ctx = session["context"]
    battle = PVP_BATTLES.get(ctx["battle_id"])
    if not battle:
        session["state"] = STATE_MENU
        return "対戦は終了しているわ。", []
    
    is_hard = session.get("is_hard_mode", False)
    ud = core.get_user_data(user_id, hard_mode=is_hard)
    player_chimera = ud['party'][0]
    sub = ctx.get("sub_state", BATTLE_SUB_MAIN)

    if sub == BATTLE_SUB_WAIT:
        return "相手の入力を待っているわ...", []

    if sub == BATTLE_SUB_MAIN:
        if "降参" in content:
            return _resolve_pvp_end(battle, loser_id=user_id)

        if "戦" in content:
            moves_txt = " / ".join([f"{data.MOVES[m]['name']}" for m in player_chimera["moves"]])
            return f"技を選んでね:\n[{moves_txt}]", []

        selected_move = None
        for mid in player_chimera["moves"]:
            if data.MOVES[mid]["name"] in content:
                selected_move = mid
                break
        
        if selected_move:
            battle["actions"][user_id] = {"type": "move", "value": selected_move}
            ctx["sub_state"] = BATTLE_SUB_WAIT
            return _check_pvp_turn_ready(battle)

        return get_k_text(user_id, "cmd_prompt"), []
    return "...", []

def _check_pvp_turn_ready(battle):
    if battle["p1"] in battle["actions"] and battle["p2"] in battle["actions"]:
        return _resolve_pvp_turn(battle)
    else:
        return "相手の入力を待っているわ...", []

def _resolve_pvp_turn(battle):
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
            dmg = int(mdata["power"] * (actor_c["stats"]["atk"] / target_c["stats"]["def"]) * 0.4)
            if dmg < 1: dmg = 1
            
            target_c["current_hp"] -= dmg
            logs.append(f"**{actor_c['nickname']}** used {mdata['name']}! {target_c['nickname']} took {dmg} dmg!")
            
            if target_c["current_hp"] <= 0:
                target_c["current_hp"] = 0
                logs.append(f"**{target_c['nickname']}** fainted!")
                
    battle["actions"] = {}
    full_log = "\n".join(logs)
    
    loser = None
    if c1["current_hp"] <= 0 and c2["current_hp"] <= 0:
        _end_pvp(battle)
        msg = f"{full_log}\n\nDraw!"
        return "", [(p1, msg), (p2, msg)]

    if c1["current_hp"] <= 0: loser = p1
    elif c2["current_hp"] <= 0: loser = p2
    
    if loser:
        _end_pvp(battle)
        winner = p2 if loser == p1 else p1
        msg = f"{full_log}\n\nWinner: <@{winner}>!"
        KIMERA_SESSIONS[p1]["state"] = STATE_MENU; KIMERA_SESSIONS[p2]["state"] = STATE_MENU
        KIMERA_SESSIONS[p1]["context"]["sub_state"] = BATTLE_SUB_MAIN
        KIMERA_SESSIONS[p2]["context"]["sub_state"] = BATTLE_SUB_MAIN
        return "", [(p1, msg), (p2, msg)]

    KIMERA_SESSIONS[p1]["context"]["sub_state"] = BATTLE_SUB_MAIN
    KIMERA_SESSIONS[p2]["context"]["sub_state"] = BATTLE_SUB_MAIN
    msg_next = f"{full_log}\n\nNext turn!"
    return "", [(p1, msg_next), (p2, msg_next)]

def _resolve_pvp_end(battle, loser_id):
    p1, p2 = battle["p1"], battle["p2"]
    winner_id = p2 if loser_id == p1 else p1
    _end_pvp(battle)
    msg = f"<@{loser_id}> surrendered.\n<@{winner_id}> wins!"
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
                f"{get_k_text(user_id, 'menu_title')}\n{get_k_text(user_id, 'menu_opts')}\n{get_k_text(user_id, 'menu_prompt')}"
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
    elif st == STATE_MOVE_MANAGE: return handle_move_manage(user_id, content)
    elif st == STATE_BATTLE_SELECT: return handle_battle_select(user_id, content)
    elif st == STATE_BATTLE_PVP_LOBBY: return handle_pvp_lobby(user_id, content)
    elif st in [STATE_BATTLE_WILD, STATE_BATTLE_TRAINER, STATE_BATTLE_CHALLENGE]: return handle_battle_action(user_id, content)
    elif st == STATE_BATTLE_PVP: return handle_pvp_action(user_id, content)
    
    return None