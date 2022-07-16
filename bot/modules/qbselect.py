from threading import Thread

from telegram import InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackQueryHandler

from bot import BASE_URL, download_dict, dispatcher, download_dict_lock, WEB_PINCODE, SUDO_USERS, OWNER_ID
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import sendMessage, sendMarkup, sendStatusMessage, auto_delete_message
from bot.helper.ext_utils.bot_utils import getDownloadByGid, MirrorStatus
from bot.helper.telegram_helper import button_build

def select(update, context):
    tag = update.message.from_user.mention_html(update.message.from_user.first_name)
    user_id = update.message.from_user.id
    if len(context.args) == 1:
        gid = context.args[0]
        dl = getDownloadByGid(gid)
        if not dl:
            sendMessage(f"⚠️ {tag} GID: <code>{gid}</code> Tidak Ditemukan.", context.bot, update.message)
            return
    elif update.message.reply_to_message:
        mirror_message = update.message.reply_to_message
        with download_dict_lock:
            if mirror_message.message_id in download_dict:
                dl = download_dict[mirror_message.message_id]
            else:
                dl = None
        if not dl:
            sendMessage(f"⚠️ {tag} Task ini sudah tidak aktif!", context.bot, update.message)
            return
    elif len(context.args) == 0:
        msg = "Balas perintah aktif /qb yang digunakan untuk memulai qb-download atau menambahkan id download bersama dengan perintah ini\n\n"
        msg += "Perintah ini terutama untuk pemilihan jika Anda memutuskan untuk memilih file dari qb-torrent yang sudah ditambahkan, "
        msg += "Tetapi kamu juga dapat menggunakan perintah /qb dengan arg `s` untuk memilih file sebelum pengunduhan dimulai."
        smsg = sendMessage(msg, context.bot, update.message)
        Thread(target=auto_delete_message, args=(context.bot, update.message, smsg)).start()
        return

    if OWNER_ID != user_id and dl.message.from_user.id != user_id and user_id not in SUDO_USERS:
        tmsg = sendMessage(f"⚠️ {tag} Task ini bukan buat elu!", context.bot, update.message)
        Thread(target=auto_delete_message, args=(context.bot, update.message, tmsg)).start()
        return

    if dl.status() != MirrorStatus.STATUS_DOWNLOADING:
        tmsg = sendMessage(f"⚠️ {tag} Task harus dalam status downloading!", context.bot, update.message)
        Thread(target=auto_delete_message, args=(context.bot, update.message, tmsg)).start()
        return
    if dl.name().endswith('[METADATA]'):
        tmsg = sendMessage(f"⚠️ {tag} Coba lagi setelah downloading METADATA selesai!", context.bot, update.message)
        Thread(target=auto_delete_message, args=(context.bot, update.message, tmsg)).start()
        return
    try:
        hash_ = dl.download().ext_hash
        client = dl.client()
    except:
        tmsg = sendMessage(f"⚠️ {tag} Task ini tidak dimulai dengan qBittorrent!", context.bot, update.message)
        Thread(target=auto_delete_message, args=(context.bot, update.message, tmsg)).start()
        return

    client.torrents_pause(torrent_hashes=hash_)
    pincode = ""
    for n in str(hash_):
        if n.isdigit():
            pincode += str(n)
        if len(pincode) == 4:
            break
    buttons = button_build.ButtonMaker()
    gid = hash_[:12]
    if WEB_PINCODE:
        buttons.buildbutton("Pilih Files", f"{BASE_URL}/app/files/{hash_}")
        buttons.sbutton("Pincode", f"qbs pin {gid} {pincode}")
    else:
        buttons.buildbutton("Pilih Files", f"{BASE_URL}/app/files/{hash_}?pin_code={pincode}")
    buttons.sbutton("Selesai Memilih", f"qbs done {gid} {hash_}")
    QBBUTTONS = InlineKeyboardMarkup(buttons.build_menu(2))
    msg = f"ℹ️ {tag} Download kamu dijeda. Silahkan pilih file kemudian klik Selesai Memilih untuk memulai qb-download."
    sendMarkup(msg, context.bot, update.message, QBBUTTONS)
    dl.download().select = True

def get_confirm(update, context):
    query = update.callback_query
    user_id = query.from_user.id
    data = query.data
    data = data.split()
    qbdl = getDownloadByGid(data[2])
    if not qbdl:
        query.answer(text="Task ini telah dibatalkan!", show_alert=True)
        query.message.delete()
    elif user_id != qbdl.listener().message.from_user.id:
        query.answer(text="Task ini bukan buat elu!", show_alert=True)
    elif data[1] == "pin":
        query.answer(text=data[3], show_alert=True)
    elif data[1] == "done":
        query.answer()
        qbdl.client().torrents_resume(torrent_hashes=data[3])
        sendStatusMessage(qbdl.listener().message, qbdl.listener().bot)
        query.message.delete()


select_handler = CommandHandler(BotCommands.QbSelectCommand, select,
                                filters=(CustomFilters.authorized_chat | CustomFilters.authorized_user), run_async=True)
qbs_handler = CallbackQueryHandler(get_confirm, pattern="qbs", run_async=True)
dispatcher.add_handler(select_handler)
dispatcher.add_handler(qbs_handler)