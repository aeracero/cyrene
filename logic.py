# logic.py
import random
import re
import datetime
from config import today_str, PRIMARY_ADMIN_ID
import database as db
import kimera_core as k_core
import kimera_data as k_data
from special_unlocks import get_janken_wins, is_nanoka_unlocked, is_danheng_unlocked

# --- ガチャ設定＆キャラクターデータ ---

# 現在開催中のピックアップキャラ
CURRENT_BANNER_KEY = "cyrene"

# 割引イベントの状態管理 (メモリ上で管理)
# { "active": bool, "percent": int, "end_time": datetime }
GLOBAL_DISCOUNT_STATE = {
    "active": False,
    "percent": 0,
    "end_time": None
}

def set_discount_event(active: bool, percent: int = 0, duration_seconds: int = 1800):
    """
    割引イベントを設定する。
    duration_seconds: 持続時間（秒）。デフォルトは30分(1800秒)。
    """
    GLOBAL_DISCOUNT_STATE["active"] = active
    if active and percent > 0:
        GLOBAL_DISCOUNT_STATE["percent"] = percent
        GLOBAL_DISCOUNT_STATE["end_time"] = datetime.datetime.now() + datetime.timedelta(seconds=duration_seconds)
    else:
        # percentが0以下、またはactive=Falseなら終了
        GLOBAL_DISCOUNT_STATE["active"] = False
        GLOBAL_DISCOUNT_STATE["percent"] = 0
        GLOBAL_DISCOUNT_STATE["end_time"] = None

def get_current_discount() -> int:
    if GLOBAL_DISCOUNT_STATE["active"]:
        if GLOBAL_DISCOUNT_STATE["end_time"] and datetime.datetime.now() < GLOBAL_DISCOUNT_STATE["end_time"]:
            return GLOBAL_DISCOUNT_STATE["percent"]
        else:
            # 時間切れならオフにする
            set_discount_event(False)
    return 0

# 黄金裔（全員限定キャラ扱い）の定義
# 凸数上限: 13凸 (Base + 13 duplicates)
LIMITED_CHARACTERS = {
    "cyrene": {
        "name": "キュレネ", 
        "title": "愛の",
        "secret_voice_id": "voice_cyrene_secret_love",
        "buff_type": "affection_boost", 
        "buff_base": 0.20,
        "buff_scale": 0.10,
        "desc": "【愛の加護】好感度XP獲得量UP (Base: +20%, 1凸毎: +10%)"
    },
    "aglaia": {
        "name": "アグライア", 
        "title": "美の",
        "secret_voice_id": "voice_aglaia_aria",
        "buff_type": "training_crit", 
        "buff_base": 0.05,
        "buff_scale": 0.02,
        "desc": "【審美眼】キメラトレーニング「大成功」率UP (Base: 5%, 1凸毎: +2%)"
    },
    "trisbeas": {
        "name": "トリスビアス", 
        "title": "富豪の",
        "secret_voice_id": "voice_trisbeas_scold",
        "buff_type": "daily_income", 
        "buff_base": 2000,
        "buff_scale": 500,
        "desc": "【パトロン】デイリー配布石が増加 (Base: +2000, 1凸毎: +500)"
    },
    "anaxagoras": {
        "name": "アナクサゴラス", 
        "title": "論理の",
        "secret_voice_id": "voice_anax_logic",
        "buff_type": "rps_win_bonus", 
        "buff_base": 5,
        "buff_scale": 2,
        "desc": "【演算】じゃんけん勝利時のXPボーナス (Base: +5, 1凸毎: +2)"
    },
    "medimos": {
        "name": "メデイモス", 
        "title": "戦神の",
        "secret_voice_id": "voice_medimos_shout",
        "buff_type": "trainer_xp_mult", 
        "buff_base": 0.1,
        "buff_scale": 0.05,
        "desc": "【スパルタ】キメラ育成XP倍率UP (Base: +10%, 1凸毎: +5%)"
    },
    "sepharia": {
        "name": "セファリア", 
        "title": "怪盗の",
        "secret_voice_id": "voice_sepharia_steal",
        "buff_type": "gacha_refund", 
        "buff_base": 0.05,
        "buff_scale": 0.02,
        "desc": "【キャッシュバック】石消費時に確率で還元 (Base: 5%, 1凸毎: +2%)"
    },
    "hyacinthia": {
        "name": "ヒアシンシア", 
        "title": "慈愛の",
        "secret_voice_id": "voice_hyacinthia_heal",
        "buff_type": "shop_discount",
        "buff_base": 0.05,
        "buff_scale": 0.02,
        "desc": "【奉仕】ショップ価格割引 (Base: 5%OFF, 1凸毎: +2%)"
    },
    "castoris": {
        "name": "キャストリス", 
        "title": "甘味の",
        "secret_voice_id": "voice_castoris_eat",
        "buff_type": "recovery_boost",
        "buff_base": 0.10,
        "buff_scale": 0.05,
        "desc": "【糖分】回復アイテム効果量UP (Base: +10%, 1凸毎: +5%)"
    },
    "phainon": {
        "name": "ファイノン", 
        "title": "夢追う",
        "secret_voice_id": "voice_phainon_dream",
        "buff_type": "battle_money_boost",
        "buff_base": 0.10,
        "buff_scale": 0.05,
        "desc": "【野望】バトル勝利金UP (Base: +10%, 1凸毎: +5%)"
    },
    "seireness": {
        "name": "セイレンス", 
        "title": "深海の",
        "secret_voice_id": "voice_seireness_song",
        "buff_type": "shiny_rate_boost",
        "buff_base": 0.05,
        "buff_scale": 0.01,
        "desc": "【潮目】高レア遭遇率UP (Base: +5%, 1凸毎: +1%)"
    },
    "kerydra": {
        "name": "ケリュドラ", 
        "title": "覇道の",
        "secret_voice_id": "voice_kerydra_king",
        "buff_type": "drop_rate_boost",
        "buff_base": 0.15,
        "buff_scale": 0.02,
        "desc": "【徴収】ドロップ率UP (Base: +15%, 1凸毎: +2%)"
    },
}

