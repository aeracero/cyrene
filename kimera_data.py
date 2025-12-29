# kimera_data.py
# キメラ、技、アイテム、トレーナーのデータを管理します。

TYPES = ["Normal", "Fire", "Water", "Grass", "Light", "Dark"]

# --- 技データ (MOVES) ---
MOVES = {
    "scratch": {"name": "ひっかく", "type": "Normal", "category": "Physical", "power": 40, "accuracy": 100, "max_pp": 35},
    "tackle": {"name": "たいあたり", "type": "Normal", "category": "Physical", "power": 40, "accuracy": 100, "max_pp": 35},
    "ember": {"name": "火の粉", "type": "Fire", "category": "Special", "power": 40, "accuracy": 100, "max_pp": 25},
    "water_gun": {"name": "水鉄砲", "type": "Water", "category": "Special", "power": 40, "accuracy": 100, "max_pp": 25},
    "leaf_blade": {"name": "リーフブレード", "type": "Grass", "category": "Physical", "power": 90, "accuracy": 100, "max_pp": 15},
    "shining_ray": {"name": "光の矢", "type": "Light", "category": "Special", "power": 60, "accuracy": 100, "max_pp": 20},
    "shadow_claw": {"name": "シャドークロー", "type": "Dark", "category": "Physical", "power": 70, "accuracy": 100, "max_pp": 15},
    "flamethrower": {"name": "火炎放射", "type": "Fire", "category": "Special", "power": 90, "accuracy": 100, "max_pp": 15},
    "hydro_pump": {"name": "ハイドロポンプ", "type": "Water", "category": "Special", "power": 110, "accuracy": 80, "max_pp": 5},
    "solar_beam": {"name": "ソーラービーム", "type": "Grass", "category": "Special", "power": 120, "accuracy": 100, "max_pp": 10},
    "hyper_beam": {"name": "破壊光線", "type": "Normal", "category": "Special", "power": 150, "accuracy": 90, "max_pp": 5},
    "dark_pulse": {"name": "悪の波動", "type": "Dark", "category": "Special", "power": 80, "accuracy": 100, "max_pp": 15},
    "flash_cannon": {"name": "ラスターカノン", "type": "Light", "category": "Special", "power": 80, "accuracy": 100, "max_pp": 10},
}

# --- キメラのベースデータ (BASE_CHIMERAS) ---
BASE_CHIMERAS = {
    "wolf_pup": {
        "name": "ウルフパピー", "type": "Normal",
        "base_stats": {"hp": 45, "atk": 60, "def": 40, "spa": 30, "spd": 40, "spe": 65},
        "ability": "闘争心",
        "learnset": {1: "scratch", 5: "shadow_claw", 15: "tackle", 30: "hyper_beam"},
        "description": "元気な狼の子供。物理攻撃が得意。"
    },
    "aqua_bird": {
        "name": "アクアバード", "type": "Water",
        "base_stats": {"hp": 40, "atk": 30, "def": 35, "spa": 65, "spd": 50, "spe": 70},
        "ability": "激流",
        "learnset": {1: "scratch", 3: "water_gun", 15: "hydro_pump"},
        "description": "水を操る小鳥。素早さと魔法攻撃が高い。"
    },
    "leaf_golem": {
        "name": "リーフゴーレム", "type": "Grass",
        "base_stats": {"hp": 60, "atk": 50, "def": 70, "spa": 40, "spd": 60, "spe": 30},
        "ability": "深緑",
        "learnset": {1: "scratch", 8: "leaf_blade", 20: "solar_beam"},
        "description": "森の守り人。防御力が自慢。"
    },
    "fire_lizard": {
        "name": "フレアリザード", "type": "Fire",
        "base_stats": {"hp": 39, "atk": 52, "def": 43, "spa": 60, "spd": 50, "spe": 65},
        "ability": "猛火",
        "learnset": {1: "scratch", 6: "ember", 25: "flamethrower"},
        "description": "尻尾に炎を宿したトカゲ。"
    },
    "light_fairy": {
        "name": "ライトフェアリー", "type": "Light",
        "base_stats": {"hp": 50, "atk": 40, "def": 40, "spa": 70, "spd": 70, "spe": 60},
        "ability": "発光",
        "learnset": {1: "shining_ray", 10: "flash_cannon"},
        "description": "光り輝く妖精。"
    },
    "dark_hound": {
        "name": "ダークハウンド", "type": "Dark",
        "base_stats": {"hp": 60, "atk": 80, "def": 50, "spa": 40, "spd": 50, "spe": 70},
        "ability": "威圧",
        "learnset": {1: "shadow_claw", 12: "dark_pulse"},
        "description": "闇夜に潜む黒い犬。"
    }
}

