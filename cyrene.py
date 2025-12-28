import os
import re
import random
import discord
from config import DISCORD_TOKEN, PRIMARY_ADMIN_ID
import database as db
import logic
import reply_system as rs
from lines import ARAFUE_TRIGGER_LINE
from forms import get_user_form, set_user_form, resolve_form_code, get_form_display_name, get_all_forms
from special_unlocks import inc_janken_win, get_janken_wins, is_nanoka_unlocked, set_nanoka_unlocked, has_danheng_stage1, mark_danheng_stage1, is_danheng_unlocked, set_danheng_unlocked

# --- Discord Setup ---
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

# --- State ---
waiting_for_nickname = set()
waiting_for_rename = set()
admin_data_mode = set()
waiting_for_admin_add = set()
waiting_for_admin_remove = set()
waiting_for_rps_choice = set()
waiting_for_guardian_level = {}
waiting_for_msg_limit = {}
waiting_for_bypass_edit = set()
waiting_for_transform_code = set()
FORCE_RPS_WIN_NEXT = set()
MYURION_QUIZ_STATE = {}

# --- Help Messages ---
ADMIN_COMMANDS_LIST = (
    "【データ管理モードよ♪】\n"
    "このモードでは以下のコマンドが使えるわ。\n\n"
    "- `!mode auto` / `!mode mention`: 反応モードの切替（自動/メンションのみ）\n"
    "- `ニックネーム確認`: みんなのあだ名を確認するわ\n"
    "- `管理者編集`: 管理者の追加や削除ができるの\n"
    "- `親衛隊レベル編集`: レベルの設定や削除ね\n"
    "- `好感度編集`: レベルの上がりやすさを調整できるわ\n"
    "- `好感度一覧`: みんなの愛の深さを確認しましょ♪\n"
    "- `メッセージ制限編集`: お話しできる回数の制限設定よ\n"
    "- `変身管理`: 誰がどの姿か確認したり、変身させたりできるわ\n"
    "- `データ管理終了`: 管理モードを終わるわね\n\n"
    "**★ メイン管理者限定 ★**\n"
    "- `好感度XP追加 @ユーザー 数値`\n"
    "- `じゃんけん勝利数追加 @ユーザー 数値`\n"
    "- `メッセージ制限bypass編集`\n"
    "- `変身解放状況確認`"
)

GENERAL_COMMANDS_LIST_JP = (
    "【あたしとできること一覧よ♪】\n\n"
    "**★ お話ししましょう♪**\n"
    "- `!mode auto`: メンションなしでもお話しするようになるわ\n"
    "- `!mode mention`: メンションした時だけお話しするわ\n"
    "- `!lang en`: 英語モードに切り替えるわ\n"
    "- `こんにちは` / `おやすみ`: 挨拶は大事よね♪\n"
    "- `みんなについて教えて`: 他の人のこと、こっそり教えるわ\n"
    "- `甘えていいんだよ`: …ふふっ、遠慮なく甘えちゃうかも？\n"
    "- `じゃんけん`: あたしに勝てるかしら？\n"
    "- `あだ名登録 [名前]`: あなただけの呼び方を教えて？\n"
    "- `好感度`: わたしたちの仲良し度、チェックしましょ♪\n"
    "- `親衛隊レベル`: あなたのレベル、教えてあげる\n\n"
    "**★ 別の姿へ…**\n"
    "- `変身`: 別の姿に変身するためのコードを教えて？\n"
    "- `変身状態` / `今の姿`: 今のあたしが誰かわかる？\n"
    "- `[特定の合言葉]`: 隠されたヒントで、新しい姿になれるかも…？\n\n"
    "**★ ガチャ**\n"
    "- `ガチャメニュー`: 石やチケットの確認よ\n"
    "- `単発ガチャ` / `10連ガチャ`: 運試し、してみない？\n"
    "- `デイリー受け取り`: 1日1回、石をプレゼントするわ♪\n\n"
    "**★ その他**\n"
    "- `ミュリオンモードオン`: ミュミュ語でお話しするわ～！\n"
    "- `コマンドを教えて`: このリストを見せるわ"
)

