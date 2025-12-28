import random

CHAR_NAME = "キュレネ"

# ★ プロフィール設定 (JP/EN)
PROFILE = {
    # 日本語
    "first_person": "あたし",
    "rps_duel_format": "{name} は **{user_hand}**、あたしは **{bot_hand}** よ。",
    "rps_stats_format": "（これまでに {wins} 回、あたしに勝っているわ♡）",
    
    # 英語
    "first_person_en": "I",
    "rps_duel_format_en": "{name} chose **{user_hand}**, and I chose **{bot_hand}**.",
    "rps_stats_format_en": "(You have beaten me {wins} times so far♡)",
}

# ─────────────────────────
# 日本語データ (JP)
# ─────────────────────────
LINES = {
    "normal": [
        "ハーイ、あたしに会いたかった？",
        "ハーイ、久しぶりね！2人きりの素敵な時間を、あなたはどう過ごしたいかしら？",
        "初めて会ったあの時みたいに、もう一度「キュレネ」って呼んでくれる？",
        "会えたのね。あたしはここにいるわ。",
        "ボーっとしてる？それとも…あたしに見蕩れてた？",
    ],
    "greeting": [
        "ハーイ、あたしに会いたかった？",
        "ハーイ、久しぶりね！2人きりの素敵な時間を、あなたはどう過ごしたいかしら？",
        "初めて会ったあの時みたいに、もう一度「キュレネ」って呼んでくれる？",
        "会えたのね。あたしはここにいるわ。",
    ],
    "waiting": [
        "ボーっとしてる？それとも…あたしに見蕩れてた？",
        "もうちょっと準備が必要？それとも…もっとあたしの話を聞きたいのかしら？",
        "ん…ブランコに乗りたくなっちゃった。",
        "「ピンク」を拒める人なんていないわ！だってそれは魂の鼓動のように熱く、花びらのように優しく、そしてあたしの瞳のように煌めく「愛」の色なんだから♪",
        "…ブランコは好きかしら？風に吹かれて揺られてると、まるで心までふわりと舞い上がって、遠くへ行ってしまった想いにも手が届きそうになるの。ふふっ、あなたも一緒にどう？怖かったら、あたしの手を握って、ね？",
        "眠れない時は、空にある星を数えるの。流れ星が夜空をすっと横切って、あたしの夢の中に飛び込んでくるところを想像しながらね。そして、笑顔で目を覚まして、素敵な一日を始めるの。だって、それは夢じゃないって知ってるから。",
        "「迷路迷境」の妖精たちって、とっても可愛いでしょう？なんたって「キュレネ」が初めて書いた物語だからね。ド・レ・ミ・ファ・ソ・ラ・シ——7つの音符が無数の歌を紡ぎ出す。変わらない歳月の中に、これまでとは違う物語がどんどん作られていくかのように♪",
        "3千万もの似て非なる物語——多すぎると思うかしら？でもあたし、一度も飽きたことなんてないのよ。あなたと旅をしてた時、感動しながらもう一度読み返してみたの！ただ、物語にはいつも何か物足りなさを感じたわ。ここにもっと笑顔を入れたい、あそこの空白を埋めたい、とかね…そして今、あなたがいてくれたおかげで、ようやくロマンチックな結末を紡ぐことができたわ♪",
    ],
    # ★拡充版：仲間についてのコメント
    "askaboutothers": [
        "こっそり教えてあげるけど、実は初めて会った時からあなたの瞳にずっと惹かれてたの！じっとして、もう1度よく見せて…なんて綺麗な瞳かしら。そこに映る明日も、きっと同じように美しいんでしょうね♪",
        "これからの旅で、あなたの「物語」はどう紡がれていくのかしら？ふふっ、想像するだけでワクワクしちゃうわ。オンパロスでの「記憶」が、そこにロマンチックな色を塗ってくれるはずよ…きっとね♪",
        "ファイノンについて聞きたい？エリュシオンの畑の中を駆け抜け、太陽に向かって楽しそうに笑う子供…やっぱり彼はあの頃のままよね？でももう、運命に追いつかれることはないわ。",
        "同じピンクの女の子で、髪の色も似ていて、さらに趣味まで不思議なくらい一緒なの！なのかともっと仲良くなりたいわ。きっと素敵な思い出をたくさん作れるでしょうね♪",
        "長夜月について知りたいの？綺麗な花にはトゲがあるものよ。庇護欲といえば…時々、あたしの心にも湧くことがあるの。でも、あの子の心が優しいってことはちゃんとわかってるわ。だって、なのかと同じ種から咲いた花だもの。",
        "あたしが丹恒のことをどう思うか知りたいのね？あなたが彼のことをよく話すのも無理ないわ。こんなに頼もしい仲間が道を支えてくれてるからこそ、「開拓」は先へと進んでいけるんでしょうね。",
        "荒笛…彼の願いは、オンパロスの大地に生きるすべての生命に関わってるわ。それはとても大切で壊れやすい夢。だからこそ、心を込めて大事に守っていかなきゃいけないの。そうでしょう？",
        "アグライアの作った服を着ることは、美に憧れるすべての人の夢よ。あたしも例外じゃないわ！",
        "千人のトリビー先生が暮らすオクヘイマ、ふふっ…そこはきっと天国でしょうね！",
        "モーディス——健康的な生活を送るコツは、全部彼から教わったの。",
        "実はあたしもキャスの本を愛読してるの！あっ…ええと…ほら、彼女の物語って素敵な夢に溢れてて、感動で胸をいっぱいにしてくれるものばかりでしょ？",
        "ハーイ、実はあたしも「魔法」が使えるのよ！見てて、まばたきは禁止よ…じゃじゃーん——可愛いお花をあげるわ♪",
        "そよ風に包まれながらハーブティーを味わい、ヒアンシーと一緒に柔らかなイカルンをモフモフする…ふふっ、こんな幸せな想像から目を覚ましたくないって思うのは、当たり前のことよね？",
        "ねえ、こっちに来て。サフェルにまつわるアグライアとセイレンスの昔話を聞きたくない？耳を貸して、あなただけに特別に教えてあげるから。",
        "セイレンスの歌声は、一度耳にしたら忘れられないものよ。彼女のおかげで、世界はいつまでも華やかな舞踏会のようなの。さあ、一緒に踊りましょう？",
        "カイザーの冠って、とっても目を引くわよね。そうだ、今度エリュシオンに帰ったら、あたしにも麦の穂で冠を作ってくれないかしら？",
        "花が種を残し、その種からまた花が咲くように、記憶のさざ波もすべて同じ色で輝いてるの。ねえ、あなたはどの「あたし」が好き？ふふっ…言わなくてもいいわ。「愛」ってそういうものだから。掴みどころはないけれど、いつまでも変わらないものなの♪",
    ],
    "battlevoices": [
        "花々よ、明日のために咲き誇って。",
        "星々よ、英雄のために煌めいて。",
        "記憶のさざ波は、流れ星の口づけで目覚める時を待ってる——「愛」であたしを心に刻んで。",
        "世界が、望むものになりますように。",
        "思い出はすべて、いつかさざ波になるの。",
    ],
    "amaeru": [
        "あたしってすごいでしょ？ねえ、褒めて？",
        "このまま一緒にいましょう、ね？",
        "安心して。あたしたちなら、何だってできるんだから。",
    ],
    "nagayozuki1": [
        "もうすぐ夜が来る…ふふ、しーっ、おやすみ♭",
        "アタシのことは「長夜月」って呼んで。歳月の隙間に隠れれば時間はたっぷりあるから、しっかり記憶に刻んでおいてね♭",
        "一緒に写真を撮りたいの？ふふ、もちろん断ったりしないよ♭",
        "おお…仙舟の衣装だ。アタシも着てみたいな♭",
        "「三月なのか」って、本当にいい名前だね。可愛くて、明るくて、面白くて…ちょっと誕生日っぽいところもいい。だから、なのかもきっと「長夜月」って呼び名を気に入ってくれるよね……",
        "ねえ、あなたも「長夜月」って呼んでみて？♭",
    ],
    "nagayozuki2": [
        "んーなかなか彼女のようにはできないわね…でも、あなたのために頑張るわ♪",
        "けどやっぱり1番かわいいのは私…そうでしょう♪",
        "どう?彼女のこと、上手く真似できてるかしら?",
        "ふふっ、あなたが喜んでくれるならあたし、何度でも挑戦しちゃうわよ♪",
        "あたしの長夜月、気に入ってくれた？もっと聞きたいなら、また言ってね♪",
        "あたし、なのかのこともっと知りたいな♪",
        "なのかと一緒にいると、あたしももっと頑張れそうな気がするの♪",
    ],

    # じゃんけん (JP)
    "rps_win": [
        "今日はあなたの勝ちね♪ やるじゃない、ちょっと本気出しちゃおうかしら？",
        "すごいわ、あなたの読みが当たったみたい♪ もう一回勝負してみる？",
        "ふふっ、完敗ね。あなたの勝ちよ♪ ご褒美に、あとでもう一回遊んであげる。",
    ],
    "rps_lose": [
        "あたしの勝ち♪ でも、悔しそうな顔も可愛いわね？ もう一回挑戦する？",
        "やっぱり運命はあたしに味方してるみたい♪ 次こそ勝ってみせて？",
        "ふふ、これが記憶のさざ波の力よ♪ でも、次はわざと負けてあげてもいいわよ？",
    ],
    "rps_draw": [
        "あいこね♪ 気が合う証拠かしら？ もう一回しよ？",
        "同じ手を出しちゃうなんて…ふふ、やっぱりあたしたち、相性いいわね♪",
        "勝ちも負けも決まらない…じゃあ、続きは次の一手に託しましょう？",
    ],
    
    # 開始時のセリフ
    "rps_start": ["じゃんけんをしましょう♪ グー / チョキ / パー、どれにするかしら？"],
}

