from re import match as re_match, findall as re_findall, split as re_split
from threading import Thread, Event
from time import time
from math import ceil
from html import escape
from psutil import cpu_percent, disk_usage
from requests import head as rhead
from urllib.request import urlopen
from telegram import InlineKeyboardMarkup
from urllib.parse import quote

from bot import download_dict, download_dict_lock, STATUS_LIMIT, botStartTime, DOWNLOAD_DIR, WEB_PINCODE, BASE_URL
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.button_build import ButtonMaker

MAGNET_REGEX = r"magnet:\?xt=urn:btih:[a-zA-Z0-9]*"

URL_REGEX = r"(?:(?:https?|ftp):\/\/)?[\w/\-?=%.]+\.[\w/\-?=%.]+"

COUNT = 0
PAGE_NO = 1


class MirrorStatus:
    STATUS_UPLOADING = "📤 Uploading"
    STATUS_DOWNLOADING = "📥 Downloading"
    STATUS_CLONING = "♻️ Cloning"
    STATUS_WAITING = "💤 Queued"
    STATUS_PAUSED = "⛔️ Paused"
    STATUS_ARCHIVING = "🔐 Archiving"
    STATUS_EXTRACTING = "📂 Extracting"
    STATUS_SPLITTING = "✂️ Splitting"
    STATUS_CHECKING = "📝 CheckingUp"
    STATUS_SEEDING = "🌧 Seeding"

SIZE_UNITS = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']


class setInterval:
    def __init__(self, interval, action):
        self.interval = interval
        self.action = action
        self.stopEvent = Event()
        thread = Thread(target=self.__setInterval)
        thread.start()

    def __setInterval(self):
        nextTime = time() + self.interval
        while not self.stopEvent.wait(nextTime - time()):
            nextTime += self.interval
            self.action()

    def cancel(self):
        self.stopEvent.set()

def get_readable_file_size(size_in_bytes) -> str:
    if size_in_bytes is None:
        return '0B'
    index = 0
    while size_in_bytes >= 1024:
        size_in_bytes /= 1024
        index += 1
    try:
        return f'{round(size_in_bytes, 2)}{SIZE_UNITS[index]}'
    except IndexError:
        return 'File terlalu besar'

def getDownloadByGid(gid):
    with download_dict_lock:
        for dl in list(download_dict.values()):
            if dl.gid() == gid:
                return dl
    return None

def getAllDownload(req_status: str):
    with download_dict_lock:
        for dl in list(download_dict.values()):
            status = dl.status()
            if req_status in ['all', status]:
                return dl
    return None

def bt_selection_buttons(id_: str):
    if len(id_) > 20:
        gid = id_[:12]
    else:
        gid = id_

    pincode = ""
    for n in id_:
        if n.isdigit():
            pincode += str(n)
        if len(pincode) == 4:
            break

    buttons = ButtonMaker()
    if WEB_PINCODE:
        buttons.buildbutton("Pilih Files", f"{BASE_URL}/app/files/{id_}")
        buttons.sbutton("Pincode", f"btsel pin {gid} {pincode}")
    else:
        buttons.buildbutton("Pilih Files", f"{BASE_URL}/app/files/{id_}?pin_code={pincode}")
    buttons.sbutton("Selesai Memilih", f"btsel done {gid} {id_}")
    return InlineKeyboardMarkup(buttons.build_menu(2))

def get_progress_bar_string(status):
    completed = status.processed_bytes() / 8
    total = status.size_raw() / 8
    p = 0 if total == 0 else round(completed * 100 / total)
    p = min(max(p, 0), 100)
    cFull = p // 8
    p_str = '■' * cFull
    p_str += '□' * (12 - cFull)
    p_str = f"[{p_str}]"
    return p_str

