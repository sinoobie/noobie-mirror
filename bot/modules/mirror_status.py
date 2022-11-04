from psutil import cpu_percent, virtual_memory, disk_usage, net_io_counters
from time import time
from threading import Thread
from telegram.ext import CommandHandler, CallbackQueryHandler

from bot import dispatcher, status_reply_dict, status_reply_dict_lock, download_dict, download_dict_lock, botStartTime, DOWNLOAD_DIR, Interval, DOWNLOAD_STATUS_UPDATE_INTERVAL, OWNER_ID, user_data
from bot.helper.telegram_helper.message_utils import sendMessage, deleteMessage, auto_delete_message, sendStatusMessage, update_all_messages, delete_all_messages
from bot.helper.ext_utils.bot_utils import get_readable_message, get_readable_file_size, get_readable_time, turn, setInterval, new_thread, MirrorStatus
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.bot_commands import BotCommands


def mirror_status(update, context):
    with download_dict_lock:
        count = len(download_dict)
    if count == 0:
        currentTime = get_readable_time(time() - botStartTime)
        free = get_readable_file_size(disk_usage(DOWNLOAD_DIR).free)
        message = '💤 Tidak Ada Proses Mirror Yang Sedang Berjalan\n'
        message += f"\n<b>CPU:</b> {cpu_percent()}% | <b>FREE:</b> {free}" \
                   f"\n<b>RAM:</b> {virtual_memory().percent}% | <b>UPTIME:</b> {currentTime}"
        reply_message = sendMessage(message, context.bot, update.message)
        Thread(target=auto_delete_message, args=(context.bot, update.message, reply_message)).start()
    else:
        sendStatusMessage(update.message, context.bot)
        deleteMessage(context.bot, update.message)
        with status_reply_dict_lock:
            try:
                if Interval:
                    Interval[0].cancel()
                    Interval.clear()
            except:
                pass
            finally:
                Interval.append(setInterval(DOWNLOAD_STATUS_UPDATE_INTERVAL, update_all_messages))

@new_thread
def status_pages(update, context):
    query = update.callback_query
    with download_dict_lock:
        if len(download_dict) != 0:
            with status_reply_dict_lock:
                if not status_reply_dict or not Interval or time() - list(status_reply_dict.values())[0][1] < 2:
                    query.answer(text="⚠️ Tunggu sebentar! gw getok ntar pala lu!", show_alert=True)
                    return
    userID = query.from_user.id
    qmessage = query.message
    data = query.data
    data = data.split()
    if data[1] == "cls":
        onstatus = []
        with download_dict_lock:
            for dl in list(download_dict.values()):
                onstatus.append(dl.message.from_user.id)
        if userID == OWNER_ID or userID in onstatus or user_data.get(userID, user_data).get('is_sudo'):
            query.answer()
            qmessage.delete()
            clsmsg = sendMessage(f"ℹ️ Status ditutup oleh {query.from_user.mention_html(query.from_user.first_name)}. Ketik /status untuk menampilkan status lagi", context.bot, update.message)
            Thread(target=auto_delete_message, args=(context.bot, update.message, clsmsg)).start()
        else:
            query.answer(text="⚠️ Minimal lu harus punya satu proses mirror!", show_alert=True)
    elif data[1] == "sta":
        stat = onProcess_stats()
        if stat:
            query.answer(text=stat, show_alert=True)
        else:
            query.answer(text="⚠️ Ini adalah status lama")
            qmessage.delete()
    elif data[1] in ['pre', 'nex']:
        query.answer()
        done = turn(data)
        if done:
            msg, buttons = get_readable_message()
            qmessage.edit_text(text=msg, reply_markup=buttons, parse_mode='HTMl', disable_web_page_preview=True)
        else:
            qmessage.delete()


def onProcess_stats():
    with download_dict_lock:
        if len(download_dict) == 0:
            return
        active = upload = extract = archive = split = dsize = 0
        for stats in list(download_dict.values()):
            if stats.status() == MirrorStatus.STATUS_DOWNLOADING:
                active += 1
                dsize += stats.processed_bytes()
            if stats.status() == MirrorStatus.STATUS_UPLOADING:
                upload += 1
            if stats.status() == MirrorStatus.STATUS_EXTRACTING:
                extract += 1
            if stats.status() == MirrorStatus.STATUS_ARCHIVING:
                archive += 1
            if stats.status() == MirrorStatus.STATUS_SPLITTING:
                split += 1
        onProcess = "==OnProcess==\n" \
                    f"ZIP: {archive} | UNZIP: {extract} | SPLIT: {split}\n" \
                    f"DL: {active} | UP: {upload} | ProcessedBytes: {get_readable_file_size(dsize)}"
        mem = virtual_memory().percent
        recv = get_readable_file_size(net_io_counters().bytes_recv)
        sent = get_readable_file_size(net_io_counters().bytes_sent)
        free = disk_usage(DOWNLOAD_DIR).free
        msg = f"==Bot Statistics==\n" \
            f"Send: {sent} | Recv: {recv}\n" \
            f"CPU: {cpu_percent()}% | RAM: {mem}%\n\n" \
            f"{onProcess}\n"
        return msg

mirror_status_handler = CommandHandler(BotCommands.StatusCommand, mirror_status,
                                       filters=CustomFilters.authorized_chat | CustomFilters.authorized_user, run_async=True)

status_pages_handler = CallbackQueryHandler(status_pages, pattern="status", run_async=True)
dispatcher.add_handler(mirror_status_handler)
dispatcher.add_handler(status_pages_handler)
