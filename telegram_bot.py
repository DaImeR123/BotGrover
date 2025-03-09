import os
import django
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, 
    CommandHandler, 
    MessageHandler, 
    filters, 
    ConversationHandler, 
    ContextTypes,
    CallbackQueryHandler
)
from asgiref.sync import sync_to_async
from django.utils import timezone
from datetime import datetime
from dotenv import load_dotenv

# Загрузка переменных окружения из .env файла
load_dotenv()

# Инициализация Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "zelen_pro.settings")
django.setup()

from plants.models import Planting, Culture

# Состояния для диалога создания посадки
CULTURE, QUANTITY = range(2)

# Состояния для диалога изменения посадки
EDIT_QUANTITY = 0

# Получение токена из переменных окружения
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

if not TOKEN:
    raise ValueError("Не найден токен бота. Где он?. Убедитесь, что в файле .env указана переменная TELEGRAM_BOT_TOKEN")

@sync_to_async
def get_available_cultures():
    """Получает список доступных культур"""
    return list(Culture.objects.all().order_by('name'))

@sync_to_async
def get_culture_details(culture_id: int):
    """Получает детальную информацию о культуре"""
    try:
        culture = Culture.objects.get(id=culture_id)
        return True, (
            f"*{culture.name}*\n"
            f"├ Срок созревания: {culture.grow_days} дней\n"
            f"├ Срок годности: {culture.expire_days} дней\n"
            f"├ Грамм на лоток: {culture.grams_per_tray} г\n"
            f"├ Замачивание: {'Да' if culture.soaking_required else 'Нет'}\n"
            f"├ Прижим: {culture.press_weight} кг\n"
            f"├ Дней на прорастание: {culture.germination_days}\n"
            f"└ Дней на свету: {culture.light_days}"
        )
    except Culture.DoesNotExist:
        return False, "❌ Культура не найдена"

@sync_to_async
def create_planting(culture_id: int, quantity: int):
    """Создает новую посадку"""
    try:
        culture = Culture.objects.get(id=culture_id)
        planting = Planting.objects.create(
            culture=culture,
            quantity=quantity,
            plant_date=timezone.now().date()  # Используем только дату, без времени
        )
        return True, (
            f"✅ Создана новая посадка:\n"
            f"Культура: {culture.name}\n"
            f"Количество: {quantity}\n"
            f"Дата посадки: {planting.plant_date}\n"
            f"Дата созревания: {planting.harvest_date}\n"
            f"Продать до: {planting.sale_deadline}"
        )
    except Exception as e:
        return False, f"❌ Ошибка при создании посадки: {str(e)}"

@sync_to_async
def get_current_plantings():
    """Получает текущие активные посадки"""
    today = timezone.now().date()  # Используем только дату, без времени
    return list(
        Planting.objects.filter(harvest_date__gte=today)
        .order_by("harvest_date")
        .select_related("culture")
    )

@sync_to_async
def delete_planting(planting_id: int):
    """Удаляет посадку"""
    try:
        planting = Planting.objects.get(id=planting_id)
        culture_name = planting.culture.name
        planting.delete()
        return True, f"✅ Посадка {planting_id} ({culture_name}) удалена"
    except Planting.DoesNotExist:
        return False, "❌ Посадка не найдена"
    except Exception as e:
        return False, f"❌ Ошибка при удалении: {str(e)}"

@sync_to_async
def edit_planting_quantity(planting_id: int, new_quantity: int):
    """Изменяет количество растений в посадке"""
    try:
        planting = Planting.objects.get(id=planting_id)
        old_quantity = planting.quantity
        planting.quantity = new_quantity
        planting.save()
        return True, f"✅ Количество растений изменено с {old_quantity} на {new_quantity}"
    except Planting.DoesNotExist:
        return False, "❌ Посадка не найдена"
    except Exception as e:
        return False, f"❌ Ошибка при изменении: {str(e)}"

