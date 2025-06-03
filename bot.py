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
BALANCES_FILE = "balances.json"
SELL_NAME, SELL_PRICE, SELL_FILE = range(3)

for file in [MARKET_FILE, ORDERS_FILE]:
    if not os.path.exists(file):
        with open(file, 'w') as f:
            json.dump([], f)

if not os.path.exists(BALANCES_FILE):
    with open(BALANCES_FILE, 'w') as f:
        json.dump({}, f)

def load_json(path):
    with open(path, 'r') as f:
        return json.load(f)

def save_json(path, data):
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)

def ensure_balances_file():
    if not os.path.exists(BALANCES_FILE):
        with open(BALANCES_FILE, 'w') as f:
            json.dump({}, f)
    else:
        with open(BALANCES_FILE, 'r+') as f:
            try:
                data = json.load(f)
                if not isinstance(data, dict):
                    raise ValueError
            except (json.JSONDecodeError, ValueError):
                f.seek(0)
                json.dump({}, f)
                f.truncate()

def ensure_user_balance(user_id):
    balances = load_json(BALANCES_FILE)
    if str(user_id) not in balances:
        balances[str(user_id)] = 1000
        save_json(BALANCES_FILE, balances)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ensure_user_balance(update.effective_user.id)
    keyboard = [
        [InlineKeyboardButton("💰 Баланс", callback_data='balance')],
        [InlineKeyboardButton("🛍 Витрина", callback_data='listings')],
        [InlineKeyboardButton("➕ Пополнить баланс", callback_data='topup')],
        [InlineKeyboardButton("📦 Мои предметы", callback_data='myitems')],
        [InlineKeyboardButton("📤 Продать новый", callback_data='sell')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Добро пожаловать в маркет! Выберите действие через меню ниже 👇", reply_markup=reply_markup)

    ensure_user_balance(update.effective_user.id)
    keyboard = [
        [InlineKeyboardButton("💰 Баланс", callback_data='balance')],
        [InlineKeyboardButton("🛍 Витрина", callback_data='listings')],
        [InlineKeyboardButton("➕ Пополнить баланс", callback_data='topup')],
        [InlineKeyboardButton("📦 Мои предметы", callback_data='myitems')],
        [InlineKeyboardButton("📤 Продать новый", callback_data='sell')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Меню:", reply_markup=reply_markup)

async def show_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    ensure_user_balance(user_id)
    balances = load_json(BALANCES_FILE)
    await query.answer()
    await query.edit_message_text(f"Ваш баланс: {balances[str(user_id)]} монет.")

async def top_up(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    ensure_user_balance(user_id)
    balances = load_json(BALANCES_FILE)
    balances[str(user_id)] += 1000
    save_json(BALANCES_FILE, balances)
    await query.answer()
    await query.edit_message_text("Баланс пополнен на 1000 монет.")

async def sell(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Введите название предмета:")
    return SELL_NAME

async def sell_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['item_name'] = update.message.text
    await update.message.reply_text("Введите цену в монетах:")
    return SELL_PRICE
    context.user_data['item_name'] = update.message.text
    await update.message.reply_text("Теперь отправьте файл (документ, фото или видео), представляющий предмет.")
    return SELL_FILE

async def sell_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        price = int(update.message.text)
        if price <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text("Введите корректную положительную цену.")
        return SELL_PRICE

    context.user_data['item_price'] = price
    await update.message.reply_text("Теперь отправьте файл (документ, фото или видео), представляющий предмет.")
    return SELL_FILE

async def sell_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file_id, file_type = None, None
    if update.message.document:
        file_id, file_type = update.message.document.file_id, "document"
    elif update.message.photo:
        file_id, file_type = update.message.photo[-1].file_id, "photo"
    elif update.message.video:
        file_id, file_type = update.message.video.file_id, "video"
    else:
        await update.message.reply_text("Неверный тип файла.")
        return SELL_FILE

    item = {
        "user_id": update.effective_user.id,
        "item_name": context.user_data['item_name'],
        "file_id": file_id,
        "file_type": file_type,
        "price": context.user_data['item_price'],
        "timestamp": datetime.utcnow().isoformat()
    }

    market = load_json(MARKET_FILE)
    market.append(item)
    save_json(MARKET_FILE, market)

    await update.message.reply_text("Предмет выставлен на продажу.", reply_markup=InlineKeyboardMarkup([
    [InlineKeyboardButton("🔙 В меню", callback_data='menu')]
]))
    return ConversationHandler.END

async def listings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    market = load_json(MARKET_FILE)

    if not market:
        await query.edit_message_text("Нет доступных предметов.")
        return

    keyboard = [
        [InlineKeyboardButton(f"Купить: {entry['item_name']}", callback_data=f"buy_{i}")]
        for i, entry in enumerate(market)
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text("Витрина:", reply_markup=reply_markup)
    await query.message.reply_text("Вы можете вернуться в меню:", reply_markup=InlineKeyboardMarkup([
    [InlineKeyboardButton("🔙 В меню", callback_data='menu')]
]))

async def buy_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    index = int(query.data.split("_")[1])
    user_id = query.from_user.id
    ensure_user_balance(user_id)

    market = load_json(MARKET_FILE)
    if index >= len(market):
        await query.edit_message_text("Этот предмет уже недоступен.")
        return

    item = market.pop(index)
    save_json(MARKET_FILE, market)

    orders = load_json(ORDERS_FILE)
    orders.append({
        "buyer_id": user_id,
        "seller_id": item['user_id'],
        "item_name": item['item_name'],
        "file_id": item['file_id'],
        "file_type": item['file_type'],
        "timestamp": datetime.utcnow().isoformat()
    })
    save_json(ORDERS_FILE, orders)

    balances = load_json(BALANCES_FILE)
    if balances[str(user_id)] < 100:
        await query.edit_message_text("Недостаточно средств.")
        return
    balances[str(user_id)] -= 100
    balances[str(item['user_id'])] += 100
    save_json(BALANCES_FILE, balances)

    await query.answer()
    if item['file_type'] == "document":
        await query.message.reply_document(document=item['file_id'], caption=f"Вы купили: {item['item_name']}")
    elif item['file_type'] == "photo":
        await query.message.reply_photo(photo=item['file_id'], caption=f"Вы купили: {item['item_name']}")
    elif item['file_type'] == "video":
        await query.message.reply_video(video=item['file_id'], caption=f"Вы купили: {item['item_name']}")

    await query.edit_message_text("Покупка завершена.")

async def myitems(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    orders = load_json(ORDERS_FILE)

    my_items = [o for o in orders if o['buyer_id'] == user_id]
    if not my_items:
        await query.edit_message_text("У вас нет купленных предметов.")
        return

    keyboard = [
        [InlineKeyboardButton(f"Продать: {item['item_name']}", callback_data=f"resell_{i}")]
        for i, item in enumerate(my_items)
    ]
    context.user_data['resell_list'] = my_items
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text("Мои предметы:", reply_markup=reply_markup)

async def resell_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    index = int(query.data.split("_")[1])
    item = context.user_data.get('resell_list', [])[index]

    item['user_id'] = query.from_user.id
    item['timestamp'] = datetime.utcnow().isoformat()

    market = load_json(MARKET_FILE)
    market.append(item)
    save_json(MARKET_FILE, market)

    await query.answer()
    await query.edit_message_text(f"Предмет '{item['item_name']}' выставлен на продажу.")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data

    if data == 'balance':
        await show_balance(update, context)
    elif data == 'topup':
        await top_up(update, context)
    elif data == 'listings':
        await listings(update, context)
    elif data == 'myitems':
        await myitems(update, context)
    elif data == 'sell':
        await sell(update.callback_query, context)
    elif data == 'menu':
        await start(update, context)
    elif data.startswith('buy_'):
        await buy_callback(update, context)
    elif data.startswith('resell_'):
        await resell_callback(update, context)

def main():
    ensure_balances_file()
    TOKEN = "7710566564:AAGeK5NsObb0uxdbtzbj4Vij5kMB8XUaZvA"
    app = ApplicationBuilder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("sell", sell)],
        states={
            SELL_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, sell_name)],
            SELL_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, sell_price)],
            SELL_FILE: [MessageHandler(filters.ALL & ~filters.COMMAND, sell_file)],
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("balance", show_balance))
    app.add_handler(CallbackQueryHandler(button_handler))

    print("Бот запущен...")
    app.run_polling()

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Операция отменена.")
    return ConversationHandler.END

if __name__ == "__main__":
    main()