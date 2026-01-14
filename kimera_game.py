# kimera_game.py
import random
import re
import math
import uuid
import asyncio
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
STATE_BATTLE_DPS_SETUP = "battle_dps_setup"
STATE_BATTLE_DPS = "battle_dps"
STATE_BOX = "box_menu"
STATE_EQUIP = "equip_menu"
STATE_MOVE_MANAGE = "move_manage"
STATE_RAID_LOBBY = "raid_lobby"
STATE_RAID_BATTLE = "raid_battle"

# サブステート
BATTLE_SUB_MAIN = "main"
BATTLE_SUB_ITEM = "item"
BATTLE_SUB_SWITCH = "switch"
BATTLE_SUB_FORCE_SWITCH = "force_switch"
BATTLE_SUB_WAIT = "wait"

KIMERA_SESSIONS = {}
PVP_CHALLENGES = {}
PVP_BATTLES = {}
RAID_SESSIONS = {} # {raid_id: {host, members:[], state, boss, turn_inputs, turn_count}}

# --- テキスト辞書 (Localization) ---
GAME_TEXT = {
    "menu_title": {"jp": "【キメラメニュー】", "en": "【Kimera Menu】"},
    "menu_opts": {
        "jp": "・**バトル**: 野生/CPU/対戦/実験/レイド\n・**編成**: 手持ちとボックスの入れ替え\n・**装備**: アイテムを持たせる\n・**技**: 技の入れ替え\n・**詳細**: ステータス確認\n・**ショップ**: ボールや薬を買う\n・**回復**: 全回復する\n・**図鑑**: 出会ったキメラ・技・道具を見る\n・**終了**: ゲームを終わる\n",
        "en": "・**Battle**: Wild/CPU/PvP/Lab/Raid\n・**Party**: Manage Team & Box\n・**Equip**: Equip Items\n・**Moves**: Manage Moves\n・**Status**: Check Stats\n・**Shop**: Buy Items\n・**Heal**: Full Restore\n・**Dex**: Pokedex\n・**Exit**: Quit Game\n"
    },
    "menu_prompt": {"jp": "何をしたいのかしら？", "en": "What would you like to do?"},
    "healed": {"jp": "キメラセンターで手持ちとボックスの子を全回復しておいたわ♪", "en": "I healed all your Kimeras in your party and box at the Center♪"},
    
    "move_title": {"jp": "【技管理】 (対象: {name})", "en": "【Move Management】 ({name})"},
    "move_list": {"jp": "現在の技: {current}\n習得可能: {learned}\n\n『1を覚える』『1を忘れる』『1を忘れて2を覚える』のように言ってね。\n(戻るなら『戻る』)", "en": "Current: {current}\nLearned: {learned}\nSay 'Learn 1', 'Forget 1', or 'Forget 1 Learn 2'."},
    "move_changed": {"jp": "{out} を忘れて {in_} を覚えたわ！", "en": "Forgot {out} and learned {in_}!"},
    "move_learned": {"jp": "{in_} を覚えたわ！", "en": "Learned {in_}!"},
    "move_forgot": {"jp": "{out} を忘れたわ。", "en": "Forgot {out}."},
    
    "items_list": {"jp": "所持: {items}\n(『けいけんアメSを使う』って言ってね♪)", "en": "Owned: {items}\n(Say 'Use exp candy S' to use)"},
    "no_items_to_use": {"jp": "手持ちがいないわね。", "en": "You don't have any Kimeras in your party."},
    
    "shop_welcome": {"jp": "【ショップ】 (所持金: {money}G / Lv.{level})\n{items}\n\n『〇〇を買う』 / 『戻る』 って言ってね♪", "en": "【Shop】 (Money: {money}G / Lv.{level})\n{items}\n\nSay 'Buy [Item Name]' or 'Back'♪"},
    "shop_bought": {"jp": "**{item}** を購入したわ♪ (残: {money}G)", "en": "Bought **{item}**♪ (Rem: {money}G)"},
    "shop_no_money": {"jp": "お金が足りないみたいね。", "en": "You don't have enough money."},
    "shop_low_level": {"jp": "今のレベルじゃまだ買えないわね。", "en": "You need a higher level to buy that."},
    
    "box_title": {"jp": "【パーティ & ボックス】", "en": "【Party & Box】"},
    "box_empty": {"jp": "(空っぽ)", "en": "(Empty)"},
    "box_cmds": {"jp": "『P1とB1を交代』 『P2を預ける』 『B1を入れる』 『戻る』", "en": "'Swap P1 B1', 'Store P2', 'Take B1', 'Back'"},
    
    "equip_title": {"jp": "【装備管理】", "en": "【Equipment Management】"},
    "equip_none": {"jp": "(なし)", "en": "(None)"},
    "equip_cmds": {"jp": "『1にハチマキを持たせる』『2を外す』\n『戻る』", "en": "'Equip Band to 1', 'Unequip 2'\n'Back'"},
    
    "status_trainer": {"jp": "【トレーナー】Lv.{lv} (Exp:{xp}) / {money}G", "en": "【Trainer】Lv.{lv} (Exp:{xp}) / {money}G"},
    "dex_seen": {"jp": "【状態】 目撃のみ (詳細は捕まえてからのお楽しみね♪)", "en": "【Status】 Seen (Catch it to see details♪)"},
    "dex_help": {"jp": "『図鑑 技』『図鑑 アイテム』で一覧が見れるわ。\n『図鑑 [名前]』で詳細検索もできるわよ。", "en": "Try 'Dex Moves' or 'Dex Items'.\nSearch details with 'Dex [Name]'."},
    
    "battle_select_title": {"jp": "どこに行くのかしら？", "en": "Where would you like to go?"},
    "battle_opts": {
        "jp": "1. **確保ゾーン** (野生捕獲)\n2. **レベル上げゾーン** (CPU戦)\n3. **{mode_text}** (黄金裔13人抜き)\n4. **対戦ゾーン** (PvP)\n5. **実験場** (DPS/検証)\n6. **レイドバトル** (協力プレイ)",
        "en": "1. **Catch Zone** (Wild)\n2. **Training Zone** (CPU)\n3. **{mode_text}** (Challenge)\n4. **PvP Zone** (Versus)\n5. **Lab** (DPS/Test)\n6. **Raid Battle** (Co-op)"
    },
    "hard_mode_warning": {
        "jp": "【警告: 真なるキメラマスターロード解放】\n\n世界が反転し、黄金裔たちの真の力が解放されたわ……。\nこれより『ハードモード』のセーブデータに切り替えるわね。\n敵は神の個体値を持ち、全力で牙を剥くわ。\n準備はいい？ 死にゲーの始まりよ♪",
        "en": "【Warning: True Kimera Master Road Unlocked】\n\nSwitching to 'Hard Mode'. Enemies use full power with max stats.\nPrepare for death♪"
    },
    
    # Raid
    "raid_menu": {"jp": "【レイドバトル】\n最大4人で強力なボスに挑むわよ！\n報酬は3V確定の強力なキメラ！\n\n・『募集』: 部屋を作る\n・『参加 [ID]』: 部屋に入る\n・『戻る』", "en": "【Raid Battle】\nCo-op with 4 players!\nRewards: 3V Chimera!\n\n・'Create': Host room\n・'Join [ID]': Join room\n・'Back'"},
    "raid_created": {"jp": "レイド部屋を作成したわ！ (ID: **{id}**)\n他の人は『参加 {id}』と言ってね。\n集まったら『開始』よ！", "en": "Raid room created! (ID: **{id}**)\nOthers say 'Join {id}'.\nSay 'Start' when ready!"},
    "raid_joined": {"jp": "レイド部屋 {id} に参加したわ！\n現在の参加者: {members}", "en": "Joined raid {id}!\nMembers: {members}"},
    "raid_started": {"jp": "レイドバトル開始！\nBOSS: **{name}** (HP: {hp}) が現れた！\n(素早さ順で行動するわよ！)", "en": "Raid Start!\nBOSS: **{name}** (HP: {hp}) appeared!"},
    "raid_win": {"jp": "やったわ！ ボスを討伐したわよ！\n報酬として **{reward}** をゲットしたわ！\n(個体値3V以上確定！)", "en": "We won! You got **{reward}**!\n(Guaranteed 3V!)"},
    "raid_lose": {"jp": "全滅しちゃったわね…強すぎたかしら…。", "en": "We were wiped out..."},
    "raid_turn_wait": {"jp": "他のプレイヤーの入力を待っているわ… ({count}/4)", "en": "Waiting for others... ({count}/4)"},
    "raid_dead": {"jp": "やられちゃった…！ でも諦めないで！\n『応援 攻撃』『応援 防御』『応援 回復』『応援 気合』で味方を支援して！", "en": "You are down! Support your team!\n'Cheer Atk', 'Cheer Def', 'Cheer Heal', 'Cheer Spirit'"},
    
    # DPS / Lab
    "dps_welcome": {"jp": "【実験場】へようこそ。\n敵を設定してダメージ検証ができるわ。\n『敵 [名前] Lv.[数字] HP倍率.[数字]』\n例: 『敵 キュレネ Lv.50 HP倍率.10』", 
                    "en": "Welcome to the Lab.\nSet up dummy: 'Enemy [Name] Lv.[Val] HPx.[Val]'"},
    "dps_start": {"jp": "実験開始よ！ 相手: **{name}** (Lv.{lv}, HP倍率 x{hpm})", "en": "Lab Start! Target: **{name}** (Lv.{lv}, HPx{hpm})"},
    
    # Battle Events
    "wild_appear": {"jp": "野生の **{name}** (Lv.{lv}) {star} が飛び出してきたわ！\n(HP補正: x{hp_mult})\n『戦う』『道具』『入れ替え』『逃げる』", "en": "A wild **{name}** (Lv.{lv}) {star} appeared!\n(HP x{hp_mult})\n'Fight', 'Bag', 'Switch', 'Run'"},
    "trainer_appear": {"jp": "黄金裔の幻影が現れたわ！ **{name}** (Lv.{lv}) を繰り出してきたわよ！", "en": "A Golden Phantom appeared! Sent out **{name}** (Lv.{lv})!"},
    "challenge_start": {"jp": "【チャレンジモード Stage {stage}】\n**{name}**: 「{msg}」\n相手は **{poke}** (Lv.{lv}) を繰り出してきたわ！", "en": "【Challenge Mode Stage {stage}】\n**{name}**: \"{msg}\"\nOpponent sent out **{poke}** (Lv.{lv})!"},
    "pvp_start": {"jp": "対戦開始！ 相手は **{name}** (Lv.{lv}) よ！\nどうする？ 『戦う』 『降参』", "en": "PvP Start! Opponent is **{name}** (Lv.{lv})!\nWhat will you do? 'Fight', 'Surrender'"},
    
    # Battle Actions & Prefixes
    "prefix_enemy": {"jp": "敵の ", "en": "Enemy "}, 
    "cmd_prompt": {"jp": "どうするの？", "en": "What will you do?"},
    "cmd_bag": {"jp": "道具: {items}\n(戻るなら『戻る』)", "en": "Bag: {items}\n(Say 'Back' to return)"},
    "cmd_switch": {"jp": "誰と入れ替える？(番号)\n{party}", "en": "Switch with whom? (Number)\n{party}"},
    "cmd_moves": {"jp": "技: {moves}", "en": "Moves: {moves}"},
    "run_success": {"jp": "逃げ出したわ♪\n\n(メニューに戻りました)", "en": "Got away safely♪\n\n(Returned to menu)"},
    "run_fail": {"jp": "チャレンジモードからは逃げられないわよ！", "en": "You can't run from a Challenge Battle!"},
    
    # Battle Logs
    "log_hit": {"jp": "{atkr} の {move}！{eff} **{dmg}** ダメージ！", "en": "{atkr} used {move}!{eff} **{dmg}** damage!"},
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
    "log_hp_bar": {"jp": "\n{p_name}: {p_hp}/{p_max} {p_bar}\n{e_name}: {e_hp}/{e_max} {e_bar}", "en": "\n{p_name}: {p_hp}/{p_max} {p_bar}\n{e_name}: {e_hp}/{e_max} {e_bar}"},
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
    "win_dps": {"jp": "実験終了よ！ お疲れ様♪\n(メニューに戻りました)", "en": "Lab test finished!\n(Returned to menu)"}
}

