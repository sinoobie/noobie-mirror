from threading import Thread
from telegram import InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackQueryHandler

from bot import LOGGER, dispatcher
from bot.helper.mirror_utils.upload_utils.gdriveTools import GoogleDriveHelper
from bot.helper.telegram_helper.message_utils import sendMessage, editMessage, sendMarkup, auto_delete_message
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper import button_build

def list_drives(update, context):
    try:
        key = update.message.text.split(" ", maxsplit=1)[1]
        LOGGER.info(f"listing: {key}")
        smsg = sendMessage(f"ℹ️ <b>Sedang mencari file</b> <code>{key}</code>", context.bot, update.message)
        gdrive = GoogleDriveHelper()
        msg, button = gdrive.drive_list(key, isRecursive=True)
        if button:
            editMessage(msg, smsg, button)
        else:
            editMessage(f'ℹ️ <b>Tidak ada file yang cocok dengan</b> <code>{key}</code>', smsg)
    except:
        smsg = sendMessage('⚠️ <b>Ketik sebuah keyword untuk memulai pencarian!</b>', context.bot, update.message)
        Thread(target=auto_delete_message, args=(context.bot, update.message, smsg)).start()

list_handler = CommandHandler(BotCommands.ListCommand, list_drives, filters=CustomFilters.authorized_chat | CustomFilters.authorized_user, run_async=True)
dispatcher.add_handler(list_handler)