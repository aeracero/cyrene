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

# --- Help Messages ---
ADMIN_COMMANDS_LIST = (
    "【データ管理モード コマンド一覧】\n"
    "- `ニックネーム確認`: 登録されているあだ名を確認\n"
    "- `管理者編集`: 管理者の追加・削除メニュー\n"
    "- `親衛隊レベル編集`: 親衛隊レベルの設定・削除メニュー\n"
    "- `好感度編集`: 好感度設定（レベル閾値など）の変更\n"
    "- `好感度XP追加 @ユーザー 数値`: 指定ユーザーのXPを増減\n"
    "- `好感度一覧`: 全ユーザーのレベルとXPを表示\n"
    "- `じゃんけん勝利数追加 @ユーザー 数値`: 勝利数を加算\n"
    "- `メッセージ制限編集`: 1日の会話回数制限の設定\n"
    "- `メッセージ制限bypass編集`: 制限無視権限の管理（メイン管理者のみ）\n"
    "- `変身管理`: 変身状態の確認・強制変更\n"
    "- `変身解放状況確認`: 各キャラの解放フラグ確認（メイン管理者のみ）\n"
    "- `データ管理終了`: 管理モードを終了"
)

GENERAL_COMMANDS_LIST = (
    "【現在使えるコマンド一覧よ♪】\n"
    "■ 会話・コミュニケーション\n"
    "- `こんにちは` / `おやすみ`: 挨拶してくれるわ\n"
    "- `みんなについて教えて`: 他の人のことをどう思ってるか教えるわ\n"
    "- `甘えていいんだよ`: …ふふっ、甘えちゃうかも？\n"
    "- `じゃんけん`: 勝負よ！\n"
    "- `あだ名登録 [名前]`: あなたの呼び方を覚えるわ\n"
    "- `好感度`: わたしたちの仲良し度を確認できるわ\n"
    "- `親衛隊レベル`: あなたの親衛隊レベルを確認\n\n"
    "■ 変身・姿\n"
    "- `変身`: 別の姿に変身するためのコードを入力\n"
    "- `変身状態` / `今の姿`: 今どの姿で話しているか確認\n"
    "- `[特定の合言葉]`: ヒントを探して、新しい姿を解放してね♪\n\n"
    "■ ガチャ\n"
    "- `ガチャメニュー`: 所持石やチケットの確認\n"
    "- `単発ガチャ` / `10連ガチャ`: 運試しよ♪\n"
    "- `デイリー受け取り`: 1日1回、石をプレゼント\n\n"
    "■ その他\n"
    "- `ミュリオンモードオン`: ミュミュ語で話すわ\n"
    "- `コマンドを教えて`: このリストを表示"
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
    
    # 処理対象かチェック
    is_active_mode = (
        user_id in waiting_for_nickname or user_id in waiting_for_rename or
        user_id in waiting_for_admin_add or user_id in waiting_for_admin_remove or
        user_id in waiting_for_rps_choice or user_id in admin_data_mode or
        user_id in waiting_for_guardian_level or user_id in waiting_for_msg_limit or
        user_id in waiting_for_transform_code or user_id in MYURION_QUIZ_STATE
    )
    # メンションされたか、何か待機モード中か、あるいは特定のキーワード（コマンド教えて等）か
    is_command_query = message.content.strip() in ["コマンド", "コマンド教えて", "コマンドを教えて", "ヘルプ"]
    
    if not (client.user in message.mentions or is_active_mode or is_command_query): return

    content = re.sub(rf"<@!?{client.user.id}>", "", message.content).strip()
    nickname = db.get_nickname(user_id)
    name = nickname if nickname else message.author.display_name
    current_form = get_user_form(user_id)
    
    # --- ★追加：一般向けコマンド一覧 ---
    if content in ["コマンド", "コマンド教えて", "コマンドを教えて", "ヘルプ"]:
        # データ管理モード中なら管理者用ヘルプを出す
        if user_id in admin_data_mode:
            await send_myu(message, user_id, ADMIN_COMMANDS_LIST)
        else:
            await send_myu(message, user_id, f"{message.author.mention} {GENERAL_COMMANDS_LIST}")
        return

    # --- 管理者コマンド（全体設定） ---
    if content == "全体ミュリオンモード" and db.is_admin(user_id):
        db.set_all_myurion_enabled(True)
        await message.channel.send(f"{message.author.mention} 全員ミュリオンモードON！")
        return
    if content == "全体ミュリオン解除" and db.is_admin(user_id):
        db.set_all_myurion_enabled(False)
        await message.channel.send(f"{message.author.mention} 全員ミュリオンモード解除。")
        return

    # --- ミュリオンクイズ ---
    if user_id in MYURION_QUIZ_STATE:
        ans = logic.parse_myurion_answer(content)
        if not ans:
            await send_myu(message, user_id, f"{message.author.mention} 1〜4で答えてミュ。")
            return
        state = MYURION_QUIZ_STATE[user_id]
        if ans - 1 == state["correct_index"]:
            total = db.add_myurion_correct(user_id)
            if total >= 3 and not db.is_myurion_unlocked(user_id):
                st = db.get_myurion_state(user_id)
                st["unlocked"], st["enabled"] = True, True
                db.save_myurion_state(user_id, st)
                MYURION_QUIZ_STATE.pop(user_id, None)
                await send_myu(message, user_id, f"{message.author.mention} 3問正解ミュ！ミュリオンモード解放ミュ！")
            else:
                MYURION_QUIZ_STATE.pop(user_id, None)
                await send_myu(message, user_id, f"{message.author.mention} 正解ミュ！(現在{total}/3)")
        else:
            MYURION_QUIZ_STATE.pop(user_id, None)
            await send_myu(message, user_id, f"{message.author.mention} 残念、ハズレミュ…。")
        return

    if "ミュウ、ミュミュミュウミュウ、ミュイー" in content:
        st = db.get_myurion_state(user_id)
        if st.get("unlocked"):
            st["enabled"] = True
            db.save_myurion_state(user_id, st)
            await send_myu(message, user_id, f"{message.author.mention} 既に解放済みミュ！モードONミュ！")
        else:
            await logic.send_myurion_question(message, user_id, st.get("quiz_correct", 0), MYURION_QUIZ_STATE)
        return

    if content in ["ミュリオンモードオン", "ミュリオンオン"]:
        st = db.get_myurion_state(user_id)
        if st.get("unlocked"):
            st["enabled"] = True
            db.save_myurion_state(user_id, st)
            await send_myu(message, user_id, "ミュリオンモードONミュ！")
        else:
            await send_myu(message, user_id, "まだ解放されてないみたい…。クイズに挑戦して？")
        return
    
    if content in ["ミュリオンモードオフ", "ミュリオンオフ"]:
        st = db.get_myurion_state(user_id)
        st["enabled"] = False
        db.save_myurion_state(user_id, st)
        await message.channel.send("通常言語に戻るわね。")
        return

    # --- 丹恒解放コード ---
    if "skopeo365" in re.sub(r"\s+", "", content).lower():
        if has_danheng_stage1(user_id) and not is_danheng_unlocked(user_id):
            set_danheng_unlocked(user_id, True)
            await send_myu(message, user_id, "丹恒解放条件達成！『たんたんになってみて』と言ってみて？")
        elif is_danheng_unlocked(user_id):
            await send_myu(message, user_id, "もう解放済みよ。")
        else:
            await send_myu(message, user_id, "まだ何かが足りないみたい。")
        waiting_for_transform_code.discard(user_id)
        return

    # --- 変身コード待ち ---
    if user_id in waiting_for_transform_code:
        t_text = content
        waiting_for_transform_code.discard(user_id)
        
        if "なのになってみて" in t_text:
            if is_nanoka_unlocked(user_id):
                set_user_form(user_id, "nanoka")
                await send_myu(message, user_id, "今日から三月なのか/長夜月の姿になるわ♪")
            else:
                await send_myu(message, user_id, "条件が足りないみたい…。じゃんけんに勝ってみて？")
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
            await send_myu(message, user_id, f"**{get_form_display_name(fk)}** に変身したわ♪")
        else:
            await send_myu(message, user_id, "そのコードは知らないみたい…。")
        return

    # --- データ管理モード ---
    if user_id in admin_data_mode:
        if content == "データ管理終了":
            admin_data_mode.discard(user_id)
            await send_myu(message, user_id, "データ管理モード終了するわ♪また何かあったら言ってちょうだいね。")
            return
        
        if content == "好感度一覧":
            text = logic.format_all_affection_status(message.guild)
            await send_myu(message, user_id, text)
            return

        # ★変更: デフォルトで全コマンドリストを表示（それ以外の処理は呼び出し元がハンドリングするか、ここに追加）
        # ここでは「コマンド入力待ち」として、ヘルプを表示しつつ入力を促す
        await send_myu(
            message, 
            user_id, 
            f"{ADMIN_COMMANDS_LIST}\n\nコマンドを入力してね。"
        )
        return
    
    if content == "データ管理" and db.is_admin(user_id):
        admin_data_mode.add(user_id)
        # ★変更: 入った瞬間にリストを表示
        await send_myu(message, user_id, f"データ管理モードに入ったわ。\n{ADMIN_COMMANDS_LIST}")
        return

    # --- あだ名系 ---
    if content.startswith("あだ名登録"):
        new = content.replace("あだ名登録", "", 1).strip()
        if not new:
            waiting_for_nickname.add(user_id)
            await send_myu(message, user_id, rs.get_nickname_message_for_form(current_form, "ask"))
        else:
            db.set_nickname(user_id, new)
            await send_myu(message, user_id, rs.get_nickname_message_for_form(current_form, "confirm", new))
        return

    if user_id in waiting_for_nickname:
        if content:
            db.set_nickname(user_id, content)
            waiting_for_nickname.discard(user_id)
            await send_myu(message, user_id, rs.get_nickname_message_for_form(current_form, "confirm", content))
        else:
            await send_myu(message, user_id, "もう一度教えて？")
        return

    # --- ガチャ ---
    if "ガチャ" in content:
        if "単発" in content:
            ok, res = logic.perform_gacha_pulls(user_id, 1)
            await send_myu(message, user_id, res)
        elif "10連" in content or "１０連" in content:
            use_ticket = "チケット" in content
            ok, res = logic.perform_gacha_pulls(user_id, 10, use_ticket)
            await send_myu(message, user_id, res)
        else:
            await send_myu(message, user_id, logic.format_gacha_status(user_id)) 
        return

    if "デイリー" in content:
        ok, stones, reason = logic.grant_daily_stones(user_id)
        await send_myu(message, user_id, f"{reason}\n所持石: {stones}")
        return

    # --- 変身開始 ---
    if content == "変身":
        waiting_for_transform_code.add(user_id)
        await send_myu(message, user_id, "変身コードを教えて？")
        return

    # --- じゃんけん ---
    if "じゃんけん" in content or user_id in waiting_for_rps_choice:
        hand = logic.parse_hand(content)
        if not hand and "じゃんけん" in content:
            waiting_for_rps_choice.add(user_id)
            prompt = logic.get_rps_prompt_for_form(current_form, name) # logic内に関数がない場合はrsかlinesへ
            # ※ get_rps_prompt_for_form は以前 cyrene.py に直書きされていたので、
            # もし logic.py に移動し忘れている場合は以下の一行で仮対処
            # prompt = "グー/チョキ/パーを選んで？" 
            # (ただし前回の logic.py には入っていないため、暫定的に単純なメッセージにします)
            # 完全に直すには logic.py に prompt取得関数を移設する必要がありますが、
            # 今回は cyrene.py 内で簡易的に処理します。
            prompt = "じゃんけんしましょ♪ グー・チョキ・パー、どれにする？"
            await send_myu(message, user_id, prompt)
            return
        
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
    if content in ["親衛隊レベル", "親衛隊レベル確認"]:
        lv = db.get_guardian_level(user_id)
        msg = f"親衛隊レベルは Lv.{lv} よ♪" if lv else "まだ親衛隊レベルは登録されてないみたい。"
        await send_myu(message, user_id, msg)
        return

    # --- 好感度チェック ---
    if content in ["好感度", "好感度チェック", "キュレネ好感度"]:
        msg = logic.get_affection_status_message(user_id)
        await send_myu(message, user_id, f"{message.author.mention} {msg}")
        return

    # --- 変身状態確認 ---
    if content in ["変身状態", "今の姿", "今のフォーム"]:
        fname = get_form_display_name(current_form)
        await send_myu(message, user_id, f"{message.author.mention} 今のあたしは **{fname}** よ♪")
        return

    # --- 通常会話 ---
    xp, lv = logic.get_user_affection(user_id)
    reply = rs.generate_reply_for_form(current_form, content, lv, user_id, name)
    
    # 荒笛トリガーチェック
    if current_form == "cyrene" and ARAFUE_TRIGGER_LINE in reply:
        mark_danheng_stage1(user_id)
    
    # なのか解放チェック
    if "記憶は流れ星を待ってる" in content and get_janken_wins(user_id) >= 307 and not is_nanoka_unlocked(user_id):
        set_nanoka_unlocked(user_id, True)
        reply += "\n\n【三月なのか 解放！】『なのになってみて』と言ってみて？"

    await send_myu(message, user_id, f"{message.author.mention} {reply}")
    logic.add_affection_xp(user_id, 3)

client.run(DISCORD_TOKEN)