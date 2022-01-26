import signal
import os

from os import path as ospath, remove as osremove, execl as osexecl
from subprocess import run as srun
from asyncio import run as asyrun
from psutil import disk_usage, cpu_percent, swap_memory, cpu_count, virtual_memory, net_io_counters, Process as psprocess
from time import time
from pyrogram import idle
from sys import executable
from telegram import ParseMode, InlineKeyboardMarkup
from telegram.ext import CommandHandler

from wserver import start_server_async
from bot import bot, app, dispatcher, updater, botStartTime, IGNORE_PENDING_REQUESTS, IS_VPS, PORT, alive, web, OWNER_ID, AUTHORIZED_CHATS, LOGGER, Interval, nox, rss_session, a2c
from .helper.ext_utils.fs_utils import start_cleanup, clean_all, exit_clean_up
from .helper.telegram_helper.bot_commands import BotCommands
from .helper.telegram_helper.message_utils import sendMessage, sendMarkup, editMessage, sendLogFile
from .helper.ext_utils.telegraph_helper import telegraph
from .helper.ext_utils.bot_utils import get_readable_file_size, get_readable_time
from .helper.telegram_helper.filters import CustomFilters
from .helper.telegram_helper.button_build import ButtonMaker
from .modules import authorize, list, cancel_mirror, mirror_status, mirror, clone, watch, shell, eval, delete, speedtest, count, leech_settings, search, rss


def stats(update, context):
    currentTime = get_readable_time(time() - botStartTime)
    total, used, free, disk= disk_usage('/')
    total = get_readable_file_size(total)
    used = get_readable_file_size(used)
    free = get_readable_file_size(free)
    sent = get_readable_file_size(net_io_counters().bytes_sent)
    recv = get_readable_file_size(net_io_counters().bytes_recv)
    cpuUsage = cpu_percent(interval=0.5)
#    p_core = cpu_count(logical=False)
#    t_core = cpu_count(logical=True)
#    swap = swap_memory()
#    swap_p = swap.percent
#    swap_t = get_readable_file_size(swap.total)
#    swap_u = get_readable_file_size(swap.used)
    memory = virtual_memory()
    mem_p = memory.percent
#    mem_t = get_readable_file_size(memory.total)
#    mem_a = get_readable_file_size(memory.available)
#    mem_u = get_readable_file_size(memory.used)
    stats = f'<b>Bot Uptime:</b> {currentTime}\n\n'\
            f'<b>Total Disk Space:</b> {total}\n'\
            f'<b>Used:</b> {used} | <b>Free:</b> {free}\n\n'\
            f'<b>Upload:</b> {sent}\n'\
            f'<b>Download:</b> {recv}\n\n'\
            f'<b>CPU:</b> {cpuUsage}%\n'\
            f'<b>RAM:</b> {mem_p}%\n'\
            f'<b>DISK:</b> {disk}%\n\n'\
#            f'<b>Physical Cores:</b> {p_core}\n'\
#            f'<b>Total Cores:</b> {t_core}\n\n'\
#            f'<b>SWAP:</b> {swap_t} | <b>Used:</b> {swap_p}%\n'\
#            f'<b>Memory Total:</b> {mem_t}\n'\
#            f'<b>Memory Free:</b> {mem_a}\n'\
#            f'<b>Memory Used:</b> {mem_u}\n'\
    stats += '<b>Bot Version:</b> 2022.01.26'
    sendMessage(stats, context.bot, update)


def start(update, context):
    buttons = ButtonMaker()
    buttons.buildbutton("Owner", "@SiNoobie")
    buttons.buildbutton("Group", "tg://openmessage?chat_id=1501822053")
    reply_markup = InlineKeyboardMarkup(buttons.build_menu(2))
    sendMarkup('Silahkan ke Grup untuk menggunakan bot!', context.bot, update, reply_markup)
    """
    if CustomFilters.authorized_user(update) or CustomFilters.authorized_chat(update):
        start_string = f'''
This bot can mirror all your links to Google Drive!
Type /{BotCommands.HelpCommand} to get a list of available commands
'''
        sendMarkup(start_string, context.bot, update, reply_markup)
    else:
        sendMarkup('Not Authorized user, go to Group', context.bot, update, reply_markup)
    """

def restart(update, context):
    restart_message = sendMessage("Restarting...", context.bot, update)
    if Interval:
        Interval[0].cancel()
    alive.kill()
    procs = psprocess(web.pid)
    for proc in procs.children(recursive=True):
        proc.kill()
    procs.kill()
    clean_all()
    srun(["python3", "update.py"])
    nox.kill()
    a2cproc = psprocess(a2c.pid)
    for proc in a2cproc.children(recursive=True):
        proc.kill()
    a2cproc.kill()
    with open(".restartmsg", "w") as f:
        f.truncate(0)
        f.write(f"{restart_message.chat.id}\n{restart_message.message_id}\n")
    osexecl(executable, executable, "-m", "bot")