@sync_to_async
def get_planting_info(planting_id: int):
    """Получает информацию о посадке"""
    try:
        planting = Planting.objects.select_related('culture').get(id=planting_id)
        return True, planting
    except Planting.DoesNotExist:
        return False, None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    await update.message.reply_text(
        "🌱 *Привет! Я бот для управления микрозеленью.*\n\n"
        "📋 *Доступные команды:*\n"
        "/start - начать работу\n"
        "/current - текущие посадки\n"
        "/new - создать новую посадку\n"
        "/edit [ID] - изменить количество\n"
        "/delete [ID] - удалить посадку\n"
        "/sell [ID] [кол-во] - продать растения\n"
        "/help - справка",
        parse_mode="Markdown"
    )

async def current_plantings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает активные посадки"""
    try:
        plantings = await get_current_plantings()

        if not plantings:
            keyboard = [[InlineKeyboardButton("➕ Добавить посадку", callback_data="new")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                "🌾 Сейчас активных посадок нет.",
                reply_markup=reply_markup
            )
            return

        today = timezone.now().date()
        total = len(plantings)

        # Добавляем кнопку создания новой посадки в начало сообщения
        message = (
            f"🌿 *Текущие посадки* (всего: {total})*\n\n"
        )

        # Отправляем каждую посадку отдельным сообщением с кнопками
        for p in plantings:
            days_left = max((p.harvest_date - today).days, 0)
            sale_deadline = p.sale_deadline.strftime("%Y-%m-%d") if p.sale_deadline else "не указано"
            culture = p.culture

            planting_message = (
                f"▫️ *ID {p.id}: {culture.name}*\n"
                f"├ Посажено: `{p.plant_date}`\n"
                f"├ Количество: {p.quantity} шт.\n"
                f"├ Грамм на лоток: {culture.grams_per_tray} г\n"
                f"├ Замачивание: {'Да' if culture.soaking_required else 'Нет'}\n"
                f"├ Прижим: {culture.press_weight} кг\n"
                f"├ Созреет: `{p.harvest_date}` (*осталось {days_left} дн.*)\n"
                f"├ Продать до: `{sale_deadline}`\n"
                f"└ Статус: _{p.get_status_display()}_"
            )

            # Создаем кнопки для каждой посадки
            keyboard = [
                [
                    InlineKeyboardButton("✏️ Изменить", callback_data=f"edit_{p.id}"),
                    InlineKeyboardButton("🗑 Удалить", callback_data=f"delete_{p.id}")
                ],
                [
                    InlineKeyboardButton("💰 Продать", callback_data=f"sell_{p.id}")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.message.reply_text(
                planting_message,
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )

        # Добавляем кнопку создания новой посадки в конце списка
        keyboard = [[InlineKeyboardButton("➕ Добавить посадку", callback_data="new")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "Добавить новую посадку:",
            reply_markup=reply_markup
        )

    except Exception as e:
        await update.message.reply_text("⚠️ Ошибка при получении данных!")
        print(f"Error: {e}")

@sync_to_async
def sell_plants(planting_id: int, amount: int):
    """Обновляет количество растений после продажи"""
    try:
        planting = Planting.objects.get(id=planting_id)

        if planting.quantity < amount:
            return False, f"Недостаточно растений. Доступно: {planting.quantity}"

        planting.quantity -= amount

        if planting.quantity == 0:
            planting.delete()
            return True, "Весь остаток продан. Посадка удалена."
        else:
            planting.save()
            return True, f"✅ Продано {amount} шт. Осталось: {planting.quantity}"

    except Planting.DoesNotExist:
        return False, "❌ Посадка не найдена"
    except Exception as e:
        return False, f"❌ Ошибка: {str(e)}"

async def sell(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /sell"""
    args = context.args

    if len(args) != 2:
        await update.message.reply_text(
            "❌ *Неверный формат*\n"
            "Используйте: `/sell [ID] [кол-во]`\n"
            "Пример: `/sell 5 10`",
            parse_mode="Markdown"
        )
        return

    try:
        planting_id = int(args[0])
        amount = int(args[1])

        if amount <= 0:
            await update.message.reply_text("⚠️ Количество должно быть больше 0!")
            return

    except ValueError:
        await update.message.reply_text("❌ ID и количество должны быть числами!")
        return

    success, message = await sell_plants(planting_id, amount)
    await update.message.reply_text(message)

