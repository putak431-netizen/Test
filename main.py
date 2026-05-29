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

# --- تنظیمات لاگینگ ---
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# --- وب سرور ---
app_web = Flask(__name__)

@app_web.route('/')
def home():
    return "✅ Bot is Running!", 200

def run_web():
    port = int(os.environ.get('PORT', 8080))
    app_web.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

# --- توکن جدید ---
TOKEN = '8298942850:AAFdcOhM0se4nHJScRI5cSwKCM_6k4H_UHQ'
ADMIN_ID = 5993860770

DB_FILE = 'data.json'
BACKUP_DIR = 'backups'

# دیتابیس
db = {
    "users": {},
    "brand": "تک نت وی‌پی‌ان",
    "card": {"number": "6277601368776066", "name": "محمد رضوانی"},
    "support": "@Support_Admin",
    "guide": "@Guide_Channel",
    "categories": {
        "🚀 قوی": [
            {"id": 1, "name": "پلن قوی 20GB", "price": 80000, "volume": "20GB", "days": 30},
            {"id": 2, "name": "پلن قوی 50GB", "price": 140000, "volume": "50GB", "days": 30}
        ],
        "💎 ارزان": [
            {"id": 3, "name": "پلن اقتصادی 10GB", "price": 45000, "volume": "10GB", "days": 30},
            {"id": 4, "name": "پلن اقتصادی 20GB", "price": 75000, "volume": "20GB", "days": 30}
        ]
    },
    "discount_codes": {},
    "blocked_users": [],
    "panel": {
        "enabled": False,
        "url": "http://p.dragonteamm.shop:8081",
        "admin_path": "hke43Y4nhZ23K1vc4S",
        "username": "amir",
        "password": "amirreza871221",
        "test_volume": 50,
        "test_hours": 3
    }
}

def save_db():
    try:
        with open(DB_FILE, 'w', encoding='utf-8') as f:
            json.dump(db, f, ensure_ascii=False, indent=4)
        return True
    except:
        return False

def load_db():
    global db
    try:
        if os.path.exists(DB_FILE):
            with open(DB_FILE, 'r', encoding='utf-8') as f:
                db = json.load(f)
                logger.info("✅ DB loaded")
                return
    except:
        pass
    save_db()

load_db()

# --- توابع پنل ---
def panel_login():
    if not db["panel"]["enabled"]:
        return None, "پنل فعال نیست"
    
    session = requests.Session()
    url = f"{db['panel']['url']}/{db['panel']['admin_path']}/login"
    
    try:
        # تلاش با JSON
        res = session.post(url, json={"username": db["panel"]["username"], "password": db["panel"]["password"]}, timeout=10)
        if res.status_code == 200:
            return session, None
    except:
        pass
    
    try:
        # تلاش با فرم
        res = session.post(url, data={"username": db["panel"]["username"], "password": db["panel"]["password"]}, timeout=10)
        if res.status_code == 200:
            return session, None
    except:
        pass
    
    return None, "خطا در اتصال به پنل"

def create_vpn_account(plan, user_email):
    session, error = panel_login()
    if error:
        return None, error
    
    # تبدیل حجم به گیگابایت
    volume_gb = int(plan["volume"].replace("GB", ""))
    expiry = int((datetime.now() + timedelta(days=plan["days"])).timestamp())
    email = f"{user_email}_{int(time.time())}".replace(" ", "_")
    
    url = f"{db['panel']['url']}/{db['panel']['admin_path']}/api/user/add"
    payload = {"email": email, "total_gb": volume_gb, "expiry_time": expiry, "enable": True}
    
    try:
        res = session.post(url, json=payload, timeout=30)
        if res.status_code == 200 and res.json().get("success"):
            return f"{db['panel']['url']}/sub/{email}", None
        return None, "خطا در ساخت اکانت"
    except Exception as e:
        return None, str(e)

