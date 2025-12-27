# reply_system.py
import lines
# 各キャラのモジュールをインポート
import lines_aglaia, lines_trisbeas, lines_anaxagoras, lines_hyacinthia
import lines_medimos, lines_sepharia, lines_castoris, lines_phainon_kasreina
import lines_electra, lines_cerydra, lines_nanoka, lines_danheng, lines_furina, lines_momo

# フォームキーとモジュールの対応表
MODULE_MAP = {
    "aglaia": lines_aglaia, "trisbeas": lines_trisbeas, "anaxagoras": lines_anaxagoras,
    "hyacinthia": lines_hyacinthia, "medimos": lines_medimos, "sepharia": lines_sepharia,
    "castoris": lines_castoris, "phainon_kasreina": lines_phainon_kasreina, "electra": lines_electra,
    "cerydra": lines_cerydra, "nanoka": lines_nanoka, "danheng": lines_danheng,
    "furina": lines_furina, "momo": lines_momo,
}

def _get_module(form_key):
    return MODULE_MAP.get(form_key)

def generate_reply_for_form(form_key: str, message_text: str, affection_level: int, user_id: int, name: str) -> str:
    mod = _get_module(form_key)
    base = ""
    
    if mod and hasattr(mod, "get_reply"):
        # キャラ固有の返答
        try:
            # 引数が合わない場合への保険（user_idが必要な古い仕様など）
            import inspect
            sig = inspect.signature(mod.get_reply)
            if len(sig.parameters) == 3:
                base = mod.get_reply(message_text, affection_level, user_id)
            else:
                base = mod.get_reply(message_text, affection_level)
        except:
            base = lines.get_cyrene_reply(message_text, affection_level)
    else:
        # デフォルト（キュレネ）
        base = lines.get_cyrene_reply(message_text, affection_level)
    
    # あだ名置換
    if name:
        base = base.replace("「あだ名」", f"「{name}」").replace("あだ名", name).replace("{nickname}", name)
    return base

def get_nickname_message_for_form(form_key: str, action: str, name: str = "") -> str:
    mod = _get_module(form_key)
    if mod and hasattr(mod, "get_nickname_line"):
        try:
            return mod.get_nickname_line(action).replace("{nickname}", name).replace("{name}", name)
        except: pass
    
    # デフォルト
    if action == "ask": return "あたし、どう呼べばいいの？"
    elif action == "confirm": return f"ふふ…これからは「{name}」って呼ぶわね♪"
    return ""

def get_rps_prompt_for_form(form_key: str, name: str) -> str:
    mod = _get_module(form_key)
    # モジュール側に rps_start 定義があれば使う
    if mod and hasattr(mod, "LINES") and "rps_start" in mod.LINES:
        import random
        return random.choice(mod.LINES["rps_start"]).replace("{nickname}", name).replace("{name}", name)
    
    return "じゃんけんをしましょう♪ グー / チョキ / パー、どれにするかしら？"

def generate_rps_message(form_key: str, user_hand: str, bot_hand: str, result: str, wins: int, name: str) -> str:
    """じゃんけん結果のメッセージを生成（一人称・語尾対応）"""
    mod = _get_module(form_key)
    
    # デフォルト設定 (キュレネ)
    profile = {"first_person": "あたし", "rps_tail": "わ♡"}
    flavor = lines.get_rps_line(result)

    # キャラ固有設定があれば上書き
    if mod:
        if hasattr(mod, "PROFILE"):
            profile.update(mod.PROFILE)
        if hasattr(mod, "get_rps_flavor"):
            flavor = mod.get_rps_flavor(result)
        elif hasattr(mod, "LINES") and f"rps_{result}" in mod.LINES:
            import random
            flavor = random.choice(mod.LINES[f"rps_{result}"])

    # あだ名置換
    flavor = flavor.replace("{nickname}", name).replace("{name}", name)
    
    return (
        f"{name} は **{user_hand}**、{profile['first_person']}は **{bot_hand}** だ。\n"
        f"{flavor}\n"
        f"（これまでに {wins} 回、{profile['first_person']}に勝っている{profile['rps_tail']}）"
    )