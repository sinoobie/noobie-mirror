from threading import Thread
from telegram import InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackQueryHandler

from bot import LOGGER, dispatcher
from bot.helper.mirror_utils.upload_utils.gdriveTools import GoogleDriveHelper
from bot.helper.telegram_helper.message_utils import sendMessage, editMessage, sendMarkup, auto_delete_message
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper import button_build

def list_buttons(update, context):
    user_id = update.message.from_user.id
    if len(update.message.text.split(" ", maxsplit=1)) < 2:
        smsg = sendMessage('ℹ️ Ketik sebuah keyword untuk memulai pencarian!', context.bot, update.message)
        Thread(target=auto_delete_message, args=(context.bot, update.message, smsg)).start()
        return
    buttons = button_build.ButtonMaker()
#    buttons.sbutton("Drive Root", f"types {user_id} root")
#    buttons.sbutton("Recursive", f"types {user_id} recu")
#    buttons.sbutton("Cancel", f"types {user_id} cancel")
    buttons.sbutton("Folder", f"types {user_id} folders root")
    buttons.sbutton("File", f"types {user_id} files root")
    buttons.sbutton("Keduanya", f"types {user_id} both root")
    buttons.sbutton("Cancel", f"types {user_id} cancel")
    button = InlineKeyboardMarkup(buttons.build_menu(2))
    sendMarkup(f'Pilih Opsi untuk memulai pencarian <code>{key}</code>', context.bot, update.message, button)

def select_type(update, context):
    query = update.callback_query
    user_id = query.from_user.id
    msg = query.message
    key = msg.reply_to_message.text.split(" ", maxsplit=1)[1]
    data = query.data
    data = data.split(" ")
    if user_id != int(data[1]):
        query.answer(text="Bukan buat elu!", show_alert=True)
#    elif data[2] in ["root", "recu"]:
#        query.answer()
#        buttons = button_build.ButtonMaker()
#        buttons.sbutton("Folder", f"types {user_id} folders {data[2]}")
#        buttons.sbutton("File", f"types {user_id} files {data[2]}")
#        buttons.sbutton("Keduanya", f"types {user_id} both {data[2]}")
#        buttons.sbutton("Cancel", f"types {user_id} cancel")
#        button = InlineKeyboardMarkup(buttons.build_menu(2))
#        editMessage(f'Pilih Opsi untuk memulai pencarian {key}.', msg, button)
    elif data[2] in ["files", "folders", "both"]:
        query.answer()
        list_method = data[3]
        item_type = data[2]
        editMessage(f"<b>Sedang mencari file </b><code>{key}</code>", msg)
        Thread(target=_list_drive, args=(key, msg, list_method, item_type)).start()
    else:
        query.answer()
        editMessage(f"<b>ℹ️ Pencarian file <code>{key}</code> dibatalkan!</b>", msg)

def _list_drive(key, bmsg, list_method, item_type):
    LOGGER.info(f"listing: {key}")
    list_method = list_method == "recu"
    gdrive = GoogleDriveHelper()
    msg, button = gdrive.drive_list(key, isRecursive=list_method, itemType=item_type)
    if button:
        editMessage(msg, bmsg, button)
    else:
        _tipe = item_type
        if _tipe == "both":
            _tipe = "folders & files"
        editMessage(f'ℹ️ Tidak ada file yang cocok dengan <code>{key}</code>\nList Mode:- <i>{_tipe}</i>', bmsg)

list_handler = CommandHandler(BotCommands.ListCommand, list_buttons, filters=CustomFilters.authorized_chat | CustomFilters.authorized_user, run_async=True)
list_type_handler = CallbackQueryHandler(select_type, pattern="types", run_async=True)
dispatcher.add_handler(list_handler)
dispatcher.add_handler(list_type_handler)
