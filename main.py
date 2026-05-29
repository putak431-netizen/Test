import os
import json
import logging
import requests
import time
import random
import string
import shutil
import base64
from datetime import datetime, timedelta
from threading import Thread
from flask import Flask
from telegram import ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, CallbackQueryHandler, Filters

# -------------------- تنظیمات لاگینگ --------------------
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# -------------------- وب سرور برای Railway --------------------
app_web = Flask(__name__)

@app_web.route('/')
def home():
    return "✅ VPN Bot is Running!", 200

def run_web():
    port = int(os.environ.get('PORT', 8080))
    app_web.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

# -------------------- توکن و تنظیمات --------------------
BOT_TOKEN = '8298942850:AAFdcOhM0se4nHJScRI5cSwKCM_6k4H_UHQ'
ADMIN_ID = 5993860770

# تنظیمات پنل سنایی (3x-ui)
PANEL_URL = "http://p.dragonteamm.shop:8081"
PANEL_USERNAME = "amir"
PANEL_PASSWORD = "amirreza871221"

# -------------------- دیتابیس --------------------
DB_FILE = 'data.json'
BACKUP_DIR = 'backups'

def load_db():
    """بارگذاری دیتابیس با تمام فیلدهای پیش‌فرض"""
    default_db = {
        "users": {},
        "brand": "تک نت وی‌پی‌ان",
        "card": {"number": "6277601368776066", "name": "محمد رضوانی"},
        "support": "@Support_Admin",
        "guide": "@Guide_Channel",
        "test_config": {"enabled": True, "volume": 50, "hours": 3},
        "discounts": {},
        "blocked": [],
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
    
    try:
        if os.path.exists(DB_FILE):
            with open(DB_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # اطمینان از وجود تمام فیلدها
                for key, value in default_db.items():
                    if key not in data:
                        data[key] = value
                # اطمینان از وجود categories
                if "categories" not in data or not data["categories"]:
                    data["categories"] = default_db["categories"]
                return data
    except Exception as e:
        logger.error(f"Error loading DB: {e}")
    
    return default_db

def save_db(data):
    try:
        with open(DB_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        return True
    except Exception as e:
        logger.error(f"Error saving DB: {e}")
        return False

db = load_db()
user_temp = {}

# -------------------- توابع اتصال به پنل 3x-ui (سنایی) --------------------
class ThreeXUIClient:
    """کلید اصلی اتصال به پنل 3x-ui - با استفاده از API استاندارد"""
    
    def __init__(self, url, username, password):
        self.url = url.rstrip('/')
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.cookies = None
        self.logged_in = False
    
    def login(self):
        """ورود به پنل و دریافت سشن"""
        try:
            # حذف /panel از انتهای URL اگر وجود داشت
            base_url = self.url.replace('/panel', '')
            
            # تلاش برای لاگین به پنل
            login_data = {
                "username": self.username,
                "password": self.password
            }
            
            # ارسال درخواست لاگین
            response = self.session.post(
                f"{base_url}/login",
                json=login_data,
                timeout=30
            )
            
            if response.status_code == 200:
                self.cookies = self.session.cookies
                self.logged_in = True
                logger.info("✅ Connected to 3x-ui panel successfully")
                return True, None
            
            # تلاش با endpoint جایگزین
            response2 = self.session.post(
                f"{base_url}/panel/login",
                json=login_data,
                timeout=30
            )
            
            if response2.status_code == 200:
                self.cookies = self.session.cookies
                self.logged_in = True
                logger.info("✅ Connected to 3x-ui panel successfully (alternative endpoint)")
                return True, None
            
            return False, f"خطا در اتصال: {response.status_code}"
            
        except Exception as e:
            return False, str(e)
    
    def add_client(self, email, total_gb, expiry_days, remark=""):
        """ساخت کلاینت جدید در پنل"""
        if not self.logged_in:
            success, error = self.login()
            if not success:
                return None, error
        
        try:
            base_url = self.url.replace('/panel', '')
            expiry_time = int((datetime.now() + timedelta(days=expiry_days)).timestamp())
            
            # دریافت لیست inboundها برای یافتن inbound فعال
            inbounds_res = self.session.get(
                f"{base_url}/panel/api/inbounds/list",
                timeout=30
            )
            
            if inbounds_res.status_code != 200:
                return None, "خطا در دریافت لیست inboundها"
            
            inbounds = inbounds_res.json().get('obj', [])
            
            # پیدا کردن اولین inbound فعال
            inbound_id = None
            for inbound in inbounds:
                if inbound.get('enable', True):
                    inbound_id = inbound.get('id')
                    break
            
            if not inbound_id:
                return None, "هیچ inbound فعالی یافت نشد"
            
            # ساخت کلاینت جدید
            client_data = {
                "id": inbound_id,
                "settings": json.dumps({
                    "clients": [{
                        "email": email,
                        "totalGB": total_gb,
                        "expiryTime": expiry_time * 1000,  # میلی‌ثانیه
                        "enable": True,
                        "remark": remark
                    }]
                })
            }
            
            add_res = self.session.post(
                f"{base_url}/panel/api/inbounds/addClient",
                json=client_data,
                timeout=30
            )
            
            if add_res.status_code == 200:
                result = add_res.json()
                if result.get('success'):
                    # دریافت لینک سابسکریپشن
                    sub_url = f"{base_url}/sub/{email}"
                    return sub_url, None
            
            return None, "خطا در ساخت اکانت"
            
        except Exception as e:
            logger.error(f"Add client error: {e}")
            return None, str(e)
    
    def get_client_traffic(self, email):
        """دریافت ترافیک مصرفی کلاینت"""
        if not self.logged_in:
            success, error = self.login()
            if not success:
                return None, error
        
        try:
            base_url = self.url.replace('/panel', '')
            traffic_res = self.session.post(
                f"{base_url}/panel/api/inbounds/getClientTraffics/{email}",
                timeout=30
            )
            
            if traffic_res.status_code == 200:
                data = traffic_res.json()
                return data.get('obj'), None
            
            return None, "خطا در دریافت ترافیک"
        except Exception as e:
            return None, str(e)

# ایجاد کلاینت پنل
panel_client = ThreeXUIClient(PANEL_URL, PANEL_USERNAME, PANEL_PASSWORD)

def create_vpn_account(plan, user_id, account_name):
    """ساخت اکانت VPN در پنل"""
    email = f"user_{user_id}_{int(time.time())}".replace('-', '_')
    remark = f"{account_name}_{user_id}"
    
    config_url, error = panel_client.add_client(email, plan['volume'], plan['days'], remark)
    
    if config_url:
        return config_url, None
    return None, error

def create_test_account(user_id):
    """ساخت اکانت تست"""
    if not db['test_config']['enabled']:
        return None, "تست غیرفعال است"
    
    volume_gb = db['test_config']['volume'] / 1024
    email = f"test_{user_id}_{int(time.time())}".replace('-', '_')
    
    config_url, error = panel_client.add_client(
        email, 
        round(volume_gb, 2), 
        0,  # تست بر اساس ساعت
        f"test_{user_id}"
    )
    
    if config_url:
        return config_url, None
    return None, error

# -------------------- منوها --------------------
def main_menu(uid):
    kb = [
        ['💰 خرید', '🎁 تست'],
        ['📂 سرویس‌ها', '👤 پشتیبانی'],
        ['📚 آموزش', '🤝 دعوت دوستان']
    ]
    if uid == ADMIN_ID:
        kb.append(['⚙️ مدیریت'])
    return ReplyKeyboardMarkup(kb, resize_keyboard=True)

def admin_menu():
    kb = [
        ['🎁 تنظیمات تست', '🎫 مدیریت تخفیف'],
        ['➕ دسته جدید', '➖ حذف دسته'],
        ['➕ پلن جدید', '➖ حذف پلن'],
        ['💳 ویرایش کارت', '🚫 بلاک کاربر'],
        ['📨 ارسال همگانی', '💾 بکاپ/بازیابی'],
        ['📊 آمار', '🔙 برگشت']
    ]
    return ReplyKeyboardMarkup(kb, resize_keyboard=True)

def back_btn():
    return ReplyKeyboardMarkup([['🔙 برگشت']], resize_keyboard=True)

# -------------------- هندلر استارت --------------------
def start(update, context):
    uid = update.effective_user.id
    
    if uid in db['blocked']:
        update.message.reply_text("🚫 شما توسط ادمین بلاک شده‌اید")
        return
    
    if str(uid) not in db['users']:
        db['users'][str(uid)] = {
            "purchases": [],
            "tests": [],
            "test_count": 0,
            "date": datetime.now().strftime("%Y-%m-%d")
        }
        save_db(db)
    
    update.message.reply_text(
        f"🔰 به {db['brand']} خوش آمدید\n\n"
        f"✅ فروش ویژه فیلترشکن\n"
        f"✅ پشتیبانی 24 ساعته\n"
        f"✅ نصب آسان",
        reply_markup=main_menu(uid)
    )

# -------------------- هندلر اصلی پیام‌ها --------------------
def handle_message(update, context):
    global user_temp
    try:
        text = update.message.text
        uid = update.effective_user.id
        
        if uid in db['blocked']:
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
            if not db['test_config']['enabled']:
                update.message.reply_text("❌ سرویس تست در حال حاضر غیرفعال است")
                return
            if db['users'][str(uid)]['test_count'] >= 1:
                update.message.reply_text("❌ شما قبلاً تست گرفته‌اید")
                return
            
            update.message.reply_text("🔄 در حال ساخت اکانت تست...")
            config, error = create_test_account(uid)
            
            if config:
                db['users'][str(uid)]['test_count'] += 1
                db['users'][str(uid)]['tests'].append(datetime.now().strftime("%Y-%m-%d"))
                save_db(db)
                
                msg = (
                    f"🎁 اکانت تست شما آماده است\n"
                    f"━━━━━━━━━━━━━━━━━\n"
                    f"⏱ مدت: {db['test_config']['hours']} ساعت\n"
                    f"📦 حجم: {db['test_config']['volume']} مگابایت\n"
                    f"━━━━━━━━━━━━━━━━━\n"
                    f"🔗 لینک اتصال:\n{config}\n\n"
                    f"📚 {db['guide']}"
                )
                update.message.reply_text(msg)
            else:
                update.message.reply_text(f"❌ خطا در ساخت تست: {error}")
            return
        
        # سرویس‌های من
        if text == '📂 سرویس‌ها':
            purchases = db['users'][str(uid)].get('purchases', [])
            tests = db['users'][str(uid)].get('tests', [])
            
            msg = "📂 سرویس‌های شما:\n━━━━━━━━━━\n"
            if purchases:
                msg += "✅ خریدها:\n"
                for i, p in enumerate(purchases[-10:], 1):
                    msg += f"{i}. {p}\n"
            else:
                msg += "❌ خریدی ندارید\n"
            
            if tests:
                msg += "\n🎁 تست‌ها:\n"
                for i, t in enumerate(tests[-5:], 1):
                    msg += f"{i}. {t}\n"
            
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
        
        # دعوت دوستان
        if text == '🤝 دعوت دوستان':
            bot_username = context.bot.get_me().username
            invite_link = f"https://t.me/{bot_username}?start={uid}"
            update.message.reply_text(
                f"🤝 لینک دعوت شما:\n{invite_link}\n\n"
                f"به ازای هر دعوت 1 روز هدیه"
            )
            return
        
        # خرید - نمایش دسته‌ها
        if text == '💰 خرید':
            categories = list(db['categories'].keys())
            kb = [[cat] for cat in categories] + [['🔙 برگشت']]
            update.message.reply_text(
                "📁 دسته مورد نظر را انتخاب کنید:",
                reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True)
            )
            return
        
        # نمایش پلن‌های یک دسته
        if text in db['categories']:
            plans = db['categories'][text]
            keyboard = []
            for p in plans:
                keyboard.append([InlineKeyboardButton(
                    f"{p['name']} - {p['price']:,} تومان",
                    callback_data=f"plan_{p['id']}"
                )])
            update.message.reply_text(
                f"📦 {text}",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return
        
        # ========== مرحله خرید ==========
        
        # مرحله 1: دریافت نام اکانت
        if step == 'get_account_name':
            user_temp[uid]['account_name'] = text
            user_temp[uid]['step'] = 'get_discount'
            update.message.reply_text(
                "🎫 کد تخفیف دارید؟ (در صورت نداشتن 'ندارم' را بفرستید):",
                reply_markup=back_btn()
            )
            return
        
        # مرحله 2: اعمال کد تخفیف
        if step == 'get_discount':
            plan = user_temp[uid]['plan']
            price = plan['price']
            discount_text = ""
            
            if text.upper() != 'ندارم':
                code = text.upper()
                if code in db['discounts']:
                    d = db['discounts'][code]
                    if d['expires'] > datetime.now().timestamp() and d['uses'] < d['max_uses']:
                        discount = d['percent']
                        price = price * (100 - discount) // 100
                        d['uses'] += 1
                        save_db(db)
                        user_temp[uid]['discount'] = discount
                        user_temp[uid]['discount_code'] = code
                        discount_text = f"\n🎫 تخفیف: {discount}% اعمال شد"
                        update.message.reply_text(f"✅ کد تخفیف {discount}% اعمال شد\n💰 قیمت جدید: {price:,} تومان")
                    else:
                        update.message.reply_text("❌ کد تخفیف نامعتبر یا منقضی")
                        discount_text = "\n❌ کد تخفیف نامعتبر"
                else:
                    update.message.reply_text("❌ کد تخفیف نامعتبر")
                    discount_text = "\n❌ کد تخفیف نامعتبر"
            else:
                update.message.reply_text("✅ بدون کد تخفیف ادامه می‌دهیم")
            
            user_temp[uid]['final_price'] = price
            user_temp[uid]['step'] = 'show_payment'
            
            # نمایش پیش فاکتور نهایی
            show_payment_invoice(update, uid)
            return
        
        # ========== منوی ادمین ==========
        
        if uid != ADMIN_ID:
            return
        
        if text == '⚙️ مدیریت':
            update.message.reply_text("🛠 پنل مدیریت:", reply_markup=admin_menu())
            return
        
        # تنظیمات تست
        if text == '🎁 تنظیمات تست':
            user_temp[uid] = {'step': 'set_test_volume'}
            update.message.reply_text(
                f"📊 حجم تست فعلی: {db['test_config']['volume']} مگابایت\n"
                f"لطفاً حجم جدید را وارد کنید (مثال: 50):",
                reply_markup=back_btn()
            )
            return
        
        if step == 'set_test_volume':
            try:
                db['test_config']['volume'] = int(text)
                user_temp[uid]['step'] = 'set_test_hours'
                update.message.reply_text(
                    f"⏱ مدت تست فعلی: {db['test_config']['hours']} ساعت\n"
                    f"لطفاً مدت جدید را وارد کنید (مثال: 3):"
                )
            except:
                update.message.reply_text("❌ عدد معتبر وارد کنید")
            return
        
        if step == 'set_test_hours':
            try:
                db['test_config']['hours'] = int(text)
                db['test_config']['enabled'] = True
                save_db(db)
                update.message.reply_text(
                    f"✅ تنظیمات تست ذخیره شد\n"
                    f"حجم: {db['test_config']['volume']} مگابایت\n"
                    f"مدت: {db['test_config']['hours']} ساعت",
                    reply_markup=admin_menu()
                )
                user_temp[uid] = {}
            except:
                update.message.reply_text("❌ عدد معتبر وارد کنید")
            return
        
        # مدیریت کد تخفیف
        if text == '🎫 مدیریت تخفیف':
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
                db['discounts'][code] = {
                    'percent': user_temp[uid]['percent'],
                    'max_uses': user_temp[uid]['max_uses'],
                    'uses': 0,
                    'expires': (datetime.now() + timedelta(days=days)).timestamp()
                }
                save_db(db)
                update.message.reply_text(
                    f"✅ کد تخفیف ساخته شد:\n\n"
                    f"🎫 کد: `{code}`\n"
                    f"📊 درصد: {user_temp[uid]['percent']}%\n"
                    f"📋 حداکثر استفاده: {user_temp[uid]['max_uses']}\n"
                    f"⏱ اعتبار: {days} روز",
                    parse_mode='Markdown',
                    reply_markup=admin_menu()
                )
                user_temp[uid] = {}
            except:
                update.message.reply_text("❌ عدد معتبر وارد کنید")
            return
        
        if text == '📋 لیست کدها':
            codes = db.get('discounts', {})
            if not codes:
                update.message.reply_text("❌ هیچ کد تخفیفی وجود ندارد")
            else:
                msg = "📋 لیست کدهای تخفیف:\n━━━━━━━━━━\n"
                for code, data in codes.items():
                    expires = datetime.fromtimestamp(data['expires']).strftime("%Y-%m-%d")
                    msg += f"🎫 `{code}`\n   {data['percent']}% | {data['uses']}/{data['max_uses']} | تا {expires}\n\n"
                update.message.reply_text(msg, parse_mode='Markdown')
            return
        
        if text == '❌ حذف کد':
            user_temp[uid] = {'step': 'delete_discount'}
            update.message.reply_text("کد تخفیف را وارد کنید:", reply_markup=back_btn())
            return
        
        if step == 'delete_discount':
            if text in db['discounts']:
                del db['discounts'][text]
                save_db(db)
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
            if text not in db['categories']:
                db['categories'][text] = []
                save_db(db)
                update.message.reply_text(f"✅ دسته {text} اضافه شد", reply_markup=admin_menu())
            else:
                update.message.reply_text("❌ این دسته قبلاً وجود دارد")
            user_temp[uid] = {}
            return
        
        if text == '➖ حذف دسته':
            categories = list(db['categories'].keys())
            if not categories:
                update.message.reply_text("❌ دسته‌ای وجود ندارد")
                return
            kb = [[f"🗑 {cat}"] for cat in categories] + [['🔙 برگشت']]
            user_temp[uid] = {'step': 'delete_category'}
            update.message.reply_text("دسته مورد نظر را انتخاب کنید:", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
            return
        
        if step == 'delete_category' and text.startswith('🗑 '):
            category = text[2:]
            if category in db['categories']:
                del db['categories'][category]
                save_db(db)
                update.message.reply_text(f"✅ دسته {category} حذف شد", reply_markup=admin_menu())
            user_temp[uid] = {}
            return
        
        # پلن جدید
        if text == '➕ پلن جدید':
            categories = list(db['categories'].keys())
            if not categories:
                update.message.reply_text("❌ ابتدا یک دسته بسازید")
                return
            kb = [[cat] for cat in categories] + [['🔙 برگشت']]
            user_temp[uid] = {'step': 'select_category_for_plan'}
            update.message.reply_text("دسته مورد نظر را انتخاب کنید:", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
            return
        
        if step == 'select_category_for_plan' and text in db['categories']:
            user_temp[uid]['plan_category'] = text
            user_temp[uid]['step'] = 'new_plan_name'
            update.message.reply_text("نام پلن:", reply_markup=back_btn())
            return
        
        if step == 'new_plan_name':
            user_temp[uid]['plan_name'] = text
            user_temp[uid]['step'] = 'new_plan_volume'
            update.message.reply_text("حجم (بر حسب گیگابایت، مثال: 20):")
            return
        
        if step == 'new_plan_volume':
            try:
                user_temp[uid]['plan_volume'] = int(text)
                user_temp[uid]['step'] = 'new_plan_days'
                update.message.reply_text("مدت اعتبار (روز):")
            except:
                update.message.reply_text("❌ عدد وارد کنید")
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
                for plans in db['categories'].values():
                    for p in plans:
                        if p['id'] > max_id:
                            max_id = p['id']
                
                new_plan = {
                    'id': max_id + 1,
                    'name': user_temp[uid]['plan_name'],
                    'price': price,
                    'volume': user_temp[uid]['plan_volume'],
                    'days': user_temp[uid]['plan_days']
                }
                db['categories'][user_temp[uid]['plan_category']].append(new_plan)
                save_db(db)
                update.message.reply_text(f"✅ پلن {user_temp[uid]['plan_name']} با موفقیت اضافه شد", reply_markup=admin_menu())
                user_temp[uid] = {}
            except:
                update.message.reply_text("❌ خطا در ایجاد پلن")
            return
        
        # حذف پلن
        if text == '➖ حذف پلن':
            keyboard = []
            for cat, plans in db['categories'].items():
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
            update.message.reply_text(
                f"💳 شماره کارت فعلی: {db['card']['number']}\n"
                f"لطفاً شماره کارت 16 رقمی جدید را وارد کنید:",
                reply_markup=back_btn()
            )
            return
        
        if step == 'edit_card_number':
            if text.isdigit() and len(text) == 16:
                db['card']['number'] = text
                user_temp[uid]['step'] = 'edit_card_name'
                update.message.reply_text(
                    f"👤 نام صاحب کارت فعلی: {db['card']['name']}\n"
                    f"لطفاً نام جدید را وارد کنید:"
                )
            else:
                update.message.reply_text("❌ شماره کارت باید 16 رقم باشد")
            return
        
        if step == 'edit_card_name':
            db['card']['name'] = text
            save_db(db)
            update.message.reply_text("✅ اطلاعات کارت به روز شد", reply_markup=admin_menu())
            user_temp[uid] = {}
            return
        
        # بلاک کاربر
        if text == '🚫 بلاک کاربر':
            user_temp[uid] = {'step': 'block_user'}
            update.message.reply_text("آیدی عددی کاربر را وارد کنید:", reply_markup=back_btn())
            return
        
        if step == 'block_user':
            try:
                target = str(int(text))
                if target == str(ADMIN_ID):
                    update.message.reply_text("❌ نمی‌توانید ادمین را بلاک کنید")
                elif target in db['blocked']:
                    db['blocked'].remove(target)
                    update.message.reply_text(f"✅ کاربر {target} آنبلاک شد")
                else:
                    db['blocked'].append(target)
                    update.message.reply_text(f"✅ کاربر {target} بلاک شد")
                save_db(db)
            except:
                update.message.reply_text("❌ آیدی عددی معتبر وارد کنید")
            user_temp[uid] = {}
            return
        
        # ارسال همگانی
        if text == '📨 ارسال همگانی':
            user_temp[uid] = {'step': 'broadcast'}
            update.message.reply_text("📨 پیام خود را وارد کنید:", reply_markup=back_btn())
            return
        
        if step == 'broadcast':
            success = 0
            for user_id in db['users']:
                if user_id not in db['blocked']:
                    try:
                        context.bot.send_message(int(user_id), text)
                        success += 1
                        time.sleep(0.05)
                    except:
                        pass
            update.message.reply_text(f"✅ پیام به {success} کاربر ارسال شد", reply_markup=admin_menu())
            user_temp[uid] = {}
            return
        
        # بکاپ
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
            
            # حذف بکاپ‌های قدیمی (فقط 10 تا آخر)
            backups = sorted([f for f in os.listdir(BACKUP_DIR) if f.endswith('.json')])
            for old in backups[:-10]:
                os.remove(os.path.join(BACKUP_DIR, old))
            
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
                global db
                db = load_db()
                update.message.reply_text("✅ بکاپ با موفقیت بازیابی شد", reply_markup=admin_menu())
            user_temp[uid] = {}
            return
        
        # آمار
        if text == '📊 آمار':
            total_users = len(db['users'])
            total_purchases = sum(len(u.get('purchases', [])) for u in db['users'].values())
            total_tests = sum(len(u.get('tests', [])) for u in db['users'].values())
            today = datetime.now().strftime("%Y-%m-%d")
            today_users = sum(1 for u in db['users'].values() if u.get('date', '').startswith(today))
            
            update.message.reply_text(
                f"📊 آمار ربات\n"
                f"━━━━━━━━━━\n"
                f"👥 کل کاربران: {total_users}\n"
                f"🆕 امروز: {today_users}\n"
                f"💰 کل خریدها: {total_purchases}\n"
                f"🎁 کل تست‌ها: {total_tests}",
                reply_markup=admin_menu()
            )
            return
        
    except Exception as e:
        logger.error(f"Message error: {e}")
        update.message.reply_text("❌ خطایی رخ داده است")

def show_payment_invoice(update, uid):
    """نمایش پیش فاکتور و روش پرداخت"""
    plan = user_temp[uid]['plan']
    price = user_temp[uid]['final_price']
    discount = user_temp[uid].get('discount', 0)
    
    msg = (
        f"📋 پیش فاکتور خرید\n"
        f"━━━━━━━━━━━━━━━━━\n"
        f"📦 {plan['name']}\n"
        f"💰 قیمت اصلی: {plan['price']:,} تومان"
    )
    
    if discount > 0:
        msg += f"\n🎫 تخفیف: {discount}%"
        msg += f"\n💵 مبلغ قابل پرداخت: {price:,} تومان"
    
    msg += f"\n━━━━━━━━━━━━━━━━━\n"
    msg += f"✅ لطفاً مبلغ را به کارت زیر واریز کنید:\n\n"
    msg += f"💳 شماره کارت:\n{db['card']['number']}\n"
    msg += f"👤 {db['card']['name']}\n"
    msg += f"━━━━━━━━━━━━━━━━━\n"
    msg += f"📸 پس از واریز، عکس فیش را ارسال کنید"
    
    # ذخیره می‌کنیم که کاربر در مرحله انتظار فیش است
    user_temp[uid]['step'] = 'waiting_for_receipt'
    
    update.message.reply_text(msg)

# -------------------- کالبک‌ها --------------------
def handle_callback(update, context):
    global user_temp
    try:
        query = update.callback_query
        uid = query.from_user.id
        query.answer()
        
        # انتخاب پلن
        if query.data.startswith("plan_"):
            plan_id = int(query.data.split("_")[1])
            for cat, plans in db['categories'].items():
                for p in plans:
                    if p['id'] == plan_id:
                        user_temp[uid] = {
                            'step': 'get_account_name',
                            'plan': p,
                            'final_price': p['price']
                        }
                        query.message.reply_text(
                            "👤 لطفاً نام اکانت خود را وارد کنید (مثال: Mohammad):",
                            reply_markup=back_btn()
                        )
                        return
            query.message.reply_text("❌ پلن یافت نشد")
            return
        
        # حذف پلن توسط ادمین
        if query.data.startswith("delete_plan_"):
            if uid == ADMIN_ID:
                plan_id = int(query.data.split("_")[2])
                for cat, plans in db['categories'].items():
                    for i, p in enumerate(plans):
                        if p['id'] == plan_id:
                            del plans[i]
                            save_db(db)
                            query.message.reply_text("✅ پلن حذف شد")
                            return
                query.message.reply_text("❌ پلن یافت نشد")
            return
        
    except Exception as e:
        logger.error(f"Callback error: {e}")

# -------------------- دریافت عکس (فیش) --------------------
def handle_photo(update, context):
    global user_temp
    try:
        uid = update.effective_user.id
        
        if uid in db['blocked']:
            update.message.reply_text("🚫 شما بلاک شده‌اید")
            return
        
        step = user_temp.get(uid, {}).get('step')
        
        # مرحله دریافت فیش
        if step == 'waiting_for_receipt':
            plan = user_temp[uid].get('plan')
            price = user_temp[uid].get('final_price')
            account_name = user_temp[uid].get('account_name', 'کاربر')
            discount = user_temp[uid].get('discount', 0)
            discount_code = user_temp[uid].get('discount_code', '')
            
            if not plan:
                update.message.reply_text("❌ خطا، لطفاً دوباره خرید را شروع کنید")
                return
            
            # دریافت اطلاعات کاربر
            user_info = f"@{update.effective_user.username}" if update.effective_user.username else update.effective_user.first_name
            
            caption = (
                f"💰 فیش جدید\n"
                f"━━━━━━━━━━━━━━━━━\n"
                f"👤 {user_info}\n"
                f"🆔 {uid}\n"
                f"📦 {plan['name']}\n"
                f"💰 مبلغ: {price:,} تومان"
            )
            
            if discount > 0:
                caption += f"\n🎫 تخفیف: {discount}%"
            if discount_code:
                caption += f"\n🎫 کد تخفیف: {discount_code}"
            
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

# -------------------- کالبک ادمین برای تایید/رد --------------------
def admin_callback(update, context):
    try:
        query = update.callback_query
        uid = query.from_user.id
        
        if uid != ADMIN_ID:
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
            config_url, error = create_vpn_account(plan, target_uid, account_name)
            
            if config_url:
                # ثبت در تاریخچه کاربر
                service_record = f"✅ {plan['name']} | {plan['volume']}GB | {datetime.now().strftime('%Y-%m-%d')}"
                if str(target_uid) not in db['users']:
                    db['users'][str(target_uid)] = {
                        "purchases": [], "tests": [], "test_count": 0,
                        "date": datetime.now().strftime("%Y-%m-%d")
                    }
                db['users'][str(target_uid)]['purchases'].append(service_record)
                save_db(db)
                
                msg = (
                    f"✅ پرداخت شما تأیید شد!\n"
                    f"━━━━━━━━━━━━━━━━━\n"
                    f"👤 {account_name}\n"
                    f"📦 {plan['name']}\n"
                    f"💰 {price:,} تومان\n"
                    f"━━━━━━━━━━━━━━━━━\n"
                    f"🔗 لینک اتصال:\n{config_url}\n\n"
                    f"📚 {db['guide']}"
                )
                
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

# -------------------- اجرای اصلی --------------------
def main():
    try:
        logger.info("🚀 Starting bot...")
        
        # حذف webhook برای جلوگیری از conflict
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook", json={"drop_pending_updates": True})
        time.sleep(2)
        
        # ایجاد پوشه بکاپ
        if not os.path.exists(BACKUP_DIR):
            os.makedirs(BACKUP_DIR)
        
        # تست اتصال به پنل
        logger.info("Testing panel connection...")
        success, error = panel_client.login()
        if success:
            logger.info("✅ Panel connection successful")
        else:
            logger.warning(f"⚠️ Panel connection failed: {error}")
        
        # اجرای وب سرور
        Thread(target=run_web, daemon=True).start()
        
        # راه‌اندازی ربات
        updater = Updater(BOT_TOKEN, use_context=True)
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
