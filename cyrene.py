# cyrene.py
import os
import re
import random
import discord
from config import DISCORD_TOKEN, PRIMARY_ADMIN_ID
import database as db
import logic
import reply_system as rs
from lines import ARAFUE_TRIGGER_LINE
from forms import get_user_form, set_user_form, resolve_form_code, get_form_display_name
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
waiting_for_transform_code = set()
FORCE_RPS_WIN_NEXT = set()
MYURION_QUIZ_STATE = {}

# --- Help Messages (柔らかい口調に修正) ---
ADMIN_COMMANDS_LIST = (
    "【データ管理モードよ♪】\n"
    "このモードでは以下のコマンドが使えるわ。\n\n"
    "- `ニックネーム確認`: みんなのあだ名を確認するわ\n"
    "- `管理者編集`: 管理者の追加や削除ができるの\n"
    "- `親衛隊レベル編集`: レベルの設定や削除ね\n"
    "- `好感度編集`: レベルの上がりやすさを調整できるわ\n"
    "- `好感度XP追加 @ユーザー 数値`: 経験値を直接あげちゃう？\n"
    "- `好感度一覧`: みんなの愛の深さを確認しましょ♪\n"
    "- `じゃんけん勝利数追加 @ユーザー 数値`: 勝ち数を操作しちゃうの？\n"
    "- `メッセージ制限編集`: お話しできる回数の制限設定よ\n"
    "- `メッセージ制限bypass編集`: 制限を無視できる人を決めるわ（メイン管理者のみ）\n"
    "- `変身管理`: 誰がどの姿か確認したり、変身させたりできるわ\n"
    "- `変身解放状況確認`: 特別な姿の解放状況をチェック（メイン管理者のみ）\n"
    "- `データ管理終了`: 管理モードを終わるわね"
)

