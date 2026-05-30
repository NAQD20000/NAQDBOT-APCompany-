import os
import logging
import re
import json
import asyncio
import random
import hashlib
import base64
import uuid
import string
from datetime import datetime
from collections import defaultdict
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, 
    filters, ContextTypes, CallbackQueryHandler
)
from dotenv import load_dotenv

# بارگذاری توکن
load_dotenv()
TOKEN = os.getenv('BOT_TOKEN')

# رمز عبور ربات
BOT_PASSWORD = "naqdbothack"

# دیکشنری برای ذخیره وضعیت احراز هویت کاربران
authenticated_users = set()

# تنظیمات لاگ
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', 
                    level=logging.INFO)

# ========== دیتابیس‌ها ==========
user_messages = defaultdict(int)
user_points = defaultdict(int)

# ========== لینک‌های مستقیم سایت‌های برنامه‌نویسی ==========
PROGRAMMING_LINKS = {
    "📚 **آموزش و مستندات:**": {
        "Python Official": "https://docs.python.org/3/",
        "W3Schools": "https://www.w3schools.com/",
        "MDN Web Docs": "https://developer.mozilla.org/",
        "GeeksforGeeks": "https://www.geeksforgeeks.org/",
        "Real Python": "https://realpython.com/",
        "Stack Overflow": "https://stackoverflow.com/",
        "Java Documentation": "https://docs.oracle.com/en/java/",
        "Go Documentation": "https://go.dev/doc/",
        "Rust Documentation": "https://doc.rust-lang.org/",
        "PHP Documentation": "https://www.php.net/docs.php",
    },
    "🎓 **دوره‌های رایگان:**": {
        "FreeCodeCamp": "https://www.freecodecamp.org/",
        "The Odin Project": "https://www.theodinproject.com/",
        "CS50 (Harvard)": "https://cs50.harvard.edu/",
        "MIT OpenCourseWare": "https://ocw.mit.edu/",
        "Khan Academy": "https://www.khanacademy.org/computing",
        "Codecademy": "https://www.codecademy.com/",
        "Coursera": "https://www.coursera.org/",
        "edX": "https://www.edx.org/",
    },
    "🐙 **GitHub و ابزارها:**": {
        "GitHub": "https://github.com/",
        "GitLab": "https://gitlab.com/",
        "Bitbucket": "https://bitbucket.org/",
        "GitHub Trends": "https://github.com/trending",
        "GitHub Stars": "https://github.com/stars",
    },
    "☁️ **ابزارهای آنلاین:**": {
        "Replit": "https://replit.com/",
        "CodePen": "https://codepen.io/",
        "JSFiddle": "https://jsfiddle.net/",
        "OnlineGDB": "https://www.onlinegdb.com/",
        "PythonAnywhere": "https://www.pythonanywhere.com/",
        "Glitch": "https://glitch.com/",
        "Codesandbox": "https://codesandbox.io/",
    },
    "🗄️ **دیتابیس و بک‌اند:**": {
        "MongoDB University": "https://university.mongodb.com/",
        "PostgreSQL Docs": "https://www.postgresql.org/docs/",
        "MySQL Docs": "https://dev.mysql.com/doc/",
        "Redis Docs": "https://redis.io/documentation",
        "Firebase": "https://firebase.google.com/docs",
    },
    "🐳 **DevOps و Docker:**": {
        "Docker Docs": "https://docs.docker.com/",
        "Kubernetes Docs": "https://kubernetes.io/docs/",
        "AWS Documentation": "https://docs.aws.amazon.com/",
        "Google Cloud Docs": "https://cloud.google.com/docs",
        "Azure Docs": "https://docs.microsoft.com/en-us/azure/",
        "Linux Journey": "https://linuxjourney.com/",
    },
    "📱 **فریم‌ورک‌ها:**": {
        "React Docs": "https://react.dev/",
        "Vue.js Docs": "https://vuejs.org/guide/",
        "Angular Docs": "https://angular.io/docs",
        "Django Docs": "https://docs.djangoproject.com/",
        "Flask Docs": "https://flask.palletsprojects.com/",
        "FastAPI Docs": "https://fastapi.tiangolo.com/",
        "Laravel Docs": "https://laravel.com/docs",
        "Spring Boot": "https://spring.io/projects/spring-boot",
    },
    "🤖 **AI و یادگیری ماشین:**": {
        "TensorFlow": "https://www.tensorflow.org/",
        "PyTorch": "https://pytorch.org/",
        "Scikit-learn": "https://scikit-learn.org/",
        "Hugging Face": "https://huggingface.co/",
        "Kaggle": "https://www.kaggle.com/",
        "OpenAI": "https://openai.com/",
    },
    "🔒 **امنیت و تست:**": {
        "OWASP": "https://owasp.org/",
        "HackerRank": "https://www.hackerrank.com/",
        "LeetCode": "https://leetcode.com/",
        "CodeWars": "https://www.codewars.com/",
        "PentesterLab": "https://pentesterlab.com/",
    },
    "📖 **کتاب‌های رایگان:**": {
        "Free Programming Books": "https://github.com/EbookFoundation/free-programming-books",
        "Go by Example": "https://gobyexample.com/",
        "Rust by Example": "https://doc.rust-lang.org/rust-by-example/",
        "Python Crash Course": "https://ehmatthes.github.io/pcc/",
    }
}

