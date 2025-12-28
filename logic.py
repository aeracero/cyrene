import random
import re
from config import today_str
import database as db
from special_unlocks import get_janken_wins

# --- アチーブメント定義 (簡単に追加可能) ---
# key: ID
# value: { 名前, 説明, 称号名, 判定条件(type, threshold) }
# type: 'rps_win'(じゃんけん勝利数), 'affection'(好感度Lv), 'xp'(累計XP), 
#       'gacha_count'(ガチャ回数), 'talk_count'(会話数), 'cyrene_copies'(キュレネ所持数)

ACHIEVEMENTS = {
    # 1. 好感度Lv6 -> 最愛の
    "aff_max_love": {
        "name_jp": "永遠の誓い", "name_en": "Eternal Oath",
        "desc_jp": "好感度Lv.6に到達する", "desc_en": "Reach Affection Level 6",
        "title_jp": "最愛の", "title_en": "Beloved",
        "type": "affection", "threshold": 6
    },
    # 2. ガチャ完凸 (7枚) -> 豪運の
    "gacha_cyrene_e6": {
        "name_jp": "運命の再会", "name_en": "Fated Reunion",
        "desc_jp": "キュレネを合計7体（完凸）所持する", "desc_en": "Own 7 copies of Cyrene (E6)",
        "title_jp": "豪運の", "title_en": "Lucky",
        "type": "cyrene_copies", "threshold": 7
    },
    # 3. 会話300回 -> おしゃべりな
    "talk_master_300": {
        "name_jp": "お喋り好き", "name_en": "Chatterbox",
        "desc_jp": "累計300回会話する", "desc_en": "Talk 300 times total",
        "title_jp": "おしゃべりな", "title_en": "Chatty",
        "type": "talk_count", "threshold": 300
    },
    # 4. XP 1000万 -> 限界を超えた愛を持った
    "xp_limit_break": {
        "name_jp": "愛の極地", "name_en": "Limitless Love",
        "desc_jp": "好感度XPを10,000,000以上獲得する", "desc_en": "Gain over 10,000,000 Affection XP",
        "title_jp": "限界を超えた愛を持った", "title_en": "Limit-Breaking",
        "type": "xp", "threshold": 10000000
    },
    
    # --- その他（既存の実績例） ---
    "rps_master_50": {
        "name_jp": "じゃんけん王", "name_en": "RPS Legend",
        "desc_jp": "じゃんけんで50回勝利する", "desc_en": "Win RPS 50 times",
        "title_jp": "勝負師", "title_en": "Gambler",
        "type": "rps_win", "threshold": 50
    },
}

def check_all_achievements(user_id: int) -> list[str]:
    """
    ユーザーの全ステータスを確認し、解除条件を満たした実績があれば解除して通知を返す。
    どのタイミングで呼んでもOK。
    """
    newly_unlocked = []
    lang = db.get_user_lang(user_id)
    
    # 1. ユーザーデータの収集
    ach_data = db.get_user_achievements(user_id)
    unlocked_ids = set(ach_data["unlocked"])
    stats = ach_data.get("stats", {}) # 累計データ (talk_count, gacha_count等)
    
    # 2. 外部データの収集
    aff_xp, aff_lv = get_user_affection(user_id)
    gacha_state = db.get_gacha_state(user_id)
    cyrene_copies = gacha_state.get("cyrene_copies", 0)
    rps_wins = get_janken_wins(user_id)
    
    # 3. 判定用辞書の作成
    current_values = {
        "affection": aff_lv,
        "xp": aff_xp,
        "cyrene_copies": cyrene_copies,
        "rps_win": rps_wins,
        "talk_count": stats.get("talk_count", 0),
        "gacha_count": stats.get("gacha_count", 0),
        "guardian": 1 if db.get_guardian_level(user_id) else 0
    }

    # 4. 全実績を走査
    for ach_id, data in ACHIEVEMENTS.items():
        if ach_id in unlocked_ids:
            continue
            
        req_type = data["type"]
        req_val = data["threshold"]
        
        # 条件を満たしているか？
        curr_val = current_values.get(req_type, 0)
        if curr_val >= req_val:
            if db.unlock_achievement(user_id, ach_id):
                # 通知作成
                name = data["name_en"] if lang == "en" else data["name_jp"]
                desc = data["desc_en"] if lang == "en" else data["desc_jp"]
                title = data["title_en"] if lang == "en" else data["title_jp"]
                
                if lang == "en":
                    msg = f"\n🏆 **Achievement Unlocked: [{name}]**\nTitle Acquired: **[{title}]**"
                else:
                    msg = f"\n🏆 **実績解除: 【{name}】**\n二つ名獲得: **【{title}】**"
                newly_unlocked.append(msg)
                
                # 自動装備（初回のみ）も可能だが、今回は手動変更にする
    
    return newly_unlocked