async def delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /delete"""
    if not context.args or len(context.args) != 1:
        await update.message.reply_text(
            "❌ *Неверный формат*\n"
            "Используйте: `/delete [ID]`\n"
            "Пример: `/delete 5`",
            parse_mode="Markdown"
        )
        return

    try:
        planting_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ ID должен быть числом!")
        return

    success, message = await delete_planting(planting_id)
    await update.message.reply_text(message, parse_mode="Markdown")

async def edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /edit - начинает процесс изменения количества"""
    if not context.args or len(context.args) != 1:
        await update.message.reply_text(
            "❌ *Неверный формат*\n"
            "Используйте: `/edit [ID]`\n"
            "Пример: `/edit 5`",
            parse_mode="Markdown"
        )
        return

    try:
        planting_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ ID должен быть числом!")
        return

    success, planting = await get_planting_info(planting_id)
    if not success:
        await update.message.reply_text("❌ Посадка не найдена")
        return

    context.user_data['edit_planting_id'] = planting_id
    context.user_data['current_quantity'] = planting.quantity

    await update.message.reply_text(
        f"🌱 *Редактирование посадки:*\n"
        f"ID: {planting.id}\n"
        f"Культура: {planting.culture.name}\n"
        f"Текущее количество: {planting.quantity}\n\n"
        f"Введите новое количество растений:",
        parse_mode="Markdown"
    )
    return EDIT_QUANTITY

async def edit_quantity_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает ввод нового количества при редактировании"""
    try:
        new_quantity = int(update.message.text)
        if new_quantity <= 0:
            await update.message.reply_text("❌ Количество должно быть больше 0!")
            return EDIT_QUANTITY

        planting_id = context.user_data['edit_planting_id']
        success, message = await edit_planting_quantity(planting_id, new_quantity)
        await update.message.reply_text(message)
        return ConversationHandler.END
    except ValueError:
        await update.message.reply_text("❌ Введите число!")
        return EDIT_QUANTITY

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает справку"""
    await update.message.reply_text(
        "📋 *Доступные команды:*\n"
        "/start - начать работу\n"
        "/current - активные посадки\n"
        "/new - создать новую посадку\n"
        "/edit [ID] - изменить количество\n"
        "/delete [ID] - удалить посадку\n"
        "/sell [ID] [кол-во] - продать растения\n"
        "/help - эта справка",
        parse_mode="Markdown"
    )

