from signal import signal, SIGINT
from os import path as ospath, remove as osremove, execl as osexecl
from subprocess import run as srun, check_output
from psutil import disk_usage, cpu_percent, swap_memory, cpu_count, virtual_memory, net_io_counters, boot_time
from time import time
from sys import executable
from telegram import InlineKeyboardMarkup
from telegram.ext import CommandHandler
from threading import Thread

from bot import bot, dispatcher, updater, botStartTime, IGNORE_PENDING_REQUESTS, LOGGER, Interval, INCOMPLETE_TASK_NOTIFIER, DB_URI, alive, app, main_loop, AUTHORIZED_CHATS
from .helper.ext_utils.fs_utils import start_cleanup, clean_all, exit_clean_up
from .helper.ext_utils.telegraph_helper import telegraph
from .helper.ext_utils.bot_utils import get_readable_file_size, get_readable_time
from .helper.ext_utils.db_handler import DbManger
from .helper.telegram_helper.bot_commands import BotCommands
from .helper.telegram_helper.message_utils import sendMessage, sendMarkup, editMessage, sendLogFile, auto_delete_message
from .helper.telegram_helper.filters import CustomFilters
from .helper.telegram_helper.button_build import ButtonMaker

from .modules import authorize, list, cancel_mirror, mirror_status, mirror, clone, watch, shell, eval, delete, count, leech_settings, search, rss, bt_select, sleep


def stats(update, context):
    botVersion = check_output(["git log -1 --date=format:v%Y.%m.%d --pretty=format:%cd"], shell=True).decode()
    currentTime = get_readable_time(time() - botStartTime)
    total, used, free, disk= disk_usage('/')
    total = get_readable_file_size(total)
    used = get_readable_file_size(used)
    free = get_readable_file_size(free)
    sent = get_readable_file_size(net_io_counters().bytes_sent)
    recv = get_readable_file_size(net_io_counters().bytes_recv)
    cpuUsage = cpu_percent(interval=0.5)
    memory = virtual_memory()
    mem_p = memory.percent
    stats = f'🕒 <b>Bot Uptime:</b> {currentTime}\n\n'\
            f'💽 <b>Total Disk Space:</b> {total}\n'\
            f'📀 <b>Used:</b> {used}\n'\
            f'💿 <b>Free:</b> {free}\n\n'\
            f'🔺 <b>Upload:</b> {sent}\n'\
            f'🔻 <b>Download:</b> {recv}\n'\
            f'🖥️ <b>CPU:</b> {cpuUsage}%\n'\
            f'💾 <b>RAM:</b> {mem_p}%\n\n'\
            f'🤖 <b>Bot Version:</b> {botVersion}'
    smsg = sendMessage(stats, context.bot, update.message)
    Thread(target=auto_delete_message, args=(context.bot, update.message, smsg)).start()


def start(update, context):
    buttons = ButtonMaker()
    buttons.buildbutton("Owner", "@SiNoobie")
    buttons.buildbutton("Group", "@cermin_in")
    reply_markup = InlineKeyboardMarkup(buttons.build_menu(2))
    sendMarkup('Silahkan gabung @cermin_in untuk menggunakan bot!', context.bot, update, reply_markup)

def restart(update, context):
    restart_message = sendMessage("♻️ Restarting...", context.bot, update.message)
    if Interval:
        Interval[0].cancel()
        Interval.clear()
    alive.kill()
    clean_all()
    srun(["pkill", "-9", "-f", "gunicorn|extra-api|last-api|megasdkrest|new-api"])
    srun(["python3", "update.py"])
    with open(".restartmsg", "w") as f:
        f.truncate(0)
        f.write(f"{restart_message.chat.id}\n{restart_message.message_id}\n")
    osexecl(executable, executable, "-m", "bot")


def ping(update, context):
    start_time = int(round(time() * 1000))
    reply = sendMessage("Starting Ping", context.bot, update.message)
    end_time = int(round(time() * 1000))
    editMessage(f'{end_time - start_time} ms', reply)


def log(update, context):
    sendLogFile(context.bot, update.message)


