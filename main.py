import os
import json
import logging
from flask import Flask
from threading import Thread
from telegram import ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, CallbackQueryHandler, Filters
from datetime import datetime, timedelta
import requests
import time
import base64

# -------------------- تنظیمات اولیه --------------------
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

app_web = Flask(__name__)

@app_web.route('/')
def home():
    return "✅ Bot is Running!", 200

def run_web():
    port = int(os.environ.get('PORT', 8080))
    app_web.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

# -------------------- توکن ها و تنظیمات --------------------
BOT_TOKEN = '8298942850:AAFdcOhM0se4nHJScRI5cSwKCM_6k4H_UHQ'
ADMIN_ID = 5993860770

# تنظیمات پنل سنایی
PANEL_URL = "http://p.dragonteamm.shop:8081"
PANEL_ADMIN_PATH = "hke43Y4nhZ23K1vc4S"
PANEL_API_TOKEN = "6bUP6MaB0Z7g6bmH2S3qyUdDKsjnhCgOeLxmsxoHeSJHiKm3"

# -------------------- دیتابیس --------------------
DB_FILE = 'data.json'

def load_db():
    try:
        if os.path.exists(DB_FILE):
            with open(DB_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except:
        pass
    
    return {
        "users": {},
        "card": {"number": "6277601368776066", "name": "محمد رضوانی"},
        "support": "@Support_Admin",
        "guide": "@Guide_Channel",
        "test_config": {"volume": 50, "hours": 3, "enabled": True},
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
            ]
        }
    }

