# БОЛЬШЕ СКРИПТОВ НА endway.org
# endway.org | endway.su

import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import CommandStart, Command
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from uuid import uuid4
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from urllib.parse import quote
from datetime import datetime

load_dotenv()

BOT_TOKEN = os.getenv("8086792303:AAFYC6hmgZMsLBjVwS2g-8AuNEUzKwHEWiw")
MONGODB_URI = os.getenv("mongodb+srv://capone:<popa22830399>@cluster0.imruwlj.mongodb.net/")
SUPPORT_USERNAME = os.getenv("arseniylap2011")
ADMIN_ID = int(os.getenv("ADMIN_ID", "8795006636"))

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN, parse_mode="HTML")
dp = Dispatcher()

mongo_client = AsyncIOMotorClient(MONGODB_URI)
db = mongo_client.get_default_database()

# Клавиатура главного меню
def get_main_menu(is_admin=False):
    settings = None
    try:
        settings = asyncio.get_event_loop().run_until_complete(db.settings.find_one({"_id": "main"}))
    except:
        pass
    support_username = settings.get("support_username") if settings and settings.get("support_username") else SUPPORT_USERNAME
    menu = [
        [InlineKeyboardButton(text="🛒 Магазин", callback_data="shop")],
        [
            InlineKeyboardButton(text="🛍 Покупки", callback_data="orders"),
            InlineKeyboardButton(text="🎁 Промокод", callback_data="promo")
        ],
        [
            InlineKeyboardButton(text="👥 Рефералка", callback_data="referral"),
            InlineKeyboardButton(text="💬 Поддержка", callback_data="support")
        ]
    ]
    if is_admin:
        menu.append([InlineKeyboardButton(text="🔐 Админ-панель", callback_data="admin_panel")])
    return InlineKeyboardMarkup(inline_keyboard=menu)

# Клавиатура выбора города
city_keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Сургут", callback_data="city_Сургут")],
    [InlineKeyboardButton(text="Тюмень", callback_data="city_Тюмень")],
    [InlineKeyboardButton(text="Когалым", callback_data="city_Когалым")],
    [InlineKeyboardButton(text="Ханты-мансийск", callback_data="city_Ханты-мансийск")],
    [InlineKeyboardButton(text="Нижневартовск", callback_data="city_Нижневартовск")],
    [InlineKeyboardButton(text="Юг", callback_data="city_Юг")],
    [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu")],
])

# Клавиатура выбора товара
product_keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Скорость", callback_data="product_Скорость")],
    [InlineKeyboardButton(text="Бошки", callback_data="product_Бошки")],
    [InlineKeyboardButton(text="Меф КРИС", callback_data="product_МефКРИС")],
    [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_city")],
])

# Клавиатура выбора района
area_keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="По городу", callback_data="area_citywide")],
    [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_pack")],
])

# Клавиатура выбора типа клада
stash_type_keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Магнит", callback_data="stash_magnet")],
    [InlineKeyboardButton(text="Прикоп", callback_data="stash_prikop")],
    [InlineKeyboardButton(text="Тайник", callback_data="stash_tainik")],
    [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_area")],
])

# Клавиатура выбора способа оплаты
payment_keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Банковская карта", callback_data="pay_card")],
    [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_stash")],
])

# --- Конфигурация фасовок по городам и товарам ---
CITY_GROUP_1 = ["Сургут", "Тюмень", "Когалым"]
CITY_GROUP_2 = ["Ханты-мансийск", "Нижневартовск", "Юг"]

PRODUCT_PACKS = {
    "group1": {
        "Скорость": [
            ("0.3г - 3800₽", "pack_03g_3800"),
            ("0.5г - 5500₽", "pack_05g_5500"),
            ("1г - 7000₽", "pack_1g_7000"),
        ],
        "Бошки": [
            ("1г - 3000₽", "pack_1g_3000"),
            ("2г - 5000₽", "pack_2g_5000"),
        ],
        "Меф КРИС": [
            ("1г - 6000₽", "pack_1g_6000"),
        ],
    },
    "group2": {
        "Скорость": [
            ("0.3г - 3900₽", "pack_03g_3900"),
            ("0.5г - 5700₽", "pack_05g_5700"),
            ("1г - 7200₽", "pack_1g_7200"),
        ],
        "Бошки": [
            ("1г - 3500₽", "pack_1g_3500"),
            ("2г - 6000₽", "pack_2g_6000"),
        ],
        "Меф КРИС": [
            ("1г - 6500₽", "pack_1g_6500"),
        ],
    },
}

