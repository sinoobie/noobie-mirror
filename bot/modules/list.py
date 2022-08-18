from threading import Thread
from telegram.ext import CommandHandler

from bot import LOGGER, dispatcher
from bot.helper.mirror_utils.upload_utils.gdriveTools import GoogleDriveHelper
from bot.helper.telegram_helper.message_utils import sendMessage, editMessage, auto_delete_message, sendFile, deleteMessage
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.bot_commands import BotCommands

def list_drives(update, context):
    try:
        key = update.message.text.split(" ", maxsplit=1)[1]
        LOGGER.info(f"listing: {key}")
        bmsg = sendMessage(f"ℹ️ <b>Sedang mencari file</b> <code>{key}</code>", context.bot, update.message)
        gdrive = GoogleDriveHelper()
        cap, f_name = gdrive.drive_list(key, isRecursive=True)
        if cap:
            deleteMessage(context.bot, bmsg)
            sendFile(context.bot, bmsg.reply_to_message, f_name, cap)
        else:
            editMessage(f'ℹ️ <b>Tidak ada file yang cocok dengan</b> <code>{key}</code>', bmsg)
    except Exception as err:
        LOGGER.error(f"listing error: {err}")
        bmsg = sendMessage('⚠️ <b>Ketik sebuah keyword untuk memulai pencarian!</b>', context.bot, update.message)
        Thread(target=auto_delete_message, args=(context.bot, update.message, bmsg)).start()

list_handler = CommandHandler(BotCommands.ListCommand, list_drives, filters=CustomFilters.authorized_chat | CustomFilters.authorized_user, run_async=True)
dispatcher.add_handler(list_handler)