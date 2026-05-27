import os
import json
import logging
from flask import Flask
from threading import Thread
from telegram import ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, CallbackQueryHandler, Filters
from datetime import datetime, timedelta
import traceback
import requests
import random
import string
import shutil

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
TOKEN = '8765075222:AAFT6p_zeYmEcahPoezxtUeqMlsGz0Ra35o'
ADMIN_ID = 5993860770

# --- تنظیمات پنل (قابل ویرایش توسط ادمین) ---
PANEL_CONFIG = {
    "enabled": False,
    "api_url": "",
    "api_key": "",
    "test_config": {
        "volume": 50,
        "expiry_hours": 3,
        "enabled": True
    }
}

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

def load_db():
    try:
        if os.path.exists(DB_FILE):
            with open(DB_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                logger.info("✅ Database loaded")
                
                if "force_join" not in data:
                    data["force_join"] = {"enabled": False, "channel_id": "", "channel_link": "", "channel_username": ""}
                if "invite_text" not in data["texts"]:
                    data["texts"]["invite"] = "🤝 لینک دعوت شما:\n{link}\n\nبه ازای هر دعوت 1 روز هدیه"
                if "discount_codes" not in data:
                    data["discount_codes"] = {}
                if "blocked_users" not in data:
                    data["blocked_users"] = []
                if "panel_config" not in data:
                    data["panel_config"] = PANEL_CONFIG.copy()
                return data
    except Exception as e:
        logger.error(f"❌ Error loading: {e}")
    
    logger.info("📁 Creating default database")
    return {
        "users": {},
        "brand": "تک نت وی‌پی‌ان",
        "card": {
            "number": "6277601368776066",
            "name": "محمد رضوانی"
        },
        "support": "@Support_Admin",
        "guide": "@Guide_Channel",
        "categories": DEFAULT_PLANS.copy(),
        "force_join": {"enabled": False, "channel_id": "", "channel_link": "", "channel_username": ""},
        "discount_codes": {},
        "blocked_users": [],
        "panel_config": PANEL_CONFIG.copy(),
        "texts": {
            "welcome": "🔰 به {brand} خوش آمدید\n\n✅ فروش ویژه فیلترشکن\n✅ پشتیبانی 24 ساعته\n✅ نصب آسان",
            "support": "🆘 پشتیبانی: {support}",
            "guide": "📚 آموزش: {guide}",
            "test": "🎁 درخواست تست شما ثبت شد",
            "force": "🔒 برای استفاده از ربات باید در کانال زیر عضو شوید:\n{link}\n\nپس از عضویت، دکمه ✅ تایید را بزنید.",
            "invite": "🤝 لینک دعوت شما:\n{link}\n\nبه ازای هر دعوت 1 روز هدیه"
        }
    }

def save_db(data):
    try:
        with open(DB_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
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
    except Exception as e:
        logger.error(f"Backup error: {e}")
        return None

def restore_backup(backup_file):
    try:
        backup_path = os.path.join(BACKUP_DIR, backup_file)
        if os.path.exists(backup_path):
            shutil.copy2(backup_path, DB_FILE)
            return True
    except Exception as e:
        logger.error(f"Restore error: {e}")
    return False

def get_user_info(uid, context):
    try:
        user = context.bot.get_chat(int(uid))
        username = user.username
        if username:
            return f"@{username}"
        else:
            first_name = user.first_name or ""
            last_name = user.last_name or ""
            return f"{first_name} {last_name}".strip() or str(uid)
    except:
        return str(uid)

def generate_discount_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

def apply_discount(price, discount_code, db_data):
    if discount_code in db_data.get("discount_codes", {}):
        code_data = db_data["discount_codes"][discount_code]
        if code_data["expires"] > datetime.now().timestamp():
            if code_data["uses"] < code_data["max_uses"]:
                discount = code_data["discount_percent"]
                new_price = price * (100 - discount) // 100
                return new_price, discount
    return price, 0

def create_account_on_panel(plan, account_name, db_data):
    panel = db_data.get("panel_config", {})
    if not panel.get("enabled"):
        return None, "پنل متصل نیست"
    
    try:
        volume = plan.get("volume", "0GB")
        volume_bytes = 0
        if "GB" in volume:
            volume_bytes = int(volume.replace("GB", "").strip()) * 1024 * 1024 * 1024
        elif "MB" in volume:
            volume_bytes = int(volume.replace("MB", "").strip()) * 1024 * 1024
        
        payload = {
            "username": f"{account_name}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "data_limit": volume_bytes,
            "expiry": int((datetime.now() + timedelta(days=plan.get("days", 30))).timestamp()),
            "status": "active"
        }
        
        headers = {
            "Authorization": f"Bearer {panel.get('api_key')}",
            "Content-Type": "application/json"
        }
        
        response = requests.post(
            f"{panel.get('api_url')}/api/user",
            json=payload,
            headers=headers,
            timeout=30
        )
        
        if response.status_code in [200, 201]:
            data = response.json()
            config_response = requests.get(
                f"{panel.get('api_url')}/api/user/{payload['username']}/config",
                headers=headers,
                timeout=30
            )
            if config_response.status_code == 200:
                return config_response.json().get("config"), None
            return data.get("subscription_url"), None
        
        return None, f"خطای API: {response.status_code}"
    except Exception as e:
        logger.error(f"Panel API error: {e}")
        return None, str(e)

def create_test_account(db_data):
    panel = db_data.get("panel_config", {})
    test_config = panel.get("test_config", {})
    
    if not panel.get("enabled") or not test_config.get("enabled"):
        return None, "تست غیرفعال است یا پنل متصل نیست"
    
    try:
        volume_bytes = test_config.get("volume", 50) * 1024 * 1024
        expiry_hours = test_config.get("expiry_hours", 3)
        
        payload = {
            "username": f"test_{datetime.now().strftime('%Y%m%d%H%M%S')}_{random.randint(1000,9999)}",
            "data_limit": volume_bytes,
            "expiry": int((datetime.now() + timedelta(hours=expiry_hours)).timestamp()),
            "status": "active"
        }
        
        headers = {
            "Authorization": f"Bearer {panel.get('api_key')}",
            "Content-Type": "application/json"
        }
        
        response = requests.post(
            f"{panel.get('api_url')}/api/user",
            json=payload,
            headers=headers,
            timeout=30
        )
        
        if response.status_code in [200, 201]:
            data = response.json()
            config_response = requests.get(
                f"{panel.get('api_url')}/api/user/{payload['username']}/config",
                headers=headers,
                timeout=30
            )
            if config_response.status_code == 200:
                return config_response.json().get("config"), None
            return data.get("subscription_url"), None
        
        return None, f"خطای API: {response.status_code}"
    except Exception as e:
        logger.error(f"Test account error: {e}")
        return None, str(e)

db = load_db()
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
    if not db["force_join"]["enabled"]:
        return True
    
    channel_id = db["force_join"].get("channel_id", "")
    channel_username = db["force_join"].get("channel_username", "")
    
    if not channel_id and not channel_username:
        return True
    
    if channel_id:
        try:
            member = context.bot.get_chat_member(
                chat_id=int(channel_id),
                user_id=int(user_id)
            )
            if member.status in ['member', 'administrator', 'creator']:
                return True
        except:
            pass
    
    if channel_username:
        try:
            member = context.bot.get_chat_member(
                chat_id=channel_username,
                user_id=int(user_id)
            )
            if member.status in ['member', 'administrator', 'creator']:
                return True
        except:
            pass
    
    return False

def start(update, context):
    uid = str(update.effective_user.id)
    
    if uid in db.get("blocked_users", []):
        update.message.reply_text("🚫 شما توسط ادمین بلاک شده‌اید")
        return
    
    if uid not in db["users"]:
        db["users"][uid] = {
            "purchases": [],
            "tests": [],
            "test_count": 0,
            "date": datetime.now().strftime("%Y-%m-%d")
        }
        save_db(db)
    
    user_data[uid] = {}
    
    if db["force_join"]["enabled"] and db["force_join"]["channel_link"]:
        if not check_join(uid, context):
            btn = InlineKeyboardMarkup([[
                InlineKeyboardButton("📢 عضویت در کانال", url=db["force_join"]["channel_link"]),
                InlineKeyboardButton("✅ تایید عضویت", callback_data="join_check")
            ]])
            msg = db["texts"]["force"].format(link=db["force_join"]["channel_link"])
            update.message.reply_text(msg, reply_markup=btn)
            return
    
    welcome = db["texts"]["welcome"].format(brand=db["brand"])
    update.message.reply_text(welcome, reply_markup=main_menu(uid))

def handle_msg(update, context):
    global db
    try:
        text = update.message.text
        uid = str(update.effective_user.id)
        name = update.effective_user.first_name or "کاربر"
        
        if uid in db.get("blocked_users", []):
            update.message.reply_text("🚫 شما توسط ادمین بلاک شده‌اید")
            return
        
        step = user_data.get(uid, {}).get('step')

        if db["force_join"]["enabled"] and db["force_join"]["channel_link"]:
            if not check_join(uid, context) and text != '/start':
                btn = InlineKeyboardMarkup([[
                    InlineKeyboardButton("📢 عضویت در کانال", url=db["force_join"]["channel_link"]),
                    InlineKeyboardButton("✅ تایید عضویت", callback_data="join_check")
                ]])
                update.message.reply_text(
                    db["texts"]["force"].format(link=db["force_join"]["channel_link"]),
                    reply_markup=btn
                )
                return

        if text == '🔙 برگشت':
            user_data[uid] = {}
            start(update, context)
            return

        if text == '🎁 تست':
            panel_config = db.get("panel_config", {})
            if not panel_config.get("enabled"):
                update.message.reply_text("❌ سرویس تست در حال حاضر غیرفعال است")
                return
            
            if db["users"][uid]["test_count"] >= 1:
                update.message.reply_text("❌ شما قبلاً تست گرفته‌اید")
                return
            
            update.message.reply_text("🔄 در حال ساخت اکانت تست...")
            
            config, error = create_test_account(db)
            
            if config:
                db["users"][uid]["test_count"] += 1
                db["users"][uid]["tests"].append(datetime.now().strftime("%Y-%m-%d"))
                save_db(db)
                
                msg = (
                    f"🎁 اکانت تست شما آماده است\n"
                    f"━━━━━━━━━━━━━━━━━\n"
                    f"⏱ مدت: {panel_config.get('test_config', {}).get('expiry_hours', 3)} ساعت\n"
                    f"📦 حجم: {panel_config.get('test_config', {}).get('volume', 50)} مگابایت\n\n"
                    f"🔗 لینک اتصال:\n`{config}`\n\n"
                    f"📚 {db['guide']}"
                )
                update.message.reply_text(msg, parse_mode='Markdown')
            else:
                update.message.reply_text(f"❌ خطا در ساخت اکانت تست: {error}")
            return

        if text == '📂 سرویس‌ها':
            pur = db["users"][uid].get("purchases", [])
            tests = db["users"][uid].get("tests", [])
            
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

        if text == '⏳ تمدید':
            pur = db["users"][uid].get("purchases", [])
            if not pur:
                update.message.reply_text("❌ سرویسی برای تمدید ندارید")
                return
            
            keyboard = []
            for i, p in enumerate(pur[-5:]):
                keyboard.append([InlineKeyboardButton(
                    f"🔄 {p[:30]}...",
                    callback_data=f"renew_{i}"
                )])
            update.message.reply_text(
                "سرویس مورد نظر را انتخاب کنید:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return

        if text == '👤 پشتیبانی':
            update.message.reply_text(db["texts"]["support"].format(support=db["support"]))
            return

        if text == '📚 آموزش':
            update.message.reply_text(db["texts"]["guide"].format(guide=db["guide"]))
            return

        if text == '🤝 دعوت دوستان':
            bot = context.bot.get_me().username
            link = f"https://t.me/{bot}?start={uid}"
            msg = db["texts"]["invite"].format(link=link)
            update.message.reply_text(msg)
            return

        if text == '💰 خرید':
            cats = list(db["categories"].keys())
            kb = [[c] for c in cats] + [['🔙 برگشت']]
            update.message.reply_text(
                "دسته را انتخاب کنید:",
                reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True)
            )
            return

        if text in db["categories"] and not step:
            plans = db["categories"][text]
            keyboard = []
            for p in plans:
                price_toman = p['price'] * 1000
                btn = InlineKeyboardButton(
                    f"{p['name']} - {price_toman:,} تومان",
                    callback_data=f"buy_{p['id']}"
                )
                keyboard.append([btn])
            update.message.reply_text(
                f"📦 {text}",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return

        if str(uid) == str(ADMIN_ID):
            
            if text == '⚙️ مدیریت':
                update.message.reply_text("🛠 پنل مدیریت:", reply_markup=admin_menu())
                return

            if text == '🔌 تنظیمات پنل':
                keyboard = [
                    ['✅ فعال کردن پنل', '❌ غیرفعال کردن پنل'],
                    ['🔗 تنظیم API', '🔑 تنظیم API Key'],
                    ['🔙 برگشت']
                ]
                status = "✅ فعال" if db["panel_config"]["enabled"] else "❌ غیرفعال"
                update.message.reply_text(
                    f"🔌 وضعیت پنل: {status}\nآدرس API: {db['panel_config'].get('api_url', 'تنظیم نشده')}",
                    reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
                )
                return

            if text == '✅ فعال کردن پنل':
                db["panel_config"]["enabled"] = True
                save_db(db)
                update.message.reply_text("✅ پنل فعال شد", reply_markup=admin_menu())
                return

            if text == '❌ غیرفعال کردن پنل':
                db["panel_config"]["enabled"] = False
                save_db(db)
                update.message.reply_text("❌ پنل غیرفعال شد", reply_markup=admin_menu())
                return

            if text == '🔗 تنظیم API':
                user_data[uid] = {'step': 'set_api_url'}
                update.message.reply_text("آدرس API پنل را بفرستید:\nمثال: https://panel.example.com", reply_markup=back_btn())
                return

            if text == '🔑 تنظیم API Key':
                user_data[uid] = {'step': 'set_api_key'}
                update.message.reply_text("API Key پنل را بفرستید:", reply_markup=back_btn())
                return

            if text == '🎁 تنظیمات تست':
                test_config = db["panel_config"].get("test_config", {})
                keyboard = [
                    ['📊 حجم تست (MB)', '⏱ مدت تست (ساعت)'],
                    ['✅ فعال کردن تست', '❌ غیرفعال کردن تست'],
                    ['🔙 برگشت']
                ]
                status = "✅ فعال" if test_config.get("enabled") else "❌ غیرفعال"
                update.message.reply_text(
                    f"🎁 تنظیمات تست:\nوضعیت: {status}\nحجم: {test_config.get('volume', 50)} مگابایت\nمدت: {test_config.get('expiry_hours', 3)} ساعت",
                    reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
                )
                return

            if text == '📊 حجم تست (MB)':
                user_data[uid] = {'step': 'set_test_volume'}
                update.message.reply_text("حجم تست را به مگابایت وارد کنید (مثال: 50):", reply_markup=back_btn())
                return

            if text == '⏱ مدت تست (ساعت)':
                user_data[uid] = {'step': 'set_test_hours'}
                update.message.reply_text("مدت تست را به ساعت وارد کنید (مثال: 3):", reply_markup=back_btn())
                return

            if text == '✅ فعال کردن تست':
                db["panel_config"]["test_config"]["enabled"] = True
                save_db(db)
                update.message.reply_text("✅ تست فعال شد", reply_markup=admin_menu())
                return

            if text == '❌ غیرفعال کردن تست':
                db["panel_config"]["test_config"]["enabled"] = False
                save_db(db)
                update.message.reply_text("❌ تست غیرفعال شد", reply_markup=admin_menu())
                return

            if text == '🎫 کد تخفیف':
                update.message.reply_text("🎫 مدیریت کدهای تخفیف:", reply_markup=discount_codes_menu())
                return

            if text == '➕ ساخت کد تخفیف':
                user_data[uid] = {'step': 'make_discount_percent'}
                update.message.reply_text("درصد تخفیف را وارد کنید (مثال: 20):", reply_markup=back_btn())
                return

            if text == '📋 لیست کدها':
                codes = db.get("discount_codes", {})
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

            if text == '🚫 بلاک کاربر':
                user_data[uid] = {'step': 'block_user'}
                update.message.reply_text("آیدی عددی کاربر را برای بلاک وارد کنید:", reply_markup=back_btn())
                return

            if text == '💾 بکاپ':
                backup_file = create_backup()
                if backup_file:
                    update.message.reply_text(f"✅ بکاپ گرفته شد: {backup_file}")
                else:
                    update.message.reply_text("❌ خطا در گرفتن بکاپ")
                return

            if text == '🔄 بازیابی بکاپ':
                backups = [f for f in os.listdir(BACKUP_DIR) if f.endswith('.json')] if os.path.exists(BACKUP_DIR) else []
                if not backups:
                    update.message.reply_text("❌ هیچ بکاپی یافت نشد")
                else:
                    keyboard = [[f"🔄 {b}"] for b in backups[-10:]] + [['🔙 برگشت']]
                    user_data[uid] = {'step': 'restore_backup'}
                    update.message.reply_text(
                        "بکاپ مورد نظر را انتخاب کنید:",
                        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
                    )
                return

            if text == '💳 ویرایش کارت':
                keyboard = [
                    ['شماره کارت', 'نام صاحب کارت'],
                    ['🔙 برگشت']
                ]
                current = f"شماره: {db['card']['number']}\nنام: {db['card']['name']}"
                update.message.reply_text(
                    current,
                    reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
                )
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
                keyboard = [
                    ['خوش‌آمدگویی', 'پشتیبانی', 'آموزش'],
                    ['تست رایگان', 'عضویت اجباری', 'دعوت دوستان'],
                    ['🔙 برگشت']
                ]
                update.message.reply_text(
                    "📝 کدام متن را ویرایش کنیم؟",
                    reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
                )
                return

            text_map = {
                'خوش‌آمدگویی': 'welcome',
                'پشتیبانی': 'support',
                'آموزش': 'guide',
                'تست رایگان': 'test',
                'عضویت اجباری': 'force',
                'دعوت دوستان': 'invite'
            }
            
            if text in text_map:
                user_data[uid] = {'step': f'edit_{text_map[text]}'}
                current_text = db["texts"][text_map[text]]
                update.message.reply_text(
                    f"متن فعلی:\n{current_text}\n\nمتن جدید را بفرستید:",
                    reply_markup=back_btn()
                )
                return

            if text == '🔒 عضویت اجباری':
                keyboard = [
                    ['✅ فعال', '❌ غیرفعال'],
                    ['🔗 تنظیم لینک کانال'],
                    ['🔙 برگشت']
                ]
                status = "✅ فعال" if db["force_join"]["enabled"] else "❌ غیرفعال"
                channel = db["force_join"]["channel_username"] or "تنظیم نشده"
                update.message.reply_text(
                    f"🔒 وضعیت:\nوضعیت: {status}\nکانال: {channel}",
                    reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
                )
                return

            if text == '✅ فعال':
                if db["force_join"]["channel_link"]:
                    db["force_join"]["enabled"] = True
                    save_db(db)
                    update.message.reply_text("✅ عضویت اجباری فعال شد", reply_markup=admin_menu())
                else:
                    update.message.reply_text("❌ ابتدا لینک کانال را تنظیم کنید")
                return

            if text == '❌ غیرفعال':
                db["force_join"]["enabled"] = False
                save_db(db)
                update.message.reply_text("✅ عضویت اجباری غیرفعال شد", reply_markup=admin_menu())
                return

            if text == '🔗 تنظیم لینک کانال':
                user_data[uid] = {'step': 'set_link'}
                update.message.reply_text(
                    "🔗 لینک کانال را بفرستید:\nمثال: https://t.me/mychannel",
                    reply_markup=back_btn()
                )
                return

            if text == '📊 آمار':
                total = len(db["users"])
                pur = sum(len(u.get("purchases", [])) for u in db["users"].values())
                tests = sum(len(u.get("tests", [])) for u in db["users"].values())
                today = datetime.now().strftime("%Y-%m-%d")
                today_users = sum(1 for u in db["users"].values() if u.get("date", "").startswith(today))
                
                update.message.reply_text(
                    f"📊 آمار ربات\n"
                    f"━━━━━━━━━━\n"
                    f"👥 کل کاربران: {total}\n"
                    f"🆕 امروز: {today_users}\n"
                    f"💰 خریدها: {pur}\n"
                    f"🎁 تست‌ها: {tests}"
                )
                return

            if text == '📨 ارسال همگانی':
                user_data[uid] = {'step': 'broadcast'}
                update.message.reply_text(
                    "📨 پیام همگانی را بفرستید:",
                    reply_markup=back_btn()
                )
                return

            if text == '➕ پلن جدید':
                cats = list(db["categories"].keys())
                kb = [[c] for c in cats] + [['🔙 برگشت']]
                user_data[uid] = {'step': 'new_cat'}
                update.message.reply_text(
                    "دسته را انتخاب کنید:",
                    reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True)
                )
                return

            if text == '➖ حذف پلن':
                keyboard = []
                for cat, plans in db["categories"].items():
                    for p in plans:
                        btn = InlineKeyboardButton(
                            f"❌ {cat} - {p['name']}",
                            callback_data=f"del_{p['id']}"
                        )
                        keyboard.append([btn])
                if keyboard:
                    update.message.reply_text(
                        "پلن را انتخاب کنید:",
                        reply_markup=InlineKeyboardMarkup(keyboard)
                    )
                else:
                    update.message.reply_text("❌ پلنی نیست")
                return

            if step == 'card_num':
                if text.isdigit() and len(text) == 16:
                    db["card"]["number"] = text
                    save_db(db)
                    update.message.reply_text("✅ شماره کارت ذخیره شد", reply_markup=admin_menu())
                else:
                    update.message.reply_text("❌ شماره کارت نامعتبر")
                user_data[uid] = {}
                return

            if step == 'card_name':
                db["card"]["name"] = text
                save_db(db)
                update.message.reply_text("✅ نام صاحب کارت ذخیره شد", reply_markup=admin_menu())
                user_data[uid] = {}
                return

            if step == 'support':
                db["support"] = text
                save_db(db)
                update.message.reply_text("✅ پشتیبان ذخیره شد", reply_markup=admin_menu())
                user_data[uid] = {}
                return

            if step == 'guide':
                db["guide"] = text
                save_db(db)
                update.message.reply_text("✅ کانال آموزش ذخیره شد", reply_markup=admin_menu())
                user_data[uid] = {}
                return

            if step == 'brand':
                db["brand"] = text
                save_db(db)
                update.message.reply_text("✅ برند ذخیره شد", reply_markup=admin_menu())
                user_data[uid] = {}
                return

            if step and step.startswith('edit_'):
                key = step.replace('edit_', '')
                db["texts"][key] = text
                save_db(db)
                update.message.reply_text("✅ متن ذخیره شد", reply_markup=admin_menu())
                user_data[uid] = {}
                return

            if step == 'set_link':
                db["force_join"]["channel_link"] = text
                if 't.me/' in text:
                    username = text.split('t.me/')[-1].split('/')[0].replace('@', '')
                    db["force_join"]["channel_username"] = f"@{username}"
                    try:
                        chat = context.bot.get_chat(f"@{username}")
                        db["force_join"]["channel_id"] = str(chat.id)
                        update.message.reply_text(f"✅ کانال شناسایی شد: {chat.title}")
                    except:
                        update.message.reply_text("⚠️ ربات در کانال ادمین نیست!")
                save_db(db)
                update.message.reply_text("✅ لینک ذخیره شد", reply_markup=admin_menu())
                user_data[uid] = {}
                return

            if step == 'broadcast':
                suc, fail = 0, 0
                for uid2 in db["users"]:
                    if uid2 not in db.get("blocked_users", []):
                        try:
                            context.bot.send_message(int(uid2), text)
                            suc += 1
                        except:
                            fail += 1
                update.message.reply_text(f"✅ ارسال شد\nموفق: {suc}\nناموفق: {fail}")
                user_data[uid] = {}
                return

            if step == 'set_api_url':
                db["panel_config"]["api_url"] = text.rstrip('/')
                save_db(db)
                update.message.reply_text("✅ آدرس API ذخیره شد", reply_markup=admin_menu())
                user_data[uid] = {}
                return

            if step == 'set_api_key':
                db["panel_config"]["api_key"] = text
                save_db(db)
                update.message.reply_text("✅ API Key ذخیره شد", reply_markup=admin_menu())
                user_data[uid] = {}
                return

            if step == 'set_test_volume':
                try:
                    volume = int(text)
                    db["panel_config"]["test_config"]["volume"] = volume
                    save_db(db)
                    update.message.reply_text(f"✅ حجم تست به {volume} مگابایت تغییر کرد", reply_markup=admin_menu())
                except:
                    update.message.reply_text("❌ عدد معتبر وارد کنید")
                user_data[uid] = {}
                return

            if step == 'set_test_hours':
                try:
                    hours = int(text)
                    db["panel_config"]["test_config"]["expiry_hours"] = hours
                    save_db(db)
                    update.message.reply_text(f"✅ مدت تست به {hours} ساعت تغییر کرد", reply_markup=admin_menu())
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
                    max_uses = int(text)
                    user_data[uid]['max_uses'] = max_uses
                    user_data[uid]['step'] = 'make_discount_days'
                    update.message.reply_text("مدت اعتبار (روز):")
                except:
                    update.message.reply_text("❌ عدد معتبر وارد کنید")
                return

            if step == 'make_discount_days':
                try:
                    days = int(text)
                    code = generate_discount_code()
                    db["discount_codes"][code] = {
                        "discount_percent": user_data[uid]['percent'],
                        "max_uses": user_data[uid]['max_uses'],
                        "uses": 0,
                        "expires": (datetime.now() + timedelta(days=days)).timestamp()
                    }
                    save_db(db)
                    update.message.reply_text(
                        f"✅ کد تخفیف ساخته شد:\n"
                        f"🎫 کد: `{code}`\n"
                        f"📊 درصد: {user_data[uid]['percent']}%\n"
                        f"📋 حداکثر استفاده: {user_data[uid]['max_uses']}\n"
                        f"⏱ اعتبار: {days} روز",
                        parse_mode='Markdown'
                    )
                    user_data[uid] = {}
                except:
                    update.message.reply_text("❌ عدد معتبر وارد کنید")
                return

            if step == 'del_discount_code':
                if text in db.get("discount_codes", {}):
                    del db["discount_codes"][text]
                    save_db(db)
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
                    else:
                        if target_id not in db.get("blocked_users", []):
                            db["blocked_users"].append(target_id)
                            save_db(db)
                            update.message.reply_text(f"✅ کاربر {target_id} بلاک شد")
                        else:
                            db["blocked_users"].remove(target_id)
                            save_db(db)
                            update.message.reply_text(f"✅ کاربر {target_id} آنبلاک شد")
                except:
                    update.message.reply_text("❌ آیدی عددی معتبر وارد کنید")
                user_data[uid] = {}
                return

            if step == 'restore_backup':
                if text.startswith('🔄 '):
                    backup_file = text[2:]
                    if restore_backup(backup_file):
                        db = load_db()
                        update.message.reply_text("✅ بکاپ با موفقیت بازیابی شد", reply_markup=admin_menu())
                    else:
                        update.message.reply_text("❌ خطا در بازیابی بکاپ")
                user_data[uid] = {}
                return

            if step == 'new_cat' and text in db["categories"]:
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
                    for p in db["categories"].values():
                        for plan in p:
                            if plan["id"] > max_id:
                                max_id = plan["id"]
                    
                    new_plan = {
                        "id": max_id + 1,
                        "name": user_data[uid]['name'],
                        "price": price,
                        "volume": user_data[uid]['vol'],
                        "days": user_data[uid]['days'],
                        "users": user_data[uid]['users']
                    }
                    
                    cat = user_data[uid]['cat']
                    db["categories"][cat].append(new_plan)
                    save_db(db)
                    
                    update.message.reply_text("✅ پلن اضافه شد", reply_markup=admin_menu())
                    user_data[uid] = {}
                except:
                    update.message.reply_text("❌ خطا")
                return

            if step == 'send_config':
                target = user_data[uid]['target']
                name = user_data[uid]['name']
                vol = user_data[uid].get('vol', 'نامحدود')
                plan = user_data[uid].get('plan')
                
                if plan:
                    config, error = create_account_on_panel(plan, name, db)
                    if config:
                        service_record = f"✅ {plan['name']} | {vol} | {datetime.now().strftime('%Y-%m-%d')}"
                        if str(target) not in db["users"]:
                            db["users"][str(target)] = {"purchases": [], "tests": [], "test_count": 0}
                        
                        if "purchases" not in db["users"][str(target)]:
                            db["users"][str(target)]["purchases"] = []
                        
                        db["users"][str(target)]["purchases"].append(service_record)
                        save_db(db)
                        
                        msg = (
                            f"🎉 سرویس شما آماده است\n"
                            f"👤 {name}\n"
                            f"📦 {plan['name']}\n"
                            f"━━━━━━━━━━━━━━━━━\n"
                            f"🔗 لینک اتصال:\n`{config}`\n\n"
                            f"📚 {db['guide']}"
                        )
                        
                        try:
                            context.bot.send_message(int(target), msg, parse_mode='Markdown')
                            update.message.reply_text("✅ کانفیگ ارسال شد")
                        except:
                            update.message.reply_text("❌ خطا در ارسال")
                    else:
                        update.message.reply_text(f"❌ خطا در ساخت اکانت: {error}")
                
                user_data[uid] = {}
                return

        if step == 'wait_name':
            user_data[uid]['account'] = text
            user_data[uid]['step'] = 'wait_discount'
            update.message.reply_text(
                "🎫 اگر کد تخفیف دارید وارد کنید، در غیر اینصورت 'ندارم' را بفرستید:",
                reply_markup=back_btn()
            )
            return

        if step == 'wait_discount':
            p = user_data[uid]['plan']
            account_name = user_data[uid]['account']
            
            price_toman = p['price'] * 1000
            discount_percent = 0
            
            if text.upper() != 'ندارم':
                new_price, discount_percent = apply_discount(p['price'] * 1000, text.upper(), db)
                if discount_percent > 0:
                    price_toman = new_price
                    user_data[uid]['discount_code'] = text.upper()
                    if text.upper() in db["discount_codes"]:
                        db["discount_codes"][text.upper()]["uses"] += 1
                        save_db(db)
                    discount_text = f"\n🎫 تخفیف: {discount_percent}%"
                else:
                    discount_text = "\n❌ کد تخفیف نامعتبر"
            else:
                discount_text = ""
            
            msg = (
                f"💳 اطلاعات پرداخت\n"
                f"━━━━━━━━━━━━━━\n"
                f"👤 نام اکانت: {account_name}\n"
                f"📦 پلن: {p['name']}\n"
                f"💰 مبلغ: {price_toman:,} تومان{discount_text}\n"
                f"━━━━━━━━━━━━━━\n"
                f"💳 شماره کارت:\n{db['card']['number']}\n"
                f"👤 {db['card']['name']}\n"
                f"━━━━━━━━━━━━━━\n"
                "پس از واریز، عکس فیش را بفرستید"
            )
            
            btn = InlineKeyboardMarkup([[
                InlineKeyboardButton("📤 ارسال فیش", callback_data="receipt")
            ]])
            
            update.message.reply_text(msg, reply_markup=btn)

    except Exception as e:
        logger.error(f"Error: {e}")
        update.message.reply_text("❌ خطا، دوباره تلاش کنید")

def handle_cb(update, context):
    global db
    try:
        query = update.callback_query
        uid = str(query.from_user.id)
        
        if uid in db.get("blocked_users", []):
            query.answer()
            query.message.reply_text("🚫 شما توسط ادمین بلاک شده‌اید")
            return
        
        query.answer()

        if query.data == "join_check":
            if check_join(uid, context):
                query.message.delete()
                welcome = db["texts"]["welcome"].format(brand=db["brand"])
                context.bot.send_message(uid, welcome, reply_markup=main_menu(uid))
            else:
                query.message.reply_text(
                    "❌ شما هنوز عضو کانال نشده‌اید!\n"
                    "لطفاً ابتدا عضو شوید سپس دکمه تایید را بزنید."
                )
            return

        if query.data.startswith("buy_"):
            pid = int(query.data.split("_")[1])
            for cat in db["categories"].values():
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
            purchases = db["users"][uid].get("purchases", [])
            
            if index < len(purchases):
                service = purchases[index]
                for cat in db["categories"].values():
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
                for cat in db["categories"].values():
                    for i, p in enumerate(cat):
                        if p["id"] == pid:
                            del cat[i]
                            save_db(db)
                            query.message.reply_text("✅ پلن حذف شد")
                            return
                query.message.reply_text("❌ یافت نشد")

        elif query.data.startswith("approve_"):
            if str(uid) == str(ADMIN_ID):
                parts = query.data.split("_")
                target_uid = parts[1]
                # بازگرداندن plan_data از قسمت‌های باقی‌مانده
                plan_json = "_".join(parts[2:])
                plan_data = json.loads(plan_json)
                
                query.message.edit_reply_markup(reply_markup=None)
                context.bot.send_message(ADMIN_ID, f"🔄 در حال ساخت اکانت برای {target_uid}...")
                
                config, error = create_account_on_panel(plan_data['plan'], plan_data['account'], db)
                
                if config:
                    service_record = f"✅ {plan_data['plan']['name']} | {plan_data['plan']['volume']} | {datetime.now().strftime('%Y-%m-%d')}"
                    if str(target_uid) not in db["users"]:
                        db["users"][str(target_uid)] = {"purchases": [], "tests": [], "test_count": 0}
                    
                    if "purchases" not in db["users"][str(target_uid)]:
                        db["users"][str(target_uid)]["purchases"] = []
                    
                    db["users"][str(target_uid)]["purchases"].append(service_record)
                    save_db(db)
                    
                    msg = (
                        f"✅ پرداخت شما تأیید شد!\n"
                        f"━━━━━━━━━━━━━━━━━\n"
                        f"👤 {plan_data['account']}\n"
                        f"📦 {plan_data['plan']['name']}\n"
                        f"━━━━━━━━━━━━━━━━━\n"
                        f"🔗 لینک اتصال:\n`{config}`\n\n"
                        f"📚 {db['guide']}"
                    )
                    
                    try:
                        context.bot.send_message(int(target_uid), msg, parse_mode='Markdown')
                        context.bot.send_message(ADMIN_ID, f"✅ کانفیگ برای {target_uid} ارسال شد")
                    except:
                        context.bot.send_message(ADMIN_ID, f"❌ خطا در ارسال کانفیگ به {target_uid}")
                else:
                    context.bot.send_message(ADMIN_ID, f"❌ خطا در ساخت اکانت: {error}")

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
    global db
    try:
        uid = str(update.effective_user.id)
        
        if uid in db.get("blocked_users", []):
            update.message.reply_text("🚫 شما توسط ادمین بلاک شده‌اید")
            return
        
        if user_data.get(uid, {}).get('step') == 'wait_photo':
            if 'plan' not in user_data[uid] or 'account' not in user_data[uid]:
                update.message.reply_text("❌ اطلاعات خرید یافت نشد")
                return
            
            p = user_data[uid]['plan']
            acc = user_data[uid]['account']
            
            price_toman = p['price'] * 1000
            discount_text = ""
            if 'discount_code' in user_data[uid]:
                discount_text = f"\n🎫 کد تخفیف: {user_data[uid]['discount_code']}"
            
            user_info = get_user_info(uid, context)
            
            cap = (
                f"💰 فیش جدید\n"
                f"━━━━━━━━━━━━━━━━━\n"
                f"👤 {user_info}\n"
                f"🆔 {uid}\n"
                f"📦 {p['name']}\n"
                f"👤 اکانت: {acc}\n"
                f"💰 {price_toman:,} تومان{discount_text}"
            )
            
            plan_data = {
                'plan': p,
                'account': acc
            }
            
            btn = InlineKeyboardMarkup([[
                InlineKeyboardButton("✅ تایید", callback_data=f"approve_{uid}_{json.dumps(plan_data)}"),
                InlineKeyboardButton("❌ رد", callback_data=f"reject_{uid}")
            ]])
            
            context.bot.send_photo(
                ADMIN_ID,
                update.message.photo[-1].file_id,
                caption=cap,
                reply_markup=btn
            )
            
            update.message.reply_text("✅ فیش ارسال شد، پس از تایید سرویس شما فعال می‌شود")
            del user_data[uid]
    except Exception as e:
        logger.error(f"Photo error: {e}")

def main():
    try:
        logger.info("🚀 Starting bot...")
        
        if not os.path.exists(BACKUP_DIR):
            os.makedirs(BACKUP_DIR)
        
        Thread(target=run_web, daemon=True).start()
        
        updater = Updater(TOKEN, use_context=True)
        dp = updater.dispatcher
        
        dp.add_handler(CommandHandler("start", start))
        dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_msg))
        dp.add_handler(MessageHandler(Filters.photo, handle_photo))
        dp.add_handler(CallbackQueryHandler(handle_cb))
        
        updater.start_polling()
        logger.info("✅ Bot is running!")
        updater.idle()
        
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")

if __name__ == '__main__':
    main()