def create_test_vpn_account():
    session, error = panel_login()
    if error:
        return None, error
    
    volume_gb = db["panel"]["test_volume"] / 1024
    expiry = int((datetime.now() + timedelta(hours=db["panel"]["test_hours"])).timestamp())
    email = f"test_{int(time.time())}_{random.randint(100,999)}"
    
    url = f"{db['panel']['url']}/{db['panel']['admin_path']}/api/user/add"
    payload = {"email": email, "total_gb": volume_gb, "expiry_time": expiry, "enable": True}
    
    try:
        res = session.post(url, json=payload, timeout=30)
        if res.status_code == 200 and res.json().get("success"):
            return f"{db['panel']['url']}/sub/{email}", None
        return None, "خطا در ساخت تست"
    except Exception as e:
        return None, str(e)

# --- منوها ---
def main_menu(uid):
    kb = [['💰 خرید', '🎁 تست'], ['📂 سرویس‌ها', '👤 پشتیبانی'], ['📚 آموزش']]
    if str(uid) == str(ADMIN_ID):
        kb.append(['⚙️ مدیریت'])
    return ReplyKeyboardMarkup(kb, resize_keyboard=True)

def admin_menu():
    kb = [
        ['🔌 فعال/غیرفعال پنل', '🎁 تنظیمات تست'],
        ['➕ دسته جدید', '➖ حذف دسته'],
        ['➕ پلن جدید', '➖ حذف پلن'],
        ['💳 ویرایش کارت', '🎫 ساخت کد تخفیف'],
        ['🚫 بلاک/آنبلاک', '📨 ارسال همگانی'],
        ['💾 بکاپ', '🔄 بازیابی'],
        ['🔙 برگشت']
    ]
    return ReplyKeyboardMarkup(kb, resize_keyboard=True)

def back_btn():
    return ReplyKeyboardMarkup([['🔙 برگشت']], resize_keyboard=True)

# --- ذخیره‌سازی موقت کاربر ---
user_temp = {}

# --- هندلر استارت ---
def start(update, context):
    uid = str(update.effective_user.id)
    
    if uid in db["blocked_users"]:
        update.message.reply_text("🚫 شما بلاک شده‌اید")
        return
    
    if uid not in db["users"]:
        db["users"][uid] = {"purchases": [], "tests": [], "test_count": 0, "date": datetime.now().strftime("%Y-%m-%d")}
        save_db()
    
    update.message.reply_text(f"🔰 به {db['brand']} خوش آمدید", reply_markup=main_menu(uid))

