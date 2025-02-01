import os
import django
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from asgiref.sync import sync_to_async
from django.utils import timezone  # Добавьте этот импорт!

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zelen_pro.settings')
django.setup()

from plants.models import Planting

TOKEN = "5447861520:AAHeBhte_6lCeo8fPqh1o3haymFAXCF-c6g"

@sync_to_async
def get_current_plantings():
    """Асинхронно получает текущие посадки"""
    today = timezone.now().date()
    return list(
        Planting.objects.filter(harvest_date__gte=today)
        .order_by("harvest_date")
        .select_related("culture")
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    await update.message.reply_text(
        "🌱 Привет! Я бот для управления микрозеленью.\n\n"
        "Доступные команды:\n"
        "/current - текущие посадки\n"
        "/help - справка"
    )


async def current_plantings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает активные посадки"""
    try:
        plantings = await get_current_plantings()

        if not plantings:
            await update.message.reply_text("🌾 Сейчас активных посадок нет.")
            return

        today = timezone.now().date()
        message = "🌿 *Текущие посадки:*\n\n"

        for p in plantings:
            days_left = (p.harvest_date - today).days
            message += (
                f"▫️ *{p.culture.name}*\n"
                f"├ Посажено: `{p.plant_date}`\n"
                f"├ Созреет: `{p.harvest_date}` (*осталось {days_left} дн.*)\n"
                f"├ Продать до: `{p.sale_deadline}`\n"
                f"└ Статус: _{p.get_status_display()}_\n\n"
            )

        await update.message.reply_text(message, parse_mode="Markdown")

    except Exception as e:
        await update.message.reply_text("⚠️ Ошибка при получении данных!")
        print(f"Error: {e}")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает справку"""
    await update.message.reply_text(
        "📋 *Доступные команды:*\n"
        "/start - начать работу\n"
        "/current - активные посадки\n"
        "/help - эта справка",
        parse_mode="Markdown"
    )


def main():
    """Запуск бота"""
    application = Application.builder().token(TOKEN).build()

    # Регистрация обработчиков
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("current", current_plantings))
    application.add_handler(CommandHandler("help", help_command))

    # Запуск
    application.run_polling()


if __name__ == "__main__":
    main()