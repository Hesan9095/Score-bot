# bot.py - نسخه ۲۰+ سازگار با python-telegram-bot[job-queue]==20.8
import os
import json
import asyncio
from datetime import time
from zoneinfo import ZoneInfo
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ForceReply
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# فقط این دو خط رو عوض کن!
TOKEN = "8247922560:AAElH7YwF5aGTWyDcrcQPaXdw-2cPGuoqAs"
YOUR_ID = 7373449365  # آیدی خودت از @userinfobot

SCORES_FILE = "scores.json"
ADMINS_FILE = "admins.json"
GROUPS_FILE = "groups.json"

tehran_tz = ZoneInfo("Asia/Tehran")

# --- توابع کمکی ---
def load_json(file):
    if os.path.exists(file):
        with open(file, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_json(file, data):
    with open(file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_admins():
    admins = load_json(ADMINS_FILE)
    if not admins:
        admins = [YOUR_ID]
        save_json(ADMINS_FILE, admins)
    return set(admins)

def is_admin(uid): return uid in load_admins()
def load_scores(): return load_json(SCORES_FILE)
def save_scores(d): save_json(SCORES_FILE, d)
def load_groups():
    groups = load_json(GROUPS_FILE)
    return groups if isinstance(groups, list) else []
def save_groups(g): save_json(GROUPS_FILE, g)
def get_name(user):
    return f"@{user.username}" if user.username else user.full_name

# --- پاک کردن پیام بعد 30 ثانیه ---
async def delete_after_30(message):
    await asyncio.sleep(30)
    try:
        await message.delete()
    except: pass

# --- پنل اصلی ---
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message.reply_to_message or not is_admin(message.from_user.id):
        return

    bot_username = f"@{context.bot.username}".lower()
    if bot_username not in message.text.lower():
        return

    keyboard = [
        [InlineKeyboardButton("امتیاز دهی", callback_data="panel_score"),
         InlineKeyboardButton("نمایش امتیازات", callback_data="panel_scores")],
        [InlineKeyboardButton("افزودن ادمین", callback_data="panel_addadmin"),
         InlineKeyboardButton("حذف ادمین", callback_data="panel_removeadmin")],
        [InlineKeyboardButton("پاک کردن همه امتیازات", callback_data="panel_resetall")]
    ]
    msg = await message.reply_text("پنل ادمین:", reply_markup=InlineKeyboardMarkup(keyboard))
    asyncio.create_task(delete_after_30(msg))

# --- صفحه امتیاز دهی ---
async def open_score_panel(query):
    keyboard = [
        [InlineKeyboardButton("+10", callback_data="score_+10"),
         InlineKeyboardButton("+25", callback_data="score_+25"),
         InlineKeyboardButton("+50", callback_data="score_+50")],
        [InlineKeyboardButton("-10", callback_data="score_-10"),
         InlineKeyboardButton("-25", callback_data="score_-25")],
        [InlineKeyboardButton("امتیاز دلخواه", callback_data="score_custom")],
        [InlineKeyboardButton("بازگشت", callback_data="back_to_main")]
    ]
    await query.edit_message_text("امتیاز بده:", reply_markup=InlineKeyboardMarkup(keyboard))

# --- بازگشت به پنل اصلی ---
async def back_to_main_panel(query):
    keyboard = [
        [InlineKeyboardButton("امتیاز دهی", callback_data="panel_score"),
         InlineKeyboardButton("نمایش امتیازات", callback_data="panel_scores")],
        [InlineKeyboardButton("افزودن ادمین", callback_data="panel_addadmin"),
         InlineKeyboardButton("حذف ادمین", callback_data="panel_removeadmin")],
        [InlineKeyboardButton("پاک کردن همه امتیازات", callback_data="panel_resetall")]
    ]
    await query.edit_message_text("پنل ادمین:", reply_markup=InlineKeyboardMarkup(keyboard))

# --- همه دکمه‌ها ---
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not query.message.reply_to_message:
        await query.edit_message_text("پیام اصلی حذف شده!")
        return

    target_user = query.message.reply_to_message.from_user
    target_id = str(target_user.id)
    data = query.data

    if data == "back_to_main":
        await back_to_main_panel(query)
        asyncio.create_task(delete_after_30(query.message))
        return

    if data == "score_custom":
        msg = await query.message.reply_text(
            "عدد رو وارد کن (مثلاً +150 یا -80):",
            reply_markup=ForceReply(selective=True)
        )
        context.application.bot_data[f"custom_{msg.message_id}"] = target_user
        return

    if data.startswith("score_") and data not in ["score_custom", "score_back"]:
        try: amount = int(data.split("_")[1])
        except: return

        scores = load_scores()
        if target_id not in scores:
            scores[target_id] = {"score": 0, "name": target_user.full_name, "username": target_user.username or "", "daily": 0}

        scores[target_id]["score"] += amount
        scores[target_id]["daily"] = scores[target_id].get("daily", 0) + amount
        save_scores(scores)

        msg_text = f"این پیام {amount:+} امتیاز گرفت!\n\nامتیاز کل: {scores[target_id]['score']}"
        keyboard = [[InlineKeyboardButton("بازگشت", callback_data="back_to_main")]]
        await query.edit_message_text(msg_text, reply_markup=InlineKeyboardMarkup(keyboard))
        asyncio.create_task(delete_after_30(query.message))
        return

    if data == "panel_score":
        await open_score_panel(query)
        asyncio.create_task(delete_after_30(query.message))
        return

    if data == "panel_scores":
        scores_data = load_scores()
        if not scores_data:
            keyboard = [[InlineKeyboardButton("بازگشت", callback_data="back_to_main")]]
            await query.edit_message_text("هنوز امتیازی ثبت نشده", reply_markup=InlineKeyboardMarkup(keyboard))
            asyncio.create_task(delete_after_30(query.message))
            return

        sorted_data = sorted(scores_data.items(), key=lambda x: x[1]["score"], reverse=True)
        text = "تابلوی امتیازات\n\n"
        for i, (uid, info) in enumerate(sorted_data[:30], 1):
            name = f"@{info.get('username')}" if info.get('username') else info.get('name', 'ناشناس')
            text += f"{i}. {name} → {info['score']} امتیاز\n"

        keyboard = [[InlineKeyboardButton("بازگشت", callback_data="back_to_main")]]
        await query.edit_message_text(text.strip(), reply_markup=InlineKeyboardMarkup(keyboard))
        asyncio.create_task(delete_after_30(query.message))
        return

    if data == "panel_addadmin":
        admins = load_admins()
        admins.add(target_user.id)
        save_json(ADMINS_FILE, list(admins))
        keyboard = [[InlineKeyboardButton("بازگشت", callback_data="back_to_main")]]
        await query.edit_message_text(f"{get_name(target_user)} حالا ادمینه", reply_markup=InlineKeyboardMarkup(keyboard))
        asyncio.create_task(delete_after_30(query.message))

    elif data == "panel_removeadmin":
        if target_user.id == YOUR_ID:
            keyboard = [[InlineKeyboardButton("بازگشت", callback_data="back_to_main")]]
            await query.edit_message_text("نمی‌تونی صاحب اصلی رو حذف کنی!", reply_markup=InlineKeyboardMarkup(keyboard))
            asyncio.create_task(delete_after_30(query.message))
            return
        admins = load_admins()
        if target_user.id in admins:
            admins.remove(target_user.id)
            save_json(ADMINS_FILE, list(admins))
            keyboard = [[InlineKeyboardButton("بازگشت", callback_data="back_to_main")]]
            await query.edit_message_text("ادمین حذف شد", reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            keyboard = [[InlineKeyboardButton("بازگشت", callback_data="back_to_main")]]
            await query.edit_message_text("این کاربر ادمین نبود", reply_markup=InlineKeyboardMarkup(keyboard))
        asyncio.create_task(delete_after_30(query.message))

    elif data == "panel_resetall":
        if os.path.exists(SCORES_FILE): os.remove(SCORES_FILE)
        keyboard = [[InlineKeyboardButton("بازگشت", callback_data="back_to_main")]]
        await query.edit_message_text("همه امتیازات پاک شد!", reply_markup=InlineKeyboardMarkup(keyboard))
        asyncio.create_task(delete_after_30(query.message))

# --- ورودی امتیاز دلخواه ---
async def custom_score_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id) or not update.message.reply_to_message:
        return

    reply_msg_id = update.message.reply_to_message.message_id
    target_user = context.application.bot_data.get(f"custom_{reply_msg_id}")
    if not target_user: return

    text = update.message.text.strip().lstrip("+")
    try: amount = int("-" + text) if text.startswith("-") else int(text)
    except:
        await update.message.reply_text("عدد معتبر وارد کن! (مثلاً +150 یا -80)")
        return

    target_id = str(target_user.id)
    scores = load_scores()
    if target_id not in scores:
        scores[target_id] = {"score": 0, "name": target_user.full_name, "username": target_user.username or "", "daily": 0}

    scores[target_id]["score"] += amount
    scores[target_id]["daily"] = scores[target_id].get("daily", 0) + amount
    save_scores(scores)

    keyboard = [[InlineKeyboardButton("بازگشت", callback_data="back_to_main")]]
    await update.message.reply_text(
        f"این پیام {amount:+} امتیاز گرفت!\n\nامتیاز کل: {scores[target_id]['score']}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    del context.application.bot_data[f"custom_{reply_msg_id}"]

# --- نمایش لیست با دستور ---
async def scores_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == "private": return
    data = load_scores()
    if not data: await update.message.reply_text("هنوز امتیازی ثبت نشده"); return
    sorted_data = sorted(data.items(), key=lambda x: x[1]["score"], reverse=True)
    text = "تابلوی امتیازات\n\n"
    for i, (uid, info) in enumerate(sorted_data[:30], 1):
        name = f"@{info.get('username')}" if info.get('username') else info.get('name', 'ناشناس')
        text += f"{i}. {name} → {info['score']} امتیاز\n"
    await update.message.reply_text(text.strip())

# --- جایزه شبانه ---
async def nightly_job(context: ContextTypes.DEFAULT_TYPE):
    scores = load_scores()
    today = {k: v.get("daily", 0) for k, v in scores.items() if v.get("daily", 0) > 0}
    if not today: return
    sorted_today = sorted(today.items(), key=lambda x: x[1], reverse=True)[:6]
    rewards = [50, 30, 20, 15, 10, 5]
    msg = "جایزه امشب به فعال‌ترین‌ها!\n\n"
    for i, (uid, daily) in enumerate(sorted_today):
        reward = rewards[i]
        scores[uid]["score"] += reward
        name = f"@{scores[uid].get('username')}" if scores[uid].get('username') else scores[uid].get('name', 'ناشناس')
        msg += f"{i+1}. {name} +{reward} جایزه\n"
    for uid in scores: scores[uid]["daily"] = 0
    save_scores(scores)
    for chat_id in load_groups():
        try: await context.bot.send_message(int(chat_id), msg)
        except: pass

# --- اجرا ---
if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(MessageHandler(filters.TEXT & filters.Entity("mention") & filters.REPLY, admin_panel))
    app.add_handler(MessageHandler(filters.TEXT & filters.REPLY, custom_score_input))
    app.add_handler(CallbackQueryHandler(button_handler))

    app.add_handler(CommandHandler("scores", scores_command))
    app.add_handler(CommandHandler("score", scores_command))
    app.add_handler(MessageHandler(filters.Regex(r"^/(امتیازات|لیست)$"), scores_command))

    app.job_queue.run_daily(nightly_job, time=time(23, 0, tzinfo=tehran_tz))

    print("ربات نهایی با دکمه بازگشت تمیز آماده است!")
    app.run_polling(drop_pending_updates=True)