# --- Временное хранилище выбора пользователя (на сессию) ---
user_order = {}

# --- Генерация клавиатуры фасовки ---
def get_pack_keyboard(city, product):
    if city in CITY_GROUP_1:
        group = "group1"
    else:
        group = "group2"
    packs = PRODUCT_PACKS[group][product]
    keyboard = [
        [InlineKeyboardButton(text=pack[0], callback_data=f"pack_{pack[1]}")] for pack in packs
    ]
    keyboard.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_product")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_sum_from_pack(pack_code):
    # pack_code: например, 'pack_03g_3800' или 'pack_1g_7000'
    if not pack_code or '_' not in pack_code:
        return "-"
    parts = pack_code.split('_')
    if len(parts) < 3:
        return "-"
    # Последняя часть — сумма
    try:
        return parts[-1].replace('р', '').replace('₽', '')
    except Exception:
        return "-"

# --- FSM для промокода ---
class PromoStates(StatesGroup):
    waiting_for_code = State()

# Reply-меню для админа
admin_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Админ-панель")],
    ],
    resize_keyboard=True
)

class AddPromoStates(StatesGroup):
    waiting_for_code = State()
    waiting_for_percent = State()
    waiting_for_limit = State()

class AdminStates(StatesGroup):
    waiting_for_wallet = State()
    waiting_for_support = State()

class BroadcastStates(StatesGroup):
    waiting_for_text = State()
    confirm = State()

class PriceStates(StatesGroup):
    waiting_for_city = State()
    waiting_for_product = State()
    waiting_for_pack = State()
    waiting_for_price = State()

async def get_user_discount(user_id):
    user = await db.users.find_one({"user_id": user_id})
    percent = user["discount_percent"] if user and "discount_percent" in user else 0
    ref_bonus = user["ref_bonus"] if user and "ref_bonus" in user else 0
    return percent, ref_bonus

async def add_ref_bonus(ref_id, amount, from_user=None):
    await db.users.update_one({"user_id": ref_id}, {"$inc": {"ref_bonus": amount}}, upsert=True)
    await db.ref_payments.insert_one({
        "ref_id": ref_id,
        "from_user": from_user,
        "amount": amount,
        "date": datetime.utcnow()
    })

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    await db.users.update_one(
        {"user_id": message.from_user.id},
        {"$setOnInsert": {
            "user_id": message.from_user.id,
            "first_name": message.from_user.first_name,
            "username": message.from_user.username,
            "discount_percent": 0,
            "ref_bonus": 0
        }},
        upsert=True
    )
    discount_percent, ref_bonus = await get_user_discount(message.from_user.id)
    text = (
        "☀ <b>Приветствуем</b>\n"
        "\n"
        "🛒 <b>Магазин</b>\n"
        "💸 <b>Кэшбэк:</b> 0₽\n"
        f"🎟 <b>Ваша скидка:</b> {discount_percent}% и {ref_bonus}₽"
    )
    is_admin = message.from_user.id == ADMIN_ID
    await message.answer(text, reply_markup=get_main_menu(is_admin))

@dp.callback_query(F.data == "shop")
async def process_shop(callback: types.CallbackQuery):
    text = "🧾 <b>Формирование заказа</b>\n\nВыберите, пожалуйста, город, в котором желаете приобрести товар:"
    await callback.message.edit_text(text, reply_markup=city_keyboard)
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("city_"))
async def process_city(callback: types.CallbackQuery):
    city = callback.data.split("_", 1)[1]
    user_id = callback.from_user.id
    user_order.setdefault(user_id, {})["city"] = city
    text = "🧾 <b>Формирование заказа</b>\n\nВыберите, пожалуйста, товар, который желаете приобрести:"
    await callback.message.edit_text(text, reply_markup=product_keyboard)
    await callback.answer()