def save_db(data):
    try:
        with open(DB_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        return True
    except:
        return False

db = load_db()
user_temp = {}

# -------------------- توابع پنل سنایی --------------------
def create_account_on_panel(volume_gb, days, user_id):
    """ساخت اکانت در پنل سنایی"""
    try:
        email = f"u{user_id}_{int(time.time())}@vpn.local"
        expiry = int((datetime.now() + timedelta(days=days)).timestamp())
        
        headers = {
            "Authorization": f"Bearer {PANEL_API_TOKEN}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "email": email,
            "total_gb": volume_gb,
            "expiry_time": expiry,
            "enable": True
        }
        
        url = f"{PANEL_URL}/{PANEL_ADMIN_PATH}/api/user/add"
        
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success') or result.get('status') == 'success':
                return f"{PANEL_URL}/sub/{email}", None
        
        return None, "خطا در ساخت اکانت"
    except Exception as e:
        return None, str(e)

def create_test_account_on_panel(user_id):
    """ساخت اکانت تست"""
    try:
        email = f"test_{user_id}_{int(time.time())}@vpn.local"
        volume_gb = db['test_config']['volume'] / 1024
        expiry = int((datetime.now() + timedelta(hours=db['test_config']['hours'])).timestamp())
        
        headers = {"Authorization": f"Bearer {PANEL_API_TOKEN}", "Content-Type": "application/json"}
        payload = {"email": email, "total_gb": round(volume_gb, 2), "expiry_time": expiry, "enable": True}
        url = f"{PANEL_URL}/{PANEL_ADMIN_PATH}/api/user/add"
        
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        
        if response.status_code == 200 and (response.json().get('success') or response.json().get('status') == 'success'):
            return f"{PANEL_URL}/sub/{email}", None
        return None, "خطا"
    except Exception as e:
        return None, str(e)

# -------------------- منوها --------------------
def main_menu(uid):
    kb = [['💰 خرید', '🎁 تست'], ['📂 سرویس‌ها', '👤 پشتیبانی'], ['📚 آموزش']]
    if uid == ADMIN_ID:
        kb.append(['⚙️ مدیریت'])
    return ReplyKeyboardMarkup(kb, resize_keyboard=True)

def admin_menu():
    kb = [
        ['🎁 تنظیم تست', '🎫 کد تخفیف'],
        ['➕ دسته جدید', '➖ حذف دسته'],
        ['➕ پلن جدید', '➖ حذف پلن'],
        ['💳 کارت', '📨 همگانی'],
        ['🔙 برگشت']
    ]
    return ReplyKeyboardMarkup(kb, resize_keyboard=True)

def back_btn():
    return ReplyKeyboardMarkup([['🔙 برگشت']], resize_keyboard=True)

# -------------------- هندلر استارت --------------------
def start(update, context):
    uid = update.effective_user.id
    
    if uid in db['blocked']:
        update.message.reply_text("🚫 شما بلاک شده‌اید")
        return
    
    if str(uid) not in db['users']:
        db['users'][str(uid)] = {"purchases": [], "tests": [], "test_count": 0, "date": datetime.now().strftime("%Y-%m-%d")}
        save_db(db)
    
    update.message.reply_text("🔰 به ربات فروش وی‌پی‌ان خوش آمدید", reply_markup=main_menu(uid))

# -------------------- هندلر اصلی --------------------
def handle_message(update, context):
    global user_temp
    try:
        text = update.message.text
        uid = update.effective_user.id
        
        if uid in db['blocked']:
            update.message.reply_text("🚫 بلاک شده‌اید")
            return
        
        step = user_temp.get(uid, {}).get('step')
        
        if text == '🔙 برگشت':
            user_temp[uid] = {}
            start(update, context)
            return
        
        # ========== کاربر ==========
        
        # تست
        if text == '🎁 تست':
            if not db['test_config']['enabled']:
                update.message.reply_text("❌ تست غیرفعال است")
                return
            if db['users'][str(uid)]['test_count'] >= 1:
                update.message.reply_text("❌ قبلاً تست گرفته‌اید")
                return
            
            update.message.reply_text("🔄 ساخت اکانت تست...")
            config, error = create_test_account_on_panel(uid)
            
            if config:
                db['users'][str(uid)]['test_count'] += 1
                db['users'][str(uid)]['tests'].append(datetime.now().strftime("%Y-%m-%d"))
                save_db(db)
                update.message.reply_text(f"🎁 اکانت تست شما:\n⏱ {db['test_config']['hours']} ساعت\n📦 {db['test_config']['volume']} مگابایت\n\n🔗 {config}")
            else:
                update.message.reply_text(f"❌ {error}")
            return
        
        # سرویس‌ها
        if text == '📂 سرویس‌ها':
            pur = db['users'][str(uid)].get('purchases', [])
            tests = db['users'][str(uid)].get('tests', [])
            msg = "📂 سرویس‌های شما:\n"
            msg += "خریدها:\n" + "\n".join(pur[-10:]) if pur else "خریدی ندارید\n"
            msg += "\nتست‌ها:\n" + "\n".join(tests[-5:]) if tests else ""
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
            cats = list(db['categories'].keys())
            kb = [[c] for c in cats] + [['🔙 برگشت']]
            update.message.reply_text("دسته را انتخاب کنید:", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
            return
        
        # نمایش پلن‌های دسته
        if text in db['categories']:
            plans = db['categories'][text]
            keyboard = []
            for p in plans:
                keyboard.append([InlineKeyboardButton(f"{p['name']} - {p['price']:,} تومان", callback_data=f"plan_{p['id']}")])
            update.message.reply_text(f"📦 {text}", reply_markup=InlineKeyboardMarkup(keyboard))
            return
        
        # دریافت کد تخفیف
        if step == 'get_discount':
            plan = user_temp[uid]['plan']
            price = plan['price']
            
            if text.upper() in db['discounts']:
                d = db['discounts'][text.upper()]
                if d['expires'] > datetime.now().timestamp() and d['uses'] < d['max_uses']:
                    price = price * (100 - d['percent']) // 100
                    d['uses'] += 1
                    save_db(db)
                    user_temp[uid]['discount'] = d['percent']
                    update.message.reply_text(f"✅ تخفیف {d['percent']}% اعمال شد\n💰 قیمت: {price:,} تومان")
                else:
                    update.message.reply_text("❌ کد منقضی شده")
            else:
                update.message.reply_text("❌ کد نامعتبر")
            
            user_temp[uid]['final_price'] = price
            user_temp[uid]['step'] = 'get_account_name'
            update.message.reply_text("👤 نام اکانت خود را وارد کنید:", reply_markup=back_btn())
            return
        
        # دریافت نام اکانت
        if step == 'get_account_name':
            user_temp[uid]['account_name'] = text
            user_temp[uid]['step'] = 'wait_photo'
            
            plan = user_temp[uid]['plan']
            price = user_temp[uid]['final_price']
            
            msg = f"💳 اطلاعات پرداخت\n━━━━━━━━━━\n📦 {plan['name']}\n💰 {price:,} تومان\n━━━━━━━━━━\n💳 شماره کارت:\n{db['card']['number']}\n👤 {db['card']['name']}\n━━━━━━━━━━\nلطفاً عکس فیش را ارسال کنید"
            
            update.message.reply_text(msg)
            return
        
        # ========== ادمین ==========
        
        if uid != ADMIN_ID:
            return
        
        if text == '⚙️ مدیریت':
            update.message.reply_text("🛠 پنل مدیریت:", reply_markup=admin_menu())
            return
        
        # تنظیم تست
        if text == '🎁 تنظیم تست':
            user_temp[uid] = {'step': 'set_volume'}
            update.message.reply_text(f"حجم فعلی: {db['test_config']['volume']} مگابایت\nحجم جدید:", reply_markup=back_btn())
            return
        
        if step == 'set_volume':
            try:
                db['test_config']['volume'] = int(text)
                user_temp[uid]['step'] = 'set_hours'
                update.message.reply_text(f"مدت فعلی: {db['test_config']['hours']} ساعت\nمدت جدید:")
            except:
                update.message.reply_text("❌ عدد وارد کن")
            return
        
        if step == 'set_hours':
            try:
                db['test_config']['hours'] = int(text)
                db['test_config']['enabled'] = True
                save_db(db)
                update.message.reply_text("✅ تنظیمات تست ذخیره شد", reply_markup=admin_menu())
                user_temp[uid] = {}
            except:
                update.message.reply_text("❌ عدد وارد کن")
            return
        
        # کد تخفیف
        if text == '🎫 کد تخفیف':
            user_temp[uid] = {'step': 'make_discount'}
            update.message.reply_text("درصد تخفیف:", reply_markup=back_btn())
            return
        
        if step == 'make_discount':
            try:
                user_temp[uid]['percent'] = int(text)
                user_temp[uid]['step'] = 'make_discount_max'
                update.message.reply_text("حداکثر استفاده:")
            except:
                update.message.reply_text("❌ عدد وارد کن")
            return
        
        if step == 'make_discount_max':
            try:
                user_temp[uid]['max_uses'] = int(text)
                user_temp[uid]['step'] = 'make_discount_days'
                update.message.reply_text("مدت اعتبار (روز):")
            except:
                update.message.reply_text("❌ عدد وارد کن")
            return
        
        if step == 'make_discount_days':
            try:
                days = int(text)
                import random, string
                code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
                db['discounts'][code] = {
                    'percent': user_temp[uid]['percent'],
                    'max_uses': user_temp[uid]['max_uses'],
                    'uses': 0,
                    'expires': (datetime.now() + timedelta(days=days)).timestamp()
                }
                save_db(db)
                update.message.reply_text(f"✅ کد: `{code}`\n{user_temp[uid]['percent']}% تخفیف\n{user_temp[uid]['max_uses']} بار\n{days} روز", parse_mode='Markdown', reply_markup=admin_menu())
                user_temp[uid] = {}
            except:
                update.message.reply_text("❌ عدد وارد کن")
            return
        
        # دسته جدید
        if text == '➕ دسته جدید':
            user_temp[uid] = {'step': 'new_cat'}
            update.message.reply_text("نام دسته:", reply_markup=back_btn())
            return
        
        if step == 'new_cat':
            if text not in db['categories']:
                db['categories'][text] = []
                save_db(db)
                update.message.reply_text(f"✅ دسته {text} اضافه شد", reply_markup=admin_menu())
            else:
                update.message.reply_text("❌ تکراری")
            user_temp[uid] = {}
            return
        
        # حذف دسته
        if text == '➖ حذف دسته':
            cats = list(db['categories'].keys())
            if cats:
                kb = [[f"🗑 {c}"] for c in cats] + [['🔙 برگشت']]
                user_temp[uid] = {'step': 'del_cat'}
                update.message.reply_text("دسته را انتخاب کنید:", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
            else:
                update.message.reply_text("❌ دسته‌ای نیست")
            return
        
        if step == 'del_cat' and text.startswith('🗑 '):
            cat = text[2:]
            if cat in db['categories']:
                del db['categories'][cat]
                save_db(db)
                update.message.reply_text(f"✅ دسته {cat} حذف شد", reply_markup=admin_menu())
            user_temp[uid] = {}
            return
        
        # پلن جدید
        if text == '➕ پلن جدید':
            cats = list(db['categories'].keys())
            if cats:
                kb = [[c] for c in cats] + [['🔙 برگشت']]
                user_temp[uid] = {'step': 'select_cat_plan'}
                update.message.reply_text("دسته را انتخاب کنید:", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
            else:
                update.message.reply_text("❌ ابتدا دسته بسازید")
            return
        
        if step == 'select_cat_plan' and text in db['categories']:
            user_temp[uid]['cat'] = text
            user_temp[uid]['step'] = 'plan_name'
            update.message.reply_text("نام پلن:", reply_markup=back_btn())
            return
        
        if step == 'plan_name':
            user_temp[uid]['name'] = text
            user_temp[uid]['step'] = 'plan_volume'
            update.message.reply_text("حجم (گیگابایت):")
            return
        
        if step == 'plan_volume':
            try:
                user_temp[uid]['volume'] = int(text)
                user_temp[uid]['step'] = 'plan_days'
                update.message.reply_text("مدت (روز):")
            except:
                update.message.reply_text("❌ عدد وارد کن")
            return
        
        if step == 'plan_days':
            try:
                user_temp[uid]['days'] = int(text)
                user_temp[uid]['step'] = 'plan_price'
                update.message.reply_text("قیمت (تومان):")
            except:
                update.message.reply_text("❌ عدد وارد کن")
            return
        
        if step == 'plan_price':
            try:
                price = int(text)
                max_id = 0
                for plans in db['categories'].values():
                    for p in plans:
                        if p['id'] > max_id:
                            max_id = p['id']
                
                new_plan = {
                    'id': max_id + 1,
                    'name': user_temp[uid]['name'],
                    'price': price,
                    'volume': user_temp[uid]['volume'],
                    'days': user_temp[uid]['days']
                }
                db['categories'][user_temp[uid]['cat']].append(new_plan)
                save_db(db)
                update.message.reply_text("✅ پلن اضافه شد", reply_markup=admin_menu())
                user_temp[uid] = {}
            except:
                update.message.reply_text("❌ خطا")
            return
        
        # حذف پلن
        if text == '➖ حذف پلن':
            keyboard = []
            for cat, plans in db['categories'].items():
                for p in plans:
                    keyboard.append([InlineKeyboardButton(f"❌ {cat} - {p['name']}", callback_data=f"delplan_{p['id']}")])
            if keyboard:
                update.message.reply_text("پلن را انتخاب کنید:", reply_markup=InlineKeyboardMarkup(keyboard))
            else:
                update.message.reply_text("❌ پلنی نیست")
            return
        
        # ویرایش کارت
        if text == '💳 کارت':
            user_temp[uid] = {'step': 'edit_card'}
            update.message.reply_text(f"شماره فعلی: {db['card']['number']}\nشماره جدید (16 رقم):", reply_markup=back_btn())
            return
        
        if step == 'edit_card':
            if text.isdigit() and len(text) == 16:
                db['card']['number'] = text
                user_temp[uid]['step'] = 'edit_name'
                update.message.reply_text(f"نام فعلی: {db['card']['name']}\nنام جدید:")
            else:
                update.message.reply_text("❌ 16 رقم وارد کن")
            return
        
        if step == 'edit_name':
            db['card']['name'] = text
            save_db(db)
            update.message.reply_text("✅ کارت ذخیره شد", reply_markup=admin_menu())
            user_temp[uid] = {}
            return
        
        # ارسال همگانی
        if text == '📨 همگانی':
            user_temp[uid] = {'step': 'broadcast'}
            update.message.reply_text("پیام را بفرست:", reply_markup=back_btn())
            return
        
        if step == 'broadcast':
            success = 0
            for uid2 in db['users']:
                if int(uid2) not in db['blocked']:
                    try:
                        context.bot.send_message(int(uid2), text)
                        success += 1
                    except:
                        pass
            update.message.reply_text(f"✅ به {success} نفر ارسال شد", reply_markup=admin_menu())
            user_temp[uid] = {}
            return
        
    except Exception as e:
        logger.error(f"Error: {e}")
        update.message.reply_text("❌ خطا")

# -------------------- کالبک --------------------
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
                            'step': 'get_discount',
                            'plan': p,
                            'final_price': p['price']
                        }
                        query.message.reply_text("🎫 کد تخفیف دارید؟ وارد کنید، در غیر اینصورت 'ندارم' را بفرستید:", reply_markup=back_btn())
                        return
            query.message.reply_text("❌ پلن یافت نشد")
            return
        
        # حذف پلن (ادمین)
        if query.data.startswith("delplan_"):
            if uid == ADMIN_ID:
                plan_id = int(query.data.split("_")[1])
                for cat, plans in db['categories'].items():
                    for i, p in enumerate(plans):
                        if p['id'] == plan_id:
                            del plans[i]
                            save_db(db)
                            query.message.reply_text("✅ پلن حذف شد")
                            return
                query.message.reply_text("❌ یافت نشد")
            return
        
    except Exception as e:
        logger.error(f"Callback error: {e}")

# -------------------- دریافت عکس --------------------
def handle_photo(update, context):
    global user_temp
    try:
        uid = update.effective_user.id
        
        if uid in db['blocked']:
            update.message.reply_text("🚫 بلاک شده‌اید")
            return
        
        step = user_temp.get(uid, {}).get('step')
        
        if step == 'wait_photo':
            plan = user_temp[uid].get('plan')
            price = user_temp[uid].get('final_price')
            account_name = user_temp[uid].get('account_name')
            discount = user_temp[uid].get('discount', 0)
            
            user_info = f"@{update.effective_user.username}" if update.effective_user.username else update.effective_user.first_name
            
            caption = f"💰 فیش جدید\n━━━━━━━━━━\n👤 {user_info}\n🆔 {uid}\n📦 {plan['name']}\n💰 {price:,} تومان"
            if discount > 0:
                caption += f"\n🎫 تخفیف: {discount}%"
            caption += f"\n👤 اکانت: {account_name}"
            
            data = {'uid': uid, 'plan': plan, 'account': account_name, 'price': price}
            encoded = base64.b64encode(json.dumps(data).encode()).decode()
            
            btn = InlineKeyboardMarkup([[
                InlineKeyboardButton("✅ تایید", callback_data=f"approve_{encoded}"),
                InlineKeyboardButton("❌ رد", callback_data=f"reject_{uid}")
            ]])
            
            context.bot.send_photo(ADMIN_ID, update.message.photo[-1].file_id, caption=caption, reply_markup=btn)
            update.message.reply_text("✅ فیش ارسال شد")
            del user_temp[uid]
        
        if step == 'reject_reason':
            target = user_temp[uid].get('target')
            if target:
                reason = update.message.caption or update.message.text or "دلیل نامشخص"
                context.bot.send_message(int(target), f"❌ فیش شما رد شد\nدلیل: {reason}")
                update.message.reply_text("✅ دلیل رد ارسال شد")
            del user_temp[uid]
        
    except Exception as e:
        logger.error(f"Photo error: {e}")

# -------------------- کالبک ادمین --------------------
def admin_callback(update, context):
    try:
        query = update.callback_query
        uid = query.from_user.id
        
        if uid != ADMIN_ID:
            query.answer("❌ فقط ادمین", show_alert=True)
            return
        
        query.answer()
        
        if query.data.startswith("approve_"):
            encoded = query.data.replace("approve_", "")
            data = json.loads(base64.b64decode(encoded).decode())
            
            target_uid = data['uid']
            plan = data['plan']
            account_name = data['account']
            
            query.message.edit_reply_markup(reply_markup=None)
            context.bot.send_message(ADMIN_ID, f"🔄 ساخت اکانت برای {target_uid}...")
            
            config, error = create_account_on_panel(plan['volume'], plan['days'], target_uid)
            
            if config:
                service = f"{plan['name']} | {plan['volume']}GB | {datetime.now().strftime('%Y-%m-%d')}"
                db['users'][str(target_uid)]['purchases'].append(service)
                save_db(db)
                
                msg = f"✅ پرداخت تأیید شد!\n👤 {account_name}\n📦 {plan['name']}\n🔗 {config}"
                try:
                    context.bot.send_message(target_uid, msg)
                    context.bot.send_message(ADMIN_ID, f"✅ کانفیگ ارسال شد")
                except:
                    context.bot.send_message(ADMIN_ID, f"❌ خطا در ارسال")
            else:
                context.bot.send_message(ADMIN_ID, f"❌ خطا: {error}")
            return
        
        if query.data.startswith("reject_"):
            target_uid = int(query.data.split("_")[1])
            user_temp[ADMIN_ID] = {'step': 'reject_reason', 'target': target_uid}
            query.message.reply_text("دلیل رد را وارد کنید:")
            query.message.edit_reply_markup(reply_markup=None)
            return
        
    except Exception as e:
        logger.error(f"Admin callback error: {e}")

# -------------------- اجرا --------------------
def main():
    try:
        logger.info("🚀 Starting bot...")
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook", json={"drop_pending_updates": True})
        time.sleep(2)
        
        Thread(target=run_web, daemon=True).start()
        
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