# --- هندلر اصلی ---
def handle_message(update, context):
    global user_temp
    try:
        text = update.message.text
        uid = str(update.effective_user.id)
        
        if uid in db["blocked_users"]:
            update.message.reply_text("🚫 بلاک شده‌اید")
            return
        
        step = user_temp.get(uid, {}).get('step')
        
        # برگشت
        if text == '🔙 برگشت':
            user_temp[uid] = {}
            start(update, context)
            return
        
        # ========== منوی کاربر ==========
        
        # تست
        if text == '🎁 تست':
            if not db["panel"]["enabled"]:
                update.message.reply_text("❌ سرویس تست فعال نیست")
                return
            if db["users"][uid]["test_count"] >= 1:
                update.message.reply_text("❌ قبلاً تست گرفته‌اید")
                return
            
            update.message.reply_text("🔄 در حال ساخت اکانت تست...")
            config, error = create_test_vpn_account()
            
            if config:
                db["users"][uid]["test_count"] += 1
                db["users"][uid]["tests"].append(datetime.now().strftime("%Y-%m-%d"))
                save_db()
                msg = f"🎁 اکانت تست شما آماده\n⏱ {db['panel']['test_hours']} ساعت\n📦 {db['panel']['test_volume']} مگابایت\n\n🔗 {config}"
                update.message.reply_text(msg)
            else:
                update.message.reply_text(f"❌ {error}")
            return
        
        # سرویس‌ها
        if text == '📂 سرویس‌ها':
            pur = db["users"][uid].get("purchases", [])
            tests = db["users"][uid].get("tests", [])
            msg = "📂 سرویس‌های شما:\n"
            if pur:
                for p in pur[-10:]:
                    msg += f"✅ {p}\n"
            else:
                msg += "❌ خریدی ندارید\n"
            if tests:
                msg += "\n🎁 تست‌ها:\n"
                for t in tests[-5:]:
                    msg += f"🎁 {t}\n"
            update.message.reply_text(msg)
            return
        
        # پشتیبانی
        if text == '👤 پشتیبانی':
            update.message.reply_text(f"🆘 {db['support']}")
            return
        
        # آموزش
        if text == '📚 آموزش':
            update.message.reply_text(f"📚 {db['guide']}")
            return
        
        # خرید - نمایش دسته‌ها
        if text == '💰 خرید':
            cats = list(db["categories"].keys())
            kb = [[c] for c in cats] + [['🔙 برگشت']]
            update.message.reply_text("دسته را انتخاب کنید:", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
            return
        
        # نمایش پلن‌های یک دسته
        if text in db["categories"]:
            plans = db["categories"][text]
            keyboard = []
            for p in plans:
                keyboard.append([InlineKeyboardButton(f"{p['name']} - {p['price']:,} تومان", callback_data=f"plan_{p['id']}")])
            update.message.reply_text(f"📦 {text}", reply_markup=InlineKeyboardMarkup(keyboard))
            return
        
        # مرحله: دریافت کد تخفیف
        if step == 'wait_discount':
            plan = user_temp[uid]['plan']
            price = plan['price']
            
            if text.upper() != 'ندارم' and text.upper() in db["discount_codes"]:
                code_data = db["discount_codes"][text.upper()]
                if code_data["expires"] > datetime.now().timestamp():
                    discount = code_data["discount_percent"]
                    price = price * (100 - discount) // 100
                    code_data["uses"] += 1
                    save_db()
                    user_temp[uid]['discount'] = discount
                    update.message.reply_text(f"✅ تخفیف {discount}% اعمال شد\n💰 مبلغ: {price:,} تومان")
            
            user_temp[uid]['final_price'] = price
            user_temp[uid]['step'] = 'wait_payment'
            
            kb = ReplyKeyboardMarkup([['💳 کارت به کارت'], ['🔙 برگشت']], resize_keyboard=True)
            update.message.reply_text("روش پرداخت را انتخاب کنید:", reply_markup=kb)
            return
        
        # مرحله: انتخاب روش پرداخت
        if step == 'wait_payment' and text == '💳 کارت به کارت':
            plan = user_temp[uid]['plan']
            price = user_temp[uid]['final_price']
            
            msg = f"💳 اطلاعات پرداخت\n━━━━━━━━━━\n📦 {plan['name']}\n💰 {price:,} تومان\n━━━━━━━━━━\n💳 شماره کارت:\n{db['card']['number']}\n👤 {db['card']['name']}\n━━━━━━━━━━\nپس از واریز، عکس فیش را بفرستید"
            
            btn = InlineKeyboardMarkup([[InlineKeyboardButton("📸 ارسال فیش", callback_data="send_fish")]])
            update.message.reply_text(msg, reply_markup=btn)
            return
        
        # ========== منوی ادمین ==========
        
        if str(uid) != str(ADMIN_ID):
            return
        
        if text == '⚙️ مدیریت':
            update.message.reply_text("🛠 پنل مدیریت:", reply_markup=admin_menu())
            return
        
        # فعال/غیرفعال پنل
        if text == '🔌 فعال/غیرفعال پنل':
            db["panel"]["enabled"] = not db["panel"]["enabled"]
            save_db()
            status = "فعال" if db["panel"]["enabled"] else "غیرفعال"
            update.message.reply_text(f"✅ پنل {status} شد", reply_markup=admin_menu())
            return
        
        # تنظیمات تست
        if text == '🎁 تنظیمات تست':
            user_temp[uid] = {'step': 'set_test_volume'}
            update.message.reply_text(f"حجم تست فعلی: {db['panel']['test_volume']} مگابایت\nحجم جدید را وارد کنید:", reply_markup=back_btn())
            return
        
        if step == 'set_test_volume':
            try:
                db["panel"]["test_volume"] = int(text)
                user_temp[uid]['step'] = 'set_test_hours'
                update.message.reply_text(f"مدت تست فعلی: {db['panel']['test_hours']} ساعت\nمدت جدید را وارد کنید:")
            except:
                update.message.reply_text("❌ عدد وارد کنید")
            return
        
        if step == 'set_test_hours':
            try:
                db["panel"]["test_hours"] = int(text)
                save_db()
                update.message.reply_text("✅ تنظیمات تست ذخیره شد", reply_markup=admin_menu())
                user_temp[uid] = {}
            except:
                update.message.reply_text("❌ عدد وارد کنید")
            return
        
        # دسته جدید
        if text == '➕ دسته جدید':
            user_temp[uid] = {'step': 'new_category'}
            update.message.reply_text("نام دسته جدید:", reply_markup=back_btn())
            return
        
        if step == 'new_category':
            if text not in db["categories"]:
                db["categories"][text] = []
                save_db()
                update.message.reply_text(f"✅ دسته {text} اضافه شد", reply_markup=admin_menu())
            else:
                update.message.reply_text("❌ تکراری")
            user_temp[uid] = {}
            return
        
        # حذف دسته
        if text == '➖ حذف دسته':
            cats = list(db["categories"].keys())
            if not cats:
                update.message.reply_text("❌ دسته‌ای نیست")
                return
            kb = [[f"🗑 {cat}"] for cat in cats] + [['🔙 برگشت']]
            user_temp[uid] = {'step': 'del_category'}
            update.message.reply_text("دسته را انتخاب کنید:", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
            return
        
        if step == 'del_category' and text.startswith('🗑 '):
            cat = text[2:]
            if cat in db["categories"]:
                del db["categories"][cat]
                save_db()
                update.message.reply_text(f"✅ دسته {cat} حذف شد", reply_markup=admin_menu())
            user_temp[uid] = {}
            return
        
        # پلن جدید
        if text == '➕ پلن جدید':
            cats = list(db["categories"].keys())
            if not cats:
                update.message.reply_text("❌ ابتدا دسته بسازید")
                return
            kb = [[c] for c in cats] + [['🔙 برگشت']]
            user_temp[uid] = {'step': 'select_category_for_plan'}
            update.message.reply_text("دسته را انتخاب کنید:", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
            return
        
        if step == 'select_category_for_plan' and text in db["categories"]:
            user_temp[uid]['plan_cat'] = text
            user_temp[uid]['step'] = 'new_plan_name'
            update.message.reply_text("نام پلن:", reply_markup=back_btn())
            return
        
        if step == 'new_plan_name':
            user_temp[uid]['plan_name'] = text
            user_temp[uid]['step'] = 'new_plan_volume'
            update.message.reply_text("حجم (مثال: 20GB):")
            return
        
        if step == 'new_plan_volume':
            user_temp[uid]['plan_volume'] = text
            user_temp[uid]['step'] = 'new_plan_days'
            update.message.reply_text("مدت (روز):")
            return
        
        if step == 'new_plan_days':
            try:
                user_temp[uid]['plan_days'] = int(text)
                user_temp[uid]['step'] = 'new_plan_price'
                update.message.reply_text("قیمت (تومان):")
            except:
                update.message.reply_text("❌ عدد وارد کنید")
            return
        
        if step == 'new_plan_price':
            try:
                price = int(text)
                max_id = 0
                for plans in db["categories"].values():
                    for p in plans:
                        if p["id"] > max_id:
                            max_id = p["id"]
                
                new_plan = {
                    "id": max_id + 1,
                    "name": user_temp[uid]['plan_name'],
                    "price": price,
                    "volume": user_temp[uid]['plan_volume'],
                    "days": user_temp[uid]['plan_days']
                }
                db["categories"][user_temp[uid]['plan_cat']].append(new_plan)
                save_db()
                update.message.reply_text("✅ پلن اضافه شد", reply_markup=admin_menu())
                user_temp[uid] = {}
            except:
                update.message.reply_text("❌ خطا")
            return
        
        # حذف پلن
        if text == '➖ حذف پلن':
            keyboard = []
            for cat, plans in db["categories"].items():
                for p in plans:
                    keyboard.append([InlineKeyboardButton(f"❌ {cat} - {p['name']}", callback_data=f"delplan_{p['id']}")])
            if keyboard:
                update.message.reply_text("پلن را انتخاب کنید:", reply_markup=InlineKeyboardMarkup(keyboard))
            else:
                update.message.reply_text("❌ پلنی نیست")
            return
        
        # ویرایش کارت
        if text == '💳 ویرایش کارت':
            user_temp[uid] = {'step': 'edit_card'}
            update.message.reply_text(f"شماره کارت فعلی: {db['card']['number']}\nشماره جدید (16 رقم):", reply_markup=back_btn())
            return
        
        if step == 'edit_card':
            if text.isdigit() and len(text) == 16:
                db["card"]["number"] = text
                user_temp[uid]['step'] = 'edit_card_name'
                update.message.reply_text(f"نام فعلی: {db['card']['name']}\nنام جدید:")
            else:
                update.message.reply_text("❌ 16 رقم وارد کنید")
            return
        
        if step == 'edit_card_name':
            db["card"]["name"] = text
            save_db()
            update.message.reply_text("✅ کارت ذخیره شد", reply_markup=admin_menu())
            user_temp[uid] = {}
            return
        
        # ساخت کد تخفیف
        if text == '🎫 ساخت کد تخفیف':
            user_temp[uid] = {'step': 'discount_percent'}
            update.message.reply_text("درصد تخفیف (1-100):", reply_markup=back_btn())
            return
        
        if step == 'discount_percent':
            try:
                percent = int(text)
                if 1 <= percent <= 100:
                    user_temp[uid]['percent'] = percent
                    user_temp[uid]['step'] = 'discount_max'
                    update.message.reply_text("حداکثر تعداد استفاده:")
                else:
                    update.message.reply_text("❌ بین 1 تا 100")
            except:
                update.message.reply_text("❌ عدد وارد کنید")
            return
        
        if step == 'discount_max':
            try:
                user_temp[uid]['max_uses'] = int(text)
                user_temp[uid]['step'] = 'discount_days'
                update.message.reply_text("مدت اعتبار (روز):")
            except:
                update.message.reply_text("❌ عدد وارد کنید")
            return
        
        if step == 'discount_days':
            try:
                days = int(text)
                code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
                db["discount_codes"][code] = {
                    "discount_percent": user_temp[uid]['percent'],
                    "max_uses": user_temp[uid]['max_uses'],
                    "uses": 0,
                    "expires": (datetime.now() + timedelta(days=days)).timestamp()
                }
                save_db()
                update.message.reply_text(f"✅ کد تخفیف: `{code}`\n{user_temp[uid]['percent']}% تخفیف\n{user_temp[uid]['max_uses']} بار استفاده\n{days} روز اعتبار", parse_mode='Markdown', reply_markup=admin_menu())
                user_temp[uid] = {}
            except:
                update.message.reply_text("❌ عدد وارد کنید")
            return
        
        # بلاک/آنبلاک
        if text == '🚫 بلاک/آنبلاک':
            user_temp[uid] = {'step': 'block_user'}
            update.message.reply_text("آیدی کاربر را وارد کنید:", reply_markup=back_btn())
            return
        
        if step == 'block_user':
            try:
                target = str(int(text))
                if target == str(ADMIN_ID):
                    update.message.reply_text("❌ نمی‌توانید ادمین را بلاک کنید")
                elif target in db["blocked_users"]:
                    db["blocked_users"].remove(target)
                    update.message.reply_text(f"✅ کاربر {target} آنبلاک شد")
                else:
                    db["blocked_users"].append(target)
                    update.message.reply_text(f"✅ کاربر {target} بلاک شد")
                save_db()
            except:
                update.message.reply_text("❌ آیدی عددی وارد کنید")
            user_temp[uid] = {}
            return
        
        # ارسال همگانی
        if text == '📨 ارسال همگانی':
            user_temp[uid] = {'step': 'broadcast'}
            update.message.reply_text("پیام را بفرستید:", reply_markup=back_btn())
            return
        
        if step == 'broadcast':
            success = 0
            for uid2 in db["users"]:
                if uid2 not in db["blocked_users"]:
                    try:
                        context.bot.send_message(int(uid2), text)
                        success += 1
                    except:
                        pass
            update.message.reply_text(f"✅ به {success} کاربر ارسال شد", reply_markup=admin_menu())
            user_temp[uid] = {}
            return
        
        # بکاپ
        if text == '💾 بکاپ':
            if not os.path.exists(BACKUP_DIR):
                os.makedirs(BACKUP_DIR)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = os.path.join(BACKUP_DIR, f"backup_{timestamp}.json")
            shutil.copy2(DB_FILE, backup_file)
            update.message.reply_text(f"✅ بکاپ: {backup_file}")
            return
        
        if text == '🔄 بازیابی':
            if os.path.exists(BACKUP_DIR):
                backups = [f for f in os.listdir(BACKUP_DIR) if f.endswith('.json')]
                if backups:
                    kb = [[f"📁 {b}"] for b in backups[-10:]] + [['🔙 برگشت']]
                    user_temp[uid] = {'step': 'restore'}
                    update.message.reply_text("بکاپ را انتخاب کنید:", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
                else:
                    update.message.reply_text("❌ بکاپی نیست")
            else:
                update.message.reply_text("❌ بکاپی نیست")
            return
        
        if step == 'restore' and text.startswith('📁 '):
            backup_file = text[2:]
            backup_path = os.path.join(BACKUP_DIR, backup_file)
            if os.path.exists(backup_path):
                shutil.copy2(backup_path, DB_FILE)
                load_db()
                update.message.reply_text("✅ بکاپ بازیابی شد", reply_markup=admin_menu())
            user_temp[uid] = {}
            return
        
        # مرحله: دریافت فیش
        if step == 'wait_fish':
            update.message.reply_text("📸 لطفاً عکس فیش را ارسال کنید")
        
    except Exception as e:
        logger.error(f"Error: {e}")
        update.message.reply_text("❌ خطا")

# --- کالبک ---
def handle_callback(update, context):
    global user_temp
    try:
        query = update.callback_query
        uid = str(query.from_user.id)
        query.answer()
        
        # انتخاب پلن
        if query.data.startswith("plan_"):
            plan_id = int(query.data.split("_")[1])
            for cat, plans in db["categories"].items():
                for p in plans:
                    if p["id"] == plan_id:
                        user_temp[uid] = {'step': 'wait_discount', 'plan': p}
                        query.message.reply_text("🎫 کد تخفیف دارید؟ وارد کنید، در غیر اینصورت 'ندارم' را بفرستید:", reply_markup=back_btn())
                        return
            query.message.reply_text("❌ پلن یافت نشد")
            return
        
        # حذف پلن
        if query.data.startswith("delplan_"):
            if str(uid) == str(ADMIN_ID):
                plan_id = int(query.data.split("_")[1])
                for cat, plans in db["categories"].items():
                    for i, p in enumerate(plans):
                        if p["id"] == plan_id:
                            del plans[i]
                            save_db()
                            query.message.reply_text("✅ پلن حذف شد")
                            return
                query.message.reply_text("❌ یافت نشد")
            return
        
        # ارسال فیش
        if query.data == "send_fish":
            if uid in user_temp and user_temp[uid].get('step') == 'wait_payment':
                user_temp[uid]['step'] = 'wait_fish'
                query.message.reply_text("📸 عکس فیش را ارسال کنید:")
            else:
                query.message.reply_text("❌ خطا")
            return
        
    except Exception as e:
        logger.error(f"Callback error: {e}")

# --- دریافت عکس ---
def handle_photo(update, context):
    global user_temp
    try:
        uid = str(update.effective_user.id)
        
        if uid in db["blocked_users"]:
            update.message.reply_text("🚫 بلاک شده‌اید")
            return
        
        step = user_temp.get(uid, {}).get('step')
        
        if step == 'wait_fish':
            plan = user_temp[uid].get('plan')
            price = user_temp[uid].get('final_price')
            discount = user_temp[uid].get('discount', 0)
            
            if not plan:
                update.message.reply_text("❌ خطا، دوباره خرید را شروع کنید")
                return
            
            # دریافت اطلاعات کاربر
            user_info = f"@{update.effective_user.username}" if update.effective_user.username else update.effective_user.first_name
            
            caption = f"💰 فیش جدید\n━━━━━━━━━━\n👤 {user_info}\n🆔 {uid}\n📦 {plan['name']}\n💰 {price:,} تومان"
            if discount > 0:
                caption += f"\n🎫 تخفیف: {discount}%"
            
            # ذخیره اطلاعات برای تایید
            receipt_data = {
                'uid': uid,
                'plan': plan,
                'price': price,
                'account': update.effective_user.first_name or "کاربر"
            }
            import base64
            encoded = base64.b64encode(json.dumps(receipt_data).encode()).decode()
            
            btn = InlineKeyboardMarkup([[
                InlineKeyboardButton("✅ تایید", callback_data=f"approve_{encoded}"),
                InlineKeyboardButton("❌ رد", callback_data=f"reject_{uid}")
            ]])
            
            context.bot.send_photo(ADMIN_ID, update.message.photo[-1].file_id, caption=caption, reply_markup=btn)
            update.message.reply_text("✅ فیش ارسال شد، پس از تایید سرویس فعال می‌شود")
            del user_temp[uid]
            return
        
        # تایید/رد توسط ادمین
        if step == 'reject_reason':
            target = user_temp[uid].get('target')
            if target:
                reason = update.message.caption or update.message.text or "نامشخص"
                context.bot.send_message(int(target), f"❌ فیش شما رد شد\nدلیل: {reason}")
                update.message.reply_text("✅ دلیل رد ارسال شد")
            del user_temp[uid]
            return
        
    except Exception as e:
        logger.error(f"Photo error: {e}")

# --- کالبک تایید/رد (ادمین) ---
def admin_callback(update, context):
    global user_temp
    try:
        query = update.callback_query
        uid = str(query.from_user.id)
        
        if uid != str(ADMIN_ID):
            query.answer("❌ فقط ادمین")
            return
        
        query.answer()
        
        # تایید فیش
        if query.data.startswith("approve_"):
            import base64
            encoded = query.data.replace("approve_", "")
            data = json.loads(base64.b64decode(encoded).decode())
            target_uid = data['uid']
            plan = data['plan']
            account_name = data['account']
            
            query.message.edit_reply_markup(reply_markup=None)
            context.bot.send_message(ADMIN_ID, f"🔄 در حال ساخت اکانت برای {target_uid}...")
            
            # ساخت اکانت در پنل
            config, error = create_vpn_account(plan, account_name)
            
            if config:
                # ثبت در تاریخچه کاربر
                service = f"{plan['name']} | {plan['volume']} | {datetime.now().strftime('%Y-%m-%d')}"
                if target_uid not in db["users"]:
                    db["users"][target_uid] = {"purchases": [], "tests": [], "test_count": 0, "date": datetime.now().strftime("%Y-%m-%d")}
                db["users"][target_uid]["purchases"].append(service)
                save_db()
                
                msg = f"✅ پرداخت شما تأیید شد!\n━━━━━━━━━━\n👤 {account_name}\n📦 {plan['name']}\n━━━━━━━━━━\n🔗 {config}"
                try:
                    context.bot.send_message(int(target_uid), msg)
                    context.bot.send_message(ADMIN_ID, f"✅ کانفیگ برای {target_uid} ارسال شد")
                except Exception as e:
                    context.bot.send_message(ADMIN_ID, f"❌ خطا در ارسال: {e}")
            else:
                context.bot.send_message(ADMIN_ID, f"❌ خطا: {error}")
            return
        
        # رد فیش
        if query.data.startswith("reject_"):
            target_uid = query.data.split("_")[1]
            user_temp[ADMIN_ID] = {'step': 'reject_reason', 'target': target_uid}
            query.message.reply_text("دلیل رد را وارد کنید:")
            query.message.edit_reply_markup(reply_markup=None)
            return
        
    except Exception as e:
        logger.error(f"Admin callback error: {e}")

# --- اجرا ---
def main():
    try:
        logger.info("🚀 Starting bot...")
        
        # حذف webhook
        requests.post(f"https://api.telegram.org/bot{TOKEN}/deleteWebhook", json={"drop_pending_updates": True})
        time.sleep(2)
        
        if not os.path.exists(BACKUP_DIR):
            os.makedirs(BACKUP_DIR)
        
        Thread(target=run_web, daemon=True).start()
        
        updater = Updater(TOKEN, use_context=True)
        dp = updater.dispatcher
        
        dp.add_handler(CommandHandler("start", start))
        dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))
        dp.add_handler(MessageHandler(Filters.photo, handle_photo))
        dp.add_handler(CallbackQueryHandler(handle_callback))
        dp.add_handler(CallbackQueryHandler(admin_callback, pattern="^(approve_|reject_)"))
        
        updater.start_polling(poll_interval=1.0)
        logger.info("✅ Bot is running!")
        updater.idle()
        
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")

if __name__ == '__main__':
    main()
