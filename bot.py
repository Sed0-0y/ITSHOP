import logging
from aiogram import Bot, Dispatcher, types, Router
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.filters import Command
from aiohttp import web
import sqlite3
import asyncio

# Настройки бота
API_TOKEN = "8190038878:AAF_gh-NqR3fCFB2hEiFFhuKPtvK_cH_aEg"  # Замените на токен вашего бота
PROVIDER_TOKEN = "2051251535:TEST:OTk5MDA4ODgxLTAwNQ"  # Токен платёжного провайдера
ADMIN_ID = 6286389072  # Замените на Telegram ID администратора
bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
router = Router()

# Логирование
logging.basicConfig(level=logging.INFO)

# Подключение к базе данных
conn = sqlite3.connect("orders.db")
cursor = conn.cursor()

# Создаём таблицу orders
cursor.execute("""
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id INTEGER,
    name TEXT,
    address TEXT,
    phone TEXT,
    email TEXT,
    order_details TEXT,
    total_weight REAL,
    total_cost REAL,
    is_paid INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")
conn.commit()

# Состояния для формы заказа
class OrderForm(StatesGroup):
    name = State()
    address = State()
    phone = State()
    email = State()
    entering_product_name = State()
    entering_quantity = State()
    entering_weight = State()
    entering_price = State()
    confirming_list = State()

# Состояния для оплаты
class PaymentForm(StatesGroup):
    total_amount = State()  # Состояние для ввода стоимости доставки

# Хранилище языков пользователей
user_languages = {}

# Словарь переводов
translations = {
    "ru": {
        "choose_language": "Выберите язык / Choose your language:",
        "language_selected": "Язык выбран!",
        "download_catalog": "Спасибо! Теперь вы можете скачать каталог товаров.",
        "catalog_not_found": "Каталог товаров не найден. Пожалуйста, загрузите файл catalog.pdf в папку с ботом.",
        "fill_order_form": "После изучения каталога нажмите на кнопку ниже, чтобы начать оформление заказа.",
        "enter_name": "Введите ваше имя и фамилию:",
        "enter_address": "Введите ваш адрес доставки:",
        "enter_phone": "Введите ваш номер телефона:",
        "enter_email": "Введите ваш email:",
        "enter_product_name": "Введите название товара:",
        "enter_quantity": "Введите количество товара:",
        "enter_weight": "Введите вес товара (в кг):",
        "enter_price": "Введите стоимость товара (в €):",
        "order_summary": "Ваш заказ:\nИмя: {name}\nАдрес: {address}\nТелефон: {phone}\nEmail: {email}\n\nДетали заказа:\n{order_details}\n\nОбщий вес: {total_weight} кг\nОбщая стоимость: {total_cost} €",
        "order_confirmed": "Ваш заказ подтверждён! Мы свяжемся с вами для уточнения деталей.",
        "order_cancelled": "Ваш заказ был отменён.",
        "unknown_message": "Извините, я не понимаю это сообщение. Попробуйте использовать команды или следуйте инструкциям.",
        "admin_notification": "Новый заказ от {name}:\nАдрес: {address}\nТелефон: {phone}\nEmail: {email}\nДетали заказа:\n{order_details}\nОбщий вес: {total_weight} кг\nОбщая стоимость: {total_cost} €\n\nTelegram ID клиента: {telegram_id}\n",
        "button_continue_order": "Продолжить заказ",
        "button_cancel_last_item": "Отменить последний товар",
        "button_finish_order": "Завершить список",
        "button_confirm": "Подтвердить",
        "button_edit": "Изменить",
        "button_cancel": "Отменить",
        "button_new_order": "Начать заказ заново",
        "button_start_order": "Начать заказ",
        "new_order_prompt": "Если вы хотите сделать новый заказ, нажмите на кнопку ниже:",
        "start_order_prompt": "Если хотите начать заказ заново, нажмите на кнопку снизу.",
        "pay_order_prompt": "Оплатить заказ",
        "total_cost_of_goods": "Общая стоимость товаров",
        "delivery_cost": "Стоимость доставки",
        "service_cost": "Стоимость услуги (10%)",
        "total_amount": "Итоговая сумма"
    }
    # Добавьте переводы для других языков (en, it, de, fr, es) аналогично
}

# Функция для получения перевода
def get_translation(user_id, key, **kwargs):
    lang = user_languages.get(user_id, "ru")  # По умолчанию русский
    if lang not in translations:
        lang = "ru"
    if key not in translations[lang]:
        return f"Ошибка: перевод для ключа '{key}' отсутствует."
    return translations[lang][key].format(**kwargs)

# Команда /start
@router.message(Command("start"))
async def start_command(message: types.Message):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Русский", callback_data="lang_ru"),
                InlineKeyboardButton(text="English", callback_data="lang_en"),
                InlineKeyboardButton(text="Italiano", callback_data="lang_it")
            ],
            [
                InlineKeyboardButton(text="Deutsch", callback_data="lang_de"),
                InlineKeyboardButton(text="Français", callback_data="lang_fr"),
                InlineKeyboardButton(text="Español", callback_data="lang_es")
            ]
        ]
    )
    await message.answer(get_translation(message.from_user.id, "choose_language"), reply_markup=keyboard)

# Обработка выбора языка
@router.callback_query(lambda c: c.data.startswith("lang_"))
async def set_language(callback_query: types.CallbackQuery):
    lang_code = callback_query.data.split("_")[1]
    user_languages[callback_query.from_user.id] = lang_code  # Сохраняем язык пользователя
    await callback_query.answer(get_translation(callback_query.from_user.id, "language_selected"))
    await callback_query.message.answer(get_translation(callback_query.from_user.id, "download_catalog"))

    try:
        document = FSInputFile("catalog.pdf")
        await bot.send_document(callback_query.from_user.id, document)
    except FileNotFoundError:
        await callback_query.message.answer(get_translation(callback_query.from_user.id, "catalog_not_found"))
        return

    # Сообщение с кнопкой "Начать заказ"
    start_order_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=get_translation(callback_query.from_user.id, "button_start_order"), callback_data="start_order")
            ]
        ]
    )
    await callback_query.message.answer(get_translation(callback_query.from_user.id, "fill_order_form"), reply_markup=start_order_keyboard)

# Обработка кнопки "Начать заказ"
@router.callback_query(lambda c: c.data == "start_order")
async def handle_start_order(callback_query: types.CallbackQuery, state: FSMContext):
    # Устанавливаем состояние для ввода имени
    await state.set_state(OrderForm.name)
    await callback_query.message.answer(get_translation(callback_query.from_user.id, "enter_name"))

# Сбор данных для заказа
@router.message(OrderForm.name)
async def process_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)  # Сохраняем имя
    await state.set_state(OrderForm.address)
    await message.answer(get_translation(message.from_user.id, "enter_address"))

@router.message(OrderForm.address)
async def process_address(message: types.Message, state: FSMContext):
    await state.update_data(address=message.text)  # Сохраняем адрес
    await state.set_state(OrderForm.phone)
    await message.answer(get_translation(message.from_user.id, "enter_phone"))

@router.message(OrderForm.phone)
async def process_phone(message: types.Message, state: FSMContext):
    await state.update_data(phone=message.text)  # Сохраняем телефон
    await state.set_state(OrderForm.email)
    await message.answer(get_translation(message.from_user.id, "enter_email"))

@router.message(OrderForm.email)
async def process_email(message: types.Message, state: FSMContext):
    await state.update_data(email=message.text)  # Сохраняем email
    await state.set_state(OrderForm.entering_product_name)
    await state.update_data(order_list=[])  # Инициализация пустого списка товаров
    await message.answer(get_translation(message.from_user.id, "enter_product_name"))

@router.message(OrderForm.entering_product_name)
async def enter_product_name(message: types.Message, state: FSMContext):
    await state.update_data(product_name=message.text)
    await message.answer(get_translation(message.from_user.id, "enter_quantity"))
    await state.set_state(OrderForm.entering_quantity)

@router.message(OrderForm.entering_quantity)
async def enter_quantity(message: types.Message, state: FSMContext):
    try:
        quantity = int(message.text)
        if quantity <= 0:
            raise ValueError
        await state.update_data(quantity=quantity)
        await message.answer(get_translation(message.from_user.id, "enter_weight"))
        await state.set_state(OrderForm.entering_weight)
    except ValueError:
        await message.answer(get_translation(message.from_user.id, "enter_quantity"))

@router.message(OrderForm.entering_weight)
async def enter_weight(message: types.Message, state: FSMContext):
    try:
        weight = float(message.text)
        if weight <= 0:
            raise ValueError
        await state.update_data(weight=weight)
        await message.answer(get_translation(message.from_user.id, "enter_price"))
        await state.set_state(OrderForm.entering_price)
    except ValueError:
        await message.answer(get_translation(message.from_user.id, "enter_weight"))

@router.message(OrderForm.entering_price)
async def enter_price(message: types.Message, state: FSMContext):
    try:
        price = float(message.text)
        if price <= 0:
            raise ValueError
        data = await state.get_data()
        product_name = data["product_name"]
        quantity = data["quantity"]
        weight = data["weight"]

        # Добавляем товар в список
        order_list = data.get("order_list", [])
        order_list.append({
            "name": product_name,
            "quantity": quantity,
            "weight": weight,
            "price": price
        })
        await state.update_data(order_list=order_list)

        # Формируем список товаров
        order_summary = "\n".join(
            [f"{i+1}. {item['name']} - {item['quantity']} шт., {item['weight']} кг, {item['price']} €"
             for i, item in enumerate(order_list)]
        )

        # Формируем перевод строки с данными
        translation = get_translation(
            message.from_user.id,
            "order_summary",
            name=data.get("name", "N/A"),
            address=data.get("address", "N/A"),
            phone=data.get("phone", "N/A"),
            email=data.get("email", "N/A"),
            order_details=order_summary,
            total_weight=sum(item["weight"] for item in order_list),
            total_cost=sum(item["price"] for item in order_list)
        )

        # Клавиатура для управления заказом
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=get_translation(message.from_user.id, "button_continue_order"),
                    callback_data="continue_order"
                )
            ],
            [
                InlineKeyboardButton(
                    text=get_translation(message.from_user.id, "button_cancel_last_item"),
                    callback_data="cancel_last_item"
                )
            ],
            [
                InlineKeyboardButton(
                    text=get_translation(message.from_user.id, "button_finish_order"),
                    callback_data="finish_order"
                )
            ]
        ])

        # Отправляем сообщение с переводом и клавиатурой
        await message.answer(translation, reply_markup=keyboard)
        await state.set_state(OrderForm.confirming_list)
    except ValueError:
        await message.answer(get_translation(message.from_user.id, "enter_price"))

@router.callback_query(lambda c: c.data == "continue_order")
async def continue_order(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.message.answer(get_translation(callback_query.from_user.id, "enter_product_name"))
    await state.set_state(OrderForm.entering_product_name)

@router.callback_query(lambda c: c.data == "cancel_last_item")
async def cancel_last_item(callback_query: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    order_list = data.get("order_list", [])
    if order_list:
        # Удаляем последний товар
        order_list.pop()
        await state.update_data(order_list=order_list)

        # Формируем обновлённый список товаров
        if order_list:
            order_summary = "\n".join(
                [f"{i+1}. {item['name']} - {item['quantity']} шт., {item['weight']} кг, {item['price']} €"
                 for i, item in enumerate(order_list)]
            )
            # Формируем перевод строки с данными
            translation = get_translation(
                callback_query.from_user.id,
                "order_summary",
                name=data.get("name", "N/A"),
                address=data.get("address", "N/A"),
                phone=data.get("phone", "N/A"),
                email=data.get("email", "N/A"),
                order_details=order_summary,
                total_weight=sum(item["weight"] for item in order_list),
                total_cost=sum(item["price"] for item in order_list)
            )

            # Клавиатура для управления заказом
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=get_translation(callback_query.from_user.id, "button_continue_order"),
                        callback_data="continue_order"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text=get_translation(callback_query.from_user.id, "button_cancel_last_item"),
                        callback_data="cancel_last_item"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text=get_translation(callback_query.from_user.id, "button_finish_order"),
                        callback_data="finish_order"
                    )
                ]
            ])

            # Отправляем обновлённый список товаров
            await callback_query.message.edit_text(translation, reply_markup=keyboard)
        else:
            # Если список пуст, уведомляем клиента и предлагаем начать заказ заново
            new_order_keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text=get_translation(callback_query.from_user.id, "button_new_order"),
                            callback_data="start_order"
                        )
                    ]
                ]
            )
            await callback_query.message.edit_text(get_translation(callback_query.from_user.id, "order_cancelled"),
                                                   reply_markup=new_order_keyboard)
    else:
        await callback_query.message.answer(get_translation(callback_query.from_user.id, "order_cancelled"))

@router.callback_query(lambda c: c.data == "finish_order")
async def finish_order(callback_query: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    order_list = data.get("order_list", [])
    if not order_list:
        # Если список пуст, уведомляем клиента и предлагаем начать заказ заново
        new_order_keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=get_translation(callback_query.from_user.id, "button_new_order"),
                        callback_data="start_order"
                    )
                ]
            ]
        )
        await callback_query.message.answer(get_translation(callback_query.from_user.id, "order_cancelled"),
                                            reply_markup=new_order_keyboard)
        return

    # Формируем итоговый список
    total_weight = sum(item["weight"] for item in order_list)
    total_price = sum(item["price"] for item in order_list)
    order_summary = "\n".join(
        [f"{i+1}. {item['name']} - {item['quantity']} шт., {item['weight']} кг, {item['price']} €"
         for i, item in enumerate(order_list)]
    )

    # Формируем перевод строки с данными
    translation = get_translation(
        callback_query.from_user.id,
        "order_summary",
        name=data.get("name", "N/A"),
        address=data.get("address", "N/A"),
        phone=data.get("phone", "N/A"),
        email=data.get("email", "N/A"),
        order_details=order_summary,
        total_weight=total_weight,
        total_cost=total_price
    )

    # Клавиатура для подтверждения, редактирования и отмены заказа
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text=get_translation(callback_query.from_user.id, "button_confirm"),
                callback_data="confirm_order"
            )
        ],
        [
            InlineKeyboardButton(
                text=get_translation(callback_query.from_user.id, "button_edit"),
                callback_data="edit_order"
            )
        ],
        [
            InlineKeyboardButton(
                text=get_translation(callback_query.from_user.id, "button_cancel"),
                callback_data="cancel_order"
            )
        ]
    ])

    # Отправляем итоговый список с кнопками
    await callback_query.message.edit_text(translation, reply_markup=keyboard)

@router.callback_query(lambda c: c.data == "edit_order")
async def edit_order(callback_query: types.CallbackQuery, state: FSMContext):
    # Возвращаем клиента к добавлению товаров
    await callback_query.message.answer(get_translation(callback_query.from_user.id, "enter_product_name"))
    await state.set_state(OrderForm.entering_product_name)

@router.callback_query(lambda c: c.data == "confirm_order")
async def confirm_order(callback_query: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    user_id = callback_query.from_user.id

    # Проверяем, есть ли детали заказа
    if not data.get("order_list"):
        await callback_query.message.answer(get_translation(user_id, "order_cancelled"))
        await state.clear()
        return

    # Сохраняем заказ в базу данных
    cursor.execute("""
    INSERT INTO orders (telegram_id, name, address, phone, email, order_details, total_weight, total_cost, is_paid)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (user_id, data['name'], data['address'], data['phone'], data['email'], str(data['order_list']),
          sum(item["weight"] for item in data["order_list"]),
          sum(item["price"] for item in data["order_list"]), 0))
    conn.commit()

    # Уведомляем клиента
    await callback_query.message.answer(get_translation(user_id, "order_confirmed"))

    # Формируем сообщение для администратора
    admin_message = get_translation(user_id, "admin_notification",
                                     name=data['name'],
                                     address=data['address'],
                                     phone=data['phone'],
                                     email=data['email'],
                                     order_details="\n".join(
                                         [f"{item['name']} - {item['quantity']} шт., {item['weight']} кг, {item['price']} €"
                                          for item in data["order_list"]]),
                                     total_weight=sum(item["weight"] for item in data["order_list"]),
                                     total_cost=sum(item["price"] for item in data["order_list"]),
                                     telegram_id=user_id)

    # Кнопки для администратора
    admin_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="Ответить",
                url=f"tg://user?id={user_id}"
            )
        ],
        [
            InlineKeyboardButton(
                text="Запросить оплату",
                callback_data=f"request_payment_{user_id}"
            )
        ]
    ])

    # Отправляем сообщение администратору
    await bot.send_message(chat_id=ADMIN_ID, text=admin_message, reply_markup=admin_keyboard)

    # Очищаем состояние
    await state.clear()

    # Предлагаем клиенту начать новый заказ
    new_order_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=get_translation(callback_query.from_user.id, "button_new_order"),
                    callback_data="start_order"
                )
            ]
        ]
    )
    await callback_query.message.answer(get_translation(callback_query.from_user.id, "new_order_prompt"),
                                        reply_markup=new_order_keyboard)