async def new_planting(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начинает процесс создания новой посадки"""
    cultures = await get_available_cultures()
    if not cultures:
        await update.message.reply_text("❌ Нет доступных культур для посадки!")
        return ConversationHandler.END

    message = "🌱 *Доступные культуры:*\n\n"
    keyboard = []
    
    for c in cultures:
        message += (
            f"*{c.id}: {c.name}*\n"
            f"├ Созревание: {c.grow_days} дней\n"
            f"├ Годность: {c.expire_days} дней\n"
            f"└ Грамм/лоток: {c.grams_per_tray} г\n\n"
        )
        keyboard.append([f"{c.id}: {c.name}"])

    message += "\nВыберите культуру для посадки:"
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
    
    await update.message.reply_text(message, parse_mode="Markdown")
    await update.message.reply_text("Выберите номер культуры:", reply_markup=reply_markup)
    return CULTURE

async def culture_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает выбор культуры"""
    try:
        culture_id = int(update.message.text.split(':')[0])
        context.user_data['culture_id'] = culture_id
        
        # Получаем детальную информацию о выбранной культуре
        success, details = await get_culture_details(culture_id)
        if not success:
            await update.message.reply_text(details)
            return CULTURE
            
        await update.message.reply_text(
            f"Выбрана культура:\n{details}\n\n"
            "Введите количество растений:",
            reply_markup=ReplyKeyboardRemove(),
            parse_mode="Markdown"
        )
        return QUANTITY
    except (ValueError, IndexError):
        await update.message.reply_text("❌ Неверный формат. Попробуйте еще раз.")
        return CULTURE

async def quantity_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает ввод количества растений"""
    try:
        quantity = int(update.message.text)
        if quantity <= 0:
            await update.message.reply_text("❌ Количество должно быть больше 0!")
            return QUANTITY

        success, message = await create_planting(context.user_data['culture_id'], quantity)
        await update.message.reply_text(message)
        return ConversationHandler.END
    except ValueError:
        await update.message.reply_text("❌ Введите число!")
        return QUANTITY

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отменяет создание посадки"""
    await update.message.reply_text(
        "❌ Создание посадки отменено.",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик нажатий на inline-кнопки"""
    query = update.callback_query
    await query.answer()  # Отвечаем на callback query

    if query.data == "new":
        return await new_planting(update, context)
    
    action, planting_id = query.data.split('_')
    
    if action == "edit":
        # Изменяем сообщение на форму редактирования
        success, planting = await get_planting_info(int(planting_id))
        if success:
            context.user_data['edit_planting_id'] = planting.id
            context.user_data['current_quantity'] = planting.quantity
            await query.edit_message_text(
                f"🌱 *Редактирование посадки:*\n"
                f"ID: {planting.id}\n"
                f"Культура: {planting.culture.name}\n"
                f"Текущее количество: {planting.quantity}\n\n"
                f"Введите новое количество растений:",
                parse_mode="Markdown"
            )
            return EDIT_QUANTITY
    
    elif action == "delete":
        success, message = await delete_planting(int(planting_id))
        await query.edit_message_text(
            message,
            parse_mode="Markdown"
        )
    
    elif action == "sell":
        # Показываем форму для ввода количества для продажи
        success, planting = await get_planting_info(int(planting_id))
        if success:
            await query.edit_message_text(
                f"💰 *Продажа растений*\n"
                f"ID: {planting.id}\n"
                f"Культура: {planting.culture.name}\n"
                f"Доступно: {planting.quantity} шт.\n\n"
                f"Используйте команду:\n"
                f"`/sell {planting.id} [количество]`",
                parse_mode="Markdown"
            )

async def get_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"Ваш Chat ID: {update.effective_chat.id}")

def main():
    """Запуск бота"""
    application = Application.builder().token(TOKEN).build()

    # Создаем обработчик диалога создания посадки
    new_planting_handler = ConversationHandler(
        entry_points=[
            CommandHandler("new", new_planting),
            CallbackQueryHandler(button_handler, pattern="^new$")
        ],
        states={
            CULTURE: [MessageHandler(filters.TEXT & ~filters.COMMAND, culture_chosen)],
            QUANTITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, quantity_chosen)],
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )

    # Создаем обработчик диалога изменения количества
    edit_handler = ConversationHandler(
        entry_points=[
            CommandHandler("edit", edit),
            CallbackQueryHandler(button_handler, pattern="^edit_\\d+$")
        ],
        states={
            EDIT_QUANTITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_quantity_chosen)],
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )

    # Регистрация обработчиков
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("current", current_plantings))
    application.add_handler(CommandHandler("sell", sell))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("delete", delete))
    application.add_handler(new_planting_handler)
    application.add_handler(edit_handler)
    
    # Добавляем обработчик для остальных кнопок (delete и sell)
    application.add_handler(CallbackQueryHandler(button_handler))

    # Добавляем обработчик команды get_id
    application.add_handler(CommandHandler('get_id', get_id))

    # Запуск
    application.run_polling()


if __name__ == "__main__":
    main()
