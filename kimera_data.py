# キメラ、技、アイテム、トレーナーのデータを管理します。

TYPES = ["Normal", "Fire", "Water", "Grass", "Light", "Dark", "Fairy"]

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
    "dragon_breath": {"name": "竜の息吹", "type": "Light", "category": "Special", "power": 60, "accuracy": 100, "max_pp": 20},
    "dragon_claw": {"name": "ドラゴンクロー", "type": "Normal", "category": "Physical", "power": 80, "accuracy": 100, "max_pp": 15},
    "dazzling_gleam": {"name": "マジカルシャイン", "type": "Fairy", "category": "Special", "power": 80, "accuracy": 100, "max_pp": 10},
}

# --- キメラのベースデータ (BASE_CHIMERAS) ---
BASE_CHIMERAS = {
    # ★1 (初期/Common)
    "wolf_pup": {
        "name": "ウルフパピー", "type": "Normal", "rarity": 1,
        "base_stats": {"hp": 45, "atk": 60, "def": 40, "spa": 30, "spd": 40, "spe": 65},
        "ability": "闘争心", # 同性なら攻撃UP
        "learnset": {1: "scratch", 5: "shadow_claw", 15: "tackle", 30: "hyper_beam"},
        "description": "元気な狼の子供。物理攻撃が得意。"
    },
    "aqua_bird": {
        "name": "アクアバード", "type": "Water", "rarity": 1,
        "base_stats": {"hp": 40, "atk": 30, "def": 35, "spa": 65, "spd": 50, "spe": 70},
        "ability": "激流", # ピンチで水技強化
        "learnset": {1: "scratch", 3: "water_gun", 15: "hydro_pump"},
        "description": "水を操る小鳥。素早さと魔法攻撃が高い。"
    },
    "leaf_golem": {
        "name": "リーフゴーレム", "type": "Grass", "rarity": 1,
        "base_stats": {"hp": 60, "atk": 50, "def": 70, "spa": 40, "spd": 60, "spe": 30},
        "ability": "深緑", # ピンチで草技強化
        "learnset": {1: "scratch", 8: "leaf_blade", 20: "solar_beam"},
        "description": "森の守り人。防御力が自慢。"
    },
    "fire_lizard": {
        "name": "フレアリザード", "type": "Fire", "rarity": 1,
        "base_stats": {"hp": 39, "atk": 52, "def": 43, "spa": 60, "spd": 50, "spe": 65},
        "ability": "猛火", # ピンチで炎技強化
        "learnset": {1: "scratch", 6: "ember", 25: "flamethrower"},
        "description": "尻尾に炎を宿したトカゲ。"
    },
    "light_fairy": {
        "name": "ライトフェアリー", "type": "Light", "rarity": 2,
        "base_stats": {"hp": 50, "atk": 40, "def": 40, "spa": 70, "spd": 70, "spe": 60},
        "ability": "発光", # 命中率UP
        "learnset": {1: "shining_ray", 10: "flash_cannon"},
        "description": "光り輝く妖精。"
    },
    "dark_hound": {
        "name": "ダークハウンド", "type": "Dark", "rarity": 2,
        "base_stats": {"hp": 60, "atk": 80, "def": 50, "spa": 40, "spd": 50, "spe": 70},
        "ability": "威圧", # 登場時相手の攻撃ダウン
        "learnset": {1: "shadow_claw", 12: "dark_pulse"},
        "description": "闇夜に潜む黒い犬。"
    },
    "cheribis":{
        "name": "チェリビス", "type": "Light", "rarity": 6,
        "base_stats": {"hp": 55, "atk": 45, "def": 50, "spa": 75, "spd": 65, "spe": 55},
        "ability": "癒しの光", # 毎ターン回復
        "learnset": {1: "shining_ray", 10: "flash_cannon", 20: "hyper_beam"},
        "description": "癒しの力を持つ光のキメラ。"
    },
    "cho_cho_cake":{
        "name": "チョウチョウケーキ", "type": "Normal", "rarity": 6,
        "base_stats": {"hp": 70, "atk": 30, "def": 60, "spa": 50, "spd": 65, "spe": 25},
        "ability": "甘美な誘惑", # 相手の攻撃ダウン
        "learnset": {1: "tackle", 5: "hyper_beam"},
        "description": "甘くて美味しいケーキのキメラ。"
    },
    "ringo_ame":{
        "name": "リンゴアメ", "type": "Grass", "rarity": 6,
        "base_stats": {"hp": 65, "atk": 55, "def": 55, "spa": 45, "spd": 50, "spe": 40},
        "ability": "ロケット", # 素早さUP
        "learnset": {1: "tackle", 7: "leaf_blade"},
        "description": "リンゴ飴のキメラ。"
    },
    "harapekono_sakana":{
        "name": "腹ペコの魚", "type": "Water", "rarity": 6,
        "base_stats": {"hp": 50, "atk": 60, "def": 40, "spa": 55, "spd": 45, "spe": 70},
        "ability": "食いしん坊", # きのみの効果UP
        "learnset": {1: "scratch", 4: "water_gun"},
        "description": "いつもお腹を空かせている魚のキメラ。"
    },
    "candy_roll":{
        "name": "キャンディーロール", "type": "Fire", "rarity": 6,
        "base_stats": {"hp": 55, "atk": 50, "def": 45, "spa": 65, "spd": 50, "spe": 60},
        "ability": "忘却", # 相手の防御無視
        "learnset": {1: "ember", 9: "flamethrower"},
        "description": "キャンディーのように甘い炎を操るキメラ。"
    },
    "honey_fruit_soup":{
        "name": "ハニーフルーツスープ", "type": "Dark", "rarity": 6,
        "base_stats": {"hp": 60, "atk": 55, "def": 50, "spa": 60, "spd": 55, "spe": 45},
        "ability": "蘇り", # HP自動回復
        "learnset": {1: "shadow_claw", 11: "dark_pulse"},
        "description": "甘い果実と蜂蜜でできたスープのキメラ。"
    },
    "oatmeal":{
        "name": "オートミール", "type": "Normal", "rarity": 6,
        "base_stats": {"hp": 65, "atk": 55, "def": 60, "spa": 50, "spd": 55, "spe": 40},
        "ability": "金糸雀", # 歌声で相手の攻撃ダウン
        "learnset": {1: "tackle", 6: "hyper_beam"},
        "description": "健康に良いオートミールのキメラ。"
    },
    "nunusu":{
        "name": "ヌヌス", "type": "Grass", "rarity": 6,
        "base_stats": {"hp": 75, "atk": 65, "def": 70, "spa": 80, "spd": 75, "spe": 55},
        "ability": "大地獣", # 防御UP
        "learnset": {1: "leaf_blade", 12: "solar_beam"},
        "description": "地龍を愛するキメラ。"
    },
    "nyanko_dorobou":{
        "name": "ニャンコ泥棒", "type": "Dark", "rarity": 6,
        "base_stats": {"hp": 50, "atk": 70, "def": 45, "spa": 40, "spd": 50, "spe": 80},
        "ability": "盗みの天才", # 素早さUP
        "learnset": {1: "scratch", 5: "shadow_claw", 15: "dark_pulse"},
        "description": "素早く物を盗む猫のキメラ。"
    },
    "biguruyashi":{
        "name": "ビ-グルヤシ", "type": "Fire", "rarity": 6,
        "base_stats": {"hp": 60, "atk": 80, "def": 50, "spa": 70, "spd": 55, "spe": 65},
        "ability": "炎の守護者", # 炎技威力UP
        "learnset": {1: "ember", 8: "flamethrower"},
        "description": "火種を操るキメラ。"
    },
    "uriu":{
        "name": "ウリウ", "type": "Water", "rarity": 2,
        "base_stats": {"hp": 55, "atk": 60, "def": 50, "spa": 65, "spd": 55, "spe": 60},
        "ability": "水流", # 素早さUP
        "learnset": {1: "water_gun", 7: "hydro_pump"},
        "description": "水中を自在に泳ぐキメラ。"
    },
    "tanki":{
        "name": "短気", "type": "Fire", "rarity": 2,
        "base_stats": {"hp": 60, "atk": 70, "def": 55, "spa": 65, "spd": 50, "spe": 75},
        "ability": "短気", # 攻撃UPだが防御DOWN
        "learnset": {1: "ember", 8: "flamethrower"},
        "description": "短気な火のキメラ。"
    },
    "skape_goat":{
        "name": "スケープゴート", "type": "Grass"," rarity": 2,
        "base_stats": {"hp": 70, "atk": 60, "def": 65, "spa": 55, "spd": 60, "spe": 50},
        "ability": "犠牲者", # HPが高い
        "learnset": {1: "leaf_blade", 10: "solar_beam"},
        "description": "犠牲を厭わない草のキメラ。"
    },
    "onkouna_ryu":{
        "name": "温厚な竜", "type": "Light", "rarity": 6,
        "base_stats": {"hp": 90, "atk": 80, "def": 85, "spa": 100, "spd": 95, "spe": 70}, # ステータス強化
        "ability": "皆を守る者", # 味方全体の防御UP
        "learnset": {1: "dragon_breath", 15: "dragon_claw"},
        "description": "温厚な竜のキメラ。"
    },
    "kijyukyou":{
        "name": "奇獣卿", "type": "Dark", "rarity": 6,
        "base_stats": {"hp": 100, "atk": 90, "def": 85, "spa": 80, "spd": 75, "spe": 70}, # ステータス強化
        "ability": "王の風格", # 相手の全ステータスダウン効果
        "learnset": {1: "shadow_claw", 10: "dark_pulse", 20: "hyper_beam"},
        "description": "奇妙な力を持つキメラ。"
    },
    "kyunure":{
        "name": "キュヌレ", "type": "Fairy", "rarity": 6,
        "base_stats": {"hp": 85, "atk": 70, "def": 75, "spa": 90, "spd": 80, "spe": 95}, # ステータス強化
        "ability": "最愛", # 全ステータスUP
        "learnset": {1: "tackle", 10: "dazzling_gleam"},
        "description": "愛の力を操るキメラ。"
    }
}

