import os
import json
import logging
from flask import Flask
from threading import Thread
from telegram import ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, CallbackQueryHandler, Filters
from datetime import datetime, timedelta
import requests
import random
import string
import shutil
import time
import base64

# --- تنظیمات لاگینگ ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- وب سرور ---
app_web = Flask(__name__)

@app_web.route('/')
def home():
    return "✅ VPN Bot is Running!", 200

def run_web():
    port = int(os.environ.get('PORT', 8080))
    app_web.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

# --- توکن و آیدی ادمین ---
TOKEN = '8298942850:AAFdcOhM0se4nHJScRI5cSwKCM_6k4H_UHQ'
ADMIN_ID = 5993860770

# --- مسیر دیتابیس ---
DB_FILE = 'data.json'
BACKUP_DIR = 'backups'

# --- پلن‌های پیش‌فرض ---
DEFAULT_PLANS = {
    "🚀 قوی": [
        {"id": 1, "name": "⚡️ پلن قوی 20GB", "price": 80, "volume": "20GB", "days": 30, "users": 1},
        {"id": 2, "name": "🔥 پلن قوی 50GB", "price": 140, "volume": "50GB", "days": 30, "users": 1}
    ],
    "💎 ارزان": [
        {"id": 3, "name": "💎 پلن اقتصادی 10GB", "price": 45, "volume": "10GB", "days": 30, "users": 1},
        {"id": 4, "name": "💎 پلن اقتصادی 20GB", "price": 75, "volume": "20GB", "days": 30, "users": 1}
    ],
    "🎯 به صرفه": [
        {"id": 5, "name": "🎯 پلن ویژه 30GB", "price": 110, "volume": "30GB", "days": 30, "users": 1},
        {"id": 6, "name": "🎯 پلن ویژه 60GB", "price": 190, "volume": "60GB", "days": 30, "users": 1}
    ],
    "👥 چند کاربره": [
        {"id": 7, "name": "👥 2 کاربره 40GB", "price": 150, "volume": "40GB", "days": 30, "users": 2},
        {"id": 8, "name": "👥 3 کاربره 60GB", "price": 210, "volume": "60GB", "days": 30, "users": 3}
    ]
}

def reset_webhook():
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/deleteWebhook"
        requests.post(url, json={"drop_pending_updates": True})
        time.sleep(1)
        url = f"https://api.telegram.org/bot{TOKEN}/setWebhook"
        requests.post(url, json={"url": ""})
        return True
    except:
        return False

# دیتابیس سراسری
DB = None

def load_db():
    global DB
    try:
        if os.path.exists(DB_FILE):
            with open(DB_FILE, 'r', encoding='utf-8') as f:
                DB = json.load(f)
                logger.info("✅ Database loaded")
                
                # فیلدهای پیش‌فرض
                if "force_join" not in DB:
                    DB["force_join"] = {"enabled": False, "channel_id": "", "channel_link": "", "channel_username": ""}
                if "discount_codes" not in DB:
                    DB["discount_codes"] = {}
                if "blocked_users" not in DB:
                    DB["blocked_users"] = []
                if "panel_config" not in DB:
                    DB["panel_config"] = {
                        "enabled": False, 
                        "api_url": "http://p.dragonteamm.shop:8081", 
                        "admin_path": "hke43Y4nhZ23K1vc4S", 
                        "username": "amir", 
                        "password": "amirreza871221", 
                        "test_config": {"volume": 50, "expiry_hours": 3, "enabled": True}
                    }
                if "categories" not in DB:
                    DB["categories"] = DEFAULT_PLANS.copy()
                if "texts" not in DB:
                    DB["texts"] = {
                        "welcome": "🔰 به {brand} خوش آمدید\n\n✅ فروش ویژه فیلترشکن\n✅ پشتیبانی 24 ساعته\n✅ نصب آسان",
                        "support": "🆘 پشتیبانی: {support}",
                        "guide": "📚 آموزش: {guide}",
                        "test": "🎁 درخواست تست شما ثبت شد",
                        "force": "🔒 برای استفاده از ربات باید در کانال زیر عضو شوید:\n{link}\n\nپس از عضویت، دکمه ✅ تایید را بزنید.",
                        "invite": "🤝 لینک دعوت شما:\n{link}\n\nبه ازای هر دعوت 1 روز هدیه"
                    }
                if "brand" not in DB:
                    DB["brand"] = "تک نت وی‌پی‌ان"
                if "card" not in DB:
                    DB["card"] = {"number": "6277601368776066", "name": "محمد رضوانی"}
                if "support" not in DB:
                    DB["support"] = "@Support_Admin"
                if "guide" not in DB:
                    DB["guide"] = "@Guide_Channel"
                if "users" not in DB:
                    DB["users"] = {}
                return
    except Exception as e:
        logger.error(f"❌ Error loading: {e}")
    
    logger.info("📁 Creating default database")
    DB = {
        "users": {},
        "brand": "تک نت وی‌پی‌ان",
        "card": {"number": "6277601368776066", "name": "محمد رضوانی"},
        "support": "@Support_Admin",
        "guide": "@Guide_Channel",
        "categories": DEFAULT_PLANS.copy(),
        "force_join": {"enabled": False, "channel_id": "", "channel_link": "", "channel_username": ""},
        "discount_codes": {},
        "blocked_users": [],
        "panel_config": {
            "enabled": False, 
            "api_url": "http://p.dragonteamm.shop:8081", 
            "admin_path": "hke43Y4nhZ23K1vc4S", 
            "username": "amir", 
            "password": "amirreza871221", 
            "test_config": {"volume": 50, "expiry_hours": 3, "enabled": True}
        },
        "texts": {
            "welcome": "🔰 به {brand} خوش آمدید\n\n✅ فروش ویژه فیلترشکن\n✅ پشتیبانی 24 ساعته\n✅ نصب آسان",
            "support": "🆘 پشتیبانی: {support}",
            "guide": "📚 آموزش: {guide}",
            "test": "🎁 درخواست تست شما ثبت شد",
            "force": "🔒 برای استفاده از ربات باید در کانال زیر عضو شوید:\n{link}\n\nپس از عضویت، دکمه ✅ تایید را بزنید.",
            "invite": "🤝 لینک دعوت شما:\n{link}\n\nبه ازای هر دعوت 1 روز هدیه"
        }
    }

def save_db():
    global DB
    try:
        with open(DB_FILE, 'w', encoding='utf-8') as f:
            json.dump(DB, f, ensure_ascii=False, indent=4)
        return True
    except:
        return False