# --- 新規: キュレネの持ち物 (すり抜け枠・レア) ---
CYRENE_BELONGINGS = [
    {"name": "古びた懐中時計", "type": "belonging", "id": "cyrene_watch", "desc": "針の止まった懐中時計。裏面にイニシャルが刻まれている。"},
    {"name": "色褪せたリボン", "type": "belonging", "id": "cyrene_ribbon", "desc": "かつて誰かが髪に結んでいたリボン。微かに甘い香りがする。"},
    {"name": "書きかけの手紙", "type": "belonging", "id": "cyrene_letter", "desc": "宛名のない手紙。「愛しています」とだけ読める。"},
    {"name": "欠けた手鏡", "type": "belonging", "id": "cyrene_mirror", "desc": "縁が装飾された手鏡。自分自身の顔は映らない。"},
    {"name": "乾いた花弁", "type": "belonging", "id": "cyrene_flower", "desc": "本の間に挟まれていた押し花。何の花かはもう分からない。"}
]

GACHA_ITEMS_R4 = ["hyper_ball", "exp_candy_m", "super_potion", "wise_glasses", "power_band", "full_heal"]

# --- アチーブメント定義 ---
ACHIEVEMENTS = {
    "aff_max_love": {
        "name_jp": "永遠の誓い", "name_en": "Eternal Oath",
        "desc_jp": "好感度Lv.6に到達する", "desc_en": "Reach Affection Level 6",
        "title_jp": "最愛の", "title_en": "Beloved",
        "type": "affection", "threshold": 6
    },
    "gacha_cyrene_e6": {
        "name_jp": "運命の再会", "name_en": "Fated Reunion",
        "desc_jp": "キュレネを合計7体所持する", "desc_en": "Own 7 copies of Cyrene",
        "title_jp": "豪運の", "title_en": "Lucky",
        "type": "cyrene_copies", "threshold": 7
    },
    "gacha_aglaia_e6": {
        "name_jp": "美の極致", "name_en": "Perfection of Beauty",
        "desc_jp": "アグライアを合計7体所持する", "desc_en": "Own 7 copies of Aglaia",
        "title_jp": "審美眼を持つ", "title_en": "Aesthetic",
        "type": "aglaia_copies", "threshold": 7
    },
    "gacha_trisbeas_e6": {
        "name_jp": "黄金の出資者", "name_en": "Golden Investor",
        "desc_jp": "トリスビアスを合計7体所持する", "desc_en": "Own 7 copies of Trisbeas",
        "title_jp": "大富豪の", "title_en": "Billionaire",
        "type": "trisbeas_copies", "threshold": 7
    },
    "gacha_anaxagoras_e6": {
        "name_jp": "真理の演算", "name_en": "Logic of Truth",
        "desc_jp": "アナクサゴラスを合計7体所持する", "desc_en": "Own 7 copies of Anaxagoras",
        "title_jp": "全知の", "title_en": "Omniscient",
        "type": "anaxagoras_copies", "threshold": 7
    },
    "gacha_medimos_e6": {
        "name_jp": "不敗の軍神", "name_en": "Invincible God of War",
        "desc_jp": "メデイモスを合計7体所持する", "desc_en": "Own 7 copies of Medimos",
        "title_jp": "常勝無敗の", "title_en": "Ever-Victorious",
        "type": "medimos_copies", "threshold": 7
    },
    "gacha_sepharia_e6": {
        "name_jp": "伝説の大泥棒", "name_en": "Legendary Phantom Thief",
        "desc_jp": "セファリアを合計7体所持する", "desc_en": "Own 7 copies of Sepharia",
        "title_jp": "世間を騒がす", "title_en": "Notorious",
        "type": "sepharia_copies", "threshold": 7
    },
    # --- 新規追加実績 ---
    "gacha_hyacinthia_e6": {
        "name_jp": "慈愛の聖女", "name_en": "Saint of Charity",
        "desc_jp": "ヒアシンシアを合計7体所持する", "desc_en": "Own 7 copies of Hyacinthia",
        "title_jp": "博愛の", "title_en": "Philanthropic",
        "type": "hyacinthia_copies", "threshold": 7
    },
    "gacha_castoris_e6": {
        "name_jp": "至高のパティシエ", "name_en": "Supreme Patissier",
        "desc_jp": "キャストリスを合計7体所持する", "desc_en": "Own 7 copies of Castoris",
        "title_jp": "甘党の", "title_en": "Sweet Tooth",
        "type": "castoris_copies", "threshold": 7
    },
    "gacha_phainon_e6": {
        "name_jp": "夢見る冒険者", "name_en": "Dreaming Adventurer",
        "desc_jp": "ファイノンを合計7体所持する", "desc_en": "Own 7 copies of Phainon",
        "title_jp": "野心的な", "title_en": "Ambitious",
        "type": "phainon_copies", "threshold": 7
    },
    "gacha_seireness_e6": {
        "name_jp": "深海の歌姫", "name_en": "Diva of the Deep",
        "desc_jp": "セイレンスを合計7体所持する", "desc_en": "Own 7 copies of Seireness",
        "title_jp": "深淵を覗く", "title_en": "Abyssal",
        "type": "seireness_copies", "threshold": 7
    },
    "gacha_kerydra_e6": {
        "name_jp": "覇王の凱旋", "name_en": "Return of the King",
        "desc_jp": "ケリュドラを合計7体所持する", "desc_en": "Own 7 copies of Kerydra",
        "title_jp": "絶対的な", "title_en": "Absolute",
        "type": "kerydra_copies", "threshold": 7
    },
    # --- 持ち物返却実績 ---
    "return_belongings": {
        "name_jp": "思い出の返却", "name_en": "Return of Memories",
        "desc_jp": "キュレネの持ち物を全て集めて返却する", "desc_en": "Return all of Cyrene's belongings",
        "title_jp": "と共に時間を分かち合う", "title_en": "Sharing Time Together",
        "type": "manual", "threshold": 1
    },
    # --- 既存実績 ---
    "maker_cry": {
        "name_jp": "製作者泣かせ", "name_en": "Developer's Nightmare",
        "desc_jp": "真なるキメラマスターロードの裏ボスを撃破する", "desc_en": "Defeat the hidden boss of True Kimera Master Road",
        "title_jp": "終焉を齎す", "title_en": "Bringer of End",
        "type": "kimera_hard_stage", "threshold": 15
    },
    "talk_master_300": {
        "name_jp": "お喋り好き", "name_en": "Chatterbox",
        "desc_jp": "累計300回会話する", "desc_en": "Talk 300 times total",
        "title_jp": "おしゃべりな", "title_en": "Chatty",
        "type": "talk_count", "threshold": 300
    },
    "xp_limit_break": {
        "name_jp": "愛の極地", "name_en": "Limitless Love",
        "desc_jp": "好感度XPを100,000以上獲得する", "desc_en": "Gain over 100,000 Affection XP",
        "title_jp": "限界を超えた愛を持った", "title_en": "Limit-Breaking",
        "type": "xp", "threshold": 100000
    },
    "rps_master_50": {
        "name_jp": "じゃんけん王", "name_en": "RPS Legend",
        "desc_jp": "じゃんけんで50回勝利する", "desc_en": "Win RPS 50 times",
        "title_jp": "勝負師", "title_en": "Gambler",
        "type": "rps_win", "threshold": 50
    },
    "kimera_champion": {
        "name_jp": "キメラチャンピオン", "name_en": "Kimera Champion",
        "desc_jp": "チャレンジモードを完全制覇する", "desc_en": "Complete Challenge Mode",
        "title_jp": "ポ◯モンマスターの", "title_en": "Po*emon Master",
        "type": "kimera_stage", "threshold": 15
    },
    "unlock_nanoka": {
        "name_jp": "可愛いは正義", "name_en": "Cute is Justice",
        "desc_jp": "三月なのかの姿を解放する", "desc_en": "Unlock March 7th form",
        "title_jp": "なのかなのか？", "title_en": "March 7th?",
        "type": "nanoka_flag", "threshold": 1
    },
    "unlock_danheng": {
        "name_jp": "過去との決別", "name_en": "Farewell to the Past",
        "desc_jp": "丹恒の姿を解放する", "desc_en": "Unlock Dan Heng form",
        "title_jp": "皆を護りし者", "title_en": "The Guardian",
        "type": "danheng_flag", "threshold": 1
    },
    "unlock_love_hc": {
        "name_jp": "HCへの愛", "name_en": "Love for HC",
        "desc_jp": "特定の言葉を紡ぐ", "desc_en": "Speak the keywords",
        "title_jp": "キュレネHCを愛する", "title_en": "Loving Cyrene HC",
        "type": "manual", "threshold": 1
    },
    "unlock_150m_dmg": {
        "name_jp": "極大ダメージ", "name_en": "Massive Damage",
        "desc_jp": "特定の変身手順を経て言葉を紡ぐ", "desc_en": "Complex transformation sequence",
        "title_jp": "150万ダメージを与えし", "title_en": "Dealt 1.5M Damage",
        "type": "manual", "threshold": 1
    },
    "unlock_shachiku": {
        "name_jp": "終わらない仕事", "name_en": "Endless Work",
        "desc_jp": "ファイノンの姿で特定の言葉を紡ぐ", "desc_en": "Speak keyword as Phainon",
        "title_jp": "社畜の", "title_en": "Corporate Slave's",
        "type": "manual", "threshold": 1
    },
    "kimera_true_master": {
        "name_jp": "真なるキメラマスター", "name_en": "True Kimera Master",
        "desc_jp": "「真なるキメラマスターロード」をクリアする", "desc_en": "Complete True Kimera Master Road",
        "title_jp": "キメラ遊びを極めし者", "title_en": "Supreme Kimera Master",
        "type": "kimera_hard_stage", "threshold": 15
    },
}

