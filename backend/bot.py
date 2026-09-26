import os
import asyncio
import httpx
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
# 🟢 رابط سيرفرك الحقيقي الدائم على Render
RENDER_URL = "https://onrender.com" 

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

# تهيئة تطبيق البوت بشكل عالمي
bot_app = Application.builder().token(TOKEN).build()

@app.get("/")
def home():
    return {"status": "Server is running securely"}

# 🚀 رابط الـ Webhook المستهدف الذي سيرسل له التلجرام الرسائل حياً
@app.post("/webhook")
async def telegram_webhook(request: Request):
    """استقبال الرسائل من التلجرام وتمريرها لكود البوت مباشرة"""
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
        raise HTTPException(status_code=500, detail="Error")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tg_user = update.effective_user
    referrer_id = None
    if context.args:
        try:
            referrer_id = int(context.args)
            if referrer_id == tg_user.id:
                referrer_id = None
        except ValueError:
            pass

    user_exists = supabase.table("app_users").select("*").eq("telegram_id", tg_user.id).execute()
    
    if not user_exists.data:
        user_data = {
            "telegram_id": tg_user.id,
            "username": tg_user.username or "Unknown",
            "balance_usd": 0.00,
            "referred_by": referrer_id
        }
        supabase.table("app_users").insert(user_data).execute()
        
        if referrer_id:
            ref_user = supabase.table("app_users").select("balance_usd").eq("telegram_id", referrer_id).execute()
            if ref_user.data:
                new_ref_balance = float(ref_user.data["balance_usd"]) + 0.02
                supabase.table("app_users").update({"balance_usd": new_ref_balance}).eq("telegram_id", referrer_id).execute()
                try:
                    await context.bot.send_message(chat_id=referrer_id, text=f"🎁 تمت إضافة 0.02\$ لرصيدك لإحالة مستخدم جديد!")
                except Exception:
                    pass
    
    referral_link = f"https://t.me{context.bot.username}?start={tg_user.id}"
    keyboard = [[InlineKeyboardButton("📱 فتح تطبيق التعدين وكسب المال", web_app={"url": "https://vercel.app"})]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"أهلاً بك يا {tg_user.first_name} في شبكة التعدين التشاركية! 🚀\n\n"
        f"🔗 رابط الإحالة الخاص بك هو:\n👉 `{referral_link}`",
        reply_markup=reply_markup, parse_mode="Markdown"
    )

# 🔄 إعداد وتشغيل المنظومة حياً عند إقلاع خادم ريندر
@app.on_event("startup")
async def on_startup():
    bot_app.add_handler(CommandHandler("start", start))
    await bot_app.initialize()
    await bot_app.start()
    # ربط البوت برابط الـ Webhook السحابي رسمياً في التلجرام
    webhook_url = f"{RENDER_URL}/webhook"
    await bot_app.bot.set_webhook(url=webhook_url)
    print(f"✅ تم تفعيل الـ Webhook سحابياً على رابط: {webhook_url}")

@app.on_event("shutdown")
async def on_shutdown():
    await bot_app.bot.delete_webhook()
    await bot_app.stop()
    await bot_app.uninitialize()

if __name__ == "__main__":
    uvicorn.run("bot:app", host="0.0.0.0", port=8000, reload=False)
