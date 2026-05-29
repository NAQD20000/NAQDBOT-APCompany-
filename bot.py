import os
import logging
import re
import json
import asyncio
import random
from datetime import datetime, timedelta
from collections import defaultdict
from telegram import Update, ChatPermissions, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, 
    filters, ContextTypes, CallbackQueryHandler
)
from dotenv import load_dotenv

# بارگذاری توکن
load_dotenv()
TOKEN = os.getenv('BOT_TOKEN')

# تنظیمات لاگ
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', 
                    level=logging.INFO)

# ========== دیتابیس‌ها ==========
user_messages = defaultdict(int)
user_warns = defaultdict(int)
user_points = defaultdict(int)
user_joins = {}
muted_until = {}
temp_bans = {}
message_count = defaultdict(int)
last_message_time = defaultdict(float)
anti_spam_count = defaultdict(int)

# تنظیمات گروه
link_locked = False
forward_locked = False
slow_mode = False
slow_mode_seconds = 3
night_mode = False
night_start = 23
night_end = 6
group_rules = "📋 **قوانین گروه:**\n1- احترام به همه\n2- عدم ارسال لینک\n3- عدم فحاشی\n4- عدم اسپم"
warn_limit = 3

# کلمات فیلتر شده (فحش، کلمات نامناسب)
bad_words = ["فحش1", "فحش2", "فحش3", "کلمه_بد1", "کلمه_بد2"]

# سطوح کاربری
RANKS = {
    0: "🌱 تازه‌وارد",
    50: "📝 عضو فعال",
    200: "⭐ نابغه",
    500: "👑 سوپراستار",
    1000: "🚀 افسانه",
    5000: "💎 اَبَرافسانه"
}

# پاسخ‌های خودکار
auto_responses = {
    "سلام": "سلام به شما! چطور می‌تونم کمکتون کنم؟",
    "خوبی": "خوبم ممنون! شما چطورید؟",
    "مرسی": "خواهش میکنم 🤗",
    "خداحافظ": "خدانگهدار! بازم سر بزنید 🙋‍♂️"
}

# ========== دستورات ادمین پیشرفته ==========