# --- アイテムデータ (ITEMS) ---
ITEMS = {
    "monster_ball": {"name": "モンスターボール", "effect_type": "capture", "value": 1.0, "price": 200, "unlock_rank": 1, "desc": "野生のキメラを捕まえるボール。"},
    "super_ball": {"name": "スーパーボール", "effect_type": "capture", "value": 1.5, "price": 600, "unlock_rank": 10, "desc": "モンスターボールより捕まえやすいボール。"},
    "hyper_ball": {"name": "ハイパーボール", "effect_type": "capture", "value": 2.0, "price": 1200, "unlock_rank": 20, "desc": "かなり捕まえやすい高性能なボール。"},
    "potion": {"name": "キズぐすり", "effect_type": "heal", "value": 20, "price": 100, "unlock_rank": 1, "desc": "HPを20回復する。"},
    "super_potion": {"name": "いいキズぐすり", "effect_type": "heal", "value": 50, "price": 300, "unlock_rank": 5, "desc": "HPを50回復する。"},
    "hyper_potion": {"name": "すごいキズぐすり", "effect_type": "heal", "value": 200, "price": 1200, "unlock_rank": 15, "desc": "HPを200回復する。"},
    "power_band": {"name": "ちからのハチマキ", "effect_type": "equip_atk", "value": 1.1, "price": 500, "unlock_rank": 1, "desc": "持たせると物理攻撃が少し上がる。"},
    "exp_candy_s": {"name": "けいけんアメS", "effect_type": "exp", "value": 800, "price": 500, "unlock_rank": 3, "desc": "キメラに800の経験値を与える。"},
    "exp_candy_m": {"name": "けいけんアメM", "effect_type": "exp", "value": 3000, "price": 2000, "unlock_rank": 10, "desc": "キメラに3000の経験値を与える。"},
    "exp_candy_l": {"name": "けいけんアメL", "effect_type": "exp", "value": 10000, "price": 8000, "unlock_rank": 25, "desc": "キメラに10000の経験値を与える。"},
    "story_page_2": {"name": "失われし紡がれた物語のページその2", "effect_type": "key_item", "value": 0, "price": 0, "unlock_rank": 999, "desc": "隠された真実が記されたページの一部。"},
}

