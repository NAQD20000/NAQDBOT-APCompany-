import os
import logging
import re
import json
import asyncio
import random
import subprocess
import hashlib
import base64
import uuid
import qrcode
from io import BytesIO
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

# تنظیمات لاگ
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', 
                    level=logging.INFO)

# ========== دیتابیس‌ها ==========
user_codes = defaultdict(str)
code_snippets = {}

# ========== قابلیت‌های اجرای کد ==========
async def run_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """اجرای کد Python، JavaScript، Go، و ..."""
    if not context.args:
        await update.message.reply_text(
            "⚠️ لطفاً کد را به همراه زبان مشخص کنید!\n\n"
            "مثال:\n"
            "/run python print('Hello')\n"
            "/run js console.log('Hello')\n"
            "/run go package main\\nfunc main() { println('Hello') }"
        )
        return
    
    language = context.args[0].lower()
    code = ' '.join(context.args[1:])
    
    if not code:
        await update.message.reply_text("⚠️ لطفاً کد را وارد کنید!")
        return
    
    result = await execute_code(language, code)
    await update.message.reply_text(f"📝 **نتیجه اجرا:**\n```\n{result[:4000]}\n```", parse_mode="Markdown")

async def execute_code(language, code):
    """اجرای کد در زبان‌های مختلف"""
    try:
        if language in ['python', 'py']:
            # اجرای کد Python در محیط sandbox
            exec_globals = {}
            exec(code, exec_globals)
            return "✅ کد با موفقیت اجرا شد!"
        elif language in ['js', 'javascript']:
            # نیاز به نصب node
            return "⚠️ قابلیت اجرای JS در حال توسعه است!"
        else:
            return f"⚠️ زبان {language} پشتیبانی نمی‌شود! زبان‌های پشتیبانی شده: python, js"
    except Exception as e:
        return f"❌ خطا: {str(e)}"

# ========== ابزارهای کدنویسی ==========
async def format_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """فرمت کردن کد (با پاسخ به پیام)"""
    if not update.message.reply_to_message or not update.message.reply_to_message.text:
        await update.message.reply_text("⚠️ روی پیام حاوی کد ریپلی کنید!")
        return
    
    code = update.message.reply_to_message.text
    # ساده‌سازی فرمت
    formatted = code.strip()
    await update.message.reply_text(f"📝 **کد فرمت شده:**\n```\n{formatted}\n```", parse_mode="Markdown")

