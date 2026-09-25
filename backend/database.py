import os
from pathlib import Path

from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv(Path(__file__).with_name(".env"))

url = os.getenv("SUPABASE_URL")
key = (
    os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    or os.getenv("SUPABASE_ANON_KEY")
    or os.getenv("SUPABASE_KEY")
)

if not url or not key:
    raise RuntimeError(
        "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set in backend/.env."
    )

if key.startswith("sb_") or key.count(".") != 2:
    raise RuntimeError(
        "Supabase key must contain the anon or service_role JWT, "
        "not a project ID or sb_publishable key. Copy it from Supabase Dashboard "
        "> Settings > API."
    )

supabase: Client = create_client(url, key)

def get_or_create_user(telegram_id: int, username: str):
    """التحقق من وجود المستخدم أو تسجيله تلقائياً إذا كان جديداً"""
    try:
        response = supabase.table("app_users").select("*").eq("telegram_id", telegram_id).execute()
        if response.data:
            return response.data
        
        user_data = {
            "telegram_id": telegram_id,
            "username": username or "Unknown",
            "balance_usd": 0.00
        }
        new_user = supabase.table("app_users").insert(user_data).execute()
        return new_user.data
    except Exception as e:
        print(f"Error in database: {e}")
        return None

def get_balance(telegram_id: int) -> float:
    """جلب رصيد المستخدم الحالي"""
    try:
        response = supabase.table("app_users").select("balance_usd").eq("telegram_id", telegram_id).execute()
        if response.data:
            return float(response.data[0]["balance_usd"])
        return 0.00
    except Exception as e:
        print(f"Error getting balance: {e}")
        return 0.00
