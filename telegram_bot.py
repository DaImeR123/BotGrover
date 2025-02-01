import os
import django
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from asgiref.sync import sync_to_async
from django.utils import timezone

# Инициализация Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "zelen_pro.settings")
django.setup()

from plants.models import Planting

TOKEN = "5447861520:AAHeBhte_6lCeo8fPqh1o3haymFAXCF-c6g"  # Замените на ваш токен


@sync_to_async
def get_current_plantings():
    """Получает текущие активные посадки"""
    today = timezone.now().date()
    return list(
        Planting.objects.filter(harvest_date__gte=today)
        .order_by("harvest_date")
        .select_related("culture")
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    await update.message.reply_text(
        "🌱 *Привет! Я бот для управления микрозеленью.*\n\n"
        "📋 *Доступные команды:*\n"
        "/start - начать работу\n"
        "/current - текущие посадки\n"
        "/sell [ID] [кол-во] - продать растения\n"
        "/help - справка",
        parse_mode="Markdown"
    )


async def current_plantings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает активные посадки"""
    try:
        plantings = await get_current_plantings()

        if not plantings:
            await update.message.reply_text("🌾 Сейчас активных посадок нет.")
            return

        today = timezone.now().date()
        total = len(plantings)

        message = (
            f"🌿 *Текущие посадки* (всего: {total}):\n\n"
            "⚠️ *Используйте ID для продажи*\n\n"
        )

        for p in plantings:
            days_left = max((p.harvest_date - today).days, 0)
            sale_deadline = p.sale_deadline.strftime("%Y-%m-%d") if p.sale_deadline else "не указано"

            message += (
                f"▫️ *ID {p.id}: {p.culture.name}*\n"
                f"├ Посажено: `{p.plant_date}`\n"
                f"├ Количество: {p.quantity} шт.\n"
                f"├ Созреет: `{p.harvest_date}` (*осталось {days_left} дн.*)\n"
                f"├ Продать до: `{sale_deadline}`\n"
                f"└ Статус: _{p.get_status_display()}_\n\n"
            )

        await update.message.reply_text(message, parse_mode="Markdown")

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


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает справку"""
    await update.message.reply_text(
        "📋 *Доступные команды:*\n"
        "/start - начать работу\n"
        "/current - активные посадки\n"
        "/sell [ID] [кол-во] - продать растения\n"
        "/help - эта справка",
        parse_mode="Markdown"
    )


def main():
    """Запуск бота"""
    application = Application.builder().token(TOKEN).build()

    # Регистрация обработчиков
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("current", current_plantings))
    application.add_handler(CommandHandler("sell", sell))
    application.add_handler(CommandHandler("help", help_command))

    # Запуск
    application.run_polling()


if __name__ == "__main__":
    main()