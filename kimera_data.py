# kimera_data.py
# キメラ、技、アイテム、トレーナー、タイプ相性等のデータを管理します。

# --- タイプ定義と相性表 ---
TYPES = ["Normal", "Fire", "Water", "Grass", "Light", "Dark", "Fairy"]

# 攻撃側をキー、防御側をキーとして倍率を定義 (定義なき場合は1.0)
TYPE_CHART = {
    "Normal": {"Light": 0.5, "Dark": 0.5},
    "Fire":   {"Grass": 2.0, "Water": 0.5, "Fire": 0.5, "Fairy": 1.0},
    "Water":  {"Fire": 2.0, "Grass": 0.5, "Water": 0.5},
    "Grass":  {"Water": 2.0, "Fire": 0.5, "Grass": 0.5, "Light": 1.0},
    "Light":  {"Dark": 2.0, "Grass": 2.0, "Light": 0.5, "Fairy": 0.5},
    "Dark":   {"Light": 2.0, "Fairy": 2.0, "Dark": 0.5, "Normal": 2.0},
    "Fairy":  {"Dark": 2.0, "Fire": 0.5, "Light": 2.0, "Fairy": 0.5}
}

# --- 状態異常定義 ---
STATUS_CONDITIONS = {
    "poison": {"name": "毒", "desc": "毎ターンHPが減るわ。"},
    "paralysis": {"name": "麻痺", "desc": "素早さが下がり、たまに動けないわ。"},
    "sleep": {"name": "眠り", "desc": "数ターン動けないわ。"},
    "burn": {"name": "火傷", "desc": "毎ターンHPが減り、物理攻撃が下がるわ。"},
    "confusion": {"name": "混乱", "desc": "たまに自分を攻撃してしまうわ。"},
    # 以下は特殊状態
    "oblivion": {"name": "忘却", "desc": "直前の技が使えず、命中率ダウン。"},
    "submission": {"name": "屈服", "desc": "与えるダメージ低下。捕獲されやすい。"},
    "recharge": {"name": "反動待機", "desc": "強力な技の反動で動けない。"}
}