@dp.callback_query(F.data == "back_to_menu")
async def process_back_to_menu(callback: types.CallbackQuery):
    text = (
        "☀ <b>Приветствие</b>\n"
        "\n"
        "🛒 <b>Магазин</b>\n"
        "💸 <b>Кэшбэк:</b> 0₽\n"
        "🎟 <b>Ваша скидка:</b> 0% и 0₽"
    )
    await callback.message.edit_text(text, reply_markup=get_main_menu())
    await callback.answer()

@dp.callback_query(F.data == "back_to_city")
async def process_back_to_city(callback: types.CallbackQuery):
    text = "🧾 <b>Формирование заказа</b>\n\nВыберите, пожалуйста, город, в котором желаете приобрести товар:"
    await callback.message.edit_text(text, reply_markup=city_keyboard)
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("product_"))
async def process_product(callback: types.CallbackQuery):
    product = callback.data.split("_", 1)[1]
    if product == "МефКРИС":
        product = "Меф КРИС"
    user_id = callback.from_user.id
    # Получаем город из user_order
    city = user_order.get(user_id, {}).get("city")
    if not city:
        # Если город не выбран, возвращаем к выбору города
        text = "🧾 <b>Формирование заказа</b>\n\nВыберите, пожалуйста, город, в котором желаете приобрести товар:"
        await callback.message.edit_text(text, reply_markup=city_keyboard)
        await callback.answer()
        return
    # Сохраняем товар
    user_order.setdefault(user_id, {})["product"] = product
    text = "🧾 <b>Формирование заказа</b>\n\nВыберите, пожалуйста, фасовку товара, которую желаете приобрести:"
    await callback.message.edit_text(text, reply_markup=get_pack_keyboard(city, product))
    await callback.answer()