def create_backup():
    try:
        if not os.path.exists(BACKUP_DIR):
            os.makedirs(BACKUP_DIR)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = os.path.join(BACKUP_DIR, f"backup_{timestamp}.json")
        shutil.copy2(DB_FILE, backup_file)
        backups = sorted([f for f in os.listdir(BACKUP_DIR) if f.endswith('.json')])
        for old in backups[:-10]:
            os.remove(os.path.join(BACKUP_DIR, old))
        return backup_file
    except:
        return None

def restore_backup(backup_file):
    try:
        backup_path = os.path.join(BACKUP_DIR, backup_file)
        if os.path.exists(backup_path):
            shutil.copy2(backup_path, DB_FILE)
            return True
    except:
        return False

def get_user_info(uid, context):
    try:
        user = context.bot.get_chat(int(uid))
        if user.username:
            return f"@{user.username}"
        else:
            return f"{user.first_name or ''} {user.last_name or ''}".strip() or str(uid)
    except:
        return str(uid)

def generate_discount_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

def login_to_panel():
    """ورود به پنل و دریافت سشن"""
    global DB
    panel = DB.get("panel_config", {})
    api_url = panel.get('api_url', '').rstrip('/')
    admin_path = panel.get('admin_path', '')
    username = panel.get('username', '')
    password = panel.get('password', '')
    
    if not api_url or not admin_path or not username or not password:
        return None, "تنظیمات پنل کامل نیست"
    
    session = requests.Session()
    
    # تلاش برای لاگین
    try:
        # روش اول: لاگین با JSON
        login_res = session.post(
            f"{api_url}/{admin_path}/login",
            json={"username": username, "password": password},
            timeout=10
        )
        if login_res.status_code == 200:
            return session, None
    except:
        pass
    
    try:
        # روش دوم: لاگین با فرم دیتا
        login_res = session.post(
            f"{api_url}/{admin_path}/login",
            data={"username": username, "password": password},
            timeout=10
        )
        if login_res.status_code == 200:
            return session, None
    except:
        pass
    
    try:
        # روش سوم: لاگین با هدر
        login_res = session.post(
            f"{api_url}/login",
            json={"username": username, "password": password},
            timeout=10
        )
        if login_res.status_code == 200:
            return session, None
    except:
        pass
    
    return None, "خطا در اتصال به پنل"

def create_account_on_panel(plan, account_name):
    """ساخت اکانت در پنل"""
    global DB
    panel = DB.get("panel_config", {})
    if not panel.get("enabled"):
        return None, "پنل متصل نیست"
    
    session, error = login_to_panel()
    if not session:
        return None, error
    
    api_url = panel.get('api_url', '').rstrip('/')
    admin_path = panel.get('admin_path', '')
    
    try:
        # دریافت حجم به گیگابایت
        volume = plan.get("volume", "0GB")
        volume_gb = 0
        if "GB" in volume:
            volume_gb = int(volume.replace("GB", "").strip())
        
        expiry_days = plan.get("days", 30)
        expiry_time = int((datetime.now() + timedelta(days=expiry_days)).timestamp())
        
        # ایمیل کاربر
        client_email = f"{account_name}_{int(time.time())}".replace(' ', '_')
        
        # ساخت کاربر جدید
        add_payload = {
            "email": client_email,
            "total_gb": volume_gb,
            "expiry_time": expiry_time,
            "enable": True
        }
        
        add_res = session.post(
            f"{api_url}/{admin_path}/api/user/add",
            json=add_payload,
            timeout=30
        )
        
        if add_res.status_code == 200:
            result = add_res.json()
            if result.get('success'):
                # لینک سابسکریپشن
                sub_url = f"{api_url}/sub/{client_email}"
                return sub_url, None
        
        return None, "خطا در ساخت اکانت"
    except Exception as e:
        return None, str(e)

def create_test_account():
    """ساخت اکانت تست"""
    global DB
    panel = DB.get("panel_config", {})
    test_config = panel.get("test_config", {})
    
    if not panel.get("enabled"):
        return None, "پنل متصل نیست"
    
    if not test_config.get("enabled"):
        return None, "تست غیرفعال است"
    
    session, error = login_to_panel()
    if not session:
        return None, error
    
    api_url = panel.get('api_url', '').rstrip('/')
    admin_path = panel.get('admin_path', '')
    
    try:
        volume_mb = test_config.get("volume", 50)
        volume_gb = round(volume_mb / 1024, 2)
        expiry_hours = test_config.get("expiry_hours", 3)
        expiry_time = int((datetime.now() + timedelta(hours=expiry_hours)).timestamp())
        
        client_email = f"test_{int(time.time())}_{random.randint(1000,9999)}"
        
        add_payload = {
            "email": client_email,
            "total_gb": volume_gb,
            "expiry_time": expiry_time,
            "enable": True
        }
        
        add_res = session.post(
            f"{api_url}/{admin_path}/api/user/add",
            json=add_payload,
            timeout=30
        )
        
        if add_res.status_code == 200 and add_res.json().get('success'):
            sub_url = f"{api_url}/sub/{client_email}"
            return sub_url, None
        
        return None, "خطا در ساخت اکانت تست"
    except Exception as e:
        return None, str(e)

# متغیرهای سراسری
user_data = {}

def main_menu(uid):
    kb = [
        ['💰 خرید', '🎁 تست'],
        ['📂 سرویس‌ها', '⏳ تمدید'],
        ['👤 پشتیبانی', '📚 آموزش'],
        ['🤝 دعوت دوستان']
    ]
    if str(uid) == str(ADMIN_ID):
        kb.append(['⚙️ مدیریت'])
    return ReplyKeyboardMarkup(kb, resize_keyboard=True)

def back_btn():
    return ReplyKeyboardMarkup([['🔙 برگشت']], resize_keyboard=True)

def admin_menu():
    kb = [
        ['➕ پلن جدید', '➖ حذف پلن'],
        ['➕ دسته جدید', '➖ حذف دسته'],
        ['💳 ویرایش کارت', '📝 ویرایش متن‌ها'],
        ['👤 ویرایش پشتیبان', '📢 ویرایش کانال'],
        ['🔒 عضویت اجباری', '🏷 ویرایش برند'],
        ['🔌 تنظیمات پنل', '🎁 تنظیمات تست'],
        ['🎫 کد تخفیف', '🚫 بلاک کاربر'],
        ['📊 آمار', '📨 ارسال همگانی'],
        ['💾 بکاپ', '🔄 بازیابی بکاپ'],
        ['🔙 برگشت']
    ]
    return ReplyKeyboardMarkup(kb, resize_keyboard=True)