def get_title_prefix(user_id: int) -> str:
    """現在の二つ名を取得（名前の前に付ける文字列）"""
    equipped_id = db.get_equipped_title_id(user_id)
    if not equipped_id or equipped_id not in ACHIEVEMENTS:
        return ""
    
    lang = db.get_user_lang(user_id)
    data = ACHIEVEMENTS[equipped_id]
    title = data["title_en"] if lang == "en" else data["title_jp"]
    return f"{title} " # 後ろにスペースを入れる

def format_achievement_progress(user_id: int) -> str:
    """実績の進捗一覧を表示"""
    ach_data = db.get_user_achievements(user_id)
    unlocked_ids = set(ach_data["unlocked"])
    lang = db.get_user_lang(user_id)
    equipped = db.get_equipped_title_id(user_id)
    
    # 現在値の再取得（表示用）
    stats = ach_data.get("stats", {})
    xp, lv = get_user_affection(user_id)
    gacha = db.get_gacha_state(user_id)
    
    vals = {
        "affection": lv, "xp": xp, "cyrene_copies": gacha.get("cyrene_copies", 0),
        "rps_win": get_janken_wins(user_id), "talk_count": stats.get("talk_count", 0),
        "gacha_count": stats.get("gacha_count", 0), "guardian": 1 if db.get_guardian_level(user_id) else 0
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
        curr = vals.get(data["type"], 0)
        
        # 進捗バー的な表示
        if ach_id in unlocked_ids:
            check = "✅"
            status = "(Complete)" if lang=="en" else "(達成)"
            if ach_id == equipped:
                status += " [Equipped]" if lang=="en" else " [装備中]"
        else:
            check = "🔒"
            status = f"({curr}/{req})"
            
        lines.append(f"{check} **{name}**: {status}")
        lines.append(f"   └ Title: {title}")
        
    if lang == "en":
        lines.append("\nUse `Change Title` or `Title List` to equip one.")
    else:
        lines.append("\n『二つ名変更』で獲得した称号をつけられるわよ♪")
        
    return "\n".join(lines)

# --- 好感度ロジック ---
def get_level_from_xp(xp: int, cfg: dict) -> int:
    thresholds = cfg.get("level_thresholds", [0])
    if len(thresholds) <= 1: return 1
    level = 1
    for lv in range(1, len(thresholds)):
        if xp >= thresholds[lv]: level = lv
        else: break
    return max(1, level)

def get_user_affection(user_id: int):
    cfg = db.load_affection_config()
    data = db.load_affection_data()
    info = data.get(str(user_id), {})
    xp = int(info.get("xp", 0))
    return xp, get_level_from_xp(xp, cfg)

def get_cyrene_affection_multiplier(user_id: int) -> float:
    try:
        state = db.get_gacha_state(user_id)
        copies = int(state.get("cyrene_copies", 0))
        mult = 1.0 + 0.2 * copies
        return min(2.4, mult)
    except: return 1.0

def add_affection_xp(user_id: int, delta: int, reason: str = ""):
    if delta == 0: return
    if delta > 0:
        mult = get_cyrene_affection_multiplier(user_id)
        if mult != 1.0:
            delta = int(delta * mult)
            if delta < 1: delta = 1
    data = db.load_affection_data()
    info = data.get(str(user_id), {})
    xp = max(0, int(info.get("xp", 0)) + delta)
    info["xp"] = xp
    data[str(user_id)] = info
    db.save_affection_data(data)

# 管理者用: 全員のリスト
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

# 好感度ステータス
def get_affection_status_message(user_id: int) -> str:
    lang = db.get_user_lang(user_id)
    xp, level = get_user_affection(user_id)
    cfg = db.load_affection_config()
    thresholds = cfg.get("level_thresholds", [0])
    
    if level + 1 < len(thresholds):
        next_xp_req = thresholds[level + 1]
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

# --- ミュリオンロジック ---
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
    # (省略なしのため記述)
    MYURION_QUESTIONS = [
        {"q": "ミュミュ、ミミュミュミュミュウミュミュウミー", "choices": ["ミュウミーミミュミミュミュ", "ミミュミュウミーミーミュウミュウミミ", "ミュウミみミュみミミュミュミュミュウ", "ミュウミュミュミュミュウ"], "answer_index": 0},
        {"q": "ミュウミュミュミュウミュミュミュウウミュウ？", "choices": ["ミュウミミミュミュミュミュウミ", "ミュウーミミュミュミュウミュウ", "ミュウミュウミュミュミュミュミュ", "ミミミュミュミュムミュウミミミュ"], "answer_index": 1},
        {"q": "ミュミュミミュウミュユミミュミュウ？", "choices": ["ミュウミュミュミュミュ、ミーミュユミュミュウ", "ミミュミュミーミーミュ。ミュミュミーミュミュ", "ミュウミュミュミュウ。ミュウミーみミュミュウ", "ミュウ。"], "answer_index": 0},
        {"q": "ミュミュミュミュミューーミュウミュウミュウミュウミュウ？", "choices": ["ミュウミュユミュミュミューミュウミュウミュウミュウ", "ミュウ。ミミュミュミュミーミミュミュミュミュミュウ", "ミミミュミュミュミュウ", "ミュウミュミュミュミュミュミュミュミュミュミュ"], "answer_index": 1},
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

# --- ガチャロジック ---
def calc_main_5star_rate(pity_5: int) -> float:
    base = 0.0006
    if pity_5 <= 73: return base
    if pity_5 < 89:
        return min(1.0, base + (1.0 - base) * ((pity_5 - 73) / 15))
    return 1.0

def perform_gacha_pulls(user_id: int, num_pulls: int, use_ticket: bool = False) -> tuple[bool, str]:
    state = db.get_gacha_state(user_id)
    lang = db.get_user_lang(user_id)

    msg_ticket_10only = "Tickets are for 10-pulls only." if lang == "en" else "チケットは10連専用みたい。"
    msg_ticket_lack = "Not enough tickets." if lang == "en" else "チケットが足りないみたい。"
    msg_stone_lack = "Not enough stones (Need: {cost})" if lang == "en" else "石が足りないみたい（必要: {cost}）"
    
    if use_ticket:
        if num_pulls != 10: return False, msg_ticket_10only
        if state.get("offbanner_tickets", 0) <= 0: return False, msg_ticket_lack
        state["offbanner_tickets"] -= 1
        cost_str = "(1 Ticket consumed)" if lang == "en" else "（すり抜けチケット1枚消費）"
    else:
        cost = 160 * num_pulls
        if state.get("stones", 0) < cost: return False, msg_stone_lack.format(cost=cost)
        state["stones"] -= cost
        cost_str = f"({cost} stones consumed)" if lang == "en" else f"（石 {cost} 個消費）"

    pity_5 = state.get("pity_5", 0)
    pity_4 = state.get("pity_4", 0)
    guaranteed = state.get("guaranteed_cyrene", False)
    results, cyrene_hit, off_hit, page_hits = [], 0, 0, 0

    txt_cyrene = "★5 [Cyrene]" if lang == "en" else "★5【キュレネ】"
    txt_off = "★5 [Off-Banner (Ticket)]" if lang == "en" else "★5【すり抜け（チケット獲得）】"
    txt_page = " + ★5 [Page: Part 1]" if lang == "en" else " ＋ ★5【??? その1】"

    for _ in range(num_pulls):
        page_got = False
        if random.random() < 0.0006:
            state["page1_count"] = state.get("page1_count", 0) + 1
            page_hits += 1
            page_got = True
        
        main5_rate = calc_main_5star_rate(pity_5)
        if random.random() < main5_rate:
            pity_5, pity_4 = 0, 0
            if guaranteed or random.random() < 0.5:
                state["cyrene_copies"] = state.get("cyrene_copies", 0) + 1
                guaranteed, cyrene_hit = False, cyrene_hit + 1
                txt = txt_cyrene
            else:
                state["offbanner_tickets"] = state.get("offbanner_tickets", 0) + 1
                guaranteed, off_hit = True, off_hit + 1
                txt = txt_off
            if page_got: txt += txt_page
        else:
            pity_5 += 1
            if pity_4 >= 9 or random.random() < 0.24:
                pity_4 = 0
                txt = "★4"
            else:
                pity_4 += 1
                txt = "★3"
            if page_got: txt += txt_page
        results.append(txt)

    state["pity_5"], state["pity_4"], state["guaranteed_cyrene"] = pity_5, pity_4, guaranteed
    db.save_gacha_state(user_id, state)

    summary = []
    if cyrene_hit: summary.append(f"★5 Cyrene: {cyrene_hit}" if lang=="en" else f"★5キュレネ: {cyrene_hit}")
    if off_hit: summary.append(f"★5 Off-Banner: {off_hit}" if lang=="en" else f"★5すり抜け: {off_hit}")
    if page_hits: summary.append(f"★5 Page: {page_hits}" if lang=="en" else f"★5ページ: {page_hits}")
    sum_text = " / ".join(summary) if summary else ("No ★5" if lang=="en" else "★5なし")
    
    body = "\n".join([f"{i+1}: {r}" for i, r in enumerate(results)])
    footer = f"Stones: {state['stones']} / Tickets: {state['offbanner_tickets']}" if lang == "en" else f"現在の石: {state['stones']} / チケット: {state['offbanner_tickets']}"
    return True, f"{cost_str}\n{body}\n\n{sum_text}\n{footer}"

def grant_daily_stones(user_id: int) -> tuple[bool, int, str]:
    state = db.get_gacha_state(user_id)
    lang = db.get_user_lang(user_id)
    
    if state.get("last_daily") == today_str():
        msg = "You already received today's reward." if lang == "en" else "今日はもう受け取っているみたい。"
        return False, state["stones"], msg
    
    state["stones"] = state.get("stones", 0) + 16000
    state["last_daily"] = today_str()
    db.save_gacha_state(user_id, state)
    
    msg = "Daily Reward: 16000 stones granted♪" if lang == "en" else "デイリー報酬 16000個 を付与したわ♪"
    return True, state["stones"], msg

def format_gacha_status(user_id: int) -> str:
    state = db.get_gacha_state(user_id)
    lang = db.get_user_lang(user_id)
    
    stones = state.get("stones", 0)
    pity_5 = state.get("pity_5", 0)
    cyrene_copies = state.get("cyrene_copies", 0)
    tickets = state.get("offbanner_tickets", 0)
    guaranteed = state.get("guaranteed_cyrene", False)
    mult = get_cyrene_affection_multiplier(user_id)
    
    if lang == "en":
        next_up = "Guaranteed Cyrene" if guaranteed else "50/50 Chance"
        return (
            "【Gacha Menu】\n"
            f"- Stones: {stones}\n"
            f"- Cyrene Copies: {cyrene_copies} (Affection x{mult:.1f})\n"
            f"- Tickets: {tickets}\n"
            f"- Pity Count: {pity_5} (Next ★5 is {next_up})\n\n"
            "Use `Pull 1` or `Pull 10` (or `Ticket 10`) to play♪"
        )
    else:
        next_up = "キュレネ確定" if guaranteed else "50%でキュレネ"
        return (
            "【ガチャメニュー】\n"
            f"・所持石: {stones} 個\n"
            f"・キュレネ所持: {cyrene_copies} 枚 (好感度倍率 x{mult:.1f})\n"
            f"・すり抜けチケット: {tickets} 枚\n"
            f"・天井カウント: {pity_5} 連 (次の★5は {next_up})\n\n"
            "『単発ガチャ』『10連ガチャ』(または『チケット10連』)で引けるわよ♪"
        )

# --- じゃんけんロジック (英語入力対応) ---
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