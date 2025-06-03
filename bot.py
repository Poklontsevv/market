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
SELL_NAME, SELL_PRICE = range(2)

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
    item = {
        "user_id": update.effective_user.id,
        "item_name": context.user_data['item_name'],
        "price": context.user_data['item_price'],
        "timestamp": datetime.utcnow().isoformat()
    }
    market = load_json(MARKET_FILE)
    market.append(item)
    save_json(MARKET_FILE, market)
    await update.message.reply_text("Предмет выставлен на продажу.", reply_markup=back_keyboard)
    return ConversationHandler.END

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
    item = {
        "user_id": update.effective_user.id,
        "item_name": context.user_data['item_name'],
        "price": context.user_data['item_price'],
        "timestamp": datetime.utcnow().isoformat()
    }
    market = load_json(MARKET_FILE)
    market.append(item)
    save_json(MARKET_FILE, market)
    await update.message.reply_text("Предмет выставлен на продажу.", reply_markup=back_keyboard)
    return ConversationHandler.END