def discount_codes_menu():
    kb = [
        ['➕ ساخت کد تخفیف', '📋 لیست کدها'],
        ['❌ حذف کد تخفیف'],
        ['🔙 برگشت']
    ]
    return ReplyKeyboardMarkup(kb, resize_keyboard=True)

def check_join(user_id, context):
    global DB
    if not DB["force_join"]["enabled"]:
        return True
    channel_username = DB["force_join"].get("channel_username", "")
    if not channel_username:
        return True
    try:
        member = context.bot.get_chat_member(chat_id=channel_username, user_id=int(user_id))
        return member.status in ['member', 'administrator', 'creator']
    except:
        return False

def start(update, context):
    global DB, user_data
    uid = str(update.effective_user.id)
    
    if uid in DB.get("blocked_users", []):
        update.message.reply_text("🚫 شما توسط ادمین بلاک شده‌اید")
        return
    
    if uid not in DB["users"]:
        DB["users"][uid] = {"purchases": [], "tests": [], "test_count": 0, "date": datetime.now().strftime("%Y-%m-%d")}
        save_db()
    
    user_data[uid] = {}
    
    if DB["force_join"]["enabled"] and DB["force_join"]["channel_link"]:
        if not check_join(uid, context):
            btn = InlineKeyboardMarkup([[
                InlineKeyboardButton("📢 عضویت در کانال", url=DB["force_join"]["channel_link"]),
                InlineKeyboardButton("✅ تایید عضویت", callback_data="join_check")
            ]])
            update.message.reply_text(DB["texts"]["force"].format(link=DB["force_join"]["channel_link"]), reply_markup=btn)
            return
    
    update.message.reply_text(DB["texts"]["welcome"].format(brand=DB["brand"]), reply_markup=main_menu(uid))

