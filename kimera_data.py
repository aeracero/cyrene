# kimera_data.py
# キメラ、技、アイテム、トレーナー、タイプ相性、シナジー等を管理します。

TYPES = ["Normal", "Fire", "Water", "Grass", "Light", "Dark", "Fairy"]

TYPE_CHART = {
    "Normal": {"Light": 0.5, "Dark": 0.5},
    "Fire":   {"Grass": 2.0, "Water": 0.5, "Fire": 0.5, "Fairy": 1.0},
    "Water":  {"Fire": 2.0, "Grass": 0.5, "Water": 0.5},
    "Grass":  {"Water": 2.0, "Fire": 0.5, "Grass": 0.5, "Light": 1.0},
    "Light":  {"Dark": 2.0, "Grass": 2.0, "Light": 0.5, "Fairy": 0.5},
    "Dark":   {"Light": 2.0, "Fairy": 2.0, "Dark": 0.5, "Normal": 2.0},
    "Fairy":  {"Dark": 2.0, "Fire": 0.5, "Light": 2.0, "Fairy": 0.5}
}

STATUS_CONDITIONS = {
    "poison": {"name": "毒", "desc": "毎ターンHPが減るわ。"},
    "paralysis": {"name": "麻痺", "desc": "素早さが下がり、たまに動けないわ。"},
    "sleep": {"name": "眠り", "desc": "数ターン動けないわ。"},
    "burn": {"name": "火傷", "desc": "毎ターンHPが減り、物理攻撃が下がるわ。"},
    "confusion": {"name": "混乱", "desc": "たまに自分を攻撃してしまうわ。"},
    "oblivion": {"name": "忘却", "desc": "直前の技が使えず、命中率ダウン。"},
    "submission": {"name": "屈服", "desc": "与えるダメージ低下。捕獲されやすい。"},
    "recharge": {"name": "反動待機", "desc": "強力な技の反動で動けない。"}
}

