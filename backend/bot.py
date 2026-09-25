import os
import asyncio
import httpx
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
from database import get_or_create_user, get_balance, supabase

load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
PROXY_URL = os.getenv("PACKETSTREAM_PROXY", "proxy.packetstream.io:3128")
API_KEY = os.getenv("PACKETSTREAM_API_KEY")

app = FastAPI()

# 🛡️ السماح للواجهة المرفوعة على Vercel بالاتصال بالسيرفر دون حظر (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class MiningRequest(BaseModel):
    telegram_id: int

@app.get("/")
def home():
    return {"status": "Server is running securely"}

@app.post("/api/ping-mining")
async def ping_mining(request: MiningRequest):
    """رابط يستقبل إشارة التعدين من الواجهة ويحسب الأرباح عبر البروكسي"""
    try:
        proxy_auth = f"http://{API_KEY}@{PROXY_URL}" if API_KEY else None
        
        async with httpx.AsyncClient(proxies=proxy_auth, timeout=5.0) as client:
            response = await client.get("https://google.com")
            bytes_transferred = len(response.content) + 500
        
        earned_amount = 0.0005 
        
        current_balance = get_balance(request.telegram_id)
        new_balance = current_balance + earned_amount
        
        supabase.table("app_users").update({"balance_usd": new_balance}).eq("telegram_id", request.telegram_id).execute()
        
        log_data = {
            "user_id": request.telegram_id,
            "mb_shared": round(bytes_transferred / (1024 * 1024), 4),
            "earnings": earned_amount
        }
        supabase.table("traffic_logs").insert(log_data).execute()
        
        return {"success": True, "new_balance": new_balance}
        
    except Exception as e:
        print(f"Mining Error: {e}")
        raise HTTPException(status_code=500, detail="فشلت عملية معالجة البيانات، تحقق من اتصال الشبكة")

# --- أكواد وأوامر بوت التلجرام ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tg_user = update.effective_user
    get_or_create_user(tg_user.id, tg_user.username)
    
    keyboard = [
        [InlineKeyboardButton("📱 فتح تطبيق التعدين وكسب المال", web_app={"url": "https://depin-telegram-project.vercel.app/"})]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"أهلاً بك يا {tg_user.first_name} في شبكة التشغيل التشاركية! 🚀\n\n"
        f"اضغط على الزر أدناه لفتح واجهة التطبيق والبدء بحصد الأرباح الحقيقية بالدولار.",
        reply_markup=reply_markup
    )

async def main_bot():
    bot_app = Application.builder().token(TOKEN).build()
    bot_app.add_handler(CommandHandler("start", start))
    await bot_app.initialize()
    await bot_app.start()
    await bot_app.updater.start_polling()

# --- دالة التشغيل الرئيسية والحديثة لتشغيل السيرفر والبوت معاً ---
async def start_all():
    # 1. تشغيل البوت في الخلفية
    await main_bot()
    
    # 2. تشغيل سيرفر الـ API لـ FastAPI
    config = uvicorn.Config(app, host="0.0.0.0", port=8000, loop="asyncio")
    server = uvicorn.Server(config)
    await server.serve()

if __name__ == "__main__":
    # تشغيل حلقة الأحداث بشكل آمن ومتوافق مع إصدارات بايثون الحديثة
    asyncio.run(start_all())
