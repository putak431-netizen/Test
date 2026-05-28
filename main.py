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
        {"id": 1, "name": "⚡️ پلن قوی 20GB", "price": 80, "volume": "20GB", "days": 30},
        {"id": 2, "name": "🔥 پلن قوی 50GB", "price": 140, "volume": "50GB", "days": 30}
    ],
    "💎 ارزان": [
        {"id": 3, "name": "💎 پلن اقتصادی 10GB", "price": 45, "volume": "10GB", "days": 30},
        {"id": 4, "name": "💎 پلن اقتصادی 20GB", "price": 75, "volume": "20GB", "days": 30}
    ],
    "🎯 به صرفه": [
        {"id": 5, "name": "🎯 پلن ویژه 30GB", "price": 110, "volume": "30GB", "days": 30},
        {"id": 6, "name": "🎯 پلن ویژه 60GB", "price": 190, "volume": "60GB", "days": 30}
    ],
    "👥 چند کاربره": [
        {"id": 7, "name": "👥 2 کاربره 40GB", "price": 150, "volume": "40GB", "days": 30},
        {"id": 8, "name": "👥 3 کاربره 60GB", "price": 210, "volume": "60GB", "days": 30}
    ]
}

# دیتابیس سراسری
DB = None

def load_db():
    global DB
    try:
        if os.path.exists(DB_FILE):
            with open(DB_FILE, 'r', encoding='utf-8') as f:
                DB = json.load(f)
                logger.info("✅ Database loaded")
        else:
            raise Exception("No DB file")
    except:
        logger.info("📁 Creating default database")
        DB = {
            "users": {},
            "brand": "تک نت وی‌پی‌ان",
            "card": {"number": "6277601368776066", "name": "محمد رضوانی"},
            "support": "@Support_Admin",
            "guide": "@Guide_Channel",
            "categories": DEFAULT_PLANS.copy(),
            "force_join": {"enabled": False, "channel_link": ""},
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
                "welcome": "🔰 به {brand} خوش آمدید\n✅ فروش ویژه فیلترشکن\n✅ پشتیبانی 24 ساعته",
                "support": "🆘 پشتیبانی: {support}",
                "guide": "📚 آموزش: {guide}",
                "force": "🔒 لطفا در کانال زیر عضو شوید:\n{link}\n\nبعد از عضویت دکمه تایید را بزنید."
            }
        }
    save_db()

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
        return f"@{user.username}" if user.username else user.first_name or str(uid)
    except:
        return str(uid)

def generate_discount_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

def login_to_panel():
    global DB
    panel = DB["panel_config"]
    if not panel["enabled"]:
        return None, "پنل فعال نیست"
    
    api_url = panel["api_url"].rstrip('/')
    admin_path = panel["admin_path"]
    username = panel["username"]
    password = panel["password"]
    
    session = requests.Session()
    
    try:
        # تلاش با JSON
        res = session.post(f"{api_url}/{admin_path}/login", json={"username": username, "password": password}, timeout=10)
        if res.status_code == 200:
            return session, None
    except:
        pass
    
    try:
        # تلاش با form data
        res = session.post(f"{api_url}/{admin_path}/login", data={"username": username, "password": password}, timeout=10)
        if res.status_code == 200:
            return session, None
    except:
        pass
    
    return None, "خطا در اتصال به پنل"

def create_account(plan, account_name):
    global DB
    session, error = login_to_panel()
    if not session:
        return None, error
    
    panel = DB["panel_config"]
    api_url = panel["api_url"].rstrip('/')
    admin_path = panel["admin_path"]
    
    try:
        volume_gb = int(plan["volume"].replace("GB", "").strip())
        expiry_time = int((datetime.now() + timedelta(days=plan["days"])).timestamp())
        email = f"{account_name}_{int(time.time())}".replace(' ', '_')
        
        payload = {
            "email": email,
            "total_gb": volume_gb,
            "expiry_time": expiry_time,
            "enable": True
        }
        
        res = session.post(f"{api_url}/{admin_path}/api/user/add", json=payload, timeout=30)
        
        if res.status_code == 200 and res.json().get("success"):
            return f"{api_url}/sub/{email}", None
        return None, "خطا در ساخت اکانت"
    except Exception as e:
        return None, str(e)