def get_gacha_buff_multiplier(user_id: int, buff_type: str) -> float:
    state = db.get_gacha_state(user_id)
    chars = state.get("characters", {})
    if "cyrene" not in chars and "cyrene_copies" in state:
        chars["cyrene"] = state["cyrene_copies"]
    
    total_val = 0.0
    for char_key, count in chars.items():
        if count > 0 and char_key in LIMITED_CHARACTERS:
            c_data = LIMITED_CHARACTERS[char_key]
            if c_data.get("buff_type") == buff_type:
                base = c_data.get("buff_base", 0)
                scale = c_data.get("buff_scale", 0)
                # 凸数上限を13凸 (計14体) に変更
                eidolon_count = min(count - 1, 13)
                val = base + (eidolon_count * scale)
                total_val += val
    return total_val

def check_secret_voice(user_id: int, char_key: str) -> bool:
    state = db.get_gacha_state(user_id)
    unlocked = state.get("unlocked_voices", [])
    if char_key in LIMITED_CHARACTERS:
        target_id = LIMITED_CHARACTERS[char_key]["secret_voice_id"]
        return target_id in unlocked
    return False

# 持ち物返却イベントのチェック関数
def check_cyrene_collection(user_id: int) -> tuple[bool, str]:
    state = db.get_gacha_state(user_id)
    belongings = state.get("belongings", [])
    
    # 必要なアイテムIDリスト
    required_ids = [item["id"] for item in CYRENE_BELONGINGS]
    
    # 所持しているかチェック
    owned_ids = set(belongings)
    if all(req in owned_ids for req in required_ids):
        # 実績解除処理
        if db.unlock_achievement(user_id, "return_belongings"):
            # アイテムを削除（返却）
            state["belongings"] = []
            db.save_gacha_state(user_id, state)
            
            ach = ACHIEVEMENTS["return_belongings"]
            msg = (f"「…これ、私の…？ 拾ってくれていたのね。\n"
                   f"ありがとう。失くしたと思っていた時間たちが、今戻ってきたみたい…。」\n\n"
                   f"🏆 **実績解除: 【{ach['name_jp']}】**\n"
                   f"二つ名獲得: **【{ach['title_jp']}】**")
            return True, msg
        else:
            return False, "（もう返してあげたはずよ。手元には何もないわ。）"
    else:
        missing = [item["name"] for item in CYRENE_BELONGINGS if item["id"] not in owned_ids]
        return False, f"まだ全ての持ち物が揃っていないみたい。\n不足: {', '.join(missing)}"