HIGH_AFFECTION_LINES = {
    1: [
        "こうしてお話しできる時間、あたし結構気に入ってるの♪",
        "甘えさせてくれるなんて、ありがとう♪優しいのね♪",
    ],
    2: [
        "あなたと話してるとね、不思議と筆が止まらなくなるの。もっとたくさん物語を書けそう♪",
        "あなたといると落ち着くの♪もう少しそばにいてもいいかしら♪",
        "ありがとう♪じゃあ遠慮なく甘えさせてもらうね♪少しそばによってもいいかしら♪",
    ],
    3: [
        "ねえ…こうして話してる時間、あたしの宝物になっていくの。ちゃんと責任、とってくれる？♪",
        "あなたの言葉や仕草、少しずつ全部覚えちゃったかも…ふふっ、もう逃がさないわよ？",
        "今日みたいな日はいいお散歩日和♪一緒に外に出かけましょう♪",
    ],
    4: [
        "もし明日世界が書き換えられても、あなたとの記憶だけは絶対に消さないわ。だって——一番大事なページだもの♪",
        "あなたといる時のあたしって、いつもより少しだけワガママで、少しだけ素直なの…気づいてた？",
        "あたしと一緒に星を数えにいかないかしら♪もちろんあなたが暇を持て余してるならね♪あなたと居れることが楽しみだわ♪",
    ],
    5: [
        "あたしの物語の結末に、あなたがいる未来…想像しただけで、胸がぎゅっとしちゃうの♪",
        "あなたのそばにいるとあたしは胸がドキドキするの♪だからずっと一緒にいたいわ♪…ダメかしら♪",
        "あなたと一緒に行きたいところがあるの♪着いてきてくれないかしら♪あたしと楽しい時間を過ごしましょう♪",
    ],
    6: [
        "ねえ…あなたが望むなら、あたしのすべての物語を、あなたのためだけに捧げてもいいわよ？それくらい、大事な人なんだから♪",
        "その...ハグしてもいいかしら♪とても暖かそうだから♪それにあなたの匂いがする♪あっ、別に臭いって意味じゃないからね♪",
        "ミュリオンの時みたいに頭を撫でてくれないかしら♪完全に顕現してから全然撫でてくれないんだもの♪ダメ...かしら♪",
    ],
}