def create_test_account():
    global DB
    panel = DB["panel_config"]
    test = panel["test_config"]
    
    if not panel["enabled"] or not test["enabled"]:
        return None, "تست غیرفعال است"
    
    session, error = login_to_panel()
    if not session:
        return None, error
    
    api_url = panel["api_url"].rstrip('/')
    admin_path = panel["admin_path"]
    
    try:
        volume_gb = test["volume"] / 1024
        expiry_time = int((datetime.now() + timedelta(hours=test["expiry_hours"])).timestamp())
        email = f"test_{int(time.time())}_{random.randint(1000,9999)}"
        
        payload = {
            "email": email,
            "total_gb": volume_gb,
            "expiry_time": expiry_time,
            "enable": True
        }
        
        res = session.post(f"{api_url}/{admin_path}/api/user/add", json=payload, timeout=30)
        
        if res.status_code == 200 and res.json().get("success"):
            return f"{api_url}/sub/{email}", None
        return None, "خطا در ساخت اکانت تست"
    except Exception as e:
        return None, str(e)

user_data = {}

def main_menu(uid):
    kb = [['💰 خرید', '🎁 تست'], ['📂 سرویس‌ها', '👤 پشتیبانی'], ['📚 آموزش']]
    if str(uid) == str(ADMIN_ID):
        kb.append(['⚙️ مدیریت'])
    return ReplyKeyboardMarkup(kb, resize_keyboard=True)

def admin_menu():
    kb = [
        ['➕ پلن جدید', '➖ حذف پلن'],
        ['➕ دسته جدید', '➖ حذف دسته'],
        ['💳 ویرایش کارت', '🔌 تنظیمات پنل'],
        ['🎁 تنظیمات تست', '🎫 کد تخفیف'],
        ['🚫 بلاک کاربر', '📨 ارسال همگانی'],
        ['💾 بکاپ', '🔄 بازیابی بکاپ'],
        ['🔙 برگشت']
    ]
    return ReplyKeyboardMarkup(kb, resize_keyboard=True)

def start(update, context):
    global DB, user_data
    uid = str(update.effective_user.id)
    
    if uid in DB["blocked_users"]:
        update.message.reply_text("🚫 شما بلاک شده‌اید")
        return
    
    if uid not in DB["users"]:
        DB["users"][uid] = {"purchases": [], "tests": [], "test_count": 0, "date": datetime.now().strftime("%Y-%m-%d")}
        save_db()
    
    user_data[uid] = {}
    
    if DB["force_join"]["enabled"] and DB["force_join"]["channel_link"]:
        btn = InlineKeyboardMarkup([[
            InlineKeyboardButton("📢 عضویت", url=DB["force_join"]["channel_link"]),
            InlineKeyboardButton("✅ تایید", callback_data="check_join")
        ]])
        update.message.reply_text(DB["texts"]["force"].format(link=DB["force_join"]["channel_link"]), reply_markup=btn)
        return
    
    update.message.reply_text(DB["texts"]["welcome"].format(brand=DB["brand"]), reply_markup=main_menu(uid))