def get_k_text(user_id, key, **kwargs):
    lang = db.get_user_lang(user_id)
    if not lang or lang == "en": lang = "jp"
    
    text_map = GAME_TEXT.get(key, {})
    tmpl = text_map.get(lang, text_map.get("jp", ""))
    if not tmpl and "jp" in text_map: tmpl = text_map["jp"]
    if not tmpl: return str(key)
    
    return tmpl.format(**kwargs)

# --- 基本ヘルパー関数 ---

def get_session(user_id):
    return KIMERA_SESSIONS.get(user_id)

def start_session(user_id):
    KIMERA_SESSIONS[user_id] = {
        "state": STATE_MENU, 
        "context": {},
        "is_hard_mode": False 
    }
    core.get_user_data(user_id, hard_mode=False)

def _leave_raid_lobby(user_id):
    rid = KIMERA_SESSIONS[user_id]["context"].get("raid_id")
    if rid and rid in RAID_SESSIONS:
        sess = RAID_SESSIONS[rid]
        if user_id in sess["members"]: sess["members"].remove(user_id)
        if not sess["members"]: del RAID_SESSIONS[rid]
        KIMERA_SESSIONS[user_id]["context"].pop("raid_id", None)

def end_session(user_id):
    if user_id in KIMERA_SESSIONS:
        if KIMERA_SESSIONS[user_id]["state"] == STATE_RAID_LOBBY:
            _leave_raid_lobby(user_id)
        if KIMERA_SESSIONS[user_id]["state"] == STATE_BATTLE_PVP_LOBBY:
            to_del = [k for k, v in PVP_CHALLENGES.items() if v == user_id]
            for k in to_del: del PVP_CHALLENGES[k]
        del KIMERA_SESSIONS[user_id]