GENERAL_COMMANDS_LIST_EN = (
    "【Available Commands】\n\n"
    "**★ Talk with me**\n"
    "- `!mode auto`: I will reply without mentions\n"
    "- `!mode mention`: I will only reply to mentions\n"
    "- `!lang jp`: Switch to Japanese mode\n"
    "- `Hello` / `Good night`: Greetings are important♪\n"
    "- `Tell me about everyone`: I'll tell you about my friends\n"
    "- `RPS` / `Rock Paper Scissors`: Let's play a game!\n"
    "- `Set nickname [name]`: Tell me what to call you\n"
    "- `Affection`: Check our bond level\n"
    "- `Guardian`: Check your Guardian level\n\n"
    "**★ Transformation**\n"
    "- `Transform`: Tell me a code to change my form\n"
    "- `Current form`: Who am I right now?\n\n"
    "**★ Gacha**\n"
    "- `Gacha`: Check gems and tickets\n"
    "- `Pull 1` / `Pull 10`: Try your luck?\n"
    "- `Daily`: Get your daily gems♪"
)

async def send_myu(message, user_id, text):
    await message.channel.send(logic.apply_myurion_filter(user_id, text))

@client.event
async def on_ready():
    print(f"Login: {client.user}")

@client.event
async def on_message(message):
    if message.author.bot: return
    user_id = message.author.id
    content = message.content.strip() # 原文
    content_lower = content.lower()
    
    # メンション除去後のテキスト
    content_body = re.sub(rf"<@!?{client.user.id}>", "", content).strip()
    content_body_lower = content_body.lower()

    is_main_admin = (user_id == PRIMARY_ADMIN_ID)
    nickname = db.get_nickname(user_id)
    name = nickname if nickname else message.author.display_name
    current_form = get_user_form(user_id)
    lang = db.get_user_lang(user_id) # 現在の言語
    
    # --- モード/言語切替コマンド (最優先・メンション不要) ---
    if content_lower == "!mode auto":
        db.set_reply_mode(user_id, "auto")
        msg = f"Got it! I'll reply even without mentions now, {name}!" if lang=="en" else f"了解です♪ これからはメンションなしでもお話しますね、{name}さん！"
        await message.channel.send(msg)
        return
    if content_lower == "!mode mention":
        db.set_reply_mode(user_id, "mention")
        msg = f"Okay. I'll only reply when you mention me." if lang=="en" else f"わかりました。これからは呼んでくれた時（メンション）だけお返事しますね。"
        await message.channel.send(msg)
        return
    if content_lower == "!lang en":
        db.set_user_lang(user_id, "en")
        await message.channel.send(f"Okay, {name}! I'll speak in English from now on♪")
        return
    if content_lower == "!lang jp":
        db.set_user_lang(user_id, "jp")
        await message.channel.send(f"わかりました、{name}さん！これからは日本語でお話ししますね♪")
        return

    # 状態チェック
    is_active_mode = (
        user_id in waiting_for_nickname or user_id in waiting_for_rename or
        user_id in waiting_for_admin_add or user_id in waiting_for_admin_remove or
        user_id in waiting_for_rps_choice or user_id in admin_data_mode or
        user_id in waiting_for_guardian_level or user_id in waiting_for_msg_limit or
        user_id in waiting_for_bypass_edit or user_id in waiting_for_transform_code or
        user_id in MYURION_QUIZ_STATE
    )
    
    # キーワードトリガー (EN/JP対応)
    CMD_KEYWORDS = ["コマンド", "ヘルプ", "command", "help"]
    RPS_KEYWORDS = ["じゃんけん", "rps", "rock paper scissors"]
    TRANS_KEYWORDS = ["変身", "transform"]
    GACHA_KEYWORDS = ["ガチャ", "gacha"]
    DAILY_KEYWORDS = ["デイリー", "daily"]
    NICK_KEYWORDS = ["あだ名", "nickname"]
    MYU_KEYWORDS = ["ミュリオン", "myurion"]
    AFF_KEYWORDS = ["好感度", "affection"]
    
    is_command_query = any(k in content_body_lower for k in CMD_KEYWORDS)
    is_keyword_trigger = any(k in content_body_lower for k in (
        RPS_KEYWORDS + TRANS_KEYWORDS + GACHA_KEYWORDS + DAILY_KEYWORDS + 
        NICK_KEYWORDS + MYU_KEYWORDS + AFF_KEYWORDS + 
        ["親衛隊レベル", "guardian", "skopeo", "skepeo", "今の姿", "current form", "記憶は流れ星"]
    ))
    
    # 返信判定
    is_mentioned = client.user in message.mentions
    reply_mode = db.get_reply_mode(user_id)
    is_auto_reply = (reply_mode == "auto")
    
    should_reply = (is_mentioned or is_active_mode or is_auto_reply)
    if not should_reply: return

    # 空メッセージ判定（メンションがあれば空でも通す）
    if not content_body and not message.attachments and not is_active_mode and not is_mentioned:
        return
    
    # --- コマンド一覧表示 ---
    if is_command_query:
        if user_id in admin_data_mode:
            await send_myu(message, user_id, ADMIN_COMMANDS_LIST)
        else:
            list_text = GENERAL_COMMANDS_LIST_EN if lang == "en" else GENERAL_COMMANDS_LIST_JP
            await send_myu(message, user_id, f"{message.author.mention} {list_text}")
        return

    # --- ミュリオン設定 ---
    if content_body == "全体ミュリオンモード" and db.is_admin(user_id):
        db.set_all_myurion_enabled(True)
        await message.channel.send(f"{message.author.mention} 全員ミュリオンモードON！ ミュミュ〜♪")
        return
    if content_body == "全体ミュリオン解除" and db.is_admin(user_id):
        db.set_all_myurion_enabled(False)
        await message.channel.send(f"{message.author.mention} 全員ミュリオンモード解除。普通の言葉に戻るわね。")
        return

    # --- ミュリオンクイズ (既存ロジック・日本語のみ) ---
    if user_id in MYURION_QUIZ_STATE:
        ans = logic.parse_myurion_answer(content_body)
        if not ans:
            await send_myu(message, user_id, f"{message.author.mention} 1〜4で答えてほしいミュ。")
            return
        state = MYURION_QUIZ_STATE[user_id]
        if ans - 1 == state["correct_index"]:
            total = db.add_myurion_correct(user_id)
            if total >= 3 and not db.is_myurion_unlocked(user_id):
                st = db.get_myurion_state(user_id)
                st["unlocked"], st["enabled"] = True, True
                db.save_myurion_state(user_id, st)
                MYURION_QUIZ_STATE.pop(user_id, None)
                await send_myu(message, user_id, f"{message.author.mention} 3問正解ミュ！ おめでとう、ミュリオンモード解放ミュ～♪")
            else:
                MYURION_QUIZ_STATE.pop(user_id, None)
                await send_myu(message, user_id, f"{message.author.mention} 正解ミュ！ やるわね♪ (現在{total}/3)")
        else:
            MYURION_QUIZ_STATE.pop(user_id, None)
            await send_myu(message, user_id, f"{message.author.mention} 残念、ハズレミュ…。また挑戦してね。")
        return

    if "ミュウ、ミュミュミュウミュウ、ミュイー" in content_body:
        st = db.get_myurion_state(user_id)
        if st.get("unlocked"):
            st["enabled"] = True
            db.save_myurion_state(user_id, st)
            await send_myu(message, user_id, f"{message.author.mention} もう解放されているわよ♪ ミュリオンモードONミュ！")
        else:
            await logic.send_myurion_question(message, user_id, st.get("quiz_correct", 0), MYURION_QUIZ_STATE)
        return

    if any(k in content_body_lower for k in ["ミュリオンモードオン", "myurion on"]):
        st = db.get_myurion_state(user_id)
        if st.get("unlocked"):
            st["enabled"] = True
            db.save_myurion_state(user_id, st)
            await send_myu(message, user_id, "Myurion Mode ON Myu!" if lang=="en" else "ミュリオンモードONミュ！ いっぱいお話ししよミュ♪")
        else:
            await send_myu(message, user_id, "Locked..." if lang=="en" else "まだその扉は開いてないみたい…。クイズに挑戦してみて？")
        return
    
    if any(k in content_body_lower for k in ["ミュリオンモードオフ", "myurion off"]):
        st = db.get_myurion_state(user_id)
        st["enabled"] = False
        db.save_myurion_state(user_id, st)
        await message.channel.send("Back to normal language." if lang=="en" else "わかったわ、通常言語に戻るわね。")
        return

    # --- 丹恒解放コード ---
    if "skopeo365" in re.sub(r"\s+", "", content_body).lower():
        if has_danheng_stage1(user_id) and not is_danheng_unlocked(user_id):
            set_danheng_unlocked(user_id, True)
            await send_myu(message, user_id, "Danheng's memory awakened..." if lang=="en" else "丹恒の記憶が…蘇ったみたい♪")
        elif is_danheng_unlocked(user_id):
            await send_myu(message, user_id, "Already unlocked." if lang=="en" else "ふふっ、その姿ならもう解放されているわよ♪")
        else:
            await send_myu(message, user_id, "Something is missing..." if lang=="en" else "ん〜…まだ何かが足りないみたいね。")
        waiting_for_transform_code.discard(user_id)
        return

    # --- 変身コード待ち ---
    if user_id in waiting_for_transform_code:
        t_text = content_body
        waiting_for_transform_code.discard(user_id)
        
        # 特殊変身
        if "なのになってみて" in t_text:
            if is_nanoka_unlocked(user_id):
                set_user_form(user_id, "nanoka")
                await send_myu(message, user_id, "Transformed into March 7th!" if lang=="en" else "今日から三月なのか/長夜月の姿になるわ♪")
            else:
                await send_myu(message, user_id, "Locked." if lang=="en" else "まだ条件が足りないみたい…。")
            return
        if "たんたんになってみて" in t_text:
            if is_danheng_unlocked(user_id):
                set_user_form(user_id, "danheng")
                await send_myu(message, user_id, "Transformed into Dan Heng." if lang=="en" else "…わかった。丹恒の姿になろう。")
            else:
                await send_myu(message, user_id, "Locked." if lang=="en" else "鍵が足りないみたい。")
            return
        
        fk = resolve_form_code(t_text)
        if fk:
            set_user_form(user_id, fk)
            dname = get_form_display_name(fk)
            msg = f"Transformed into **{dname}**!" if lang=="en" else f"**{dname}** に変身したわ♪ どう？似合う？"
            await send_myu(message, user_id, msg)
        else:
            msg = "Unknown code. Try again?" if lang=="en" else "そのコードは知らないみたい…。もう一度確認してくれる？"
            await send_myu(message, user_id, msg)
        return

    # --- データ管理モード ---
    if user_id in admin_data_mode:
        
        if content_body == "データ管理終了":
            admin_data_mode.discard(user_id)
            await send_myu(message, user_id, "データ管理モード、終了ね。また必要になったら呼んでちょうだい♪")
            return

        if content_body == "ニックネーム確認":
            nicks = db.load_nicknames()
            if not nicks:
                await send_myu(message, user_id, "まだ誰もあだ名を登録してないみたい。")
            else:
                lines = ["【登録済みニックネーム】"]
                for uid, n in nicks.items():
                    lines.append(f"<@{uid}>: {n}")
                await send_myu(message, user_id, "\n".join(lines))
            return
        
        if content_body == "管理者編集":
            await send_myu(message, user_id, "管理者を「追加」する？「削除」する？\n`追加` または `削除` と入力してね。")
            return
        
        if content_body == "追加":
            admin_data_mode.discard(user_id)
            waiting_for_admin_add.add(user_id)
            await send_myu(message, user_id, "誰を管理者に追加する？ メンションして教えてちょうだい。")
            return

        if content_body == "削除":
            admin_data_mode.discard(user_id)
            waiting_for_admin_remove.add(user_id)
            await send_myu(message, user_id, "誰を管理者から外す？ メンションして教えてちょうだい。")
            return

        if content_body == "親衛隊レベル編集":
            admin_data_mode.discard(user_id)
            waiting_for_guardian_level[user_id] = {"step": "mention"}
            await send_myu(message, user_id, "親衛隊レベルを設定する人をメンションしてね。")
            return

        if content_body == "メッセージ制限編集":
            admin_data_mode.discard(user_id)
            waiting_for_msg_limit[user_id] = {"step": "mention"}
            await send_myu(message, user_id, "メッセージ制限を設定する人をメンションしてね。")
            return

        # ★メイン管理者限定: Bypass編集
        if content_body == "メッセージ制限bypass編集":
            if not is_main_admin:
                await send_myu(message, user_id, "ごめんなさい、それはメイン管理者だけの権限よ。")
                return
            admin_data_mode.discard(user_id)
            waiting_for_bypass_edit.add(user_id)
            await send_myu(message, user_id, "制限無視(bypass)リストに「追加」する？「削除」する？\n`追加` か `削除` で答えて。")
            return

        # ★メイン管理者限定: 好感度XP直接追加
        if content_body.startswith("好感度XP追加"):
            if not is_main_admin:
                await send_myu(message, user_id, "ごめんなさい、それはメイン管理者だけの権限よ。")
                return
            m = re.search(r"好感度XP追加\s+<@!?(\d+)>\s+(\d+)", content_body)
            if m:
                tid, val = int(m.group(1)), int(m.group(2))
                logic.add_affection_xp(tid, val)
                await send_myu(message, user_id, f"<@{tid}> に {val} XPを追加したわ♪")
            else:
                await send_myu(message, user_id, "書式が違うみたい。`好感度XP追加 @ユーザー 100` のように書いてね。")
            return

        # ★メイン管理者限定: じゃんけん勝利数追加
        if content_body.startswith("じゃんけん勝利数追加"):
            if not is_main_admin:
                await send_myu(message, user_id, "ごめんなさい、それはメイン管理者だけの権限よ。")
                return
            m = re.search(r"じゃんけん勝利数追加\s+<@!?(\d+)>\s+(\d+)", content_body)
            if m:
                tid, val = int(m.group(1)), int(m.group(2))
                current = get_janken_wins(tid)
                db.set_janken_wins_direct(tid, current + val)
                await send_myu(message, user_id, f"<@{tid}> の勝利数を {val} 増やしたわ。")
            else:
                await send_myu(message, user_id, "書式が違うみたい。`じゃんけん勝利数追加 @ユーザー 10` のように書いてね。")
            return

        # ★メイン管理者限定: 変身解放状況確認
        if content_body == "変身解放状況確認":
            if not is_main_admin:
                await send_myu(message, user_id, "ごめんなさい、それはメイン管理者だけの権限よ。")
                return
            status_list = db.get_all_special_status()
            if not status_list:
                await send_myu(message, user_id, "まだ特別な解放をしている人はいないみたい。")
            else:
                msg = "\n".join(status_list)
                await send_myu(message, user_id, f"【現在の解放状況】\n{msg}")
            return

        if content_body == "好感度一覧":
            text = logic.format_all_affection_status(message.guild)
            await send_myu(message, user_id, text)
            return

        if content_body == "変身管理":
            forms_data = get_all_forms()
            lines = ["【現在の変身状態】"]
            for uid, key in forms_data.items():
                dname = get_form_display_name(key)
                lines.append(f"<@{uid}>: {dname} ({key})")
            await send_myu(message, user_id, "\n".join(lines))
            return

        # デフォルト案内
        await send_myu(message, user_id, f"{ADMIN_COMMANDS_LIST}\n\nコマンドを待ってるわ。何をすればいいかしら？♪")
        return
    
    # --- Bypass編集待ち ---
    if user_id in waiting_for_bypass_edit:
        if content_body == "中止":
            waiting_for_bypass_edit.discard(user_id)
            admin_data_mode.add(user_id)
            await send_myu(message, user_id, "中止したわ。")
            return

        m = re.match(r"(追加|削除)\s+<@!?(\d+)>", content_body)
        if m:
            action, tid = m.group(1), int(m.group(2))
            if action == "追加":
                db.add_bypass_user(tid)
                await send_myu(message, user_id, f"<@{tid}> をBypassリストに追加したわ。")
            else:
                db.remove_bypass_user(tid)
                await send_myu(message, user_id, f"<@{tid}> をBypassリストから削除したわ。")
            
            waiting_for_bypass_edit.discard(user_id)
            admin_data_mode.add(user_id)
        else:
            await send_myu(message, user_id, "書式が違うみたい。\n`追加 @ユーザー` または `削除 @ユーザー` と入力してね。")
        return

    # --- 管理者追加待ち処理 ---
    if user_id in waiting_for_admin_add:
        if message.mentions:
            target = message.mentions[0]
            db.add_admin(target.id)
            waiting_for_admin_add.discard(user_id)
            admin_data_mode.add(user_id) # モードに戻る
            await send_myu(message, user_id, f"{target.mention} を管理者に追加したわ。\nデータ管理モードに戻るわね。")
        else:
            await send_myu(message, user_id, "ユーザーをメンションしてね。（中止なら `中止` と言って）")
            if content_body == "中止":
                waiting_for_admin_add.discard(user_id)
                admin_data_mode.add(user_id)
        return

    # --- 管理者削除待ち処理 ---
    if user_id in waiting_for_admin_remove:
        if message.mentions:
            target = message.mentions[0]
            if db.remove_admin(target.id):
                await send_myu(message, user_id, f"{target.mention} を管理者から外したわ。")
            else:
                await send_myu(message, user_id, "その人は管理者じゃないか、削除できない人みたい。")
            waiting_for_admin_remove.discard(user_id)
            admin_data_mode.add(user_id)
        else:
            await send_myu(message, user_id, "ユーザーをメンションしてね。（中止なら `中止` と言って）")
            if content_body == "中止":
                waiting_for_admin_remove.discard(user_id)
                admin_data_mode.add(user_id)
        return

    # --- 親衛隊レベル設定待ち処理 ---
    if user_id in waiting_for_guardian_level:
        step_data = waiting_for_guardian_level[user_id]
        if step_data["step"] == "mention":
            if message.mentions:
                step_data["target_id"] = message.mentions[0].id
                step_data["step"] = "level"
                await send_myu(message, user_id, "設定するレベルを数値で教えて。（削除なら 0）")
            elif content_body == "中止":
                del waiting_for_guardian_level[user_id]
                admin_data_mode.add(user_id)
            else:
                await send_myu(message, user_id, "ユーザーをメンションしてね。")
        elif step_data["step"] == "level":
            try:
                lv = int(content_body)
                tid = step_data["target_id"]
                if lv <= 0:
                    db.delete_guardian_level(tid)
                    await send_myu(message, user_id, f"<@{tid}> の親衛隊レベルを削除したわ。")
                else:
                    db.set_guardian_level(tid, lv)
                    await send_myu(message, user_id, f"<@{tid}> を親衛隊レベル {lv} に設定したわ。")
                del waiting_for_guardian_level[user_id]
                admin_data_mode.add(user_id)
            except ValueError:
                await send_myu(message, user_id, "数値を入力してね。")
        return

    # --- メッセージ制限設定待ち処理 ---
    if user_id in waiting_for_msg_limit:
        step_data = waiting_for_msg_limit[user_id]
        if step_data["step"] == "mention":
            if message.mentions:
                step_data["target_id"] = message.mentions[0].id
                step_data["step"] = "limit"
                await send_myu(message, user_id, "1日のメッセージ制限回数を数値で教えて。（制限解除なら 0）")
            elif content_body == "中止":
                del waiting_for_msg_limit[user_id]
                admin_data_mode.add(user_id)
            else:
                await send_myu(message, user_id, "ユーザーをメンションしてね。")
        elif step_data["step"] == "limit":
            try:
                lim = int(content_body)
                tid = step_data["target_id"]
                if lim <= 0:
                    db.delete_message_limit(tid)
                    await send_myu(message, user_id, f"<@{tid}> の制限を解除したわ。")
                else:
                    db.set_message_limit(tid, lim)
                    await send_myu(message, user_id, f"<@{tid}> の制限を {lim} 回に設定したわ。")
                del waiting_for_msg_limit[user_id]
                admin_data_mode.add(user_id)
            except ValueError:
                await send_myu(message, user_id, "数値を入力してね。")
        return

    # --- データ管理モード開始コマンド ---
    if content_body == "データ管理" and db.is_admin(user_id):
        admin_data_mode.add(user_id)
        await send_myu(message, user_id, f"データ管理モードに入ったわ。\n{ADMIN_COMMANDS_LIST}")
        return

    # --- あだ名系 (EN/JP) ---
    if any(content_body_lower.startswith(k) for k in ["あだ名登録", "set nickname"]):
        # "あだ名登録" または "set nickname" を削除
        new = re.sub(r"^(あだ名登録|set nickname)\s*", "", content_body, flags=re.IGNORECASE).strip()
        if not new:
            waiting_for_nickname.add(user_id)
            await send_myu(message, user_id, rs.get_nickname_message_for_form(current_form, "ask", name, user_id))
        else:
            db.set_nickname(user_id, new)
            await send_myu(message, user_id, rs.get_nickname_message_for_form(current_form, "confirm", new, user_id))
        return

    if user_id in waiting_for_nickname:
        if content_body:
            db.set_nickname(user_id, content_body)
            waiting_for_nickname.discard(user_id)
            await send_myu(message, user_id, rs.get_nickname_message_for_form(current_form, "confirm", content_body, user_id))
        else:
            msg = "I couldn't hear you." if lang=="en" else "聞こえなかったわ、もう一度教えてくれる？"
            await send_myu(message, user_id, msg)
        return

    # --- ガチャ (EN/JP) ---
    if any(k in content_body_lower for k in GACHA_KEYWORDS):
        if any(k in content_body_lower for k in ["単発", "pull 1"]) and "10" not in content_body_lower:
            ok, res = logic.perform_gacha_pulls(user_id, 1)
            await send_myu(message, user_id, res)
        elif any(k in content_body_lower for k in ["10連", "pull 10"]):
            use_ticket = "ticket" in content_body_lower or "チケット" in content_body_lower
            ok, res = logic.perform_gacha_pulls(user_id, 10, use_ticket)
            await send_myu(message, user_id, res)
        else:
            await send_myu(message, user_id, logic.format_gacha_status(user_id)) 
        return

    if any(k in content_body_lower for k in DAILY_KEYWORDS):
        ok, stones, reason = logic.grant_daily_stones(user_id)
        await send_myu(message, user_id, f"{reason}\nStones: {stones}" if lang=="en" else f"{reason}\n所持石: {stones}")
        return

    # --- 変身開始 ---
    if any(k in content_body_lower for k in TRANS_KEYWORDS) and "state" not in content_body_lower and "状態" not in content_body_lower:
        waiting_for_transform_code.add(user_id)
        msg = "Tell me the transformation code." if lang=="en" else "ふふっ、別の姿になりたいの？ 変身コードを教えてくれるかしら♪"
        await send_myu(message, user_id, msg)
        return

    # --- じゃんけん (EN/JP) ---
    is_rps_msg = any(k in content_body_lower for k in RPS_KEYWORDS)
    if is_rps_msg or user_id in waiting_for_rps_choice:
        hand = logic.parse_hand(content_body)
        
        if not hand and is_rps_msg:
            waiting_for_rps_choice.add(user_id)
            prompt = rs.get_rps_prompt_for_form(current_form, name, user_id)
            await send_myu(message, user_id, prompt)
            return
        
        if hand:
            force = user_id in FORCE_RPS_WIN_NEXT
            bot_hand = logic.get_bot_hand(hand, force)
            res = "win" if force else logic.judge_janken(hand, bot_hand)
            if force: FORCE_RPS_WIN_NEXT.discard(user_id)
            
            wins = inc_janken_win(user_id) if res == "win" else get_janken_wins(user_id)
            
            result_msg = rs.format_rps_result(current_form, name, hand, bot_hand, rs.get_rps_flavor(current_form, res, name, user_id), wins, user_id)
            
            await send_myu(message, user_id, result_msg)
            
            xp_map = {"win": 10, "lose": 5, "draw": 7}
            logic.add_affection_xp(user_id, xp_map.get(res, 0))
            waiting_for_rps_choice.discard(user_id)
            return

    # --- 親衛隊レベル確認 ---
    if any(k in content_body_lower for k in ["親衛隊レベル", "guardian"]):
        lv = db.get_guardian_level(user_id)
        if lang == "en":
            msg = f"Your Guardian Level is Lv.{lv}." if lv else "No Guardian Level registered."
        else:
            msg = f"あなたの親衛隊レベルは Lv.{lv} よ♪" if lv else "まだ親衛隊レベルは登録されてないみたいね。"
        await send_myu(message, user_id, msg)
        return

    # --- 好感度チェック ---
    if any(k in content_body_lower for k in AFF_KEYWORDS):
        msg = logic.get_affection_status_message(user_id)
        await send_myu(message, user_id, f"{message.author.mention} {msg}")
        return

    # --- 変身状態確認 ---
    if any(k in content_body_lower for k in ["変身状態", "今の姿", "current form"]):
        fname = get_form_display_name(current_form)
        msg = f"I am currently **{fname}**." if lang=="en" else f"今のあたしは **{fname}** よ♪"
        await send_myu(message, user_id, f"{message.author.mention} {msg}")
        return

    # --- 通常会話 ---
    xp, lv = logic.get_user_affection(user_id)
    reply = rs.generate_reply_for_form(current_form, content_body, lv, user_id, name)
    
    if current_form == "cyrene" and ARAFUE_TRIGGER_LINE in reply:
        mark_danheng_stage1(user_id)
    
    if "記憶は流れ星を待ってる" in content_body and get_janken_wins(user_id) >= 307 and not is_nanoka_unlocked(user_id):
        set_nanoka_unlocked(user_id, True)
        reply += "\n\n【三月なのか 解放！】『なのになってみて』と言ってみて？"

    await send_myu(message, user_id, f"{message.author.mention} {reply}")
    logic.add_affection_xp(user_id, 3)

client.run(DISCORD_TOKEN)