@dp.callback_query(F.data == "back_to_product")
async def process_back_to_product(callback: types.CallbackQuery):
    text = "🧾 <b>Формирование заказа</b>\n\nВыберите, пожалуйста, товар, который желаете приобрести:"
    await callback.message.edit_text(text, reply_markup=product_keyboard)
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("pack_"))
async def process_pack(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    # Сохраняем фасовку (можно доработать позже)
    user_order.setdefault(user_id, {})["pack"] = callback.data
    text = "🧾 <b>Формирование заказа</b>\n\nВыберите, пожалуйста, район, в котором желаете забрать товар:"
    await callback.message.edit_text(text, reply_markup=area_keyboard)
    await callback.answer()

@dp.callback_query(F.data == "back_to_pack")
async def process_back_to_pack(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    city = user_order.get(user_id, {}).get("city")
    product = user_order.get(user_id, {}).get("product")
    if not (city and product):
        # Если что-то не выбрано, возвращаем к выбору города
        text = "🧾 <b>Формирование заказа</b>\n\nВыберите, пожалуйста, город, в котором желаете приобрести товар:"
        await callback.message.edit_text(text, reply_markup=city_keyboard)
        await callback.answer()
        return
    text = "🧾 <b>Формирование заказа</b>\n\nВыберите, пожалуйста, фасовку товара, которую желаете приобрести:"
    await callback.message.edit_text(text, reply_markup=get_pack_keyboard(city, product))
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("area_"))
async def process_area(callback: types.CallbackQuery):
    user_id = callback.from_user.id

    user_order.setdefault(user_id, {})["area"] = callback.data
    text = "🧾 <b>Формирование заказа</b>\n\nВыберите, пожалуйста, тип клада, который будет Вам удобнее всего для комфортного съема клада:"
    await callback.message.edit_text(text, reply_markup=stash_type_keyboard)
    await callback.answer()

@dp.callback_query(F.data == "back_to_area")
async def process_back_to_area(callback: types.CallbackQuery):
    text = "🧾 <b>Формирование заказа</b>\n\nВыберите, пожалуйста, район, в котором желаете забрать товар:"
    await callback.message.edit_text(text, reply_markup=area_keyboard)
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("stash_"))
async def process_stash(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    stash_type = callback.data.split('_', 1)[1]
    # Приводим к читаемому виду
    stash_map = {"magnet": "Магнит", "prikop": "Прикоп", "tainik": "Тайник"}
    stash = stash_map.get(stash_type, stash_type)
    user_order.setdefault(user_id, {})["stash"] = stash
    # Получаем город и товар для отображения
    city = user_order.get(user_id, {}).get("city", "-")
    product = user_order.get(user_id, {}).get("product", "-")
    text = f"🧾 <b>Формирование заказа</b>\n\n🏙 <b>Локация:</b> {city}\n📦 <b>Товар:</b> {product}\n🔑 <b>Тип клада:</b> {stash}\n\nВыберите, пожалуйста, наиболее удобный для Вас способ оплаты:"
    await callback.message.edit_text(text, reply_markup=payment_keyboard)
    await callback.answer()

@dp.callback_query(F.data == "back_to_stash")
async def process_back_to_stash(callback: types.CallbackQuery):
    text = "🧾 <b>Формирование заказа</b>\n\nВыберите, пожалуйста, тип клада, который будет Вам удобнее всего для комфортного съема клада:"
    await callback.message.edit_text(text, reply_markup=stash_type_keyboard)
    await callback.answer()

@dp.callback_query(F.data == "pay_card")
async def process_pay_card(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    order = user_order.get(user_id, {})
    city = order.get("city", "-")
    product = order.get("product", "-")
    pack = order.get("pack", "-")
    area = order.get("area", "-")
    stash = order.get("stash", "-")
    sum_rub = await get_price(city, product, pack)
    order_id = str(uuid4())[:8]
    settings = await db.settings.find_one({"_id": "main"})
    wallet = settings.get("pay_wallet") if settings else os.getenv("PAY_WALLET", "1234 5678 9012 3456")
    support = settings.get("support_username") if settings and settings.get("support_username") else SUPPORT_USERNAME
    text = (
        f"🛒 <b>Заказ #{order_id}</b>\n\n"
        f"Оплатите, пожалуйста, заказ по данным реквизитам:\n"
        f"👛 <b>Кошелек:</b> <code>{wallet}</code>\n"
        f"Нажмите на кошелек, чтобы скопировать\n"
        f"💲 <b>Сумма для перевода в рублях:</b> <code>{sum_rub}</code>\n"
        f"Нажмите на сумму, чтобы скопировать\n\n"
        f"Тип клада: <b>{stash}</b>\n"
        f"У вас есть 20 минут на оплату заявки, далее она отменится автоматически.\n"
        f"Переводите точную сумму, в случае ошибки, заказ не будет выдан, а средства невозможно будет вернуть.\n\n"
        f"‼️ Если вы оплатили, но бот не увидел Вашу оплату, перешлите данное сообщение и чек об оплате — @" + support + "\n"
        f"ID заявки: <code>{order_id}</code>"
    )
    pay_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_payment")],
    ])
    await callback.message.edit_text(text, reply_markup=pay_keyboard)
    await callback.answer()

@dp.callback_query(F.data == "back_to_payment")
async def process_back_to_payment(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    city = user_order.get(user_id, {}).get("city", "-")
    product = user_order.get(user_id, {}).get("product", "-")
    text = f"🧾 <b>Формирование заказа</b>\n\n🏙 <b>Локация:</b> {city}\n📦 <b>Товар:</b> {product}\n\nВыберите, пожалуйста, наиболее удобный для Вас способ оплаты:"
    await callback.message.edit_text(text, reply_markup=payment_keyboard)
    await callback.answer()

@dp.callback_query(F.data == "orders")
async def process_orders(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    # TODO: получить историю заказов из MongoDB
    # Пока выводим заглушку с отображением stash
    order = user_order.get(user_id, {})
    stash = order.get("stash", "-")
    text = f"🛍 <b>История покупок</b>\n\nПоследний заказ:\nТип клада: <b>{stash}</b>\n(здесь будет подробная история)\n\nУ вас пока нет покупок."
    orders_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu")],
    ])
    await callback.message.edit_text(text, reply_markup=orders_keyboard)
    await callback.answer()

@dp.callback_query(F.data == "promo")
async def process_promo(callback: types.CallbackQuery, state: FSMContext):
    text = "🎁 Введите промокод для получения скидки:"
    promo_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu")],
    ])
    await callback.message.edit_text(text, reply_markup=promo_keyboard)
    await state.set_state(PromoStates.waiting_for_code)
    await callback.answer()

