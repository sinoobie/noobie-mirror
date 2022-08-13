from threading import Thread
from os import remove, path as ospath
from telegram.ext import CommandHandler, CallbackQueryHandler

from bot import aria2, BASE_URL, download_dict, dispatcher, download_dict_lock, SUDO_USERS, OWNER_ID
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import sendMessage, sendMarkup, sendStatusMessage, auto_delete_message
from bot.helper.ext_utils.bot_utils import getDownloadByGid, MirrorStatus, bt_selection_buttons

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
        msg = "Balas perintah aktif yang digunakan untuk memulai bt-download atau menambahkan ID Download bersama dengan perintah ini\n\n"
        msg += "Perintah ini terutama untuk pemilihan jika Kamu memutuskan untuk memilih file dari torrent yang sudah ditambahkan, "
        msg += "Tetapi kamu juga dapat menggunakan perintah dengan arg `s` untuk memilih file sebelum download dimulai."
        smsg = sendMessage(msg, context.bot, update.message)
        Thread(target=auto_delete_message, args=(context.bot, update.message, smsg)).start()
        return

    if OWNER_ID != user_id and dl.message.from_user.id != user_id and user_id not in SUDO_USERS:
        tmsg = sendMessage(f"⚠️ {tag} Task ini bukan buat elu!", context.bot, update.message)
        Thread(target=auto_delete_message, args=(context.bot, update.message, tmsg)).start()
        return

    if dl.status() not in [MirrorStatus.STATUS_DOWNLOADING, MirrorStatus.STATUS_PAUSED, MirrorStatus.STATUS_WAITING]:
        tmsg = sendMessage(f"⚠️ {tag} Task harus dalam status downloading atau paused!", context.bot, update.message)
        Thread(target=auto_delete_message, args=(context.bot, update.message, tmsg)).start()
        return
    if dl.name().startswith('[METADATA]'):
        tmsg = sendMessage(f"⚠️ {tag} Coba lagi setelah downloading METADATA selesai!", context.bot, update.message)
        Thread(target=auto_delete_message, args=(context.bot, update.message, tmsg)).start()
        return
    try:
        if dl.listener().isQbit:
            id_ = dl.download().ext_hash
            client = dl.client()
            client.torrents_pause(torrent_hashes=id_)
            dl.download().select = True
        else:
            id_ = dl.gid()
            aria2.client.force_pause(id_)
    except:
        tmsg = sendMessage(f"⚠️ {tag} Task ini bukan torrent!", context.bot, update.message)
        Thread(target=auto_delete_message, args=(context.bot, update.message, tmsg)).start()
        return

    SBUTTONS = bt_selection_buttons(id_)
    msg = f"⛔️ {tag} Download kamu dijeda. Silahkan pilih file kemudian klik Selesai Memilih untuk memulai qb-download."
    sendMarkup(msg, context.bot, update.message, SBUTTONS)

def get_confirm(update, context):
    query = update.callback_query
    user_id = query.from_user.id
    data = query.data
    data = data.split()
    dl = getDownloadByGid(data[2])
    if not dl:
        query.answer(text="Task ini telah dibatalkan!", show_alert=True)
        query.message.delete()
        return
    listener = dl.listener()
    if user_id != listener.message.from_user.id:
        query.answer(text="Task ini bukan buat elu!", show_alert=True)
    elif data[1] == "pin":
        query.answer(text=data[3], show_alert=True)
    elif data[1] == "done":
        query.answer()
        id_ = data[3]
        if len(id_) > 20:
            client = dl.client()
            tor_info = client.torrents_info(torrent_hash=id_)[0]
            path = tor_info.content_path.rsplit('/', 1)[0]
            res = client.torrents_files(torrent_hash=id_)
            for f in res:
                if f.priority == 0:
                    f_paths = [f"{path}/{f.name}", f"{path}/{f.name}.!qB"]
                    for f_path in f_paths:
                       if ospath.exists(f_path):
                           try:
                               remove(f_path)
                           except:
                               pass
            client.torrents_resume(torrent_hashes=id_)
        else:
            res = aria2.client.get_files(id_)
            for f in res:
                if f['selected'] == 'false' and ospath.exists(f['path']):
                    try:
                        remove(f['path'])
                    except:
                        pass
            aria2.client.unpause(id_)
        sendStatusMessage(listener.message, listener.bot)
        query.message.delete()


select_handler = CommandHandler(BotCommands.BtSelectCommand, select,
                                filters=(CustomFilters.authorized_chat | CustomFilters.authorized_user), run_async=True)
bts_handler = CallbackQueryHandler(get_confirm, pattern="btsel", run_async=True)
dispatcher.add_handler(select_handler)
dispatcher.add_handler(bts_handler)