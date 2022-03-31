import random
import string

from telegram.ext import CommandHandler
from threading import Thread

from bot.helper.mirror_utils.upload_utils.gdriveTools import GoogleDriveHelper
from bot.helper.telegram_helper.message_utils import sendMessage, sendMarkup, deleteMessage, delete_all_messages, update_all_messages, sendStatusMessage, auto_delete_message
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.mirror_utils.status_utils.clone_status import CloneStatus
from bot import dispatcher, LOGGER, CLONE_LIMIT, STOP_DUPLICATE, download_dict, download_dict_lock, Interval
from bot.helper.ext_utils.bot_utils import get_readable_file_size, is_gdrive_link, is_gdtot_link, new_thread
from bot.helper.mirror_utils.download_utils.direct_link_generator import gdtot
from bot.helper.ext_utils.exceptions import DirectDownloadLinkException

@new_thread
def cloneNode(update, context):
    args = update.message.text.split(" ", maxsplit=1)
    reply_to = update.message.reply_to_message
    link = ''
    if len(args) > 1:
        link = args[1]
        if update.message.from_user.username:
            tag = f"@{update.message.from_user.username}"
        else:
            tag = update.message.from_user.mention_html(update.message.from_user.first_name)
    if reply_to is not None:
        if len(link) == 0:
            link = reply_to.text
        if reply_to.from_user.username:
            tag = f"@{reply_to.from_user.username}"
        else:
            tag = reply_to.from_user.mention_html(reply_to.from_user.first_name)
    is_gdtot = is_gdtot_link(link)
    if is_gdtot:
        try:
            _msg = sendMessage(f"ℹ️ {tag} Processing: <code>{link}</code>", context.bot, update.message)
            link = gdtot(link)
            deleteMessage(context.bot, _msg)
        except DirectDownloadLinkException as e:
            deleteMessage(context.bot, _msg)
            return sendMessage(f"⚠️ {tag} {e}", context.bot, update.message)
    if is_gdrive_link(link):
        _msg = sendMessage(f"ℹ️ {tag} Cloning: <code>{link}</code>", context.bot, update.message)
        gd = GoogleDriveHelper()
        res, size, name, files = gd.helper(link)
        if res != "":
            deleteMessage(context.bot, _msg)
            return sendMessage(f"⚠️ {tag} {res}", context.bot, update.message)
        if STOP_DUPLICATE:
            LOGGER.info('Checking File/Folder if already in Drive...')
            smsg, button = gd.drive_list(name, True, True)
            if smsg:
                msg3 = f"⚠️ {tag} <code>{name}</code> sudah ada di Drive."
                deleteMessage(context.bot, _msg)
                return sendMarkup(msg3, context.bot, update.message, button)
        if CLONE_LIMIT is not None:
            LOGGER.info('Checking File/Folder Size...')
            if size > CLONE_LIMIT * 1024**3:
                msg2 = f'⚠️ {tag} Gagal, Clone limit adalah {CLONE_LIMIT}GB.\nUkuran File/Folder kamu adalah {get_readable_file_size(size)}.'
                deleteMessage(context.bot, _msg)
                return sendMessage(msg2, context.bot, update.message)
        if files <= 20:
            result, button = gd.clone(link)
        else:
            drive = GoogleDriveHelper(name)
            gid = ''.join(random.SystemRandom().choices(string.ascii_letters + string.digits, k=12))
            clone_status = CloneStatus(drive, size, update.message, gid)
            with download_dict_lock:
                download_dict[update.message.message_id] = clone_status
            sendStatusMessage(update.message, context.bot)
            result, button = drive.clone(link)
            with download_dict_lock:
                del download_dict[update.message.message_id]
                count = len(download_dict)
            try:
                if count == 0:
                    Interval[0].cancel()
                    del Interval[0]
                    delete_all_messages()
                else:
                    update_all_messages()
            except IndexError:
                pass
        deleteMessage(context.bot, _msg)
        cc = f'\n\n👤 <b>Pemirror: </b>{tag}'
        if reply_to is not None:
            cc += f'\n#️⃣ <b>UID: </b><code>{reply_to.from_user.id}</code>'
        else: cc += f'\n#️⃣ <b>UID: </b><code>{update.message.from_user.id}</code>'
        if button in ["cancelled", ""]:
            sendMessage(f"⚠️ {tag} {result}", context.bot, update.message)
        else:
            sendMarkup(result + cc, context.bot, update.message, button)
        if is_gdtot:
            gd.deletefile(link)
        deleteMessage(context.bot, update.message)
    else:
        smsg = sendMessage(f'ℹ️ {tag} Ketik Gdrive atau gdtot link yang mau di-mirror.', context.bot, update.message)
        Thread(target=auto_delete_message, args=(context.bot, update.message, smsg)).start()

clone_handler = CommandHandler(BotCommands.CloneCommand, cloneNode, filters=CustomFilters.authorized_chat | CustomFilters.authorized_user, run_async=True)
dispatcher.add_handler(clone_handler)