def check_all_achievements(user_id: int) -> list[str]:
    newly_unlocked = []
    lang = db.get_user_lang(user_id)
    ach_data = db.get_user_achievements(user_id)
    unlocked_ids = set(ach_data["unlocked"])
    stats = ach_data.get("stats", {})
    aff_xp, aff_lv = get_user_affection(user_id)
    gacha_state = db.get_gacha_state(user_id)
    
    # ガチャキャラ所持数の整理
    char_counts = gacha_state.get("characters", {})
    if "cyrene_copies" in gacha_state:
        char_counts["cyrene"] = max(char_counts.get("cyrene", 0), gacha_state["cyrene_copies"])
    
    # 全員完凸チェック
    all_limited_e6 = 1 if all(char_counts.get(k, 0) >= 7 for k in LIMITED_CHARACTERS.keys()) else 0

    rps_wins = get_janken_wins(user_id)
    
    k_ud_normal = k_core.get_user_data(user_id, hard_mode=False)
    k_ud_hard = k_core.get_user_data(user_id, hard_mode=True)
    kimera_stage = k_ud_normal.get("challenge_stage", 1)
    kimera_hard_stage = k_ud_hard.get("challenge_stage", 1)

    current_values = {
        "affection": aff_lv,
        "xp": aff_xp,
        "cyrene_copies": char_counts.get("cyrene", 0),
        "aglaia_copies": char_counts.get("aglaia", 0),
        "trisbeas_copies": char_counts.get("trisbeas", 0),
        "anaxagoras_copies": char_counts.get("anaxagoras", 0),
        "medimos_copies": char_counts.get("medimos", 0),
        "sepharia_copies": char_counts.get("sepharia", 0),
        # --- 新規キャラ分 ---
        "hyacinthia_copies": char_counts.get("hyacinthia", 0),
        "castoris_copies": char_counts.get("castoris", 0),
        "phainon_copies": char_counts.get("phainon", 0),
        "seireness_copies": char_counts.get("seireness", 0),
        "kerydra_copies": char_counts.get("kerydra", 0),
        # -------------------
        "all_limited_e6": all_limited_e6,
        "rps_win": rps_wins,
        "kimera_stage": kimera_stage,
        "kimera_hard_stage": kimera_hard_stage,
        "talk_count": stats.get("talk_count", 0),
        "gacha_count": stats.get("gacha_count", 0),
        "guardian": 1 if db.get_guardian_level(user_id) else 0,
        "nanoka_flag": 1 if is_nanoka_unlocked(user_id) else 0,
        "danheng_flag": 1 if is_danheng_unlocked(user_id) else 0
    }

    for ach_id, data in ACHIEVEMENTS.items():
        if ach_id in unlocked_ids: continue
        if data["type"] == "manual": continue
        req_type = data["type"]
        req_val = data["threshold"]
        curr_val = current_values.get(req_type, 0)
        if curr_val >= req_val:
            if db.unlock_achievement(user_id, ach_id):
                name = data["name_en"] if lang == "en" else data["name_jp"]
                title = data["title_en"] if lang == "en" else data["title_jp"]
                if lang == "en":
                    msg = f"\n🏆 **Achievement Unlocked: [{name}]**\nTitle Acquired: **[{title}]**"
                else:
                    msg = f"\n🏆 **実績解除: 【{name}】**\n二つ名獲得: **【{title}】**"
                newly_unlocked.append(msg)
    return newly_unlocked

def get_title_prefix(user_id: int) -> str:
    equipped_id = db.get_equipped_title_id(user_id)
    if not equipped_id or equipped_id not in ACHIEVEMENTS:
        return ""
    lang = db.get_user_lang(user_id)
    data = ACHIEVEMENTS[equipped_id]
    title = data["title_en"] if lang == "en" else data["title_jp"]
    return f"{title} "

