from random import SystemRandom
from string import ascii_letters, digits
from telegram.ext import CommandHandler
from threading import Thread
from time import sleep, time

from bot.helper.mirror_utils.upload_utils.gdriveTools import GoogleDriveHelper
from bot.helper.telegram_helper.message_utils import sendMessage, sendFile, deleteMessage, delete_all_messages, update_all_messages, sendStatusMessage, auto_delete_message, sendMarkup
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.mirror_utils.status_utils.clone_status import CloneStatus
from bot import dispatcher, LOGGER, CLONE_LIMIT, STOP_DUPLICATE, download_dict, download_dict_lock, Interval
from bot.helper.ext_utils.bot_utils import get_readable_time, get_readable_file_size, is_gdrive_link, is_gdtot_link, new_thread, is_appdrive_link, is_sharerpw_link
from bot.helper.mirror_utils.download_utils.direct_link_generator import gdtot, appdrive, sharerpw
from bot.helper.ext_utils.exceptions import DirectDownloadLinkException


def _clone(message, bot, multi=0):
    args = message.text.split()
    reply_to = message.reply_to_message
    gdrive_sharer = False
    link = ''
    if len(args) > 1:
        link = args[1].strip()
        if link.strip().isdigit():
            multi = int(link)
            link = ''
    if message.from_user.username:
        tag = f"@{message.from_user.username}"
    else:
        tag = message.from_user.mention_html(message.from_user.first_name)
    if reply_to:
        if len(link) == 0:
            link = reply_to.text.split(maxsplit=1)[0].strip()
        if not reply_to.from_user.is_bot:
            if reply_to.from_user.username:
                tag = f"@{reply_to.from_user.username}"
            else:
                tag = reply_to.from_user.mention_html(reply_to.from_user.first_name)
    if multi == 0:
        _msg = sendMessage(f"♻️ {tag} Cloning: <code>{link}</code>", bot, message)
    else: _msg = None
    try:
        if is_gdtot := is_gdtot_link(link):
            link = gdtot(link)
            gdrive_sharer = True
        elif is_appdrive := is_appdrive_link(link):
            link = appdrive(link)
            gdrive_sharer = True
        elif is_sharerpw := is_sharerpw_link(link):
            link = sharerpw(link)
            gdrive_sharer = True
    except DirectDownloadLinkException as e:
        if _msg:
            deleteMessage(bot, _msg)
        return sendMessage(f"⚠️ {tag} {e}", bot, message)
    if is_gdrive_link(link):
        gd = GoogleDriveHelper()
        res, size, name, files = gd.helper(link)
        if res != "":
            if _msg:
                deleteMessage(bot, _msg)
            return sendMessage(f"⚠️ {tag} {res}", bot, message)
        if STOP_DUPLICATE:
            LOGGER.info('Checking File/Folder if already in Drive...')
            cap, f_name = gd.drive_list(name, True, True)
            if cap:
                if _msg:
                    deleteMessage(bot, _msg)
                dupmsg = f"⚠️ {tag} Download kamu dihentikan karena: <code>{name}</code> <b><u>sudah ada di Drive</u></b>"
                sendFile(bot, message, f_name, dupmsg)
                return
        if CLONE_LIMIT is not None:
            LOGGER.info('Checking File/Folder Size...')
            if size > CLONE_LIMIT * 1024**3:
                if _msg:
                    deleteMessage(bot, _msg)
                msg2 = f'⚠️ {tag} Gagal, Clone limit adalah {CLONE_LIMIT}GB.\nUkuran File/Folder kamu adalah {get_readable_file_size(size)}.'
                return sendMessage(msg2, bot, message)
        if multi > 1:
            sleep(4)
            nextmsg = type('nextmsg', (object, ), {'chat_id': message.chat_id, 'message_id': message.reply_to_message.message_id + 1})
            nextmsg = sendMessage(args[0], bot, nextmsg)
            nextmsg.from_user.id = message.from_user.id
            multi -= 1
            sleep(4)
            Thread(target=_clone, args=(nextmsg, bot, multi)).start()
        if files <= 20:
            result, button = gd.clone(link)
        else:
            drive = GoogleDriveHelper(name)
            gid = ''.join(SystemRandom().choices(ascii_letters + digits, k=12))
            clone_status = CloneStatus(drive, size, message, gid)
            with download_dict_lock:
                download_dict[message.message_id] = clone_status
            sendStatusMessage(message, bot)
            result, button = drive.clone(link)
            with download_dict_lock:
                del download_dict[message.message_id]
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
        if _msg:
            deleteMessage(bot, _msg)
        cc = f'\n⏱ <b>Selesai Dalam: </b>{get_readable_time(time() - message.date.timestamp())}'
        cc += f'\n\n👤 <b>Pemirror: </b>{tag}'
        if not reply_to or reply_to.from_user.is_bot:
            cc += f'\n#️⃣ <b>UID: </b><code>{message.from_user.id}</code>'
        else:
            cc += f'\n#️⃣ <b>UID: </b><code>{reply_to.from_user.id}</code>'
        if button in ["cancelled", ""]:
            sendMessage(f"⚠️ {tag} {result}", bot, message)
        else:
            sendMarkup(result + cc, bot, message, button)
            LOGGER.info(f'Cloning Done: {name}')
        if gdrive_sharer:
            gd.deletefile(link)
    else:
        if _msg:
            deleteMessage(bot, _msg)
        smsg = sendMessage(f'ℹ️ Ketik Gdrive/gdtot/appdrive/sharerpw link yang mau di-mirror.', bot, message)
        Thread(target=auto_delete_message, args=(bot, message, smsg)).start()

@new_thread
def cloneNode(update, context):
    _clone(update.message, context.bot)

clone_handler = CommandHandler(BotCommands.CloneCommand, cloneNode, filters=CustomFilters.authorized_chat | CustomFilters.authorized_user, run_async=True)
dispatcher.add_handler(clone_handler)
