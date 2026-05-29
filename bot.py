import os
import logging
import re
from datetime import datetime, timedelta
from collections import defaultdict
from telegram import Update, ChatPermissions
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

# دیتابیس ساده (برای ذخیره آمار موقت)
user_messages = defaultdict(int)
user_ranks = {}
muted_until = {}
banned_until = {}

# سطوح کاربری
RANKS = {
    0: "🌱 تازه‌وارد",
    10: "📝 عضو فعال",
    50: "⭐ نابغه",
    100: "👑 سوپراستار",
    500: "🚀 افسانه"
}

# ========== دستورات ادمین ==========
async def mute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """سکوت کردن یک کاربر"""
    if not update.effective_chat.get_member(update.effective_user.id).is_chat_admin():
        await update.message.reply_text("❌ فقط ادمین‌ها میتوانند از این دستور استفاده کنند!")
        return
    
    if not update.message.reply_to_message:
        await update.message.reply_text("⚠️ لطفاً روی پیام فرد مورد نظر ریپلی کنید!\n/میکس")
        return
    
    user_id = update.message.reply_to_message.from_user.id
    user_name = update.message.reply_to_message.from_user.first_name
    
    # جداسازی زمان (پیش‌فرض ۱ ساعت)
    args = context.args
    duration = 60  # دقیقه
    
    if args and args[0].isdigit():
        duration = int(args[0])
    
    until_date = datetime.now() + timedelta(minutes=duration)
    muted_until[user_id] = until_date
    
    await context.bot.restrict_chat_member(
        chat_id=update.effective_chat.id,
        user_id=user_id,
        permissions=ChatPermissions(can_send_messages=False),
        until_date=until_date
    )
    
    await update.message.reply_text(f"🔇 کاربر {user_name} به مدت {duration} دقیقه سکوت شد!")

async def unmute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """برداشتن سکوت کاربر"""
    if not update.effective_chat.get_member(update.effective_user.id).is_chat_admin():
        await update.message.reply_text("❌ فقط ادمین‌ها میتوانند از این دستور استفاده کنند!")
        return
    
    if not update.message.reply_to_message:
        await update.message.reply_text("⚠️ لطفاً روی پیام فرد مورد نظر ریپلی کنید!")
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
    
    await update.message.reply_text(f"🔊 سکوت کاربر {user_name} برداشته شد!")