MOVES = {
    # --- 既存の技 ---
    "scratch": {"name": "ひっかく", "type": "Normal", "category": "Physical", "power": 40, "accuracy": 100, "max_pp": 35, "target": "Enemy"},
    "tackle": {"name": "たいあたり", "type": "Normal", "category": "Physical", "power": 40, "accuracy": 100, "max_pp": 35, "target": "Enemy"},
    "leaf_blade": {"name": "リーフブレード", "type": "Grass", "category": "Physical", "power": 90, "accuracy": 100, "max_pp": 15, "target": "Enemy"},
    "shadow_claw": {"name": "シャドークロー", "type": "Dark", "category": "Physical", "power": 70, "accuracy": 100, "max_pp": 15, "target": "Enemy"},
    "dragon_claw": {"name": "ドラゴンクロー", "type": "Normal", "category": "Physical", "power": 80, "accuracy": 100, "max_pp": 15, "target": "Enemy"},
    "quick_attack": {"name": "電光石火", "type": "Normal", "category": "Physical", "power": 40, "accuracy": 100, "max_pp": 30, "priority": 1, "target": "Enemy"},
    "flare_blitz": {"name": "フレアドライブ", "type": "Fire", "category": "Physical", "power": 120, "accuracy": 100, "max_pp": 15, "target": "Enemy", "effect": {"type": "recoil", "percent": 0.33}, "desc": "高威力だが反動ダメージを受ける。"},
    "giga_impact": {"name": "ギガインパクト", "type": "Normal", "category": "Physical", "power": 150, "accuracy": 90, "max_pp": 5, "target": "Enemy", "effect": {"type": "recharge"}, "desc": "超高威力だが次のターン動けない。"},
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
    
    # 補助技
    "growl": {"name": "鳴き声", "type": "Normal", "category": "Status", "power": 0, "accuracy": 100, "max_pp": 40, "target": "Enemy", "effect": {"type": "debuff", "stat": "atk", "stage": 1}},
    "tail_whip": {"name": "しっぽをふる", "type": "Normal", "category": "Status", "power": 0, "accuracy": 100, "max_pp": 40, "target": "Enemy", "effect": {"type": "debuff", "stat": "def", "stage": 1}},
    "sharpen": {"name": "つるぎのまい", "type": "Normal", "category": "Status", "power": 0, "accuracy": 100, "max_pp": 20, "target": "Self", "effect": {"type": "buff", "stat": "atk", "stage": 2}},
    "growth": {"name": "成長", "type": "Normal", "category": "Status", "power": 0, "accuracy": 100, "max_pp": 20, "target": "Self", "effect": {"type": "buff", "stat": "spa", "stage": 1}},
    "poison_powder": {"name": "毒の粉", "type": "Grass", "category": "Status", "power": 0, "accuracy": 75, "max_pp": 35, "target": "Enemy", "effect": {"type": "status", "status": "poison"}},
    "thunder_wave": {"name": "電磁波", "type": "Light", "category": "Status", "power": 0, "accuracy": 90, "max_pp": 20, "target": "Enemy", "effect": {"type": "status", "status": "paralysis"}},
    "sing": {"name": "歌う", "type": "Normal", "category": "Status", "power": 0, "accuracy": 55, "max_pp": 15, "target": "Enemy", "effect": {"type": "status", "status": "sleep"}},
    "recover": {"name": "自己再生", "type": "Normal", "category": "Status", "power": 0, "accuracy": 100, "max_pp": 10, "target": "Self", "effect": {"type": "heal", "percent": 0.5}},

    # --- 新規追加: 状態異常特攻技 ---
    "venom_shock": {"name": "ベノムショック", "type": "Dark", "category": "Special", "power": 65, "accuracy": 100, "max_pp": 10, "target": "Enemy", "effect": {"type": "conditional_power", "condition": "poison", "multiplier": 2.0}, "desc": "相手が毒状態なら威力が倍になる。"},
    "hex_break": {"name": "祟り目", "type": "Dark", "category": "Special", "power": 65, "accuracy": 100, "max_pp": 10, "target": "Enemy", "effect": {"type": "conditional_power", "condition": "any_status", "multiplier": 2.0}, "desc": "相手が状態異常なら威力が倍になる。"},

    # --- 新規追加: 通常攻撃技（効果なし・安定） ---
    "slam": {"name": "たたきつける", "type": "Normal", "category": "Physical", "power": 80, "accuracy": 75, "max_pp": 20, "target": "Enemy", "desc": "長い体などを使い相手をたたきつけて攻撃する。"},
    "strength": {"name": "怪力", "type": "Normal", "category": "Physical", "power": 80, "accuracy": 100, "max_pp": 15, "target": "Enemy", "desc": "渾身の力を込めて相手を殴りつける。"},
    "gem_power": {"name": "パワージェム", "type": "Light", "category": "Special", "power": 80, "accuracy": 100, "max_pp": 20, "target": "Enemy", "desc": "宝石のような光を発射して攻撃する。"},
    "seed_bomb": {"name": "タネばくだん", "type": "Grass", "category": "Physical", "power": 80, "accuracy": 100, "max_pp": 15, "target": "Enemy", "desc": "硬い殻に包まれた種を上からたたきつけて攻撃する。"},
    "night_slash": {"name": "つじぎり", "type": "Dark", "category": "Physical", "power": 70, "accuracy": 100, "max_pp": 15, "target": "Enemy", "desc": "急所に当たりやすい斬撃。"},
    "aqua_tail": {"name": "アクアテール", "type": "Water", "category": "Physical", "power": 90, "accuracy": 90, "max_pp": 10, "target": "Enemy", "desc": "水をまとった尻尾で激しく叩く。"},

    # --- 黄金裔モチーフ・高レベル専用技 ---
    "golden_thread": {"name": "黄金の糸", "type": "Normal", "category": "Physical", "power": 130, "accuracy": 90, "max_pp": 5, "target": "Enemy", "effect": {"type": "recoil", "percent": 0.2}, "desc": "命を削る糸で拘束する。反動ダメージ。"},
    "golden_rush": {"name": "黄金ラッシュ", "type": "Normal", "category": "Physical", "power": 150, "accuracy": 90, "max_pp": 5, "target": "Enemy", "effect": {"type": "recharge"}, "desc": "全財産を投げ打つような一撃。次ターン動けない。"},
    "apple_bomb": {"name": "アップルボム", "type": "Grass", "category": "Physical", "power": 140, "accuracy": 85, "max_pp": 5, "target": "Enemy", "effect": {"type": "recoil", "percent": 0.3}, "desc": "自爆覚悟の爆撃。大きな反動を受ける。"},
    "rocket_dive": {"name": "ロケットダイブ", "type": "Fire", "category": "Physical", "power": 120, "accuracy": 95, "max_pp": 10, "target": "Enemy", "effect": {"type": "debuff_self", "stat": "def", "stage": 1}, "desc": "防御を捨てて突撃する。"},
    "logic_break": {"name": "論理崩壊", "type": "Grass", "category": "Special", "power": 140, "accuracy": 90, "max_pp": 5, "target": "Enemy", "effect": {"type": "debuff_self", "stat": "spa", "stage": 2}, "desc": "演算限界を超えるビーム。特攻ががくっと下がる。"},
    "paradox_lock": {"name": "パラドックス", "type": "Grass", "category": "Status", "power": 0, "accuracy": 100, "max_pp": 5, "target": "Enemy", "effect": {"type": "status", "status": "paralysis"}, "desc": "相手を思考の檻に閉じ込め、麻痺させる。"},
    "holy_nova": {"name": "ホーリーノヴァ", "type": "Light", "category": "Special", "power": 100, "accuracy": 100, "max_pp": 5, "target": "Enemy", "effect": {"type": "heal", "percent": 0.5}, "desc": "攻撃と同時に自身のHPを半分回復する。"},
    "sacred_prayer": {"name": "聖なる祈り", "type": "Light", "category": "Status", "power": 0, "accuracy": 100, "max_pp": 5, "target": "Self", "effect": {"type": "buff", "stat": "spa", "stage": 2}, "desc": "特攻をぐーんと上げる。"},
    "abyss_gulp": {"name": "深淵の暴食", "type": "Dark", "category": "Special", "power": 120, "accuracy": 90, "max_pp": 5, "target": "Enemy", "effect": {"type": "heal", "percent": 0.25}, "desc": "相手の生命力を吸い取る。"},
    "venom_soup": {"name": "劇毒スープ", "type": "Dark", "category": "Status", "power": 0, "accuracy": 85, "max_pp": 10, "target": "Enemy", "effect": {"type": "status", "status": "poison"}, "desc": "猛毒を浴びせる。"},
    "cat_burglar": {"name": "猫騙し", "type": "Dark", "category": "Physical", "power": 50, "accuracy": 100, "max_pp": 10, "target": "Enemy", "priority": 3, "effect": {"type": "chance_status", "status": "paralysis", "chance": 1.0}, "desc": "必ず先制し、相手をひるませる(麻痺)。"},
    "shadow_steal": {"name": "影盗み", "type": "Dark", "category": "Physical", "power": 90, "accuracy": 100, "max_pp": 10, "target": "Enemy", "desc": "相手の影を利用して攻撃する。"},
    "sweet_temptation": {"name": "甘い誘惑", "type": "Fairy", "category": "Status", "power": 0, "accuracy": 80, "max_pp": 10, "target": "Enemy", "effect": {"type": "status", "status": "sleep"}, "desc": "強力な催眠効果のあるお菓子を投げる。"},
    "cream_cannon": {"name": "クリーム砲", "type": "Fairy", "category": "Special", "power": 110, "accuracy": 85, "max_pp": 5, "target": "Enemy", "effect": {"type": "debuff", "stat": "spe", "stage": 1}, "desc": "相手をベタベタにして素早さを下げる。"},
    "volcanic_ash": {"name": "ヴォルカニック", "type": "Fire", "category": "Special", "power": 130, "accuracy": 85, "max_pp": 5, "target": "Enemy", "effect": {"type": "chance_status", "status": "burn", "chance": 0.5}, "desc": "広範囲を焼き尽くす。火傷にすることがある。"},
    "magma_storm": {"name": "マグマの嵐", "type": "Fire", "category": "Special", "power": 100, "accuracy": 90, "max_pp": 5, "target": "Enemy", "effect": {"type": "recharge"}, "desc": "相手をマグマに閉じ込める。次ターン動けない。"},
    "deep_sea_gulp": {"name": "丸呑み", "type": "Water", "category": "Physical", "power": 100, "accuracy": 100, "max_pp": 10, "target": "Enemy", "effect": {"type": "heal", "percent": 0.3}, "desc": "相手を齧って回復する。"},
    "siren_voice": {"name": "滅びの歌", "type": "Water", "category": "Status", "power": 0, "accuracy": 100, "max_pp": 5, "target": "Enemy", "effect": {"type": "debuff", "stat": "def", "stage": 2}, "desc": "相手の防御をがくっと下げる。"},
    "kings_pressure": {"name": "王の威圧", "type": "Dark", "category": "Status", "power": 0, "accuracy": 100, "max_pp": 5, "target": "Enemy", "effect": {"type": "debuff", "stat": "atk", "stage": 2}, "desc": "相手の攻撃をがくっと下げる。"},
    "dictator_crush": {"name": "独裁者の鉄槌", "type": "Dark", "category": "Physical", "power": 150, "accuracy": 80, "max_pp": 5, "target": "Enemy", "effect": {"type": "recharge"}, "desc": "圧倒的な力で粉砕する。次ターン動けない。"},
    "memory_erasure": {"name": "記憶消去", "type": "Light", "category": "Special", "power": 140, "accuracy": 90, "max_pp": 5, "target": "Enemy", "effect": {"type": "recharge"}, "desc": "強烈な光で記憶ごと吹き飛ばす。次ターン動けない。"},
    "freeze_camera": {"name": "氷結カメラ", "type": "Water", "category": "Special", "power": 90, "accuracy": 100, "max_pp": 10, "target": "Enemy", "effect": {"type": "chance_status", "status": "paralysis", "chance": 0.3}, "desc": "時間を止めるような冷気。"},
    "dragon_sanctuary": {"name": "竜の聖域", "type": "Light", "category": "Status", "power": 0, "accuracy": 100, "max_pp": 5, "target": "Self", "effect": {"type": "buff", "stat": "def", "stage": 2}, "desc": "防御をぐーんと上げる。"},
    "cloud_piercer": {"name": "雲を穿つ槍", "type": "Light", "category": "Physical", "power": 120, "accuracy": 100, "max_pp": 5, "target": "Enemy", "effect": {"type": "recoil", "percent": 0.2}, "desc": "自身も傷つくほどの鋭い一撃。"},
    "eternal_love": {"name": "永遠の愛", "type": "Fairy", "category": "Special", "power": 200, "accuracy": 100, "max_pp": 1, "target": "Enemy", "effect": {"type": "recharge"}, "desc": "全てを包み込む究極の一撃。使用後しばらく動けない。"},
    "star_burst": {"name": "スターバースト", "type": "Fire", "category": "Physical", "power": 999, "accuracy": 200, "max_pp": 1, "target": "Enemy", "desc": "必中・一撃必殺"},
}

