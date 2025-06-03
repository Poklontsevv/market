import json
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    filters, ContextTypes, CallbackQueryHandler, ConversationHandler
)

MARKET_FILE = "market.json"
ORDERS_FILE = "orders.json"
SELL_NAME, SELL_PRICE = range(2)

for file in [MARKET_FILE, ORDERS_FILE]:
    if not os.path.exists(file):
        with open(file, 'w') as f:
            json.dump([], f)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Добро пожаловать в маркет! Используйте /sell, /buy, /listings или /myitems.")

async def sell(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Введите название предмета:")
    return SELL_NAME

async def sell_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['item_name'] = update.message.text
    await update.message.reply_text("Введите цену:")
    return SELL_PRICE

async def sell_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        price = float(update.message.text)
    except ValueError:
        await update.message.reply_text("Введите корректную цену.")
        return SELL_PRICE

    item = {
        "user_id": update.effective_user.id,
        "item_name": context.user_data['item_name'],
        "price": price
    }

    with open(MARKET_FILE, 'r+') as f:
        market = json.load(f)
        market.append(item)
        f.seek(0)
        json.dump(market, f, indent=2)
        f.truncate()

    await update.message.reply_text("Предмет выставлен на продажу!")
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Операция отменена.")
    return ConversationHandler.END

async def listings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    with open(MARKET_FILE, 'r') as f:
        market = json.load(f)

    if not market:
        await update.message.reply_text("В маркете пока нет предметов.")
        return

    msg = "\n".join([f"{i + 1}. {item['item_name']} — {item['price']} монет" for i, item in enumerate(market)])
    await update.message.reply_text(msg)

async def myitems(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    with open(MARKET_FILE, 'r') as f:
        market = json.load(f)

    items = [item for item in market if item['user_id'] == user_id]

    if not items:
        await update.message.reply_text("Вы не выставляли предметов.")
        return

    msg = "\n".join([f"{i + 1}. {item['item_name']} — {item['price']} монет" for i, item in enumerate(items)])
    await update.message.reply_text(msg)

async def buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    with open(MARKET_FILE, 'r') as f:
        market = json.load(f)

    if not market:
        await update.message.reply_text("Нет доступных предметов для покупки.")
        return

    keyboard = [
        [InlineKeyboardButton(f"{item['item_name']} - {item['price']} монет", callback_data=str(i))]
        for i, item in enumerate(market)
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Выберите предмет для покупки:", reply_markup=reply_markup)

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

    order = {
        "buyer_id": query.from_user.id,
        "item_name": item['item_name'],
        "price": item['price'],
        "seller_id": item['user_id']
    }

    with open(ORDERS_FILE, 'r+') as f:
        orders = json.load(f)
        orders.append(order)
        f.seek(0)
        json.dump(orders, f, indent=2)
        f.truncate()

    await query.edit_message_text(f"Вы купили: {item['item_name']} за {item['price']} монет.")

def main():
    TOKEN = "7710566564:AAGeK5NsObb0uxdbtzbj4Vij5kMB8XUaZvA"

    app = ApplicationBuilder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("sell", sell)],
        states={
            SELL_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, sell_name)],
            SELL_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, sell_price)],
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("listings", listings))
    app.add_handler(CommandHandler("myitems", myitems))
    app.add_handler(CommandHandler("buy", buy))
    app.add_handler(CallbackQueryHandler(handle_buy_callback))

    print("Бот запущен...")
    app.run_polling()

if __name__ == "__main__":
    main()
