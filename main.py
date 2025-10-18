# -*- coding: utf-8 -*-
"""
main.py - Core runner for Telegram Account Selling Bot
Stage: core launcher (imports modules/*.py)
Author: GTR_SADIK (custom)
"""

import os
import sys
import traceback
from dotenv import load_dotenv

# load .env (if exists)
load_dotenv()

# -------------------------
# Configuration (from .env or defaults you provided)
# -------------------------
BOT_TOKEN = os.getenv("BOT_TOKEN", "7733074141:AAHYuk7ws3x3elc-Hb7atNqR9uJUbxyyZjM")
ADMIN_IDS_ENV = os.getenv("ADMIN_IDS", os.getenv("ADMIN_ID", "7933487472"))
# ADMIN_IDS may be comma-separated
ADMIN_IDS = [int(x.strip()) for x in ADMIN_IDS_ENV.split(",") if x.strip().isdigit()]

LOG_CHANNEL = int(os.getenv("LOG_CHANNEL", "-1003191717687"))
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///database/sellerbot.db")
# ensure DB file path (remove sqlite:/// prefix for local path usage)
DB_FILEPATH = DATABASE_URL.replace("sqlite:///", "") if DATABASE_URL.startswith("sqlite:///") else DATABASE_URL
DOWNLOAD_BASE_URL = os.getenv("DOWNLOAD_BASE_URL", "https://market.gtrsadik.shop/files")

# -------------------------
# Safe check for token
# -------------------------
if not BOT_TOKEN or ":" not in BOT_TOKEN:
    print("ERROR: BOT_TOKEN missing or invalid. Set BOT_TOKEN in .env")
    sys.exit(1)

# -------------------------
# Imports (telebot initialized here to allow modules to use it)
# -------------------------
try:
    from telebot import TeleBot
    from telebot import types
except Exception as e:
    print("ERROR: 'pyTelegramBotAPI' not installed. Run: pip install pytelegrambotapi")
    raise

bot = TeleBot(BOT_TOKEN, parse_mode="HTML")

# -------------------------
# Try to import components from modules/
# -------------------------
MODULES_PRESENT = True
try:
    # database helper (should provide init_db(), get_connection() etc.)
    import modules.database as database_module
except Exception:
    database_module = None
    MODULES_PRESENT = False
    print("Warning: modules.database not found. Create modules/database.py next.")

try:
    import modules.utils as utils_module
except Exception:
    utils_module = None
    MODULES_PRESENT = False
    print("Warning: modules.utils not found. Create modules/utils.py next.")

try:
    import modules.user as user_module
except Exception:
    user_module = None
    MODULES_PRESENT = False
    print("Warning: modules.user not found. Create modules/user.py next.")

try:
    import modules.admin as admin_module
except Exception:
    admin_module = None
    MODULES_PRESENT = False
    print("Warning: modules.admin not found. Create modules/admin.py next.")

# -------------------------
# Initialize DB (if module exists)
# -------------------------
if database_module:
    try:
        # database_module should implement init_db(db_path) or init_db()
        if hasattr(database_module, "init_db"):
            # prefer init_db(DB_FILEPATH) if signature supports path
            try:
                database_module.init_db(DB_FILEPATH)
            except TypeError:
                database_module.init_db()
        else:
            print("modules.database exists but has no init_db(). Ensure it defines init_db().")
    except Exception:
        traceback.print_exc()
        print("Failed to initialize DB via modules.database.init_db()")

# -------------------------
# /start handler (delegates to user module if present)
# -------------------------
@bot.message_handler(commands=["start"])
def handle_start(message):
    try:
        if user_module and hasattr(user_module, "handle_start"):
            return user_module.handle_start(bot, message, ADMIN_IDS, DOWNLOAD_BASE_URL)
        # fallback simple start
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🛒 Browse Products", callback_data="browse"))
        markup.add(types.InlineKeyboardButton("👤 Profile", callback_data="profile"))
        if message.from_user.id in ADMIN_IDS and admin_module and hasattr(admin_module, "admin_panel_keyboard"):
            markup.add(types.InlineKeyboardButton("🛠 Admin Panel", callback_data="admin"))
        bot.send_message(message.chat.id,
                         "⚡️ Welcome to the Telegram Account Selling Bot!\n\nModules not loaded fully. Please add modules/ files.",
                         reply_markup=markup)
    except Exception:
        traceback.print_exc()
        bot.send_message(message.chat.id, "An error occurred while processing /start.")

# -------------------------
# Generic callback handler that delegates to user/admin modules
# -------------------------
@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    data = call.data or ""
    try:
        # Admin callbacks take precedence if user is admin and admin module exists
        if call.from_user and call.from_user.id in ADMIN_IDS and admin_module and hasattr(admin_module, "handle_admin_callback"):
            handled = admin_module.handle_admin_callback(bot, call, ADMIN_IDS, DOWNLOAD_BASE_URL, DB_FILEPATH, LOG_CHANNEL)
            if handled:
                return
        # Delegate to user module
        if user_module and hasattr(user_module, "handle_user_callback"):
            handled = user_module.handle_user_callback(bot, call, ADMIN_IDS, DOWNLOAD_BASE_URL, DB_FILEPATH, LOG_CHANNEL)
            if handled:
                return
        # Fallback simple handler
        if data == "browse":
            bot.answer_callback_query(call.id, "Browse not available yet (modules missing).")
        elif data == "profile":
            bot.answer_callback_query(call.id, "Profile not available yet (modules missing).")
        elif data == "admin":
            bot.answer_callback_query(call.id, "Admin panel not available yet (modules missing).")
        else:
            bot.answer_callback_query(call.id, "Action not implemented (modules missing).")
    except Exception:
        traceback.print_exc()
        try:
            bot.answer_callback_query(call.id, "Internal error.")
        except:
            pass

# -------------------------
# Simple error handler for messages
# -------------------------
@bot.message_handler(func=lambda m: True)
def catch_all_messages(message):
    # Let user module attempt to handle (e.g., step handlers)
    try:
        if user_module and hasattr(user_module, "handle_message"):
            handled = user_module.handle_message(bot, message, ADMIN_IDS, DOWNLOAD_BASE_URL, DB_FILEPATH, LOG_CHANNEL)
            if handled:
                return
    except Exception:
        traceback.print_exc()
    # fallback
    if message.text and message.text.startswith("/"):
        bot.send_message(message.chat.id, "Unknown command. Use /start.")
    else:
        bot.send_message(message.chat.id, "I received your message. Modules not fully installed to handle it.")

# -------------------------
# Start polling
# -------------------------
def main():
    print("Starting main bot...")
    print(f"Admin IDs: {ADMIN_IDS}")
    print(f"Log Channel: {LOG_CHANNEL}")
    print(f"Database path: {DB_FILEPATH}")
    print(f"Download base URL: {DOWNLOAD_BASE_URL}")
    try:
        bot.infinity_polling(timeout=60, long_polling_timeout=60)
    except KeyboardInterrupt:
        print("Stopping bot (KeyboardInterrupt).")
    except Exception:
        traceback.print_exc()

if __name__ == "__main__":
    main()