# --- アイテムデータ (ITEMS) ---
ITEMS = {
    "monster_ball": {"name": "モンスターボール", "effect_type": "capture", "value": 1.0, "price": 200, "unlock_rank": 1, "desc": "野生のキメラを捕まえるボール。"},
    "super_ball": {"name": "スーパーボール", "effect_type": "capture", "value": 1.5, "price": 600, "unlock_rank": 10, "desc": "モンスターボールより捕まえやすいボール。"},
    "hyper_ball": {"name": "ハイパーボール", "effect_type": "capture", "value": 2.0, "price": 1200, "unlock_rank": 20, "desc": "かなり捕まえやすい高性能なボール。"},
    
    "potion": {"name": "キズぐすり", "effect_type": "heal", "value": 50, "price": 100, "unlock_rank": 1, "desc": "HPを50回復する。"},
    "super_potion": {"name": "いいキズぐすり", "effect_type": "heal", "value": 150, "price": 500, "unlock_rank": 5, "desc": "HPを150回復する。"},
    "hyper_potion": {"name": "すごいキズぐすり", "effect_type": "heal", "value": 400, "price": 1500, "unlock_rank": 15, "desc": "HPを400回復する。"},
    
    # 育成
    "exp_candy_s": {"name": "けいけんアメS", "effect_type": "exp", "value": 5000, "price": 500, "unlock_rank": 1, "desc": "キメラに5000の経験値を与える。"},
    "exp_candy_m": {"name": "けいけんアメM", "effect_type": "exp", "value": 20000, "price": 2000, "unlock_rank": 5, "desc": "キメラに20000の経験値を与える。"},
    "exp_candy_l": {"name": "けいけんアメL", "effect_type": "exp", "value": 100000, "price": 8000, "unlock_rank": 15, "desc": "キメラに100000の経験値を与える。"},
    
    # 新規装備アイテム
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
# レベル100超え、全員持ち物あり、AI用ポーション所持
CHALLENGE_TRAINERS_HARD = {
    1: {
        "name": "真・アグライア",
        "party": [{"base_id": "light_fairy", "level": 105, "item": "sitrus_berry"}, {"base_id": "oatmeal", "level": 110, "item": "power_band"}], "potions": 2,
        "dialogue_start": "金糸によって全てお見通しです。今回は負けません。",
        "dialogue_win": "私にも見えないまぶしい光でした…あなたの勝ちです。"
    },
    2: {
        "name": "真・トリスビアス",
        "party": [{"base_id": "ringo_ame", "level": 115, "item": "hard_stone"}, {"base_id": "leaf_golem", "level": 115, "item": "sitrus_berry"}], "potions": 2,
        "dialogue_start": "あたち今度は負けないからね！",
        "dialogue_win": "すごーい戦いだったね！あたち負けちゃったよ〜"
    },
    3: {
        "name": "真・アナクサゴラス",
        "party": [{"base_id": "nunusu", "level": 120, "item": "vitality_belt"}, {"base_id": "aqua_bird", "level": 120, "item": "wise_glasses"}], "potions": 2,
        "dialogue_start": "全てのパターンを考慮しました。敗北などありえないでしょう。",
        "dialogue_win": "おめでとうございます。"
    },
    4: {
        "name": "真・ヒアシンシア",
        "party": [{"base_id": "cheribis", "level": 125, "item": "leftovers"}, {"base_id": "fire_lizard", "level": 125, "item": "power_band"}], "potions": 3,
        "dialogue_start": "全力で行きますね♪",
        "dialogue_win": "お強いですね♪完敗です♪"
    },
    5: {
        "name": "真・メデイモス",
        "party": [{"base_id": "honey_fruit_soup", "level": 130, "item": "leftovers"}, {"base_id": "wolf_pup", "level": 130, "item": "power_band"}], "potions": 3,
        "dialogue_start": "クレムノス人の辞書に“不可能”の文字は無い。",
        "dialogue_win": "俺に勝つとは…お見事だ。"
    },
    6: {
        "name": "真・セファリア",
        "party": [{"base_id": "nyanko_dorobou", "level": 135, "item": "focus_sash"}, {"base_id": "dark_hound", "level": 135, "item": "power_band"}], "potions": 3,
        "dialogue_start": "へへーん、今度は負けないよ！",
        "dialogue_win": "うぅ…負けちゃったよ〜！"
    },
    7: {
        "name": "真・キャストリス",
        "party": [{"base_id": "cho_cho_cake", "level": 140, "item": "leftovers"}, {"base_id": "leaf_golem", "level": 140, "item": "hard_stone"}], "potions": 3,
        "dialogue_start": "腹が減っては戦はできぬ、と、言いますでしょう？",
        "dialogue_win": "レシピの改良が必要ですね……"
    },
    8: {
        "name": "真・ファイノン",
        "party": [{"base_id": "biguruyashi", "level": 145, "item": "wise_glasses"}, {"base_id": "wolf_pup", "level": 145, "item": "power_band"}], "potions": 3,
        "dialogue_start": "僕は、最強のキメラトレーナーになるんだ！",
        "dialogue_win": "僕の道は、まだ終わりじゃない。"
    },
    9: {
        "name": "真・セイレンス",
        "party": [{"base_id": "harapekono_sakana", "level": 150, "item": "leftovers"}, {"base_id": "aqua_bird", "level": 150, "item": "wise_glasses"}], "potions": 4,
        "dialogue_start": "いい余興になりそうだ。",
        "dialogue_win": "幕が下りた・・・"
    },
    10: {
        "name": "真・ケリュドラ",
        "party": [{"base_id": "kijyukyou", "level": 155, "item": "focus_sash"}, {"base_id": "dark_hound", "level": 155, "item": "power_band"}], "potions": 4,
        "dialogue_start": "しょせんチェスとあまり変わらないだろう",
        "dialogue_win": "ほう…この僕を打ち負かすとは…やるではないか。。"
    },
    11: {
        "name": "真・三月なのか",
        "party": [{"base_id": "candy_roll", "level": 160, "item": "wise_glasses"}, {"base_id": "light_fairy", "level": 160, "item": "focus_sash"}], "potions": 4,
        "dialogue_start": "アンタが相手でも手加減しないから！！",
        "dialogue_win": "負けちゃった〜。アンタ強いね。"
    },
    12: {
        "name": "真・丹恒",
        "party": [{"base_id": "onkouna_ryu", "level": 165, "item": "leftovers"}, {"base_id": "leaf_golem", "level": 165, "item": "hard_stone"}], "potions": 4,
        "dialogue_start": "新たに得た力で、お前を止めよう。",
        "dialogue_win": "やるな。さっすがだ。"
    },
    13: {
        "name": "真・キュレネ",
        "party": [{"base_id": "kyunure", "level": 170, "item": "leftovers"}, {"base_id": "cho_cho_cake", "level": 170, "item": "focus_sash"}, {"base_id": "biguruyashi", "level": 175, "item": "wise_glasses"}], "potions": 5,
        "reward_title": "キメラを極めし者",
        "dialogue_start": "これが私たちの『愛』の最終形…受け止めきれるかしら？",
        "dialogue_win": "ふふっ、素晴らしいわ！ あなたの愛、確かに受け取ったわ。"
    }
}