def handle_msg(update, context):
    global DB, user_data
    try:
        text = update.message.text
        uid = str(update.effective_user.id)
        
        if uid in DB["blocked_users"]:
            update.message.reply_text("🚫 شما بلاک شده‌اید")
            return
        
        step = user_data.get(uid, {}).get('step')
        
        if text == '🔙 برگشت':
            user_data[uid] = {}
            start(update, context)
            return
        
        # --- تست رایگان ---
        if text == '🎁 تست':
            panel = DB["panel_config"]
            if not panel["enabled"]:
                update.message.reply_text("❌ سرویس تست فعال نیست")
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
                msg = f"🎁 اکانت تست شما آماده است\n⏱ مدت: {panel['test_config']['expiry_hours']} ساعت\n📦 حجم: {panel['test_config']['volume']} مگابایت\n\n🔗 لینک اتصال:\n`{config}`"
                update.message.reply_text(msg, parse_mode='Markdown')
            else:
                update.message.reply_text(f"❌ {error}")
            return
        
        # --- سرویس‌ها ---
        if text == '📂 سرویس‌ها':
            pur = DB["users"][uid].get("purchases", [])
            tests = DB["users"][uid].get("tests", [])
            msg = "📂 سرویس‌های شما:\n━━━━━━━━━━\n"
            if pur:
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
        
        # --- پشتیبانی ---
        if text == '👤 پشتیبانی':
            update.message.reply_text(DB["texts"]["support"].format(support=DB["support"]))
            return
        
        # --- آموزش ---
        if text == '📚 آموزش':
            update.message.reply_text(DB["texts"]["guide"].format(guide=DB["guide"]))
            return
        
        # --- خرید - نمایش دسته‌ها ---
        if text == '💰 خرید':
            cats = list(DB["categories"].keys())
            kb = [[c] for c in cats] + [['🔙 برگشت']]
            update.message.reply_text("دسته را انتخاب کنید:", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
            return
        
        # --- نمایش پلن‌های یک دسته ---
        if text in DB["categories"] and not step:
            plans = DB["categories"][text]
            keyboard = []
            for p in plans:
                price_toman = p['price'] * 1000
                keyboard.append([InlineKeyboardButton(f"{p['name']} - {price_toman:,} تومان", callback_data=f"select_plan_{p['id']}")])
            update.message.reply_text(f"📦 {text}", reply_markup=InlineKeyboardMarkup(keyboard))
            return
        
        # --- مرحله دریافت کد تخفیف (بعد از انتخاب پلن) ---
        if step == 'waiting_for_discount':
            p = user_data[uid]['selected_plan']
            price_toman = p['price'] * 1000
            
            if text.upper() != 'ندارم' and text.upper() in DB["discount_codes"]:
                code_data = DB["discount_codes"][text.upper()]
                if code_data["expires"] > datetime.now().timestamp() and code_data["uses"] < code_data["max_uses"]:
                    discount = code_data["discount_percent"]
                    price_toman = price_toman * (100 - discount) // 100
                    code_data["uses"] += 1
                    save_db()
                    user_data[uid]['discount'] = discount
                    user_data[uid]['discount_code'] = text.upper()
                    update.message.reply_text(f"✅ کد تخفیف {discount}% اعمال شد\n💰 مبلغ نهایی: {price_toman:,} تومان")
            
            user_data[uid]['final_price'] = price_toman
            user_data[uid]['step'] = 'waiting_for_payment_method'
            
            kb = ReplyKeyboardMarkup([['💳 کارت به کارت'], ['🔙 برگشت']], resize_keyboard=True)
            update.message.reply_text("روش پرداخت را انتخاب کنید:", reply_markup=kb)
            return
        
        # --- مرحله انتخاب روش پرداخت ---
        if step == 'waiting_for_payment_method' and text == '💳 کارت به کارت':
            p = user_data[uid]['selected_plan']
            price = user_data[uid]['final_price']
            msg = f"💳 اطلاعات پرداخت\n━━━━━━━━━━━━━━\n📦 {p['name']}\n💰 مبلغ: {price:,} تومان\n━━━━━━━━━━━━━━\n💳 شماره کارت:\n{DB['card']['number']}\n👤 {DB['card']['name']}\n━━━━━━━━━━━━━━\nپس از واریز، عکس فیش را بفرستید"
            
            btn = InlineKeyboardMarkup([[InlineKeyboardButton("📸 ارسال فیش", callback_data="send_receipt")]])
            update.message.reply_text(msg, reply_markup=btn)
            return
        
        # --- مدیریت ادمین ---
        if str(uid) == str(ADMIN_ID):
            
            if text == '⚙️ مدیریت':
                update.message.reply_text("🛠 پنل مدیریت:", reply_markup=admin_menu())
                return
            
            # تنظیمات پنل
            if text == '🔌 تنظیمات پنل':
                status = "✅ فعال" if DB["panel_config"]["enabled"] else "❌ غیرفعال"
                kb = [['✅ فعال کردن', '❌ غیرفعال کردن'], ['🔙 برگشت']]
                update.message.reply_text(f"وضعیت پنل: {status}\nآدرس: {DB['panel_config']['api_url']}", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
                return
            
            if text == '✅ فعال کردن':
                DB["panel_config"]["enabled"] = True
                save_db()
                update.message.reply_text("✅ پنل فعال شد", reply_markup=admin_menu())
                return
            
            if text == '❌ غیرفعال کردن':
                DB["panel_config"]["enabled"] = False
                save_db()
                update.message.reply_text("❌ پنل غیرفعال شد", reply_markup=admin_menu())
                return
            
            # تنظیمات تست
            if text == '🎁 تنظیمات تست':
                test = DB["panel_config"]["test_config"]
                status = "✅ فعال" if test["enabled"] else "❌ غیرفعال"
                kb = [['📊 حجم تست', '⏱ مدت تست'], ['✅ فعال کردن تست', '❌ غیرفعال کردن تست'], ['🔙 برگشت']]
                update.message.reply_text(f"وضعیت: {status}\nحجم: {test['volume']} مگابایت\nمدت: {test['expiry_hours']} ساعت", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
                return
            
            if text == '📊 حجم تست':
                user_data[uid] = {'step': 'set_test_volume'}
                update.message.reply_text("حجم تست را به مگابایت وارد کنید:", reply_markup=back_btn())
                return
            
            if text == '⏱ مدت تست':
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
                kb = [['➕ ساخت کد', '📋 لیست کدها'], ['❌ حذف کد'], ['🔙 برگشت']]
                update.message.reply_text("مدیریت کدهای تخفیف:", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
                return
            
            if text == '➕ ساخت کد':
                user_data[uid] = {'step': 'make_discount_percent'}
                update.message.reply_text("درصد تخفیف (1-100):", reply_markup=back_btn())
                return
            
            if text == '📋 لیست کدها':
                codes = DB.get("discount_codes", {})
                if not codes:
                    update.message.reply_text("❌ کدی وجود ندارد")
                else:
                    msg = "📋 کدهای تخفیف:\n"
                    for code, data in codes.items():
                        expires = datetime.fromtimestamp(data["expires"]).strftime("%Y-%m-%d")
                        msg += f"🎫 {code} | {data['discount_percent']}% | {data['uses']}/{data['max_uses']} | تا {expires}\n"
                    update.message.reply_text(msg)
                return
            
            if text == '❌ حذف کد':
                user_data[uid] = {'step': 'del_discount_code'}
                update.message.reply_text("کد تخفیف را وارد کنید:", reply_markup=back_btn())
                return
            
            # دسته‌بندی
            if text == '➕ دسته جدید':
                user_data[uid] = {'step': 'new_category'}
                update.message.reply_text("نام دسته جدید:", reply_markup=back_btn())
                return
            
            if text == '➖ حذف دسته':
                cats = list(DB["categories"].keys())
                if cats:
                    kb = [[f"❌ {cat}"] for cat in cats] + [['🔙 برگشت']]
                    user_data[uid] = {'step': 'del_category'}
                    update.message.reply_text("دسته را انتخاب کنید:", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
                else:
                    update.message.reply_text("❌ دسته‌ای وجود ندارد")
                return
            
            # پلن
            if text == '➕ پلن جدید':
                cats = list(DB["categories"].keys())
                if cats:
                    kb = [[c] for c in cats] + [['🔙 برگشت']]
                    user_data[uid] = {'step': 'new_plan_cat'}
                    update.message.reply_text("دسته را انتخاب کنید:", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
                else:
                    update.message.reply_text("❌ ابتدا دسته بسازید")
                return
            
            if text == '➖ حذف پلن':
                keyboard = []
                for cat, plans in DB["categories"].items():
                    for p in plans:
                        keyboard.append([InlineKeyboardButton(f"❌ {cat} - {p['name']}", callback_data=f"del_plan_{p['id']}")])
                if keyboard:
                    update.message.reply_text("پلن را انتخاب کنید:", reply_markup=InlineKeyboardMarkup(keyboard))
                else:
                    update.message.reply_text("❌ پلنی وجود ندارد")
                return
            
            # ویرایش کارت
            if text == '💳 ویرایش کارت':
                kb = [['شماره کارت', 'نام صاحب کارت'], ['🔙 برگشت']]
                update.message.reply_text(f"شماره: {DB['card']['number']}\nنام: {DB['card']['name']}", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
                return
            
            if text == 'شماره کارت':
                user_data[uid] = {'step': 'edit_card_number'}
                update.message.reply_text("شماره کارت 16 رقمی:", reply_markup=back_btn())
                return
            
            if text == 'نام صاحب کارت':
                user_data[uid] = {'step': 'edit_card_name'}
                update.message.reply_text("نام صاحب کارت:", reply_markup=back_btn())
                return
            
            # بلاک کاربر
            if text == '🚫 بلاک کاربر':
                user_data[uid] = {'step': 'block_user'}
                update.message.reply_text("آیدی عددی کاربر:", reply_markup=back_btn())
                return
            
            # ارسال همگانی
            if text == '📨 ارسال همگانی':
                user_data[uid] = {'step': 'broadcast'}
                update.message.reply_text("پیام همگانی را بفرستید:", reply_markup=back_btn())
                return
            
            # بکاپ
            if text == '💾 بکاپ':
                backup_file = create_backup()
                update.message.reply_text(f"✅ بکاپ: {backup_file}" if backup_file else "❌ خطا")
                return
            
            if text == '🔄 بازیابی بکاپ':
                if os.path.exists(BACKUP_DIR):
                    backups = [f for f in os.listdir(BACKUP_DIR) if f.endswith('.json')]
                    if backups:
                        kb = [[f"🔄 {b}"] for b in backups[-10:]] + [['🔙 برگشت']]
                        user_data[uid] = {'step': 'restore_backup'}
                        update.message.reply_text("بکاپ را انتخاب کنید:", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
                    else:
                        update.message.reply_text("❌ بکاپی وجود ندارد")
                else:
                    update.message.reply_text("❌ بکاپی وجود ندارد")
                return
            
            # مراحل مرحله‌ای
            if step == 'edit_card_number':
                if text.isdigit() and len(text) == 16:
                    DB["card"]["number"] = text
                    save_db()
                    update.message.reply_text("✅ ذخیره شد", reply_markup=admin_menu())
                else:
                    update.message.reply_text("❌ نامعتبر")
                user_data[uid] = {}
                return
            
            if step == 'edit_card_name':
                DB["card"]["name"] = text
                save_db()
                update.message.reply_text("✅ ذخیره شد", reply_markup=admin_menu())
                user_data[uid] = {}
                return
            
            if step == 'set_test_volume':
                try:
                    DB["panel_config"]["test_config"]["volume"] = int(text)
                    save_db()
                    update.message.reply_text(f"✅ حجم تست: {text} مگابایت", reply_markup=admin_menu())
                except:
                    update.message.reply_text("❌ عدد وارد کنید")
                user_data[uid] = {}
                return
            
            if step == 'set_test_hours':
                try:
                    DB["panel_config"]["test_config"]["expiry_hours"] = int(text)
                    save_db()
                    update.message.reply_text(f"✅ مدت تست: {text} ساعت", reply_markup=admin_menu())
                except:
                    update.message.reply_text("❌ عدد وارد کنید")
                user_data[uid] = {}
                return
            
            if step == 'make_discount_percent':
                try:
                    percent = int(text)
                    if 1 <= percent <= 100:
                        user_data[uid]['percent'] = percent
                        user_data[uid]['step'] = 'make_discount_max'
                        update.message.reply_text("حداکثر تعداد استفاده:")
                    else:
                        update.message.reply_text("❌ بین 1 تا 100")
                except:
                    update.message.reply_text("❌ عدد وارد کنید")
                return
            
            if step == 'make_discount_max':
                try:
                    user_data[uid]['max_uses'] = int(text)
                    user_data[uid]['step'] = 'make_discount_days'
                    update.message.reply_text("مدت اعتبار (روز):")
                except:
                    update.message.reply_text("❌ عدد وارد کنید")
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
                    update.message.reply_text(f"✅ کد: `{code}`\n{user_data[uid]['percent']}% تخفیف\n{user_data[uid]['max_uses']} بار استفاده\n{days} روز اعتبار", parse_mode='Markdown', reply_markup=admin_menu())
                    user_data[uid] = {}
                except:
                    update.message.reply_text("❌ عدد وارد کنید")
                return
            
            if step == 'del_discount_code':
                if text in DB["discount_codes"]:
                    del DB["discount_codes"][text]
                    save_db()
                    update.message.reply_text("✅ حذف شد", reply_markup=admin_menu())
                else:
                    update.message.reply_text("❌ یافت نشد")
                user_data[uid] = {}
                return
            
            if step == 'new_category':
                if text not in DB["categories"]:
                    DB["categories"][text] = []
                    save_db()
                    update.message.reply_text(f"✅ دسته {text} اضافه شد", reply_markup=admin_menu())
                else:
                    update.message.reply_text("❌ تکراری")
                user_data[uid] = {}
                return
            
            if step == 'del_category' and text.startswith('❌ '):
                cat = text[2:]
                if cat in DB["categories"]:
                    del DB["categories"][cat]
                    save_db()
                    update.message.reply_text(f"✅ دسته {cat} حذف شد", reply_markup=admin_menu())
                user_data[uid] = {}
                return
            
            if step == 'new_plan_cat' and text in DB["categories"]:
                user_data[uid]['plan_cat'] = text
                user_data[uid]['step'] = 'new_plan_name'
                update.message.reply_text("نام پلن:", reply_markup=back_btn())
                return
            
            if step == 'new_plan_name':
                user_data[uid]['plan_name'] = text
                user_data[uid]['step'] = 'new_plan_vol'
                update.message.reply_text("حجم (مثال: 20GB):")
                return
            
            if step == 'new_plan_vol':
                user_data[uid]['plan_vol'] = text
                user_data[uid]['step'] = 'new_plan_days'
                update.message.reply_text("مدت (روز):")
                return
            
            if step == 'new_plan_days':
                try:
                    user_data[uid]['plan_days'] = int(text)
                    user_data[uid]['step'] = 'new_plan_price'
                    update.message.reply_text("قیمت (هزار تومان):")
                except:
                    update.message.reply_text("❌ عدد وارد کنید")
                return
            
            if step == 'new_plan_price':
                try:
                    price = int(text)
                    max_id = 0
                    for plans in DB["categories"].values():
                        for p in plans:
                            if p["id"] > max_id:
                                max_id = p["id"]
                    
                    new_plan = {
                        "id": max_id + 1,
                        "name": user_data[uid]['plan_name'],
                        "price": price,
                        "volume": user_data[uid]['plan_vol'],
                        "days": user_data[uid]['plan_days']
                    }
                    DB["categories"][user_data[uid]['plan_cat']].append(new_plan)
                    save_db()
                    update.message.reply_text("✅ پلن اضافه شد", reply_markup=admin_menu())
                    user_data[uid] = {}
                except:
                    update.message.reply_text("❌ خطا")
                return
            
            if step == 'block_user':
                try:
                    target = str(int(text))
                    if target == str(ADMIN_ID):
                        update.message.reply_text("❌ نمی‌توانید ادمین را بلاک کنید")
                    elif target in DB["blocked_users"]:
                        DB["blocked_users"].remove(target)
                        update.message.reply_text(f"✅ کاربر {target} آنبلاک شد")
                    else:
                        DB["blocked_users"].append(target)
                        update.message.reply_text(f"✅ کاربر {target} بلاک شد")
                    save_db()
                except:
                    update.message.reply_text("❌ آیدی عددی معتبر وارد کنید")
                user_data[uid] = {}
                return
            
            if step == 'broadcast':
                success, fail = 0, 0
                for uid2 in DB["users"]:
                    if uid2 not in DB["blocked_users"]:
                        try:
                            context.bot.send_message(int(uid2), text)
                            success += 1
                        except:
                            fail += 1
                update.message.reply_text(f"✅ ارسال شد\nموفق: {success}\nناموفق: {fail}", reply_markup=admin_menu())
                user_data[uid] = {}
                return
            
            if step == 'restore_backup' and text.startswith('🔄 '):
                backup_file = text[2:]
                if restore_backup(backup_file):
                    load_db()
                    update.message.reply_text("✅ بکاپ بازیابی شد", reply_markup=admin_menu())
                else:
                    update.message.reply_text("❌ خطا")
                user_data[uid] = {}
                return
        
        # --- مرحله دریافت فیش ---
        if step == 'waiting_for_receipt':
            update.message.reply_text("لطفاً عکس فیش واریزی را ارسال کنید")
        
    except Exception as e:
        logger.error(f"Error: {e}")
        update.message.reply_text("❌ خطا، دوباره تلاش کنید")

def handle_cb(update, context):
    global DB, user_data
    try:
        query = update.callback_query
        uid = str(query.from_user.id)
        query.answer()
        
        if query.data == "check_join":
            start(update, context)
            return
        
        if query.data == "send_receipt":
            user_data[uid] = {'step': 'waiting_for_receipt'}
            query.message.reply_text("📸 عکس فیش را ارسال کنید:")
            return
        
        if query.data.startswith("select_plan_"):
            plan_id = int(query.data.split("_")[2])
            for cat, plans in DB["categories"].items():
                for p in plans:
                    if p["id"] == plan_id:
                        user_data[uid] = {
                            'step': 'waiting_for_discount',
                            'selected_plan': p
                        }
                        query.message.reply_text("🎫 کد تخفیف دارید؟ وارد کنید، در غیر اینصورت 'ندارم' را بفرستید:", reply_markup=back_btn())
                        return
            query.message.reply_text("❌ پلن یافت نشد")
            return
        
        if query.data.startswith("del_plan_"):
            if str(uid) == str(ADMIN_ID):
                plan_id = int(query.data.split("_")[2])
                for cat, plans in DB["categories"].items():
                    for i, p in enumerate(plans):
                        if p["id"] == plan_id:
                            del plans[i]
                            save_db()
                            query.message.reply_text("✅ پلن حذف شد")
                            return
                query.message.reply_text("❌ یافت نشد")
            return
        
        if query.data.startswith("approve_"):
            if str(uid) == str(ADMIN_ID):
                encoded = query.data.replace("approve_", "")
                data = json.loads(base64.b64decode(encoded).decode())
                target_uid = data['uid']
                plan = data['plan']
                account_name = data['account']
                price = data['price']
                
                query.message.edit_reply_markup(reply_markup=None)
                context.bot.send_message(ADMIN_ID, f"🔄 در حال ساخت اکانت برای {target_uid}...")
                
                config, error = create_account(plan, account_name)
                
                if config:
                    service_record = f"✅ {plan['name']} | {plan['volume']} | {datetime.now().strftime('%Y-%m-%d')}"
                    if str(target_uid) not in DB["users"]:
                        DB["users"][str(target_uid)] = {"purchases": [], "tests": [], "test_count": 0}
                    DB["users"][str(target_uid)]["purchases"].append(service_record)
                    save_db()
                    
                    msg = f"✅ پرداخت شما تأیید شد!\n━━━━━━━━━━━━━━━━━\n👤 {account_name}\n📦 {plan['name']}\n💰 {price:,} تومان\n━━━━━━━━━━━━━━━━━\n🔗 لینک اتصال:\n`{config}`"
                    try:
                        context.bot.send_message(int(target_uid), msg, parse_mode='Markdown')
                        context.bot.send_message(ADMIN_ID, f"✅ کانفیگ برای {target_uid} ارسال شد")
                    except:
                        context.bot.send_message(ADMIN_ID, f"❌ خطا در ارسال به {target_uid}")
                else:
                    context.bot.send_message(ADMIN_ID, f"❌ خطا: {error}")
        
        if query.data.startswith("reject_"):
            if str(uid) == str(ADMIN_ID):
                target_uid = query.data.split("_")[1]
                query.message.edit_reply_markup(reply_markup=None)
                query.message.reply_text("دلیل رد فیش را وارد کنید:")
                user_data[ADMIN_ID] = {'step': 'reject_reason', 'target': target_uid}
        
        if query.data.startswith("test_approve_"):
            if str(uid) == str(ADMIN_ID):
                target_uid = query.data.split("_")[2]
                query.message.edit_reply_markup(reply_markup=None)
                config, error = create_test_account()
                if config:
                    DB["users"][target_uid]["test_count"] = 1
                    DB["users"][target_uid]["tests"].append(datetime.now().strftime("%Y-%m-%d"))
                    save_db()
                    msg = f"🎁 اکانت تست شما آماده است\n🔗 {config}"
                    try:
                        context.bot.send_message(int(target_uid), msg)
                        context.bot.send_message(ADMIN_ID, f"✅ تست برای {target_uid} ارسال شد")
                    except:
                        context.bot.send_message(ADMIN_ID, f"❌ خطا در ارسال تست")
                else:
                    context.bot.send_message(ADMIN_ID, f"❌ خطا: {error}")
        
    except Exception as e:
        logger.error(f"Callback error: {e}")

def handle_photo(update, context):
    global DB, user_data
    try:
        uid = str(update.effective_user.id)
        
        if uid in DB["blocked_users"]:
            update.message.reply_text("🚫 شما بلاک شده‌اید")
            return
        
        step = user_data.get(uid, {}).get('step')
        
        if step == 'waiting_for_receipt':
            if 'selected_plan' not in user_data[uid]:
                update.message.reply_text("❌ خطا، دوباره خرید را شروع کنید")
                return
            
            plan = user_data[uid]['selected_plan']
            account_name = user_data[uid].get('account_name', 'کاربر')
            price = user_data[uid].get('final_price', plan['price'] * 1000)
            discount = user_data[uid].get('discount', 0)
            user_info = get_user_info(uid, context)
            
            cap = f"💰 فیش جدید\n━━━━━━━━━━━━━━━━━\n👤 {user_info}\n🆔 {uid}\n📦 {plan['name']}\n💰 {price:,} تومان"
            if discount > 0:
                cap += f"\n🎫 تخفیف: {discount}%"
            cap += f"\n👤 اکانت: {account_name}"
            
            receipt_data = {
                'uid': uid,
                'plan': plan,
                'account': account_name,
                'price': price
            }
            encoded = base64.b64encode(json.dumps(receipt_data).encode()).decode()
            
            btn = InlineKeyboardMarkup([[
                InlineKeyboardButton("✅ تایید", callback_data=f"approve_{encoded}"),
                InlineKeyboardButton("❌ رد", callback_data=f"reject_{uid}")
            ]])
            
            context.bot.send_photo(ADMIN_ID, update.message.photo[-1].file_id, caption=cap, reply_markup=btn)
            update.message.reply_text("✅ فیش ارسال شد، پس از تایید سرویس شما فعال می‌شود")
            del user_data[uid]
        
        elif step == 'waiting_for_test_receipt':
            user_info = get_user_info(uid, context)
            cap = f"🎁 درخواست تست\n👤 {user_info}\n🆔 {uid}"
            btn = InlineKeyboardMarkup([[
                InlineKeyboardButton("✅ ارسال تست", callback_data=f"test_approve_{uid}")
            ]])
            context.bot.send_photo(ADMIN_ID, update.message.photo[-1].file_id, caption=cap, reply_markup=btn)
            update.message.reply_text("✅ درخواست تست ارسال شد")
            del user_data[uid]
        
        elif step == 'reject_reason':
            target = user_data[uid].get('target')
            if target:
                context.bot.send_message(int(target), f"❌ فیش شما رد شد\nدلیل: {update.message.caption or update.message.text or 'نامشخص'}")
                update.message.reply_text("✅ دلیل رد به کاربر اعلام شد")
            del user_data[uid]
        
    except Exception as e:
        logger.error(f"Photo error: {e}")

def main():
    try:
        logger.info("🚀 Starting bot...")
        
        # حذف webhook برای جلوگیری از Conflict
        requests.post(f"https://api.telegram.org/bot{TOKEN}/deleteWebhook", json={"drop_pending_updates": True})
        time.sleep(2)
        
        load_db()
        
        if not os.path.exists(BACKUP_DIR):
            os.makedirs(BACKUP_DIR)
        
        Thread(target=run_web, daemon=True).start()
        
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