def _draw_hp_bar(current, max_val, length=10):
    if max_val <= 0: pct = 0
    else: pct = max(0.0, min(1.0, current / max_val))
    filled = int(length * pct)
    empty = length - filled
    bar = "█" * filled + "-" * empty
    return f"[{bar}]"

def _get_level_limit(user_id):
    normal_ud = core.get_user_data(user_id, hard_mode=False)
    if "story_page_2" not in normal_ud["items"]: return 100 
    hard_ud = core.get_user_data(user_id, hard_mode=True)
    stage = hard_ud.get("challenge_stage", 1)
    if stage >= 15: return 999999
    elif stage >= 14: return 2000
    else: return 200

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
    except: pass
    return {"success": False, "msg": "番号を指定してね。"}

def _distribute_raid_rewards(sess):
    msgs = []
    boss_base_id = sess["boss"]["base_id"]
    for uid in sess["members"]:
        is_hard = KIMERA_SESSIONS.get(uid, {}).get("is_hard_mode", False)
        
        reward_c = core.create_chimera_instance(boss_base_id, level=1)
        stats_keys = ["hp", "atk", "def", "spa", "spd", "spe"]
        v_stats = random.sample(stats_keys, 3)
        for s in v_stats: reward_c["ivs"][s] = 31
        
        is_rare = random.random() < 0.1
        rare_txt = ""
        if is_rare:
            raid_move = random.choice(list(data.RAID_MOVES.keys()))
            reward_c["moves"].insert(0, raid_move)
            if len(reward_c["moves"]) > 4: reward_c["moves"].pop()
            raid_abil = random.choice(list(data.RAID_ABILITIES.keys()))
            reward_c["ability"] = f"{data.RAID_ABILITIES[raid_abil]['name']} (Rare!)"
            rare_txt = "✨ **特別個体ゲット！** (専用技・特性持ち)"
        
        core.update_chimera_stats(reward_c)
        reward_c["current_hp"] = reward_c["stats"]["max_hp"]
        
        ud = core.get_user_data(uid, hard_mode=is_hard)
        if len(ud["party"]) < 3: ud["party"].append(reward_c)
        else: ud["box"].append(reward_c)
        core.register_dex(ud, boss_base_id, caught=True)
        core.save_user_data(uid, ud, hard_mode=is_hard)
        msgs.append(f"<@{uid}>: {data.BASE_CHIMERAS[boss_base_id]['name']} を獲得！ {rare_txt}")
    return msgs

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

def _init_chimera_battle_states(session, side, ud=None, enemy_party=None):
    party = []
    if side == "p1":
        if ud: party = ud["party"]
    else:
        party = enemy_party if enemy_party else session["context"]["enemy_party"]
    for c in party:
        c["battle_state"] = {
            "revived": False, "barrier_hp": 0, "submission_prep": False,
            "rocket": False, "oblivion": None, "recharge": False, "choice_lock": None, "form": None
        }
        c["stat_stages"] = {"atk": 0, "def": 0, "spa": 0, "spd": 0, "spe": 0, "acc": 0, "eva": 0}
        base = data.BASE_CHIMERAS[c["base_id"]]
        if base["name"] == "キュヌレ":
            session["context"]["field_effects"]["remembrance"][side] = 24

def _init_battle_context(session, enemy_party, enemy_name, stage=None, potions=0, ud=None):
    session["context"] = {
        "enemy_party": enemy_party, "enemy_name": enemy_name, "stage": stage,
        "sub_state": BATTLE_SUB_MAIN, "potions": potions, "turn_count": 0,
        "field_effects": {
            "icarun": {"p1": False, "p2": False}, "kyurene_ghost": {"p1": False, "p2": False},
            "embers": {"p1": 0, "p2": 0}, "remembrance": {"p1": 0, "p2": 0}, "aglaia_speed": {"p1": 0, "p2": 0},
        },
        "active_synergies": {"p1": [], "p2": []}, "logs": []
    }
    if ud:
        _init_chimera_battle_states(session, "p1", ud=ud)
        _apply_team_synergies(session, "p1", ud["party"])
    _init_chimera_battle_states(session, "p2", enemy_party=enemy_party)

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
        if cond == "poison" and target_status == "poison": power = int(power * mult)
        elif cond == "any_status" and target_status is not None: power = int(power * mult)
    def get_stage_mult(stage): return max(2, 2 + stage) / max(2, 2 - stage)
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
        if base_def["type"] in eff_dict: type_eff = eff_dict[base_def["type"]]
    dmg = int(dmg * type_eff)
    if attacker.get("status_condition") == "submission": dmg = int(dmg * 0.75)
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
        if "battle_state" in char:
            oblv = char["battle_state"].get("oblivion")
            if oblv and isinstance(oblv, int) and oblv > 0:
                char["battle_state"]["oblivion"] -= 1
                if char["battle_state"]["oblivion"] <= 0: char["battle_state"]["oblivion"] = None

def _resolve_pve_win(user_id, session, ud, pre_logs=""):
    msg = pre_logs
    base_money = 1000
    trainer_xp = 500
    is_hard = session.get("is_hard_mode", False)
    if session["state"] == STATE_BATTLE_CHALLENGE:
        st = session["context"]["stage"]
        if st == 14 and is_hard:
             t_data = {"name": "aeracero", "dialogue_win": "見事だ……。君こそ真のキメラマスターだ。"}
        else:
             trainer_source = data.CHALLENGE_TRAINERS_HARD if is_hard else data.CHALLENGE_TRAINERS
             t_data = trainer_source.get(st, {})
        win_msg = t_data.get("dialogue_win", "Well done...")
        msg += f"\n**{t_data.get('name', 'Unknown')}**: \"{win_msg}\"\n"
        ud["challenge_stage"] = st + 1
        base_money = st * 5000
        trainer_xp = st * 1000
        if is_hard:
             if st == 13: msg += "\n🔓 **レベル上限解放**: Lv.2000まで育成可能になったわ！\n"
             if st == 14:
                 msg += "\n🔓 **レベル上限撤廃**: レベルの枷は外されたわ！無限の彼方へ！\n"
                 new_unlocks = logic.check_all_achievements(user_id)
                 if new_unlocks: msg += "\n" + "\n".join(new_unlocks)
        else:
            if st == 14:
                reward_title = t_data.get("reward_title")
                if reward_title:
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

