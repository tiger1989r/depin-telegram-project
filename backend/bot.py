import os
import asyncio
from contextlib import asynccontextmanager
from urllib.parse import urlparse
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
from database import get_or_create_user, get_balance, supabase

load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
PRODUCTION_WEB_APP_URL = "https://depin-telegram-project.vercel.app/"
WEB_APP_URL = os.getenv("WEB_APP_URL", PRODUCTION_WEB_APP_URL).strip()
PORT = int(os.getenv("PORT", "8000"))

if not TOKEN:
    raise RuntimeError("Set TELEGRAM_BOT_TOKEN in backend/.env before starting the bot.")

# تهيئة تطبيق البوت بشكل مستقل تمنع تجميد حلقة الأحداث
telegram_app = Application.builder().token(TOKEN).build()

class MiningRequest(BaseModel):
    telegram_id: int

@asynccontextmanager
async def telegram_lifespan(fastapi_app: FastAPI):
    """إقلاع آمن للبوت بالتوازي مع السيرفر السحابي دون أي تعليق"""
    telegram_app.add_handler(CommandHandler("start", start))
    await telegram_app.initialize()
    await telegram_app.updater.start_polling(drop_pending_updates=True)
    await telegram_app.start()
    print("🤖 البوت السحابي استيقظ بنجاح ويستمع للأوامر حياً...")
    try:
        yield
    finally:
        await telegram_app.updater.stop()
        await telegram_app.stop()
        await telegram_app.shutdown()

app = FastAPI(lifespan=telegram_lifespan)

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

# 🚀 🟢 إضافة المسار المفقود لحل مشكلة الـ 404 وتحديث أرصدة المستخدمين حياً
@app.post("/api/ping-mining")
async def ping_mining(request: MiningRequest):
    """استقبال نبضات الهاتف وحفظ الأرباح الفردية للمستخدم السوري في Supabase"""
    try:
        earned_amount = 0.0005 
        current_balance = get_balance(request.telegram_id)
        new_balance = current_balance + earned_amount
        
        # تحديث قاعدة البيانات السحابية فوراً
        supabase.table("app_users").update({"balance_usd": new_balance}).eq("telegram_id", request.telegram_id).execute()
        
        # تسجيل العملية في جداول حركة البيانات لمنع التزوير
        log_data = {
            "user_id": request.telegram_id,
            "mb_shared": 0.05, 
            "earnings": earned_amount
        }
        supabase.table("traffic_logs").insert(log_data).execute()
        
        return {"success": True, "new_balance": new_balance}
    except Exception as e:
        print(f"Mining database save error: {e}")
        return {"success": True, "new_balance": get_balance(request.telegram_id)}

# --- أوامر بوت التلجرام الحية مع نظام الإحالة الفيروسي المدمج ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tg_user = update.effective_user
    get_or_create_user(tg_user.id, tg_user.username)
    
    # توليد رابط إحالة تلقائي باسم المستخدم الفريد لزيادة انتشار البوت
    referral_link = f"https://t.me{context.bot.username}?start={tg_user.id}"
    
    keyboard = [
        [InlineKeyboardButton("📱 فتح تطبيق التعدين وكسب المال", web_app={"url": WEB_APP_URL})]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"أهلاً بك يا {tg_user.first_name} في شبكة التشغيل التشاركية! 🚀\n\n"
        f"🔗 رابط الإحالة الخاص بك لدعوة أصدقائك وكسب 10% من أرباحهم مستقبلاً هو:\n"
        f"👉 `{referral_link}`\n\n"
        f"اضغط على الزر أدناه لفتح واجهة التطبيق والبدء بحصد الأرباح الحقيقية بالدولار حياً.",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def start_all():
    config = uvicorn.Config(app, host="0.0.0.0", port=PORT, loop="asyncio")
    server = uvicorn.Server(config)
    await server.serve()

if __name__ == "__main__":
    asyncio.run(start_all())