# ========== تابع بررسی رمز ==========
async def check_auth(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بررسی احراز هویت کاربر"""
    user_id = update.effective_user.id
    if user_id not in authenticated_users:
        await update.message.reply_text(
            "🔐 **دسترسی محدود شده است!**\n\n"
            "این ربات فقط برای اعضای گروه NAQD قابل استفاده است.\n"
            "لطفاً رمز عبور را وارد کنید:\n\n"
            "`/login رمزعبور`\n\n"
            f"اگر رمز را ندارید، با @AMIRSAMDERAKHSHAN تماس بگیرید.",
            parse_mode="Markdown"
        )
        return False
    return True

async def login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ورود با رمز عبور"""
    if not context.args:
        await update.message.reply_text(
            "🔐 **ورود به ربات**\n\n"
            "لطفاً رمز عبور را وارد کنید:\n"
            "`/login naqdbothack`\n\n"
            "پس از ورود، به تمام قابلیت‌ها دسترسی خواهید داشت.",
            parse_mode="Markdown"
        )
        return
    
    password = context.args[0]
    if password == BOT_PASSWORD:
        authenticated_users.add(update.effective_user.id)
        await update.message.reply_text(
            "✅ **ورود موفق!**\n\n"
            "به ربات حرفه‌ای برنامه‌نویسان خوش آمدید.\n"
            "از دستور `/start` برای دیدن امکانات استفاده کنید.",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text("❌ **رمز عبور اشتباه است!**\nدسترسی غیرمجاز رد شد.", parse_mode="Markdown")

# ========== لینک‌های مستقیم ==========
async def links(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش لینک‌های مستقیم سایت‌های برنامه‌نویسی"""
    if not await check_auth(update, context):
        return
    
    keyboard = []
    for category in PROGRAMMING_LINKS.keys():
        keyboard.append([InlineKeyboardButton(category, callback_data=f"cat_{category}")])
    keyboard.append([InlineKeyboardButton("🔍 جستجوی سریع", callback_data="search_links")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🔗 **لینک‌های مستقیم سایت‌های برنامه‌نویسی**\n\n"
        "بیش از **100 سایت معتبر** برنامه‌نویسی:\n"
        "• آموزش و مستندات\n"
        "• دوره‌های رایگان\n"
        "• ابزارهای آنلاین\n"
        "• فریم‌ورک‌ها و دیتابیس\n"
        "• DevOps و امنیت\n\n"
        "دسته مورد نظر را انتخاب کنید:",
        parse_mode="Markdown",
        reply_markup=reply_markup
    )

async def category_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش لینک‌های یک دسته"""
    query = update.callback_query
    await query.answer()
    
    category = query.data.replace("cat_", "")
    
    links_text = f"🔗 **{category}**\n\n"
    for name, url in PROGRAMMING_LINKS.get(category, {}).items():
        links_text += f"• [{name}]({url})\n"
    
    keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_links")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.message.edit_text(links_text, parse_mode="Markdown", reply_markup=reply_markup, disable_web_page_preview=True)

async def back_to_links(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بازگشت به منوی لینک‌ها"""
    query = update.callback_query
    await query.answer()
    
    keyboard = []
    for category in PROGRAMMING_LINKS.keys():
        keyboard.append([InlineKeyboardButton(category, callback_data=f"cat_{category}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.message.edit_text(
        "🔗 **لینک‌های مستقیم سایت‌های برنامه‌نویسی**\n\n"
        "دسته مورد نظر را انتخاب کنید:",
        parse_mode="Markdown",
        reply_markup=reply_markup
    )

# ========== دستورات فارسی ==========

async def start_fa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دستور شروع به فارسی"""
    if not await check_auth(update, context):
        return
    
    keyboard = [
        [InlineKeyboardButton("🔗 لینک‌های برنامه‌نویسی", callback_data="links_menu")],
        [InlineKeyboardButton("💻 اجرای کد", callback_data="run_code_fa")],
        [InlineKeyboardButton("🔐 ابزارهای رمزنگاری", callback_data="crypto_fa")],
        [InlineKeyboardButton("🗄️ ابزارهای دیتابیس", callback_data="db_fa")],
        [InlineKeyboardButton("🐳 Docker و DevOps", callback_data="docker_fa")],
        [InlineKeyboardButton("📚 آموزش و راهنما", callback_data="learn_fa")],
        [InlineKeyboardButton("🛠️ ابزارهای کاربردی", callback_data="utils_fa")],
        [InlineKeyboardButton("📊 آمار گروه", callback_data="stats_fa")],
        [InlineKeyboardButton("🏆 مسابقه و جایزه", callback_data="game_fa")],
        [InlineKeyboardButton("❓ راهنمای دستورات", callback_data="help_fa")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🤖 **ربات حرفه‌ای برنامه‌نویسان NAQD**\n\n"
        "به بزرگترین ربات تخصصی برنامه‌نویسی فارسی خوش آمدید!\n\n"
        "**🔧 امکانات ربات:**\n"
        "• 🔗 بیش از 100 لینک مستقیم سایت‌های برنامه‌نویسی\n"
        "• 💻 اجرای کد در 6 زبان مختلف\n"
        "• 🔐 رمزنگاری و هش کردن (Base64, MD5, SHA)\n"
        "• 🗄️ تولید SQL و دیتابیس\n"
        "• 🐳 تولید Dockerfile و docker-compose\n"
        "• 📚 نقشه‌های راه یادگیری\n"
        "• 🛠️ تبدیل رنگ، تایم‌استمپ، رمزساز و...\n"
        "• 🏆 قرعه‌کشی روزانه و امتیازدهی\n\n"
        "**توسعه‌دهنده:** @AMIRSAMDERAKHSHAN\n"
        "**نسخه:** 4.0.0",
        parse_mode="Markdown",
        reply_markup=reply_markup
    )

# ========== ابزارهای رمزنگاری فارسی ==========
async def hash_fa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ساخت هش به فارسی"""
    if not await check_auth(update, context):
        return
    
    if not context.args:
        await update.message.reply_text(
            "🔐 **ساخت هش (Hash)**\n\n"
            "❗ نحوه استفاده:\n"
            "`/هش md5 متن شما`\n"
            "`/هش sha1 متن شما`\n"
            "`/هش sha256 متن شما`\n\n"
            "مثال: `/هش md5 سلام`",
            parse_mode="Markdown"
        )
        return
    
    algo = context.args[0].lower()
    text = ' '.join(context.args[1:])
    
    if not text:
        await update.message.reply_text("❌ لطفاً متن را وارد کنید!")
        return
    
    if algo == 'md5':
        result = hashlib.md5(text.encode()).hexdigest()
    elif algo == 'sha1':
        result = hashlib.sha1(text.encode()).hexdigest()
    elif algo == 'sha256':
        result = hashlib.sha256(text.encode()).hexdigest()
    else:
        await update.message.reply_text("❌ نوع هش نامعتبر! فقط md5, sha1, sha256")
        return
    
    await update.message.reply_text(f"🔐 **{algo.upper()} هش:**\n`{result}`", parse_mode="Markdown")

async def base64_fa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تبدیل Base64 به فارسی"""
    if not await check_auth(update, context):
        return
    
    if not context.args:
        await update.message.reply_text(
            "🔐 **ابزار Base64**\n\n"
            "❗ نحوه استفاده:\n"
            "برای رمزگذاری: `/بیس رمز متن شما`\n"
            "برای رمزگشایی: `/بیس رمزگشا Base64Text`\n\n"
            "مثال:\n"
            "`/بیس رمز سلام`\n"
            "`/بیس رمزگشا U2FsdGVkX1`",
            parse_mode="Markdown"
        )
        return
    
    mode = context.args[0]
    text = ' '.join(context.args[1:])
    
    if mode == 'رمز' or mode == 'encode':
        encoded = base64.b64encode(text.encode()).decode()
        await update.message.reply_text(f"🔐 **Base64 رمزگذاری شده:**\n`{encoded}`", parse_mode="Markdown")
    elif mode == 'رمزگشا' or mode == 'decode':
        try:
            decoded = base64.b64decode(text).decode()
            await update.message.reply_text(f"🔓 **Base64 رمزگشایی شده:**\n`{decoded}`", parse_mode="Markdown")
        except:
            await update.message.reply_text("❌ متن Base64 نامعتبر است!")
    else:
        await update.message.reply_text("❌ حالت نامعتبر! از 'رمز' یا 'رمزگشا' استفاده کنید.")

async def uuid_fa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ساخت UUID به فارسی"""
    if not await check_auth(update, context):
        return
    
    new_uuid = uuid.uuid4()
    await update.message.reply_text(f"🆔 **UUID جدید:**\n`{new_uuid}`", parse_mode="Markdown")

async def password_fa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ساخت رمز عبور به فارسی"""
    if not await check_auth(update, context):
        return
    
    length = int(context.args[0]) if context.args and context.args[0].isdigit() else 16
    
    characters = string.ascii_letters + string.digits + string.punctuation
    password = ''.join(random.choice(characters) for _ in range(length))
    
    await update.message.reply_text(f"🔐 **رمز عبور پیشنهادی ({length} کاراکتر):**\n`{password}`", parse_mode="Markdown")

# ========== ابزارهای کاربردی فارسی ==========
async def timestamp_fa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تبدیل تایم‌استمپ به فارسی"""
    if not await check_auth(update, context):
        return
    
    if not context.args:
        await update.message.reply_text(
            "⏱️ **تبدیل تایم‌استمپ**\n\n"
            "❗ نحوه استفاده:\n"
            "`/زمان 1704067200` - تبدیل تایم‌استمپ به تاریخ\n"
            "`/زمان 2024-01-01` - تبدیل تاریخ به تایم‌استمپ\n\n"
            "فرمت تاریخ: YYYY-MM-DD",
            parse_mode="Markdown"
        )
        return
    
    input_value = context.args[0]
    
    if input_value.isdigit():
        dt = datetime.fromtimestamp(int(input_value))
        result = f"📅 **تاریخ:** {dt.strftime('%Y-%m-%d %H:%M:%S')}"
    else:
        try:
            dt = datetime.strptime(input_value, '%Y-%m-%d')
            timestamp = int(dt.timestamp())
            result = f"⏱️ **تایم‌استمپ:** {timestamp}"
        except:
            result = "❌ فرمت نامعتبر! استفاده کنید: YYYY-MM-DD"
    
    await update.message.reply_text(result)

async def color_fa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تبدیل رنگ به فارسی"""
    if not await check_auth(update, context):
        return
    
    if not context.args:
        await update.message.reply_text(
            "🎨 **تبدیل رنگ**\n\n"
            "❗ نحوه استفاده:\n"
            "`/رنگ #FF5733` - تبدیل Hex به RGB\n"
            "`/رنگ rgb(255, 87, 51)` - تبدیل RGB به Hex",
            parse_mode="Markdown"
        )
        return
    
    color_input = context.args[0]
    
    if color_input.startswith('#'):
        hex_color = color_input.lstrip('#')
        rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        result = f"🎨 **RGB:** rgb({rgb[0]}, {rgb[1]}, {rgb[2]})"
    elif color_input.startswith('rgb'):
        numbers = re.findall(r'\d+', color_input)
        if len(numbers) == 3:
            hex_color = '#{:02x}{:02x}{:02x}'.format(int(numbers[0]), int(numbers[1]), int(numbers[2]))
            result = f"🎨 **Hex:** {hex_color}"
        else:
            result = "❌ فرمت RGB نامعتبر!"
    else:
        result = "❌ فرمت نامعتبر! استفاده کنید: #RRGGBB یا rgb(r,g,b)"
    
    await update.message.reply_text(result)

# ========== ابزارهای دیتابیس فارسی ==========
async def sql_fa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تولید SQL به فارسی"""
    if not await check_auth(update, context):
        return
    
    if not context.args:
        await update.message.reply_text(
            "🗄️ **تولید SQL Query**\n\n"
            "❗ نحوه استفاده:\n"
            "`/اسکیوال users with id, name, email, created_at`\n\n"
            "این دستور یک جدول و کوئری SELECT برای شما می‌سازد.",
            parse_mode="Markdown"
        )
        return
    
    description = ' '.join(context.args)
    sql = f"-- SQL Query for: {description}\n\n"
    sql += "CREATE TABLE IF NOT EXISTS table_name (\n"
    sql += "    id INT PRIMARY KEY AUTO_INCREMENT,\n"
    sql += "    name VARCHAR(100) NOT NULL,\n"
    sql += "    email VARCHAR(100) UNIQUE,\n"
    sql += "    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP\n"
    sql += ");\n\n"
    sql += "-- INSERT example\n"
    sql += "INSERT INTO table_name (name, email) VALUES ('John Doe', 'john@example.com');\n\n"
    sql += "-- SELECT query\n"
    sql += "SELECT * FROM table_name WHERE condition ORDER BY created_at DESC;"
    
    await update.message.reply_text(f"📊 **SQL Query:**\n```sql\n{sql}\n```", parse_mode="Markdown")

# ========== ابزارهای Docker فارسی ==========
async def dockerfile_fa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تولید Dockerfile به فارسی"""
    if not await check_auth(update, context):
        return
    
    if not context.args:
        await update.message.reply_text(
            "🐳 **تولید Dockerfile**\n\n"
            "❗ نحوه استفاده:\n"
            "`/داکر پایتون`\n"
            "`/داکر نود`\n"
            "`/داکر گو`\n\n"
            "زبان‌های پشتیبانی شده: پایتون, نود, گو, رست",
            parse_mode="Markdown"
        )
        return
    
    language = context.args[0]
    
    dockerfiles = {
        'پایتون': """
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "bot.py"]
""",
        'نود': """
FROM node:18-alpine

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .

EXPOSE 3000
CMD ["npm", "start"]
""",
        'گو': """
FROM golang:1.21-alpine

WORKDIR /app

COPY go.mod go.sum ./
RUN go mod download

COPY . .
RUN go build -o main .

CMD ["./main"]
""",
    }
    
    result = dockerfiles.get(language, dockerfiles['پایتون'])
    await update.message.reply_text(f"🐳 **Dockerfile ({language}):**\n```dockerfile\n{result}\n```", parse_mode="Markdown")

# ========== آموزش فارسی ==========
async def python_roadmap_fa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نقشه راه پایتون به فارسی"""
    if not await check_auth(update, context):
        return
    
    roadmap = """
🐍 **نقشه راه یادگیری پایتون (Python Roadmap)**

**مرحله 1 - مبانی (2 هفته):**
• متغیرها و انواع داده
• حلقه‌ها (for, while)
• شرط‌ها (if, elif, else)
• توابع (def)
• لیست‌ها و دیکشنری‌ها

**مرحله 2 - پیشرفته (3 هفته):**
• کلاس‌ها و شی‌گرایی (OOP)
• مدیریت استثناها (try/except)
• Decorators و Generators
• ماژول‌ها و پکیج‌ها
• فایل‌ها (open, read, write)

**مرحله 3 - تخصصی (1 ماه):**
• وب (Django/Flask/FastAPI)
• دیتا (Pandas/NumPy)
• API و RESTful
• تست (pytest, unittest)

**منابع رایگان:**
• docs.python.org
• realpython.com
• w3schools.com/python
• geeksforgeeks.org/python

**تمرین روزانه:**
هر روز حداقل 30 دقیقه کد بزنید!
"""
    await update.message.reply_text(roadmap, parse_mode="Markdown")

async def interview_fa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """سوالات مصاحبه به فارسی"""
    if not await check_auth(update, context):
        return
    
    questions = [
        "❓ تفاوت بین `==` و `is` در پایتون چیست؟",
        "❓ REST API چیست و چه اصولی دارد؟",
        "❓ تفاوت Git merge و rebase چیست؟",
        "❓ HTTP Status Code 404 یعنی چه؟",
        "❓ Docker و تفاوت آن با ماشین مجازی چیست؟",
        "❓ NoSQL و SQL چه تفاوت‌هایی دارند؟",
        "❓ GIL در پایتون چیست؟",
        "❓ تفاوت بین list و tuple در پایتون؟",
        "❓ Decorator در پایتون چیست؟",
        "❓ تفاوت بین `@staticmethod` و `@classmethod`؟",
    ]
    question = random.choice(questions)
    
    keyboard = [[InlineKeyboardButton("🎲 سوال بعدی", callback_data="next_question")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(question, reply_markup=reply_markup)

# ========== آمار و سرگرمی فارسی ==========
async def stats_fa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """آمار گروه به فارسی"""
    if not await check_auth(update, context):
        return
    
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
        f"🎯 میانگین پیام به ازای هر کاربر: {total_msgs // max(active_users, 1)}",
        parse_mode="Markdown"
    )

async def lottery_fa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """قرعه‌کشی روزانه به فارسی"""
    if not await check_auth(update, context):
        return
    
    user_id = update.effective_user.id
    today = datetime.now().date()
    
    if user_points.get(f"lottery_{user_id}") == str(today):
        await update.message.reply_text("🎲 شما امروز قبلاً در قرعه‌کشی شرکت کردید!\nفردا دوباره امتحان کنید.")
        return
    
    user_points[f"lottery_{user_id}"] = str(today)
    prize = random.randint(5, 100)
    user_points[user_id] += prize
    
    await update.message.reply_text(
        f"🎉 **تبریک!** 🎉\n\n"
        f"شما در قرعه‌کشی روزانه برنده شدید!\n"
        f"🎁 جایزه شما: {prize} امتیاز\n"
        f"⭐ امتیاز کل شما: {user_points[user_id]}"
    )

async def rank_fa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش رنک کاربر به فارسی"""
    if not await check_auth(update, context):
        return
    
    user_id = update.effective_user.id
    msg_count = user_messages[user_id]
    points = user_points[user_id]
    
    if msg_count < 10:
        rank = "🌱 تازه‌وارد"
    elif msg_count < 50:
        rank = "📝 عضو فعال"
    elif msg_count < 200:
        rank = "⭐ نابغه"
    elif msg_count < 500:
        rank = "👑 سوپراستار"
    else:
        rank = "🚀 افسانه"
    
    await update.message.reply_text(
        f"📈 **کارت شما**\n\n"
        f"👤 نام: {update.effective_user.first_name}\n"
        f"🏆 سطح: {rank}\n"
        f"📨 پیام‌ها: {msg_count}\n"
        f"⭐ امتیاز: {points}\n"
        f"🎯 تا سطح بعدی: {50 - (msg_count % 50)} پیام",
        parse_mode="Markdown"
    )

# ========== راهنمای فارسی ==========
async def help_fa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """راهنمای کامل فارسی"""
    if not await check_auth(update, context):
        return
    
    help_text = """
🤖 **راهنمای کامل ربات برنامه‌نویسان NAQD**

**🔗 لینک‌ها:**
/links - لینک‌های مستقیم سایت‌های برنامه‌نویسی

**🔐 رمزنگاری و هش:**
/هش [md5|sha1|sha256] [متن] - ساخت هش
/بیس [رمز|رمزگشا] [متن] - ابزار Base64
/uuid - ساخت UUID جدید
/رمز [طول] - ساخت رمز عبور قوی

**🛠️ ابزارهای کاربردی:**
/زمان [timestamp|تاریخ] - تبدیل تایم‌استمپ
/رنگ [hex|rgb] - تبدیل رنگ
/اسکیوال [توضیح] - تولید SQL Query

**🐳 DevOps:**
/داکر [پایتون|نود|گو] - تولید Dockerfile

**📚 آموزش:**
/پایتون - نقشه راه پایتون
/مصاحبه - سوالات مصاحبه

**📊 آمار:**
/امار - آمار گروه
/رنک - کارت شما
/قرعه - قرعه‌کشی روزانه

**🔐 ورود:**
/login naqdbothack - ورود به ربات

**توسعه‌دهنده:** @AMIRSAMDERAKHSHAN
"""
    await update.message.reply_text(help_text, parse_mode="Markdown")

# ========== ردیابی پیام‌ها ==========
async def track_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ردیابی پیام‌ها برای آمار"""
    if update.message and update.message.text and not update.message.text.startswith('/'):
        if update.effective_user.id in authenticated_users:
            user_messages[update.effective_user.id] += 1
            user_points[update.effective_user.id] += 1

# ========== Callback Handlers ==========
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "links_menu":
        await links(query.message, context)
    elif query.data == "run_code_fa":
        await query.message.reply_text("💻 برای اجرای کد از دستور `/run` استفاده کنید.\nمثال: `/run python print('Hello')`", parse_mode="Markdown")
    elif query.data == "crypto_fa":
        await query.message.reply_text("🔐 ابزارهای رمزنگاری:\n• `/هش md5 متن`\n• `/بیس رمز متن`\n• `/uuid`\n• `/رمز 16`", parse_mode="Markdown")
    elif query.data == "db_fa":
        await query.message.reply_text("🗄️ ابزارهای دیتابیس:\n• `/اسکیوال users with id, name`", parse_mode="Markdown")
    elif query.data == "docker_fa":
        await query.message.reply_text("🐳 ابزارهای DevOps:\n• `/داکر پایتون`\n• `/داکر نود`", parse_mode="Markdown")
    elif query.data == "learn_fa":
        await query.message.reply_text("📚 آموزش:\n• `/پایتون` - نقشه راه\n• `/مصاحبه` - سوالات", parse_mode="Markdown")
    elif query.data == "utils_fa":
        await query.message.reply_text("🛠️ ابزارها:\n• `/زمان`\n• `/رنگ`\n• `/بیس`", parse_mode="Markdown")
    elif query.data == "stats_fa":
        await stats_fa(query.message, context)
    elif query.data == "game_fa":
        await query.message.reply_text("🎮 سرگرمی:\n• `/قرعه` - قرعه‌کشی\n• `/رنک` - سطح شما", parse_mode="Markdown")
    elif query.data == "help_fa":
        await help_fa(query.message, context)
    elif query.data == "next_question":
        await interview_fa(query.message, context)
    elif query.data.startswith("cat_"):
        await category_callback(update, context)
    elif query.data == "back_to_links":
        await back_to_links(update, context)

# ========== اجرای اصلی ==========
if __name__ == '__main__':
    application = ApplicationBuilder().token(TOKEN).build()
    
    # دستورات فارسی
    application.add_handler(CommandHandler('start', start_fa))
    application.add_handler(CommandHandler('help', help_fa))
    application.add_handler(CommandHandler('login', login))
    application.add_handler(CommandHandler('links', links))
    
    # ابزارهای فارسی
    application.add_handler(CommandHandler('هش', hash_fa))
    application.add_handler(CommandHandler('بیس', base64_fa))
    application.add_handler(CommandHandler('uuid', uuid_fa))
    application.add_handler(CommandHandler('رمز', password_fa))
    application.add_handler(CommandHandler('زمان', timestamp_fa))
    application.add_handler(CommandHandler('رنگ', color_fa))
    application.add_handler(CommandHandler('اسکیوال', sql_fa))
    application.add_handler(CommandHandler('داکر', dockerfile_fa))
    
    # آموزش فارسی
    application.add_handler(CommandHandler('پایتون', python_roadmap_fa))
    application.add_handler(CommandHandler('مصاحبه', interview_fa))
    
    # آمار فارسی
    application.add_handler(CommandHandler('امار', stats_fa))
    application.add_handler(CommandHandler('رنک', rank_fa))
    application.add_handler(CommandHandler('قرعه', lottery_fa))
    
    # دستورات انگلیسی (برای سازگاری)
    application.add_handler(CommandHandler('hash', hash_fa))
    application.add_handler(CommandHandler('base64', base64_fa))
    application.add_handler(CommandHandler('timestamp', timestamp_fa))
    application.add_handler(CommandHandler('color', color_fa))
    application.add_handler(CommandHandler('sql', sql_fa))
    application.add_handler(CommandHandler('dockerfile', dockerfile_fa))
    application.add_handler(CommandHandler('python', python_roadmap_fa))
    application.add_handler(CommandHandler('interview', interview_fa))
    application.add_handler(CommandHandler('stats', stats_fa))
    application.add_handler(CommandHandler('rank', rank_fa))
    application.add_handler(CommandHandler('lottery', lottery_fa))
    
    # ردیابی پیام
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, track_messages))
    
    # Callback
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # اجرا
    application.run_polling()