BASE_CHIMERAS = {
    # ★1 (初期/Common)
    "wolf_pup": {
        "name": "ウルフパピー", "type": "Normal", "rarity": 1,
        "base_stats": {"hp": 45, "atk": 60, "def": 40, "spa": 30, "spd": 40, "spe": 65},
        "ability": "闘争心",
        "learnset": {1: "scratch", 5: "growl", 10: "quick_attack", 15: "sharpen", 25: "slam", 30: "hyper_beam"},
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
        "learnset": {1: "shining_ray", 8: "thunder_wave", 15: "flash_cannon", 20: "recover", 30: "gem_power"},
        "description": "光り輝く妖精。回復技も覚える。"
    },
    "dark_hound": {
        "name": "ダークハウンド", "type": "Dark", "rarity": 2,
        "base_stats": {"hp": 60, "atk": 80, "def": 50, "spa": 40, "spd": 50, "spe": 70},
        "ability": "威圧",
        "learnset": {1: "shadow_claw", 5: "growl", 12: "dark_pulse", 20: "night_slash", 30: "hex_break"},
        "description": "闇夜に潜む黒い犬。"
    },
    "uriu":{
        "name": "ウリウ", "type": "Water", "rarity": 2,
        "base_stats": {"hp": 55, "atk": 60, "def": 50, "spa": 65, "spd": 55, "spe": 60},
        "ability": "水流",
        "learnset": {1: "water_gun", 7: "hydro_pump", 15: "sing", 25: "aqua_tail"},
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
        "learnset": {1: "leaf_blade", 10: "poison_powder", 20: "solar_beam", 25: "seed_bomb"},
        "description": "犠牲を厭わない草のキメラ。"
    },

    # --- 黄金裔モチーフ (★6) ---
    "oatmeal":{
        "name": "オートミール", "type": "Normal", "rarity": 6,
        "base_stats": {"hp": 65, "atk": 55, "def": 60, "spa": 50, "spd": 55, "spe": 40},
        "ability": "金糸雀", 
        "learnset": {1: "tackle", 5: "sing", 10: "sharpen", 20: "hyper_beam", 30: "strength", 40: "golden_rush", 50: "golden_thread"},
        "description": "アグライアの相棒。攻撃するたび加速し、想いを次へ託す。"
    },
    "ringo_ame":{
        "name": "リンゴアメ", "type": "Grass", "rarity": 6,
        "base_stats": {"hp": 65, "atk": 55, "def": 55, "spa": 45, "spd": 50, "spe": 40},
        "ability": "ロケット", 
        "learnset": {1: "tackle", 5: "growth", 10: "leaf_blade", 15: "poison_powder", 25: "seed_bomb", 35: "rocket_dive", 50: "apple_bomb"},
        "description": "トリスビアスの相棒。ロケットに乗って戦場を駆ける。"
    },
    "nunusu":{
        "name": "ヌヌス", "type": "Grass", "rarity": 6,
        "base_stats": {"hp": 75, "atk": 65, "def": 70, "spa": 80, "spd": 75, "spe": 55},
        "ability": "大地獣", 
        "learnset": {1: "leaf_blade", 5: "poison_powder", 12: "solar_beam", 30: "seed_bomb", 40: "logic_break", 50: "paradox_lock"},
        "description": "アナクサゴラスの相棒。相手を解析し弱体化させる。"
    },
    "cheribis":{
        "name": "チェリビス", "type": "Light", "rarity": 6,
        "base_stats": {"hp": 55, "atk": 45, "def": 50, "spa": 75, "spd": 65, "spe": 55},
        "ability": "癒しの光", 
        "learnset": {1: "shining_ray", 5: "recover", 10: "flash_cannon", 20: "hyper_beam", 30: "gem_power", 45: "holy_nova", 55: "sacred_prayer"},
        "description": "ヒアシンシアの相棒。イカルンと共に味方を癒やす。"
    },
    "honey_fruit_soup":{
        "name": "ハニーフルーツスープ", "type": "Dark", "rarity": 6,
        "base_stats": {"hp": 60, "atk": 55, "def": 50, "spa": 60, "spd": 55, "spe": 45},
        "ability": "蘇り", 
        "learnset": {1: "shadow_claw", 5: "growth", 11: "dark_pulse", 30: "venom_shock", 40: "abyss_gulp", 50: "venom_soup"},
        "description": "メデイモスの相棒。何度でも蘇る不屈の魂。"
    },
    "nyanko_dorobou":{
        "name": "ニャンコ泥棒", "type": "Dark", "rarity": 6,
        "base_stats": {"hp": 50, "atk": 70, "def": 45, "spa": 40, "spd": 50, "spe": 80},
        "ability": "盗みの天才", 
        "learnset": {1: "scratch", 5: "tail_whip", 10: "shadow_claw", 15: "dark_pulse", 25: "night_slash", 30: "cat_burglar", 45: "shadow_steal"},
        "description": "セファリアの相棒。素早く相手の道具を奪う。"
    },
    "cho_cho_cake":{
        "name": "チョウチョウケーキ", "type": "Normal", "rarity": 6,
        "base_stats": {"hp": 70, "atk": 30, "def": 60, "spa": 50, "spd": 65, "spe": 25},
        "ability": "甘美な誘惑", 
        "learnset": {1: "tackle", 5: "sing", 10: "recover", 20: "hyper_beam", 30: "strength", 40: "sweet_temptation", 50: "cream_cannon"},
        "description": "キャストリスの相棒。攻撃した相手に甘いお返しをする。"
    },
    "biguruyashi":{
        "name": "ビ-グルヤシ", "type": "Fire", "rarity": 6,
        "base_stats": {"hp": 60, "atk": 80, "def": 50, "spa": 70, "spd": 55, "spe": 65},
        "ability": "炎の守護者", 
        "learnset": {1: "ember", 5: "sharpen", 10: "flamethrower", 30: "star_burst", 50: "volcanic_ash", 60: "magma_storm"},
        "description": "ファイノンの相棒。火種を集め、伝説の姿へと覚醒する。"
    },
    "harapekono_sakana":{
        "name": "腹ペコの魚", "type": "Water", "rarity": 6,
        "base_stats": {"hp": 50, "atk": 60, "def": 40, "spa": 55, "spd": 45, "spe": 70},
        "ability": "食いしん坊", 
        "learnset": {1: "scratch", 5: "tail_whip", 10: "water_gun", 25: "aqua_tail", 35: "deep_sea_gulp", 50: "siren_voice"},
        "description": "セイレンスの相棒。メーレを飲んで体力を回復する。"
    },
    "kijyukyou":{
        "name": "奇獣卿", "type": "Dark", "rarity": 6,
        "base_stats": {"hp": 100, "atk": 90, "def": 85, "spa": 80, "spd": 75, "spe": 70},
        "ability": "王の風格", 
        "learnset": {1: "shadow_claw", 5: "growl", 10: "dark_pulse", 20: "hyper_beam", 30: "strength", 50: "kings_pressure", 60: "dictator_crush"},
        "description": "ケリュドラの相棒。圧倒的な風格で相手を屈服させる。"
    },
    "candy_roll":{
        "name": "キャンディーロール", "type": "Fire", "rarity": 6,
        "base_stats": {"hp": 55, "atk": 50, "def": 45, "spa": 65, "spd": 50, "spe": 60},
        "ability": "忘却", 
        "learnset": {1: "ember", 5: "sing", 9: "flamethrower", 30: "hex_break", 40: "memory_erasure", 50: "freeze_camera"},
        "description": "三月なのかの相棒。攻撃してきた相手の記憶を奪う。"
    },
    "onkouna_ryu":{
        "name": "温厚な竜", "type": "Light", "rarity": 6,
        "base_stats": {"hp": 90, "atk": 80, "def": 85, "spa": 100, "spd": 95, "spe": 70},
        "ability": "皆を守る者", 
        "learnset": {1: "dragon_breath", 5: "recover", 15: "dragon_claw", 30: "draco_meteor", 40: "gem_power", 50: "dragon_sanctuary", 60: "cloud_piercer"},
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
    
    # 装備 (ステータスアップ)
    "power_band": {"name": "ちからのハチマキ", "effect_type": "equip_atk", "value": 1.1, "price": 1000, "unlock_rank": 1, "desc": "持たせると物理攻撃が少し上がる。"},
    "wise_glasses": {"name": "ものしりメガネ", "effect_type": "equip_spa", "value": 1.1, "price": 1000, "unlock_rank": 1, "desc": "持たせると特殊攻撃が少し上がる。"},
    "vitality_belt": {"name": "あつぞこブーツ", "effect_type": "equip_hp", "value": 1.1, "price": 1500, "unlock_rank": 5, "desc": "持たせると最大HPが増える。"},
    "hard_stone": {"name": "かたいイシ", "effect_type": "equip_def", "value": 1.1, "price": 1000, "unlock_rank": 5, "desc": "持たせると防御が少し上がる。"},
    
    # 特殊装備 (新規追加分含む)
    "leftovers": {"name": "たべのこし", "effect_type": "equip_heal_turn", "value": 0.06, "price": 5000, "unlock_rank": 20, "desc": "毎ターン少しずつHPを回復する。"},
    "focus_sash": {"name": "きあいのタスキ", "effect_type": "equip_guts", "value": 1, "price": 10000, "unlock_rank": 30, "desc": "HP満タンならひんしになるダメージでも1残る（使い捨て）。"},
    "sitrus_berry": {"name": "オボンのみ", "effect_type": "equip_heal_pinch", "value": 0.25, "price": 2000, "unlock_rank": 10, "desc": "HPが半分以下になると自動で回復する（使い捨て）。"},
    "resist_berry": {"name": "半減の実", "effect_type": "equip_resist", "value": 0.5, "price": 2000, "unlock_rank": 15, "desc": "効果抜群のダメージを受けた時、威力を半減する（使い捨て）。"},
    
    # --- 新規追加アイテム ---
    "choice_band": {"name": "こだわりハチマキ", "effect_type": "equip_choice", "stat": "atk", "value": 1.5, "price": 10000, "unlock_rank": 25, "desc": "物理攻撃が1.5倍になるが、同じ技しか出せなくなる。"},
    "choice_specs": {"name": "こだわりメガネ", "effect_type": "equip_choice", "stat": "spa", "value": 1.5, "price": 10000, "unlock_rank": 25, "desc": "特殊攻撃が1.5倍になるが、同じ技しか出せなくなる。"},
    "life_orb": {"name": "命の珠", "effect_type": "equip_life_orb", "value": 1.3, "price": 8000, "unlock_rank": 20, "desc": "技の威力が1.3倍になるが、攻撃するたびにHPが減る。"},
    "expert_belt": {"name": "達人の帯", "effect_type": "equip_expert", "value": 1.2, "price": 5000, "unlock_rank": 15, "desc": "効果抜群の時、威力が1.2倍になる。"},

    "story_page_2": {"name": "失われし紡がれた物語のページその2", "effect_type": "key_item", "value": 0, "price": 0, "unlock_rank": 999, "desc": "隠された真実が記されたページの一部。"},
}

# --- 新規システム: パーティシナジー ---
# 特定の組み合わせがパーティ内にいると発動する効果
TEAM_SYNERGIES = {
    "golden_duo": {
        "name": "黄金の絆",
        "members": ["oatmeal", "ringo_ame"], # アグライア & トリスビアス
        "effect": {"type": "buff_start", "stats": {"atk": 1, "spa": 1}},
        "desc": "アグライアとトリスビアスの絆。攻撃・特攻ランクが上がる。"
    },
    "knights_oath": {
        "name": "騎士の誓い",
        "members": ["onkouna_ryu", "kijyukyou"], # 丹恒 & ケリュドラ
        "effect": {"type": "buff_start", "stats": {"def": 2}},
        "desc": "丹恒とケリュドラの誓い。防御ランクがぐーんと上がる。"
    },
    "sweet_tooth": {
        "name": "甘党同盟",
        "members": ["cho_cho_cake", "candy_roll", "honey_fruit_soup"], # キャストリス & なのか & メデイモス
        "effect": {"type": "regen", "percent": 0.05},
        "desc": "甘いもの好きたち。毎ターンHPが少し回復する。"
    },
    "elements": {
        "name": "元素の共鳴",
        "members": ["fire_lizard", "aqua_bird", "leaf_golem"], # 御三家
        "effect": {"type": "buff_start", "stats": {"spe": 1, "acc": 1}},
        "desc": "基本元素の調和。素早さと命中が上がる。"
    }
}

ACHIEVEMENTS = {
    "kimera_true_master": {"name_jp": "真・キメラマスター", "title_jp": "制作者泣かせ"},
    "kimera_champion": {"name_jp": "キメラチャンピオン", "title_jp": "ポ◯モンマスター"}
}

CHALLENGE_TRAINERS = {
    # 既存のトレーナーデータ (省略なしで記述)
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
        "reward_item": "story_page_2", "reward_title": "ポ◯モンマスター",
        "dialogue_start": "さあ、あなたの『愛』の深さ…試させてもらうわよ？",
        "dialogue_win": "ふふっ、素晴らしいわ！あなたこそチャンピオンよ♪"
    }
}

