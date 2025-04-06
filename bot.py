import logging
from aiogram import Bot, Dispatcher, types, Router
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.filters import Command
import sqlite3
from aiohttp import web
import asyncio

# Настройки бота
API_TOKEN = "8190038878:AAF_gh-NqR3fCFB2hEiFFhuKPtvK_cH_aEg"  # Замените на токен вашего бота
PROVIDER_TOKEN = "2051251535:TEST:OTk5MDA4ODgxLTAwNQ"  # Замените на токен платёжного провайдера
ADMIN_ID = 6286389072  # Замените на ваш Telegram ID
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
    order_details = State()
    confirm = State()

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
        "enter_order_details": (
            "Введите детали заказа в следующем формате:\n"
            "1. Nutella, 2, 0.95, 6\n"
            "2. Kinder, 3, 0.5, 4.5\n\n"
            "Формат: <название товара>, <количество>, <вес (кг)>, <цена за единицу (€)>"
        ),
        "order_summary": "Ваш заказ:\nИмя: {name}\nАдрес: {address}\nТелефон: {phone}\nEmail: {email}\n\nДетали заказа:\n{order_details}\n\nОбщий вес: {total_weight} кг\nОбщая стоимость: {total_cost} €",
        "order_confirmed": "Ваш заказ подтверждён! Мы свяжемся с вами для уточнения деталей.",
        "order_cancelled": "Заказ отменён.",
        "unknown_message": "Извините, я не понимаю это сообщение. Попробуйте использовать команды или следуйте инструкциям.",
        "admin_notification": "Новый заказ от {name}:\nАдрес: {address}\nТелефон: {phone}\nEmail: {email}\nДетали заказа:\n{order_details}\nОбщий вес: {total_weight} кг\nОбщая стоимость: {total_cost} €\n\nTelegram ID клиента: {telegram_id}\n",
        "order_details_error": (
            "Пожалуйста, введите детали заказа в правильном формате. Пример:\n\n"
            "1. Nutella, 2, 0.95, 6\n"
            "2. Kinder, 3, 0.5, 4.5\n\n"
            "Формат: <название товара>, <количество>, <вес (кг)>, <цена за единицу (€)>"
        ),
        "button_confirm": "Подтвердить",
        "button_edit": "Изменить",
        "button_cancel": "Отменить",
        "button_new_order": "Новый заказ",
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
        "download_catalog": "Thank you! Now you can download the product catalog.",
        "catalog_not_found": "The product catalog was not found. Please upload the catalog.pdf file to the bot's folder.",
        "fill_order_form": "After reviewing the catalog, click the button below to start your order.",
        "enter_name": "Enter your full name:",
        "enter_address": "Enter your delivery address:",
        "enter_phone": "Enter your phone number:",
        "enter_email": "Enter your email:",
        "enter_order_details": (
            "Enter the details of your order in the following format:\n"
            "1. Nutella, 2, 0.95, 6\n"
            "2. Kinder, 3, 0.5, 4.5\n\n"
            "Format: <product name>, <quantity>, <weight (kg)>, <price per unit (€)>"
        ),
        "order_summary": "Your order:\nName: {name}\nAddress: {address}\nPhone: {phone}\nEmail: {email}\n\nOrder details:\n{order_details}\n\nTotal weight: {total_weight} kg\nTotal cost: {total_cost} €",
        "order_confirmed": "Your order has been confirmed! We will contact you to clarify the details.",
        "order_cancelled": "Order cancelled.",
        "unknown_message": "Sorry, I don't understand this message. Try using commands or follow the instructions.",
        "admin_notification": "New order from {name}:\nAddress: {address}\nPhone: {phone}\nEmail: {email}\nOrder details:\n{order_details}\nTotal weight: {total_weight} kg\nTotal cost: {total_cost} €\n\nTelegram ID of the client: {telegram_id}\n",
        "order_details_error": (
            "Please enter the order details in the correct format. Example:\n\n"
            "1. Nutella, 2, 0.95, 6\n"
            "2. Kinder, 3, 0.5, 4.5\n\n"
            "Format: <product name>, <quantity>, <weight (kg)>, <price per unit (€)>"
        ),
        "button_confirm": "Confirm",
        "button_edit": "Edit",
        "button_cancel": "Cancel",
        "button_new_order": "New Order",
        "button_start_order": "Start Order",
        "new_order_prompt": "If you want to place a new order, click the button below:",
        "start_order_prompt": "If you want to start the order again, click the button below.",
        "pay_order_prompt": "Pay for the order",
        "total_cost_of_goods": "Total cost of goods",
        "delivery_cost": "Delivery cost",
        "service_cost": "Service cost (10%)",
        "total_amount": "Total amount"
    },
    "it": {
        "choose_language": "Scegli la tua lingua:",
        "language_selected": "Lingua selezionata!",
        "download_catalog": "Grazie! Ora puoi scaricare il catalogo dei prodotti.",
        "catalog_not_found": "Il catalogo dei prodotti non è stato trovato. Carica il file catalog.pdf nella cartella del bot.",
        "fill_order_form": "Dopo aver esaminato il catalogo, clicca sul pulsante qui sotto per iniziare l'ordine.",
        "enter_name": "Inserisci il tuo nome e cognome:",
        "enter_address": "Inserisci il tuo indirizzo di consegna:",
        "enter_phone": "Inserisci il tuo numero di telefono:",
        "enter_email": "Inserisci la tua email:",
        "enter_order_details": (
            "Inserisci i dettagli del tuo ordine nel seguente formato:\n"
            "1. Nutella, 2, 0.95, 6\n"
            "2. Kinder, 3, 0.5, 4.5\n\n"
            "Formato: <nome del prodotto>, <quantità>, <peso (kg)>, <prezzo unitario (€)>"
        ),
        "order_summary": "Il tuo ordine:\nNome: {name}\nIndirizzo: {address}\nTelefono: {phone}\nEmail: {email}\n\nDettagli ordine:\n{order_details}\n\nPeso totale: {total_weight} kg\nCosto totale: {total_cost} €",
        "order_confirmed": "Il tuo ordine è stato confermato! Ti contatteremo per ulteriori dettagli.",
        "order_cancelled": "Ordine annullato.",
        "unknown_message": "Mi dispiace, non capisco questo messaggio. Prova a usare i comandi o segui le istruzioni.",
        "admin_notification": "Nuovo ordine da {name}:\nIndirizzo: {address}\nTelefono: {phone}\nEmail: {email}\nDettagli ordine:\n{order_details}\nPeso totale: {total_weight} kg\nCosto totale: {total_cost} €\n\nTelegram ID del cliente: {telegram_id}\n",
        "order_details_error": (
            "Inserisci i dettagli del tuo ordine nel formato corretto. Esempio:\n\n"
            "1. Nutella, 2, 0.95, 6\n"
            "2. Kinder, 3, 0.5, 4.5\n\n"
            "Formato: <nome del prodotto>, <quantità>, <peso (kg)>, <prezzo unitario (€)>"
        ),
        "button_confirm": "Conferma",
        "button_edit": "Modifica",
        "button_cancel": "Annulla",
        "button_new_order": "Nuovo ordine",
        "button_start_order": "Inizia ordine",
        "new_order_prompt": "Se desideri effettuare un nuovo ordine, clicca sul pulsante qui sotto:",
        "start_order_prompt": "Se desideri ricominciare l'ordine, clicca sul pulsante qui sotto.",
        "pay_order_prompt": "Paga l'ordine",
        "total_cost_of_goods": "Costo totale dei prodotti",
        "delivery_cost": "Costo di consegna",
        "service_cost": "Costo del servizio (10%)",
        "total_amount": "Importo totale"
    },
    "de": {
        "choose_language": "Wähle deine Sprache:",
        "language_selected": "Sprache ausgewählt!",
        "download_catalog": "Danke! Jetzt kannst du den Produktkatalog herunterladen.",
        "catalog_not_found": "Der Produktkatalog wurde nicht gefunden. Bitte lade die Datei catalog.pdf in den Bot-Ordner hoch.",
        "fill_order_form": "Klicke nach Durchsicht des Katalogs auf die Schaltfläche unten, um deine Bestellung zu starten.",
        "enter_name": "Gib deinen vollständigen Namen ein:",
        "enter_address": "Gib deine Lieferadresse ein:",
        "enter_phone": "Gib deine Telefonnummer ein:",
        "enter_email": "Gib deine E-Mail-Adresse ein:",
        "enter_order_details": (
            "Gib die Details deiner Bestellung im folgenden Format ein:\n"
            "1. Nutella, 2, 0.95, 6\n"
            "2. Kinder, 3, 0.5, 4.5\n\n"
            "Format: <Produktname>, <Menge>, <Gewicht (kg)>, <Preis pro Einheit (€)>"
        ),
        "order_summary": "Deine Bestellung:\nName: {name}\nAdresse: {address}\nTelefon: {phone}\nE-Mail: {email}\n\nBestelldetails:\n{order_details}\n\nGesamtgewicht: {total_weight} kg\nGesamtkosten: {total_cost} €",
        "order_confirmed": "Deine Bestellung wurde bestätigt! Wir werden uns mit dir in Verbindung setzen, um die Details zu klären.",
        "order_cancelled": "Bestellung storniert.",
        "unknown_message": "Entschuldigung, ich verstehe diese Nachricht nicht. Versuche, Befehle zu verwenden oder folge den Anweisungen.",
        "admin_notification": "Neue Bestellung von {name}:\nAdresse: {address}\nTelefon: {phone}\nE-Mail: {email}\nBestelldetails:\n{order_details}\nGesamtgewicht: {total_weight} kg\nGesamtkosten: {total_cost} €\n\nTelegram-ID des Kunden: {telegram_id}\n",
        "order_details_error": (
            "Bitte gib die Bestelldetails im richtigen Format ein. Beispiel:\n\n"
            "1. Nutella, 2, 0.95, 6\n"
            "2. Kinder, 3, 0.5, 4.5\n\n"
            "Format: <Produktname>, <Menge>, <Gewicht (kg)>, <Preis pro Einheit (€)>"
        ),
        "button_confirm": "Bestätigen",
        "button_edit": "Bearbeiten",
        "button_cancel": "Abbrechen",
        "button_new_order": "Neue Bestellung",
        "button_start_order": "Bestellung starten",
        "new_order_prompt": "Wenn Sie eine neue Bestellung aufgeben möchten, klicken Sie auf die Schaltfläche unten:",
        "start_order_prompt": "Wenn Sie die Bestellung erneut starten möchten, klicken Sie auf die Schaltfläche unten.",
        "pay_order_prompt": "Bestellung bezahlen",
        "total_cost_of_goods": "Gesamtkosten der Waren",
        "delivery_cost": "Lieferkosten",
        "service_cost": "Servicekosten (10%)",
        "total_amount": "Gesamtbetrag"
    },
    "fr": {
        "choose_language": "Choisissez votre langue:",
        "language_selected": "Langue sélectionnée!",
        "download_catalog": "Merci! Vous pouvez maintenant télécharger le catalogue des produits.",
        "catalog_not_found": "Le catalogue des produits est introuvable. Veuillez télécharger le fichier catalog.pdf dans le dossier du bot.",
        "fill_order_form": "Après avoir consulté le catalogue, cliquez sur le bouton ci-dessous pour commencer votre commande.",
        "enter_name": "Entrez votre nom complet:",
        "enter_address": "Entrez votre adresse de livraison:",
        "enter_phone": "Entrez votre numéro de téléphone:",
        "enter_email": "Entrez votre email:",
        "enter_order_details": (
            "Entrez les détails de votre commande dans le format suivant:\n"
            "1. Nutella, 2, 0.95, 6\n"
            "2. Kinder, 3, 0.5, 4.5\n\n"
            "Format: <nom du produit>, <quantité>, <poids (kg)>, <prix unitaire (€)>"
        ),
        "order_summary": "Votre commande:\nNom: {name}\nAdresse: {address}\nTéléphone: {phone}\nEmail: {email}\n\nDétails de la commande:\n{order_details}\n\nPoids total: {total_weight} kg\nCoût total: {total_cost} €",
        "order_confirmed": "Votre commande a été confirmée! Nous vous contacterons pour plus de détails.",
        "order_cancelled": "Commande annulée.",
        "unknown_message": "Désolé, je ne comprends pas ce message. Essayez d'utiliser des commandes ou suivez les instructions.",
        "admin_notification": "Nouvelle commande de {name}:\nAdresse: {address}\nTéléphone: {phone}\nEmail: {email}\nDétails de la commande:\n{order_details}\nPoids total: {total_weight} kg\nCoût total: {total_cost} €\n\nID Telegram du client: {telegram_id}\n",
        "order_details_error": (
            "Veuillez entrer les détails de la commande dans le format correct. Exemple:\n\n"
            "1. Nutella, 2, 0.95, 6\n"
            "2. Kinder, 3, 0.5, 4.5\n\n"
            "Format: <nom du produit>, <quantité>, <poids (kg)>, <prix unitaire (€)>"
        ),
        "button_confirm": "Confirmer",
        "button_edit": "Modifier",
        "button_cancel": "Annuler",
        "button_new_order": "Nouvelle commande",
        "button_start_order": "Commencer la commande",
        "new_order_prompt": "Si vous souhaitez passer une nouvelle commande, cliquez sur le bouton ci-dessous:",
        "start_order_prompt": "Si vous souhaitez recommencer la commande, cliquez sur le bouton ci-dessous.",
        "pay_order_prompt": "Payer la commande",
        "total_cost_of_goods": "Coût total des marchandises",
        "delivery_cost": "Frais de livraison",
        "service_cost": "Frais de service (10%)",
        "total_amount": "Montant total"
    },
    "es": {
        "choose_language": "Elige tu idioma:",
        "language_selected": "¡Idioma seleccionado!",
        "download_catalog": "¡Gracias! Ahora puedes descargar el catálogo de productos.",
        "catalog_not_found": "No se encontró el catálogo de productos. Por favor, sube el archivo catalog.pdf a la carpeta del bot.",
        "fill_order_form": "Después de revisar el catálogo, haz clic en el botón de abajo para iniciar tu pedido.",
        "enter_name": "Introduce tu nombre completo:",
        "enter_address": "Introduce tu dirección de entrega:",
        "enter_phone": "Introduce tu número de teléfono:",
        "enter_email": "Introduce tu correo electrónico:",
        "enter_order_details": (
            "Introduce los detalles de tu pedido en el siguiente formato:\n"
            "1. Nutella, 2, 0.95, 6\n"
            "2. Kinder, 3, 0.5, 4.5\n\n"
            "Formato: <nombre del producto>, <cantidad>, <peso (kg)>, <precio por unidad (€)>"
        ),
        "order_summary": "Tu pedido:\nNombre: {name}\nDirección: {address}\nTeléfono: {phone}\nCorreo electrónico: {email}\n\nDetalles del pedido:\n{order_details}\n\nPeso total: {total_weight} kg\nCosto total: {total_cost} €",
        "order_confirmed": "¡Tu pedido ha sido confirmado! Nos pondremos en contacto contigo para más detalles.",
        "order_cancelled": "Pedido cancelado.",
        "unknown_message": "Lo siento, no entiendo este mensaje. Intenta usar comandos o sigue las instrucciones.",
        "admin_notification": "Nuevo pedido de {name}:\nDirección: {address}\nTeléfono: {phone}\nCorreo electrónico: {email}\nDetalles del pedido:\n{order_details}\nPeso total: {total_weight} kg\nCosto total: {total_cost} €\n\nID de Telegram del cliente: {telegram_id}\n",
        "order_details_error": (
            "Por favor, introduce los detalles del pedido en el formato correcto. Ejemplo:\n\n"
            "1. Nutella, 2, 0.95, 6\n"
            "2. Kinder, 3, 0.5, 4.5\n\n"
            "Formato: <nombre del producto>, <cantidad>, <peso (kg)>, <precio por unidad (€)>"
        ),
        "button_confirm": "Confirmar",
        "button_edit": "Editar",
        "button_cancel": "Cancelar",
        "button_new_order": "Nuevo pedido",
        "button_start_order": "Iniciar pedido",
        "new_order_prompt": "Si deseas realizar un nuevo pedido, haz clic en el botón de abajo:",
        "start_order_prompt": "Si deseas comenzar el pedido de nuevo, haz clic en el botón de abajo.",
        "pay_order_prompt": "Pagar el pedido",
        "total_cost_of_goods": "Costo total de los productos",
        "delivery_cost": "Costo de envío",
        "service_cost": "Costo del servicio (10%)",
        "total_amount": "Cantidad total"
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
    await state.update_data(name=message.text)
    await state.set_state(OrderForm.address)
    await message.answer(get_translation(message.from_user.id, "enter_address"))

@router.message(OrderForm.address)
async def process_address(message: types.Message, state: FSMContext):
    await state.update_data(address=message.text)
    await state.set_state(OrderForm.phone)
    await message.answer(get_translation(message.from_user.id, "enter_phone"))

@router.message(OrderForm.phone)
async def process_phone(message: types.Message, state: FSMContext):
    await state.update_data(phone=message.text)
    await state.set_state(OrderForm.email)
    await message.answer(get_translation(message.from_user.id, "enter_email"))

@router.message(OrderForm.email)
async def process_email(message: types.Message, state: FSMContext):
    await state.update_data(email=message.text)
    await state.set_state(OrderForm.order_details)
    await message.answer(get_translation(message.from_user.id, "enter_order_details"))

@router.message(OrderForm.order_details)
async def process_order_details(message: types.Message, state: FSMContext):
    order_details = message.text
    total_weight = 0
    total_cost = 0

    # Разбор строки с деталями заказа
    try:
        items = order_details.split("\n")  # Предполагаем, что товары разделены переносом строки
        parsed_items = []
        for item in items:
            # Проверяем, соответствует ли строка формату "<название>, <количество>, <вес>, <цена>"
            parts = item.split(",")
            if len(parts) != 4:
                raise ValueError("Неверный формат строки")

            name, quantity, weight, cost = parts
            name = name.strip()
            quantity = int(quantity.strip())
            weight = float(weight.strip())
            cost = float(cost.strip())

            total_weight += weight * quantity
            total_cost += cost * quantity
            parsed_items.append(f"{name} x{quantity} ({weight} kg) - {cost} €")

        # Сохраняем данные в состояние
        await state.update_data(order_details="\n".join(parsed_items), total_weight=total_weight, total_cost=total_cost)
        data = await state.get_data()

        # Переход к подтверждению заказа
        await state.set_state(OrderForm.confirm)

        # Получаем переводы для кнопок
        lang = user_languages.get(message.from_user.id, "ru")
        confirm_text = translations[lang].get("button_confirm", "Confirm")
        edit_text = translations[lang].get("button_edit", "Edit")
        cancel_text = translations[lang].get("button_cancel", "Cancel")

        # Кнопки для подтверждения, изменения и отмены
        confirm_keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text=confirm_text, callback_data="confirm_order"),
                    InlineKeyboardButton(text=edit_text, callback_data="edit_order"),
                    InlineKeyboardButton(text=cancel_text, callback_data="cancel_order")
                ]
            ]
        )

        await message.answer(get_translation(message.from_user.id, "order_summary",
                                             name=data['name'],
                                             address=data['address'],
                                             phone=data['phone'],
                                             email=data['email'],
                                             order_details=data['order_details'],
                                             total_weight=total_weight,
                                             total_cost=total_cost),
                             reply_markup=confirm_keyboard)
    except ValueError:
        # Если формат неверный, отправляем пример
        await message.answer(get_translation(message.from_user.id, "order_details_error"))