def get_readable_message():
    with download_dict_lock:
        msg = ""
        tasks = len(download_dict)
        if STATUS_LIMIT is not None:
            global pages
            pages = ceil(tasks/STATUS_LIMIT)
            if PAGE_NO > pages and pages != 0:
                globals()['COUNT'] -= STATUS_LIMIT
                globals()['PAGE_NO'] -= 1
        for index, download in enumerate(list(download_dict.values())[COUNT:], start=1):
            ### AWAL CUSTOM STATUS ###
            pemirror = download.Pemirror()
            reply_to = pemirror.reply_to_message
            if not reply_to or reply_to.from_user.is_bot:
                link = f"https://t.me/c/{str(pemirror.chat.id)[4:]}/{pemirror.message_id}"
                if pemirror.from_user.username:
                    tag = f"<code>@{pemirror.from_user.username}</code> (<code>{pemirror.from_user.id}</code>)"
                else:
                    tag = f"<code>{pemirror.from_user.first_name}</code> (<code>{pemirror.from_user.id}</code>)"
            else:
                link = f"https://t.me/c/{str(pemirror.chat.id)[4:]}/{reply_to.message_id}"
                if reply_to.from_user.username:
                    tag = f"<code>@{reply_to.from_user.username}</code> (<code>{reply_to.from_user.id}</code>)"
                else:
                    tag = f"<code>{reply_to.from_user.first_name}</code> (<code>{reply_to.from_user.id}</code>)"
            ### AKHIR CUSTOM STATUS ###
            msg += f"💽 <code>{escape(str(download.name()))}</code>"
            msg += f"\n<a href=\"{link}\"><b>{download.status()}</b></a>"
            if download.status() != MirrorStatus.STATUS_SEEDING:
                msg += f"\n🌀 {get_progress_bar_string(download)} {download.progress()}"
                msg += f"\n📦 {get_readable_file_size(download.processed_bytes())} / {download.size()}"
                msg += f"\n⚡️ {download.speed()} | ⏳ {download.eta()}"
                msg += f"\n⏱ {get_readable_time(time() - download.message.date.timestamp())}"
                try:
                    msg += f"\n🧲 <b>Seeders:</b> {download.aria_download().num_seeders}" \
                           f" | <b>Peers:</b> {download.aria_download().connections}"
                except:
                    pass
                try:
                    msg += f"\n🧲 <b>Seeders:</b> {download.torrent_info().num_seeds}" \
                           f" | <b>Leechers:</b> {download.torrent_info().num_leechs}"
                except:
                    pass
            elif download.status() == MirrorStatus.STATUS_SEEDING:
                msg += f"\n📦 <b>Size: </b>{download.size()}"
                msg += f"\n⚡️ <b>Speed: </b>{get_readable_file_size(download.torrent_info().upspeed)}/s"
                msg += f" | 📤 <b>Uploaded: </b>{get_readable_file_size(download.torrent_info().uploaded)}"
                msg += f"\n🧩 <b>Ratio: </b>{round(download.torrent_info().ratio, 3)}"
                msg += f" | 🕒 <b>Time: </b>{get_readable_time(download.torrent_info().seeding_time)}"
            else:
                msg += f"\n📦 {download.size()}"
            msg += f"\n👤 {tag}"
            msg += f"\n❌ <code>/{BotCommands.CancelMirror} {download.gid()}</code>"
            msg += "\n\n"
            if STATUS_LIMIT is not None and index == STATUS_LIMIT:
                break
        if len(msg) == 0:
            return None, None
        msg += f"🎯 <b>Tasks:</b> {tasks}"
        bmsg = f"\n🖥️ <b>CPU:</b> {cpu_percent()}% | 💿 <b>FREE:</b> {get_readable_file_size(disk_usage(DOWNLOAD_DIR).free)}"
        dlspeed_bytes = 0
        upspeed_bytes = 0
        for download in list(download_dict.values()):
            spd = download.speed()
            if download.status() == MirrorStatus.STATUS_DOWNLOADING:
                if 'K' in spd:
                    dlspeed_bytes += float(spd.split('K')[0]) * 1024
                elif 'M' in spd:
                    dlspeed_bytes += float(spd.split('M')[0]) * 1048576
            elif download.status() == MirrorStatus.STATUS_UPLOADING:
                if 'KB/s' in spd:
                    upspeed_bytes += float(spd.split('K')[0]) * 1024
                elif 'MB/s' in spd:
                    upspeed_bytes += float(spd.split('M')[0]) * 1048576
        bmsg += f"\n🔻 <b>DL:</b> {get_readable_file_size(dlspeed_bytes)}/s | 🔺 <b>UL:</b> {get_readable_file_size(upspeed_bytes)}/s"
        if STATUS_LIMIT is not None and tasks > STATUS_LIMIT:
            msg += f" | 📑 <b>Page:</b> {PAGE_NO}/{pages}"
            buttons = ButtonMaker()
            buttons.sbutton("⏪ Previous", "status pre")
            buttons.sbutton("Next ⏩", "status nex")
            button = InlineKeyboardMarkup(buttons.build_menu(2))
            return msg + bmsg, button
        return msg + bmsg, ""