help_string_telegraph = f'''<br>
<b>/{BotCommands.HelpCommand}</b> Untuk mendapatkan pesan ini
<br><br>
<b>/{BotCommands.MirrorCommand} [download_url] atau [magnet_link]</b>
<br>Untuk memulai mirror direct atau torrent link. Ketik <b>/{BotCommands.MirrorCommand}</b> untuk penggunaan lebih lanjut
<br><br>
<b>/{BotCommands.ZipMirrorCommand} [download_url] atau [magnet_link]</b>
<br>Untuk mengarsip file atau folder ke zip
<br><br>
<b>/{BotCommands.UnzipMirrorCommand} [download_url] atau [magnet_link]</b>
<br>Untuk mengekstraks file atau folder
<br><br>
<b>/{BotCommands.QbMirrorCommand} [magnet_link] atau [torrent_file] atau [torrent_file_url]</b>
<br>Untuk mirror torrent dengan qBittorrent, Kirim <b>/{BotCommands.QbMirrorCommand}</b> untuk detail lebih lanjut
<br><br>
<b>/{BotCommands.QbZipMirrorCommand} [magnet_link] atau [torrent_file] atau [torrent_file_url]</b>
<br>Untuk mirror torrent dengan qBittorrent lalu kemudian mengarsip file atau folder ke zip
<br><br>
<b>/{BotCommands.QbUnzipMirrorCommand} [magnet_link] atau [torrent_file] atau [torrent_file_url]</b>
<br>Untuk mirror torrent dengan qBittorrent lalu kemudian mengekstraks file atau folder
<br><br>
<b>/{BotCommands.LeechCommand} [download_url] atau [magnet_link]</b>
<br>Untuk mengupload hasil mirror ke telegram, Ketik <b>/{BotCommands.LeechCommand} s [download_url] atau [magnet_link]</b> untuk memilih file sebelum mulai mirror
<br><br>
<b>/{BotCommands.ZipLeechCommand} [download_url] atau [magnet_link]</b>
<br>Untuk mengupload hasil mirror ke telegram lalu kemudian mengarsip file atau folder ke zip
<br><br>
<b>/{BotCommands.UnzipLeechCommand} [download_url] atau [magnet_link] atau [torent_file]</b>
<br>Untuk mengupload hasil mirror ke telegram lalu kemudian mengekstraks file atau folder
<br><br>
<b>/{BotCommands.QbLeechCommand} [magnet_link] atau [torrent_file] atau [torrent_file_url]</b>
<br>Untuk mengupload hasil mirror ke telegram dengan qBittorrent, Ketik <b>/{BotCommands.QbLeechCommand} s [magnet_link] atau [torrent_file] atau [torrent_file_url]</b> untuk memilih file sebelum mulai mirror
<br><br>
<b>/{BotCommands.QbZipLeechCommand} [magnet_link] atau [torrent_file] atau [torrent_file_url]</b>
<br>Untuk mengupload hasil mirror ke telegram dengan qBittorrent lalu kemudian mengarsip file atau folder ke zip
<br><br>
<b>/{BotCommands.QbUnzipLeechCommand} [magnet_link] atau [torrent_file] atau [torrent_file_url]</b>
<br>Untuk mengupload hasil mirror ke telegram dengan qBittorrent lalu kemudian mengekstraks file atau folder
<br><br>
<b>/{BotCommands.CloneCommand} [drive_url] atau [gdtot_url]</b>
<br>Copy file atau folder ke Google Drive
<br><br>
<b>/{BotCommands.CountCommand} [drive_url] atau [gdtot_url]</b>
<br>Menghitung file atau folder dari Google Drive
<br><br>
<b>/{BotCommands.DeleteCommand} [drive_url]</b>
<br>Hapus file atau folder dari Google Drive (Hanya Owner & Sudo)
<br><br>
<b>/{BotCommands.WatchCommand} [YouTube link]</b>
<br>Mirror YouTube link. Ketik <b>/{BotCommands.WatchCommand}</b> untuk lebih detail
<br><br>
<b>/{BotCommands.ZipWatchCommand} [YouTube link]</b>
<br>Mirror YouTube link dan kompres ke zip
<br><br>
<b>/{BotCommands.LeechWatchCommand} [YouTube link]</b>
<br>Leech (upload ke telegram) YouTube link
<br><br>
<b>/{BotCommands.LeechZipWatchCommand} [YouTube link]</b>
<br>Leech (upload ke telegram) YouTube link as zip
<br><br>
<b>/{BotCommands.BtSelectCommand}</b>
<br>Perintah ini terutama untuk pemilihan jika Anda memutuskan untuk memilih file dari bt-torrent yang sudah ditambahkan, Tetapi kamu juga dapat menggunakan perintah dengan arg `s` untuk memilih file sebelum pengunduhan dimulai. Cara penggunaan: Balas perintah aktif yang digunakan untuk memulai bt-download atau menambahkan ID Download bersama dengan perintah ini.
<br><br>
<b>/{BotCommands.LeechSetCommand}</b>: Leech settings
<br><br>
<b>/{BotCommands.SetThumbCommand}</b>: Reply photo untuk menetapkan Thumbnail
<br><br>
<b>/{BotCommands.CancelMirror}</b>: Untuk cancel task berdasarkan ID
<br><br>
<b>/{BotCommands.CancelAllCommand}</b>: Cancel semua downloading tasks
<br><br>
<b>/{BotCommands.ListCommand} [query]</b>
<br>Search in Google Drive(s)
<br><br>
<b>/{BotCommands.SearchCommand} [query]</b>
<br>Search for torrents with API
<br>sites: <code>rarbg, 1337x, yts, etzv, tgx, torlock, piratebay, nyaasi, ettv</code><br><br>
<b>/{BotCommands.StatusCommand}</b>: Tampilkan semua status tasks
<br><br>
<b>/{BotCommands.StatsCommand}</b>: Tampilkan statistik/speksifikasi bot
'''