async def mute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """سکوت کاربر با زمان دلخواه"""
    if not update.effective_chat.get_member(update.effective_user.id).is_chat_admin():
        await update.message.reply_text("❌ فقط ادمین‌ها!")
        return
    
    if not update.message.reply_to_message:
        await update.message.reply_text("⚠️ روی پیام فرد ریپلی کن!")
        return
    
    user_id = update.message.reply_to_message.from_user.id
    user_name = update.message.reply_to_message.from_user.first_name
    args = context.args
    duration = int(args[0]) if args and args[0].isdigit() else 30
    
    until_date = datetime.now() + timedelta(minutes=duration)
    muted_until[user_id] = until_date
    
    await context.bot.restrict_chat_member(
        chat_id=update.effective_chat.id,
        user_id=user_id,
        permissions=ChatPermissions(can_send_messages=False),
        until_date=until_date
    )
    
    keyboard = [[InlineKeyboardButton("گزارش خطا", callback_data=f"report_mute_{user_id}")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"🔇 کاربر {user_name} به مدت {duration} دقیقه سکوت شد!",
        reply_markup=reply_markup
    )

async def unmute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """برداشتن سکوت"""
    if not update.effective_chat.get_member(update.effective_user.id).is_chat_admin():
        await update.message.reply_text("❌ فقط ادمین‌ها!")
        return
    
    if not update.message.reply_to_message:
        await update.message.reply_text("⚠️ روی پیام فرد ریپلی کن!")
        return
    
    user_id = update.message.reply_to_message.from_user.id
    user_name = update.message.reply_to_message.from_user.first_name
    
    await context.bot.restrict_chat_member(
        chat_id=update.effective_chat.id,
        user_id=user_id,
        permissions=ChatPermissions(
            can_send_messages=True,
            can_send_media_messages=True,
            can_send_other_messages=True,
            can_add_web_page_previews=True
        )
    )
    
    if user_id in muted_until:
        del muted_until[user_id]
    
    await update.message.reply_text(f"🔊 سکوت {user_name} برداشته شد!")

async def temp_ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بن موقت کاربر"""
    if not update.effective_chat.get_member(update.effective_user.id).is_chat_admin():
        await update.message.reply_text("❌ فقط ادمین‌ها!")
        return
    
    if not update.message.reply_to_message:
        await update.message.reply_text("⚠️ روی پیام فرد ریپلی کن!")
        return
    
    args = context.args
    duration = int(args[0]) if args and args[0].isdigit() else 60
    
    user_id = update.message.reply_to_message.from_user.id
    user_name = update.message.reply_to_message.from_user.first_name
    until_date = datetime.now() + timedelta(minutes=duration)
    temp_bans[user_id] = until_date
    
    await context.bot.ban_chat_member(chat_id=update.effective_chat.id, user_id=user_id)
    
    # تنظیم آنبلاک خودکار
    asyncio.create_task(auto_unban(update.effective_chat.id, user_id, duration))
    
    await update.message.reply_text(f"⛔ {user_name} به مدت {duration} دقیقه بن شد!")

async def auto_unban(chat_id, user_id, duration):
    await asyncio.sleep(duration * 60)
    try:
        await application.bot.unban_chat_member(chat_id=chat_id, user_id=user_id)
        if user_id in temp_bans:
            del temp_bans[user_id]
    except:
        pass

async def ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بن دائم"""
    if not update.effective_chat.get_member(update.effective_user.id).is_chat_admin():
        await update.message.reply_text("❌ فقط ادمین‌ها!")
        return
    
    if not update.message.reply_to_message:
        await update.message.reply_text("⚠️ روی پیام فرد ریپلی کن!")
        return
    
    user_id = update.message.reply_to_message.from_user.id
    user_name = update.message.reply_to_message.from_user.first_name
    
    await context.bot.ban_chat_member(chat_id=update.effective_chat.id, user_id=user_id)
    await update.message.reply_text(f"⛔ {user_name} از گروه بن شد!")

async def warn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """اخطار به کاربر (3 اخطار = بن)"""
    if not update.effective_chat.get_member(update.effective_user.id).is_chat_admin():
        await update.message.reply_text("❌ فقط ادمین‌ها!")
        return
    
    if not update.message.reply_to_message:
        await update.message.reply_text("⚠️ روی پیام فرد ریپلی کن!")
        return
    
    user_id = update.message.reply_to_message.from_user.id
    user_name = update.message.reply_to_message.from_user.first_name
    user_warns[user_id] += 1
    warns_left = warn_limit - user_warns[user_id]
    
    if user_warns[user_id] >= warn_limit:
        await context.bot.ban_chat_member(chat_id=update.effective_chat.id, user_id=user_id)
        await update.message.reply_text(f"⚠️ کاربر {user_name} به دلیل 3 اخطار از گروه بن شد!")
        del user_warns[user_id]
    else:
        await update.message.reply_text(
            f"⚠️ اخطار {user_warns[user_id]} از {warn_limit} به {user_name}!\n"
            f"📝 {warns_left} اخطار تا بن شدن باقی مونده!"
        )

async def clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """پاک کردن پیام‌ها"""
    if not update.effective_chat.get_member(update.effective_user.id).is_chat_admin():
        await update.message.reply_text("❌ فقط ادمین‌ها!")
        return
    
    if not update.message.reply_to_message:
        await update.message.reply_text("⚠️ روی اولین پیام ریپلی کن!")
        return
    
    message_id = update.message.reply_to_message.message_id
    count = 0
    for i in range(message_id, update.message.message_id):
        try:
            await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=i)
            count += 1
        except:
            pass
    
    msg = await update.message.reply_text(f"🧹 {count} پیام پاک شد!")
    await asyncio.sleep(3)
    await msg.delete()

# ========== تنظیمات قفل ==========

