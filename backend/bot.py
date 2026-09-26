import os
import asyncio
import shutil
from contextlib import asynccontextmanager
from urllib.parse import urlparse

from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from database import get_or_create_user

load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TRAFFMONETIZER_TOKEN = os.getenv("TRAFFMONETIZER_TOKEN", "").strip()
TRAFFMONETIZER_CONTAINER = "depin-traffmonetizer"
TRAFFMONETIZER_STATUS = "not_configured"
PRODUCTION_WEB_APP_URL = "https://depin-telegram-project.vercel.app/"
WEB_APP_URL = os.getenv("WEB_APP_URL", PRODUCTION_WEB_APP_URL).strip()
PORT = int(os.getenv("PORT", "8000"))

if not TOKEN:
    raise RuntimeError("Set TELEGRAM_BOT_TOKEN in backend/.env before starting the bot.")

if not WEB_APP_URL:
    raise RuntimeError("Set WEB_APP_URL in backend/.env to your public HTTPS Mini App URL.")

if urlparse(WEB_APP_URL).scheme != "https":
    raise RuntimeError("WEB_APP_URL must be a valid HTTPS URL for Telegram Mini App buttons.")

async def run_docker(*args: str) -> tuple[int, str]:
    process = await asyncio.create_subprocess_exec(
        "docker",
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.DEVNULL,
    )
    stdout, _ = await process.communicate()
    return process.returncode or 0, stdout.decode(errors="replace").strip()

async def start_traffmonetizer():
    global TRAFFMONETIZER_STATUS

    if not TRAFFMONETIZER_TOKEN:
        TRAFFMONETIZER_STATUS = "not_configured"
        return

    if not shutil.which("docker"):
        TRAFFMONETIZER_STATUS = "docker_unavailable"
        return

    code, running = await run_docker(
        "inspect", "--format={{.State.Running}}", TRAFFMONETIZER_CONTAINER
    )
    if code == 0:
        if running.lower() == "true":
            TRAFFMONETIZER_STATUS = "running"
            return
        code, _ = await run_docker("start", TRAFFMONETIZER_CONTAINER)
    else:
        code, _ = await run_docker(
            "run",
            "-d",
            "--restart",
            "unless-stopped",
            "--name",
            TRAFFMONETIZER_CONTAINER,
            "traffmonetizer/cli_v2",
            "start",
            "accept",
            "--token",
            TRAFFMONETIZER_TOKEN,
            "--device-name",
            "depin-telegram-project",
        )

    TRAFFMONETIZER_STATUS = "running" if code == 0 else "error"

@asynccontextmanager
async def telegram_lifespan(fastapi_app: FastAPI):
    await start_traffmonetizer()
    telegram_app = Application.builder().token(TOKEN).build()
    telegram_app.add_handler(CommandHandler("start", start))
    await telegram_app.initialize()
    await telegram_app.updater.start_polling()
    await telegram_app.start()
    try:
        yield
    finally:
        await telegram_app.updater.stop()
        await telegram_app.stop()
        await telegram_app.shutdown()

app = FastAPI(lifespan=telegram_lifespan)

# 🛡️ السماح للواجهة المرفوعة على Vercel بالاتصال بالسيرفر دون حظر (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def home():
    return {"status": "Server is running securely"}

@app.get("/api/traffmonetizer/status")
async def traffmonetizer_status():
    if not TRAFFMONETIZER_TOKEN:
        return {"status": "not_configured"}
    if not shutil.which("docker"):
        return {"status": "docker_unavailable"}

    code, running = await run_docker(
        "inspect", "--format={{.State.Running}}", TRAFFMONETIZER_CONTAINER
    )
    if code == 0:
        return {"status": "running" if running.lower() == "true" else "not_running"}
    if TRAFFMONETIZER_STATUS == "error":
        return {"status": "error"}
    return {"status": "not_running"}

# --- أكواد وأوامر بوت التلجرام ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tg_user = update.effective_user
    get_or_create_user(tg_user.id, tg_user.username)
    
    keyboard = [
        [InlineKeyboardButton("📱 فتح تطبيق التعدين وكسب المال", web_app={"url": WEB_APP_URL})]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"أهلاً بك يا {tg_user.first_name} في شبكة التشغيل التشاركية! 🚀\n\n"
        f"اضغط على الزر أدناه لمتابعة حالة خدمة TraffMonetizer المشتركة للمشروع.",
        reply_markup=reply_markup
    )

# --- دالة التشغيل الرئيسية والحديثة لتشغيل السيرفر والبوت معاً ---
async def start_all():
    config = uvicorn.Config(app, host="0.0.0.0", port=PORT, loop="asyncio")
    server = uvicorn.Server(config)
    await server.serve()

if __name__ == "__main__":
    # تشغيل حلقة الأحداث بشكل آمن ومتوافق مع إصدارات بايثون الحديثة
    asyncio.run(start_all())
