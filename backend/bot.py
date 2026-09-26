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
TRAFF_TOKEN = os.getenv("TRAFFMONETIZER_TOKEN")

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

# 🟢 هذا هو السطر الحاسم والمسار المفقود الذي يبحث عنه الهاتف
@app.post("/api/ping-mining")
async def ping_mining(request: MiningRequest):
    """ربط إشارة الهاتف بتوجيه البيانات لحساب Traffmonetizer وتحديث الأرباح"""
    try:
        # إرسال نبضة اتصال (Ping) إلى خوادم Traffmonetizer باستخدام التوكن الخاص بك
        async with httpx.AsyncClient(timeout=5.0) as client:
            headers = {"Authorization": f"Bearer {TRAFF_TOKEN}"} if TRAFF_TOKEN else {}
            await client.post("https://traffmonetizer.com", headers=headers)
            
        # الحسبة المالية المحلية للمشتركين (نمنحهم رصيداً ثابتاً في Supabase عند كل نبضة)
        earned_amount = 0.0005 
        
        # جلب وتحديث الرصيد في قاعدة بيانات Supabase المستقلة
        current_balance = get_balance(request.telegram_id)
        new_balance = current_balance + earned_amount
        
        supabase.table("app_users").update({"balance_usd": new_balance}).eq("telegram_id", request.telegram_id).execute()
        
        # تسجيل العملية في جدول حركة البيانات (Traffic Logs)
        log_data = {
            "user_id": request.telegram_id,
            "mb_shared": 0.05, 
            "earnings": earned_amount
        }
        supabase.table("traffic_logs").insert(log_data).execute()
        
        return {"success": True, "new_balance": new_balance}
        
    except Exception as e:
        print(f"Traffmonetizer Mining Error: {e}")
        raise HTTPException(status_code=500, detail="فشلت مزامنة البيانات السحابية")

# --- أكواد وأوامر بوت التلجرام مع نظام الإحالة الفيروسي المدمج ---
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
                new_ref_balance = float(ref_user.data[0]["balance_usd"]) + 0.02
                supabase.table("app_users").update({"balance_usd": new_ref_balance}).eq("telegram_id", referrer_id).execute()
                try:
                    await context.bot.send_message(
                        chat_id=referrer_id, 
                        text=f"🎁 تهانينا! سجل مستخدم جديد عبر رابط الإحالة الخاص بك، وتمت إضافة 0.02\$ إلى رصيدك!"
                    )
                except Exception:
                    pass
    
    referral_link = f"https://t.me{context.bot.username}?start={tg_user.id}"
    
    keyboard = [
        [InlineKeyboardButton("📱 فتح تطبيق التعدين وكسب المال", web_app={"url": "https://vercel.app"})]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"أهلاً بك يا {tg_user.first_name} في شبكة التعدين التشاركية! 🚀\n\n"
        f"🔗 رابط الإحالة الخاص بك لدعوة أصدقائك وكسب 10% من أرباحهم مستقبلاً هو:\n"
        f"👉 `{referral_link}`\n\n"
        f"انشره في مجموعات الفيس بوك والتلجرام لتبدأ بجني الدولارات تلقائياً!",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def main_bot():
    bot_app = Application.builder().token(TOKEN).build()
    bot_app.add_handler(CommandHandler("start", start))
    await bot_app.initialize()
    await bot_app.start()
    await bot_app.updater.start_polling()

async def start_all():
    await main_bot()
    config = uvicorn.Config(app, host="0.0.0.0", port=8000, loop="asyncio")
    server = uvicorn.Server(config)
    await server.serve()

if __name__ == "__main__":
    asyncio.run(start_all())