# --- 技データ (MOVES) ---
# category: Physical(物理), Special(特殊), Status(変化)
# effect types: 
#   buff/debuff (stat, stage)
#   status (status)
#   recoil (percent of damage taken)
#   recharge (skip next turn)
#   debuff_self (stat, stage)
MOVES = {
    # 物理技
    "scratch": {"name": "ひっかく", "type": "Normal", "category": "Physical", "power": 40, "accuracy": 100, "max_pp": 35, "target": "Enemy"},
    "tackle": {"name": "たいあたり", "type": "Normal", "category": "Physical", "power": 40, "accuracy": 100, "max_pp": 35, "target": "Enemy"},
    "leaf_blade": {"name": "リーフブレード", "type": "Grass", "category": "Physical", "power": 90, "accuracy": 100, "max_pp": 15, "target": "Enemy"},
    "shadow_claw": {"name": "シャドークロー", "type": "Dark", "category": "Physical", "power": 70, "accuracy": 100, "max_pp": 15, "target": "Enemy"},
    "dragon_claw": {"name": "ドラゴンクロー", "type": "Normal", "category": "Physical", "power": 80, "accuracy": 100, "max_pp": 15, "target": "Enemy"},
    "quick_attack": {"name": "電光石火", "type": "Normal", "category": "Physical", "power": 40, "accuracy": 100, "max_pp": 30, "priority": 1, "target": "Enemy"},
    "flare_blitz": {"name": "フレアドライブ", "type": "Fire", "category": "Physical", "power": 120, "accuracy": 100, "max_pp": 15, "target": "Enemy", "effect": {"type": "recoil", "percent": 0.33}, "desc": "高威力だが反動ダメージを受ける。"},
    "giga_impact": {"name": "ギガインパクト", "type": "Normal", "category": "Physical", "power": 150, "accuracy": 90, "max_pp": 5, "target": "Enemy", "effect": {"type": "recharge"}, "desc": "超高威力だが次のターン動けない。"},

    # 特殊技
    "ember": {"name": "火の粉", "type": "Fire", "category": "Special", "power": 40, "accuracy": 100, "max_pp": 25, "target": "Enemy"},
    "water_gun": {"name": "水鉄砲", "type": "Water", "category": "Special", "power": 40, "accuracy": 100, "max_pp": 25, "target": "Enemy"},
    "shining_ray": {"name": "光の矢", "type": "Light", "category": "Special", "power": 60, "accuracy": 100, "max_pp": 20, "target": "Enemy"},
    "flamethrower": {"name": "火炎放射", "type": "Fire", "category": "Special", "power": 90, "accuracy": 100, "max_pp": 15, "target": "Enemy", "effect": {"type": "chance_status", "status": "burn", "chance": 0.1}},
    "hydro_pump": {"name": "ハイドロポンプ", "type": "Water", "category": "Special", "power": 110, "accuracy": 80, "max_pp": 5, "target": "Enemy"},
    "solar_beam": {"name": "ソーラービーム", "type": "Grass", "category": "Special", "power": 120, "accuracy": 100, "max_pp": 10, "target": "Enemy"},
    "hyper_beam": {"name": "破壊光線", "type": "Normal", "category": "Special", "power": 150, "accuracy": 90, "max_pp": 5, "target": "Enemy", "effect": {"type": "recharge"}, "desc": "超高威力だが次のターン動けない。"},
    "dark_pulse": {"name": "悪の波動", "type": "Dark", "category": "Special", "power": 80, "accuracy": 100, "max_pp": 15, "target": "Enemy"},
    "flash_cannon": {"name": "ラスターカノン", "type": "Light", "category": "Special", "power": 80, "accuracy": 100, "max_pp": 10, "target": "Enemy"},
    "dragon_breath": {"name": "竜の息吹", "type": "Light", "category": "Special", "power": 60, "accuracy": 100, "max_pp": 20, "target": "Enemy", "effect": {"type": "chance_status", "status": "paralysis", "chance": 0.3}},
    "dazzling_gleam": {"name": "マジカルシャイン", "type": "Fairy", "category": "Special", "power": 80, "accuracy": 100, "max_pp": 10, "target": "Enemy"},
    "draco_meteor": {"name": "流星群", "type": "Normal", "category": "Special", "power": 130, "accuracy": 90, "max_pp": 5, "target": "Enemy", "effect": {"type": "debuff_self", "stat": "spa", "stage": 2}, "desc": "高威力だが使用後に特攻がガクッと下がる。"},

    # 変化技 (バフ・デバフ・状態異常)
    "growl": {"name": "鳴き声", "type": "Normal", "category": "Status", "power": 0, "accuracy": 100, "max_pp": 40, "target": "Enemy", "effect": {"type": "debuff", "stat": "atk", "stage": 1}},
    "tail_whip": {"name": "しっぽをふる", "type": "Normal", "category": "Status", "power": 0, "accuracy": 100, "max_pp": 40, "target": "Enemy", "effect": {"type": "debuff", "stat": "def", "stage": 1}},
    "sharpen": {"name": "つるぎのまい", "type": "Normal", "category": "Status", "power": 0, "accuracy": 100, "max_pp": 20, "target": "Self", "effect": {"type": "buff", "stat": "atk", "stage": 2}},
    "growth": {"name": "成長", "type": "Normal", "category": "Status", "power": 0, "accuracy": 100, "max_pp": 20, "target": "Self", "effect": {"type": "buff", "stat": "spa", "stage": 1}},
    "poison_powder": {"name": "毒の粉", "type": "Grass", "category": "Status", "power": 0, "accuracy": 75, "max_pp": 35, "target": "Enemy", "effect": {"type": "status", "status": "poison"}},
    "thunder_wave": {"name": "電磁波", "type": "Light", "category": "Status", "power": 0, "accuracy": 90, "max_pp": 20, "target": "Enemy", "effect": {"type": "status", "status": "paralysis"}},
    "sing": {"name": "歌う", "type": "Normal", "category": "Status", "power": 0, "accuracy": 55, "max_pp": 15, "target": "Enemy", "effect": {"type": "status", "status": "sleep"}},
    "recover": {"name": "自己再生", "type": "Normal", "category": "Status", "power": 0, "accuracy": 100, "max_pp": 10, "target": "Self", "effect": {"type": "heal", "percent": 0.5}},

    # 黄金裔専用技 (デメリット付きなど強力な技)
    "golden_rush": {"name": "黄金ラッシュ", "type": "Normal", "category": "Physical", "power": 120, "accuracy": 100, "max_pp": 5, "target": "Enemy", "effect": {"type": "debuff_self", "stat": "def", "stage": 1}, "desc": "アグライア専用。防御を犠牲に猛攻を仕掛ける。"},
    "rocket_dive": {"name": "ロケットダイブ", "type": "Fire", "category": "Physical", "power": 130, "accuracy": 95, "max_pp": 5, "target": "Enemy", "effect": {"type": "recoil", "percent": 0.25}, "desc": "トリスビアス専用。ロケットで突撃する捨て身の技。"},
    "logic_burst": {"name": "論理崩壊", "type": "Grass", "category": "Special", "power": 140, "accuracy": 90, "max_pp": 5, "target": "Enemy", "effect": {"type": "debuff_self", "stat": "spa", "stage": 2}, "desc": "アナクサゴラス専用。演算限界を超えるビーム。"},
    "holy_nova": {"name": "ホーリーノヴァ", "type": "Light", "category": "Special", "power": 90, "accuracy": 100, "max_pp": 10, "target": "Enemy", "effect": {"type": "heal", "percent": 0.5}, "desc": "ヒアシンシア専用。攻撃と同時に回復を行う。"},
    "abyss_soup": {"name": "深淵のスープ", "type": "Dark", "category": "Special", "power": 110, "accuracy": 95, "max_pp": 10, "target": "Enemy", "effect": {"type": "recoil", "percent": 0.2}, "desc": "メデイモス専用。命を削って毒のスープを浴びせる。"},
    "cat_burglar": {"name": "猫騙し", "type": "Dark", "category": "Physical", "power": 40, "accuracy": 100, "max_pp": 10, "target": "Enemy", "priority": 3, "effect": {"type": "chance_status", "status": "paralysis", "chance": 1.0}, "desc": "セファリア専用。必ず先制し、相手をひるませる(麻痺)。"},
    "sweet_temptation": {"name": "甘い誘惑", "type": "Fairy", "category": "Status", "power": 0, "accuracy": 90, "max_pp": 10, "target": "Enemy", "effect": {"type": "status", "status": "sleep"}, "desc": "キャストリス専用。強力な眠り技。"},
    "volcanic_ash": {"name": "ヴォルカニック", "type": "Fire", "category": "Special", "power": 130, "accuracy": 85, "max_pp": 5, "target": "Enemy", "effect": {"type": "chance_status", "status": "burn", "chance": 0.5}, "desc": "ファイノン専用。広範囲を焼き尽くす。"},
    "deep_sea_gulp": {"name": "丸呑み", "type": "Water", "category": "Physical", "power": 100, "accuracy": 100, "max_pp": 10, "target": "Enemy", "effect": {"type": "heal", "percent": 0.3}, "desc": "セイレンス専用。相手を齧って回復する。"},
    "kings_pressure": {"name": "王のプレッシャー", "type": "Dark", "category": "Status", "power": 0, "accuracy": 100, "max_pp": 5, "target": "Enemy", "effect": {"type": "debuff", "stat": "def", "stage": 2}, "desc": "ケリュドラ専用。相手の防御を大幅に下げる。"},
    "memory_erasure": {"name": "記憶消去", "type": "Light", "category": "Special", "power": 120, "accuracy": 100, "max_pp": 5, "target": "Enemy", "effect": {"type": "recharge"}, "desc": "三月なのか専用。強烈な光で記憶ごと吹き飛ばす。"},
    "dragon_sanctuary": {"name": "竜の聖域", "type": "Light", "category": "Status", "power": 0, "accuracy": 100, "max_pp": 5, "target": "Self", "effect": {"type": "buff", "stat": "def", "stage": 2}, "desc": "丹恒専用。防御と特防を大幅に上げる。"},
    "eternal_love": {"name": "永遠の愛", "type": "Fairy", "category": "Special", "power": 200, "accuracy": 100, "max_pp": 1, "target": "Enemy", "effect": {"type": "recharge"}, "desc": "キュレネ専用。全てを包み込む究極の一撃。"},

    # 特殊個体用（変身後など）
    "star_burst": {"name": "スターバースト", "type": "Fire", "category": "Physical", "power": 999, "accuracy": 200, "max_pp": 1, "target": "Enemy", "desc": "必中・一撃必殺"},
}

