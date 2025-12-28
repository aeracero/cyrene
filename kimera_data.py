# kimera_data.py
# キメラ、技、アイテムのデータを管理します。

TYPES = ["Normal", "Fire", "Water", "Grass", "Light", "Dark"]

# --- 技データ (MOVES) ---
MOVES = {
    "scratch": {
        "name": "ひっかく",
        "type": "Normal",
        "category": "Physical",
        "power": 40,
        "accuracy": 100,
        "max_pp": 35
    },
    "ember": {
        "name": "火の粉",
        "type": "Fire",
        "category": "Special",
        "power": 40,
        "accuracy": 100,
        "max_pp": 25
    },
    "water_gun": {
        "name": "水鉄砲",
        "type": "Water",
        "category": "Special",
        "power": 40,
        "accuracy": 100,
        "max_pp": 25
    },
    "leaf_blade": {
        "name": "リーフブレード",
        "type": "Grass",
        "category": "Physical",
        "power": 90,
        "accuracy": 100,
        "max_pp": 15
    },
    "shining_ray": {
        "name": "光の矢",
        "type": "Light",
        "category": "Special",
        "power": 60,
        "accuracy": 100,
        "max_pp": 20
    },
    "shadow_claw": {
        "name": "シャドークロー",
        "type": "Dark",
        "category": "Physical",
        "power": 70,
        "accuracy": 100,
        "max_pp": 15
    },
    "tackle": {
        "name": "たいあたり",
        "type": "Normal",
        "category": "Physical",
        "power": 40,
        "accuracy": 100,
        "max_pp": 35
    }
}

# --- キメラのベースデータ (BASE_CHIMERAS) ---
BASE_CHIMERAS = {
    "wolf_pup": {
        "name": "ウルフパピー",
        "type": "Normal",
        "base_stats": {"hp": 45, "atk": 60, "def": 40, "spa": 30, "spd": 40, "spe": 65},
        "ability": "闘争心",
        "learnset": {
            1: "scratch",
            5: "shadow_claw"
        },
        "description": "元気な狼の子供。物理攻撃が得意。"
    },
    "aqua_bird": {
        "name": "アクアバード",
        "type": "Water",
        "base_stats": {"hp": 40, "atk": 30, "def": 35, "spa": 65, "spd": 50, "spe": 70},
        "ability": "激流",
        "learnset": {
            1: "scratch",
            3: "water_gun"
        },
        "description": "水を操る小鳥。素早さと魔法攻撃が高い。"
    },
    "leaf_golem": {
        "name": "リーフゴーレム",
        "type": "Grass",
        "base_stats": {"hp": 60, "atk": 50, "def": 70, "spa": 40, "spd": 60, "spe": 30},
        "ability": "深緑",
        "learnset": {
            1: "scratch",
            8: "leaf_blade"
        },
        "description": "森の守り人。防御力が自慢。"
    }
}

# --- アイテムデータ (ITEMS) ---
# id: キー名
# name: 日本語名
# effect_type: heal (回復), capture (捕獲), equip (装備)
ITEMS = {
    "monster_ball": {
        "name": "モンスターボール",
        "effect_type": "capture",
        "value": 1.0, # 捕獲倍率
        "price": 200,
        "desc": "野生のキメラを捕まえるボール。"
    },
    "potion": {
        "name": "キズぐすり",
        "effect_type": "heal",
        "value": 20,
        "price": 100,
        "desc": "HPを20回復する。"
    },
    "super_potion": {
        "name": "いいキズぐすり",
        "effect_type": "heal",
        "value": 50,
        "price": 300,
        "desc": "HPを50回復する。"
    },
    "power_band": {
        "name": "ちからのハチマキ",
        "effect_type": "equip_atk",
        "value": 1.1,
        "price": 500,
        "desc": "持たせると物理攻撃が少し上がる。"
    }
}