help = telegraph.create_page(
        title='Mirror-in Help',
        content=help_string_telegraph,
    )["path"]

help_string = f'''
/{BotCommands.PingCommand}: Ping Bot

/{BotCommands.AuthorizeCommand}: Mengizinkan pengguna atau grup untuk menggunakan bot (Hanya untuk Owner)

/{BotCommands.UnAuthorizeCommand}: Mencabut izin pengguna atau grup untuk menggunakan bot (Hanya untuk Owner)

/{BotCommands.AuthorizedUsersCommand}: Tampilkan pengguna yang diberi izin menggunakan bot (Hanya untuk Owner)

/{BotCommands.AddSudoCommand}: Menambahkan sudo user (Hanya untuk Owner)

/{BotCommands.RmSudoCommand}: Menghapus sudo users (Hanya untuk Owner)

/{BotCommands.RestartCommand}: Restart bot (Hanya untuk Owner)

/{BotCommands.LogCommand}: Mendapatkan log debuging dari bot (Hanya untuk Owner)

/{BotCommands.ShellCommand}: Menjalankan commands di Shell (Hanya untuk Owner)

/{BotCommands.ExecHelpCommand}: Bantuan untuk Executor module (Hanya untuk Owner)
'''

def bot_help(update, context):
    button = ButtonMaker()
    button.buildbutton("Perintah lainnya", f"https://telegra.ph/{help}")
    reply_markup = InlineKeyboardMarkup(button.build_menu(1))
    sendMarkup(help_string, context.bot, update.message, reply_markup)

botcmds = [

        (f'{BotCommands.MirrorCommand}', 'Mirror'),
        (f'{BotCommands.ZipMirrorCommand}','Mirror lalu arsip ke zip'),
        (f'{BotCommands.UnzipMirrorCommand}','Mirror dan ekstrak file'),
        (f'{BotCommands.QbMirrorCommand}','Mirror torrent menggunakan qBittorrent'),
        (f'{BotCommands.QbZipMirrorCommand}','Mirror torrent menggunakan qBittorrent dan arsip ke zip'),
        (f'{BotCommands.QbUnzipMirrorCommand}','Mirror torrent menggunakan qBittorrent dan ekstrak file'),
        (f'{BotCommands.WatchCommand}','Mirror YouTube link'),
        (f'{BotCommands.ZipWatchCommand}','Mirror YouTube link lalu arsip ke zip'),
        (f'{BotCommands.CloneCommand}','Copy file/folder to Drive'),
        (f'{BotCommands.LeechCommand}','Upload file ke telegram'),
        (f'{BotCommands.ZipLeechCommand}','Arsip file ke zip lalu Upload ke telegram'),
        (f'{BotCommands.UnzipLeechCommand}','Ekstrak file lalu Upload file ke telegram'),
        (f'{BotCommands.QbLeechCommand}','Upload torrent ke telegram menggunakan qBittorrent'),
        (f'{BotCommands.QbZipLeechCommand}','Arsip torrent ke zip lalu Upload ke telegram menggunakan qBittorrent'),
        (f'{BotCommands.QbUnzipLeechCommand}','Ekstrak torrent lalu Upload ke telegram menggunakan qBittorrent'),
        (f'{BotCommands.LeechWatchCommand}','Upload YouTube video ke telegram'),
        (f'{BotCommands.LeechZipWatchCommand}','Arsip ke zip YouTube video lalu upload ke telegram'),
        (f'{BotCommands.CountCommand}','Menghitung file/folder dari Drive'),
        (f'{BotCommands.DeleteCommand}','Menghapus file/folder dari Drive'),
        (f'{BotCommands.CancelMirror}','Cancel sebuah task'),
        (f'{BotCommands.CancelAllCommand}','Cancel semua downloading tasks'),
        (f'{BotCommands.LeechSetCommand}','Leech settings'),
        (f'{BotCommands.SetThumbCommand}','Set Leech thumbnail'),
        (f'{BotCommands.ListCommand}', 'Mencari file yang sudah ada di Drive'),
        (f'{BotCommands.StatusCommand}','Menampilkan status mirror'),
        (f'{BotCommands.StatsCommand}','Statistik penggunaan bot'),
        (f'{BotCommands.PingCommand}','Ping bot'),
        (f'{BotCommands.HelpCommand}','Mendapatkan detail perintah bot')
    ]

