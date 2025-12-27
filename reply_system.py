# reply_system.py
from lines import get_cyrene_reply, get_rps_line
from lines_aglaia import get_reply as get_aglaia_reply
from lines_trisbeas import get_reply as get_trisbeas_reply
from lines_anaxagoras import get_reply as get_anaxagoras_reply
from lines_hyacinthia import get_reply as get_hyacinthia_reply, get_nickname_line as get_hyacinthia_nickname_line
from lines_medimos import get_reply as get_medimos_reply
from lines_sepharia import get_reply as get_sepharia_reply
from lines_castoris import get_reply as get_castoris_reply
from lines_phainon_kasreina import get_reply as get_phainon_kasreina_reply
from lines_electra import get_reply as get_electra_reply
from lines_cerydra import get_reply as get_cerydra_reply
from lines_nanoka import get_reply as get_nanoka_reply
from lines_danheng import get_reply as get_danheng_reply
from lines_furina import get_reply as get_furina_reply
from lines_momo import get_reply as get_momo_reply

def generate_reply_for_form(form_key: str, message_text: str, affection_level: int, user_id: int, name: str) -> str:
    form_handlers = {
        "aglaia": get_aglaia_reply, "trisbeas": get_trisbeas_reply, "anaxagoras": get_anaxagoras_reply,
        "hyacinthia": get_hyacinthia_reply, "medimos": get_medimos_reply, "sepharia": get_sepharia_reply,
        "castoris": get_castoris_reply, "phainon_kasreina": get_phainon_kasreina_reply, "electra": get_electra_reply,
        "cerydra": get_cerydra_reply, "nanoka": get_nanoka_reply, "danheng": get_danheng_reply,
        "furina": get_furina_reply, "momo": get_momo_reply,
    }
    handler = form_handlers.get(form_key)
    if handler:
        base = handler(message_text, affection_level)
    else:
        try: base = get_cyrene_reply(message_text, affection_level)
        except: base = get_cyrene_reply(message_text)
    
    if name:
        base = base.replace("「あだ名」", f"「{name}」").replace("あだ名", name).replace("{nickname}", name)
    return base

def get_nickname_message_for_form(form_key: str, action: str, name: str = "") -> str:
    if form_key == "hyacinthia":
        try: return get_hyacinthia_nickname_line(action).replace("{name}", name)
        except: pass
    if action == "ask": return "あたし、どう呼べばいいの？"
    elif action == "confirm": return f"ふふ…これからは「{name}」って呼ぶわね♪"
    return ""

def get_rps_flavor(form_key: str, result: str, name: str) -> str:
    if form_key == "hyacinthia":
        return {"win": "ふふ、お見事です〜。", "lose": "あら、わたしの勝ちですね〜。", "draw": "おや、あいこですね〜。"}.get(result, "")
    # 必要に応じて他キャラも追加
    return get_rps_line(result)