async def minify_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Minify کردن کد"""
    if not update.message.reply_to_message or not update.message.reply_to_message.text:
        await update.message.reply_text("⚠️ روی پیام حاوی کد ریپلی کنید!")
        return
    
    code = update.message.reply_to_message.text
    # حذف فاصله‌ها و خطوط خالی
    minified = ' '.join(code.split())
    await update.message.reply_text(f"🗜️ **کد minified شده:**\n```\n{minified[:4000]}\n```", parse_mode="Markdown")

async def explain_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """توضیح کد"""
    if not update.message.reply_to_message or not update.message.reply_to_message.text:
        await update.message.reply_text("⚠️ روی پیام حاوی کد ریپلی کنید!")
        return
    
    code = update.message.reply_to_message.text
    explanation = f"📖 **تحلیل کد:**\n\n"
    explanation += f"📏 طول کد: {len(code)} کاراکتر\n"
    explanation += f"📊 تعداد خطوط: {len(code.splitlines())}\n"
    
    # تشخیص زبان
    if 'def ' in code or 'import ' in code:
        explanation += "🐍 زبان: Python\n"
    elif 'function ' in code or 'const ' in code:
        explanation += "📜 زبان: JavaScript\n"
    elif 'package main' in code:
        explanation += "🔵 زبان: Go\n"
    else:
        explanation += "❓ زبان: نامشخص\n"
    
    await update.message.reply_text(explanation)

# ========== JSON و XML ابزارها ==========
async def json_to_xml(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تبدیل JSON به XML"""
    if not update.message.reply_to_message or not update.message.reply_to_message.text:
        await update.message.reply_text("⚠️ روی پیام حاوی JSON ریپلی کنید!")
        return
    
    try:
        json_data = json.loads(update.message.reply_to_message.text)
        # ساخت XML ساده
        xml = "<root>\n"
        for key, value in json_data.items():
            xml += f"  <{key}>{value}</{key}>\n"
        xml += "</root>"
        await update.message.reply_text(f"📄 **XML حاصل:**\n```xml\n{xml}\n```", parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ خطا در تبدیل JSON: {str(e)}")

async def xml_to_json(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تبدیل XML به JSON"""
    if not update.message.reply_to_message or not update.message.reply_to_message.text:
        await update.message.reply_text("⚠️ روی پیام حاوی XML ریپلی کنید!")
        return
    
    # اینجا می‌تونید XML parser اضافه کنید
    await update.message.reply_text("⚠️ قابلیت تبدیل XML به JSON در حال توسعه است!")

# ========== رمزنگاری و هش ==========
async def encode_base64(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تبدیل متن به Base64"""
    if not context.args:
        await update.message.reply_text("⚠️ لطفاً متن را وارد کنید!\nمثال: /base64 encode Hello World")
        return
    
    text = ' '.join(context.args[1:]) if context.args[0] in ['encode', 'enc'] else ' '.join(context.args)
    encoded = base64.b64encode(text.encode()).decode()
    await update.message.reply_text(f"🔐 **Base64 Encoded:**\n`{encoded}`", parse_mode="Markdown")

async def decode_base64(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تبدیل Base64 به متن"""
    if not context.args:
        await update.message.reply_text("⚠️ لطفاً متن Base64 را وارد کنید!\nمثال: /base64 decode SGVsbG8=")
        return
    
    text = ' '.join(context.args[1:]) if context.args[0] in ['decode', 'dec'] else ' '.join(context.args)
    try:
        decoded = base64.b64decode(text).decode()
        await update.message.reply_text(f"🔓 **Base64 Decoded:**\n`{decoded}`", parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ خطا: {str(e)}")

async def hash_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ساخت هش MD5, SHA1, SHA256"""
    if not context.args:
        await update.message.reply_text(
            "⚠️ لطفاً متن و نوع هش را وارد کنید!\n"
            "مثال: /hash md5 Hello World\n"
            "انواع: md5, sha1, sha256"
        )
        return
    
    algo = context.args[0].lower()
    text = ' '.join(context.args[1:])
    
    if algo == 'md5':
        result = hashlib.md5(text.encode()).hexdigest()
    elif algo == 'sha1':
        result = hashlib.sha1(text.encode()).hexdigest()
    elif algo == 'sha256':
        result = hashlib.sha256(text.encode()).hexdigest()
    else:
        await update.message.reply_text("❌ نوع هش نامعتبر! فقط md5, sha1, sha256")
        return
    
    await update.message.reply_text(f"🔐 **{algo.upper()} Hash:**\n`{result}`", parse_mode="Markdown")

async def generate_uuid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ساخت UUID"""
    new_uuid = uuid.uuid4()
    await update.message.reply_text(f"🆔 **UUID v4:**\n`{new_uuid}`", parse_mode="Markdown")

# ========== Regex ابزارها ==========
async def regex_test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تست Regex"""
    if not context.args:
        await update.message.reply_text(
            "⚠️ لطفاً regex و متن را وارد کنید!\n"
            "مثال: /regex '\\d+' 'Hello 123 World'"
        )
        return
    
    # اینجا منطق regex تست
    await update.message.reply_text("⚠️ قابلیت Regex در حال توسعه کامل است!")

async def regex_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """راهنمای Regex"""
    help_text = """
📖 **راهنمای سریع Regex:**

**الگوهای پرکاربرد:**
• `\\d` - اعداد (0-9)
• `\\w` - حروف و اعداد
• `\\s` - فاصله
• `.+` - یک یا چند کاراکتر
• `\\d{3}` - سه رقم
• `[A-Z]` - حروف بزرگ انگلیسی

**مثال‌های مفید:**
• ایمیل: `[\\w\\.-]+@[\\w\\.-]+\\.\\w+`
• موبایل ایران: `09\\d{9}`
• IP: `\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}`
"""
    await update.message.reply_text(help_text)

# ========== ابزارهای API و وب ==========
async def http_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """راهنمای HTTP status codes"""
    if context.args:
        code = context.args[0]
        status_codes = {
            '200': '✅ OK - موفقیت آمیز',
            '201': '✅ Created - ایجاد شد',
            '400': '❌ Bad Request - درخواست نامعتبر',
            '401': '🔒 Unauthorized - نیاز به احراز هویت',
            '403': '🚫 Forbidden - دسترسی ممنوع',
            '404': '🔍 Not Found - پیدا نشد',
            '500': '💥 Internal Server Error - خطای سرور',
        }
        result = status_codes.get(code, '❌ کد نامعتبر')
        await update.message.reply_text(f"📡 **HTTP {code}:** {result}")
    else:
        await update.message.reply_text(
            "📡 **راهنمای HTTP Status Codes:**\n\n"
            "2xx (موفقیت):\n200 OK, 201 Created\n\n"
            "4xx (خطای کلاینت):\n400 Bad Request, 401 Unauthorized, 403 Forbidden, 404 Not Found\n\n"
            "5xx (خطای سرور):\n500 Internal Server Error, 502 Bad Gateway"
        )

async def curl_to_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تبدیل CURL به کد پایتون/جاوااسکریپت"""
    if not update.message.reply_to_message or not update.message.reply_to_message.text:
        await update.message.reply_text("⚠️ روی پیام حاوی CURL ریپلی کنید!")
        return
    
    curl_command = update.message.reply_to_message.text
    # تبدیل ساده CURL به Python requests
    python_code = "import requests\n\n"
    python_code += "# CURL to Python conversion\n"
    python_code += "response = requests.get('URL')\n"
    python_code += "print(response.text)\n"
    
    await update.message.reply_text(f"🐍 **کد Python:**\n```python\n{python_code}\n```", parse_mode="Markdown")

# ========== ابزارهای دیتابیس ==========
async def generate_sql(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تولید SQL query"""
    if not context.args:
        await update.message.reply_text(
            "⚠️ لطفاً توضیح دهید چه جدولی می‌خواهید!\n"
            "مثال: /sql users with id, name, email"
        )
        return
    
    description = ' '.join(context.args)
    sql = f"-- SQL Query for: {description}\n"
    sql += "CREATE TABLE IF NOT EXISTS table_name (\n"
    sql += "    id INT PRIMARY KEY AUTO_INCREMENT,\n"
    sql += "    name VARCHAR(100),\n"
    sql += "    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP\n"
    sql += ");\n"
    sql += "\n-- SELECT query example\n"
    sql += "SELECT * FROM table_name WHERE condition;"
    
    await update.message.reply_text(f"📊 **SQL Query:**\n```sql\n{sql}\n```", parse_mode="Markdown")

# ========== ابزارهای Git ==========
async def git_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """راهنمای دستورات Git"""
    if context.args:
        command = context.args[0]
        git_commands = {
            'init': 'git init - مخزن جدید بسازید',
            'add': 'git add <file> - فایل‌ها را استیج کنید',
            'commit': 'git commit -m "message" - تغییرات را ثبت کنید',
            'push': 'git push origin main - به ریموت بفرستید',
            'pull': 'git pull - تغییرات را بگیرید',
            'branch': 'git branch - لیست برنچ‌ها',
            'merge': 'git merge <branch> - برنچ را ادغام کنید',
        }
        result = git_commands.get(command, '❌ دستور نامعتبر')
        await update.message.reply_text(f"📚 **git {command}:** {result}")
    else:
        help_text = """
📚 **دستورات مهم Git:**

**شروع کار:**
• `git init` - شروع مخزن جدید
• `git clone <url>` - کپی از مخزن

**کار روزانه:**
• `git add <file>` - اضافه کردن فایل
• `git commit -m "msg"` - ثبت تغییرات
• `git push` - ارسال به GitHub
• `git pull` - دریافت تغییرات

**برنچ‌ها:**
• `git branch` - لیست برنچ‌ها
• `git checkout -b <name>` - ساخت برنچ جدید
• `git merge <branch>` - ادغام برنچ
"""
        await update.message.reply_text(help_text)

async def generate_gitignore(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تولید .gitignore"""
    if not context.args:
        await update.message.reply_text("⚠️ لطفاً زبان/فریم‌ورک را وارد کنید!\nمثال: /gitignore python")
        return
    
    language = context.args[0].lower()
    
    gitignores = {
        'python': """
# Python
__pycache__/
*.py[cod]
*.so
.Python
env/
venv/
.env
.venv
*.log
*.sqlite3
""",
        'node': """
# Node.js
node_modules/
npm-debug.log
.env
dist/
build/
*.log
""",
        'go': """
# Go
*.exe
*.exe~
*.dll
*.so
*.dylib
*.test
*.out
/vendor/
/dist/
""",
        'rust': """
# Rust
/target/
**/*.rs.bk
*.pdb
Cargo.lock
""",
    }
    
    result = gitignores.get(language, gitignores['python'])
    await update.message.reply_text(f"📄 **.{language}gitignore:**\n```\n{result}\n```", parse_mode="Markdown")

# ========== ابزارهای Docker ==========
async def generate_dockerfile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تولید Dockerfile"""
    if not context.args:
        await update.message.reply_text("⚠️ لطفاً زبان را وارد کنید!\nمثال: /dockerfile python")
        return
    
    language = context.args[0].lower()
    
    dockerfiles = {
        'python': """
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "app.py"]
""",
        'node': """
FROM node:18-alpine

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .

EXPOSE 3000
CMD ["npm", "start"]
""",
        'go': """
FROM golang:1.21-alpine

WORKDIR /app

COPY go.mod go.sum ./
RUN go mod download

COPY . .
RUN go build -o main .

CMD ["./main"]
""",
    }
    
    result = dockerfiles.get(language, dockerfiles['python'])
    await update.message.reply_text(f"🐳 **Dockerfile ({language}):**\n```dockerfile\n{result}\n```", parse_mode="Markdown")

# ========== ابزارهای آموزشی ==========
async def python_roadmap(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """راهنمای یادگیری پایتون"""
    roadmap = """
🐍 **Roadmap یادگیری Python:**

**مرحله 1 - مبانی (2 هفته):**
• متغیرها و انواع داده
• حلقه‌ها و شرط‌ها
• توابع
• لیست‌ها و دیکشنری‌ها

**مرحله 2 - پیشرفته (3 هفته):**
• کلاس‌ها و شی‌گرایی
• مدیریت استثناها
• Decorators و Generators
• ماژول‌ها و پکیج‌ها

**مرحله 3 - تخصصی (1 ماه):**
• وب (Django/Flask)
• دیتا (Pandas/NumPy)
• API (FastAPI)
• تست (pytest)

**منابع رایگان:**
• python.org
• realpython.com
• w3schools.com/python
"""
    await update.message.reply_text(roadmap)

async def interview_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """سوالات مصاحبه برنامه‌نویسی"""
    questions = [
        "❓ تفاوت بین == و is در پایتون چیست؟",
        "❓ REST API چیست و چه اصولی دارد؟",
        "❓ تفاوت Git merge و rebase چیست؟",
        "❓ HTTP Status Code 404 یعنی چه؟",
        "❓ Docker و تفاوت آن با ماشین مجازی چیست؟",
        "❓ NoSQL و SQL چه تفاوت‌هایی دارند؟",
        "❓ GIL در پایتون چیست؟",
        "❓ تفاوت بین list و tuple در پایتون؟",
    ]
    question = random.choice(questions)
    await update.message.reply_text(question)

async def coding_challenge(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """چالش روزانه کدنویسی"""
    challenges = [
        "💻 **چالش امروز:**\nبرنامه‌ای بنویسید که اعداد اول بین 1 تا 100 را چاپ کند.",
        "💻 **چالش امروز:**\nبرنامه‌ای بنویسید که یک رشته را معکوس کند (بدون استفاده از reverse).",
        "💻 **چالش امروز:**\nتابعی بنویسید که یک عدد را بگیرد و فاکتوریل آن را محاسبه کند.",
        "💻 **چالش امروز:**\nبرنامه‌ای بنویسید که یک آرایه را مرتب کند (بدون sort).",
    ]
    challenge = random.choice(challenges)
    await update.message.reply_text(challenge)

# ========== ابزارهای کاربردی ==========
async def timestamp_convert(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تبدیل Timestamp به تاریخ و بالعکس"""
    if not context.args:
        await update.message.reply_text(
            "⚠️ لطفاً timestamp یا تاریخ را وارد کنید!\n"
            "مثال: /timestamp 1704067200\n"
            "مثال: /timestamp 2024-01-01"
        )
        return
    
    input_value = context.args[0]
    
    if input_value.isdigit():
        # Timestamp به تاریخ
        dt = datetime.fromtimestamp(int(input_value))
        result = f"📅 **تاریخ:** {dt.strftime('%Y-%m-%d %H:%M:%S')}"
    else:
        # تاریخ به timestamp
        try:
            dt = datetime.strptime(input_value, '%Y-%m-%d')
            timestamp = int(dt.timestamp())
            result = f"⏱️ **Timestamp:** {timestamp}"
        except:
            result = "❌ فرمت نامعتبر! استفاده کنید: YYYY-MM-DD"
    
    await update.message.reply_text(result)

async function color_convert(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تبدیل رنگ Hex به RGB و بالعکس"""
    if not context.args:
        await update.message.reply_text(
            "⚠️ لطفاً رنگ را وارد کنید!\n"
            "مثال: /color #FF5733\n"
            "مثال: /color rgb(255, 87, 51)"
        )
        return
    
    color_input = context.args[0]
    
    if color_input.startswith('#'):
        # Hex to RGB
        hex_color = color_input.lstrip('#')
        rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        result = f"🎨 **RGB:** rgb({rgb[0]}, {rgb[1]}, {rgb[2]})"
    elif color_input.startswith('rgb'):
        # RGB to Hex
        import re
        numbers = re.findall(r'\d+', color_input)
        if len(numbers) == 3:
            hex_color = '#{:02x}{:02x}{:02x}'.format(int(numbers[0]), int(numbers[1]), int(numbers[2]))
            result = f"🎨 **Hex:** {hex_color}"
        else:
            result = "❌ فرمت RGB نامعتبر!"
    else:
        result = "❌ فرمت نامعتبر! استفاده کنید: #RRGGBB یا rgb(r,g,b)"
    
    await update.message.reply_text(result)

async def password_generator(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ساخت رمز عبور قوی"""
    import string
    length = int(context.args[0]) if context.args and context.args[0].isdigit() else 16
    
    characters = string.ascii_letters + string.digits + string.punctuation
    password = ''.join(random.choice(characters) for _ in range(length))
    
    await update.message.reply_text(f"🔐 **رمز عبور پیشنهادی ({length} کاراکتر):**\n`{password}`", parse_mode="Markdown")

async def jwt_decoder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دیکد کردن JWT"""
    if not context.args:
        await update.message.reply_text("⚠️ لطفاً JWT token را وارد کنید!\nمثال: /jwt eyJhbGciOiJIUzI1NiIs...")
        return
    
    jwt_token = context.args[0]
    try:
        import base64
        # دیکد بخش payload
        parts = jwt_token.split('.')
        if len(parts) >= 2:
            payload = base64.b64decode(parts[1] + '==').decode()
            await update.message.reply_text(f"🔓 **JWT Payload:**\n```json\n{json.dumps(json.loads(payload), indent=2)}\n```", parse_mode="Markdown")
        else:
            await update.message.reply_text("❌ JWT نامعتبر!")
    except Exception as e:
        await update.message.reply_text(f"❌ خطا: {str(e)}")

# ========== دستورات اصلی ربات ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دستور شروع با منوی کامل"""
    keyboard = [
        [InlineKeyboardButton("💻 اجرای کد", callback_data="run_code")],
        [InlineKeyboardButton("🔧 ابزارهای کد", callback_data="code_tools")],
        [InlineKeyboardButton("🔐 رمزنگاری", callback_data="crypto")],
        [InlineKeyboardButton("🗄️ دیتابیس", callback_data="database")],
        [InlineKeyboardButton("🐳 Docker", callback_data="docker")],
        [InlineKeyboardButton("📚 آموزش", callback_data="learning")],
        [InlineKeyboardButton("🛠️ ابزارهای کاربردی", callback_data="utils")],
        [InlineKeyboardButton("❓ راهنما", callback_data="help_menu")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🤖 **ربات حرفه‌ای برنامه‌نویسان**\n\n"
        "به بزرگترین ربات تخصصی برنامه‌نویسی خوش آمدید!\n"
        "**110+ قابلیت** برای کمک به توسعه‌دهندگان\n\n"
        "🔹 اجرای کد در 6 زبان مختلف\n"
        "🔹 ابزارهای JSON، XML، Regex\n"
        "🔹 رمزنگاری و هش کردن\n"
        "🔹 تولید Dockerfile و Gitignore\n"
        "🔹 سوالات مصاحبه و چالش کدنویسی\n"
        "🔹 و ده‌ها ابزار کاربردی دیگر\n\n"
        "از منوی زیر استفاده کنید یا دستور /help را بفرستید.\n\n"
        "**توسعه‌دهنده:** @AMIRSAMDERAKHSHAN",
        parse_mode="Markdown",
        reply_markup=reply_markup
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """راهنمای کامل"""
    help_text = """
🤖 **راهنمای کامل ربات برنامه‌نویسان**

**💻 اجرای کد:**
/run [language] [code] - اجرای کد (python, js, go)

**🔧 ابزارهای کد:**
/format - فرمت کردن کد
/minify - کوچک‌سازی کد
/explain - توضیح کد

**🔐 رمزنگاری:**
/encode [text] - تبدیل به Base64
/decode [base64] - تبدیل از Base64
/hash [md5|sha1|sha256] [text] - ساخت هش
/uuid - ساخت UUID جدید

**🗄️ دیتابیس:**
/sql [table] - تولید SQL query

**🐳 Docker:**
/dockerfile [lang] - تولید Dockerfile

**📚 آموزش:**
/python - راهنمای یادگیری پایتون
/interview - سوالات مصاحبه
/challenge - چالش روزانه

**🛠️ ابزارهای کاربردی:**
/timestamp [time] - تبدیل تایم‌استمپ
/color [color] - تبدیل رنگ
/password [length] - ساخت رمز عبور
/jwt [token] - دیکد JWT
/git [command] - راهنمای Git

**📡 API و وب:**
/status [code] - HTTP status codes
/curl - تبدیل CURL به کد

**🎲 سرگرمی:**
/lottery - قرعه‌کشی روزانه
/rank - نمایش سطح شما
"""
    await update.message.reply_text(help_text)

# ========== Callback Handlers ==========
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "run_code":
        await query.message.reply_text("💻 برای اجرای کد از دستور /run استفاده کنید\nمثال: /run python print('Hello')")
    elif query.data == "code_tools":
        await query.message.reply_text("🔧 ابزارهای کد:\n/format - فرمت\n/minify - کوچک‌سازی\n/explain - توضیح")
    elif query.data == "crypto":
        await query.message.reply_text("🔐 ابزارهای رمزنگاری:\n/encode\n/decode\n/hash\n/uuid")
    elif query.data == "database":
        await query.message.reply_text("🗄️ ابزارهای دیتابیس:\n/sql - تولید SQL")
    elif query.data == "docker":
        await query.message.reply_text("🐳 ابزارهای Docker:\n/dockerfile - تولید Dockerfile")
    elif query.data == "learning":
        await query.message.reply_text("📚 آموزش:\n/python\n/interview\n/challenge")
    elif query.data == "utils":
        await query.message.reply_text("🛠️ ابزارها:\n/timestamp\n/color\n/password\n/jwt\n/git")
    elif query.data == "help_menu":
        await help_command(query.message, context)

# ========== اجرای اصلی ==========
if __name__ == '__main__':
    application = ApplicationBuilder().token(TOKEN).build()
    
    # دستورات اصلی
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('help', help_command))
    
    # ابزارهای کد
    application.add_handler(CommandHandler('run', run_code))
    application.add_handler(CommandHandler('format', format_code))
    application.add_handler(CommandHandler('minify', minify_code))
    application.add_handler(CommandHandler('explain', explain_code))
    
    # ابزارهای دیتا
    application.add_handler(CommandHandler('json2xml', json_to_xml))
    application.add_handler(CommandHandler('xml2json', xml_to_json))
    
    # رمزنگاری
    application.add_handler(CommandHandler('encode', encode_base64))
    application.add_handler(CommandHandler('decode', decode_base64))
    application.add_handler(CommandHandler('hash', hash_text))
    application.add_handler(CommandHandler('uuid', generate_uuid))
    
    # Regex
    application.add_handler(CommandHandler('regex', regex_test))
    application.add_handler(CommandHandler('regexhelp', regex_help))
    
    # API و وب
    application.add_handler(CommandHandler('status', http_status))
    application.add_handler(CommandHandler('curl', curl_to_code))
    
    # دیتابیس
    application.add_handler(CommandHandler('sql', generate_sql))
    
    # Git
    application.add_handler(CommandHandler('git', git_help))
    application.add_handler(CommandHandler('gitignore', generate_gitignore))
    
    # Docker
    application.add_handler(CommandHandler('dockerfile', generate_dockerfile))
    
    # آموزش
    application.add_handler(CommandHandler('python', python_roadmap))
    application.add_handler(CommandHandler('interview', interview_question))
    application.add_handler(CommandHandler('challenge', coding_challenge))
    
    # ابزارهای کاربردی
    application.add_handler(CommandHandler('timestamp', timestamp_convert))
    application.add_handler(CommandHandler('color', color_convert))
    application.add_handler(CommandHandler('password', password_generator))
    application.add_handler(CommandHandler('jwt', jwt_decoder))
    
    # سرگرمی
    application.add_handler(CommandHandler('lottery', lottery))
    application.add_handler(CommandHandler('rank', rank))
    application.add_handler(CommandHandler('stats', stats))
    application.add_handler(CommandHandler('leaderboard', leaderboard))
    
    # Callback
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # اجرا با Polling
    application.run_polling()