def handle_msg(update, context):
    global DB, user_data
    try:
        text = update.message.text
        uid = str(update.effective_user.id)
        
        if uid in DB.get("blocked_users", []):
            update.message.reply_text("🚫 شما توسط ادمین بلاک شده‌اید")
            return
        
        step = user_data.get(uid, {}).get('step')

        if DB["force_join"]["enabled"] and DB["force_join"]["channel_link"]:
            if not check_join(uid, context) and text != '/start':
                btn = InlineKeyboardMarkup([[
                    InlineKeyboardButton("📢 عضویت در کانال", url=DB["force_join"]["channel_link"]),
                    InlineKeyboardButton("✅ تایید عضویت", callback_data="join_check")
                ]])
                update.message.reply_text(DB["texts"]["force"].format(link=DB["force_join"]["channel_link"]), reply_markup=btn)
                return

        if text == '🔙 برگشت':
            user_data[uid] = {}
            start(update, context)
            return

        # تست رایگان
        if text == '🎁 تست':
            panel_config = DB.get("panel_config", {})
            if not panel_config.get("enabled"):
                update.message.reply_text("❌ سرویس تست غیرفعال است\nلطفا ابتدا پنل را در بخش مدیریت تنظیم و فعال کنید")
                return
            if DB["users"][uid]["test_count"] >= 1:
                update.message.reply_text("❌ شما قبلاً تست گرفته‌اید")
                return
            
            update.message.reply_text("🔄 در حال ساخت اکانت تست...")
            config, error = create_test_account()
            
            if config:
                DB["users"][uid]["test_count"] += 1
                DB["users"][uid]["tests"].append(datetime.now().strftime("%Y-%m-%d"))
                save_db()
                msg = f"🎁 اکانت تست شما آماده است\n━━━━━━━━━━━━━━━━━\n⏱ مدت: {panel_config.get('test_config', {}).get('expiry_hours', 3)} ساعت\n📦 حجم: {panel_config.get('test_config', {}).get('volume', 50)} مگابایت\n━━━━━━━━━━━━━━━━━\n🔗 لینک اتصال:\n`{config}`\n\n📚 {DB['guide']}"
                update.message.reply_text(msg, parse_mode='Markdown')
            else:
                update.message.reply_text(f"❌ خطا در ساخت اکانت تست:\n{error}\n\nلطفاً تنظیمات پنل را بررسی کنید")
            return

        # سرویس‌ها
        if text == '📂 سرویس‌ها':
            pur = DB["users"][uid].get("purchases", [])
            tests = DB["users"][uid].get("tests", [])
            msg = "📂 سرویس‌های شما:\n━━━━━━━━━━\n"
            if pur:
                msg += "✅ خریدها:\n"
                for i, p in enumerate(pur[-10:], 1):
                    msg += f"{i}. {p}\n"
            else:
                msg += "❌ خریدی ندارید\n"
            if tests:
                msg += "\n🎁 تست‌ها:\n"
                for i, t in enumerate(tests[-5:], 1):
                    msg += f"{i}. {t}\n"
            update.message.reply_text(msg)
            return

        # تمدید
        if text == '⏳ تمدید':
            pur = DB["users"][uid].get("purchases", [])
            if not pur:
                update.message.reply_text("❌ سرویسی برای تمدید ندارید")
                return
            keyboard = [[InlineKeyboardButton(f"🔄 {p[:30]}...", callback_data=f"renew_{i}")] for i, p in enumerate(pur[-5:])]
            update.message.reply_text("سرویس مورد نظر را انتخاب کنید:", reply_markup=InlineKeyboardMarkup(keyboard))
            return

        # پشتیبانی
        if text == '👤 پشتیبانی':
            update.message.reply_text(DB["texts"]["support"].format(support=DB["support"]))
            return

        # آموزش
        if text == '📚 آموزش':
            update.message.reply_text(DB["texts"]["guide"].format(guide=DB["guide"]))
            return

        # دعوت
        if text == '🤝 دعوت دوستان':
            bot = context.bot.get_me().username
            link = f"https://t.me/{bot}?start={uid}"
            update.message.reply_text(DB["texts"]["invite"].format(link=link))
            return

        # خرید
        if text == '💰 خرید':
            cats = list(DB["categories"].keys())
            kb = [[c] for c in cats] + [['🔙 برگشت']]
            update.message.reply_text("دسته را انتخاب کنید:", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
            return

        # نمایش پلن‌ها
        if text in DB["categories"] and not step:
            plans = DB["categories"][text]
            keyboard = []
            for p in plans:
                price_toman = p['price'] * 1000
                keyboard.append([InlineKeyboardButton(f"{p['name']} - {price_toman:,} تومان", callback_data=f"buy_{p['id']}")])
            update.message.reply_text(f"📦 {text}", reply_markup=InlineKeyboardMarkup(keyboard))
            return

        # --- مدیریت ادمین ---
        if str(uid) == str(ADMIN_ID):
            
            if text == '⚙️ مدیریت':
                update.message.reply_text("🛠 پنل مدیریت:", reply_markup=admin_menu())
                return

            # تنظیمات پنل
            if text == '🔌 تنظیمات پنل':
                keyboard = [
                    ['✅ فعال کردن پنل', '❌ غیرفعال کردن پنل'],
                    ['🔗 تنظیم آدرس پنل', '🔐 تنظیم مسیر ادمین'],
                    ['👤 تنظیم یوزرنیم', '🔑 تنظیم رمز'],
                    ['🔙 برگشت']
                ]
                status = "✅ فعال" if DB["panel_config"]["enabled"] else "❌ غیرفعال"
                update.message.reply_text(f"🔌 وضعیت پنل: {status}\nآدرس: {DB['panel_config'].get('api_url', 'تنظیم نشده')}\nمسیر ادمین: {DB['panel_config'].get('admin_path', 'تنظیم نشده')}", reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))
                return

            if text == '✅ فعال کردن پنل':
                DB["panel_config"]["enabled"] = True
                save_db()
                update.message.reply_text("✅ پنل فعال شد", reply_markup=admin_menu())
                return

            if text == '❌ غیرفعال کردن پنل':
                DB["panel_config"]["enabled"] = False
                save_db()
                update.message.reply_text("❌ پنل غیرفعال شد", reply_markup=admin_menu())
                return

            if text == '🔗 تنظیم آدرس پنل':
                user_data[uid] = {'step': 'set_api_url'}
                update.message.reply_text("آدرس پنل را وارد کنید:\nمثال: http://p.dragonteamm.shop:8081", reply_markup=back_btn())
                return

            if text == '🔐 تنظیم مسیر ادمین':
                user_data[uid] = {'step': 'set_admin_path'}
                update.message.reply_text("مسیر پنل ادمین را وارد کنید:\nمثال: hke43Y4nhZ23K1vc4S", reply_markup=back_btn())
                return

            if text == '👤 تنظیم یوزرنیم':
                user_data[uid] = {'step': 'set_username'}
                update.message.reply_text("یوزرنیم ادمین پنل را وارد کنید:", reply_markup=back_btn())
                return

            if text == '🔑 تنظیم رمز':
                user_data[uid] = {'step': 'set_password'}
                update.message.reply_text("رمز عبور ادمین پنل را وارد کنید:", reply_markup=back_btn())
                return

            # تنظیمات تست
            if text == '🎁 تنظیمات تست':
                test_config = DB["panel_config"].get("test_config", {})
                keyboard = [
                    ['📊 حجم تست (MB)', '⏱ مدت تست (ساعت)'],
                    ['✅ فعال کردن تست', '❌ غیرفعال کردن تست'],
                    ['🔙 برگشت']
                ]
                status = "✅ فعال" if test_config.get("enabled") else "❌ غیرفعال"
                update.message.reply_text(f"🎁 تنظیمات تست:\nوضعیت: {status}\nحجم: {test_config.get('volume', 50)} مگابایت\nمدت: {test_config.get('expiry_hours', 3)} ساعت", reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))
                return

            if text == '📊 حجم تست (MB)':
                user_data[uid] = {'step': 'set_test_volume'}
                update.message.reply_text("حجم تست را به مگابایت وارد کنید:", reply_markup=back_btn())
                return

            if text == '⏱ مدت تست (ساعت)':
                user_data[uid] = {'step': 'set_test_hours'}
                update.message.reply_text("مدت تست را به ساعت وارد کنید:", reply_markup=back_btn())
                return

            if text == '✅ فعال کردن تست':
                DB["panel_config"]["test_config"]["enabled"] = True
                save_db()
                update.message.reply_text("✅ تست فعال شد", reply_markup=admin_menu())
                return

            if text == '❌ غیرفعال کردن تست':
                DB["panel_config"]["test_config"]["enabled"] = False
                save_db()
                update.message.reply_text("❌ تست غیرفعال شد", reply_markup=admin_menu())
                return

            # کد تخفیف
            if text == '🎫 کد تخفیف':
                update.message.reply_text("🎫 مدیریت کدهای تخفیف:", reply_markup=discount_codes_menu())
                return

            if text == '➕ ساخت کد تخفیف':
                user_data[uid] = {'step': 'make_discount_percent'}
                update.message.reply_text("درصد تخفیف را وارد کنید (1 تا 100):", reply_markup=back_btn())
                return

            if text == '📋 لیست کدها':
                codes = DB.get("discount_codes", {})
                if not codes:
                    update.message.reply_text("❌ کد تخفیفی وجود ندارد")
                else:
                    msg = "📋 لیست کدهای تخفیف:\n━━━━━━━━━━\n"
                    for code, data_item in codes.items():
                        expires = datetime.fromtimestamp(data_item["expires"]).strftime("%Y-%m-%d")
                        msg += f"🎫 {code}\n   {data_item['discount_percent']}% | {data_item['uses']}/{data_item['max_uses']} | تا {expires}\n\n"
                    update.message.reply_text(msg)
                return

            if text == '❌ حذف کد تخفیف':
                user_data[uid] = {'step': 'del_discount_code'}
                update.message.reply_text("کد تخفیف را وارد کنید:", reply_markup=back_btn())
                return

            # دسته‌بندی
            if text == '➕ دسته جدید':
                user_data[uid] = {'step': 'new_category'}
                update.message.reply_text("نام دسته جدید را وارد کنید:", reply_markup=back_btn())
                return

            if text == '➖ حذف دسته':
                cats = list(DB["categories"].keys())
                if not cats:
                    update.message.reply_text("❌ دسته‌ای وجود ندارد")
                else:
                    keyboard = [[f"❌ {cat}"] for cat in cats] + [['🔙 برگشت']]
                    user_data[uid] = {'step': 'del_category'}
                    update.message.reply_text("دسته مورد نظر را انتخاب کنید:", reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))
                return

            # بلاک کاربر
            if text == '🚫 بلاک کاربر':
                user_data[uid] = {'step': 'block_user'}
                update.message.reply_text("آیدی عددی کاربر را وارد کنید:", reply_markup=back_btn())
                return

            # بکاپ
            if text == '💾 بکاپ':
                backup_file = create_backup()
                update.message.reply_text(f"✅ بکاپ گرفته شد: {backup_file}" if backup_file else "❌ خطا در گرفتن بکاپ")
                return

            if text == '🔄 بازیابی بکاپ':
                backups = [f for f in os.listdir(BACKUP_DIR) if f.endswith('.json')] if os.path.exists(BACKUP_DIR) else []
                if not backups:
                    update.message.reply_text("❌ هیچ بکاپی یافت نشد")
                else:
                    keyboard = [[f"🔄 {b}"] for b in backups[-10:]] + [['🔙 برگشت']]
                    user_data[uid] = {'step': 'restore_backup'}
                    update.message.reply_text("بکاپ مورد نظر را انتخاب کنید:", reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))
                return

            # ویرایش کارت
            if text == '💳 ویرایش کارت':
                keyboard = [['شماره کارت', 'نام صاحب کارت'], ['🔙 برگشت']]
                update.message.reply_text(f"شماره: {DB['card']['number']}\nنام: {DB['card']['name']}", reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))
                return

            if text == 'شماره کارت':
                user_data[uid] = {'step': 'card_num'}
                update.message.reply_text("شماره کارت 16 رقمی را بفرستید:", reply_markup=back_btn())
                return

            if text == 'نام صاحب کارت':
                user_data[uid] = {'step': 'card_name'}
                update.message.reply_text("نام صاحب کارت را بفرستید:", reply_markup=back_btn())
                return

            if text == '👤 ویرایش پشتیبان':
                user_data[uid] = {'step': 'support'}
                update.message.reply_text("آیدی پشتیبان را بفرستید:", reply_markup=back_btn())
                return

            if text == '📢 ویرایش کانال':
                user_data[uid] = {'step': 'guide'}
                update.message.reply_text("آیدی کانال آموزش را بفرستید:", reply_markup=back_btn())
                return

            if text == '🏷 ویرایش برند':
                user_data[uid] = {'step': 'brand'}
                update.message.reply_text("نام برند را بفرستید:", reply_markup=back_btn())
                return

            if text == '📝 ویرایش متن‌ها':
                keyboard = [['خوش‌آمدگویی', 'پشتیبانی', 'آموزش'], ['تست رایگان', 'عضویت اجباری', 'دعوت دوستان'], ['🔙 برگشت']]
                update.message.reply_text("📝 کدام متن را ویرایش کنیم؟", reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))
                return

            text_map = {'خوش‌آمدگویی': 'welcome', 'پشتیبانی': 'support', 'آموزش': 'guide', 'تست رایگان': 'test', 'عضویت اجباری': 'force', 'دعوت دوستان': 'invite'}
            if text in text_map:
                user_data[uid] = {'step': f'edit_{text_map[text]}'}
                update.message.reply_text(f"متن فعلی:\n{DB['texts'][text_map[text]]}\n\nمتن جدید را بفرستید:", reply_markup=back_btn())
                return

            if text == '🔒 عضویت اجباری':
                keyboard = [['✅ فعال', '❌ غیرفعال'], ['🔗 تنظیم لینک کانال'], ['🔙 برگشت']]
                status = "✅ فعال" if DB["force_join"]["enabled"] else "❌ غیرفعال"
                update.message.reply_text(f"🔒 وضعیت: {status}\nکانال: {DB['force_join'].get('channel_link', 'تنظیم نشده')}", reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))
                return

            if text == '✅ فعال':
                if DB["force_join"]["channel_link"]:
                    DB["force_join"]["enabled"] = True
                    save_db()
                    update.message.reply_text("✅ عضویت اجباری فعال شد", reply_markup=admin_menu())
                else:
                    update.message.reply_text("❌ ابتدا لینک کانال را تنظیم کنید")
                return

            if text == '❌ غیرفعال':
                DB["force_join"]["enabled"] = False
                save_db()
                update.message.reply_text("✅ عضویت اجباری غیرفعال شد", reply_markup=admin_menu())
                return

            if text == '🔗 تنظیم لینک کانال':
                user_data[uid] = {'step': 'set_link'}
                update.message.reply_text("لینک کانال را بفرستید:", reply_markup=back_btn())
                return

            if text == '📊 آمار':
                total = len(DB["users"])
                pur = sum(len(u.get("purchases", [])) for u in DB["users"].values())
                tests = sum(len(u.get("tests", [])) for u in DB["users"].values())
                update.message.reply_text(f"📊 آمار ربات\n━━━━━━━━━━\n👥 کل کاربران: {total}\n💰 خریدها: {pur}\n🎁 تست‌ها: {tests}")
                return

            if text == '📨 ارسال همگانی':
                user_data[uid] = {'step': 'broadcast'}
                update.message.reply_text("پیام همگانی را بفرستید:", reply_markup=back_btn())
                return

            if text == '➕ پلن جدید':
                cats = list(DB["categories"].keys())
                user_data[uid] = {'step': 'new_cat'}
                update.message.reply_text("دسته را انتخاب کنید:", reply_markup=ReplyKeyboardMarkup([[c] for c in cats] + [['🔙 برگشت']], resize_keyboard=True))
                return

            if text == '➖ حذف پلن':
                keyboard = []
                for cat, plans in DB["categories"].items():
                    for p in plans:
                        keyboard.append([InlineKeyboardButton(f"❌ {cat} - {p['name']}", callback_data=f"del_{p['id']}")])
                if keyboard:
                    update.message.reply_text("پلن را انتخاب کنید:", reply_markup=InlineKeyboardMarkup(keyboard))
                else:
                    update.message.reply_text("❌ پلنی نیست")
                return

            # مراحل مرحله‌ای ادمین
            if step == 'card_num':
                if text.isdigit() and len(text) == 16:
                    DB["card"]["number"] = text
                    save_db()
                    update.message.reply_text("✅ شماره کارت ذخیره شد", reply_markup=admin_menu())
                else:
                    update.message.reply_text("❌ شماره کارت نامعتبر")
                user_data[uid] = {}
                return

            if step == 'card_name':
                DB["card"]["name"] = text
                save_db()
                update.message.reply_text("✅ نام صاحب کارت ذخیره شد", reply_markup=admin_menu())
                user_data[uid] = {}
                return

            if step == 'support':
                DB["support"] = text
                save_db()
                update.message.reply_text("✅ پشتیبان ذخیره شد", reply_markup=admin_menu())
                user_data[uid] = {}
                return

            if step == 'guide':
                DB["guide"] = text
                save_db()
                update.message.reply_text("✅ کانال آموزش ذخیره شد", reply_markup=admin_menu())
                user_data[uid] = {}
                return

            if step == 'brand':
                DB["brand"] = text
                save_db()
                update.message.reply_text("✅ برند ذخیره شد", reply_markup=admin_menu())
                user_data[uid] = {}
                return

            if step and step.startswith('edit_'):
                key = step.replace('edit_', '')
                DB["texts"][key] = text
                save_db()
                update.message.reply_text("✅ متن ذخیره شد", reply_markup=admin_menu())
                user_data[uid] = {}
                return

            if step == 'set_link':
                DB["force_join"]["channel_link"] = text
                if 't.me/' in text:
                    username = text.split('t.me/')[-1].split('/')[0].replace('@', '')
                    DB["force_join"]["channel_username"] = f"@{username}"
                save_db()
                update.message.reply_text("✅ لینک ذخیره شد", reply_markup=admin_menu())
                user_data[uid] = {}
                return

            if step == 'broadcast':
                suc, fail = 0, 0
                for uid2 in DB["users"]:
                    if uid2 not in DB.get("blocked_users", []):
                        try:
                            context.bot.send_message(int(uid2), text)
                            suc += 1
                        except:
                            fail += 1
                update.message.reply_text(f"✅ ارسال شد\nموفق: {suc}\nناموفق: {fail}")
                user_data[uid] = {}
                return

            if step == 'set_api_url':
                DB["panel_config"]["api_url"] = text.rstrip('/')
                save_db()
                update.message.reply_text("✅ آدرس پنل ذخیره شد", reply_markup=admin_menu())
                user_data[uid] = {}
                return

            if step == 'set_admin_path':
                DB["panel_config"]["admin_path"] = text
                save_db()
                update.message.reply_text("✅ مسیر ادمین ذخیره شد", reply_markup=admin_menu())
                user_data[uid] = {}
                return

            if step == 'set_username':
                DB["panel_config"]["username"] = text
                save_db()
                update.message.reply_text("✅ یوزرنیم ذخیره شد", reply_markup=admin_menu())
                user_data[uid] = {}
                return

            if step == 'set_password':
                DB["panel_config"]["password"] = text
                save_db()
                update.message.reply_text("✅ رمز عبور ذخیره شد", reply_markup=admin_menu())
                user_data[uid] = {}
                return

            if step == 'set_test_volume':
                try:
                    DB["panel_config"]["test_config"]["volume"] = int(text)
                    save_db()
                    update.message.reply_text(f"✅ حجم تست به {text} مگابایت تغییر کرد", reply_markup=admin_menu())
                except:
                    update.message.reply_text("❌ عدد معتبر وارد کنید")
                user_data[uid] = {}
                return

            if step == 'set_test_hours':
                try:
                    DB["panel_config"]["test_config"]["expiry_hours"] = int(text)
                    save_db()
                    update.message.reply_text(f"✅ مدت تست به {text} ساعت تغییر کرد", reply_markup=admin_menu())
                except:
                    update.message.reply_text("❌ عدد معتبر وارد کنید")
                user_data[uid] = {}
                return

            if step == 'make_discount_percent':
                try:
                    percent = int(text)
                    if 1 <= percent <= 100:
                        user_data[uid]['percent'] = percent
                        user_data[uid]['step'] = 'make_discount_max'
                        update.message.reply_text("حداکثر تعداد استفاده را وارد کنید:")
                    else:
                        update.message.reply_text("❌ درصد باید بین 1 تا 100 باشد")
                except:
                    update.message.reply_text("❌ عدد معتبر وارد کنید")
                return

            if step == 'make_discount_max':
                try:
                    user_data[uid]['max_uses'] = int(text)
                    user_data[uid]['step'] = 'make_discount_days'
                    update.message.reply_text("مدت اعتبار (روز):")
                except:
                    update.message.reply_text("❌ عدد معتبر وارد کنید")
                return

            if step == 'make_discount_days':
                try:
                    days = int(text)
                    code = generate_discount_code()
                    DB["discount_codes"][code] = {
                        "discount_percent": user_data[uid]['percent'],
                        "max_uses": user_data[uid]['max_uses'],
                        "uses": 0,
                        "expires": (datetime.now() + timedelta(days=days)).timestamp()
                    }
                    save_db()
                    update.message.reply_text(f"✅ کد تخفیف ساخته شد:\n🎫 کد: `{code}`\n📊 درصد: {user_data[uid]['percent']}%\n📋 حداکثر استفاده: {user_data[uid]['max_uses']}\n⏱ اعتبار: {days} روز", parse_mode='Markdown')
                    user_data[uid] = {}
                except:
                    update.message.reply_text("❌ عدد معتبر وارد کنید")
                return

            if step == 'del_discount_code':
                if text in DB.get("discount_codes", {}):
                    del DB["discount_codes"][text]
                    save_db()
                    update.message.reply_text("✅ کد تخفیف حذف شد", reply_markup=admin_menu())
                else:
                    update.message.reply_text("❌ کد یافت نشد")
                user_data[uid] = {}
                return

            if step == 'block_user':
                try:
                    target_id = str(int(text))
                    if target_id == str(ADMIN_ID):
                        update.message.reply_text("❌ نمی‌توانید ادمین را بلاک کنید")
                    elif target_id in DB.get("blocked_users", []):
                        DB["blocked_users"].remove(target_id)
                        save_db()
                        update.message.reply_text(f"✅ کاربر {target_id} آنبلاک شد")
                    else:
                        DB["blocked_users"].append(target_id)
                        save_db()
                        update.message.reply_text(f"✅ کاربر {target_id} بلاک شد")
                except:
                    update.message.reply_text("❌ آیدی عددی معتبر وارد کنید")
                user_data[uid] = {}
                return

            if step == 'restore_backup':
                if text.startswith('🔄 '):
                    backup_file = text[2:]
                    if restore_backup(backup_file):
                        load_db()
                        update.message.reply_text("✅ بکاپ با موفقیت بازیابی شد", reply_markup=admin_menu())
                    else:
                        update.message.reply_text("❌ خطا در بازیابی بکاپ")
                user_data[uid] = {}
                return

            if step == 'new_category':
                if text not in DB["categories"]:
                    DB["categories"][text] = []
                    save_db()
                    update.message.reply_text(f"✅ دسته {text} اضافه شد", reply_markup=admin_menu())
                else:
                    update.message.reply_text("❌ این دسته قبلاً وجود دارد")
                user_data[uid] = {}
                return

            if step == 'del_category' and text.startswith('❌ '):
                cat_name = text[2:]
                if cat_name in DB["categories"]:
                    del DB["categories"][cat_name]
                    save_db()
                    update.message.reply_text(f"✅ دسته {cat_name} حذف شد", reply_markup=admin_menu())
                user_data[uid] = {}
                return

            # مراحل پلن جدید
            if step == 'new_cat' and text in DB["categories"]:
                user_data[uid]['cat'] = text
                user_data[uid]['step'] = 'new_name'
                update.message.reply_text("نام پلن:", reply_markup=back_btn())
                return

            if step == 'new_name':
                user_data[uid]['name'] = text
                user_data[uid]['step'] = 'new_vol'
                update.message.reply_text("حجم (مثال: 50GB):")
                return

            if step == 'new_vol':
                user_data[uid]['vol'] = text
                user_data[uid]['step'] = 'new_users'
                update.message.reply_text("تعداد کاربران:")
                return

            if step == 'new_users':
                try:
                    user_data[uid]['users'] = int(text)
                    user_data[uid]['step'] = 'new_days'
                    update.message.reply_text("مدت اعتبار (روز):")
                except:
                    update.message.reply_text("❌ عدد وارد کنید")
                return

            if step == 'new_days':
                try:
                    user_data[uid]['days'] = int(text)
                    user_data[uid]['step'] = 'new_price'
                    update.message.reply_text("قیمت (هزار تومان):")
                except:
                    update.message.reply_text("❌ عدد وارد کنید")
                return

            if step == 'new_price':
                try:
                    price = int(text)
                    max_id = 0
                    for p in DB["categories"].values():
                        for plan in p:
                            if plan["id"] > max_id:
                                max_id = plan["id"]
                    new_plan = {"id": max_id + 1, "name": user_data[uid]['name'], "price": price, "volume": user_data[uid]['vol'], "days": user_data[uid]['days'], "users": user_data[uid]['users']}
                    DB["categories"][user_data[uid]['cat']].append(new_plan)
                    save_db()
                    update.message.reply_text("✅ پلن اضافه شد", reply_markup=admin_menu())
                    user_data[uid] = {}
                except:
                    update.message.reply_text("❌ خطا")
                return

            if step == 'send_config':
                target = user_data[uid]['target']
                name = user_data[uid]['name']
                plan = user_data[uid].get('plan')
                if plan:
                    config, error = create_account_on_panel(plan, name)
                    if config:
                        service_record = f"✅ {plan['name']} | {plan['volume']} | {datetime.now().strftime('%Y-%m-%d')}"
                        if str(target) not in DB["users"]:
                            DB["users"][str(target)] = {"purchases": [], "tests": [], "test_count": 0}
                        DB["users"][str(target)]["purchases"].append(service_record)
                        save_db()
                        msg = f"🎉 سرویس شما آماده است\n━━━━━━━━━━━━━━━━━\n👤 {name}\n📦 {plan['name']}\n━━━━━━━━━━━━━━━━━\n🔗 لینک اتصال:\n`{config}`\n\n📚 {DB['guide']}"
                        try:
                            context.bot.send_message(int(target), msg, parse_mode='Markdown')
                            update.message.reply_text("✅ کانفیگ ارسال شد")
                        except:
                            update.message.reply_text("❌ خطا در ارسال")
                    else:
                        update.message.reply_text(f"❌ خطا: {error}")
                user_data[uid] = {}
                return

        # مرحله انتظار نام اکانت
        if step == 'wait_name':
            user_data[uid]['account'] = text
            user_data[uid]['step'] = 'wait_discount'
            update.message.reply_text("🎫 اگر کد تخفیف دارید وارد کنید، در غیر اینصورت 'ندارم' را بفرستید:", reply_markup=back_btn())
            return

        # مرحله انتظار کد تخفیف
        if step == 'wait_discount':
            p = user_data[uid]['plan']
            account_name = user_data[uid]['account']
            price_toman = p['price'] * 1000
            discount_text = ""
            
            if text.upper() != 'ندارم':
                code = text.upper()
                if code in DB.get("discount_codes", {}):
                    code_data = DB["discount_codes"][code]
                    if code_data["expires"] > datetime.now().timestamp() and code_data["uses"] < code_data["max_uses"]:
                        discount = code_data["discount_percent"]
                        price_toman = price_toman * (100 - discount) // 100
                        code_data["uses"] += 1
                        save_db()
                        discount_text = f"\n🎫 تخفیف: {discount}%"
                        user_data[uid]['discount_code'] = code
                    else:
                        discount_text = "\n❌ کد تخفیف نامعتبر یا منقضی"
                else:
                    discount_text = "\n❌ کد تخفیف نامعتبر"
            
            msg = f"💳 اطلاعات پرداخت\n━━━━━━━━━━━━━━\n👤 نام اکانت: {account_name}\n📦 پلن: {p['name']}\n💰 مبلغ: {price_toman:,} تومان{discount_text}\n━━━━━━━━━━━━━━\n💳 شماره کارت:\n{DB['card']['number']}\n👤 {DB['card']['name']}\n━━━━━━━━━━━━━━\nپس از واریز، عکس فیش را بفرستید"
            
            btn = InlineKeyboardMarkup([[InlineKeyboardButton("📤 ارسال فیش", callback_data="receipt")]])
            update.message.reply_text(msg, reply_markup=btn)

    except Exception as e:
        logger.error(f"Error: {e}")
        update.message.reply_text("❌ خطا، دوباره تلاش کنید")