# --- キメラのベースデータ (BASE_CHIMERAS) ---
BASE_CHIMERAS = {
    # ★1 (初期/Common)
    "wolf_pup": {
        "name": "ウルフパピー", "type": "Normal", "rarity": 1,
        "base_stats": {"hp": 45, "atk": 60, "def": 40, "spa": 30, "spd": 40, "spe": 65},
        "ability": "闘争心",
        "learnset": {1: "scratch", 5: "growl", 10: "quick_attack", 15: "sharpen", 30: "hyper_beam"},
        "description": "元気な狼の子供。物理攻撃が得意。"
    },
    "aqua_bird": {
        "name": "アクアバード", "type": "Water", "rarity": 1,
        "base_stats": {"hp": 40, "atk": 30, "def": 35, "spa": 65, "spd": 50, "spe": 70},
        "ability": "激流",
        "learnset": {1: "scratch", 3: "water_gun", 8: "sing", 15: "hydro_pump"},
        "description": "水を操る小鳥。素早さと魔法攻撃が高い。"
    },
    "leaf_golem": {
        "name": "リーフゴーレム", "type": "Grass", "rarity": 1,
        "base_stats": {"hp": 60, "atk": 50, "def": 70, "spa": 40, "spd": 60, "spe": 30},
        "ability": "深緑",
        "learnset": {1: "tackle", 5: "growth", 8: "leaf_blade", 15: "poison_powder", 25: "solar_beam"},
        "description": "森の守り人。防御力が自慢。"
    },
    "fire_lizard": {
        "name": "フレアリザード", "type": "Fire", "rarity": 1,
        "base_stats": {"hp": 39, "atk": 52, "def": 43, "spa": 60, "spd": 50, "spe": 65},
        "ability": "猛火",
        "learnset": {1: "scratch", 6: "ember", 12: "tail_whip", 25: "flamethrower", 40: "flare_blitz"},
        "description": "尻尾に炎を宿したトカゲ。"
    },
    # ★2
    "light_fairy": {
        "name": "ライトフェアリー", "type": "Light", "rarity": 2,
        "base_stats": {"hp": 50, "atk": 40, "def": 40, "spa": 70, "spd": 70, "spe": 60},
        "ability": "発光",
        "learnset": {1: "shining_ray", 8: "thunder_wave", 15: "flash_cannon", 20: "recover"},
        "description": "光り輝く妖精。回復技も覚える。"
    },
    "dark_hound": {
        "name": "ダークハウンド", "type": "Dark", "rarity": 2,
        "base_stats": {"hp": 60, "atk": 80, "def": 50, "spa": 40, "spd": 50, "spe": 70},
        "ability": "威圧",
        "learnset": {1: "shadow_claw", 5: "growl", 12: "dark_pulse"},
        "description": "闇夜に潜む黒い犬。"
    },
    "uriu":{
        "name": "ウリウ", "type": "Water", "rarity": 2,
        "base_stats": {"hp": 55, "atk": 60, "def": 50, "spa": 65, "spd": 55, "spe": 60},
        "ability": "水流",
        "learnset": {1: "water_gun", 7: "hydro_pump", 15: "sing"},
        "description": "水中を自在に泳ぐキメラ。"
    },
    "tanki":{
        "name": "短気", "type": "Fire", "rarity": 2,
        "base_stats": {"hp": 60, "atk": 70, "def": 55, "spa": 65, "spd": 50, "spe": 75},
        "ability": "短気",
        "learnset": {1: "ember", 5: "sharpen", 15: "flamethrower", 30: "flare_blitz"},
        "description": "短気な火のキメラ。攻撃が高い。"
    },
    "skape_goat":{
        "name": "スケープゴート", "type": "Grass", "rarity": 2,
        "base_stats": {"hp": 70, "atk": 60, "def": 65, "spa": 55, "spd": 60, "spe": 50},
        "ability": "犠牲者",
        "learnset": {1: "leaf_blade", 10: "poison_powder", 20: "solar_beam"},
        "description": "犠牲を厭わない草のキメラ。"
    },

    # --- 黄金裔モチーフ (★6) 特殊能力持ち ---
    "oatmeal":{
        "name": "オートミール", "type": "Normal", "rarity": 6,
        "base_stats": {"hp": 65, "atk": 55, "def": 60, "spa": 50, "spd": 55, "spe": 40},
        "ability": "金糸雀", 
        "learnset": {1: "tackle", 5: "sing", 10: "sharpen", 20: "hyper_beam", 40: "golden_rush"},
        "description": "アグライアの相棒。攻撃するたび加速し、想いを次へ託す。"
    },
    "ringo_ame":{
        "name": "リンゴアメ", "type": "Grass", "rarity": 6,
        "base_stats": {"hp": 65, "atk": 55, "def": 55, "spa": 45, "spd": 50, "spe": 40},
        "ability": "ロケット", 
        "learnset": {1: "tackle", 5: "growth", 10: "leaf_blade", 15: "poison_powder", 35: "rocket_dive"},
        "description": "トリスビアスの相棒。ロケットに乗って戦場を駆ける。"
    },
    "nunusu":{
        "name": "ヌヌス", "type": "Grass", "rarity": 6,
        "base_stats": {"hp": 75, "atk": 65, "def": 70, "spa": 80, "spd": 75, "spe": 55},
        "ability": "大地獣", 
        "learnset": {1: "leaf_blade", 5: "poison_powder", 12: "solar_beam", 40: "logic_burst"},
        "description": "アナクサゴラスの相棒。相手を解析し弱体化させる。"
    },
    "cheribis":{
        "name": "チェリビス", "type": "Light", "rarity": 6,
        "base_stats": {"hp": 55, "atk": 45, "def": 50, "spa": 75, "spd": 65, "spe": 55},
        "ability": "癒しの光", 
        "learnset": {1: "shining_ray", 5: "recover", 10: "flash_cannon", 20: "hyper_beam", 45: "holy_nova"},
        "description": "ヒアシンシアの相棒。イカルンと共に味方を癒やす。"
    },
    "honey_fruit_soup":{
        "name": "ハニーフルーツスープ", "type": "Dark", "rarity": 6,
        "base_stats": {"hp": 60, "atk": 55, "def": 50, "spa": 60, "spd": 55, "spe": 45},
        "ability": "蘇り", 
        "learnset": {1: "shadow_claw", 5: "growth", 11: "dark_pulse", 40: "abyss_soup"},
        "description": "メデイモスの相棒。何度でも蘇る不屈の魂。"
    },
    "nyanko_dorobou":{
        "name": "ニャンコ泥棒", "type": "Dark", "rarity": 6,
        "base_stats": {"hp": 50, "atk": 70, "def": 45, "spa": 40, "spd": 50, "spe": 80},
        "ability": "盗みの天才", 
        "learnset": {1: "scratch", 5: "tail_whip", 10: "shadow_claw", 15: "dark_pulse", 30: "cat_burglar"},
        "description": "セファリアの相棒。素早く相手の道具を奪う。"
    },
    "cho_cho_cake":{
        "name": "チョウチョウケーキ", "type": "Normal", "rarity": 6,
        "base_stats": {"hp": 70, "atk": 30, "def": 60, "spa": 50, "spd": 65, "spe": 25},
        "ability": "甘美な誘惑", 
        "learnset": {1: "tackle", 5: "sing", 10: "recover", 20: "hyper_beam", 40: "sweet_temptation"},
        "description": "キャストリスの相棒。攻撃した相手に甘いお返しをする。"
    },
    "biguruyashi":{
        "name": "ビ-グルヤシ", "type": "Fire", "rarity": 6,
        "base_stats": {"hp": 60, "atk": 80, "def": 50, "spa": 70, "spd": 55, "spe": 65},
        "ability": "炎の守護者", 
        "learnset": {1: "ember", 5: "sharpen", 10: "flamethrower", 30: "star_burst", 50: "volcanic_ash"},
        "description": "ファイノンの相棒。火種を集め、伝説の姿へと覚醒する。"
    },
    "harapekono_sakana":{
        "name": "腹ペコの魚", "type": "Water", "rarity": 6,
        "base_stats": {"hp": 50, "atk": 60, "def": 40, "spa": 55, "spd": 45, "spe": 70},
        "ability": "食いしん坊", 
        "learnset": {1: "scratch", 5: "tail_whip", 10: "water_gun", 35: "deep_sea_gulp"},
        "description": "セイレンスの相棒。メーレを飲んで体力を回復する。"
    },
    "kijyukyou":{
        "name": "奇獣卿", "type": "Dark", "rarity": 6,
        "base_stats": {"hp": 100, "atk": 90, "def": 85, "spa": 80, "spd": 75, "spe": 70},
        "ability": "王の風格", 
        "learnset": {1: "shadow_claw", 5: "growl", 10: "dark_pulse", 20: "hyper_beam", 50: "kings_pressure"},
        "description": "ケリュドラの相棒。圧倒的な風格で相手を屈服させる。"
    },
    "candy_roll":{
        "name": "キャンディーロール", "type": "Fire", "rarity": 6,
        "base_stats": {"hp": 55, "atk": 50, "def": 45, "spa": 65, "spd": 50, "spe": 60},
        "ability": "忘却", 
        "learnset": {1: "ember", 5: "sing", 9: "flamethrower", 40: "memory_erasure"},
        "description": "三月なのかの相棒。攻撃してきた相手の記憶を奪う。"
    },
    "onkouna_ryu":{
        "name": "温厚な竜", "type": "Light", "rarity": 6,
        "base_stats": {"hp": 90, "atk": 80, "def": 85, "spa": 100, "spd": 95, "spe": 70},
        "ability": "皆を守る者", 
        "learnset": {1: "dragon_breath", 5: "recover", 15: "dragon_claw", 30: "draco_meteor", 50: "dragon_sanctuary"},
        "description": "丹恒の相棒。仲間を守る強固なバリアを展開する。"
    },
    "kyunure":{
        "name": "キュヌレ", "type": "Fairy", "rarity": 6,
        "base_stats": {"hp": 85, "atk": 70, "def": 75, "spa": 90, "spd": 80, "spe": 95},
        "ability": "最愛", 
        "learnset": {1: "tackle", 5: "sing", 10: "dazzling_gleam", 60: "eternal_love"},
        "description": "キュレネの相棒。愛の記憶は消えず、永遠に共に戦う。"
    }
}

