import os
import httpx
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
from database import get_or_create_user, get_balance, supabase

load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TRAFF_TOKEN = os.getenv("TRAFFMONETIZER_TOKEN")
# 🌐 رابط سيرفر ريندر الخاص بك الذي أرسلته سابقاً
RENDER_URL = "https://onrender.com"

# تهيئة البوت لإصدارات بايثون وتليجرام الحديثة
bot_app = Application.builder().updater(None).token(TOKEN).build()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """تهيئة وتنشيط الـ Webhook فور إقلاع السيرفر سحابياً"""
    await bot_app.initialize()
    await bot_app.start()
    
    # ربط البوت برابط الـ Webhook السحابي رسمياً
    webhook_url = f"{RENDER_URL}/webhook"
    await bot_app.bot.set_webhook(url=webhook_url)
    print(f"✅ Webhook is live at: {webhook_url}")
    
    yield
    
    # 🟢 التصحيح البرمجي الآمن لإصدارات المكتبة الحديثة عند الإغلاق
    await bot_app.bot.delete_webhook()
    await bot_app.stop()
    await bot_app.shutdown() # تم تصحيح الاسم هنا لمنع خطأ AttributeError


app = FastAPI(lifespan=lifespan)

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
    return {"status": "Secure Webhook Server is Alive"}

# 🚀 نقطة الاستقبال الرئيسية لدفقات تليجرام
@app.post("/webhook")
async def telegram_webhook(request: Request):
    try:
        data = await request.json()
        update = Update.de_json(data, bot_app.bot)
        await bot_app.process_update(update)
        return {"status": "ok"}
    except Exception as e:
        print(f"Webhook Error: {e}")
        return {"status": "error"}

@app.post("/api/ping-mining")
async def ping_mining(request: MiningRequest):
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            headers = {"Authorization": f"Bearer {TRAFF_TOKEN}"} if TRAFF_TOKEN else {}
            await client.post("https://traffmonetizer.com", headers=headers)
            
        earned_amount = 0.0005 
        current_balance = get_balance(request.telegram_id)
        new_balance = current_balance + earned_amount
        
        supabase.table("app_users").update({"balance_usd": new_balance}).eq("telegram_id", request.telegram_id).execute()
        
        log_data = {
            "user_id": request.telegram_id,
            "mb_shared": 0.05, 
            "earnings": earned_amount
        }
        supabase.table("traffic_logs").insert(log_data).execute()
        
        return {"success": True, "new_balance": new_balance}
    except Exception as e:
        print(f"Mining Error: {e}")
        return {"success": True, "new_balance": get_balance(request.telegram_id)}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tg_user = update.effective_user
    get_or_create_user(tg_user.id, tg_user.username)
    
    referral_link = f"https://t.me{context.bot.username}?start={tg_user.id}"
    keyboard = [[InlineKeyboardButton("📱 فتح تطبيق التعدين وكسب المال", web_app={"url": "https://depin-telegram-project.vercel.app/"})]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"أهلاً بك يا {tg_user.first_name} في شبكة التعدين التشاركية! 🚀\n\n"
        f"🔗 رابط الإحالة الخاص بك هو:\n👉 `{referral_link}`",
        reply_markup=reply_markup, parse_mode="Markdown"
    )

bot_app.add_handler(CommandHandler("start", start))

if __name__ == "__main__":
    uvicorn.run("bot:app", host="0.0.0.0", port=8000, reload=False)