def _handle_enemy_faint(user_id, session, ud, enemy, pre_logs=""):
    enemy["current_hp"] = 0
    base_name = data.BASE_CHIMERAS[enemy["base_id"]]["name"]
    if base_name == "ハニーフルーツスープ" and not enemy["battle_state"]["revived"]:
        enemy["current_hp"] = enemy["stats"]["max_hp"] // 2
        enemy["battle_state"]["revived"] = True
        return pre_logs + get_k_text(user_id, "log_revived", name=f"{get_k_text(user_id, 'prefix_enemy')}{enemy['nickname']}")
    msg = pre_logs + get_k_text(user_id, "fainted", name=f"{get_k_text(user_id, 'prefix_enemy')}{enemy['nickname']}")
    if session["state"] == STATE_BATTLE_DPS:
        session["state"] = STATE_MENU
        session["context"] = {}
        return msg + "\n\n" + get_k_text(user_id, "win_dps"), []
    xp_mult = 150
    is_hard = session.get("is_hard_mode", False)
    if is_hard: xp_mult = 30
    base_xp = (enemy["level"] * xp_mult) + random.randint(0, enemy["level"] * 10)
    lv_limit = _get_level_limit(user_id)
    for p in ud["party"]:
        if p["current_hp"] > 0:
            p["xp"] += base_xp
            if p["xp"] >= p["next_xp"]:
                msg += "\n" + core.level_up_chimera(p, is_hard_mode=is_hard, limit=lv_limit)
    msg += f"\nParty gained {base_xp} XP!"
    core.save_user_data(user_id, ud, hard_mode=is_hard)
    ctx = session["context"]
    next_enemy = next((c for c in ctx["enemy_party"] if c["current_hp"] > 0), None)
    if next_enemy:
        _init_chimera_battle_states(session, "p2")
        prefix = get_k_text(user_id, "prefix_enemy")
        msg += f"\n{prefix}sent out **{next_enemy['nickname']}** (Lv.{next_enemy['level']})!"
        return msg, []
    else: return _resolve_pve_win(user_id, session, ud, msg)

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
        if session["state"] == STATE_BATTLE_DPS:
            core.heal_all_kimeras(ud)
            core.save_user_data(user_id, ud, hard_mode=session.get("is_hard_mode", False))
            session["state"] = STATE_MENU
            session["context"] = {}
            return msg + "\n\n" + get_k_text(user_id, "win_dps"), []
        lost = int(ud["money"] * 0.1)
        ud["money"] -= lost
        core.heal_all_kimeras(ud)
        core.save_user_data(user_id, ud, hard_mode=session.get("is_hard_mode", False))
        session["state"] = STATE_MENU
        session["context"] = {}
        msg += get_k_text(user_id, "lose_pve", lost=lost)
    return msg

def _start_raid_battle(raid_id):
    sess = RAID_SESSIONS[raid_id]
    sess["state"] = "battle"
    boss_base = random.choice(data.RAID_BOSS_CANDIDATES)
    boss = core.create_chimera_instance(boss_base, level=100)
    # Boss HP adjustment: 10000
    boss["stats"]["max_hp"] = 10000 
    boss["current_hp"] = boss["stats"]["max_hp"]
    for k in ["atk", "def", "spa", "spd", "spe"]: boss["stats"][k] = int(boss["stats"][k] * 2.0)
    boss["moves"] = random.sample(list(data.RAID_MOVES.keys()), 2) + boss["moves"][:2]
    boss["ability"] = random.choice(list(data.RAID_ABILITIES.keys()))
    sess["boss"] = boss
    msgs = []
    start_msg = get_k_text(sess["host"], "raid_started", name=boss["nickname"], hp=boss["stats"]["max_hp"])
    for uid in sess["members"]:
        KIMERA_SESSIONS[uid]["state"] = STATE_RAID_BATTLE
        ud = core.get_user_data(uid, hard_mode=KIMERA_SESSIONS[uid].get("is_hard_mode",False))
        pc = ud["party"][0]
        pc["battle_state"] = {"recharge":False, "oblivion":None}
        pc["stat_stages"] = {"atk":0,"def":0,"spa":0,"spd":0,"spe":0,"acc":0,"eva":0}
        msgs.append((uid, start_msg + "\n" + get_k_text(uid, "cmd_prompt")))
    return start_msg + "\n" + get_k_text(sess["host"], "cmd_prompt"), msgs[1:]

