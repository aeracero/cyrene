# forms.py
import json
from pathlib import Path

# 変身状態（黄金裔 / 開拓者）を管理するためのモジュール。
# - 保存先: /data/forms.json
# - form_key: 英字のキー（例: "cyrene", "aglaia", "nanoka" など）

DATA_DIR = Path("/data")
DATA_DIR.mkdir(parents=True, exist_ok=True)
FORMS_FILE = DATA_DIR / "forms.json"

# 利用可能なフォームのキーと表示名
FORM_DISPLAY_NAMES = {
    "cyrene": "キュレネ",
    "aglaia": "アグライア",
    "trisbeas": "トリスビアス",
    "anaxagoras": "アナクサゴラス",
    "hyacinthia": "ヒアシンシア",
    "medimos": "メデイモス",
    "sepharia": "セファリア",
    "castoris": "キャストリス",
    "phainon_kasreina": "ファイノン・カスライナ",
    "electra": "ヘレクトラ",
    "cerydra": "ケリュドラ",
    "nanoka": "三月なのか / 長夜月",
    "danheng": "丹恒",
    "furina": "フリーナ",
    "momo": "モモ",
}

# 変身コード → フォームキー
# ユーザーが「変身」後に入力するコード
FORM_CODE_MAP = {
    "kalos618": "aglaia",             # アグライア
    "haplotes405": "trisbeas",        # トリスビアス
    "skemma720": "anaxagoras",        # アナクサゴラス
    "eleos252": "hyacinthia",         # ヒアシンシア
    "polemos600": "medimos",          # メデイモス
    "orexis945": "sepharia",          # セファリア
    "epieikeia216": "castoris",       # キャストリス
    "neikos496": "phainon_kasreina",  # ファイノン・カスライナ
    "aporia432": "electra",           # ヘレクトラ
    "hubris504": "cerydra",           # ケリュドラ
    "philia093": "cyrene",            # キュレネ
    "グロシ":"furina",               # フリーナ
    # 必要ならここに追加
}

# 日本語名などからフォームキーを解決するための別名テーブル
FORM_NAME_ALIASES = {
    "キュレネ": "cyrene",
    "アグライア": "aglaia",
    "トリスビアス": "trisbeas",
    "アナクサゴラス": "anaxagoras",
    "ヒアシンシア": "hyacinthia",
    "メデイモス": "medimos",
    "セファリア": "sepharia",
    "キャストリス": "castoris",
    "ファイノン・カスライナ": "phainon_kasreina",
    "ヘレクトラ": "electra",
    "ケリュドラ": "cerydra",
    "三月なのか": "nanoka",
    "なのか": "nanoka",
    "長夜月": "nanoka",
    "丹恒": "danheng",
    "フリーナ": "furina",
    "モモ": "momo",
}

VALID_FORM_KEYS = set(FORM_DISPLAY_NAMES.keys())


def load_forms() -> dict:
    """保存されているフォーム情報を読み込む {user_id(str): form_key}"""
    if not FORMS_FILE.exists():
        return {}
    try:
        data = json.loads(FORMS_FILE.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return {}
        return data
    except Exception:
        return {}


def save_forms(data: dict):
    FORMS_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def get_user_form(user_id: int) -> str:
    """
    指定ユーザーのフォームキーを取得。
    保存されていない場合は 'cyrene'（キュレネ）を返す。
    """
    data = load_forms()
    key = data.get(str(user_id))
    if key in VALID_FORM_KEYS:
        return key
    return "cyrene"


def set_user_form(user_id: int, form_key: str):
    """
    指定ユーザーのフォームを設定。
    無効な form_key の場合は 'cyrene' にフォールバック。
    """
    if form_key not in VALID_FORM_KEYS:
        form_key = "cyrene"
    data = load_forms()
    data[str(user_id)] = form_key
    save_forms(data)


def get_all_forms() -> dict:
    """全ユーザーのフォーム dict を返す。"""
    return load_forms()


def set_all_forms(form_key: str):
    """
    登録されている全ユーザーのフォームを一括変更。
    新しいユーザーのデフォルトまでは変えない。
    """
    if form_key not in VALID_FORM_KEYS:
        form_key = "cyrene"
    data = load_forms()
    for uid in list(data.keys()):
        data[uid] = form_key
    save_forms(data)


def get_form_display_name(form_key: str) -> str:
    """フォームキーから、Discord上で見せる日本語名（デフォルト: キュレネ）を返す。"""
    return FORM_DISPLAY_NAMES.get(form_key, "キュレネ")


def resolve_form_code(code: str):
    """
    ユーザーが入力した変身コードからフォームキーを解決。
    大文字小文字・空白は無視。
    """
    if not code:
        return None
    normalized = code.strip().replace(" ", "").replace("　", "").lower()
    return FORM_CODE_MAP.get(normalized)


def resolve_form_spec(spec: str):
    """
    データ管理モード用:
    - コード（KaLos618 など）
    - 英字フォームキー（aglaia など）
    - 日本語名（アグライア など）
    のいずれかからフォームキーを解決する。
    """
    if not spec:
        return None

    s = spec.strip()

    # 1) コードとして解釈
    key = resolve_form_code(s)
    if key:
        return key

    # 2) 英字フォームキーとして解釈（大文字小文字は無視）
    lower = s.lower()
    for fk in VALID_FORM_KEYS:
        if fk.lower() == lower:
            return fk

    # 3) 日本語名などの別名として解釈
    alias_key = FORM_NAME_ALIASES.get(s)
    if alias_key in VALID_FORM_KEYS:
        return alias_key

    return None
