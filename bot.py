import json
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    filters, ContextTypes, CallbackQueryHandler, ConversationHandler
)
from datetime import datetime

MARKET_FILE = "market.json"
ORDERS_FILE = "orders.json"
SELL_NAME, SELL_FILE = range(2)

for file in [MARKET_FILE, ORDERS_FILE]:
    if not os.path.exists(file):
        with open(file, 'w') as f:
            json.dump([], f)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Добро пожаловать! Используйте /sell для продажи и /listings для покупки.")

async def sell(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Введите название предмета:")
    return SELL_NAME

async def sell_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['item_name'] = update.message.text
    await update.message.reply_text("Теперь отправьте файл (документ, фото или видео), представляющий предмет.")
    return SELL_FILE

async def sell_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file_id = None
    file_type = None

    if update.message.document:
        file_id = update.message.document.file_id
        file_type = "document"
    elif update.message.photo:
        file_id = update.message.photo[-1].file_id
        file_type = "photo"
    elif update.message.video:
        file_id = update.message.video.file_id
        file_type = "video"
    else:
        await update.message.reply_text("Пожалуйста, отправьте документ, фото или видео.")
        return SELL_FILE

    item = {
        "user_id": update.effective_user.id,
        "item_name": context.user_data['item_name'],
        "file_id": file_id,
        "file_type": file_type,
        "timestamp": datetime.utcnow().isoformat()
    }

    with open(MARKET_FILE, 'r+') as f:
        market = json.load(f)
        market.append(item)
        f.seek(0)
        json.dump(market, f, indent=2)
        f.truncate()

    await update.message.reply_text("Предмет успешно выставлен!")
    return ConversationHandler.END

async def listings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    with open(MARKET_FILE, 'r') as f:
        market = json.load(f)

    if not market:
        await update.message.reply_text("Нет доступных предметов.")
        return

    keyboard = [
        [InlineKeyboardButton(f"Купить: {entry['item_name']}", callback_data=str(i))]
        for i, entry in enumerate(market)
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Витрина товаров:", reply_markup=reply_markup)

async def handle_buy_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    index = int(query.data)

    with open(MARKET_FILE, 'r+') as f:
        market = json.load(f)
        if index >= len(market):
            await query.edit_message_text("Этот предмет уже недоступен.")
            return
        item = market.pop(index)
        f.seek(0)
        json.dump(market, f, indent=2)
        f.truncate()

    with open(ORDERS_FILE, 'r+') as f:
        orders = json.load(f)
        orders.append({
            "buyer_id": query.from_user.id,
            "seller_id": item['user_id'],
            "item_name": item['item_name'],
            "timestamp": datetime.utcnow().isoformat()
        })
        f.seek(0)
        json.dump(orders, f, indent=2)
        f.truncate()

    caption = f"Вы купили: {item['item_name']}"
    if item['file_type'] == "document":
        await query.message.reply_document(document=item['file_id'], caption=caption)
    elif item['file_type'] == "photo":
        await query.message.reply_photo(photo=item['file_id'], caption=caption)
    elif item['file_type'] == "video":
        await query.message.reply_video(video=item['file_id'], caption=caption)
    else:
        await query.message.reply_text(caption)

    await query.edit_message_text("Покупка завершена.")

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Операция отменена.")
    return ConversationHandler.END

def main():
    TOKEN = "7710566564:AAGeK5NsObb0uxdbtzbj4Vij5kMB8XUaZvA"
    app = ApplicationBuilder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("sell", sell)],
        states={
            SELL_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, sell_name)],
            SELL_FILE: [MessageHandler(filters.ALL & ~filters.COMMAND, sell_file)],
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("listings", listings))
    app.add_handler(CallbackQueryHandler(handle_buy_callback))

    print("Бот запущен...")
    app.run_polling()

if __name__ == "__main__":
    main()