def handle_cb(update, context):
    global DB, user_data
    try:
        query = update.callback_query
        uid = str(query.from_user.id)
        
        if uid in DB.get("blocked_users", []):
            query.answer()
            query.message.reply_text("🚫 شما توسط ادمین بلاک شده‌اید")
            return
        
        query.answer()

        if query.data == "join_check":
            if check_join(uid, context):
                query.message.delete()
                context.bot.send_message(uid, DB["texts"]["welcome"].format(brand=DB["brand"]), reply_markup=main_menu(uid))
            else:
                query.message.reply_text("❌ شما هنوز عضو کانال نشده‌اید!")
            return

        if query.data.startswith("buy_"):
            pid = int(query.data.split("_")[1])
            for cat in DB["categories"].values():
                for p in cat:
                    if p["id"] == pid:
                        user_data[uid] = {'step': 'wait_name', 'plan': p}
                        query.message.reply_text("📝 نام اکانت را وارد کنید:")
                        return
            query.message.reply_text("❌ پلن یافت نشد")

        elif query.data == "receipt":
            if uid in user_data and 'plan' in user_data[uid]:
                user_data[uid]['step'] = 'wait_photo'
                query.message.reply_text("📸 عکس فیش را بفرستید:")
            else:
                query.message.reply_text("❌ خطا")

        elif query.data.startswith("renew_"):
            index = int(query.data.split("_")[1])
            purchases = DB["users"][uid].get("purchases", [])
            if index < len(purchases):
                service = purchases[index]
                for cat in DB["categories"].values():
                    for p in cat:
                        if p['volume'] in service:
                            user_data[uid] = {'step': 'wait_name', 'plan': p}
                            query.message.reply_text("📝 نام اکانت را وارد کنید:")
                            return
                query.message.reply_text("❌ پلن یافت نشد")
            else:
                query.message.reply_text("❌ سرویس یافت نشد")

        elif query.data.startswith("del_"):
            if str(uid) == str(ADMIN_ID):
                pid = int(query.data.split("_")[1])
                for cat in DB["categories"].values():
                    for i, p in enumerate(cat):
                        if p["id"] == pid:
                            del cat[i]
                            save_db()
                            query.message.reply_text("✅ پلن حذف شد")
                            return
                query.message.reply_text("❌ یافت نشد")

        elif query.data.startswith("approve_"):
            if str(uid) == str(ADMIN_ID):
                encoded = query.data.replace("approve_", "")
                try:
                    plan_data = json.loads(base64.b64decode(encoded).decode())
                    target_uid = plan_data['uid']
                    
                    query.message.edit_reply_markup(reply_markup=None)
                    context.bot.send_message(ADMIN_ID, f"🔄 در حال ساخت اکانت...")
                    
                    config, error = create_account_on_panel(plan_data['plan'], plan_data['account'])
                    
                    if config:
                        service_record = f"✅ {plan_data['plan']['name']} | {plan_data['plan']['volume']} | {datetime.now().strftime('%Y-%m-%d')}"
                        if str(target_uid) not in DB["users"]:
                            DB["users"][str(target_uid)] = {"purchases": [], "tests": [], "test_count": 0}
                        DB["users"][str(target_uid)]["purchases"].append(service_record)
                        save_db()
                        
                        msg = f"✅ پرداخت شما تأیید شد!\n━━━━━━━━━━━━━━━━━\n👤 {plan_data['account']}\n📦 {plan_data['plan']['name']}\n━━━━━━━━━━━━━━━━━\n🔗 لینک اتصال:\n`{config}`\n\n📚 {DB['guide']}"
                        try:
                            context.bot.send_message(int(target_uid), msg, parse_mode='Markdown')
                            context.bot.send_message(ADMIN_ID, f"✅ کانفیگ برای {target_uid} ارسال شد")
                        except Exception as e:
                            context.bot.send_message(ADMIN_ID, f"❌ خطا در ارسال: {e}")
                    else:
                        context.bot.send_message(ADMIN_ID, f"❌ خطا در ساخت اکانت: {error}")
                except Exception as e:
                    context.bot.send_message(ADMIN_ID, f"❌ خطا در پردازش: {e}")

        elif query.data.startswith("reject_"):
            if str(uid) == str(ADMIN_ID):
                target_uid = query.data.split("_")[1]
                user_data[ADMIN_ID] = {'step': 'reject_reason', 'target': target_uid}
                query.message.reply_text("دلیل رد فیش را وارد کنید:")
                query.message.edit_reply_markup(reply_markup=None)

    except Exception as e:
        logger.error(f"Callback error: {e}")
        if 'query' in locals():
            query.message.reply_text("❌ خطا")

