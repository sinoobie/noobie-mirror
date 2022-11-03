from psutil import cpu_percent, virtual_memory, disk_usage
from time import time
from threading import Thread
from telegram.ext import CommandHandler, CallbackQueryHandler

from bot import dispatcher, status_reply_dict_lock, download_dict, download_dict_lock, botStartTime, DOWNLOAD_DIR, Interval, DOWNLOAD_STATUS_UPDATE_INTERVAL, OWNER_ID, user_data
from bot.helper.telegram_helper.message_utils import sendMessage, deleteMessage, auto_delete_message, sendStatusMessage, update_all_messages, delete_all_messages
from bot.helper.ext_utils.bot_utils import get_readable_file_size, get_readable_time, turn, setInterval, new_thread, statistik
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
    user_id = query.from_user.id
    data = query.data
    data = data.split()
    if data[1] == "cls":
        onstatus = []
        with download_dict_lock:
            for dl in list(download_dict.values()):
                onstatus.append(dl.message.from_user.id)
        if user_id == OWNER_ID or user_id in onstatus or user_data.get(user_id, user_data).get('is_sudo'):
            delete_all_messages()
            query.answer()
        else:
            query.answer(text="⚠️ Minimal harus punya satu proses mirror!", show_alert=True)
    elif data[1] == "sta":
        stat = statistik(alert=True)
        query.answer(text=stat, show_alert=True)
    elif data[1] in ['pre', 'nex']:
        done = turn(data)
        if done:
            update_all_messages(True)
            query.answer()
        else:
            query.message.delete()
    else:
        query.message.delete()


mirror_status_handler = CommandHandler(BotCommands.StatusCommand, mirror_status,
                                       filters=CustomFilters.authorized_chat | CustomFilters.authorized_user, run_async=True)

status_pages_handler = CallbackQueryHandler(status_pages, pattern="status", run_async=True)
dispatcher.add_handler(mirror_status_handler)
dispatcher.add_handler(status_pages_handler)