def format_achievement_progress(user_id: int) -> str:
    new_unlocks = check_all_achievements(user_id)
    ach_data = db.get_user_achievements(user_id)
    unlocked_ids = set(ach_data["unlocked"])
    lang = db.get_user_lang(user_id)
    equipped = db.get_equipped_title_id(user_id)
    stats = ach_data.get("stats", {})
    xp, lv = get_user_affection(user_id)
    gacha = db.get_gacha_state(user_id)
    
    char_counts = gacha.get("characters", {})
    if "cyrene_copies" in gacha:
        char_counts["cyrene"] = max(char_counts.get("cyrene", 0), gacha["cyrene_copies"])
    
    all_limited_e6 = 1 if all(char_counts.get(k, 0) >= 7 for k in LIMITED_CHARACTERS.keys()) else 0

    k_ud_normal = k_core.get_user_data(user_id, hard_mode=False)
    k_ud_hard = k_core.get_user_data(user_id, hard_mode=True)
    kimera_stage = k_ud_normal.get("challenge_stage", 1)
    kimera_hard_stage = k_ud_hard.get("challenge_stage", 1)

    vals = {
        "affection": lv, "xp": xp, 
        "cyrene_copies": char_counts.get("cyrene", 0),
        "aglaia_copies": char_counts.get("aglaia", 0),
        "trisbeas_copies": char_counts.get("trisbeas", 0),
        "anaxagoras_copies": char_counts.get("anaxagoras", 0),
        "medimos_copies": char_counts.get("medimos", 0),
        "sepharia_copies": char_counts.get("sepharia", 0),
        # --- 新規キャラ分 ---
        "hyacinthia_copies": char_counts.get("hyacinthia", 0),
        "castoris_copies": char_counts.get("castoris", 0),
        "phainon_copies": char_counts.get("phainon", 0),
        "seireness_copies": char_counts.get("seireness", 0),
        "kerydra_copies": char_counts.get("kerydra", 0),
        # -------------------
        "all_limited_e6": all_limited_e6,
        "rps_win": get_janken_wins(user_id), 
        "kimera_stage": kimera_stage,
        "kimera_hard_stage": kimera_hard_stage,
        "talk_count": stats.get("talk_count", 0),
        "gacha_count": stats.get("gacha_count", 0), "guardian": 1 if db.get_guardian_level(user_id) else 0,
        "nanoka_flag": 1 if is_nanoka_unlocked(user_id) else 0,
        "danheng_flag": 1 if is_danheng_unlocked(user_id) else 0
    }
    
    total = len(ACHIEVEMENTS)
    count = len(unlocked_ids)
    
    if lang == "en":
        lines = [f"【Achievements: {count}/{total}】"]
    else:
        lines = [f"【実績進捗: {count}/{total}】"]
        
    for ach_id, data in ACHIEVEMENTS.items():
        name = data["name_en"] if lang == "en" else data["name_jp"]
        title = data["title_en"] if lang == "en" else data["title_jp"]
        req = data["threshold"]
        
        if ach_id in unlocked_ids:
            check = "✅"
            status = "(Complete)" if lang=="en" else "(達成)"
            if ach_id == equipped:
                status += " [Equipped]" if lang=="en" else " [装備中]"
        else:
            check = "🔒"
            if data["type"] == "manual":
                status = "(???)"
            else:
                curr = vals.get(data["type"], 0)
                status = f"({curr}/{req})"
            
        lines.append(f"{check} **{name}**: {status}")
        lines.append(f"   └ Title: {title}")
    
    if new_unlocks:
        lines.append("\n" + "\n".join(new_unlocks))
    if lang == "en":
        lines.append("\nUse `Change Title` to equip one.")
    else:
        lines.append("\n『二つ名変更』で獲得した称号をつけられるわよ♪")
    return "\n".join(lines)

def get_level_from_xp(xp: int, cfg: dict) -> int:
    thresholds = [0, 1000, 2000, 3500, 7000, 10000]
    current_level = 1
    for i, th in enumerate(thresholds):
        if xp >= th:
            current_level = i + 1
        else:
            break
    return current_level

def get_user_affection(user_id: int):
    cfg = db.load_affection_config()
    data = db.load_affection_data()
    info = data.get(str(user_id), {})
    xp = int(info.get("xp", 0))
    return xp, get_level_from_xp(xp, cfg)

def add_affection_xp(user_id: int, delta: int, reason: str = ""):
    if delta == 0: return
    if delta > 0:
        buff_mult = get_gacha_buff_multiplier(user_id, "affection_boost")
        mult = 1.0 + buff_mult
        delta = int(delta * mult)
        if delta < 1: delta = 1

    data = db.load_affection_data()
    info = data.get(str(user_id), {})
    xp = max(0, int(info.get("xp", 0)) + delta)
    info["xp"] = xp
    data[str(user_id)] = info
    db.save_affection_data(data)

def format_all_affection_status(guild) -> str:
    data = db.load_affection_data()
    if not data: return "No data."
    cfg = db.load_affection_config()
    user_list = []
    for uid_str, info in data.items():
        xp = int(info.get("xp", 0))
        level = get_level_from_xp(xp, cfg)
        user_list.append((uid_str, xp, level))
    user_list.sort(key=lambda x: x[1], reverse=True)
    lines = ["【Affection List】"]
    for uid_str, xp, level in user_list:
        name = f"ID: {uid_str}"
        if guild:
            try:
                member = guild.get_member(int(uid_str))
                if member: name = member.display_name
            except: pass
        lines.append(f"- **{name}**: Lv.{level} ({xp} XP)")
    return "\n".join(lines)

def get_affection_status_message(user_id: int) -> str:
    lang = db.get_user_lang(user_id)
    xp, level = get_user_affection(user_id)
    thresholds = [0, 1000, 2000, 3500, 7000, 10000]
    
    if level < len(thresholds):
        next_xp_req = thresholds[level] 
        needed = max(0, next_xp_req - xp)
        if lang == "en":
            return (f"Your affection is **Lv.{level}** (Total {xp} XP)♪\n"
                    f"To reach Lv.{level + 1}, you need **{needed} more XP**.")
        else:
            return (f"あなたの好感度は **Lv.{level}** (累計 {xp} XP) よ♪\n"
                    f"次の Lv.{level + 1} までは、あと **{needed} XP** 必要ね。")
    else:
        if lang == "en":
            return (f"Your affection is **Lv.{level}** (Total {xp} XP)♪\n"
                    "We are already super close! I can't even count it anymore♪")
        else:
            return (f"あなたの好感度は **Lv.{level}** (累計 {xp} XP) よ♪\n"
                    "もう十分すぎるくらい仲良しね！これ以上は数え切れないわ♪")

