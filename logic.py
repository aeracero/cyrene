# logic.py
import random
import re
from config import today_str
import database as db

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

# ★管理者用：全員のリスト
def format_all_affection_status(guild) -> str:
    data = db.load_affection_data()
    if not data:
        return "まだ好感度データは誰も登録されていないみたい。"
    
    cfg = db.load_affection_config()
    
    user_list = []
    for uid_str, info in data.items():
        xp = int(info.get("xp", 0))
        level = get_level_from_xp(xp, cfg)
        user_list.append((uid_str, xp, level))
    
    user_list.sort(key=lambda x: x[1], reverse=True)
    
    lines = ["【みんなの好感度・経験値一覧】"]
    for uid_str, xp, level in user_list:
        name = f"ID: {uid_str}"
        if guild:
            try:
                member = guild.get_member(int(uid_str))
                if member: name = member.display_name
            except: pass
        lines.append(f"- **{name}**: Lv.{level} ({xp} XP)")
        
    return "\n".join(lines)

# ★一般ユーザー用好感度メッセージ
def get_affection_status_message(user_id: int) -> str:
    xp, level = get_user_affection(user_id)
    cfg = db.load_affection_config()
    thresholds = cfg.get("level_thresholds", [0])
    
    if level + 1 < len(thresholds):
        next_xp_req = thresholds[level + 1]
        needed = max(0, next_xp_req - xp)
        return (f"あなたの好感度は **Lv.{level}** (累計 {xp} XP) よ♪\n"
                f"次の Lv.{level + 1} までは、あと **{needed} XP** 必要ね。")
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

# ★追加: ミュリオンクイズ回答解析
def parse_myurion_answer(text: str) -> int | None:
    if any(ch in text for ch in ["1", "１"]): return 1
    if any(ch in text for ch in ["2", "２"]): return 2
    if any(ch in text for ch in ["3", "３"]): return 3
    if any(ch in text for ch in ["4", "４"]): return 4
    return None

MYURION_QUESTIONS = [
    {"q": "ミュミュ、ミミュミュミュミュウミュミュウミー", "choices": ["ミュウミーミミュミミュミュ", "ミミュミュウミーミーミュウミュウミミ", "ミュウミみミュみミミュミュミュミュウ", "ミュウミュミュミュミュウ"], "answer_index": 0},
    {"q": "ミュウミュミュミュウミュミュミュウウミュウ？", "choices": ["ミュウミミミュミュミュミュウミ", "ミュウーミミュミュミュウミュウ", "ミュウミュウミュミュミュミュミュ", "ミミミュミュミュムミュウミミミュ"], "answer_index": 1},
    {"q": "ミュミュミミュウミュユミミュミュウ？", "choices": ["ミュウミュミュミュミュ、ミーミュユミュミュウ", "ミミュミュミーミーミュ。ミュミュミーミュミュ", "ミュウミュミュミュウ。ミュウミーみミュミュウ", "ミュウ。"], "answer_index": 0},
    {"q": "ミュミュミュミュミューーミュウミュウミュウミュウミュウ？", "choices": ["ミュウミュユミュミュミューミュウミュウミュウミュウ", "ミュウ。ミミュミュミュミーミミュミュミュミュミュウ", "ミミミュミュミュミュウ", "ミュウミュミュミュミュミュミュミュミュミュミュ"], "answer_index": 1},
    {"q": "ミュミュミュミュウミュウミュウミュウミュウミュウミュウミュウ？", "choices": ["ミュウ!", "ミュウ?", "ミュウ。", "ミュウ♪"], "answer_index": 0},
]

async def send_myurion_question(message, user_id, correct_count, state_dict):
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
    if use_ticket:
        if num_pulls != 10: return False, "チケットは10連専用みたい。"
        if state.get("offbanner_tickets", 0) <= 0: return False, "チケットが足りないみたい。"
        state["offbanner_tickets"] -= 1
        cost_str = "（チケット1枚消費）"
    else:
        cost = 160 * num_pulls if num_pulls == 1 else 1600
        if state.get("stones", 0) < cost: return False, f"石が足りないみたい（必要: {cost}）"
        state["stones"] -= cost
        cost_str = f"（石 {cost} 個消費）"

    pity_5 = state.get("pity_5", 0)
    pity_4 = state.get("pity_4", 0)
    guaranteed = state.get("guaranteed_cyrene", False)
    results, cyrene_hit, off_hit, page_hits = [], 0, 0, 0

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
                txt = "★5【キュレネ】"
            else:
                state["offbanner_tickets"] = state.get("offbanner_tickets", 0) + 1
                guaranteed, off_hit = True, off_hit + 1
                txt = "★5【すり抜け（チケット獲得）】"
            if page_got: txt += " ＋ ★5【??? その1】"
        else:
            pity_5 += 1
            if pity_4 >= 9 or random.random() < 0.24:
                pity_4 = 0
                txt = "★4"
            else:
                pity_4 += 1
                txt = "★3"
            if page_got: txt += " ＋ ★5【??? その1】"
        results.append(txt)

    state["pity_5"], state["pity_4"], state["guaranteed_cyrene"] = pity_5, pity_4, guaranteed
    db.save_gacha_state(user_id, state)

    summary = []
    if cyrene_hit: summary.append(f"★5キュレネ: {cyrene_hit}")
    if off_hit: summary.append(f"★5すり抜け: {off_hit}")
    if page_hits: summary.append(f"★5ページ: {page_hits}")
    sum_text = " / ".join(summary) if summary else "★5なし"
    
    body = "\n".join([f"{i+1}: {r}" for i, r in enumerate(results)])
    return True, f"{cost_str}\n{body}\n\n{sum_text}\n現在の石: {state['stones']} / チケット: {state['offbanner_tickets']}"

def grant_daily_stones(user_id: int) -> tuple[bool, int, str]:
    state = db.get_gacha_state(user_id)
    if state.get("last_daily") == today_str():
        return False, state["stones"], "今日はもう受け取っているみたい。"
    state["stones"] = state.get("stones", 0) + 16000
    state["last_daily"] = today_str()
    db.save_gacha_state(user_id, state)
    return True, state["stones"], "デイリー報酬 16000個 を付与したわ♪"

# ★追加：ガチャステータス表示
def format_gacha_status(user_id: int) -> str:
    state = db.get_gacha_state(user_id)
    stones = state.get("stones", 0)
    pity_5 = state.get("pity_5", 0)
    cyrene_copies = state.get("cyrene_copies", 0)
    tickets = state.get("offbanner_tickets", 0)
    guaranteed = state.get("guaranteed_cyrene", False)
    mult = get_cyrene_affection_multiplier(user_id)
    
    next_up = "キュレネ確定" if guaranteed else "50%でキュレネ"
    
    return (
        "【ガチャメニュー】\n"
        f"・所持石: {stones} 個\n"
        f"・キュレネ所持: {cyrene_copies} 枚 (好感度倍率 x{mult:.1f})\n"
        f"・すり抜けチケット: {tickets} 枚\n"
        f"・天井カウント: {pity_5} 連 (次の★5は {next_up})\n\n"
        "『単発ガチャ』『10連ガチャ』で引けるわよ♪"
    )

# --- じゃんけんロジック ---
JANKEN_HANDS = ["グー", "チョキ", "パー"]

# ★追加：これが抜けていたためエラーになっていました
def parse_hand(text: str):
    if "グー" in text: return "グー"
    if "チョキ" in text: return "チョキ"
    if "パー" in text: return "パー"
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