def _execute_raid_turn(raid_id):
    sess = RAID_SESSIONS[raid_id]
    boss = sess["boss"]
    members = sess["members"]
    inputs = sess["turn_inputs"]
    sess["turn_inputs"] = {}
    sess["turn_count"] += 1
    logs = [f"--- Turn {sess['turn_count']} ---"]
    actions = []
    
    for uid in members:
        ud = core.get_user_data(uid, hard_mode=KIMERA_SESSIONS[uid].get("is_hard_mode",False))
        pc = ud["party"][0]
        cmd = inputs.get(uid)
        if cmd:
            speed = pc["stats"]["spe"]
            if cmd["type"] == "cheer": speed = 9999
            actions.append({"uid": uid, "unit": pc, "cmd": cmd, "speed": speed, "is_player": True})
            
    boss_speed = boss["stats"]["spe"]
    actions.append({"unit": boss, "cmd": {"type": "boss_atk"}, "speed": boss_speed, "is_player": False})
    
    # Speed sorting logic: descending order
    actions.sort(key=lambda x: x["speed"], reverse=True)
    
    for act in actions:
        if act["is_player"]:
            unit = act["unit"]
            cmd = act["cmd"]
            uid = act["uid"]
            if cmd["type"] == "cheer":
                eff_data = data.CHEER_EFFECTS[cmd["value"]]
                logs.append(f"**{unit['nickname']}** (霊体) の {eff_data['name']}！")
                eff = eff_data["effect"]
                if eff["type"] == "buff_all":
                    stat = eff["stat"]
                    for m_uid in members:
                        # Apply to in-memory check
                        pass 
                    logs.append(eff_data["msg"])
                    # Save to DB
                    for m_uid in members:
                        is_hard = KIMERA_SESSIONS[m_uid].get("is_hard_mode", False)
                        m_ud = core.get_user_data(m_uid, hard_mode=is_hard)
                        m_pc = m_ud["party"][0]
                        if m_pc["current_hp"] > 0: 
                            m_pc["stat_stages"][stat] = min(6, m_pc["stat_stages"][stat] + 1)
                        core.save_user_data(m_uid, m_ud, hard_mode=is_hard)

                elif eff["type"] == "heal_all":
                    logs.append(eff_data["msg"])
                    for m_uid in members:
                        is_hard = KIMERA_SESSIONS[m_uid].get("is_hard_mode", False)
                        m_ud = core.get_user_data(m_uid, hard_mode=is_hard)
                        m_pc = m_ud["party"][0]
                        if m_pc["current_hp"] > 0:
                            rec = int(m_pc["stats"]["max_hp"] * eff["percent"])
                            m_pc["current_hp"] = min(m_pc["stats"]["max_hp"], m_pc["current_hp"] + rec)
                        core.save_user_data(m_uid, m_ud, hard_mode=is_hard)
                
                elif eff["type"] == "restore_pp":
                    logs.append(eff_data["msg"])
                    # No PP implemented yet, placeholder log

            elif cmd["type"] == "move" and unit["current_hp"] > 0:
                m_id = cmd["value"]
                m_data = data.MOVES[m_id]
                logs.append(f"**{unit['nickname']}** の {m_data['name']}！")
                power = m_data["power"]
                if m_data["category"] == "Physical":
                    atk = unit["stats"]["atk"] * (1.0 + 0.5 * unit["stat_stages"]["atk"])
                    defense = boss["stats"]["def"]
                else:
                    atk = unit["stats"]["spa"] * (1.0 + 0.5 * unit["stat_stages"]["spa"])
                    defense = boss["stats"]["spd"]
                dmg = int((power * atk / defense) * (unit["level"] / 50 + 2))
                boss["current_hp"] -= dmg
                logs.append(f"ボスに **{dmg}** のダメージ！ (残りHP: {max(0, boss['current_hp'])})")
        else:
            if boss["current_hp"] > 0:
                move_id = random.choice(boss["moves"])
                is_raid_move = move_id in data.RAID_MOVES
                m_data = data.RAID_MOVES[move_id] if is_raid_move else data.MOVES[move_id]
                logs.append(f"🔥 **BOSS {boss['nickname']}** の {m_data['name']}！")
                target_type = m_data.get("target", "Enemy")
                targets = []
                if target_type == "AllEnemies":
                    for m_uid in members:
                        is_hard = KIMERA_SESSIONS[m_uid].get("is_hard_mode", False)
                        m_ud = core.get_user_data(m_uid, hard_mode=is_hard)
                        if m_ud["party"][0]["current_hp"] > 0: targets.append((m_uid, m_ud["party"][0]))
                else:
                    alive = []
                    for m_uid in members:
                        is_hard = KIMERA_SESSIONS[m_uid].get("is_hard_mode", False)
                        m_ud = core.get_user_data(m_uid, hard_mode=is_hard)
                        if m_ud["party"][0]["current_hp"] > 0: alive.append((m_uid, m_ud["party"][0]))
                    if alive: targets.append(random.choice(alive))
                
                for t_uid, t in targets:
                    power = m_data["power"]
                    if m_data["category"] == "Physical":
                        atk = boss["stats"]["atk"]
                        defense = t["stats"]["def"] * (1.0 + 0.5 * t["stat_stages"]["def"])
                    elif m_data["category"] == "Special":
                        atk = boss["stats"]["spa"]
                        defense = t["stats"]["spd"] * (1.0 + 0.5 * t["stat_stages"]["spd"])
                    else: atk = 0; defense = 1
                    
                    if m_data["category"] != "Status":
                        dmg = int((power * atk / defense) * (boss["level"] / 50 + 2) * 0.5)
                        t["current_hp"] -= dmg
                        logs.append(f"{t['nickname']} に **{dmg}** ダメージ！")
                        if t["current_hp"] <= 0:
                            t["current_hp"] = 0
                            logs.append(f"{t['nickname']} は倒れた！ (次回から応援のみ可能)")
                    else: logs.append(f"{t['nickname']} は {m_data.get('desc','')} を受けた！")
                    
                    # Apply damage to DB
                    is_hard = KIMERA_SESSIONS[t_uid].get("is_hard_mode", False)
                    t_ud = core.get_user_data(t_uid, hard_mode=is_hard)
                    t_ud["party"][0]["current_hp"] = t["current_hp"]
                    core.save_user_data(t_uid, t_ud, hard_mode=is_hard)

    if boss["current_hp"] <= 0:
        reward_msgs = _distribute_raid_rewards(sess)
        final_log = "\n".join(logs) + "\n\n" + "\n".join(reward_msgs)
        msgs = []
        for uid in members:
            msgs.append((uid, final_log + "\n(メニューに戻りました)"))
            KIMERA_SESSIONS[uid]["state"] = STATE_MENU
            is_hard = KIMERA_SESSIONS[uid].get("is_hard_mode", False)
            ud = core.get_user_data(uid, hard_mode=is_hard)
            ud["party"][0]["current_hp"] = ud["party"][0]["stats"]["max_hp"]
            core.save_user_data(uid, ud, hard_mode=is_hard)
        del RAID_SESSIONS[raid_id]
        return msgs[0][1], msgs[1:]

    all_dead = True
    for m_uid in members:
        is_hard = KIMERA_SESSIONS[m_uid].get("is_hard_mode", False)
        m_ud = core.get_user_data(m_uid, hard_mode=is_hard)
        if m_ud["party"][0]["current_hp"] > 0: all_dead = False; break
            
    if all_dead:
        final_log = "\n".join(logs) + "\n\n💀 **全滅しました...**"
        msgs = []
        for uid in members:
            msgs.append((uid, final_log))
            KIMERA_SESSIONS[uid]["state"] = STATE_MENU
            is_hard = KIMERA_SESSIONS[uid].get("is_hard_mode", False)
            core.heal_all_kimeras(core.get_user_data(uid, hard_mode=is_hard))
        del RAID_SESSIONS[raid_id]
        return msgs[0][1], msgs[1:]

    final_log = "\n".join(logs)
    msgs = []
    for uid in members:
        is_hard = KIMERA_SESSIONS[uid].get("is_hard_mode", False)
        ud = core.get_user_data(uid, hard_mode=is_hard)
        pc = ud["party"][0]
        status_line = f"あなた: {pc['nickname']} HP: {pc['current_hp']}/{pc['stats']['max_hp']}"
        boss_line = f"BOSS: {boss['nickname']} HP: {boss['current_hp']}/{boss['stats']['max_hp']}"
        prompt = get_k_text(uid, "cmd_prompt") if pc["current_hp"] > 0 else get_k_text(uid, "raid_dead")
        msgs.append((uid, f"{final_log}\n\n{boss_line}\n{status_line}\n{prompt}"))
        core.save_user_data(uid, ud, hard_mode=is_hard)

    return msgs[0][1], msgs[1:]