MYURION_SYLLABLES = ["ミュ", "ミュウ", "ミュミュ", "ミュイー"]

def to_myurion_text(body: str) -> str:
    result = []
    for ch in body:
        if ch in "\r\n" or ch.isspace() or ch in "。、！？…,.!?「」『』()（）[]【】:：;；/｜|\\-—ー♪☆★":
            result.append(ch)
        else:
            result.append(random.choice(MYURION_SYLLABLES))
    return "".join(result)

def apply_myurion_filter(user_id: int, text: str) -> str:
    st = db.get_myurion_state(user_id)
    if not st.get("enabled", False):
        return text
    m = re.match(r"^(<@!?\d+>)(.*)$", text, flags=re.DOTALL)
    if not m: return to_myurion_text(text)
    return m.group(1) + to_myurion_text(m.group(2))

def parse_myurion_answer(text: str) -> int | None:
    if any(ch in text for ch in ["1", "１"]): return 1
    if any(ch in text for ch in ["2", "２"]): return 2
    if any(ch in text for ch in ["3", "３"]): return 3
    if any(ch in text for ch in ["4", "４"]): return 4
    return None

async def send_myurion_question(message, user_id, correct_count, state_dict):
    MYURION_QUESTIONS = [
        {"q": "ミュミュ、ミミュミュミュミュウミュミュウミー", "choices": ["ミュウミーミミュミミュミュ", "ミミュミュウミーミーミュウミュウミミ", "ミュウミみミュみミミュミュミュミュウ", "ミュウミュミュミュミュウ"], "answer_index": 0},
        {"q": "ミュウミュミュミュウミュミュミュウウミュウ？", "choices": ["ミュウミミミュミュミュミュウミ", "ミュウーミミュミュミュウミュウ", "ミュウミュウミュミュミュミュミュ", "ミミミュミュミュムミュウミミミュ"], "answer_index": 1},
        {"q": "ミュミュミミュウミュユミミュミュウ？", "choices": ["ミュウミュミュミュミュ、ミーミュユミュミュウ", "ミミュミュミーミーミュ。ミュミュミーミュミュ", "ミュウミュミュミュウ。ミュウミーみミュミュウ", "ミュウ。"], "answer_index": 0},
        {"q": "ミュミュミュミュミューーミュウミュウミュウミュウミュウ？", "choices": ["ミュウミュユミュミュミューミュウミュウミュウミュウ", "ミュウ。ミミュミュミュミーミミュミュミュミュミュウ", "ミミミュミュミュミュウ", "ミュウミュミュミュミュミュミュミュミュミュ"], "answer_index": 1},
        {"q": "ミュミュミュミュウミュウミュウミュウミュウミュウミュウミュウ？", "choices": ["ミュウ!", "ミュウ?", "ミュウ。", "ミュウ♪"], "answer_index": 0},
    ]
    q = random.choice(MYURION_QUESTIONS)
    indexed = list(enumerate(q["choices"]))
    random.shuffle(indexed)
    correct_index = None
    for new_idx, (orig_idx, _) in enumerate(indexed):
        if orig_idx == q["answer_index"]:
            correct_index = new_idx
            break
    options_text = "\n".join([f"{i+1}. {c}" for i, (_, c) in enumerate(indexed)])
    body = (f"ミュミュミュ…（現在 {correct_count}/3 問正解ミュ）\n{q['q']}\n"
            f"ミュミュ…好きな番号を選んでミュ（1〜4）\n\n{options_text}")
    state_dict[user_id] = {"question": q, "options": [c for _, c in indexed], "correct_index": correct_index}
    await message.channel.send(apply_myurion_filter(user_id, f"{message.author.mention} {body}"))

# --- 石の譲渡機能 ---
def transfer_stones(sender_id: int, receiver_id: int, amount: int) -> str:
    if amount <= 0:
        return "あげる数は1以上にしないとね。"
    if sender_id == receiver_id:
        return "自分には送れないわ。"
    
    sender_state = db.get_gacha_state(sender_id)
    if sender_state.get("stones", 0) < amount:
        return "石が足りないみたいよ。"
    
    receiver_state = db.get_gacha_state(receiver_id)
    
    sender_state["stones"] -= amount
    receiver_state["stones"] = receiver_state.get("stones", 0) + amount
    
    db.save_gacha_state(sender_id, sender_state)
    db.save_gacha_state(receiver_id, receiver_state)
    
    return f"<@{receiver_id}> に {amount}個 の石をプレゼントしたわ♪"

# --- ガチャロジック ---

def calc_pickup_rate(spark_counter: int) -> float:
    """
    天井(300連)に近づくほど、すり抜け率が50%に近づく（ピックアップ率が上がる）。
    0連: ピックアップ率 20% (すり抜け 80%)
    300連: ピックアップ率 50% (すり抜け 50%)
    ※300連目自体は別途確定処理される
    """
    base_rate = 0.20 # 20%
    target_rate = 0.50 # 50%
    progress = min(1.0, spark_counter / 300.0)
    
    return base_rate + (target_rate - base_rate) * progress

def calc_main_5star_rate(pity_5: int) -> float:
    base = 0.0006
    if pity_5 <= 73: return base
    if pity_5 < 89:
        return min(1.0, base + (1.0 - base) * ((pity_5 - 73) / 15))
    return 1.0