# Подтверждение заказа и отправка администратору
@router.callback_query(lambda c: c.data == "confirm_order")
async def confirm_order(callback_query: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    user_id = callback_query.from_user.id

    # Проверяем, есть ли детали заказа
    if not data.get("order_details") or data.get("total_weight") == 0 or data.get("total_cost") == 0:
        await callback_query.message.answer("Детали заказа отсутствуют или некорректны. Пожалуйста, начните заново.")
        await state.clear()
        return

    # Сохраняем заказ в таблицу orders
    cursor.execute("""
    INSERT INTO orders (telegram_id, name, address, phone, email, order_details, total_weight, total_cost, is_paid)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (user_id, data['name'], data['address'], data['phone'], data['email'], data['order_details'], data['total_weight'], data['total_cost'], 0))
    conn.commit()

    # Уведомляем клиента
    await callback_query.message.answer(get_translation(user_id, "order_confirmed"))

    # Формируем сообщение для администратора
    admin_message = (
        f"Новый заказ от {data['name']}:\n"
        f"Адрес: {data['address']}\n"
        f"Телефон: {data['phone']}\n"
        f"Email: {data['email']}\n"
        f"Детали заказа:\n{data['order_details']}\n"
        f"Общий вес: {data['total_weight']} кг\n"
        f"Общая стоимость: {data['total_cost']} €\n\n"
        f"Telegram ID клиента: {user_id}\n"
    )

    # Кнопки для администратора
    admin_buttons = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Ответить", url=f"tg://user?id={user_id}"),
                InlineKeyboardButton(text="Запросить оплату", callback_data=f"request_payment_{user_id}")
            ]
        ]
    )

    # Отправляем сообщение администратору
    await bot.send_message(chat_id=ADMIN_ID, text=admin_message, reply_markup=admin_buttons)

    # Очищаем состояние
    await state.clear()

# Обработка кнопки "Запросить оплату"
@router.callback_query(lambda c: c.data.startswith("request_payment_"))
async def request_payment(callback_query: types.CallbackQuery, state: FSMContext):
    # Извлекаем ID клиента из callback_data
    client_id = int(callback_query.data.split("_")[2])

    # Получаем последний заказ клиента из таблицы orders
    cursor.execute("""
    SELECT name, address, phone, email, order_details, total_weight, total_cost
    FROM orders
    WHERE telegram_id = ?
    ORDER BY created_at DESC
    LIMIT 1
    """, (client_id,))
    order = cursor.fetchone()

    if not order:
        await callback_query.answer("Заказ не найден.", show_alert=True)
        return

    # Извлекаем данные заказа
    name, address, phone, email, order_details, total_weight, total_cost = order

    # Сохраняем данные заказа в состояние
    await state.update_data(
        client_id=client_id,
        name=name,
        address=address,
        phone=phone,
        email=email,
        order_details=order_details,
        total_weight=total_weight,
        total_cost=total_cost
    )

    # Запрашиваем у администратора ввод стоимости доставки
    await state.set_state(PaymentForm.total_amount)
    await callback_query.message.answer(
        f"Введите стоимость доставки для клиента:\n\n"
        f"Стоимость товаров: {total_cost} €\n"
        f"Введите стоимость доставки в формате: 12.50"
    )


# Обрабатываем ввод стоимости доставки
@router.message(PaymentForm.total_amount)
async def process_total_amount(message: types.Message, state: FSMContext):
    try:
        # Получаем введённую стоимость доставки
        delivery_cost = float(message.text)

        # Получаем данные из состояния
        data = await state.get_data()
        client_id = data['client_id']
        name = data['name']
        address = data['address']
        phone = data['phone']
        email = data['email']
        order_details = data['order_details']
        total_weight = data['total_weight']
        total_cost = data['total_cost']

        # Рассчитываем стоимость услуги (10% от общей стоимости товаров)
        service_cost = round(total_cost * 0.1, 2)

        # Итоговая сумма
        total_amount = round(total_cost + delivery_cost + service_cost, 2)

        # Сохраняем итоговую сумму в таблицу orders
        cursor.execute("""
        UPDATE orders
        SET total_cost = ?, is_paid = 0
        WHERE id = (
            SELECT id
            FROM orders
            WHERE telegram_id = ? AND is_paid = 0
            ORDER BY created_at DESC
            LIMIT 1
        )
        """, (total_amount, client_id))
        conn.commit()

        # Извлекаем язык клиента
        lang = user_languages.get(client_id, "ru")

        # Формируем сообщение с деталями заказа
        order_details_message = get_translation(client_id, "order_summary",
                                                 name=name,
                                                 address=address,
                                                 phone=phone,
                                                 email=email,
                                                 order_details=order_details,
                                                 total_weight=total_weight,
                                                 total_cost=total_cost)

        # Формируем сообщение с расчётом стоимости
        cost_breakdown_message = (
            f"{get_translation(client_id, 'total_cost_of_goods')}: {total_cost} €\n"
            f"{get_translation(client_id, 'delivery_cost')}: {delivery_cost} €\n"
            f"{get_translation(client_id, 'service_cost')}: {service_cost} €\n\n"
            f"{get_translation(client_id, 'total_amount')}: {total_amount} €"
        )

        # Кнопка "Оплатить заказ"
        pay_button_text = get_translation(client_id, "pay_order_prompt")
        pay_button = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text=pay_button_text, callback_data=f"pay_order_{client_id}")
                ]
            ]
        )

        # Отправляем клиенту сообщение с деталями заказа
        await bot.send_message(chat_id=client_id, text=order_details_message, parse_mode="Markdown")

        # Отправляем клиенту сообщение с расчётом стоимости
        await bot.send_message(chat_id=client_id, text=cost_breakdown_message, reply_markup=pay_button)

        # Уведомляем администратора
        await message.answer(f"Запрос на оплату отправлен клиенту. Итоговая сумма: {total_amount} €")

        # Завершаем состояние
        await state.clear()

    except ValueError:
        # Если введено некорректное значение
        await message.answer("Пожалуйста, введите корректную сумму в формате: 12.50")


# Обработка кнопки "Оплатить заказ"
@router.callback_query(lambda c: c.data.startswith("pay_order_"))
async def send_invoice(callback_query: types.CallbackQuery):
    # Извлекаем ID клиента из callback_data
    client_id = int(callback_query.data.split("_")[2])

    # Получаем итоговую сумму из таблицы orders
    cursor.execute("""
    SELECT total_cost
    FROM orders
    WHERE telegram_id = ? AND is_paid = 0
    ORDER BY created_at DESC
    LIMIT 1
    """, (client_id,))
    order = cursor.fetchone()

    if not order:
        await callback_query.answer("Итоговая сумма не найдена. Попробуйте снова.", show_alert=True)
        return

    total_amount = order[0]

    # Извлекаем язык пользователя
    lang = user_languages.get(client_id, "ru")

    # Перевод текста сообщения и кнопки
    payment_title = get_translation(client_id, "pay_order_prompt")  # Текст заголовка
    payment_description = get_translation(client_id, "pay_order_prompt")  # Описание платежа

    # Отправляем счёт через Telegram Payments
    await bot.send_invoice(
        chat_id=client_id,
        title=payment_title,
        description=payment_description,
        payload=f"order_{client_id}",  # Уникальный идентификатор заказа
        provider_token=PROVIDER_TOKEN,  # Токен платёжного провайдера
        currency="EUR",
        prices=[
            types.LabeledPrice(label=payment_title, amount=int(total_amount * 100))  # Сумма в центах
        ],
        start_parameter="pay_order",
        need_name=True,
        need_phone_number=True,
        need_email=True
    )

    # Уведомляем администратора, что счёт отправлен
    await callback_query.answer("Счёт отправлен клиенту.")


# Обработка успешной оплаты
@router.message()
async def process_successful_payment(message: types.Message):
    # Проверяем, является ли сообщение успешным платежом
    if message.successful_payment:
        payment_info = message.successful_payment
        client_id = message.from_user.id
        total_amount = payment_info.total_amount / 100  # Сумма в евро

        # Обновляем статус заказа в базе данных
        cursor.execute("UPDATE orders SET is_paid = 1 WHERE telegram_id = ? ORDER BY created_at DESC LIMIT 1", (client_id,))
        conn.commit()

        # Извлекаем язык пользователя
        lang = user_languages.get(client_id, "ru")

        # Уведомляем клиента
        payment_confirmation_message = get_translation(client_id, "order_confirmed")
        await message.answer(payment_confirmation_message)

        # Уведомляем администратора
        admin_message = (
            f"Клиент оплатил заказ:\n"
            f"Telegram ID: {client_id}\n"
            f"Сумма оплаты: {total_amount} €"
        )
        await bot.send_message(ADMIN_ID, admin_message)

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
