import os
import httpx
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
from database import get_or_create_user, get_balance, supabase

load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TRAFF_TOKEN = os.getenv("TRAFFMONETIZER_TOKEN")

# 1. بناء تطبيق البوت المستقر (تعطيل الـ Updater ليعمل بالويب-هوك فقط)
bot_app = Application.builder().token(TOKEN).updater(None).build()

app = FastAPI()

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
    return {"status": "Live Webhook Server is Alive"}

# 🚀 البوابة الرئيسية القياسية: استقبال البيانات وقذفها للمكافحة فوراً
@app.post("/webhook")
async def telegram_webhook(request: Request):
    try:
        data = await request.json()
        
        # هندسة الإرسال المباشر لـ المعالجات (Handlers) دون تجميد
        update = Update.de_json(data, bot_app.bot)
        await bot_app.initialize()  # ضمان فتح الذاكرة
        await bot_app.process_update(update)
        return {"status": "ok"}
    except Exception as e:
        print(f"Webhook Execution Error: {e}")
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
        return {"success": True, "new_balance": new_balance}
    except Exception:
        return {"success": True, "new_balance": get_balance(request.telegram_id)}

# 🤖 أمر الـ Start الرئيسي ونظام الإحالة الفيروسي
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

# تسجيل معالج الأوامر برمجياً في الماكينة الأساسية
bot_app.add_handler(CommandHandler("start", start))

if __name__ == "__main__":
    uvicorn.run("bot:app", host="0.0.0.0", port=8000, reload=False)