# --- チャレンジモード：黄金裔トレーナーデータ (13人抜き) ---
CHALLENGE_TRAINERS = {
    1: {
        "name": "黄金裔 アグライア",
        "dialogue_start": "美こそが力。私のデザインしたキメラたち、ご覧なさい！",
        "dialogue_win": "美しい敗北だわ…あなた、センスがあるのね。",
        "party": [
            {"base_id": "light_fairy", "level": 70},
            {"base_id": "light_fairy", "level": 70},
            {"base_id": "aqua_bird", "level": 72}
        ]
    },
    2: {
        "name": "黄金裔 トリスビアス",
        "dialogue_start": "ほっほっほ、若いの。ワシの知識と経験、越えられるかな？",
        "dialogue_win": "見事じゃ。未来は明るいようじゃな。",
        "party": [
            {"base_id": "leaf_golem", "level": 72},
            {"base_id": "leaf_golem", "level": 72},
            {"base_id": "fire_lizard", "level": 74}
        ]
    },
    3: {
        "name": "黄金裔 アナクサゴラス",
        "dialogue_start": "論理的思考こそが最強への道だ。",
        "dialogue_win": "計算外だ…感情の力が上回ったというのか？",
        "party": [
            {"base_id": "aqua_bird", "level": 75},
            {"base_id": "wolf_pup", "level": 75},
            {"base_id": "light_fairy", "level": 77}
        ]
    },
    4: {
        "name": "黄金裔 ヒアシンシア",
        "dialogue_start": "あら、お手柔らかにお願いね？ …なんて、手加減はしないわ。",
        "dialogue_win": "強烈ね…嫌いじゃないわ、その熱さ。",
        "party": [
            {"base_id": "fire_lizard", "level": 78},
            {"base_id": "fire_lizard", "level": 78},
            {"base_id": "dark_hound", "level": 80}
        ]
    },
    5: {
        "name": "黄金裔 メデイモス",
        "dialogue_start": "健康第一！鍛え上げた肉体とキメラの力、受けてみろ！",
        "dialogue_win": "ハッハッハ！気持ちのいい勝負だったぞ！",
        "party": [
            {"base_id": "wolf_pup", "level": 80},
            {"base_id": "wolf_pup", "level": 80},
            {"base_id": "leaf_golem", "level": 82}
        ]
    },
    6: {
        "name": "黄金裔 セファリア",
        "dialogue_start": "ふふっ、あなたの欲望…見せてもらうわよ？",
        "dialogue_win": "あらあら、すごい情熱ね。満足したわ。",
        "party": [
            {"base_id": "dark_hound", "level": 82},
            {"base_id": "light_fairy", "level": 82},
            {"base_id": "aqua_bird", "level": 85}
        ]
    },
    7: {
        "name": "黄金裔 キャストリス",
        "dialogue_start": "私の物語の登場人物にしてあげる！派手にいくよー！",
        "dialogue_win": "うっそー！？バッドエンド！？…でも面白いからオッケー！",
        "party": [
            {"base_id": "light_fairy", "level": 85},
            {"base_id": "leaf_golem", "level": 85},
            {"base_id": "wolf_pup", "level": 87}
        ]
    },
    8: {
        "name": "黄金裔 ファイノン",
        "dialogue_start": "ボクの計算によれば、キミの勝率は0%だよ。",
        "dialogue_win": "ボクの計算が間違っていたのか…？",
        "party": [
            {"base_id": "leaf_golem", "level": 88},
            {"base_id": "wolf_pup", "level": 88},
            {"base_id": "aqua_bird", "level": 90}
        ]
    },
    9: {
        "name": "黄金裔 セイレンス",
        "dialogue_start": "私の歌声と共に、永遠の眠りにつきなさい。",
        "dialogue_win": "静寂…それが敗北の味なのね。",
        "party": [
            {"base_id": "aqua_bird", "level": 90},
            {"base_id": "light_fairy", "level": 90},
            {"base_id": "dark_hound", "level": 92}
        ]
    },
    10: {
        "name": "黄金裔 ケリュドラ",
        "dialogue_start": "傲慢なる者よ、ひれ伏すがいい。",
        "dialogue_win": "馬鹿な…私が屈するなど…！",
        "party": [
            {"base_id": "dark_hound", "level": 92},
            {"base_id": "dark_hound", "level": 92},
            {"base_id": "fire_lizard", "level": 95}
        ]
    },
    11: {
        "name": "三月なのか",
        "dialogue_start": "あたしも負けてられないっ！可愛いキメラたち、いっくよー！",
        "dialogue_win": "ええーっ！？負けちゃった…でも楽しかったね！",
        "party": [
            {"base_id": "light_fairy", "level": 95},
            {"base_id": "aqua_bird", "level": 95},
            {"base_id": "light_fairy", "level": 97}
        ]
    },
    12: {
        "name": "丹恒",
        "dialogue_start": "…手合わせ願おう。全力で来てくれ。",
        "dialogue_win": "見事だ。学ぶべき点が多いな。",
        "party": [
            {"base_id": "leaf_golem", "level": 97},
            {"base_id": "wolf_pup", "level": 97},
            {"base_id": "aqua_bird", "level": 99}
        ]
    },
    13: {
        "name": "黄金裔 キュレネ",
        "dialogue_start": "ここまで来たのね。愛を込めて、全力で相手をしてあげるわ♪",
        "dialogue_win": "ああんっ、完敗よ…！ あなたのその強さ、とっても魅力的だわ♪",
        "party": [
            {"base_id": "wolf_pup", "level": 98},
            {"base_id": "fire_lizard", "level": 99},
            {"base_id": "leaf_golem", "level": 100}
        ],
        "reward_item": "story_page_2",
        "reward_title": "ポ◯モンマスターの"
    }
}