# --- メインハンドラ (依存関数が定義済みなので安全) ---

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
        else: return "指定された番号が正しくないわ。", []
    elif m_learn_only and not m_swap_forget:
        l_idx = int(m_learn_only.group(1)) - 1
        if 0 <= l_idx < len(available):
            if len(c["moves"]) < 4:
                learn_move = available[l_idx]
                c["moves"].append(learn_move)
                core.save_user_data(user_id, ud, hard_mode=session.get("is_hard_mode", False))
                msg = get_k_text(user_id, "move_learned", in_=data.MOVES[learn_move]['name'])
                return msg + "\n\n" + _get_move_manage_text(user_id), []
            else: return "技がいっぱいで覚えられないわ。忘れる技も指定してね。", []
        else: return "指定された番号の技は習得リストにないわ。", []
    elif m_forget_only:
        f_idx = int(m_forget_only.group(1)) - 1
        if 0 <= f_idx < len(c["moves"]):
            if len(c["moves"]) > 1:
                forgot_move = c["moves"].pop(f_idx)
                core.save_user_data(user_id, ud, hard_mode=session.get("is_hard_mode", False))
                msg = get_k_text(user_id, "move_forgot", out=data.MOVES[forgot_move]['name'])
                return msg + "\n\n" + _get_move_manage_text(user_id), []
            else: return "全ての技を忘れることはできないわ。", []
        else: return "指定された番号の技は持っていないわ。", []
    return "『1を忘れて2を覚える』のように指定してね。", []

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
        else: return get_k_text(user_id, "err_no_item"), []
    m = re.search(r"(\d+)(?:を外す| unequip)", content, re.IGNORECASE)
    if m:
        idx = int(m.group(1)) - 1
        res = core.unequip_item_logic(ud, idx)
        core.save_user_data(user_id, ud, hard_mode=is_hard)
        return res + "\n" + _get_equip_menu_text(user_id), []
    return get_k_text(user_id, "equip_cmds"), []

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
    else: msg += get_k_text(user_id, "box_empty")
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
        else: return get_k_text(user_id, "shop_no_money"), []
    return "『〇〇を買う』と言ってね。", []

def handle_battle_select(user_id, content):
    session = KIMERA_SESSIONS[user_id]
    is_hard = session.get("is_hard_mode", False)
    ud = core.get_user_data(user_id, hard_mode=is_hard)
    tlv = ud["trainer_level"]
    content = content.translate(str.maketrans({chr(0xFF10 + i): chr(0x30 + i) for i in range(10)}))
    if "真なるキメラマスターロード" in content:
        if is_hard: return "既にハードモードよ。", []
        normal_ud = core.get_user_data(user_id, hard_mode=False)
        if "story_page_2" in normal_ud["items"]:
            session["is_hard_mode"] = True
            core.get_user_data(user_id, hard_mode=True)
            session["state"] = STATE_MENU
            return get_k_text(user_id, "hard_mode_warning") + "\n\n(メニューに戻りました)", []
        else: return "まだその資格はないみたい。", []
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
        mult_hp = 2.0 if not is_hard else 3.5
        mult_st = 1.2 if not is_hard else 1.8
        wild["stats"]["max_hp"] = int(wild["stats"]["max_hp"] * mult_hp)
        for k in ["atk", "def", "spa", "spd", "spe"]: wild["stats"][k] = int(wild["stats"][k] * mult_st)
        wild["current_hp"] = wild["stats"]["max_hp"]
        session["state"] = STATE_BATTLE_WILD
        _init_battle_context(session, [wild], "Wild Kimera", ud=ud)
        core.register_dex(ud, wild["base_id"], caught=False)
        core.save_user_data(user_id, ud, hard_mode=is_hard)
        rarity_star = "★" * wild.get("rarity", 1)
        return get_k_text(user_id, "wild_appear", name=wild['nickname'], lv=wild['level'], star=rarity_star, hp_mult=mult_hp), []
    if "レベル上げ" in content or "2" in content:
        cpu_base = random.choice(list(data.BASE_CHIMERAS.keys()))
        c_lv = max(5, tlv + random.randint(3, 8))
        cpu_c = core.create_chimera_instance(cpu_base, level=c_lv)
        for k in ["atk", "def", "spa", "spd", "spe"]: cpu_c["stats"][k] = int(cpu_c["stats"][k] * 1.2)
        cpu_c["current_hp"] = cpu_c["stats"]["max_hp"]
        session["state"] = STATE_BATTLE_TRAINER
        _init_battle_context(session, [cpu_c], "Phantom", ud=ud)
        core.register_dex(ud, cpu_c["base_id"], caught=False)
        core.save_user_data(user_id, ud, hard_mode=is_hard)
        return get_k_text(user_id, "trainer_appear", name=cpu_c['nickname'], lv=cpu_c['level']), []
    if "チャレンジ" in content or "3" in content:
        stage = ud.get("challenge_stage", 1)
        if stage > 15: stage = 1; ud["challenge_stage"] = 1; core.save_user_data(user_id, ud, hard_mode=is_hard)
        t_data = None
        if stage == 14 and is_hard:
             t_data = {"name": "aeracero", "party": [{"base_id": "kyunure", "level": 1500, "item": "life_orb", "fixed_iv": 31}, {"base_id": "aglaia", "level": 1500, "item": "choice_specs", "fixed_iv": 31}, {"base_id": "trisbeas", "level": 1500, "item": "leftovers", "fixed_iv": 31}], "dialogue_start": "……よくここまで来たね。", "dialogue_win": "見事だ。", "potions": 10}
        else:
             trainer_source = data.CHALLENGE_TRAINERS_HARD if is_hard else data.CHALLENGE_TRAINERS
             t_data = trainer_source.get(stage)
        if not t_data: return "準備中よ。", []
        enemy_party = []
        for p in t_data["party"]:
            c = core.create_chimera_instance(p["base_id"], p["level"], held_item=p.get("item"), fixed_iv=31 if is_hard else None)
            core.update_chimera_stats(c); c["current_hp"] = c["stats"]["max_hp"]; enemy_party.append(c)
            core.register_dex(ud, c["base_id"], caught=False)
        core.save_user_data(user_id, ud, hard_mode=is_hard)
        session["state"] = STATE_BATTLE_CHALLENGE
        _init_battle_context(session, enemy_party, t_data["name"], stage=stage, potions=t_data.get("potions", 0), ud=ud)
        start_msg = t_data.get("dialogue_start", "Start!")
        return get_k_text(user_id, "challenge_start", stage=stage, name=t_data['name'], msg=start_msg, poke=enemy_party[0]['nickname'], lv=enemy_party[0]['level']), []
    if "対戦" in content or "4" in content:
        challenger = PVP_CHALLENGES.get(user_id)
        if challenger: return _initiate_pvp_battle(challenger, user_id)
        session["state"] = STATE_BATTLE_PVP_LOBBY
        return "対戦相手をメンションしてね。", []
    if "実験" in content or "5" in content:
        session["state"] = STATE_BATTLE_DPS_SETUP
        return get_k_text(user_id, "dps_welcome"), []
    if "レイド" in content or "6" in content:
        session["state"] = STATE_RAID_LOBBY
        return get_k_text(user_id, "raid_menu"), []
    return get_k_text(user_id, "battle_select_title"), []