@dp.message(PromoStates.waiting_for_code)
async def promo_code_entered(message: types.Message, state: FSMContext):
    code = message.text.strip()
    promo = await db.promo_codes.find_one({"code": code.upper()})
    if not promo:
        text = "❌ Промокод не найден или недействителен."
    else:
        from datetime import datetime
        now = datetime.utcnow()
        expired = promo.get("expires_at") and now > promo["expires_at"]
        max_activations = promo.get("max_activations")
        used = promo.get("used", 0)
        if expired:
            text = "❌ Срок действия промокода истёк."
        elif max_activations and used >= max_activations:
            text = "❌ Промокод уже исчерпал лимит активаций."
        else:
            await db.promo_codes.update_one({"_id": promo["_id"]}, {"$inc": {"used": 1}})
            percent = promo.get("percent", 0)
            text = f"✅ Промокод успешно применён! Ваша скидка: {percent}%"
    await message.answer(text, reply_markup=get_main_menu())
    await state.clear()

@dp.callback_query(F.data == "admin_panel")
async def admin_panel_inline(callback: types.CallbackQuery, state: FSMContext):
    admin_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Добавить промокод", callback_data="admin_addpromo")],
        [InlineKeyboardButton(text="Реквизиты для оплаты", callback_data="admin_wallet")],
        [InlineKeyboardButton(text="Сменить поддержку", callback_data="admin_support")],
        [InlineKeyboardButton(text="Изменить прайс", callback_data="admin_price")],
        [InlineKeyboardButton(text="Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton(text="Рассылка", callback_data="admin_broadcast")],
        [InlineKeyboardButton(text="⬅️ Выйти", callback_data="back_to_menu")],
    ])
    text = "🔐 <b>Админ-панель</b>\n\nВыберите действие:"
    await callback.message.edit_text(text, reply_markup=admin_keyboard)
    await callback.answer()

@dp.callback_query(F.data == "admin_addpromo")
async def admin_addpromo(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Введите код промокода (только латиница/цифры):")
    await state.set_state(AddPromoStates.waiting_for_code)
    await callback.answer()

@dp.message(AddPromoStates.waiting_for_code)
async def addpromo_code(message: types.Message, state: FSMContext):
    code = message.text.strip().upper()
    if not code.isalnum():
        await message.answer("❗ Код должен содержать только латиницу и цифры. Введите снова:")
        return
    existing = await db.promo_codes.find_one({"code": code})
    if existing:
        await message.answer("❗ Такой промокод уже существует. Введите другой код:")
        return
    await state.update_data(code=code)
    await message.answer("Введите процент скидки (целое число):")
    await state.set_state(AddPromoStates.waiting_for_percent)

@dp.message(AddPromoStates.waiting_for_percent)
async def addpromo_percent(message: types.Message, state: FSMContext):
    try:
        percent = int(message.text.strip())
        if not (1 <= percent <= 100):
            raise ValueError
    except ValueError:
        await message.answer("❗ Введите корректный процент скидки (от 1 до 100):")
        return
    await state.update_data(percent=percent)
    await message.answer("Введите лимит активаций (целое число):")
    await state.set_state(AddPromoStates.waiting_for_limit)

@dp.message(AddPromoStates.waiting_for_limit)
async def addpromo_limit(message: types.Message, state: FSMContext):
    try:
        limit = int(message.text.strip())
        if limit < 1:
            raise ValueError
    except ValueError:
        await message.answer("❗ Введите корректный лимит активаций (целое число > 0):")
        return
    data = await state.get_data()
    promo = {
        "code": data["code"],
        "percent": data["percent"],
        "max_activations": limit,
        "used": 0
    }
    await db.promo_codes.insert_one(promo)
    await message.answer(f"✅ Промокод <b>{promo['code']}</b> на скидку {promo['percent']}% (лимит: {limit}) успешно добавлен!", parse_mode="HTML", reply_markup=get_main_menu())
    await state.clear()

@dp.callback_query(F.data == "admin_wallet")
async def admin_wallet(callback: types.CallbackQuery, state: FSMContext):
    # Получаем текущий кошелек
    settings = await db.settings.find_one({"_id": "main"})
    wallet = settings.get("pay_wallet") if settings else None
    text = "💳 <b>Текущий кошелек для оплаты:</b>\n"
    text += f"<code>{wallet}</code>\n\n" if wallet else "<i>Не задан</i>\n\n"
    text += "Введите новый кошелек для оплаты:"
    await callback.message.edit_text(text, reply_markup=None)
    await callback.message.answer(text)
    await state.set_state(AdminStates.waiting_for_wallet)
    await callback.answer()

@dp.message(AdminStates.waiting_for_wallet)
async def admin_wallet_set(message: types.Message, state: FSMContext):
    wallet = message.text.strip()
    await db.settings.update_one({"_id": "main"}, {"$set": {"pay_wallet": wallet}}, upsert=True)
    await message.answer(f"✅ Кошелек для оплаты обновлён: <code>{wallet}</code>", parse_mode="HTML", reply_markup=get_main_menu(message.from_user.id == ADMIN_ID))
    await state.clear()

@dp.callback_query(F.data == "admin_stats")
async def admin_stats(callback: types.CallbackQuery):
    users_count = await db.users.count_documents({})
    orders_count = await db.orders.count_documents({}) if "orders" in await db.list_collection_names() else 0
    turnover = 0
    if "orders" in await db.list_collection_names():
        async for order in db.orders.find({}):
            turnover += int(order.get("sum", 0))
    promo_count = await db.promo_codes.count_documents({"used": {"$lt": "$max_activations"}}) if "promo_codes" in await db.list_collection_names() else 0
    text = (
        f"📊 <b>Статистика бота</b>\n\n"
        f"👤 Пользователей: <b>{users_count}</b>\n"
        f"🛒 Заказов: <b>{orders_count}</b>\n"
        f"💰 Оборот: <b>{turnover}₽</b>\n"
        f"🎁 Активных промокодов: <b>{promo_count}</b>"
    )
    stats_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_panel")],
    ])
    await callback.message.edit_text(text, reply_markup=stats_keyboard)
    await callback.answer()