async def locklink(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global link_locked
    if not update.effective_chat.get_member(update.effective_user.id).is_chat_admin():
        await update.message.reply_text("❌ فقط ادمین‌ها!")
        return
    link_locked = True
    await update.message.reply_text("🔒 لینک قفل شد! کاربران عادی نمیتوانند لینک بفرستند.")

async def unlocklink(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global link_locked
    if not update.effective_chat.get_member(update.effective_user.id).is_chat_admin():
        await update.message.reply_text("❌ فقط ادمین‌ها!")
        return
    link_locked = False
    await update.message.reply_text("🔓 قفل لینک برداشته شد.")

async def lockforward(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global forward_locked
    if not update.effective_chat.get_member(update.effective_user.id).is_chat_admin():
        await update.message.reply_text("❌ فقط ادمین‌ها!")
        return
    forward_locked = True
    await update.message.reply_text("🔒 فوروارد قفل شد!")

async def unlockforward(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global forward_locked
    if not update.effective_chat.get_member(update.effective_user.id).is_chat_admin():
        await update.message.reply_text("❌ فقط ادمین‌ها!")
        return
    forward_locked = False
    await update.message.reply_text("🔓 فوروارد آزاد شد!")

async def slowmode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global slow_mode, slow_mode_seconds
    if not update.effective_chat.get_member(update.effective_user.id).is_chat_admin():
        await update.message.reply_text("❌ فقط ادمین‌ها!")
        return
    args = context.args
    if args and args[0].isdigit():
        slow_mode_seconds = int(args[0])
        slow_mode = True
        await update.message.reply_text(f"🐢 حالت آهسته فعال شد! هر {slow_mode_seconds} ثانیه یک پیام")
    else:
        slow_mode = False
        await update.message.reply_text("🐢 حالت آهسته غیرفعال شد!")

async def setrules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global group_rules
    if not update.effective_chat.get_member(update.effective_user.id).is_chat_admin():
        await update.message.reply_text("❌ فقط ادمین‌ها!")
        return
    args = context.args
    if args:
        group_rules = " ".join(args)
        await update.message.reply_text(f"✅ قوانین گروه به‌روزرسانی شد!\n\n{group_rules}")
    else:
        await update.message.reply_text("⚠️ لطفاً قوانین جدید را وارد کنید!\nمثال: /setrules قانون 1 - قانون 2")

async def getrules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(group_rules, parse_mode="Markdown")

# ========== دستورات عمومی ==========

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📊 آمار گروه", callback_data="stats")],
        [InlineKeyboardButton("📈 رنک من", callback_data="rank")],
        [InlineKeyboardButton("📋 قوانین", callback_data="rules")],
        [InlineKeyboardButton("🎁 قرعه‌کشی", callback_data="lottery")],
        [InlineKeyboardButton("ℹ️ راهنما", callback_data="help")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🤖 **ربات اَبَرمدیریت گروه NAQD**\n\n"
        "به ربات قدرتمند مدیریت گروه خوش آمدید!\n"
        "با استفاده از دکمه‌های زیر از امکانات ربات استفاده کنید:\n\n"
        "**نسخه:** 3.0.0 | **توسعه‌دهنده:** @AMIRSAMDERAKHSHAN",
        parse_mode="Markdown",
        reply_markup=reply_markup
    )

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    member_count = await context.bot.get_chat_member_count(chat.id)
    admins = await context.bot.get_chat_administrators(chat.id)
    
    total_msgs = sum(user_messages.values())
    active_users = len([v for v in user_messages.values() if v > 0])
    
    await update.message.reply_text(
        f"📊 **آمار گروه {chat.title}**\n\n"
        f"👥 کل اعضا: {member_count}\n"
        f"👑 تعداد ادمین‌ها: {len(admins)}\n"
        f"💬 کل پیام‌ها: {total_msgs}\n"
        f"⭐ کاربران فعال: {active_users}\n"
        f"🔇 سکوت شده‌ها: {len(muted_until)}\n"
        f"⛔ موقت بن‌ها: {len(temp_bans)}\n"
        f"🔒 وضعیت قفل لینک: {'فعال' if link_locked else 'غیرفعال'}\n"
        f"🔒 وضعیت قفل فوروارد: {'فعال' if forward_locked else 'غیرفعال'}\n"
        f"🐢 حالت آهسته: {'فعال' if slow_mode else 'غیرفعال'}",
        parse_mode="Markdown"
    )

async def rank(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    msg_count = user_messages[user_id]
    points = user_points[user_id]
    
    level = "🌱 تازه‌وارد"
    for required, title in sorted(RANKS.items()):
        if msg_count >= required:
            level = title
    
    next_rank = _get_next_rank(msg_count)
    
    await update.message.reply_text(
        f"📈 **کارت شما**\n\n"
        f"👤 نام: {update.effective_user.first_name}\n"
        f"🏆 سطح: {level}\n"
        f"📨 پیام‌ها: {msg_count}\n"
        f"⭐ امتیاز: {points}\n"
        f"⚠️ اخطارها: {user_warns.get(user_id, 0)}/{warn_limit}\n"
        f"🎯 تا سطح بعدی: {next_rank} پیام",
        parse_mode="Markdown"
    )

async def leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not user_messages:
        await update.message.reply_text("📊 هنوز آماری ثبت نشده!")
        return
    
    sorted_users = sorted(user_messages.items(), key=lambda x: x[1], reverse=True)[:10]
    leaderboard_text = "🏆 **جدول برترین‌ها** 🏆\n\n"
    
    for i, (user_id, count) in enumerate(sorted_users, 1):
        try:
            user = await context.bot.get_chat(user_id)
            name = user.first_name
            leaderboard_text += f"{i}. {name}: {count} پیام\n"
        except:
            leaderboard_text += f"{i}. کاربر ناشناس: {count} پیام\n"
    
    await update.message.reply_text(leaderboard_text, parse_mode="Markdown")

async def lottery(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """قرعه‌کشی روزانه"""
    user_id = update.effective_user.id
    today = datetime.now().date()
    
    if user_joins.get(user_id) == today:
        await update.message.reply_text("🎲 شما امروز قبلاً در قرعه‌کشی شرکت کردید! فردا دوباره امتحان کنید.")
        return
    
    user_joins[user_id] = today
    prize = random.randint(1, 50)
    user_points[user_id] += prize
    
    await update.message.reply_text(
        f"🎉 **تبریک!** 🎉\n\n"
        f"شما در قرعه‌کشی روزانه برنده شدید!\n"
        f"🎁 جایزه شما: {prize} امتیاز\n"
        f"⭐ امتیاز کل شما: {user_points[user_id]}"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 **راهنمای کامل ربات**\n\n"
        "**دستورات عمومی:**\n"
        "/start - شروع به کار\n"
        "/stats - آمار گروه\n"
        "/rank - کارت شما\n"
        "/leaderboard - جدول برترین‌ها\n"
        "/lottery - قرعه‌کشی روزانه\n"
        "/rules - مشاهده قوانین\n"
        "/info - اطلاعات کاربر\n\n"
        "**دستورات ادمین (با ریپلی):**\n"
        "/mute [دقیقه] - سکوت کاربر\n"
        "/unmute - برداشتن سکوت\n"
        "/ban - بن دائم\n"
        "/tempban [دقیقه] - بن موقت\n"
        "/warn - اخطار\n"
        "/clear - پاک کردن پیام‌ها\n\n"
        "**تنظیمات ادمین:**\n"
        "/locklink - قفل لینک\n"
        "/unlocklink - باز کردن قفل لینک\n"
        "/lockforward - قفل فوروارد\n"
        "/unlockforward - باز کردن قفل فوروارد\n"
        "/slowmode [ثانیه] - حالت آهسته\n"
        "/setrules [قوانین] - تنظیم قوانین\n"
        "/getrules - مشاهده قوانین",
        parse_mode="Markdown"
    )

async def rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(group_rules, parse_mode="Markdown")

async def userinfo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = update.message.reply_to_message.from_user if update.message.reply_to_message else update.effective_user
    user_id = target.id
    
    msg_count = user_messages[user_id]
    warns = user_warns.get(user_id, 0)
    points = user_points[user_id]
    
    status = "در حال چت"
    if user_id in muted_until:
        status = f"سکوت شده تا {muted_until[user_id].strftime('%H:%M')}"
    elif user_id in temp_bans:
        status = f"بن موقت تا {temp_bans[user_id].strftime('%H:%M')}"
    
    await update.message.reply_text(
        f"ℹ️ **اطلاعات کاربر**\n\n"
        f"👤 نام: {target.first_name}\n"
        f"🆔 آیدی: `{user_id}`\n"
        f"📊 وضعیت: {status}\n"
        f"📨 پیام‌ها: {msg_count}\n"
        f"⚠️ اخطارها: {warns}/{warn_limit}\n"
        f"⭐ امتیاز: {points}",
        parse_mode="Markdown"
    )

# ========== هندلرهای خودکار ==========

async def welcome_new_members(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for new_member in update.message.new_chat_members:
        if new_member.id == context.bot.id:
            await update.message.reply_text(
                "🤖 **ربات اَبَرمدیریت با موفقیت فعال شد!**\n\n"
                f"قوانین گروه:\n{group_rules}\n\n"
                "از دستور /help برای دیدن امکانات استفاده کنید.",
                parse_mode="Markdown"
            )
        else:
            keyboard = [[InlineKeyboardButton("📋 قوانین", callback_data="rules")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                f"✨ **به گروه خوش آمدید {new_member.first_name}!** ✨\n\n"
                f"📋 لطفاً قوانین گروه را مطالعه کنید.\n"
                f"💬 برای شروع از دستور /help استفاده کنید.\n"
                f"🎁 هر روز در قرعه‌کشی شرکت کنید!",
                parse_mode="Markdown",
                reply_markup=reply_markup
            )

async def left_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.left_chat_member:
        user = update.message.left_chat_member
        await update.message.reply_text(f"👋 {user.first_name} از گروه خارج شد! خدا حافظ.")

async def anti_spam(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    
    user_id = update.effective_user.id
    current_time = datetime.now().timestamp()
    
    # Slow mode
    if slow_mode:
        last_time = last_message_time.get(user_id, 0)
        if current_time - last_time < slow_mode_seconds:
            await update.message.delete()
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"🐢 {update.effective_user.first_name} جان! لطفاً {slow_mode_seconds} ثانیه صبر کن!",
                reply_to_message_id=update.message.message_id
            )
            return
        last_message_time[user_id] = current_time
    
    # Anti-flood (تکرار سریع)
    message_count[user_id] += 1
    
    if message_count[user_id] > 5:
        if anti_spam_count[user_id] >= 2:
            await context.bot.restrict_chat_member(
                chat_id=update.effective_chat.id,
                user_id=user_id,
                permissions=ChatPermissions(can_send_messages=False),
                until_date=datetime.now() + timedelta(minutes=5)
            )
            await update.message.reply_text(f"🚫 {update.effective_user.first_name} به دلیل اسپم شدید 5 دقیقه سکوت شد!")
            message_count[user_id] = 0
            anti_spam_count[user_id] = 0
        else:
            await update.message.reply_text(f"⚠️ {update.effective_user.first_name} از اسپم خودداری کن!")
            anti_spam_count[user_id] += 1
            message_count[user_id] = 0
    else:
        # Reset counter after 5 seconds
        asyncio.create_task(reset_counter(user_id))
    
    # به‌روزرسانی آمار
    user_messages[user_id] += 1
    user_points[user_id] += 1

async def reset_counter(user_id):
    await asyncio.sleep(5)
    if user_id in message_count:
        message_count[user_id] = max(0, message_count[user_id] - 1)

async def filter_links(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global link_locked
    
    if not update.message or not update.message.text:
        return
    
    if link_locked:
        user = update.effective_user
        chat_member = await context.bot.get_chat_member(update.effective_chat.id, user.id)
        
        if not chat_member.is_chat_admin:
            link_pattern = r'(https?://|www\.|@|t\.me/|\.com|\.ir|\.org|\.net)'
            if re.search(link_pattern, update.message.text, re.IGNORECASE):
                await update.message.delete()
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=f"🔗 {user.first_name} جان! ارسال لینک در گروه ممنوع است!",
                    reply_to_message_id=update.message.message_id
                )

async def filter_forward(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global forward_locked
    
    if forward_locked and update.message.forward_from:
        user = update.effective_user
        chat_member = await context.bot.get_chat_member(update.effective_chat.id, user.id)
        
        if not chat_member.is_chat_admin:
            await update.message.delete()
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"🚫 {user.first_name} جان! فوروارد پیام در گروه ممنوع است!",
                reply_to_message_id=update.message.message_id
            )

async def filter_bad_words(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    
    for word in bad_words:
        if word.lower() in update.message.text.lower():
            await update.message.delete()
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"🚫 {update.effective_user.first_name} جان! از کلمات نامناسب استفاده نکنید!",
                reply_to_message_id=update.message.message_id
            )
            return

async def auto_responses_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    
    text = update.message.text.strip().lower()
    for key, response in auto_responses.items():
        if key in text:
            await update.message.reply_text(response)
            break

async def track_all_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ردیابی همه پیام‌ها برای آمار"""
    if update.message and update.message.text and not update.message.text.startswith('/'):
        user_messages[update.effective_user.id] += 1

# ========== Callback handlers ==========
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "stats":
        await stats(query.message, context)
    elif query.data == "rank":
        await rank(query.message, context)
    elif query.data == "rules":
        await rules(query.message, context)
    elif query.data == "lottery":
        await lottery(query.message, context)
    elif query.data == "help":
        await help_command(query.message, context)

# ========== تابع کمکی ==========
def _get_next_rank(current_msgs):
    for required, _ in sorted(RANKS.items()):
        if current_msgs < required:
            return required - current_msgs
    return 0

# ========== اجرای اصلی ==========
if __name__ == '__main__':
    application = ApplicationBuilder().token(TOKEN).build()
    
    # دستورات ادمین
    application.add_handler(CommandHandler('mute', mute))
    application.add_handler(CommandHandler('unmute', unmute))
    application.add_handler(CommandHandler('ban', ban))
    application.add_handler(CommandHandler('tempban', temp_ban))
    application.add_handler(CommandHandler('warn', warn))
    application.add_handler(CommandHandler('clear', clear))
    application.add_handler(CommandHandler('locklink', locklink))
    application.add_handler(CommandHandler('unlocklink', unlocklink))
    application.add_handler(CommandHandler('lockforward', lockforward))
    application.add_handler(CommandHandler('unlockforward', unlockforward))
    application.add_handler(CommandHandler('slowmode', slowmode))
    application.add_handler(CommandHandler('setrules', setrules))
    application.add_handler(CommandHandler('getrules', getrules))
    
    # دستورات عمومی
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('stats', stats))
    application.add_handler(CommandHandler('rank', rank))
    application.add_handler(CommandHandler('leaderboard', leaderboard))
    application.add_handler(CommandHandler('lottery', lottery))
    application.add_handler(CommandHandler('help', help_command))
    application.add_handler(CommandHandler('rules', rules))
    application.add_handler(CommandHandler('info', userinfo))
    
    # Callback handlers
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # هندلرهای خودکار
    application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_new_members))
    application.add_handler(MessageHandler(filters.StatusUpdate.LEFT_CHAT_MEMBER, left_member))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, anti_spam))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, filter_links))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, filter_forward))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, filter_bad_words))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, auto_responses_handler))
    application.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, track_all_messages))
    
    # اجرا با Polling
    application.run_polling()