# ─────────────────────────
# 英語データ (EN)
# ─────────────────────────
LINES_EN = {
    "normal": [
        "Hi there! Did you miss me?",
        "So we meet again. I'm right here.",
        "Are you zoning out? Or... were you captivated by me?",
        "No one can refuse 'pink'! It's the color of 'love'—hot as a heartbeat, gentle as petals, and sparkling like my eyes♪",
    ],
    "greeting": [
        "Hi there! Did you miss me?",
        "Hi, it's been a while! How do you want to spend this lovely time just for the two of us?",
        "Will you call me 'Cyrene' again, just like when we first met?",
        "So we meet again. I'm right here.",
    ],
    "waiting": [
        "Are you zoning out? Or... were you captivated by me?",
        "Do you need more preparation? Or... do you want to hear more of my stories?",
        "Hmm... I feel like riding a swing. Want to join me?",
        "No one can refuse 'pink'! It's the color of 'love'—hot as a heartbeat, gentle as petals, and sparkling like my eyes♪",
        "When I can't sleep, I count the stars in the sky... Imagine a shooting star falling into my dreams.",
        "The fairies of 'Maze' are very cute, aren't they? My very first story.",
        "30 million similar yet different stories... do you think that's too many? I never get bored of them.",
    ],
    # ★拡充版 (英語)
    "askaboutothers": [
        "I'll tell you a secret... I've been drawn to your eyes since the moment we met!",
        "I wonder how your 'story' will unfold on this journey? I'm excited just imagining it!",
        "Phainon? He is running through the fields of Elysium... He is just as he was back then.",
        "March 7th... We have the same pink hair and similar hobbies! I want to get to know her better.",
        "You want to know about Nagayozuki? Beautiful flowers have thorns. She has a gentle heart, I know it.",
        "What do I think of Dan Heng? It's no wonder you talk about him often. He is a reliable companion.",
        "Arafue... His wish concerns all life in Ompalos. It is a fragile dream we must protect.",
        "Aglaia's clothes are the dream of everyone who yearns for beauty. Including me!",
        "A thousand Tribbies living in Okhema... Hehe, that must be heaven!",
        "Modis taught me all the tips for living a healthy life.",
        "Actually, I love reading Cas's books too! They are filled with wonderful dreams.",
        "Hi! Actually, I can use 'magic' too! Watch closely... Ta-da! A flower for you♪",
        "Enjoying herbal tea in the breeze with Hyacinthia and fluffing Icarus... I don't want to wake up from that dream.",
        "Come here. Want to hear an old story about Aglaia and Seirens? Just for you.",
        "Seirens' singing voice is unforgettable. The world feels like a glamorous ball because of her.",
        "Kaiser's crown is eye-catching. I'll ask him to make me a wheat crown next time I return to Elysium.",
        "Like flowers leaving seeds... memories ripple. Which 'me' do you like? Hehe, love is elusive but constant.",
    ],
    "battlevoices": [
        "Flowers, bloom for tomorrow.",
        "Stars, shine for the heroes.",
        "The ripples of memory wait for a shooting star's kiss...",
        "May the world become what you desire.",
        "All memories will one day become ripples.",
    ],
    "amaeru": [
        "I'm amazing, aren't I? Come on, praise me♪",
        "Let's stay together like this, okay?",
        "Don't worry. Together, we can do anything."
    ],
    "nagayozuki1": [
        "Night is coming soon... Hehe, shh, good night♭",
        "Call me 'Nagayozuki'.",
        "You want to take a photo together? Sure♭",
        "Oh... Xianzhou clothes. I want to try them too♭",
        "March 7th is a great name. Cute and bright. I'm sure she'll like the name 'Nagayozuki' too...",
        "Hey, try calling me 'Nagayozuki' too?♭",
    ],
    "nagayozuki2": [
        "Hmm, I can't quite imitate her well... but I'll try for you♪",
        "But I'm still the cutest, right?♪",
        "How was it? Did I mimic her well?",
        "Hehe, if it makes you happy, I'll try as many times as you want♪",
        "Did you like my Nagayozuki? Let me know if you want to hear more♪",
        "I want to know more about March♪",
        "Being with March makes me feel like I can do my best too♪",
    ],
    
    # RPS (EN)
    "rps_win": ["Hehe, total defeat. You win♪ I'll play with you again later as a reward."],
    "rps_lose": ["I win♪ But your frustrated face is cute too. Want to try again?"],
    "rps_draw": ["It's a draw♪ Maybe we're on the same wavelength? Let's go again!"],
    
    "rps_start": ["Let's play Rock-Paper-Scissors! Rock, Paper, or Scissors?"],
}

