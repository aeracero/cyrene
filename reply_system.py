import random
import database as db
import lines as lines_cyrene

# 各キャラのモジュールをインポート
import lines_aglaia, lines_trisbeas, lines_anaxagoras
import lines_hyacinthia, lines_medimos, lines_sepharia, lines_castoris
import lines_phainon_kasreina, lines_electra, lines_cerydra
import lines_nanoka, lines_danheng, lines_furina, lines_momo

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
    
    if hasattr(module, "get_reply"):
        try:
            # ★優先1: 最新の形式（本文, 好感度, 名前）で呼び出す
            # ヒアシンシア、ケリュドラなどはこっち
            base = module.get_reply(message_text, affection_level, name)
        except TypeError:
            try:
                # ★優先2: 従来の形式（本文, 好感度）で呼び出す
                # まだ修正していない他のキャラはこっち
                base = module.get_reply(message_text, affection_level)
            except TypeError:
                # ★優先3: さらに古い形式（本文のみ）
                base = module.get_reply(message_text)
    else:
        base = lines_cyrene.get_cyrene_reply(message_text, affection_level)

    if name:
        # モジュール側で対応していても、念のためここでも置換を実行しておく（安全策）
        base = base.replace("「あだ名」", f"「{name}」").replace("あだ名", name).replace("{nickname}", name).replace("{name}", name)
    return base

def get_nickname_message_for_form(form_key: str, action: str, name: str = "") -> str:
    module = MODULE_MAP.get(form_key, lines_cyrene)
    
    if hasattr(module, "get_nickname_line"):
        try:
            # ★修正: 名前引数ありを優先
            line = module.get_nickname_line(action, name)
        except TypeError:
            # 引数なしの旧バージョン
            line = module.get_nickname_line(action)
        return line.replace("{name}", name)
    
    if action == "ask": return "あたし、どう呼べばいいの？"
    elif action == "confirm": return f"ふふ…これからは「{name}」って呼ぶわね♪"
    return ""

def get_rps_flavor(form_key: str, result: str, name: str) -> str:
    module = MODULE_MAP.get(form_key, lines_cyrene)
    
    # もしモジュールに専用の関数があれば、そちらを優先的に試す（新しい形式への対応）
    if hasattr(module, "get_rps_flavor"):
        try:
            return module.get_rps_flavor(result, name)
        except TypeError:
            pass # 引数が合わなければ下のLINES取得処理へ進む

    if hasattr(module, "LINES"):
        lines_dict = module.LINES
        key = f"rps_{result}"
        if key in lines_dict and lines_dict[key]:
            base = random.choice(lines_dict[key])
            return base.replace("{nickname}", name).replace("{name}", name)
            
    return lines_cyrene.get_rps_line(result)

# ★ここが重要：じゃんけん開始時のセリフ
def get_rps_prompt_for_form(form_key: str, name: str) -> str:
    module = MODULE_MAP.get(form_key, lines_cyrene)
    
    # 各キャラファイルの LINES["rps_start"] を優先
    if hasattr(module, "LINES"):
        lines_dict = module.LINES
        if "rps_start" in lines_dict and lines_dict["rps_start"]:
            base = random.choice(lines_dict["rps_start"])
            return base.replace("{nickname}", name).replace("{name}", name)
    
    # デフォルト（キュレネ）
    return "じゃんけんをしましょう♪ グー / チョキ / パー、どれにするかしら？"

def format_rps_result(form_key: str, name: str, user_hand: str, bot_hand: str, flavor: str, wins: int) -> str:
    module = MODULE_MAP.get(form_key, lines_cyrene)
    
    pronoun = "あたし"
    tail = "わ♡"
    
    if hasattr(module, "PROFILE"): # CHAR_PROFILE -> PROFILE に統一されている場合が多いので変更を推奨
        profile = module.PROFILE
        pronoun = profile.get("first_person", pronoun) # "pronoun" or "first_person"
        tail = profile.get("rps_tail", tail)
    elif hasattr(module, "CHAR_PROFILE"):
        profile = module.CHAR_PROFILE
        pronoun = profile.get("pronoun", pronoun)
        tail = profile.get("rps_tail", tail)
        
    return (
        f"{name} は **{user_hand}**、{pronoun}は **{bot_hand}** だ。\n"
        f"{flavor}\n"
        f"（これまでに {wins} 回、{pronoun}に勝っている{tail}）"
    )