def handle_raid_lobby(user_id, content):
    if "戻る" in content:
        _leave_raid_lobby(user_id)
        KIMERA_SESSIONS[user_id]["state"] = STATE_MENU
        return get_k_text(user_id, "menu_prompt"), []
    if "募集" in content or "作成" in content:
        _leave_raid_lobby(user_id)
        raid_id = str(random.randint(1000, 9999))
        while raid_id in RAID_SESSIONS: raid_id = str(random.randint(1000, 9999))
        RAID_SESSIONS[raid_id] = {"host": user_id, "members": [user_id], "state": "lobby", "boss": None, "turn_inputs": {}, "turn_count": 0}
        KIMERA_SESSIONS[user_id]["context"]["raid_id"] = raid_id
        return get_k_text(user_id, "raid_created", id=raid_id), []
    if "参加" in content:
        m = re.search(r"(\d{4})", content)
        if not m: return "部屋ID（4桁）を指定してね。", []
        raid_id = m.group(1)
        if raid_id not in RAID_SESSIONS: return "その部屋は見つからないわ。", []
        sess = RAID_SESSIONS[raid_id]
        if sess["state"] != "lobby": return "もう始まっているわ。", []
        if len(sess["members"]) >= 4: return "満員よ。", []
        _leave_raid_lobby(user_id)
        sess["members"].append(user_id)
        KIMERA_SESSIONS[user_id]["context"]["raid_id"] = raid_id
        msgs = []
        member_names = [f"<@{uid}>" for uid in sess["members"]]
        msg = get_k_text(user_id, "raid_joined", id=raid_id, members=", ".join(member_names))
        for mem in sess["members"]:
            if mem != user_id: msgs.append((mem, msg))
        return msg, msgs
    if "開始" in content:
        raid_id = KIMERA_SESSIONS[user_id]["context"].get("raid_id")
        if not raid_id or raid_id not in RAID_SESSIONS: return "部屋に入っていないわ。", []
        sess = RAID_SESSIONS[raid_id]
        if sess["host"] != user_id: return "ホストしか開始できないわ。", []
        return _start_raid_battle(raid_id)
    return get_k_text(user_id, "raid_menu"), []

def handle_raid_battle(user_id, content):
    rid = KIMERA_SESSIONS[user_id]["context"].get("raid_id")
    if not rid or rid not in RAID_SESSIONS:
        KIMERA_SESSIONS[user_id]["state"] = STATE_MENU
        return "レイドセッションが見つからないわ。", []
    sess = RAID_SESSIONS[rid]
    ud = core.get_user_data(user_id, hard_mode=KIMERA_SESSIONS[user_id].get("is_hard_mode",False))
    pc = ud["party"][0]
    cmd = None
    if pc["current_hp"] > 0:
        if "戦" in content or "Fight" in content:
            moves = [data.MOVES[m]['name'] for m in pc["moves"]]
            return get_k_text(user_id, "cmd_moves", moves=", ".join(moves)), []
        for m_id in pc["moves"]:
            if data.MOVES[m_id]["name"] in content:
                cmd = {"type": "move", "value": m_id}; break
        if not cmd and "回復" in content: cmd = {"type": "heal_spam"}
    else:
        for k, v in data.CHEER_EFFECTS.items():
            if v["name"] in content or content.endswith(v["name"][-2:]):
                cmd = {"type": "cheer", "value": k}; break
        if not cmd: return get_k_text(user_id, "raid_dead"), []
    if cmd:
        sess["turn_inputs"][user_id] = cmd
        if len(sess["turn_inputs"]) >= len(sess["members"]): return _execute_raid_turn(rid)
        else: return get_k_text(user_id, "raid_turn_wait", count=len(sess["turn_inputs"])), []
    return get_k_text(user_id, "cmd_prompt"), []

def handle_dps_setup(user_id, content):
    session = KIMERA_SESSIONS[user_id]
    ud = core.get_user_data(user_id, hard_mode=session.get("is_hard_mode", False))
    if "戻る" in content:
        session["state"] = STATE_MENU
        return get_k_text(user_id, "menu_prompt"), []
    t_name = "ウルフパピー"
    t_lv = 50
    t_hp_mult = 50
    m_name = re.search(r"(?:敵|Enemy)\s+([^\s]+)", content)
    m_lv = re.search(r"Lv\.?(\d+)", content, re.IGNORECASE)
    m_hp = re.search(r"(?:HP|hp)(?:倍率|x|X)\.?(\d+)", content)
    if m_name: t_name = m_name.group(1)
    if m_lv: t_lv = int(m_lv.group(1))
    if m_hp: t_hp_mult = int(m_hp.group(1))
    base_id = None
    for k, v in data.BASE_CHIMERAS.items():
        if v["name"] == t_name or v.get("name_en", "").lower() == t_name.lower():
            base_id = k; break
    if not base_id:
        if "おまかせ" in content or "default" in content.lower(): base_id = "wolf_pup"
        else: return "その名前のキメラはいないわ。もう一度教えて？\n(例: 『敵 ウルフパピー』)", []
    enemy = core.create_chimera_instance(base_id, level=t_lv)
    enemy["stats"]["max_hp"] *= t_hp_mult
    enemy["current_hp"] = enemy["stats"]["max_hp"]
    session["state"] = STATE_BATTLE_DPS
    _init_battle_context(session, [enemy], "Target Dummy", ud=ud)
    return get_k_text(user_id, "dps_start", name=enemy['nickname'], lv=t_lv, hpm=t_hp_mult), []

def handle_battle_action(user_id, content):
    session = KIMERA_SESSIONS[user_id]
    if session["state"] == STATE_BATTLE_PVP: return handle_pvp_action(user_id, content)
    if session["state"] == STATE_BATTLE_DPS_SETUP: return handle_dps_setup(user_id, content)
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
        if sel_item: return use_item_in_battle(user_id, session, sel_item, ud, player, enemy), []
        return "アイテムを選んでね。", []
    elif sub == BATTLE_SUB_SWITCH:
        if "戻る" in content:
            ctx["sub_state"] = BATTLE_SUB_MAIN
            return get_k_text(user_id, "cmd_prompt"), []
        res = _try_switch_member(user_id, content, ud, player, allow_cancel=True)
        if res["success"]:
            ctx["sub_state"] = BATTLE_SUB_MAIN
            target = res["target"]
            if "battle_state" in target: target["battle_state"]["choice_lock"] = None
            if "stat_stages" not in target:
                 target["battle_state"] = {"revived": False, "barrier_hp": 0, "submission_prep": False, "rocket": False, "oblivion": None, "recharge": False, "choice_lock": None, "form": None}
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
                 target["battle_state"] = {"revived": False, "barrier_hp": 0, "submission_prep": False, "rocket": False, "oblivion": None, "recharge": False, "choice_lock": None, "form": None}
                 target["stat_stages"] = {"atk": 0, "def": 0, "spa": 0, "spd": 0, "spe": 0, "acc": 0, "eva": 0}
            return f"ゆけっ！ {target['nickname']}！\n{get_k_text(user_id, 'cmd_prompt')}", []
        return res["msg"], []
    return get_k_text(user_id, "err_invalid"), []

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
    if sub == BATTLE_SUB_WAIT: return "相手の入力を待っているわ...", []
    if sub == BATTLE_SUB_MAIN:
        if "降参" in content: return _resolve_pvp_end(battle, loser_id=user_id)
        if "戦" in content:
            moves_txt = " / ".join([f"{data.MOVES[m]['name']}" for m in player_chimera["moves"]])
            return f"技を選んでね:\n[{moves_txt}]", []
        selected_move = None
        for mid in player_chimera["moves"]:
            if data.MOVES[mid]["name"] in content:
                selected_move = mid; break
        if selected_move:
            battle["actions"][user_id] = {"type": "move", "value": selected_move}
            ctx["sub_state"] = BATTLE_SUB_WAIT
            return _check_pvp_turn_ready(battle)
        return get_k_text(user_id, "cmd_prompt"), []
    return "...", []

