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
API_TOKEN = "8190038878:AAF_gh-NqR3fCFB2hEiFFhuKPtvK_cH_aEg"  # Токен бота
PROVIDER_TOKEN = "2051251535:TEST:OTk5MDA4ODgxLTAwNQ"  # Токен платёжного провайдера
ADMIN_ID = 6286389072  # Telegram ID администратора
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
    },
    "en": {
        "choose_language": "Choose your language:",
        "language_selected": "Language selected!",
        "download_catalog": "Thank you! You can now download the product catalog.",
        "catalog_not_found": "Product catalog not found. Please upload the catalog.pdf file to the bot's folder.",
        "fill_order_form": "After reviewing the catalog, click the button below to start placing your order.",
        "enter_name": "Enter your full name:",
        "enter_address": "Enter your delivery address:",
        "enter_phone": "Enter your phone number:",
        "enter_email": "Enter your email:",
        "enter_product_name": "Enter the product name:",
        "enter_quantity": "Enter the quantity of the product:",
        "enter_weight": "Enter the weight of the product (in kg):",
        "enter_price": "Enter the price of the product (in €):",
        "order_summary": "Your order:\nName: {name}\nAddress: {address}\nPhone: {phone}\nEmail: {email}\n\nOrder details:\n{order_details}\n\nTotal weight: {total_weight} kg\nTotal cost: {total_cost} €",
        "order_confirmed": "Your order has been confirmed! We will contact you to clarify the details.",
        "order_cancelled": "Your order has been cancelled.",
        "unknown_message": "Sorry, I don't understand this message. Please try using commands or follow the instructions.",
        "admin_notification": "New order from {name}:\nAddress: {address}\nPhone: {phone}\nEmail: {email}\nOrder details:\n{order_details}\nTotal weight: {total_weight} kg\nTotal cost: {total_cost} €\n\nClient's Telegram ID: {telegram_id}\n",
        "button_continue_order": "Continue order",
        "button_cancel_last_item": "Cancel last item",
        "button_finish_order": "Finish list",
        "button_confirm": "Confirm",
        "button_edit": "Edit",
        "button_cancel": "Cancel",
        "button_new_order": "Start a new order",
        "button_start_order": "Start order",
        "new_order_prompt": "If you want to place a new order, click the button below:",
        "start_order_prompt": "If you want to start a new order, click the button below.",
        "pay_order_prompt": "Pay for the order",
        "total_cost_of_goods": "Total cost of goods",
        "delivery_cost": "Delivery cost",
        "service_cost": "Service fee (10%)",
        "total_amount": "Total amount"
    },
    "it": {
        "choose_language": "Scegli la tua lingua:",
        "language_selected": "Lingua selezionata!",
        "download_catalog": "Grazie! Ora puoi scaricare il catalogo dei prodotti.",
        "catalog_not_found": "Catalogo dei prodotti non trovato. Carica il file catalog.pdf nella cartella del bot.",
        "fill_order_form": "Dopo aver esaminato il catalogo, fai clic sul pulsante qui sotto per iniziare a effettuare l'ordine.",
        "enter_name": "Inserisci il tuo nome completo:",
        "enter_address": "Inserisci il tuo indirizzo di consegna:",
        "enter_phone": "Inserisci il tuo numero di telefono:",
        "enter_email": "Inserisci la tua email:",
        "enter_product_name": "Inserisci il nome del prodotto:",
        "enter_quantity": "Inserisci la quantità del prodotto:",
        "enter_weight": "Inserisci il peso del prodotto (in kg):",
        "enter_price": "Inserisci il prezzo del prodotto (in €):",
        "order_summary": "Il tuo ordine:\nNome: {name}\nIndirizzo: {address}\nTelefono: {phone}\nEmail: {email}\n\nDettagli dell'ordine:\n{order_details}\n\nPeso totale: {total_weight} kg\nCosto totale: {total_cost} €",
        "order_confirmed": "Il tuo ordine è stato confermato! Ti contatteremo per chiarire i dettagli.",
        "order_cancelled": "Il tuo ordine è stato annullato.",
        "unknown_message": "Mi dispiace, non capisco questo messaggio. Prova a usare i comandi o segui le istruzioni.",
        "admin_notification": "Nuovo ordine da {name}:\nIndirizzo: {address}\nTelefono: {phone}\nEmail: {email}\nDettagli dell'ordine:\n{order_details}\nPeso totale: {total_weight} kg\nCosto totale: {total_cost} €\n\nID Telegram del cliente: {telegram_id}\n",
        "button_continue_order": "Continua ordine",
        "button_cancel_last_item": "Annulla ultimo articolo",
        "button_finish_order": "Termina elenco",
        "button_confirm": "Conferma",
        "button_edit": "Modifica",
        "button_cancel": "Annulla",
        "button_new_order": "Inizia un nuovo ordine",
        "button_start_order": "Inizia ordine",
        "new_order_prompt": "Se vuoi effettuare un nuovo ordine, fai clic sul pulsante qui sotto:",
        "start_order_prompt": "Se vuoi iniziare un nuovo ordine, fai clic sul pulsante qui sotto.",
        "pay_order_prompt": "Paga l'ordine",
        "total_cost_of_goods": "Costo totale dei prodotti",
        "delivery_cost": "Costo di consegna",
        "service_cost": "Costo del servizio (10%)",
        "total_amount": "Importo totale"
    },
    "de": {
        "choose_language": "Wählen Sie Ihre Sprache:",
        "language_selected": "Sprache ausgewählt!",
        "download_catalog": "Vielen Dank! Sie können jetzt den Produktkatalog herunterladen.",
        "catalog_not_found": "Produktkatalog nicht gefunden. Bitte laden Sie die Datei catalog.pdf in den Bot-Ordner hoch.",
        "fill_order_form": "Nachdem Sie den Katalog überprüft haben, klicken Sie auf die Schaltfläche unten, um mit der Bestellung zu beginnen.",
        "enter_name": "Geben Sie Ihren vollständigen Namen ein:",
        "enter_address": "Geben Sie Ihre Lieferadresse ein:",
        "enter_phone": "Geben Sie Ihre Telefonnummer ein:",
        "enter_email": "Geben Sie Ihre E-Mail-Adresse ein:",
        "enter_product_name": "Geben Sie den Produktnamen ein:",
        "enter_quantity": "Geben Sie die Menge des Produkts ein:",
        "enter_weight": "Geben Sie das Gewicht des Produkts (in kg) ein:",
        "enter_price": "Geben Sie den Preis des Produkts (in €) ein:",
        "order_summary": "Ihre Bestellung:\nName: {name}\nAdresse: {address}\nTelefon: {phone}\nE-Mail: {email}\n\nBestelldetails:\n{order_details}\n\nGesamtgewicht: {total_weight} kg\nGesamtkosten: {total_cost} €",
        "order_confirmed": "Ihre Bestellung wurde bestätigt! Wir werden uns mit Ihnen in Verbindung setzen, um die Details zu klären.",
        "order_cancelled": "Ihre Bestellung wurde storniert.",
        "unknown_message": "Entschuldigung, ich verstehe diese Nachricht nicht. Bitte versuchen Sie, Befehle zu verwenden oder folgen Sie den Anweisungen.",
        "admin_notification": "Neue Bestellung von {name}:\nAdresse: {address}\nTelefon: {phone}\nE-Mail: {email}\nBestelldetails:\n{order_details}\nGesamtgewicht: {total_weight} kg\nGesamtkosten: {total_cost} €\n\nTelegram-ID des Kunden: {telegram_id}\n",
        "button_continue_order": "Bestellung fortsetzen",
        "button_cancel_last_item": "Letzten Artikel stornieren",
        "button_finish_order": "Liste abschließen",
        "button_confirm": "Bestätigen",
        "button_edit": "Bearbeiten",
        "button_cancel": "Stornieren",
        "button_new_order": "Neue Bestellung starten",
        "button_start_order": "Bestellung starten",
        "new_order_prompt": "Wenn Sie eine neue Bestellung aufgeben möchten, klicken Sie auf die Schaltfläche unten:",
        "start_order_prompt": "Wenn Sie eine neue Bestellung starten möchten, klicken Sie auf die Schaltfläche unten.",
        "pay_order_prompt": "Bestellung bezahlen",
        "total_cost_of_goods": "Gesamtkosten der Waren",
        "delivery_cost": "Lieferkosten",
        "service_cost": "Servicegebühr (10%)",
        "total_amount": "Gesamtbetrag"
    },
    "fr": {
        "choose_language": "Choisissez votre langue :",
        "language_selected": "Langue sélectionnée !",
        "download_catalog": "Merci ! Vous pouvez maintenant télécharger le catalogue des produits.",
        "catalog_not_found": "Catalogue des produits introuvable. Veuillez télécharger le fichier catalog.pdf dans le dossier du bot.",
        "fill_order_form": "Après avoir consulté le catalogue, cliquez sur le bouton ci-dessous pour commencer à passer votre commande.",
        "enter_name": "Entrez votre nom complet :",
        "enter_address": "Entrez votre adresse de livraison :",
        "enter_phone": "Entrez votre numéro de téléphone :",
        "enter_email": "Entrez votre email :",
        "enter_product_name": "Entrez le nom du produit :",
        "enter_quantity": "Entrez la quantité du produit :",
        "enter_weight": "Entrez le poids du produit (en kg) :",
        "enter_price": "Entrez le prix du produit (en €) :",
        "order_summary": "Votre commande :\nNom : {name}\nAdresse : {address}\nTéléphone : {phone}\nEmail : {email}\n\nDétails de la commande :\n{order_details}\n\nPoids total : {total_weight} kg\nCoût total : {total_cost} €",
        "order_confirmed": "Votre commande a été confirmée ! Nous vous contacterons pour clarifier les détails.",
        "order_cancelled": "Votre commande a été annulée.",
        "unknown_message": "Désolé, je ne comprends pas ce message. Veuillez essayer d'utiliser des commandes ou suivre les instructions.",
        "admin_notification": "Nouvelle commande de {name} :\nAdresse : {address}\nTéléphone : {phone}\nEmail : {email}\nDétails de la commande :\n{order_details}\nPoids total : {total_weight} kg\nCoût total : {total_cost} €\n\nID Telegram du client : {telegram_id}\n",
        "button_continue_order": "Continuer la commande",
        "button_cancel_last_item": "Annuler le dernier article",
        "button_finish_order": "Terminer la liste",
        "button_confirm": "Confirmer",
        "button_edit": "Modifier",
        "button_cancel": "Annuler",
        "button_new_order": "Commencer une nouvelle commande",
        "button_start_order": "Commencer la commande",
        "new_order_prompt": "Si vous souhaitez passer une nouvelle commande, cliquez sur le bouton ci-dessous :",
        "start_order_prompt": "Si vous souhaitez recommencer une commande, cliquez sur le bouton ci-dessous.",
        "pay_order_prompt": "Payer la commande",
        "total_cost_of_goods": "Coût total des produits",
        "delivery_cost": "Coût de livraison",
        "service_cost": "Frais de service (10%)",
        "total_amount": "Montant total"
    },
    "es": {
        "choose_language": "Elige tu idioma:",
        "language_selected": "¡Idioma seleccionado!",
        "download_catalog": "¡Gracias! Ahora puedes descargar el catálogo de productos.",
        "catalog_not_found": "Catálogo de productos no encontrado. Por favor, sube el archivo catalog.pdf a la carpeta del bot.",
        "fill_order_form": "Después de revisar el catálogo, haz clic en el botón de abajo para comenzar a realizar tu pedido.",
        "enter_name": "Introduce tu nombre completo:",
        "enter_address": "Introduce tu dirección de entrega:",
        "enter_phone": "Introduce tu número de teléfono:",
        "enter_email": "Introduce tu correo electrónico:",
        "enter_product_name": "Introduce el nombre del producto:",
        "enter_quantity": "Introduce la cantidad del producto:",
        "enter_weight": "Introduce el peso del producto (en kg):",
        "enter_price": "Introduce el precio del producto (en €):",
        "order_summary": "Tu pedido:\nNombre: {name}\nDirección: {address}\nTeléfono: {phone}\nCorreo electrónico: {email}\n\nDetalles del pedido:\n{order_details}\n\nPeso total: {total_weight} kg\nCosto total: {total_cost} €",
        "order_confirmed": "¡Tu pedido ha sido confirmado! Nos pondremos en contacto contigo para aclarar los detalles.",
        "order_cancelled": "Tu pedido ha sido cancelado.",
        "unknown_message": "Lo siento, no entiendo este mensaje. Por favor, intenta usar comandos o sigue las instrucciones.",
        "admin_notification": "Nuevo pedido de {name}:\nDirección: {address}\nTeléfono: {phone}\nCorreo electrónico: {email}\nDetalles del pedido:\n{order_details}\nPeso total: {total_weight} kg\nCosto total: {total_cost} €\n\nID de Telegram del cliente: {telegram_id}\n",
        "button_continue_order": "Continuar pedido",
        "button_cancel_last_item": "Cancelar último artículo",
        "button_finish_order": "Finalizar lista",
        "button_confirm": "Confirmar",
        "button_edit": "Editar",
        "button_cancel": "Cancelar",
        "button_new_order": "Comenzar un nuevo pedido",
        "button_start_order": "Comenzar pedido",
        "new_order_prompt": "Si deseas realizar un nuevo pedido, haz clic en el botón de abajo:",
        "start_order_prompt": "Si deseas comenzar un nuevo pedido, haz clic en el botón de abajo.",
        "pay_order_prompt": "Pagar el pedido",
        "total_cost_of_goods": "Costo total de los productos",
        "delivery_cost": "Costo de envío",
        "service_cost": "Costo del servicio (10%)",
        "total_amount": "Monto total"
    }
    
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