# --- アイテムデータ (ITEMS) ---
ITEMS = {
    # 捕獲
    "monster_ball": {"name": "モンスターボール", "effect_type": "capture", "value": 1.0, "price": 200, "unlock_rank": 1, "desc": "野生のキメラを捕まえるボール。"},
    "super_ball": {"name": "スーパーボール", "effect_type": "capture", "value": 1.5, "price": 600, "unlock_rank": 10, "desc": "モンスターボールより捕まえやすいボール。"},
    "hyper_ball": {"name": "ハイパーボール", "effect_type": "capture", "value": 2.0, "price": 1200, "unlock_rank": 20, "desc": "かなり捕まえやすい高性能なボール。"},
    
    # 回復
    "potion": {"name": "キズぐすり", "effect_type": "heal", "value": 50, "price": 100, "unlock_rank": 1, "desc": "HPを50回復する。"},
    "super_potion": {"name": "いいキズぐすり", "effect_type": "heal", "value": 150, "price": 500, "unlock_rank": 5, "desc": "HPを150回復する。"},
    "hyper_potion": {"name": "すごいキズぐすり", "effect_type": "heal", "value": 400, "price": 1500, "unlock_rank": 15, "desc": "HPを400回復する。"},
    "antidote": {"name": "毒消し", "effect_type": "heal_status", "status": "poison", "price": 100, "unlock_rank": 1, "desc": "毒状態を治す。"},
    "paralyze_heal": {"name": "麻痺直し", "effect_type": "heal_status", "status": "paralysis", "price": 100, "unlock_rank": 1, "desc": "麻痺状態を治す。"},
    "full_heal": {"name": "なんでも直し", "effect_type": "heal_status", "status": "all", "price": 600, "unlock_rank": 10, "desc": "すべての状態異常を治す。"},

    # 育成
    "exp_candy_s": {"name": "けいけんアメS", "effect_type": "exp", "value": 5000, "price": 500, "unlock_rank": 1, "desc": "キメラに5000の経験値を与える。"},
    "exp_candy_m": {"name": "けいけんアメM", "effect_type": "exp", "value": 20000, "price": 2000, "unlock_rank": 5, "desc": "キメラに20000の経験値を与える。"},
    "exp_candy_l": {"name": "けいけんアメL", "effect_type": "exp", "value": 100000, "price": 8000, "unlock_rank": 15, "desc": "キメラに100000の経験値を与える。"},
    
    # 装備
    "power_band": {"name": "ちからのハチマキ", "effect_type": "equip_atk", "value": 1.2, "price": 1000, "unlock_rank": 1, "desc": "持たせると物理攻撃が上がる。"},
    "wise_glasses": {"name": "ものしりメガネ", "effect_type": "equip_spa", "value": 1.2, "price": 1000, "unlock_rank": 1, "desc": "持たせると特殊攻撃が上がる。"},
    "vitality_belt": {"name": "あつぞこブーツ", "effect_type": "equip_hp", "value": 1.2, "price": 1500, "unlock_rank": 5, "desc": "持たせると最大HPが増える。"},
    "hard_stone": {"name": "かたいイシ", "effect_type": "equip_def", "value": 1.2, "price": 1000, "unlock_rank": 5, "desc": "持たせると防御が上がる。"},
    
    # 特殊装備
    "leftovers": {"name": "たべのこし", "effect_type": "equip_heal_turn", "value": 0.06, "price": 5000, "unlock_rank": 20, "desc": "毎ターン少しずつHPを回復する。"},
    "focus_sash": {"name": "きあいのタスキ", "effect_type": "equip_guts", "value": 1, "price": 10000, "unlock_rank": 30, "desc": "HP満タンならひんしになるダメージでも1残る（使い捨て）。"},
    "sitrus_berry": {"name": "オボンのみ", "effect_type": "equip_heal_pinch", "value": 0.25, "price": 2000, "unlock_rank": 10, "desc": "HPが半分以下になると自動で回復する（使い捨て）。"},
    "resist_berry": {"name": "半減の実", "effect_type": "equip_resist", "value": 0.5, "price": 2000, "unlock_rank": 15, "desc": "効果抜群のダメージを受けた時、威力を半減する（使い捨て）。"},

    "story_page_2": {"name": "失われし紡がれた物語のページその2", "effect_type": "key_item", "value": 0, "price": 0, "unlock_rank": 999, "desc": "隠された真実が記されたページの一部。"},
}

