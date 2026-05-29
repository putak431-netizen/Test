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
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# --- وب سرور ---
app_web = Flask(__name__)

@app_web.route('/')
def home():
    return "✅ VPN Bot is Running!", 200

def run_web():
    port = int(os.environ.get('PORT', 8080))
    app_web.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

# --- توکن ربات و ادمین ---
TOKEN = '8298942850:AAFdcOhM0se4nHJScRI5cSwKCM_6k4H_UHQ'
ADMIN_ID = 5993860770

# --- تنظیمات پنل سنایی ---
PANEL_URL = "http://p.dragonteamm.shop:8081"
PANEL_PATH = "hke43Y4nhZ23K1vc4S"
API_TOKEN = "6bUP6MaB0Z7g6bmH2S3qyUdDKsjnhCgOeLxmsxoHeSJHiKm3"

# --- دیتابیس ---
DB_FILE = 'data.json'
BACKUP_DIR = 'backups'

db = {
    "users": {},
    "brand": "تک نت وی‌پی‌ان",
    "card": {"number": "6277601368776066", "name": "محمد رضوانی"},
    "support": "@Support_Admin",
    "guide": "@Guide_Channel",
    "panel_enabled": True,
    "test_volume": 50,
    "test_hours": 3,
    "discount_codes": {},
    "blocked_users": [],
    "categories": {
        "🚀 قوی": [
            {"id": 1, "name": "پلن قوی 20GB", "price": 80000, "volume": 20, "days": 30},
            {"id": 2, "name": "پلن قوی 50GB", "price": 140000, "volume": 50, "days": 30}
        ],
        "💎 ارزان": [
            {"id": 3, "name": "پلن اقتصادی 10GB", "price": 45000, "volume": 10, "days": 30},
            {"id": 4, "name": "پلن اقتصادی 20GB", "price": 75000, "volume": 20, "days": 30}
        ],
        "🎯 به صرفه": [
            {"id": 5, "name": "پلن ویژه 30GB", "price": 110000, "volume": 30, "days": 30},
            {"id": 6, "name": "پلن ویژه 60GB", "price": 190000, "volume": 60, "days": 30}
        ],
        "👥 چند کاربره": [
            {"id": 7, "name": "پلن 2 کاربره 40GB", "price": 150000, "volume": 40, "days": 30},
            {"id": 8, "name": "پلن 3 کاربره 60GB", "price": 210000, "volume": 60, "days": 30}
        ]
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

# ==================== توابع اتصال به پنل سنایی ====================

def create_vpn_account(plan, user_id, account_name):
    """ساخت اکانت در پنل سنایی با API Token"""
    try:
        # ایمیل منحصر به فرد برای کاربر
        email = f"user_{user_id}_{int(time.time())}@vpn.local"
        
        # محاسبه تاریخ انقضا
        expiry_time = int((datetime.now() + timedelta(days=plan['days'])).timestamp())
        
        # ساخت payload برای API
        payload = {
            "email": email,
            "total_gb": plan['volume'],
            "expiry_time": expiry_time,
            "enable": True,
            "remark": f"{account_name}_{user_id}"
        }
        
        headers = {
            "Authorization": f"Bearer {API_TOKEN}",
            "Content-Type": "application/json"
        }
        
        url = f"{PANEL_URL}/{PANEL_PATH}/api/user/add"
        
        logger.info(f"Sending request to panel: {url}")
        logger.info(f"Payload: {payload}")
        
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        
        logger.info(f"Response status: {response.status_code}")
        logger.info(f"Response body: {response.text}")
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success') or result.get('status') == 'success':
                # لینک سابسکریپشن کاربر
                sub_url = f"{PANEL_URL}/sub/{email}"
                return sub_url, None
        
        return None, f"خطا: {response.text}"
        
    except Exception as e:
        logger.error(f"Panel error: {e}")
        return None, str(e)

def create_test_vpn_account(user_id):
    """ساخت اکانت تست در پنل سنایی"""
    try:
        email = f"test_{user_id}_{int(time.time())}@vpn.local"
        
        volume_gb = db['test_volume'] / 1024  # تبدیل مگابایت به گیگابایت
        expiry_time = int((datetime.now() + timedelta(hours=db['test_hours'])).timestamp())
        
        payload = {
            "email": email,
            "total_gb": round(volume_gb, 2),
            "expiry_time": expiry_time,
            "enable": True
        }
        
        headers = {
            "Authorization": f"Bearer {API_TOKEN}",
            "Content-Type": "application/json"
        }
        
        url = f"{PANEL_URL}/{PANEL_PATH}/api/user/add"
        
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success') or result.get('status') == 'success':
                sub_url = f"{PANEL_URL}/sub/{email}"
                return sub_url, None
        
        return None, f"خطا در ساخت تست: {response.text}"
        
    except Exception as e:
        return None, str(e)

# ==================== منوها ====================

def main_menu(uid):
    kb = [['💰 خرید', '🎁 تست'], ['📂 سرویس‌ها', '👤 پشتیبانی'], ['📚 آموزش']]
    if str(uid) == str(ADMIN_ID):
        kb.append(['⚙️ مدیریت'])
    return ReplyKeyboardMarkup(kb, resize_keyboard=True)

def admin_menu():
    kb = [
        ['🎁 تنظیمات تست', '🎫 مدیریت کد تخفیف'],
        ['➕ دسته جدید', '➖ حذف دسته'],
        ['➕ پلن جدید', '➖ حذف پلن'],
        ['💳 ویرایش کارت', '🚫 بلاک/آنبلاک'],
        ['📨 ارسال همگانی', '💾 بکاپ/بازیابی'],
        ['🔙 برگشت']
    ]
    return ReplyKeyboardMarkup(kb, resize_keyboard=True)

def back_btn():
    return ReplyKeyboardMarkup([['🔙 برگشت']], resize_keyboard=True)

# ذخیره موقت اطلاعات کاربران
user_temp = {}

# ==================== هندلرها ====================

def start(update, context):
    uid = str(update.effective_user.id)
    
    if uid in db["blocked_users"]:
        update.message.reply_text("🚫 شما بلاک شده‌اید")
        return
    
    if uid not in db["users"]:
        db["users"][uid] = {
            "purchases": [],
            "tests": [],
            "test_count": 0,
            "date": datetime.now().strftime("%Y-%m-%d")
        }
        save_db()
    
    update.message.reply_text(f"🔰 به {db['brand']} خوش آمدید", reply_markup=main_menu(uid))

def handle_message(update, context):
    global user_temp
    try:
        text = update.message.text
        uid = str(update.effective_user.id)
        
        if uid in db["blocked_users"]:
            update.message.reply_text("🚫 شما بلاک شده‌اید")
            return
        
        step = user_temp.get(uid, {}).get('step')
        
        if text == '🔙 برگشت':
            user_temp[uid] = {}
            start(update, context)
            return
        
        # ========== منوی کاربر ==========
        
        # تست رایگان
        if text == '🎁 تست':
            if not db["panel_enabled"]:
                update.message.reply_text("❌ سرویس تست فعال نیست")
                return
            if db["users"][uid]["test_count"] >= 1:
                update.message.reply_text("❌ شما قبلاً تست گرفته‌اید")
                return
            
            update.message.reply_text("🔄 در حال ساخت اکانت تست...")
            config, error = create_test_vpn_account(uid)
            
            if config:
                db["users"][uid]["test_count"] += 1
                db["users"][uid]["tests"].append(datetime.now().strftime("%Y-%m-%d"))
                save_db()
                msg = f"🎁 اکانت تست شما آماده است\n━━━━━━━━━━━━━━━━━\n⏱ مدت: {db['test_hours']} ساعت\n📦 حجم: {db['test_volume']} مگابایت\n━━━━━━━━━━━━━━━━━\n🔗 {config}"
                update.message.reply_text(msg)
            else:
                update.message.reply_text(f"❌ {error}")
            return
        
        # سرویس‌های من
        if text == '📂 سرویس‌ها':
            purchases = db["users"][uid].get("purchases", [])
            tests = db["users"][uid].get("tests", [])
            msg = "📂 سرویس‌های شما:\n━━━━━━━━━━\n"
            if purchases:
                for p in purchases[-10:]:
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
            update.message.reply_text("📁 دسته مورد نظر را انتخاب کنید:", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
            return
        
        # نمایش پلن‌های یک دسته
        if text in db["categories"]:
            plans = db["categories"][text]
            keyboard = []
            for p in plans:
                keyboard.append([InlineKeyboardButton(f"{p['name']} - {p['price']:,} تومان", callback_data=f"plan_{p['id']}")])
            update.message.reply_text(f"📦 {text}", reply_markup=InlineKeyboardMarkup(keyboard))
            return
        
        # مرحله: اعمال کد تخفیف (اگر کاربر از دکمه زده باشد)
        if step == 'applying_discount':
            plan = user_temp[uid]['plan']
            original_price = plan['price']
            price = original_price
            
            if text.upper() in db["discount_codes"]:
                code_data = db["discount_codes"][text.upper()]
                if code_data["expires"] > datetime.now().timestamp():
                    discount = code_data["discount_percent"]
                    price = original_price * (100 - discount) // 100
                    code_data["uses"] += 1
                    save_db()
                    user_temp[uid]['discount'] = discount
                    user_temp[uid]['discount_code'] = text.upper()
                    update.message.reply_text(f"✅ کد تخفیف {discount}% اعمال شد\n💰 قیمت جدید: {price:,} تومان")
                else:
                    update.message.reply_text("❌ کد تخفیف منقضی شده است")
            else:
                update.message.reply_text("❌ کد تخفیف نامعتبر است")
            
            user_temp[uid]['final_price'] = price
            user_temp[uid]['step'] = 'showing_invoice'
            
            # نمایش پیش فاکتور نهایی
            show_invoice(update, uid)
            return
        
        # مرحله: دریافت نام اکانت (بعد از تایید نهایی)
        if step == 'getting_account_name':
            user_temp[uid]['account_name'] = text
            user_temp[uid]['step'] = 'waiting_for_receipt'
            update.message.reply_text("📸 لطفاً عکس فیش واریزی را ارسال کنید")
            return
        
        # ========== منوی ادمین ==========
        
        if str(uid) != str(ADMIN_ID):
            return
        
        if text == '⚙️ مدیریت':
            update.message.reply_text("🛠 پنل مدیریت:", reply_markup=admin_menu())
            return
        
        # تنظیمات تست
        if text == '🎁 تنظیمات تست':
            user_temp[uid] = {'step': 'set_test_volume'}
            update.message.reply_text(f"📊 حجم تست فعلی: {db['test_volume']} مگابایت\nلطفاً حجم جدید را وارد کنید:", reply_markup=back_btn())
            return
        
        if step == 'set_test_volume':
            try:
                db['test_volume'] = int(text)
                user_temp[uid]['step'] = 'set_test_hours'
                update.message.reply_text(f"⏱ مدت تست فعلی: {db['test_hours']} ساعت\nلطفاً مدت جدید را وارد کنید:")
            except:
                update.message.reply_text("❌ عدد معتبر وارد کنید")
            return
        
        if step == 'set_test_hours':
            try:
                db['test_hours'] = int(text)
                save_db()
                update.message.reply_text(f"✅ تنظیمات تست ذخیره شد\nحجم: {db['test_volume']} مگابایت\nمدت: {db['test_hours']} ساعت", reply_markup=admin_menu())
                user_temp[uid] = {}
            except:
                update.message.reply_text("❌ عدد معتبر وارد کنید")
            return
        
        # مدیریت کد تخفیف
        if text == '🎫 مدیریت کد تخفیف':
            kb = [['➕ ساخت کد جدید', '📋 لیست کدها'], ['❌ حذف کد'], ['🔙 برگشت']]
            update.message.reply_text("🎫 مدیریت کدهای تخفیف:", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
            return
        
        if text == '➕ ساخت کد جدید':
            user_temp[uid] = {'step': 'discount_percent'}
            update.message.reply_text("درصد تخفیف (1 تا 100):", reply_markup=back_btn())
            return
        
        if step == 'discount_percent':
            try:
                percent = int(text)
                if 1 <= percent <= 100:
                    user_temp[uid]['percent'] = percent
                    user_temp[uid]['step'] = 'discount_max_uses'
                    update.message.reply_text("حداکثر تعداد استفاده:")
                else:
                    update.message.reply_text("❌ درصد باید بین 1 تا 100 باشد")
            except:
                update.message.reply_text("❌ عدد معتبر وارد کنید")
            return
        
        if step == 'discount_max_uses':
            try:
                user_temp[uid]['max_uses'] = int(text)
                user_temp[uid]['step'] = 'discount_days'
                update.message.reply_text("مدت اعتبار (روز):")
            except:
                update.message.reply_text("❌ عدد معتبر وارد کنید")
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
                update.message.reply_text(f"✅ کد تخفیف ساخته شد:\n\n🎫 کد: `{code}`\n📊 درصد: {user_temp[uid]['percent']}%\n📋 حداکثر استفاده: {user_temp[uid]['max_uses']}\n⏱ اعتبار: {days} روز", parse_mode='Markdown', reply_markup=admin_menu())
                user_temp[uid] = {}
            except:
                update.message.reply_text("❌ عدد معتبر وارد کنید")
            return
        
        if text == '📋 لیست کدها':
            codes = db.get("discount_codes", {})
            if not codes:
                update.message.reply_text("❌ هیچ کد تخفیفی وجود ندارد")
            else:
                msg = "📋 لیست کدهای تخفیف:\n━━━━━━━━━━\n"
                for code, data in codes.items():
                    expires = datetime.fromtimestamp(data["expires"]).strftime("%Y-%m-%d")
                    msg += f"🎫 `{code}`\n   {data['discount_percent']}% | {data['uses']}/{data['max_uses']} | تا {expires}\n\n"
                update.message.reply_text(msg, parse_mode='Markdown')
            return
        
        if text == '❌ حذف کد':
            user_temp[uid] = {'step': 'delete_discount'}
            update.message.reply_text("کد تخفیف را وارد کنید:", reply_markup=back_btn())
            return
        
        if step == 'delete_discount':
            if text in db["discount_codes"]:
                del db["discount_codes"][text]
                save_db()
                update.message.reply_text("✅ کد تخفیف حذف شد", reply_markup=admin_menu())
            else:
                update.message.reply_text("❌ کد یافت نشد")
            user_temp[uid] = {}
            return
        
        # دسته‌بندی
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
                update.message.reply_text("❌ این دسته قبلاً وجود دارد")
            user_temp[uid] = {}
            return
        
        if text == '➖ حذف دسته':
            cats = list(db["categories"].keys())
            if not cats:
                update.message.reply_text("❌ دسته‌ای وجود ندارد")
                return
            kb = [[f"🗑 {cat}"] for cat in cats] + [['🔙 برگشت']]
            user_temp[uid] = {'step': 'delete_category'}
            update.message.reply_text("دسته مورد نظر را انتخاب کنید:", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
            return
        
        if step == 'delete_category' and text.startswith('🗑 '):
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
                update.message.reply_text("❌ ابتدا یک دسته بسازید")
                return
            kb = [[c] for c in cats] + [['🔙 برگشت']]
            user_temp[uid] = {'step': 'select_category_for_plan'}
            update.message.reply_text("دسته مورد نظر را انتخاب کنید:", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
            return
        
        if step == 'select_category_for_plan' and text in db["categories"]:
            user_temp[uid]['plan_category'] = text
            user_temp[uid]['step'] = 'new_plan_name'
            update.message.reply_text("نام پلن:", reply_markup=back_btn())
            return
        
        if step == 'new_plan_name':
            user_temp[uid]['plan_name'] = text
            user_temp[uid]['step'] = 'new_plan_volume'
            update.message.reply_text("حجم (بر حسب گیگابایت، مثال: 20):", reply_markup=back_btn())
            return
        
        if step == 'new_plan_volume':
            try:
                user_temp[uid]['plan_volume'] = int(text)
                user_temp[uid]['step'] = 'new_plan_days'
                update.message.reply_text("مدت اعتبار (روز):", reply_markup=back_btn())
            except:
                update.message.reply_text("❌ عدد وارد کنید")
            return
        
        if step == 'new_plan_days':
            try:
                user_temp[uid]['plan_days'] = int(text)
                user_temp[uid]['step'] = 'new_plan_price'
                update.message.reply_text("قیمت (تومان):", reply_markup=back_btn())
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
                db["categories"][user_temp[uid]['plan_category']].append(new_plan)
                save_db()
                update.message.reply_text(f"✅ پلن {user_temp[uid]['plan_name']} با موفقیت اضافه شد", reply_markup=admin_menu())
                user_temp[uid] = {}
            except:
                update.message.reply_text("❌ خطا در ایجاد پلن")
            return
        
        # حذف پلن
        if text == '➖ حذف پلن':
            keyboard = []
            for cat, plans in db["categories"].items():
                for p in plans:
                    keyboard.append([InlineKeyboardButton(f"❌ {cat} - {p['name']}", callback_data=f"delete_plan_{p['id']}")])
            if keyboard:
                update.message.reply_text("پلن مورد نظر را انتخاب کنید:", reply_markup=InlineKeyboardMarkup(keyboard))
            else:
                update.message.reply_text("❌ پلنی وجود ندارد")
            return
        
        # ویرایش کارت
        if text == '💳 ویرایش کارت':
            user_temp[uid] = {'step': 'edit_card_number'}
            update.message.reply_text(f"شماره کارت فعلی: {db['card']['number']}\nلطفاً شماره کارت 16 رقمی جدید را وارد کنید:", reply_markup=back_btn())
            return
        
        if step == 'edit_card_number':
            if text.isdigit() and len(text) == 16:
                db["card"]["number"] = text
                user_temp[uid]['step'] = 'edit_card_name'
                update.message.reply_text(f"نام فعلی: {db['card']['name']}\nلطفاً نام جدید را وارد کنید:")
            else:
                update.message.reply_text("❌ شماره کارت باید 16 رقم باشد")
            return
        
        if step == 'edit_card_name':
            db["card"]["name"] = text
            save_db()
            update.message.reply_text("✅ اطلاعات کارت به روز شد", reply_markup=admin_menu())
            user_temp[uid] = {}
            return
        
        # بلاک/آنبلاک کاربر
        if text == '🚫 بلاک/آنبلاک':
            user_temp[uid] = {'step': 'block_user'}
            update.message.reply_text("آیدی عددی کاربر را وارد کنید:", reply_markup=back_btn())
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
                update.message.reply_text("❌ آیدی عددی معتبر وارد کنید")
            user_temp[uid] = {}
            return
        
        # ارسال همگانی
        if text == '📨 ارسال همگانی':
            user_temp[uid] = {'step': 'broadcast'}
            update.message.reply_text("پیام خود را وارد کنید:", reply_markup=back_btn())
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
            update.message.reply_text(f"✅ پیام به {success} کاربر ارسال شد", reply_markup=admin_menu())
            user_temp[uid] = {}
            return
        
        # بکاپ و بازیابی
        if text == '💾 بکاپ/بازیابی':
            kb = [['💾 گرفتن بکاپ', '🔄 بازیابی بکاپ'], ['🔙 برگشت']]
            update.message.reply_text("مدیریت بکاپ:", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
            return
        
        if text == '💾 گرفتن بکاپ':
            if not os.path.exists(BACKUP_DIR):
                os.makedirs(BACKUP_DIR)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = os.path.join(BACKUP_DIR, f"backup_{timestamp}.json")
            shutil.copy2(DB_FILE, backup_file)
            update.message.reply_text(f"✅ بکاپ گرفته شد: {backup_file}", reply_markup=admin_menu())
            return
        
        if text == '🔄 بازیابی بکاپ':
            if os.path.exists(BACKUP_DIR):
                backups = [f for f in os.listdir(BACKUP_DIR) if f.endswith('.json')]
                if backups:
                    kb = [[f"📁 {b}"] for b in backups[-10:]] + [['🔙 برگشت']]
                    user_temp[uid] = {'step': 'restore_backup'}
                    update.message.reply_text("بکاپ مورد نظر را انتخاب کنید:", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
                else:
                    update.message.reply_text("❌ هیچ بکاپی یافت نشد")
            else:
                update.message.reply_text("❌ هیچ بکاپی یافت نشد")
            return
        
        if step == 'restore_backup' and text.startswith('📁 '):
            backup_file = text[2:]
            backup_path = os.path.join(BACKUP_DIR, backup_file)
            if os.path.exists(backup_path):
                shutil.copy2(backup_path, DB_FILE)
                load_db()
                update.message.reply_text("✅ بکاپ با موفقیت بازیابی شد", reply_markup=admin_menu())
            user_temp[uid] = {}
            return
        
    except Exception as e:
        logger.error(f"Message error: {e}")
        update.message.reply_text("❌ خطایی رخ داده است")

def show_invoice(update, uid):
    """نمایش پیش فاکتور با دو دکمه"""
    plan = user_temp[uid]['plan']
    price = user_temp[uid].get('final_price', plan['price'])
    discount = user_temp[uid].get('discount', 0)
    
    msg = f"📋 پیش فاکتور خرید\n━━━━━━━━━━━━━━━━━\n📦 {plan['name']}\n💰 قیمت: {plan['price']:,} تومان"
    
    if discount > 0:
        msg += f"\n🎫 تخفیف: {discount}%"
        msg += f"\n💵 مبلغ قابل پرداخت: {price:,} تومان"
    
    msg += f"\n━━━━━━━━━━━━━━━━━"
    
    keyboard = [
        [InlineKeyboardButton("🎫 کد تخفیف", callback_data=f"discount_{uid}")],
        [InlineKeyboardButton("💳 کارت به کارت", callback_data=f"card_payment_{uid}")]
    ]
    
    update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(keyboard))

def handle_callback(update, context):
    global user_temp
    try:
        query = update.callback_query
        uid = str(query.from_user.id)
        
        if uid in db["blocked_users"]:
            query.answer("شما بلاک شده‌اید")
            return
        
        query.answer()
        
        # انتخاب پلن
        if query.data.startswith("plan_"):
            plan_id = int(query.data.split("_")[1])
            for cat, plans in db["categories"].items():
                for p in plans:
                    if p["id"] == plan_id:
                        user_temp[uid] = {
                            'step': 'showing_invoice',
                            'plan': p,
                            'final_price': p['price']
                        }
                        query.message.delete()
                        show_invoice(update, uid)
                        return
            query.message.reply_text("❌ پلن یافت نشد")
            return
        
        # دکمه کد تخفیف
        if query.data.startswith("discount_"):
            user_temp[uid]['step'] = 'applying_discount'
            query.message.reply_text("🎫 کد تخفیف خود را وارد کنید:", reply_markup=back_btn())
            return
        
        # دکمه کارت به کارت
        if query.data.startswith("card_payment_"):
            if 'plan' not in user_temp[uid]:
                query.message.reply_text("❌ خطا، لطفاً دوباره خرید را شروع کنید")
                return
            
            plan = user_temp[uid]['plan']
            price = user_temp[uid].get('final_price', plan['price'])
            
            msg = f"💳 اطلاعات پرداخت\n━━━━━━━━━━━━━━━━━\n📦 {plan['name']}\n💰 مبلغ: {price:,} تومان\n━━━━━━━━━━━━━━━━━\n💳 شماره کارت:\n{db['card']['number']}\n👤 {db['card']['name']}\n━━━━━━━━━━━━━━━━━\nپس از واریز، نام اکانت خود را وارد کنید:"
            
            user_temp[uid]['step'] = 'getting_account_name'
            query.message.reply_text(msg, reply_markup=back_btn())
            return
        
        # حذف پلن توسط ادمین
        if query.data.startswith("delete_plan_"):
            if str(uid) == str(ADMIN_ID):
                plan_id = int(query.data.split("_")[2])
                for cat, plans in db["categories"].items():
                    for i, p in enumerate(plans):
                        if p["id"] == plan_id:
                            del plans[i]
                            save_db()
                            query.message.reply_text("✅ پلن حذف شد")
                            return
                query.message.reply_text("❌ پلن یافت نشد")
            return
        
    except Exception as e:
        logger.error(f"Callback error: {e}")
        query.message.reply_text("❌ خطا")

def handle_photo(update, context):
    global user_temp
    try:
        uid = str(update.effective_user.id)
        
        if uid in db["blocked_users"]:
            update.message.reply_text("🚫 شما بلاک شده‌اید")
            return
        
        step = user_temp.get(uid, {}).get('step')
        
        if step == 'waiting_for_receipt':
            plan = user_temp[uid].get('plan')
            price = user_temp[uid].get('final_price')
            account_name = user_temp[uid].get('account_name', 'کاربر')
            discount = user_temp[uid].get('discount', 0)
            
            if not plan:
                update.message.reply_text("❌ خطا، لطفاً دوباره خرید را شروع کنید")
                return
            
            # دریافت اطلاعات کاربر
            user_info = f"@{update.effective_user.username}" if update.effective_user.username else update.effective_user.first_name
            
            caption = f"💰 فیش جدید\n━━━━━━━━━━━━━━━━━\n👤 {user_info}\n🆔 {uid}\n📦 {plan['name']}\n💰 {price:,} تومان"
            if discount > 0:
                caption += f"\n🎫 تخفیف: {discount}%"
            caption += f"\n👤 نام اکانت: {account_name}"
            
            # ذخیره اطلاعات برای تایید ادمین
            receipt_data = {
                'uid': uid,
                'plan': plan,
                'price': price,
                'account_name': account_name,
                'discount': discount
            }
            encoded = base64.b64encode(json.dumps(receipt_data).encode()).decode()
            
            btn = InlineKeyboardMarkup([[
                InlineKeyboardButton("✅ تایید", callback_data=f"approve_{encoded}"),
                InlineKeyboardButton("❌ رد", callback_data=f"reject_{uid}")
            ]])
            
            context.bot.send_photo(ADMIN_ID, update.message.photo[-1].file_id, caption=caption, reply_markup=btn)
            update.message.reply_text("✅ فیش شما ارسال شد، پس از تایید سرویس فعال می‌شود")
            del user_temp[uid]
            return
        
        # دریافت دلیل رد توسط ادمین
        if step == 'reject_reason':
            target = user_temp[uid].get('target')
            if target:
                reason = update.message.caption or update.message.text or "دلیل مشخص نشده"
                context.bot.send_message(int(target), f"❌ فیش شما رد شد\nدلیل: {reason}")
                update.message.reply_text("✅ دلیل رد به کاربر اعلام شد")
            del user_temp[uid]
            return
        
    except Exception as e:
        logger.error(f"Photo error: {e}")
        update.message.reply_text("❌ خطا در ارسال فیش")

def admin_callback(update, context):
    global user_temp
    try:
        query = update.callback_query
        uid = str(query.from_user.id)
        
        if uid != str(ADMIN_ID):
            query.answer("❌ فقط ادمین", show_alert=True)
            return
        
        query.answer()
        
        # تایید فیش
        if query.data.startswith("approve_"):
            encoded = query.data.replace("approve_", "")
            data = json.loads(base64.b64decode(encoded).decode())
            
            target_uid = data['uid']
            plan = data['plan']
            account_name = data['account_name']
            price = data['price']
            
            query.message.edit_reply_markup(reply_markup=None)
            context.bot.send_message(ADMIN_ID, f"🔄 در حال ساخت اکانت برای کاربر {target_uid}...")
            
            # ساخت اکانت در پنل
            config, error = create_vpn_account(plan, target_uid, account_name)
            
            if config:
                # ثبت در تاریخچه کاربر
                service_record = f"✅ {plan['name']} | {plan['volume']}GB | {datetime.now().strftime('%Y-%m-%d')}"
                if target_uid not in db["users"]:
                    db["users"][target_uid] = {"purchases": [], "tests": [], "test_count": 0, "date": datetime.now().strftime("%Y-%m-%d")}
                db["users"][target_uid]["purchases"].append(service_record)
                save_db()
                
                msg = f"✅ پرداخت شما تأیید شد!\n━━━━━━━━━━━━━━━━━\n👤 {account_name}\n📦 {plan['name']}\n💰 {price:,} تومان\n━━━━━━━━━━━━━━━━━\n🔗 لینک اتصال:\n{config}\n━━━━━━━━━━━━━━━━━\n📚 {db['guide']}"
                
                try:
                    context.bot.send_message(int(target_uid), msg)
                    context.bot.send_message(ADMIN_ID, f"✅ کانفیگ برای کاربر {target_uid} ارسال شد")
                except Exception as e:
                    context.bot.send_message(ADMIN_ID, f"❌ خطا در ارسال کانفیگ: {e}")
            else:
                context.bot.send_message(ADMIN_ID, f"❌ خطا در ساخت اکانت: {error}")
            return
        
        # رد فیش
        if query.data.startswith("reject_"):
            target_uid = query.data.split("_")[1]
            user_temp[ADMIN_ID] = {'step': 'reject_reason', 'target': target_uid}
            query.message.reply_text("دلیل رد فیش را وارد کنید:")
            query.message.edit_reply_markup(reply_markup=None)
            return
        
    except Exception as e:
        logger.error(f"Admin callback error: {e}")
        query.message.reply_text("❌ خطا در پردازش")

def main():
    try:
        logger.info("🚀 Starting bot...")
        
        # حذف webhook برای جلوگیری از conflict
        requests.post(f"https://api.telegram.org/bot{TOKEN}/deleteWebhook", json={"drop_pending_updates": True})
        time.sleep(2)
        
        # ایجاد پوشه بکاپ
        if not os.path.exists(BACKUP_DIR):
            os.makedirs(BACKUP_DIR)
        
        # اجرای وب سرور
        Thread(target=run_web, daemon=True).start()
        
        # راه‌اندازی ربات
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