@router.callback_query(lambda c: c.data == "cancel_order")
async def cancel_order(callback_query: types.CallbackQuery, state: FSMContext):
    # Очищаем состояние
    await state.clear()

    # Уведомляем клиента, что заказ отменён
    await callback_query.message.answer(get_translation(callback_query.from_user.id, "order_cancelled"))

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
async def request_payment(callback_query: types.CallbackQuery):
    user_id = int(callback_query.data.split("_")[-1])

    # Запрашиваем у администратора стоимость доставки
    await callback_query.message.answer("Введите стоимость доставки (в €):")
    await PaymentForm.total_amount.set()

    # Сохраняем ID клиента для дальнейшей обработки
    await bot.get("state").update_data(client_id=user_id)

@router.message(PaymentForm.total_amount)
async def process_delivery_cost(message: types.Message, state: FSMContext):
    try:
        delivery_cost = float(message.text)
        if delivery_cost <= 0:
            raise ValueError

        # Получаем данные клиента
        data = await state.get_data()
        client_id = data.get("client_id")

        # Рассчитываем итоговую сумму
        total_cost = delivery_cost + (delivery_cost * 0.1)  # Добавляем 10% за услугу
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
    await bot.delete_webhook(drop_pending_updates=True)

    # Запускаем HTTP-сервер и бота параллельно
    await asyncio.gather(
        start_web_server(),  # Запуск HTTP-сервера
        dp.start_polling(bot)  # Запуск бота
    )

if __name__ == "__main__":
    asyncio.run(main())