# --- チャレンジモード：黄金裔トレーナーデータ (Normal) ---
CHALLENGE_TRAINERS = {
    1: {
        "name": "黄金裔 アグライア",
        "party": [{"base_id": "light_fairy", "level": 70}, {"base_id": "light_fairy", "level": 70}, {"base_id": "oatmeal", "level": 72}],
        "dialogue_start": "手加減はしません。 あなたの実力、見せてください。",
        "dialogue_win": "さっすがですね…私の負けです。"
    },
    2: {
        "name": "黄金裔 トリスビアス",
        "party": [{"base_id": "leaf_golem", "level": 72}, {"base_id": "leaf_golem", "level": 72}, {"base_id": "ringo_ame", "level": 74}],
        "dialogue_start": "あたちとひと勝負しましょう！",
        "dialogue_win": "あーあ、負けちゃった…また今度リベンジするからわ！"
    },
    3: {
        "name": "黄金裔 アナクサゴラス",
        "party": [{"base_id": "aqua_bird", "level": 75}, {"base_id": "wolf_pup", "level": 75}, {"base_id": "nunusu", "level": 77}],
        "dialogue_start": "あなたの勝率は0%となるでしょう。",
        "dialogue_win": "おめでとうございます。"
    },
    4: {
        "name": "黄金裔 ヒアシンシア",
        "party": [{"base_id": "fire_lizard", "level": 78}, {"base_id": "fire_lizard", "level": 78}, {"base_id": "cheribis", "level": 80}],
        "dialogue_start": "この勝負、勝ちに行きます♪",
        "dialogue_win": "うぅ...負けてしまいました。次は勝ちます♪"
    },
    5: {
        "name": "黄金裔 メデイモス",
        "party": [{"base_id": "wolf_pup", "level": 80}, {"base_id": "wolf_pup", "level": 80}, {"base_id": "honey_fruit_soup", "level": 82}],
        "dialogue_start": "クレムノスの力、見せてやる！",
        "dialogue_win": "お前の実力、認めざるを得んな。"
    },
    6: {
        "name": "黄金裔 セファリア",
        "party": [{"base_id": "dark_hound", "level": 82}, {"base_id": "light_fairy", "level": 82}, {"base_id": "nyanko_dorobou", "level": 85}],
        "dialogue_start": "あたしが勝ったら、あんたのキメラをもらうからね！",
        "dialogue_win": "あんた、なかなかやるじゃん！"
    },
    7: {
        "name": "黄金裔 キャストリス",
        "party": [{"base_id": "light_fairy", "level": 85}, {"base_id": "leaf_golem", "level": 85}, {"base_id": "cho_cho_cake", "level": 87}],
        "dialogue_start": "腹が減っては戦はできぬ、と、言いますでしょう？",
        "dialogue_win": "レシピの改良が必要ですね……。"
    },
    8: {
        "name": "黄金裔 ファイノン",
        "party": [{"base_id": "leaf_golem", "level": 88}, {"base_id": "wolf_pup", "level": 88}, {"base_id": "biguruyashi", "level": 90}],
        "dialogue_start": "僕は、最強のキメラトレーナーになるんだ！",
        "dialogue_win": "僕の道は、まだ終わりじゃない。"
    },
    9: {
        "name": "黄金裔 セイレンス",
        "party": [{"base_id": "aqua_bird", "level": 90}, {"base_id": "light_fairy", "level": 90}, {"base_id": "harapekono_sakana", "level": 92}],
        "dialogue_start": "聴いてくれ魚たちの泡の音だ。",
        "dialogue_win": "潮目の変わる時は必ず訪れる。"
    },
    10: {
        "name": "黄金裔 ケリュドラ",
        "party": [{"base_id": "dark_hound", "level": 92}, {"base_id": "dark_hound", "level": 92}, {"base_id": "kijyukyou", "level": 95}],
        "dialogue_start": "ふん、貴様だとしても手加減はなしだぞ。",
        "dialogue_win": "次の進軍方法を考えなければ…"
    },
    11: {
        "name": "三月なのか",
        "party": [{"base_id": "light_fairy", "level": 95}, {"base_id": "aqua_bird", "level": 95}, {"base_id": "candy_roll", "level": 97}],
        "dialogue_start": "ウチ絶対負けないから！！",
        "dialogue_win": "うぅ〜悔しい〜！次は絶対負けないから！"
    },
    12: {
        "name": "丹恒",
        "party": [{"base_id": "leaf_golem", "level": 97}, {"base_id": "wolf_pup", "level": 97}, {"base_id": "onkouna_ryu", "level": 99}],
        "dialogue_start": "お前の仲間として、手加減はしない。",
        "dialogue_win": "見事なキメラ捌きだ…お俺も精進せねば。"
    },
    13: {
        "name": "黄金裔 キュレネ",
        "party": [{"base_id": "cho_cho_cake", "level": 98}, {"base_id": "biguruyashi", "level": 99}, {"base_id": "kyunure", "level": 100}],
        "reward_item": "story_page_2", "reward_title": "ポ◯モンマスターの",
        "dialogue_start": "さあ、あなたの『愛』の深さ…試させてもらうわよ？",
        "dialogue_win": "ふふっ、素晴らしいわ！あなたこそチャンピオンよ♪"
    }
}

