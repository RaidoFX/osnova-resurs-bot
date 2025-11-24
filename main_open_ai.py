import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes, CallbackQueryHandler
from openai import OpenAI

from src import OPENAI_API_KEY, ASSISTANT_ID, TELEGRAM_TOKEN

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализация клиента OpenAI
client = OpenAI(api_key=OPENAI_API_KEY)

# Хранилище данных пользователей
user_states = {}
user_data = {}  # Для хранения собранных данных
user_threads = {}  # Для хранения тредов OpenAI

# ID менеджера для уведомлений (замените на реальный ID)
MANAGER_CHAT_ID = 1791945909


# --- Клавиатуры ---
def get_consent_keyboard():
    keyboard = [
        [InlineKeyboardButton("✅ Согласен", callback_data="consent_agree")],
        [InlineKeyboardButton("❌ Не согласен", callback_data="consent_disagree")]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_service_keyboard():
    keyboard = [
        [InlineKeyboardButton("🚗 Заправить газгольдер", callback_data="service_gasgolder")],
        [InlineKeyboardButton("🏭 Доставка на АГЗС", callback_data="service_ags")]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_confirmation_keyboard():
    keyboard = [
        [InlineKeyboardButton("✅ Всё верно, отправить заявку", callback_data="confirm_yes")],
        [InlineKeyboardButton("✏️ Исправить данные", callback_data="confirm_no")]
    ]
    return InlineKeyboardMarkup(keyboard)


# --- Функции для работы с данными ---
def init_user_data(user_id):
    """Инициализирует данные пользователя"""
    if user_id not in user_data:
        user_data[user_id] = {
            "address": "",
            "gas_amount": "",
            "phone": "",
            "service_type": ""
        }


def update_user_data(user_id, field, value):
    """Обновляет данные пользователя"""
    init_user_data(user_id)
    user_data[user_id][field] = value


def get_user_data_summary(user_id):
    """Возвращает сводку данных пользователя"""
    init_user_data(user_id)
    data = user_data[user_id]
    return f"""
📋 Сводка заявки:

📍 Адрес: {data['address'] or 'не указан'}
⚡ Количество газа: {data['gas_amount'] or 'не указано'}  
📞 Телефон: {data['phone'] or 'не указан'}
🎯 Услуга: {data['service_type'] or 'не указана'}
"""


def clear_user_data(user_id):
    """Очищает данные пользователя"""
    if user_id in user_data:
        user_data[user_id] = {
            "address": "",
            "gas_amount": "",
            "phone": "",
            "service_type": ""
        }
    if user_id in user_states:
        user_states[user_id] = {}
    if user_id in user_threads:
        del user_threads[user_id]


async def send_to_manager(user_id, user_name, context: ContextTypes.DEFAULT_TYPE):
    """Отправляет заявку менеджеру"""
    try:
        data = user_data.get(user_id, {})

        message_to_manager = f"""
🚨 НОВАЯ ЗАЯВКА

👤 Клиент: {user_name}
📞 ID: {user_id}

📍 Адрес: {data.get('address', 'не указан')}
⚡ Количество газа: {data.get('gas_amount', 'не указано')}
📞 Телефон: {data.get('phone', 'не указан')}
🎯 Услуга: {data.get('service_type', 'не указана')}

Свяжитесь с клиентом для уточнения деталей!
        """

        # Отправляем менеджеру (замените на реальный ID)
        await context.bot.send_message(chat_id=MANAGER_CHAT_ID, text=message_to_manager)

        # Временный вывод в консоль
        print("=" * 50)
        print("🚨 НОВАЯ ЗАЯВКА:")
        print(message_to_manager)
        print("=" * 50)

        logger.info(f"Заявка отправлена менеджеру для пользователя {user_id}")
        return True

    except Exception as e:
        logger.error(f"Ошибка отправки менеджеру: {e}")
        return False


async def get_assistant_response(user_id, user_message):
    """Получает ответ от ассистента OpenAI"""
    try:
        # Создаем или получаем тред пользователя
        if user_id not in user_threads:
            thread = client.beta.threads.create()
            user_threads[user_id] = thread.id

        thread_id = user_threads[user_id]

        # Отправляем сообщение пользователя в тред
        client.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=user_message
        )

        # Запускаем ассистента
        run = client.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=ASSISTANT_ID
        )

        # Ожидаем завершения обработки
        while run.status in ("queued", "in_progress"):
            run = client.beta.threads.runs.retrieve(
                thread_id=thread_id,
                run_id=run.id
            )

        # Получаем ответ ассистента
        messages = client.beta.threads.messages.list(thread_id=thread_id)
        response_texts = [
            msg.content[0].text.value
            for msg in reversed(messages.data)
            if msg.role == "assistant"
        ]

        return "\n".join(response_texts) if response_texts else "Нет ответа от ассистента."

    except Exception as e:
        logger.error(f"Ошибка OpenAI: {e}")
        return "Ошибка при обработке запроса. Попробуйте позже."


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка команды /start"""
    user_id = update.message.chat.id
    user_name = update.message.from_user.first_name

    # Сбрасываем состояние и данные пользователя
    clear_user_data(user_id)
    user_states[user_id] = {"step": "consent"}

    welcome_text = f"""
👋 Добро пожаловать, {user_name}! 

Говорит представитель компании «ОСНОВА-РЕСУРС». 

Мы помогаем с надежными поставками пропан-бутана для бизнеса и частных лиц.