async def ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بن کردن کاربر"""
    if not update.effective_chat.get_member(update.effective_user.id).is_chat_admin():
        await update.message.reply_text("❌ فقط ادمین‌ها میتوانند از این دستور استفاده کنند!")
        return
    
    if not update.message.reply_to_message:
        await update.message.reply_text("⚠️ لطفاً روی پیام فرد مورد نظر ریپلی کنید!")
        return
    
    user_id = update.message.reply_to_message.from_user.id
    user_name = update.message.reply_to_message.from_user.first_name
    
    await context.bot.ban_chat_member(chat_id=update.effective_chat.id, user_id=user_id)
    await update.message.reply_text(f"⛔ کاربر {user_name} از گروه بن شد!")

async def warn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """اخطار دادن به کاربر"""
    if not update.effective_chat.get_member(update.effective_user.id).is_chat_admin():
        await update.message.reply_text("❌ فقط ادمین‌ها میتوانند از این دستور استفاده کنند!")
        return
    
    if not update.message.reply_to_message:
        await update.message.reply_text("⚠️ لطفاً روی پیام فرد مورد نظر ریپلی کنید!")
        return
    
    user_name = update.message.reply_to_message.from_user.first_name
    await update.message.reply_text(f"⚠️ اخطار به کاربر {user_name}!\nلطفاً قوانین گروه را رعایت کنید.")

async def clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """پاک کردن پیام‌ها"""
    if not update.effective_chat.get_member(update.effective_user.id).is_chat_admin():
        await update.message.reply_text("❌ فقط ادمین‌ها میتوانند از این دستور استفاده کنند!")
        return
    
    if not update.message.reply_to_message:
        await update.message.reply_text("⚠️ روی اولین پیامی که میخواهید پاک کنید ریپلی کنید!")
        return
    
    message_id = update.message.reply_to_message.message_id
    for i in range(message_id, update.message.message_id):
        try:
            await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=i)
        except:
            pass
    
    await update.message.reply_text("🧹 پیام‌ها پاک شدند!")

# ========== دستورات عمومی ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دستور شروع"""
    await update.message.reply_text(
        "🤖 **ربات مدیریت گروه APCompany**\n\n"
        "**دستورات کاربری:**\n"
        "• `/stats` - آمار گروه\n"
        "• `/rank` - سطح شما\n"
        "• `/help` - راهنما\n\n"
        "**دستورات ادمین (با ریپلی):**\n"
        "• `/mute [دقیقه]` - سکوت کاربر\n"
        "• `/unmute` - برداشتن سکوت\n"
        "• `/ban` - بن کردن کاربر\n"
        "• `/warn` - اخطار به کاربر\n"
        "• `/clear` - پاک کردن پیام‌ها\n"
        "• `/locklink` - قفل لینک\n"
        "• `/unlocklink` - باز کردن قفل لینک",
        parse_mode="Markdown"
    )

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش آمار گروه"""
    chat = update.effective_chat
    member_count = await context.bot.get_chat_member_count(chat.id)
    
    # محاسبه پیام‌های امروز
    today_msgs = sum(1 for count in user_messages.values() if count > 0)
    
    await update.message.reply_text(
        f"📊 **آمار گروه {chat.title}**\n\n"
        f"👥 تعداد اعضا: {member_count}\n"
        f"💬 پیام‌های امروز: {today_msgs}\n"
        f"⭐ کاربران فعال: {len(user_messages)}\n"
        f"🔇 کاربران سکوت شده: {len(muted_until)}",
        parse_mode="Markdown"
    )

async def rank(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش سطح کاربر"""
    user_id = update.effective_user.id
    msg_count = user_messages[user_id]
    
    # محاسبه سطح
    level = 0
    for required, title in sorted(RANKS.items()):
        if msg_count >= required:
            level = title
    
    await update.message.reply_text(
        f"📈 **سطح شما:** {level}\n"
        f"📨 **تعداد پیام‌ها:** {msg_count}\n"
        f"🎯 **برای سطح بعدی:** {_get_next_rank(msg_count)} پیام دیگر لازم است",
        parse_mode="Markdown"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دستور راهنما"""
    await start(update, context)

# ========== قفل لینک ==========
link_locked = False

async def locklink(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """قفل کردن لینک"""
    global link_locked
    if not update.effective_chat.get_member(update.effective_user.id).is_chat_admin():
        await update.message.reply_text("❌ فقط ادمین‌ها!")
        return
    link_locked = True
    await update.message.reply_text("🔒 لینک قفل شد! کاربران عادی نمیتوانند لینک بفرستند.")

async def unlocklink(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """باز کردن قفل لینک"""
    global link_locked
    if not update.effective_chat.get_member(update.effective_user.id).is_chat_admin():
        await update.message.reply_text("❌ فقط ادمین‌ها!")
        return
    link_locked = False
    await update.message.reply_text("🔓 قفل لینک برداشته شد.")

# ========== خوش‌آمدگویی خودکار ==========
async def welcome_new_members(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """خوش‌آمدگویی به اعضای جدید"""
    for new_member in update.message.new_chat_members:
        if new_member.id == context.bot.id:
            # ربات به گروه اضافه شده
            await update.message.reply_text("🤖 ربات مدیریت گروه فعال شد!\nاز دستور /help برای دیدن امکانات استفاده کنید.")
        else:
            await update.message.reply_text(
                f"✨ به گروه خوش آمدید {new_member.first_name}! ✨\n\n"
                f"📋 لطفاً قوانین گروه را مطالعه کنید.\n"
                f"💬 برای شروع از دستور /help استفاده کنید."
            )

# ========== ضد اسپم ==========
last_messages = defaultdict(list)

async def anti_spam(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تشخیص و حذف پیام‌های تکراری"""
    if not update.message or not update.message.text:
        return
    
    user_id = update.effective_user.id
    current_time = datetime.now()
    message_text = update.message.text
    
    # پاک کردن پیام‌های قدیمی
    last_messages[user_id] = [t for t in last_messages[user_id] if (current_time - t).seconds < 5]
    
    # بررسی اسپم
    if len(last_messages[user_id]) >= 3:
        await update.message.delete()
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"⚠️ کاربر {update.effective_user.first_name} به دلیل اسپم سکوت شد!",
            reply_to_message_id=update.message.message_id
        )
        # سکوت خودکار ۱ دقیقه‌ای
        await context.bot.restrict_chat_member(
            chat_id=update.effective_chat.id,
            user_id=user_id,
            permissions=ChatPermissions(can_send_messages=False),
            until_date=datetime.now() + timedelta(minutes=1)
        )
        return
    
    last_messages[user_id].append(current_time)
    
    # به‌روزرسانی آمار پیام
    user_messages[user_id] += 1

# ========== فیلتر لینک ==========
async def filter_links(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """فیلتر کردن لینک‌ها"""
    global link_locked
    
    if not update.message or not update.message.text:
        return
    
    # اگر کاربر ادمین است یا قفل باز است
    if link_locked:
        user = update.effective_user
        chat_member = await context.bot.get_chat_member(update.effective_chat.id, user.id)
        
        if not chat_member.is_chat_admin:
            # چک کردن وجود لینک
            link_pattern = r'(https?://|www\.|@|t\.me/|\.com|\.ir|\.org)'
            if re.search(link_pattern, update.message.text, re.IGNORECASE):
                await update.message.delete()
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=f"🔗 {user.first_name} جان! ارسال لینک در گروه آزاد نیست!",
                    reply_to_message_id=update.message.message_id
                )

# ========== تابع کمکی ==========
def _get_next_rank(current_msgs):
    """پیدا کردن تعداد پیام تا سطح بعدی"""
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
    application.add_handler(CommandHandler('warn', warn))
    application.add_handler(CommandHandler('clear', clear))
    application.add_handler(CommandHandler('locklink', locklink))
    application.add_handler(CommandHandler('unlocklink', unlocklink))
    
    # دستورات عمومی
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('stats', stats))
    application.add_handler(CommandHandler('rank', rank))
    application.add_handler(CommandHandler('help', help_command))
    
    # هندلرهای خودکار
    application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_new_members))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, anti_spam))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, filter_links))
    
    # اجرا با Webhook
        # اجرا با Polling (بدون نیاز به Webhook)
    application.run_polling()