def perform_gacha_pulls(user_id: int, num_pulls: int, use_ticket: bool = False) -> tuple[bool, str]:
    from reply_system import get_secret_voice

    state = db.get_gacha_state(user_id)
    lang = db.get_user_lang(user_id)
    user_kimera_data = k_core.get_user_data(user_id, hard_mode=False)

    pickup_key = state.get("selected_pickup", CURRENT_BANNER_KEY)
    if pickup_key not in LIMITED_CHARACTERS:
        pickup_key = CURRENT_BANNER_KEY
    pickup_char = LIMITED_CHARACTERS[pickup_key]

    # --- コスト計算 (割引適用) ---
    discount_percent = get_current_discount()
    base_cost = 160 * num_pulls
    
    if use_ticket:
        if num_pulls != 10: return False, "チケットは10連専用です。"
        if state.get("offbanner_tickets", 0) <= 0: return False, "チケットが足りません。"
        state["offbanner_tickets"] -= 1
        cost_str = "(チケット消費)"
    else:
        # 割引適用
        final_cost = int(base_cost * (1.0 - discount_percent / 100.0))
        
        # セファリアのキャッシュバックバフ
        refund_chance = get_gacha_buff_multiplier(user_id, "gacha_refund")
        is_refunded = False
        if refund_chance > 0 and random.random() < refund_chance:
             final_cost = int(final_cost * 0.5)
             is_refunded = True

        cost_str = f"({final_cost} 個消費)"
        if discount_percent > 0:
            cost_str += f" **[{discount_percent}% OFF!]**"
        if is_refunded:
            cost_str += " [怪盗の還元発動!]"

        if state.get("stones", 0) < final_cost: return False, f"石が足りません（必要: {final_cost}）"
        state["stones"] -= final_cost

    pity_5 = state.get("pity_5", 0)
    pity_4 = state.get("pity_4", 0)
    spark_counter = state.get("spark_counter", 0) # 300連天井用カウンター
    
    if "characters" not in state: state["characters"] = {}
    if "unlocked_voices" not in state: state["unlocked_voices"] = []
    if "belongings" not in state: state["belongings"] = [] 

    results = []
    new_features = []

    for _ in range(num_pulls):
        rank = 3
        # 300連天井 (Spark) チェック: ピックアップ確定
        spark_counter += 1
        is_spark_trigger = False
        
        if spark_counter >= 300:
            rank = 5
            is_spark_trigger = True
            # 天井到達時は確実にピックアップ
        elif random.random() < calc_main_5star_rate(pity_5):
            rank = 5
        else:
            pity_5 += 1
            if pity_4 >= 9 or random.random() < 0.051:
                rank = 4
                pity_4 = 0
            else:
                pity_4 += 1
        
        if rank == 5:
            pity_5 = 0
            is_pickup_win = False
            
            # ピックアップ判定
            if is_spark_trigger:
                is_pickup_win = True
            else:
                # 天井に近づくほど確率は上がる (20% -> 50%)
                current_pickup_rate = calc_pickup_rate(spark_counter)
                if random.random() < current_pickup_rate:
                    is_pickup_win = True
                else:
                    is_pickup_win = False
            
            if is_pickup_win:
                # ピックアップ入手 (※ここでは天井リセットしない)
                char_key = pickup_key
                char_info = pickup_char
                count = state["characters"].get(char_key, 0) + 1
                state["characters"][char_key] = count
                
                if char_key == "cyrene": state["cyrene_copies"] = count

                if count == 7:
                    if char_info["secret_voice_id"] not in state["unlocked_voices"]:
                        state["unlocked_voices"].append(char_info["secret_voice_id"])
                    voice_text = get_secret_voice(char_key, lang)
                    new_features.append(f"🎉 **完凸達成！シークレットボイス解放**: \n「{voice_text}」")

                eidolon = count - 1 
                prefix = "🌠 **[天井]** " if is_spark_trigger else ""
                if count == 1:
                    res_txt = f"{prefix}**★5 [限定] {char_info['name']}** (New!)"
                    new_features.append(f"✨ バフ獲得: {char_info['desc']}")
                else:
                    res_txt = f"{prefix}**★5 [限定] {char_info['name']}** ({eidolon}凸)"
            else:
                # すり抜け: 持ち物(レア) or チケットのみ(ハズレ)
                # 持ち物はレアにする (例: 10%で持ち物, 90%でチケットのみ)
                if random.random() < 0.10:
                    spook_item = random.choice(CYRENE_BELONGINGS)
                    item_id = spook_item["id"]
                    state["belongings"].append(item_id)
                    res_txt = f"★5 🗝️ **{spook_item['name']}**\n_{spook_item['desc']}_"
                else:
                    res_txt = f"★5 🎫 **幸運のチケット** (ハズレ枠…)"
                
                # すり抜け時はチケット付与
                state["offbanner_tickets"] = state.get("offbanner_tickets", 0) + 1
                res_txt += "\n(チケット +1)"
            
            results.append(res_txt)

        elif rank == 4:
            item_key = random.choice(GACHA_ITEMS_R4)
            item_name = k_data.ITEMS[item_key]["name"]
            user_kimera_data["items"][item_key] = user_kimera_data["items"].get(item_key, 0) + 1
            results.append(f"★4 {item_name}")

        else: 
            state["stones"] += 10
            results.append(f"★3 (10石に変換されました)")

    state["pity_5"] = pity_5
    state["pity_4"] = pity_4
    state["spark_counter"] = spark_counter # 天井カウンタ保存
    db.save_gacha_state(user_id, state)
    k_core.save_user_data(user_id, user_kimera_data, hard_mode=False)

    new_unlocks = check_all_achievements(user_id)

    header = f"【ガチャ結果】PickUp: {pickup_char['name']}\n"
    body = "\n".join(results)
    
    # 持ち物収集状況のヒント
    owned_ids = set(state.get("belongings", []))
    total_belongings = len(CYRENE_BELONGINGS)
    current_belongings = len([i for i in CYRENE_BELONGINGS if i["id"] in owned_ids])
    
    footer = f"\n\n{cost_str} / 残り石: {state['stones']} / チケット: {state.get('offbanner_tickets',0)}"
    footer += f"\n天井(確定)まで: {300 - spark_counter}連"
    footer += f"\nキュレネの持ち物: {current_belongings}/{total_belongings} 種"
    
    if new_features: footer += "\n\n" + "\n".join(new_features)
    if new_unlocks: footer += "\n" + "\n".join(new_unlocks)

    return True, header + body + footer