def ping(update, context):
    start_time = int(round(time() * 1000))
    reply = sendMessage("Starting Ping", context.bot, update)
    end_time = int(round(time() * 1000))
    editMessage(f'{end_time - start_time} ms', reply)


def log(update, context):
    sendLogFile(context.bot, update)


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
<br>Untuk mirror torrent dengan qBittorrent, Ketik <b>/{BotCommands.QbMirrorCommand} s [magnet_link] atau [torrent_file] atau [torrent_file_url]</b> untuk memilih file sebelum mulai mirror
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

/{BotCommands.SpeedCommand}: Check Internet Speed (Hanya untuk Owner)

/{BotCommands.ShellCommand}: Menjalankan commands di Shell (Hanya untuk Owner)

/{BotCommands.ExecHelpCommand}: Bantuan untuk Executor module (Hanya untuk Owner)
'''

def bot_help(update, context):
    button = ButtonMaker()
    button.buildbutton("Perintah lainnya", f"https://telegra.ph/{help}")
    reply_markup = InlineKeyboardMarkup(button.build_menu(1))
    sendMarkup(help_string, context.bot, update, reply_markup)

botcmds = [

        (f'{BotCommands.MirrorCommand}', 'Mirror'),
        (f'{BotCommands.ZipMirrorCommand}','Mirror dan upload lalu arsip ke zip'),
        (f'{BotCommands.UnzipMirrorCommand}','Mirror dan extract files'),
        (f'{BotCommands.QbMirrorCommand}','Mirror torrent menggunakan qBittorrent'),
        (f'{BotCommands.QbZipMirrorCommand}','Mirror torrent menggunakan qBittorrent dan arsip ke zip'),
        (f'{BotCommands.QbUnzipMirrorCommand}','Mirror torrent menggunakan qBittorrent dan extract files'),
        (f'{BotCommands.WatchCommand}','Mirror YouTube link'),
        (f'{BotCommands.ZipWatchCommand}','Mirror YouTube link lalu arsip ke zip'),
        (f'{BotCommands.CloneCommand}','Copy file/folder to Drive'),
        (f'{BotCommands.LeechCommand}','Leech'),
        (f'{BotCommands.ZipLeechCommand}','Leech dan upload lalu arsip ke zip'),
        (f'{BotCommands.UnzipLeechCommand}','Leech dan extract files'),
        (f'{BotCommands.QbLeechCommand}','Leech torrent menggunakan qBittorrent'),
        (f'{BotCommands.QbZipLeechCommand}','Leech torrent menggunakan qBittorrent dan arsip ke zip'),
        (f'{BotCommands.QbUnzipLeechCommand}','Leech torrent menggunakan qBittorrent dan extract'),
        (f'{BotCommands.LeechWatchCommand}','Leech YouTube link'),
        (f'{BotCommands.LeechZipWatchCommand}','Leech YouTube link lalu arsip ke zip'),
        (f'{BotCommands.CountCommand}','Menghitung file/folder dari Drive'),
        (f'{BotCommands.DeleteCommand}','Menghapus file/folder dari Drive'),
        (f'{BotCommands.CancelMirror}','Cancel sebuah task'),
        (f'{BotCommands.CancelAllCommand}','Cancel semua downloading tasks'),
        (f'{BotCommands.LeechSetCommand}','Leech settings'),
        (f'{BotCommands.SetThumbCommand}','Set thumbnail'),
        (f'{BotCommands.StatusCommand}','Menampilkan status mirror'),
        (f'{BotCommands.StatsCommand}','Statik penggunaan bot'),
        (f'{BotCommands.PingCommand}','Ping bot'),
        (f'{BotCommands.RestartCommand}','Restart bot'),
        (f'{BotCommands.HelpCommand}','Mendapatkan detail help')
    ]

def main():
    # bot.set_my_commands(botcmds)
    start_cleanup()
    if IS_VPS:
        asyrun(start_server_async(PORT))
    # Check if the bot is restarting
    if ospath.isfile(".restartmsg"):
        with open(".restartmsg") as f:
            chat_id, msg_id = map(int, f)
        bot.edit_message_text("Restarted successfully!", chat_id, msg_id)
        osremove(".restartmsg")
    elif OWNER_ID:
        try:
            text = "<b>Bot Restarted!</b>"
            bot.sendMessage(chat_id=OWNER_ID, text=text, parse_mode=ParseMode.HTML)
            if AUTHORIZED_CHATS:
                for i in AUTHORIZED_CHATS:
                    bot.sendMessage(chat_id=i, text=text, parse_mode=ParseMode.HTML)
        except Exception as e:
            LOGGER.warning(e)

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
    signal.signal(signal.SIGINT, exit_clean_up)
    if rss_session is not None:
        rss_session.start()

app.start()
main()
idle()
