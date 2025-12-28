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
            base = module.get_reply(message_text, affection_level, name)
        except TypeError:
            try:
                # ★優先2: 従来の形式（本文, 好感度）で呼び出す
                base = module.get_reply(message_text, affection_level)
            except TypeError:
                # ★優先3: さらに古い形式（本文のみ）
                base = module.get_reply(message_text)
    else:
        base = lines_cyrene.get_cyrene_reply(message_text, affection_level)

    if name:
        base = base.replace("「あだ名」", f"「{name}」").replace("あだ名", name).replace("{nickname}", name).replace("{name}", name)
    return base

def get_nickname_message_for_form(form_key: str, action: str, name: str = "") -> str:
    module = MODULE_MAP.get(form_key, lines_cyrene)
    
    if hasattr(module, "get_nickname_line"):
        try:
            line = module.get_nickname_line(action, name)
        except TypeError:
            line = module.get_nickname_line(action)
        return line.replace("{name}", name)
    
    if action == "ask": return "あたし、どう呼べばいいの？"
    elif action == "confirm": return f"ふふ…これからは「{name}」って呼ぶわね♪"
    return ""

def get_rps_flavor(form_key: str, result: str, name: str) -> str:
    module = MODULE_MAP.get(form_key, lines_cyrene)
    
    if hasattr(module, "get_rps_flavor"):
        try:
            return module.get_rps_flavor(result, name)
        except TypeError:
            pass 

    if hasattr(module, "LINES"):
        lines_dict = module.LINES
        key = f"rps_{result}"
        if key in lines_dict and lines_dict[key]:
            base = random.choice(lines_dict[key])
            return base.replace("{nickname}", name).replace("{name}", name)
            
    return lines_cyrene.get_rps_line(result)

def get_rps_prompt_for_form(form_key: str, name: str) -> str:
    module = MODULE_MAP.get(form_key, lines_cyrene)
    
    if hasattr(module, "LINES"):
        lines_dict = module.LINES
        if "rps_start" in lines_dict and lines_dict["rps_start"]:
            base = random.choice(lines_dict["rps_start"])
            return base.replace("{nickname}", name).replace("{name}", name)
    
    return "じゃんけんをしましょう♪ グー / チョキ / パー、どれにするかしら？"

# ★重要修正: フォーマットを柔軟に変更可能にしました
def format_rps_result(form_key: str, name: str, user_hand: str, bot_hand: str, flavor: str, wins: int) -> str:
    module = MODULE_MAP.get(form_key, lines_cyrene)
    
    # デフォルト設定 (キュレネ用)
    # これが基本の形です。各キャラファイルで上書きできます。
    duel_fmt = "{name} は **{user_hand}**、あたしは **{bot_hand}** よ。"
    stats_fmt = "（これまでに {wins} 回、あたしに勝っているわ♡）"
    
    # キャラごとの設定 (PROFILE) を読み込む
    if hasattr(module, "PROFILE"):
        profile = module.PROFILE
        # PROFILE辞書にフォーマットがあればそれを使う
        if "rps_duel_format" in profile:
            duel_fmt = profile["rps_duel_format"]
        elif "first_person" in profile:
             # フォーマット指定がない場合の自動生成（簡易版）
             fp = profile["first_person"]
             # 「僕は〜だ」のようにしたい場合、ここだと制御しきれないので
             # 基本的には各ファイルで format を指定することを推奨
             duel_fmt = f"{{name}} は **{{user_hand}}**、{fp}は **{{bot_hand}}** だ。"

        if "rps_stats_format" in profile:
            stats_fmt = profile["rps_stats_format"]
    
    # フォーマットを適用
    # user_name, user_hand, bot_hand, wins が使えます
    try:
        duel_msg = duel_fmt.format(name=name, user_hand=user_hand, bot_hand=bot_hand)
        stats_msg = stats_fmt.format(name=name, wins=wins)
    except:
        # 万が一フォーマットエラーが出た場合の安全策
        duel_msg = f"{name} : {user_hand} vs {bot_hand}"
        stats_msg = f"(Wins: {wins})"

    return f"{duel_msg}\n{flavor}\n{stats_msg}"