def turn(data):
    try:
        with download_dict_lock:
            global COUNT, PAGE_NO
            if data[1] == "nex":
                if PAGE_NO == pages:
                    COUNT = 0
                    PAGE_NO = 1
                else:
                    COUNT += STATUS_LIMIT
                    PAGE_NO += 1
            elif data[1] == "pre":
                if PAGE_NO == 1:
                    COUNT = STATUS_LIMIT * (pages - 1)
                    PAGE_NO = pages
                else:
                    COUNT -= STATUS_LIMIT
                    PAGE_NO -= 1
        return True
    except:
        return False

def get_readable_time(seconds: int) -> str:
    result = ''
    (days, remainder) = divmod(seconds, 86400)
    days = int(days)
    if days != 0:
        result += f'{days} hari '
    (hours, remainder) = divmod(remainder, 3600)
    hours = int(hours)
    if hours != 0:
        result += f'{hours} jam '
    (minutes, seconds) = divmod(remainder, 60)
    minutes = int(minutes)
    if minutes != 0:
        result += f'{minutes} menit '
    seconds = int(seconds)
    result += f'{seconds} detik '
    return result

def is_url(url: str):
    url = re_findall(URL_REGEX, url)
    return bool(url)

def is_gdrive_link(url: str):
    return "drive.google.com" in url

def is_sharerpw_link(url: str):
    return "sharer.pw" in url

def is_gdtot_link(url: str):
    url = re_match(r'https?://.+\.gdtot\.\S+', url)
    return bool(url)

def is_appdrive_link(url: str):
    appdrive_links = ['appdrive.in', 'driveapp.in', 'drivehub.in', 'gdflix.pro', 'drivesharer.in', 'drivebit.in', 'drivelinks.in', 'driveace.in', 'drivepro.in']
    return any(x in url for x in appdrive_links)

def is_mega_link(url: str):
    return "mega.nz" in url or "mega.co.nz" in url

def get_mega_link_type(url: str):
    if "folder" in url:
        return "folder"
    elif "file" in url:
        return "file"
    elif "/#F!" in url:
        return "folder"
    return "file"

def is_magnet(url: str):
    magnet = re_findall(MAGNET_REGEX, url)
    return bool(magnet)

def new_thread(fn):
    """To use as decorator to make a function call threaded.
    Needs import
    from threading import Thread"""

    def wrapper(*args, **kwargs):
        thread = Thread(target=fn, args=args, kwargs=kwargs)
        thread.start()
        return thread

    return wrapper

def get_content_type(link: str) -> str:
    try:
        res = rhead(link, allow_redirects=True, timeout=5, headers = {'user-agent': 'Wget/1.12'})
        content_type = res.headers.get('content-type')
    except:
        try:
            res = urlopen(link, timeout=5)
            info = res.info()
            content_type = info.get_content_type()
        except:
            content_type = None
    return content_type