def main():
    bot.set_my_commands(botcmds)
    start_cleanup()
    notifier_dict = False
    if INCOMPLETE_TASK_NOTIFIER and DB_URI is not None:
        if notifier_dict := DbManger().get_incomplete_tasks():
            for cid, data in notifier_dict.items():
                if ospath.isfile(".restartmsg"):
                    with open(".restartmsg") as f:
                        chat_id, msg_id = map(int, f)
                    msg = '♻️ <b>Restarted successfully!</b>'
                else:
                    msg = '♻️ <b>Bot Restarted!</b>'
                for tag, links in data.items():
                    msg += f"\n\n⚠️ {tag} <b>{len(links)} Proses mirror kamu dibatalkan</b>"
                    for index, link in enumerate(links, start=1):
                        msg += f"\n📍 <a href='{link}'><u>Proses ke {index}</u></a>"
                        if len(msg.encode()) > 4000:
                            if '♻️ <b>Restarted successfully!</b>' in msg and cid == chat_id:
                                bot.editMessageText(msg, chat_id, msg_id, parse_mode='HTMl', disable_web_page_preview=True)
                                osremove(".restartmsg")
                            else:
                                try:
                                    bot.sendMessage(cid, msg, 'HTML', disable_web_page_preview=True)
                                except Exception as e:
                                    LOGGER.error(e)
                            msg = ''
                if '♻️ <b>Restarted successfully!</b>' in msg and cid == chat_id:
                    bot.editMessageText(msg, chat_id, msg_id, parse_mode='HTMl', disable_web_page_preview=True)
                    osremove(".restartmsg")
                else:
                    try:
                        bot.sendMessage(cid, msg, 'HTML', disable_web_page_preview=True)
                    except Exception as e:
                        LOGGER.error(e)

    if ospath.isfile(".restartmsg"):
        with open(".restartmsg") as f:
            chat_id, msg_id = map(int, f)
        bot.editMessageText("♻️ <b>Restarted successfully!</b>", chat_id, msg_id, parse_mode='HTMl', disable_web_page_preview=True)
        osremove(".restartmsg")

    start_handler = CommandHandler(BotCommands.StartCommand, start, run_async=True)
    ping_handler = CommandHandler(BotCommands.PingCommand, ping,
                                  filters=CustomFilters.authorized_chat | CustomFilters.authorized_user, run_async=True)
    restart_handler = CommandHandler(BotCommands.RestartCommand, restart,
                                     filters=CustomFilters.owner_filter | CustomFilters.sudo_user, run_async=True)
    help_handler = CommandHandler(BotCommands.HelpCommand,
                                  bot_help, filters=CustomFilters.authorized_chat | CustomFilters.authorized_user, run_async=True)
    stats_handler = CommandHandler(BotCommands.StatsCommand,
                                   stats, filters=CustomFilters.authorized_chat | CustomFilters.authorized_user, run_async=True)
    log_handler = CommandHandler(BotCommands.LogCommand, log, filters=CustomFilters.owner_filter | CustomFilters.sudo_user, run_async=True)
    dispatcher.add_handler(start_handler)
    dispatcher.add_handler(ping_handler)
    dispatcher.add_handler(restart_handler)
    dispatcher.add_handler(help_handler)
    dispatcher.add_handler(stats_handler)
    dispatcher.add_handler(log_handler)
    updater.start_polling(drop_pending_updates=IGNORE_PENDING_REQUESTS)
    LOGGER.info("Bot Started!")
    signal(SIGINT, exit_clean_up)

app.start()
main()

main_loop.run_forever()