# --- 真なるキメラマスターロード用 (Hard Mode) ---
# レベル、持ち物、技構成、回復頻度を大幅強化
CHALLENGE_TRAINERS_HARD = {
    1: {
        "name": "真・アグライア",
        "party": [{"base_id": "light_fairy", "level": 110, "item": "sitrus_berry"}, {"base_id": "oatmeal", "level": 115, "item": "power_band"}], "potions": 3,
        "dialogue_start": "金糸によって全てお見通しです。今回は負けません。",
        "dialogue_win": "私にも見えないまぶしい光でした…あなたの勝ちです。"
    },
    2: {
        "name": "真・トリスビアス",
        "party": [{"base_id": "ringo_ame", "level": 120, "item": "hard_stone"}, {"base_id": "leaf_golem", "level": 120, "item": "sitrus_berry"}], "potions": 3,
        "dialogue_start": "あたち今度は負けないからね！",
        "dialogue_win": "すごーい戦いだったね！あたち負けちゃったよ〜"
    },
    3: {
        "name": "真・アナクサゴラス",
        "party": [{"base_id": "nunusu", "level": 125, "item": "vitality_belt"}, {"base_id": "aqua_bird", "level": 125, "item": "wise_glasses"}], "potions": 3,
        "dialogue_start": "全てのパターンを考慮しました。敗北などありえないでしょう。",
        "dialogue_win": "おめでとうございます。"
    },
    4: {
        "name": "真・ヒアシンシア",
        "party": [{"base_id": "cheribis", "level": 130, "item": "leftovers"}, {"base_id": "fire_lizard", "level": 130, "item": "power_band"}], "potions": 4,
        "dialogue_start": "全力で行きますね♪",
        "dialogue_win": "お強いですね♪完敗です♪"
    },
    5: {
        "name": "真・メデイモス",
        "party": [{"base_id": "honey_fruit_soup", "level": 135, "item": "leftovers"}, {"base_id": "wolf_pup", "level": 135, "item": "power_band"}], "potions": 4,
        "dialogue_start": "クレムノス人の辞書に“不可能”の文字は無い。",
        "dialogue_win": "俺に勝つとは…お見事だ。"
    },
    6: {
        "name": "真・セファリア",
        "party": [{"base_id": "nyanko_dorobou", "level": 140, "item": "focus_sash"}, {"base_id": "dark_hound", "level": 140, "item": "power_band"}], "potions": 4,
        "dialogue_start": "へへーん、今度は負けないよ！",
        "dialogue_win": "うぅ…負けちゃったよ〜！"
    },
    7: {
        "name": "真・キャストリス",
        "party": [{"base_id": "cho_cho_cake", "level": 145, "item": "leftovers"}, {"base_id": "leaf_golem", "level": 145, "item": "hard_stone"}], "potions": 4,
        "dialogue_start": "腹が減っては戦はできぬ、と、言いますでしょう？",
        "dialogue_win": "レシピの改良が必要ですね……"
    },
    8: {
        "name": "真・ファイノン",
        "party": [{"base_id": "biguruyashi", "level": 150, "item": "wise_glasses"}, {"base_id": "wolf_pup", "level": 150, "item": "power_band"}], "potions": 4,
        "dialogue_start": "僕は、最強のキメラトレーナーになるんだ！",
        "dialogue_win": "僕の道は、まだ終わりじゃない。"
    },
    9: {
        "name": "真・セイレンス",
        "party": [{"base_id": "harapekono_sakana", "level": 155, "item": "leftovers"}, {"base_id": "aqua_bird", "level": 155, "item": "wise_glasses"}], "potions": 5,
        "dialogue_start": "いい余興になりそうだ。",
        "dialogue_win": "幕が下りた・・・"
    },
    10: {
        "name": "真・ケリュドラ",
        "party": [{"base_id": "kijyukyou", "level": 160, "item": "focus_sash"}, {"base_id": "dark_hound", "level": 160, "item": "power_band"}], "potions": 5,
        "dialogue_start": "しょせんチェスとあまり変わらないだろう",
        "dialogue_win": "ほう…この僕を打ち負かすとは…やるではないか。。"
    },
    11: {
        "name": "真・三月なのか",
        "party": [{"base_id": "candy_roll", "level": 165, "item": "wise_glasses"}, {"base_id": "light_fairy", "level": 165, "item": "focus_sash"}], "potions": 5,
        "dialogue_start": "アンタが相手でも手加減しないから！！",
        "dialogue_win": "負けちゃった〜。アンタ強いね。"
    },
    12: {
        "name": "真・丹恒",
        "party": [{"base_id": "onkouna_ryu", "level": 170, "item": "leftovers"}, {"base_id": "leaf_golem", "level": 170, "item": "hard_stone"}], "potions": 5,
        "dialogue_start": "新たに得た力で、お前を止めよう。",
        "dialogue_win": "やるな。さっすがだ。"
    },
    13: {
        "name": "真・キュレネ",
        "party": [{"base_id": "kyunure", "level": 175, "item": "leftovers"}, {"base_id": "cho_cho_cake", "level": 175, "item": "focus_sash"}, {"base_id": "biguruyashi", "level": 180, "item": "wise_glasses"}], "potions": 6,
        "reward_title": "キメラを極めし者",
        "dialogue_start": "これが私たちの『愛』の最終形…受け止めきれるかしら？",
        "dialogue_win": "ふふっ、素晴らしいわ！ あなたの愛、確かに受け取ったわ。"
    }
    14: {
        "name": "制作者 aeracero",
        "party": [{"base_id": "candy_roll", "level": 1000, "item": "cheribish"}, {"base_id": "kyurune", "level": 1000, "item": "leftovers"}, {"base_id": "kyunure", "level": 1000, "item": "wise_glasses"}], "potions": 33350337,
        "reward_title": "制作者泣かせ",
        "dialogue_start": "どうも、制作者のaeraceroです。今は暇なんで、相手してあげますよ。",
        "dialogue_win": "すごいっすね、まさか私も殺っちゃうなんて..."
    }
}