GENERAL_COMMANDS_LIST = (
    "【あたしとできること一覧よ♪】\n\n"
    "**★ お話ししましょう♪**\n"
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
    
    # 状態チェック
    is_active_mode = (
        user_id in waiting_for_nickname or user_id in waiting_for_rename or
        user_id in waiting_for_admin_add or user_id in waiting_for_admin_remove or
        user_id in waiting_for_rps_choice or user_id in admin_data_mode or
        user_id in waiting_for_guardian_level or user_id in waiting_for_msg_limit or
        user_id in waiting_for_transform_code or user_id in MYURION_QUIZ_STATE
    )
    
    # コマンド確認キーワード
    is_command_query = content in ["コマンド", "コマンド教えて", "コマンドを教えて", "ヘルプ"]

    # キーワードトリガー
    KEYWORD_TRIGGERS = [
        "じゃんけん", "変身", "ガチャ", "デイリー", "あだ名", "ミュリオン", 
        "親衛隊レベル", "好感度", "skopeo", "skepeo", "今の姿", "今のフォーム",
        "記憶は流れ星"
    ]
    is_keyword_trigger = any(k in content for k in KEYWORD_TRIGGERS)
    
    # 処理開始判定
    if not (client.user in message.mentions or is_active_mode or is_command_query or is_keyword_trigger):
        return

    # メンション除去後のテキスト
    content_body = re.sub(rf"<@!?{client.user.id}>", "", content).strip()
    nickname = db.get_nickname(user_id)
    name = nickname if nickname else message.author.display_name
    current_form = get_user_form(user_id)
    
    # --- コマンド一覧表示 ---
    if is_command_query:
        if user_id in admin_data_mode:
            await send_myu(message, user_id, ADMIN_COMMANDS_LIST)
        else:
            await send_myu(message, user_id, f"{message.author.mention} {GENERAL_COMMANDS_LIST}")
        return

    # --- 管理者コマンド（全体設定） ---
    if content_body == "全体ミュリオンモード" and db.is_admin(user_id):
        db.set_all_myurion_enabled(True)
        await message.channel.send(f"{message.author.mention} 全員ミュリオンモードON！ ミュミュ〜♪")
        return
    if content_body == "全体ミュリオン解除" and db.is_admin(user_id):
        db.set_all_myurion_enabled(False)
        await message.channel.send(f"{message.author.mention} 全員ミュリオンモード解除。普通の言葉に戻るわね。")
        return

    # --- ミュリオンクイズ ---
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
            await send_myu(message, user_id, f"{message.author.mention} もう解放されてるわよ♪ ミュリオンモードONミュ！")
        else:
            await logic.send_myurion_question(message, user_id, st.get("quiz_correct", 0), MYURION_QUIZ_STATE)
        return

    if content_body in ["ミュリオンモードオン", "ミュリオンオン"]:
        st = db.get_myurion_state(user_id)
        if st.get("unlocked"):
            st["enabled"] = True
            db.save_myurion_state(user_id, st)
            await send_myu(message, user_id, "ミュリオンモードONミュ！ いっぱいお話ししよミュ♪")
        else:
            await send_myu(message, user_id, "まだその扉は開いてないみたい…。クイズに挑戦してみて？")
        return
    
    if content_body in ["ミュリオンモードオフ", "ミュリオンオフ"]:
        st = db.get_myurion_state(user_id)
        st["enabled"] = False
        db.save_myurion_state(user_id, st)
        await message.channel.send("わかったわ、通常言語に戻るわね。")
        return

    # --- 丹恒解放コード ---
    if "skopeo365" in re.sub(r"\s+", "", content_body).lower():
        if has_danheng_stage1(user_id) and not is_danheng_unlocked(user_id):
            set_danheng_unlocked(user_id, True)
            await send_myu(message, user_id, "丹恒の記憶が…蘇ったみたい♪ 『たんたんになってみて』と言ってみて？")
        elif is_danheng_unlocked(user_id):
            await send_myu(message, user_id, "ふふっ、その姿ならもう解放されているわよ♪")
        else:
            await send_myu(message, user_id, "ん〜…まだ何かが足りないみたいね。")
        waiting_for_transform_code.discard(user_id)
        return

    # --- 変身コード待ち ---
    if user_id in waiting_for_transform_code:
        t_text = content_body
        waiting_for_transform_code.discard(user_id)
        
        if "なのになってみて" in t_text:
            if is_nanoka_unlocked(user_id):
                set_user_form(user_id, "nanoka")
                await send_myu(message, user_id, "今日から三月なのか/長夜月の姿になるわ♪ よろしくねっ！")
            else:
                await send_myu(message, user_id, "まだ条件が足りないみたい…。じゃんけんにいっぱい勝ってみて？")
            return
        if "たんたんになってみて" in t_text:
            if is_danheng_unlocked(user_id):
                set_user_form(user_id, "danheng")
                await send_myu(message, user_id, "…わかった。丹恒の姿になろう。")
            else:
                await send_myu(message, user_id, "鍵が足りないみたい。")
            return
        
        fk = resolve_form_code(t_text)
        if fk:
            set_user_form(user_id, fk)
            await send_myu(message, user_id, f"**{get_form_display_name(fk)}** に変身したわ♪ どう？似合う？")
        else:
            await send_myu(message, user_id, "そのコードは知らないみたい…。もう一度確認してくれる？")
        return

    # --- データ管理モード ---
    if user_id in admin_data_mode:
        if content_body == "データ管理終了":
            admin_data_mode.discard(user_id)
            await send_myu(message, user_id, "データ管理モード、終了ね。また必要になったら呼んでちょうだい♪")
            return
        
        if content_body == "好感度一覧":
            text = logic.format_all_affection_status(message.guild)
            await send_myu(message, user_id, text)
            return

        # デフォルト案内
        await send_myu(message, user_id, f"{ADMIN_COMMANDS_LIST}\n\nコマンドを待ってるわ。何をすればいいかしら？♪")
        return
    
    if content_body == "データ管理" and db.is_admin(user_id):
        admin_data_mode.add(user_id)
        await send_myu(message, user_id, f"データ管理モードに入ったわ。\n{ADMIN_COMMANDS_LIST}")
        return

    # --- あだ名系 ---
    if content_body.startswith("あだ名登録"):
        new = content_body.replace("あだ名登録", "", 1).strip()
        if not new:
            waiting_for_nickname.add(user_id)
            await send_myu(message, user_id, rs.get_nickname_message_for_form(current_form, "ask"))
        else:
            db.set_nickname(user_id, new)
            await send_myu(message, user_id, rs.get_nickname_message_for_form(current_form, "confirm", new))
        return

    if user_id in waiting_for_nickname:
        if content_body:
            db.set_nickname(user_id, content_body)
            waiting_for_nickname.discard(user_id)
            await send_myu(message, user_id, rs.get_nickname_message_for_form(current_form, "confirm", content_body))
        else:
            await send_myu(message, user_id, "聞こえなかったわ、もう一度教えてくれる？")
        return

    # --- ガチャ ---
    if "ガチャ" in content_body:
        if "単発" in content_body:
            ok, res = logic.perform_gacha_pulls(user_id, 1)
            await send_myu(message, user_id, res)
        elif "10連" in content_body or "１０連" in content_body:
            use_ticket = "チケット" in content_body
            ok, res = logic.perform_gacha_pulls(user_id, 10, use_ticket)
            await send_myu(message, user_id, res)
        else:
            await send_myu(message, user_id, logic.format_gacha_status(user_id)) 
        return

    if "デイリー" in content_body:
        ok, stones, reason = logic.grant_daily_stones(user_id)
        await send_myu(message, user_id, f"{reason}\n所持石: {stones}")
        return

    # --- 変身開始 ---
    if content_body == "変身":
        waiting_for_transform_code.add(user_id)
        await send_myu(message, user_id, "ふふっ、別の姿になりたいの？ 変身コードを教えてくれるかしら♪")
        return

    # --- じゃんけん ---
    if "じゃんけん" in content_body or user_id in waiting_for_rps_choice:
        hand = logic.parse_hand(content_body)
        
        # 手が入力されていない場合 -> 開始
        if not hand and "じゃんけん" in content_body:
            waiting_for_rps_choice.add(user_id)
            # ★修正: rs.get_rps_prompt_for_form を使用
            prompt = rs.get_rps_prompt_for_form(current_form, name)
            await send_myu(message, user_id, prompt)
            return
        
        # 手が入力された場合
        if hand:
            force = user_id in FORCE_RPS_WIN_NEXT
            bot_hand = logic.get_bot_hand(hand, force)
            res = "win" if force else logic.judge_janken(hand, bot_hand)
            if force: FORCE_RPS_WIN_NEXT.discard(user_id)
            
            wins = inc_janken_win(user_id) if res == "win" else get_janken_wins(user_id)
            
            result_msg = rs.format_rps_result(current_form, name, hand, bot_hand, rs.get_rps_flavor(current_form, res, name), wins)
            
            await send_myu(message, user_id, result_msg)
            
            xp_map = {"win": 10, "lose": 5, "draw": 7}
            logic.add_affection_xp(user_id, xp_map.get(res, 0))
            waiting_for_rps_choice.discard(user_id)
            return

    # --- 親衛隊レベル確認 ---
    if content_body in ["親衛隊レベル", "親衛隊レベル確認"]:
        lv = db.get_guardian_level(user_id)
        msg = f"あなたの親衛隊レベルは Lv.{lv} よ♪" if lv else "まだ親衛隊レベルは登録されてないみたいね。"
        await send_myu(message, user_id, msg)
        return

    # --- 好感度チェック ---
    if content_body in ["好感度", "好感度チェック", "キュレネ好感度"]:
        msg = logic.get_affection_status_message(user_id)
        await send_myu(message, user_id, f"{message.author.mention} {msg}")
        return

    # --- 変身状態確認 ---
    if content_body in ["変身状態", "今の姿", "今のフォーム"]:
        fname = get_form_display_name(current_form)
        await send_myu(message, user_id, f"{message.author.mention} 今のあたしは **{fname}** よ♪")
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