@router.callback_query(lambda c: c.data.startswith("request_payment_"))
async def request_payment(callback_query: types.CallbackQuery, state: FSMContext):
    # Извлекаем ID клиента из callback_data
    client_id = int(callback_query.data.split("_")[-1])

    # Сохраняем ID клиента в состоянии
    await state.update_data(client_id=client_id)

    # Запрашиваем у администратора стоимость доставки
    await callback_query.message.answer("Введите стоимость доставки (в €):")
    await state.set_state(PaymentForm.total_amount)

@router.message(PaymentForm.total_amount)
async def process_delivery_cost(message: types.Message, state: FSMContext):
    try:
        # Получаем стоимость доставки
        delivery_cost = float(message.text)
        if delivery_cost <= 0:
            raise ValueError

        # Получаем ID клиента из состояния
        data = await state.get_data()
        client_id = data.get("client_id")

        # Рассчитываем итоговую сумму
        total_cost = delivery_cost + (delivery_cost * 0.1)  # Добавляем 10% за услугу

        # Отправляем клиенту запрос на оплату
        await bot.send_message(
            client_id,
            f"Ваш заказ готов к оплате. Итоговая сумма: {total_cost:.2f} €.\n"
            f"Нажмите на кнопку ниже, чтобы оплатить.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text=get_translation(client_id, "pay_order_prompt"),
                            callback_data="pay_order"
                        )
                    ]
                ]
            )
        )

        # Уведомляем администратора, что запрос на оплату отправлен
        await message.answer("Запрос на оплату отправлен клиенту.")
        await state.clear()
    except ValueError:
        # Если введено некорректное значение, просим администратора повторить ввод
        await message.answer("Введите корректную стоимость доставки (в €).")

# HTTP-сервер для поддержки активности
async def handle(request):
    return web.Response(text="Bot is running!")

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", handle)  # Обработка GET-запросов на корневой URL
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8080)  # Сервер будет слушать порт 8080
    await site.start()
    print("Web server is running on http://0.0.0.0:8080")

# Запуск бота и HTTP-сервера
async def main():
    dp.include_router(router)
    await bot.delete_webhook(drop_pending_updates=True)  # Удаляем старый webhook
    await asyncio.gather(
        start_web_server(),  # Запуск HTTP-сервера
        dp.start_polling(bot)  # Запуск бота
    )

if __name__ == "__main__":
    asyncio.run(main())