@dp.callback_query(F.data == "admin_broadcast")
async def admin_broadcast(callback: types.CallbackQuery, state: FSMContext):
    text = (
        "Введите текст рассылки (HTML поддерживается):\n\n"
        "&lt;b&gt;Жирный&lt;/b&gt; &lt;i&gt;Курсив&lt;/i&gt; &lt;u&gt;Подчёркнутый&lt;/u&gt; &lt;a href='https://example.com'&gt;Ссылка&lt;/a&gt;\n"
        "\nНиже пример для копирования (без экранирования):"
    )
    example = "<b>Жирный</b> <i>Курсив</i> <u>Подчёркнутый</u> <a href='https://example.com'>Ссылка</a>"
    await callback.message.edit_text(text, reply_markup=None, parse_mode="HTML")
    await callback.message.answer(f"<code>{example}</code>", parse_mode="HTML")
    await state.set_state(BroadcastStates.waiting_for_text)
    await callback.answer()

@dp.message(BroadcastStates.waiting_for_text)
async def admin_broadcast_preview(message: types.Message, state: FSMContext):
    data = {"text": message.text, "photo": None}
    if message.photo:
        data["photo"] = message.photo[-1].file_id
        data["caption"] = message.caption or ""
    await state.update_data(**data)
    # Клавиатура подтверждения
    confirm_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Отправить", callback_data="broadcast_send")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="broadcast_cancel")],
    ])
    if data["photo"]:
        await message.answer_photo(data["photo"], caption=data["caption"], parse_mode="HTML", reply_markup=confirm_keyboard)
    else:
        await message.answer(data["text"], parse_mode="HTML", reply_markup=confirm_keyboard)
    await state.set_state(BroadcastStates.confirm)