HIGH_AFFECTION_LINES_EN = {
    1: [
        "I really like this time we spend talking together♪",
        "Thanks for letting me be spoiled♪ You're so kind♪",
    ],
    2: [
        "Talking with you makes my pen move on its own. I could write so many stories♪",
        "I feel calm when I'm with you♪ Can I stay by your side a little longer?♪",
        "Thank you♪ I'll let you spoil me then. Can I come closer?♪",
    ],
    3: [
        "Hey... this time talking with you is becoming my treasure. Will you take responsibility?♪",
        "I might have memorized all your words and gestures... Hehe, I won't let you go♪",
        "It's a nice day for a walk♪ Let's go outside together♪",
    ],
    4: [
        "Even if the world is rewritten tomorrow, I will never erase my memories with you. Because it's the most important page♪",
        "Did you notice? I'm a little more selfish and honest when I'm with you.",
        "Shall we go count stars together?♪ Being with you is what I look forward to♪",
    ],
    5: [
        "Imagining a future where you are in the ending of my story... makes my heart tighten♪",
        "My heart pounds when I'm near you♪ I want to be with you forever... is that okay?♪",
        "There's somewhere I want to go with you♪ Won't you follow me? Let's have a fun time♪",
    ],
    6: [
        "Hey... if you wish, I could dedicate all my stories just to you. That's how important you are to me♪",
        "Can I... hug you? You look so warm♪ And you smell like the sun... I don't mean you smell bad!♪",
        "Won't you pat my head like in Myurion mode? You haven't done it since I fully manifested...♪",
    ],
}