def grant_daily_stones(user_id: int) -> tuple[bool, int, str]:
    state = db.get_gacha_state(user_id)
    lang = db.get_user_lang(user_id)
    
    if state.get("last_daily") == today_str():
        msg = "You already received today's reward." if lang == "en" else "今日はもう受け取っているみたい。"
        return False, state.get("stones", 0), msg
    
    base = 16000
    bonus = int(get_gacha_buff_multiplier(user_id, "daily_income"))
    
    total = base + bonus
    state["stones"] = state.get("stones", 0) + total
    state["last_daily"] = today_str()
    db.save_gacha_state(user_id, state)
    
    msg = f"デイリー報酬 {total}個 を付与しました。"
    if bonus > 0:
        msg += f"\n(富豪のバフ効果で +{bonus}個 ボーナス！)"
    return True, state["stones"], msg

def format_gacha_status(user_id: int) -> str:
    state = db.get_gacha_state(user_id)
    lang = db.get_user_lang(user_id)
    
    stones = state.get("stones", 0)
    pity_5 = state.get("pity_5", 0)
    tickets = state.get("offbanner_tickets", 0)
    spark_counter = state.get("spark_counter", 0)
    aff_mult = 1.0 + get_gacha_buff_multiplier(user_id, "affection_boost")
    
    chars = state.get("characters", {})
    pickup_key = state.get("selected_pickup", CURRENT_BANNER_KEY)
    if pickup_key not in LIMITED_CHARACTERS: pickup_key = CURRENT_BANNER_KEY
    
    pickup_char = LIMITED_CHARACTERS.get(pickup_key, {})
    pickup_name = pickup_char.get("name", "Unknown")

    if lang == "en":
        return (
            "【Gacha Menu】\n"
            f"- Stones: {stones}\n"
            f"- Current Banner: {pickup_name}\n"
            f"- Pity Count: {pity_5} / Spark: {spark_counter}/300\n"
            f"- Ticket: {tickets}\n"
            f"- Affection Bonus: x{aff_mult:.2f}\n"
        )
    else:
        char_list = []
        for k, v in chars.items():
            if k in LIMITED_CHARACTERS and v > 0:
                name = LIMITED_CHARACTERS[k]["name"]
                eidolon = v - 1
                char_list.append(f"{name}({eidolon}凸)")
        
        char_str = ", ".join(char_list) if char_list else "なし"
        
        # 割引表示
        discount = get_current_discount()
        discount_msg = f"現在 {discount}% OFF中！" if discount > 0 else ""

        return (
            "【ガチャメニュー】\n"
            f"・開催中: {pickup_name} ピックアップ {discount_msg}\n"
            f"・所持石: {stones} 個\n"
            f"・チケット: {tickets} 枚\n"
            f"・天井: {pity_5} (仮) / 確定まで: {300 - spark_counter}連\n"
            f"・好感度倍率: x{aff_mult:.2f}\n"
            f"・所持キャラ: {char_str}\n\n"
            "『単発ガチャ』『10連ガチャ』で運試しよ！"
        )

def change_pickup_banner(user_id: int, target_name: str) -> tuple[bool, str]:
    target_key = None
    if target_name in LIMITED_CHARACTERS:
        target_key = target_name
    else:
        for k, v in LIMITED_CHARACTERS.items():
            if v["name"] == target_name:
                target_key = k
                break
    
    if not target_key:
        return False, "そのキャラクターはピックアップ対象にいないみたい。"
        
    is_main_admin = (user_id == PRIMARY_ADMIN_ID)
    cost = 3200 # コストを2倍に変更
    state = db.get_gacha_state(user_id)
    
    if is_main_admin:
        pass
    else:
        if state.get("stones", 0) < cost:
            return False, f"石が足りないわ。（必要: {cost}個）"
        state["stones"] -= cost
        
    state["selected_pickup"] = target_key
    state["spark_counter"] = 0 # ピックアップ変更で300連天井リセット
    db.save_gacha_state(user_id, state)
    
    char_name = LIMITED_CHARACTERS[target_key]['name']
    msg = f"ピックアップを **{char_name}** に変更したわ♪ (天井カウントはリセットされました)"
    if is_main_admin: msg += "\n(デバッグ権限: 消費なし)"
    else: msg += f"\n({cost}石 消費 / 残り: {state['stones']}個)"
    return True, msg

def set_user_stones(user_id: int, amount: int) -> int:
    state = db.get_gacha_state(user_id)
    state["stones"] = max(0, amount)
    db.save_gacha_state(user_id, state)
    return state["stones"]

JANKEN_HANDS = ["グー", "チョキ", "パー"]
def parse_hand(text: str):
    t = text.lower()
    if "グー" in t or "rock" in t: return "グー"
    if "チョキ" in t or "scissors" in t: return "チョキ"
    if "パー" in t or "paper" in t: return "パー"
    return None

def judge_janken(user_hand, bot_hand):
    if user_hand == bot_hand: return "draw"
    if (user_hand=="グー" and bot_hand=="チョキ") or \
       (user_hand=="チョキ" and bot_hand=="パー") or \
       (user_hand=="パー" and bot_hand=="グー"): return "win"
    return "lose"

def get_bot_hand(user_hand, force_win=False):
    if not force_win: return random.choice(JANKEN_HANDS)
    if user_hand == "グー": return "チョキ"
    if user_hand == "チョキ": return "パー"
    return "グー"