Прежде чем продолжить, для соблюдения законодательства РФ, мне необходимо ваше согласие на обработку персональных данных.
    """

    sent_message = await update.message.reply_text(
        welcome_text,
        reply_markup=get_consent_keyboard()
    )


async def handle_button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка нажатий на кнопки"""
    query = update.callback_query
    user_id = query.message.chat.id
    user_name = query.message.chat.first_name
    data = query.data

    await query.answer()

    if data == "consent_agree":
        user_states[user_id] = {"step": "service_selection", "consent": True}

        new_message = await query.message.reply_text(
            "✅ Спасибо за доверие!\n\n"
            "Выберите подходящую услугу:",
            reply_markup=get_service_keyboard()
        )

    elif data == "consent_disagree":
        await query.message.reply_text(
            "Я понимаю. Без вашего согласия я не могу обработать заявку. "
            "Если возникнут вопросы - обращайтесь. Хорошего дня!",
            reply_markup=None
        )

    elif data == "service_gasgolder":
        user_states[user_id] = {"step": "address", "service": "gasgolder"}
        update_user_data(user_id, "service_type", "Заправка газгольдера")

        new_message = await query.message.reply_text(
            "🚗 Вы выбрали заправку газгольдера.\n\n"
            "📍 Шаг 1 из 3: Укажите ваш полный адрес для доставки:\n"
            "• Населенный пункт\n"
            "• Улица, дом\n"
            "• Район\n\n"
            "Например: деревня Дурыкино, Солнечногорский район, ул. Центральная, д. 10",
            reply_markup=None
        )

    elif data == "service_ags":
        user_states[user_id] = {"step": "address", "service": "ags"}
        update_user_data(user_id, "service_type", "Доставка на АГЗС")

        new_message = await query.message.reply_text(
            "🏭 Вы выбрали доставку на АГЗС.\n\n"
            "📍 Шаг 1 из 3: Укажите адрес АГЗС:\n"
            "• Населенный пункт\n"
            "• Адрес АГЗС\n"
            "• Район\n\n"
            "Например: г. Солнечногорск, ул. Промышленная, АГЗС №5",
            reply_markup=None
        )

    elif data == "confirm_yes":
        # Отправляем заявку менеджеру
        success = await send_to_manager(user_id, user_name, context)

        if success:
            await query.message.reply_text(
                f"✅ Отлично! Ваша заявка принята и передана менеджеру.\n\n"
                f"📋 Номер заявки: #{user_id}\n"
                f"📞 Наш менеджер свяжется с вами в ближайшее время для уточнения деталей.\n\n"
                f"Спасибо за выбор «ОСНОВА-РЕСУРС»! 🚚",
                reply_markup=None
            )
        else:
            await query.message.reply_text(
                "❌ Произошла ошибка при отправке заявки. Пожалуйста, позвоните нам напрямую.",
                reply_markup=None
            )

    elif data == "confirm_no":
        user_states[user_id] = {"step": "address", "service": user_data[user_id].get("service_type", "")}
        await query.message.reply_text(
            "Давайте исправим данные. Начнем с адреса:\n\n"
            "📍 Укажите ваш полный адрес:",
            reply_markup=None
        )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка текстовых сообщений"""
    user_id = update.message.chat.id
    user_message = update.message.text
    user_state = user_states.get(user_id, {})

    status_msg = await update.message.reply_text("⏳ Сохраняю информацию...")

    try:
        current_step = user_state.get("step")

        if current_step == "address":
            # Сохраняем адрес
            update_user_data(user_id, "address", user_message)
            user_states[user_id] = {"step": "gas_amount", "service": user_state.get("service", "")}

            await status_msg.edit_text(
                "✅ Адрес сохранен!\n\n"
                "⚡ Шаг 2 из 3: Укажите необходимое количество газа:\n"
                "• Для газгольдера: сколько литров нужно заправить\n"
                "• Для АГЗС: сколько тонн/литров требуется\n\n"
                "Например: 5000 литров или 2 тонны"
            )

        elif current_step == "gas_amount":
            # Сохраняем количество газа
            update_user_data(user_id, "gas_amount", user_message)
            user_states[user_id] = {"step": "phone", "service": user_state.get("service", "")}

            await status_msg.edit_text(
                "✅ Количество газа сохранено!\n\n"
                "📞 Шаг 3 из 3: Укажите ваш контактный телефон:\n"
                "• Номер для связи\n"
                "• В любом формате\n\n"
                "Например: +7 999 123-45-67 или 89991234567"
            )

        elif current_step == "phone":
            # Сохраняем телефон и показываем сводку
            update_user_data(user_id, "phone", user_message)

            summary = get_user_data_summary(user_id)

            await status_msg.edit_text(
                f"{summary}\n\n"
                "Проверьте правильность данных и отправьте заявку менеджеру:",
                reply_markup=get_confirmation_keyboard()
            )

        else:
            # Для других сообщений используем ассистента OpenAI
            response_text = await get_assistant_response(user_id, user_message)
            await status_msg.edit_text(response_text)

    except Exception as e:
        logger.error(f"Ошибка: {e}")
        await status_msg.edit_text("❌ Ошибка обработки. Попробуйте позже.")


def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_button_click))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("✅ Бот-сборщик заявок запущен с OpenAI Assistant!")
    print("⚠️  Не забудьте установить MANAGER_CHAT_ID для отправки уведомлений")
    app.run_polling()


if __name__ == "__main__":
    main()