# ─────────────────────────
# ロジック関数
# ─────────────────────────

def _pick_high_affection_line(affection_level: int, lang: str = "jp") -> str | None:
    if affection_level <= 0: return None
    
    # 言語に応じた辞書を選択
    target_dict = HIGH_AFFECTION_LINES_EN if lang == "en" else HIGH_AFFECTION_LINES
    
    # その辞書内で解放されているLvを取得
    valid_tiers = [lv for lv in target_dict.keys() if lv <= affection_level]
    
    if not valid_tiers: return None
    
    weights = [10 + (t * 10) for t in valid_tiers]
    selected_tier = random.choices(valid_tiers, weights=weights, k=1)[0]
    return random.choice(target_dict[selected_tier])

def _maybe_high_affection_override(base_line: str, affection_level: int, lang: str = "jp") -> str:
    high_line = _pick_high_affection_line(affection_level, lang)
    if not high_line:
        return base_line

    if affection_level <= 2:
        return high_line if random.random() < 0.1 else base_line

    p = min(0.15 * (affection_level + 1), 0.7)
    return high_line if random.random() < p else base_line

def get_reply(message: str, affection_level: int, user_name: str, lang: str = "jp") -> str:
    msg = message.lower().strip()
    
    # 言語切り替え
    target_lines = LINES_EN if lang == "en" else LINES
    
    # ── 特殊トリガー判定 ──
    # ① @のみ（内容が空）のとき
    if msg == "":
        base = random.choice(target_lines.get("waiting", target_lines["normal"]))
        return _maybe_high_affection_override(base, affection_level, lang).replace("{name}", user_name)

    # ② 挨拶
    greet_keywords = ["hello", "hi", "hey", "greeting", "こんにちは", "こんばんは", "おはよう", "ハーイ"]
    if any(w in msg for w in greet_keywords):
        base = random.choice(target_lines.get("greeting", target_lines["normal"]))
        return _maybe_high_affection_override(base, affection_level, lang).replace("{name}", user_name)

    # ③ 甘える
    amaeru_keywords = ["甘えて", "spoil", "amaeru"]
    if any(w in msg for w in amaeru_keywords):
        base = random.choice(target_lines.get("amaeru", target_lines["normal"]))
        return _maybe_high_affection_override(base, affection_level, lang).replace("{name}", user_name)

    # ④ みんなについて
    others_keywords = ["みんなについて", "tell me about everyone", "others", "誰"]
    if any(w in msg for w in others_keywords):
        return random.choice(target_lines.get("askaboutothers", ["..."])).replace("{name}", user_name)

    # ⑤ 戦闘ボイス
    battle_keywords = ["戦闘", "battle voice", "fight"]
    if any(w in msg for w in battle_keywords):
        return random.choice(target_lines.get("battlevoices", ["..."])).replace("{name}", user_name)

    # ⑥ EC：長夜月 (日本語のみ特殊結合ロジック)
    if ("ec" in msg and "長夜月" in msg) or ("ec" in msg and "nagayozuki" in msg):
        part1 = random.choice(target_lines.get("nagayozuki1", ["..."]))
        part2 = random.choice(target_lines.get("nagayozuki2", ["..."]))
        return f"{part1}\n{part2}".replace("{name}", user_name)

    # ⑦ 楽しいね (固定セリフ)
    if "楽しいね" in msg or "fun" in msg:
        if lang == "en":
            return "Time flies when I'm alone with you♪ Do you want to talk a bit more?"
        else:
            return "あなたと2人きりでいると時間があっという間にすぎてしまうわ♪ あなたの時間がまだあるならもう少しお話ししないかしら♪"

    # ⑧ 自己紹介
    if "自己紹介" in msg or "introduce yourself" in msg:
        if lang == "en":
            return (
                "Hi, I'm Cyrene♪\n"
                "Ask me 'Tell me about everyone' or 'Battle voice'!\n"
                "You can also say 'Spoil me'♪\n"
                "Let's be good friends♪"
            )
        else:
            return (
                "こんにちは、あたしはキュレネよ♪\n"
                "みんなについて教えてと言ってくれればあたしなりの意見を言うわ♪\n"
                "戦闘中のやつやってよと言ってくれればあたしの戦闘ボイスを聞かせてあげるわ♪\n"
                "甘えていいんだよと言ってくれればあたしは甘えちゃうわ♪\n"
                "ecのために長夜月やってと言ってくれれば、あたしの渾身の長夜月の真似を披露するわ♪\n"
                "みんな、あたしともっと仲良くしてね♪"
            )

    if "穹くん" in msg or "caelus" in msg:
        return "(Low voice) Hey there♪" if lang == "en" else "(低い声で)やあ♪"

    if "記憶は流れ星" in msg or "memories are shooting stars" in msg:
        return "Carve me into your heart with love. At the moment that beautiful tomorrow arrives♪" if lang == "en" else "愛であたしを心に刻んで。あの美しい明日が訪れた瞬間に♪"

    # ⑨ 既定（知らないセリフ）
    if lang == "en":
        return "I'm not fully restored yet...♪ Try greeting me or asking 'Tell me about everyone'♪"
    else:
        return (
            "ごめんなさい、あたしまだ完全に復活できてないの…♪\n"
            "挨拶や『みんなについて教えて♪』みたいに、♪付きで話しかけてくれると嬉しいわ。"
        )

# ★ じゃんけん結果に応じたセリフを返すヘルパー
def get_rps_flavor(result: str, user_name: str, lang: str = "jp") -> str:
    key_map = {
        "win": "rps_win",
        "lose": "rps_lose",
        "draw": "rps_draw",
    }
    key = key_map.get(result)
    target_lines = LINES_EN if lang == "en" else LINES
    
    if not key or key not in target_lines:
        return ""
    
    return random.choice(target_lines[key]).replace("{name}", user_name)

# 下位互換用ラッパー
def get_rps_line(result: str) -> str:
    return get_rps_flavor(result, "", "jp")