def handle_photo(update, context):
    global DB, user_data
    try:
        uid = str(update.effective_user.id)
        
        if uid in DB.get("blocked_users", []):
            update.message.reply_text("🚫 شما توسط ادمین بلاک شده‌اید")
            return
        
        if user_data.get(uid, {}).get('step') == 'wait_photo':
            if 'plan' not in user_data[uid] or 'account' not in user_data[uid]:
                update.message.reply_text("❌ اطلاعات خرید یافت نشد")
                return
            
            p = user_data[uid]['plan']
            acc = user_data[uid]['account']
            price_toman = p['price'] * 1000
            user_info = get_user_info(uid, context)
            
            discount_text = ""
            if 'discount_code' in user_data[uid]:
                discount_text = f"\n🎫 کد تخفیف: {user_data[uid]['discount_code']}"
            
            cap = f"💰 فیش جدید\n━━━━━━━━━━━━━━━━━\n👤 {user_info}\n🆔 {uid}\n📦 {p['name']}\n👤 اکانت: {acc}\n💰 {price_toman:,} تومان{discount_text}"
            
            plan_data = {'uid': uid, 'plan': p, 'account': acc}
            encoded = base64.b64encode(json.dumps(plan_data).encode()).decode()
            
            btn = InlineKeyboardMarkup([[
                InlineKeyboardButton("✅ تایید", callback_data=f"approve_{encoded}"),
                InlineKeyboardButton("❌ رد", callback_data=f"reject_{uid}")
            ]])
            
            context.bot.send_photo(ADMIN_ID, update.message.photo[-1].file_id, caption=cap, reply_markup=btn)
            update.message.reply_text("✅ فیش ارسال شد، پس از تایید سرویس شما فعال می‌شود")
            del user_data[uid]
    except Exception as e:
        logger.error(f"Photo error: {e}")

def main():
    try:
        logger.info("🚀 Starting bot...")
        
        # بارگذاری دیتابیس
        load_db()
        
        # ریست وب‌هوک
        reset_webhook()
        
        # ایجاد پوشه بکاپ
        if not os.path.exists(BACKUP_DIR):
            os.makedirs(BACKUP_DIR)
        
        # اجرای وب سرور
        Thread(target=run_web, daemon=True).start()
        
        # راه‌اندازی ربات
        updater = Updater(TOKEN, use_context=True)
        dp = updater.dispatcher
        
        dp.add_handler(CommandHandler("start", start))
        dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_msg))
        dp.add_handler(MessageHandler(Filters.photo, handle_photo))
        dp.add_handler(CallbackQueryHandler(handle_cb))
        
        updater.start_polling(poll_interval=1.0, timeout=30)
        logger.info("✅ Bot is running!")
        updater.idle()
        
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")

if __name__ == '__main__':
    main()