def handle_menu(user_id, content):
    session = KIMERA_SESSIONS[user_id]
    is_hard = session.get("is_hard_mode", False)
    ud = core.get_user_data(user_id, hard_mode=is_hard)
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
    if "真なるキメラマスターロード" in content:
        if is_hard: return "既にハードモードよ。", []
        normal_ud = core.get_user_data(user_id, hard_mode=False)
        if "story_page_2" in normal_ud["items"]:
            session["is_hard_mode"] = True
            core.get_user_data(user_id, hard_mode=True)
            return get_k_text(user_id, "hard_mode_warning"), []
        else: return "まだその資格はないみたい。", []
    if "ノーマルに戻る" in content:
        if is_hard:
            session["is_hard_mode"] = False
            return "平和な世界（ノーマルモード）のデータに戻したわよ♪", []
        return "既にノーマルモードよ。", []
    norm_content = content.translate(str.maketrans({chr(0xFF10 + i): chr(0x30 + i) for i in range(10)}))
    c_lower = content.lower()
    if "技" in content or "moves" in c_lower:
        session["state"] = STATE_MOVE_MANAGE
        return _get_move_manage_text(user_id), []
    if "バトル" in content or "battle" in c_lower or "3" in norm_content:
        session["state"] = STATE_BATTLE_SELECT
        if "チャレンジ" in content or "3" in norm_content: return handle_battle_select(user_id, content)
        mode_text = "【真・キメラマスターロード】" if is_hard else "チャレンジモード"
        msg = f"{get_k_text(user_id, 'battle_select_title')}\n{get_k_text(user_id, 'battle_opts', mode_text=mode_text)}"
        if not is_hard:
            normal_ud = core.get_user_data(user_id, hard_mode=False)
            if "story_page_2" in normal_ud["items"]: msg += "\n\n★『真なるキメラマスターロード』と言えば、裏世界へ連れて行ってあげるわよ♪"
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
    if "図鑑" in content or "dex" in c_lower:
        if "技" in content or "move" in c_lower:
             m_srch = re.search(r"(?:技|moves)\s+(.+)", content)
             if m_srch:
                 t_move = m_srch.group(1).strip()
                 found = None
                 for k, v in data.MOVES.items():
                     if v["name"] == t_move: found = v; break
                 if found:
                     cat = found['category']
                     return f"📖 **{found['name']}** ({cat})\nType: {found['type']} / Power: {found['power']} / Acc: {found.get('accuracy', 100)}\nEffect: {found.get('desc', 'なし')}", []
                 return "その技は見つからないわ。", []
             move_list = sorted([v['name'] for v in data.MOVES.values()])
             return f"【技図鑑】\n{', '.join(move_list)}\n\n『図鑑 技 10万ボルト』のように検索してね。", []
        if "アイテム" in content or "item" in c_lower:
             m_srch = re.search(r"(?:アイテム|items)\s+(.+)", content)
             if m_srch:
                 t_item = m_srch.group(1).strip()
                 found = None
                 for k, v in data.ITEMS.items():
                     if v["name"] == t_item: found = v; break
                 if found:
                     return f"📖 **{found['name']}** (Price: {found['price']}G)\n{found.get('desc', '効果不明')}", []
                 return "そのアイテムは見つからないわ。", []
             item_list = sorted([v['name'] for v in data.ITEMS.values()])
             return f"【アイテム図鑑】\n{', '.join(item_list)}\n\n『図鑑 アイテム モンスターボール』のように検索してね。", []
        m_search = re.search(r"(?:図鑑|dex)\s+(.+)", content, re.IGNORECASE)
        if m_search:
            target_name = m_search.group(1).strip()
            found_key = None
            for k, v in data.BASE_CHIMERAS.items():
                if v["name"] == target_name or v.get("name_en", "").lower() == target_name.lower():
                    found_key = k; break
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
                msg = (f"━━━━━━━━━━━━━━━\n📖 **No.{found_key} {base['name']}** {rarity}\n━━━━━━━━━━━━━━━\n"
                       f"Type: {base['type']}\nAbility: **{base['ability']}**\n-------------------------------\n{desc}\n-------------------------------\n"
                       f"HP:{bs['hp']} Atk:{bs['atk']} Def:{bs['def']} SpA:{bs['spa']} SpD:{bs['spd']} Spe:{bs['spe']} (Total:{total_bs})\n━━━━━━━━━━━━━━━")
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
        return "\n".join(lines) + "\n" + get_k_text(user_id, 'dex_help'), []
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
    new_unlocks = logic.check_all_achievements(user_id)
    extra_msg = ""
    if new_unlocks: extra_msg = "\n" + "\n".join(new_unlocks)
    return f"{get_k_text(user_id, 'menu_title')}\n{get_k_text(user_id, 'menu_opts')}\n{get_k_text(user_id, 'menu_prompt')}{extra_msg}", []

def process_kimera_command(user_id, content):
    session = get_session(user_id)
    if not session:
        if "キメラと遊びたい" in content:
            start_session(user_id)
            return (f"{get_k_text(user_id, 'menu_title')}\n{get_k_text(user_id, 'menu_opts')}\n{get_k_text(user_id, 'menu_prompt')}"), []
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
    elif st in [STATE_BATTLE_WILD, STATE_BATTLE_TRAINER, STATE_BATTLE_CHALLENGE, STATE_BATTLE_DPS]: return handle_battle_action(user_id, content)
    elif st == STATE_BATTLE_DPS_SETUP: return handle_dps_setup(user_id, content)
    elif st == STATE_BATTLE_PVP: return handle_pvp_action(user_id, content)
    elif st == STATE_RAID_LOBBY: return handle_raid_lobby(user_id, content)
    elif st == STATE_RAID_BATTLE: return handle_raid_battle(user_id, content)
    return None