@dp.callback_query(F.data == "broadcast_send")
async def admin_broadcast_send(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    users = db.users.find({})
    sent = 0
    failed = 0
    if data.get("photo"):
        for user in await users.to_list(length=100000):
            try:
                await bot.send_photo(user["user_id"], data["photo"], caption=data.get("caption", ""), parse_mode="HTML")
                sent += 1
            except Exception:
                failed += 1
        # После предпросмотра фото нельзя edit_text, отправляем новое сообщение
        await callback.message.answer(f"✅ <b>Рассылка завершена!</b>\nУспешно: <b>{sent}</b>\nОшибок: <b>{failed}</b>", parse_mode="HTML", reply_markup=get_main_menu(callback.from_user.id == ADMIN_ID))
    else:
        for user in await users.to_list(length=100000):
            try:
                await bot.send_message(user["user_id"], data["text"], parse_mode="HTML")
                sent += 1
            except Exception:
                failed += 1
        await callback.message.edit_text(f"✅ <b>Рассылка завершена!</b>\nУспешно: <b>{sent}</b>\nОшибок: <b>{failed}</b>", parse_mode="HTML", reply_markup=get_main_menu(callback.from_user.id == ADMIN_ID))
    await state.clear()
    await callback.answer()

@dp.callback_query(F.data == "broadcast_cancel")
async def admin_broadcast_cancel(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text("❌ <b>Рассылка отменена.</b>", parse_mode="HTML", reply_markup=get_main_menu(callback.from_user.id == ADMIN_ID))
    await state.clear()
    await callback.answer()

@dp.callback_query(F.data == "admin_support")
async def admin_support(callback: types.CallbackQuery, state: FSMContext):
    settings = await db.settings.find_one({"_id": "main"})
    support = settings.get("support_username") if settings and settings.get("support_username") else SUPPORT_USERNAME
    text = f"💬 <b>Текущий username поддержки:</b> <code>{support}</code>\n\nВведите новый username (без @):"
    await callback.message.edit_text(text, reply_markup=None)
    await state.set_state(AdminStates.waiting_for_support)
    await callback.answer()

@dp.message(AdminStates.waiting_for_support)
async def admin_support_set(message: types.Message, state: FSMContext):
    username = message.text.strip().replace('@', '')
    await db.settings.update_one({"_id": "main"}, {"$set": {"support_username": username}}, upsert=True)
    await message.answer(f"✅ Username поддержки обновлён: <code>{username}</code>", parse_mode="HTML", reply_markup=get_main_menu(message.from_user.id == ADMIN_ID))
    await state.clear()

@dp.callback_query(F.data == "admin_price")
async def admin_price(callback: types.CallbackQuery, state: FSMContext):
    city_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=city, callback_data=f"price_city_{city}")] for city in CITY_GROUP_1 + CITY_GROUP_2
    ] + [[InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_panel")]])
    await callback.message.edit_text("Выберите город для изменения прайса:", reply_markup=city_keyboard)
    await state.set_state(PriceStates.waiting_for_city)
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("price_city_"))
async def admin_price_city(callback: types.CallbackQuery, state: FSMContext):
    city = callback.data.split("_", 2)[2]
    await state.update_data(city=city)
    product_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=prod, callback_data=f"price_product_{prod}")] for prod in ["Скорость", "Бошки", "Меф КРИС"]
    ] + [[InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_price")]])
    await callback.message.edit_text(f"Город: <b>{city}</b>\n\nВыберите товар:", parse_mode="HTML", reply_markup=product_keyboard)
    await state.set_state(PriceStates.waiting_for_product)
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("price_product_"))
async def admin_price_product(callback: types.CallbackQuery, state: FSMContext):
    product = callback.data.split("_", 2)[2]
    data = await state.get_data()
    city = data["city"]
    # Определяем фасовки по городу и товару
    if city in CITY_GROUP_1:
        group = "group1"
    else:
        group = "group2"
    packs = [p[0] for p in PRODUCT_PACKS[group][product]]
    pack_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=pack, callback_data=f"price_pack_{pack}")] for pack in packs
    ] + [[InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_price")]])
    await state.update_data(product=product)
    await callback.message.edit_text(f"Город: <b>{city}</b>\nТовар: <b>{product}</b>\n\nВыберите фасовку:", parse_mode="HTML", reply_markup=pack_keyboard)
    await state.set_state(PriceStates.waiting_for_pack)
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("price_pack_"))
async def admin_price_pack(callback: types.CallbackQuery, state: FSMContext):
    pack = callback.data.split("_", 2)[2]
    data = await state.get_data()
    await state.update_data(pack=pack)
    await callback.message.edit_text(f"Город: <b>{data['city']}</b>\nТовар: <b>{data['product']}</b>\nФасовка: <b>{pack}</b>\n\nВведите новую цену (только число):", parse_mode="HTML")
    await state.set_state(PriceStates.waiting_for_price)
    await callback.answer()

@dp.message(PriceStates.waiting_for_price)
async def admin_price_set(message: types.Message, state: FSMContext):
    try:
        price = int(message.text.strip())
        if price < 1:
            raise ValueError
    except ValueError:
        await message.answer("❗ Введите корректную цену (целое число > 0):")
        return
    data = await state.get_data()
    await db.prices.update_one(
        {"city": data["city"], "product": data["product"], "pack": data["pack"]},
        {"$set": {"price": price}}, upsert=True
    )
    await message.answer(f"✅ Цена для <b>{data['city']}</b> / <b>{data['product']}</b> / <b>{data['pack']}</b> обновлена: <b>{price}₽</b>", parse_mode="HTML", reply_markup=get_main_menu(message.from_user.id == ADMIN_ID))
    await state.clear()

# Использую цену из базы при формировании заказа
async def get_price(city, product, pack):
    doc = await db.prices.find_one({"city": city, "product": product, "pack": pack})
    if doc and "price" in doc:
        return doc["price"]
    # Фолбэк: ищем цену в PRODUCT_PACKS
    if city in CITY_GROUP_1:
        group = "group1"
    else:
        group = "group2"
    for p in PRODUCT_PACKS[group][product]:
        if p[0] == pack:
            return int(p[0].split('-')[-1].replace('₽', '').replace(' ', ''))
    return 0

# --- начисление реферального бонуса при покупке ---
async def process_order_payment(user_id, order_sum):
    user = await db.users.find_one({"user_id": user_id})
    ref_id = user.get("ref_id") if user else None
    if ref_id:
        bonus = int(order_sum * 0.05)
        from_user = user_id
        await add_ref_bonus(ref_id, bonus, from_user=from_user)

@dp.callback_query(F.data == "referral")
async def process_referral(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    bot_username = (await bot.me()).username
    ref_link = f"https://t.me/{bot_username}?start={user_id}"
    # История начислений
    payments = db.ref_payments.find({"ref_id": user_id})
    history = []
    async for p in payments:
        from_user = p.get("from_user", "-")
        amount = p.get("amount", 0)
        date = p.get("date")
        date_str = date.strftime('%d.%m.%Y %H:%M') if date else "-"
        history.append(f"{date_str}: +{amount}₽ от {from_user}")
    if history:
        history_text = "\n".join(history)
    else:
        history_text = "Нет начислений."
    referral_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu")],
    ])
    text = (
        "👥 <b>Ваша реферальная ссылка:</b>\n"
        f"<code>{ref_link}</code>\n\n"
        "Пригласите друга и получите 5% от его покупок!\n\n"
        "<b>История начислений:</b>\n"
        f"{history_text}"
    )
    await callback.message.edit_text(text, reply_markup=referral_keyboard)
    await callback.answer()

