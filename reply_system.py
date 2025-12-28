import random
import database as db
import lines as lines_cyrene

# 各キャラのモジュールをインポート
import lines_aglaia, lines_trisbeas, lines_anaxagoras, lines_hyacinthia
import lines_medimos, lines_sepharia, lines_castoris, lines_phainon_kasreina
import lines_electra, lines_cerydra, lines_nanoka, lines_danheng, lines_furina, lines_momo

MODULE_MAP = {
    "cyrene": lines_cyrene,
    "aglaia": lines_aglaia,
    "trisbeas": lines_trisbeas,
    "anaxagoras": lines_anaxagoras,
    "hyacinthia": lines_hyacinthia,
    "medimos": lines_medimos,
    "sepharia": lines_sepharia,
    "castoris": lines_castoris,
    "phainon_kasreina": lines_phainon_kasreina,
    "electra": lines_electra,
    "cerydra": lines_cerydra,
    "nanoka": lines_nanoka,
    "danheng": lines_danheng,
    "furina": lines_furina,
    "momo": lines_momo,
}

def generate_reply_for_form(form_key: str, message_text: str, affection_level: int, user_id: int, name: str) -> str:
    module = MODULE_MAP.get(form_key, lines_cyrene)
    lang = db.get_user_lang(user_id) # 言語取得
    
    if hasattr(module, "get_reply"):
        try:
            # 優先1: 言語引数つき (get_reply(msg, lv, name, lang))
            base = module.get_reply(message_text, affection_level, name, lang)
        except TypeError:
            try:
                # 優先2: 言語なし (get_reply(msg, lv, name))
                base = module.get_reply(message_text, affection_level, name)
            except TypeError:
                # 優先3: 古い形式
                try:
                    base = module.get_reply(message_text, affection_level)
                except TypeError:
                     base = module.get_reply(message_text)
    else:
        base = "..."

    if name:
        base = base.replace("「あだ名」", f"「{name}」").replace("あだ名", name).replace("{nickname}", name).replace("{name}", name)
    return base

def get_nickname_message_for_form(form_key: str, action: str, name: str, user_id: int) -> str:
    module = MODULE_MAP.get(form_key, lines_cyrene)
    lang = db.get_user_lang(user_id)
    
    if hasattr(module, "get_nickname_line"):
        try:
            line = module.get_nickname_line(action, name, lang)
            return line.replace("{name}", name)
        except TypeError:
            try:
                line = module.get_nickname_line(action, name)
                return line.replace("{name}", name)
            except: pass

    # デフォルトメッセージ
    if lang == "en":
        return "What should I call you?" if action == "ask" else f"Okay, I'll call you '{name}' from now on."
    else:
        return "あたし、どう呼べばいいの？" if action == "ask" else f"ふふ…これからは「{name}」って呼ぶわね♪"

# ★修正: user_id を受け取るように変更 (エラー箇所)
def get_rps_flavor(form_key: str, result: str, name: str, user_id: int) -> str:
    module = MODULE_MAP.get(form_key, lines_cyrene)
    lang = db.get_user_lang(user_id)

    if hasattr(module, "get_rps_flavor"):
        try:
            return module.get_rps_flavor(result, name, lang)
        except TypeError:
            try:
                return module.get_rps_flavor(result, name)
            except: pass

    # フォールバック (LINES_EN / LINES 直接参照)
    target_lines = getattr(module, "LINES_EN" if lang == "en" else "LINES", getattr(module, "LINES", {}))
    key = f"rps_{result}"
    if key in target_lines:
        return random.choice(target_lines[key]).replace("{name}", name)
            
    return ""

# ★修正: user_id を受け取るように変更 (エラー箇所)
def get_rps_prompt_for_form(form_key: str, name: str, user_id: int) -> str:
    module = MODULE_MAP.get(form_key, lines_cyrene)
    lang = db.get_user_lang(user_id)
    
    target_lines = getattr(module, "LINES_EN" if lang == "en" else "LINES", getattr(module, "LINES", {}))
    
    if "rps_start" in target_lines:
        return random.choice(target_lines["rps_start"]).replace("{name}", name)
    
    return "Let's play RPS! Rock, Paper, or Scissors?" if lang == "en" else "じゃんけんをしましょう♪ グー / チョキ / パー、どれにするかしら？"

# ★修正: user_id を受け取るように変更 (エラー箇所)
def format_rps_result(form_key: str, name: str, user_hand: str, bot_hand: str, flavor: str, wins: int, user_id: int) -> str:
    module = MODULE_MAP.get(form_key, lines_cyrene)
    lang = db.get_user_lang(user_id)
    
    # 手の翻訳 (ENモード時)
    if lang == "en":
        hand_map = {"グー": "Rock", "チョキ": "Scissors", "パー": "Paper"}
        user_hand = hand_map.get(user_hand, user_hand)
        bot_hand = hand_map.get(bot_hand, bot_hand)
        duel_fmt = "{name} chose **{user_hand}**, I chose **{bot_hand}**."
        stats_fmt = "(Wins: {wins})"
    else:
        duel_fmt = "{name} は **{user_hand}**、あたしは **{bot_hand}** よ。"
        stats_fmt = "（これまでに {wins} 回、あたしに勝っているわ♡）"
    
    if hasattr(module, "PROFILE"):
        profile = module.PROFILE
        d_key = "rps_duel_format_en" if lang == "en" else "rps_duel_format"
        s_key = "rps_stats_format_en" if lang == "en" else "rps_stats_format"
        
        if d_key in profile: duel_fmt = profile[d_key]
        elif "rps_duel_format" in profile and lang != "en": duel_fmt = profile["rps_duel_format"]

        if s_key in profile: stats_fmt = profile[s_key]
        elif "rps_stats_format" in profile and lang != "en": stats_fmt = profile["rps_stats_format"]
    
    try:
        duel_msg = duel_fmt.format(name=name, user_hand=user_hand, bot_hand=bot_hand)
        stats_msg = stats_fmt.format(name=name, wins=wins)
    except:
        duel_msg = f"{name}: {user_hand} vs {bot_hand}"
        stats_msg = f"(Wins: {wins})"

    return f"{duel_msg}\n{flavor}\n{stats_msg}"