CHALLENGE_TRAINERS_HARD = {
    1: {
        "name": "真・アグライア",
        "party": [
            {"base_id": "light_fairy", "level": 110, "item": "sitrus_berry"}, 
            {"base_id": "light_fairy", "level": 110, "item": "sitrus_berry"},
            {"base_id": "oatmeal", "level": 115, "item": "choice_band"}
        ], "potions": 3,
        "dialogue_start": "金糸によって全てお見通しです。今回は負けません。",
        "dialogue_win": "私にも見えないまぶしい光でした…あなたの勝ちです。"
    },
    2: {
        "name": "真・トリスビアス",
        "party": [
            {"base_id": "leaf_golem", "level": 120, "item": "sitrus_berry"}, 
            {"base_id": "leaf_golem", "level": 120, "item": "sitrus_berry"},
            {"base_id": "ringo_ame", "level": 120, "item": "hard_stone"}
        ], "potions": 3,
        "dialogue_start": "あたち今度は負けないからね！",
        "dialogue_win": "すごーい戦いだったね！あたち負けちゃったよ〜"
    },
    3: {
        "name": "真・アナクサゴラス",
        "party": [
            {"base_id": "aqua_bird", "level": 125, "item": "wise_glasses"},
            {"base_id": "wolf_pup", "level": 125, "item": "power_band"},
            {"base_id": "nunusu", "level": 125, "item": "vitality_belt"}
        ], "potions": 3,
        "dialogue_start": "全てのパターンを考慮しました。敗北などありえないでしょう。",
        "dialogue_win": "おめでとうございます。"
    },
    4: {
        "name": "真・ヒアシンシア",
        "party": [
            {"base_id": "fire_lizard", "level": 130, "item": "power_band"},
            {"base_id": "light_fairy", "level": 130, "item": "sitrus_berry"},
            {"base_id": "cheribis", "level": 130, "item": "leftovers"}
        ], "potions": 4,
        "dialogue_start": "全力で行きますね♪",
        "dialogue_win": "お強いですね♪完敗です♪"
    },
    5: {
        "name": "真・メデイモス",
        "party": [
            {"base_id": "wolf_pup", "level": 135, "item": "power_band"},
            {"base_id": "wolf_pup", "level": 135, "item": "power_band"},
            {"base_id": "honey_fruit_soup", "level": 135, "item": "leftovers"}
        ], "potions": 4,
        "dialogue_start": "クレムノス人の辞書に“不可能”の文字は無い。",
        "dialogue_win": "俺に勝つとは…お見事だ。"
    },
    6: {
        "name": "真・セファリア",
        "party": [
            {"base_id": "dark_hound", "level": 140, "item": "choice_band"},
            {"base_id": "light_fairy", "level": 140, "item": "wise_glasses"},
            {"base_id": "nyanko_dorobou", "level": 140, "item": "focus_sash"}
        ], "potions": 4,
        "dialogue_start": "へへーん、今度は負けないよ！",
        "dialogue_win": "うぅ…負けちゃったよ〜！"
    },
    7: {
        "name": "真・キャストリス",
        "party": [
            {"base_id": "leaf_golem", "level": 145, "item": "hard_stone"},
            {"base_id": "light_fairy", "level": 145, "item": "wise_glasses"},
            {"base_id": "cho_cho_cake", "level": 145, "item": "leftovers"}
        ], "potions": 4,
        "dialogue_start": "腹が減っては戦はできぬ、と、言いますでしょう？",
        "dialogue_win": "レシピの改良が必要ですね……"
    },
    8: {
        "name": "真・ファイノン",
        "party": [
            {"base_id": "wolf_pup", "level": 150, "item": "power_band"},
            {"base_id": "leaf_golem", "level": 150, "item": "hard_stone"},
            {"base_id": "biguruyashi", "level": 150, "item": "choice_specs"}
        ], "potions": 4,
        "dialogue_start": "僕は、最強のキメラトレーナーになるんだ！",
        "dialogue_win": "僕の道は、まだ終わりじゃない。"
    },
    9: {
        "name": "真・セイレンス",
        "party": [
            {"base_id": "aqua_bird", "level": 155, "item": "wise_glasses"},
            {"base_id": "light_fairy", "level": 155, "item": "sitrus_berry"},
            {"base_id": "harapekono_sakana", "level": 155, "item": "leftovers"}
        ], "potions": 5,
        "dialogue_start": "いい余興になりそうだ。",
        "dialogue_win": "幕が下りた・・・"
    },
    10: {
        "name": "真・ケリュドラ",
        "party": [
            {"base_id": "dark_hound", "level": 160, "item": "life_orb"},
            {"base_id": "dark_hound", "level": 160, "item": "focus_sash"},
            {"base_id": "kijyukyou", "level": 160, "item": "focus_sash"}
        ], "potions": 5,
        "dialogue_start": "しょせんチェスとあまり変わらないだろう",
        "dialogue_win": "ほう…この僕を打ち負かすとは…やるではないか。。"
    },
    11: {
        "name": "真・三月なのか",
        "party": [
            {"base_id": "light_fairy", "level": 165, "item": "focus_sash"},
            {"base_id": "aqua_bird", "level": 165, "item": "wise_glasses"},
            {"base_id": "candy_roll", "level": 165, "item": "choice_specs"}
        ], "potions": 5,
        "dialogue_start": "アンタが相手でも手加減しないから！！",
        "dialogue_win": "負けちゃった〜。アンタ強いね。"
    },
    12: {
        "name": "真・丹恒",
        "party": [
            {"base_id": "leaf_golem", "level": 170, "item": "hard_stone"},
            {"base_id": "wolf_pup", "level": 170, "item": "power_band"},
            {"base_id": "onkouna_ryu", "level": 170, "item": "leftovers"}
        ], "potions": 5,
        "dialogue_start": "新たに得た力で、お前を止めよう。",
        "dialogue_win": "やるな。さっすがだ。"
    },
    13: {
        "name": "真・キュレネ",
        "party": [
            {"base_id": "cho_cho_cake", "level": 175, "item": "focus_sash"}, 
            {"base_id": "biguruyashi", "level": 180, "item": "life_orb"},
            {"base_id": "kyunure", "level": 175, "item": "leftovers"}
        ], "potions": 6,
        "reward_title": "キメラを極めし者",
        "dialogue_start": "これが私たちの『愛』の最終形…受け止めきれるかしら？",
        "dialogue_win": "ふふっ、素晴らしいわ！ あなたの愛、確かに受け取ったわ。"
    },
    14: {
        "name": "制作者 aeracero",
        "party": [
            {"base_id": "candy_roll", "level": 1000, "item": "life_orb"}, 
            {"base_id": "kyunure", "level": 1000, "item": "choice_specs"}, 
            {"base_id": "cheribis", "level": 1000, "item": "leftovers"}
        ], "potions": 33350337,
        "reward_title": "制作者泣かせ",
        "dialogue_start": "どうも、制作者のaeraceroです。今は暇なんで、相手してあげますよ。",
        "dialogue_win": "すごいっすね、まさか私も殺っちゃうなんて..."
    }
}