@dp.message(CommandStart(deep_link=True))
async def cmd_start_ref(message: types.Message, command: CommandStart):
    await db.users.update_one(
        {"user_id": message.from_user.id},
        {"$setOnInsert": {
            "user_id": message.from_user.id,
            "first_name": message.from_user.first_name,
            "username": message.from_user.username,
            "discount_percent": 0,
            "ref_bonus": 0
        }},
        upsert=True
    )
    ref_id = command.args
    user_id = message.from_user.id
    if ref_id and ref_id != str(user_id):
        user = await db.users.find_one({"user_id": user_id})
        if not user or "ref_id" not in user:
            await db.users.update_one({"user_id": user_id}, {"$set": {"ref_id": int(ref_id)}}, upsert=True)
    await cmd_start(message)

@dp.callback_query(F.data == "support")
async def process_support(callback: types.CallbackQuery):
    settings = await db.settings.find_one({"_id": "main"})
    support_username = settings.get("support_username") if settings and settings.get("support_username") else SUPPORT_USERNAME
    support_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Написать в поддержку", url=f"https://t.me/{support_username}")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu")],
    ])
    text = "💬 <b>Поддержка</b>\n\nЕсли у вас возникли вопросы или проблемы, напишите нам:"
    await callback.message.edit_text(text, reply_markup=support_keyboard)
    await callback.answer()

if __name__ == "__main__":
    asyncio.run(dp.start_polling(bot)) 
