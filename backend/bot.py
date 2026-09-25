import os
import asyncio
from dotenv import load_dotenv  # 🟢 تم تصحيح الاسم هنا
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes
from fastapi import FastAPI
import uvicorn
from database import get_or_create_user, get_balance

load_dotenv()  # 🟢 تم تصحيح الاسم هنا
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# تأسيس سيرفر الـ API للواجهات المستقبلية
app = FastAPI()

@app.get("/")
def home():
    return {"status": "Server is running securely"}

# --- أكواد وأوامر بوت التلجرام ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر الترحيب بالمستخدمين وحفظ بياناتهم بشكل مستقل"""
    tg_user = update.effective_user
    get_or_create_user(tg_user.id, tg_user.username)
    
    keyboard = [
        [InlineKeyboardButton("📱 فتح تطبيق التعدين وكسب المال", web_app={"url": "https://vercel.app"})]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"أهلاً بك يا {tg_user.first_name} في شبكة التشغيل التشاركية الموثوقة! 🚀\n\n"
        f"اضغط على الزر أدناه للموافقة على مشاركة الإنترنت الفائض والبدء في حصد الأرباح حياً تلقائياً.",
        reply_markup=reply_markup
    )

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر فحص الرصيد المالي المدمج"""
    tg_user = update.effective_user
    current_balance = get_balance(tg_user.id)
    await update.message.reply_text(
        f"💰 رصيدك المالي الحالي هو:\n"
        f"👉 {current_balance:.2f} USD\n\n"
        f"يمكنك طلب السحب عند الوصول للحد الأدنى عبر سيريتل كاش بنجاح."
    )

async def main_bot():
    """تشغيل البوت في الخلفية بشكل حي"""
    bot_app = Application.builder().token(TOKEN).build()
    bot_app.add_handler(CommandHandler("start", start))
    bot_app.add_handler(CommandHandler("balance", balance))
    
    await bot_app.initialize()
    await bot_app.start()
    await bot_app.updater.start_polling()

async def run_services():
    bot_task = asyncio.create_task(main_bot())
    server = uvicorn.Server(uvicorn.Config(app, host="0.0.0.0", port=8000))

    try:
        await server.serve()
    finally:
        bot_task.cancel()
        await asyncio.gather(bot_task, return_exceptions=True)


if __name__ == "__main__":
    asyncio.run(run_services())
