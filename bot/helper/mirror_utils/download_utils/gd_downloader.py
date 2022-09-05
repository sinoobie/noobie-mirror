from random import SystemRandom
from string import ascii_letters, digits

from bot import download_dict, download_dict_lock, ZIP_UNZIP_LIMIT, LOGGER, STOP_DUPLICATE, TORRENT_DIRECT_LIMIT
from bot.helper.mirror_utils.upload_utils.gdriveTools import GoogleDriveHelper
from bot.helper.mirror_utils.status_utils.gd_download_status import GdDownloadStatus
from bot.helper.telegram_helper.message_utils import sendMessage, sendStatusMessage, sendFile
from bot.helper.ext_utils.bot_utils import get_readable_file_size
from bot.helper.ext_utils.fs_utils import get_base_name


def add_gd_download(link, path, listener, newname, gdrive_sharer):
    res, size, name, files = GoogleDriveHelper().helper(link)
    if res != "":
        return sendMessage(res, listener.bot, listener.message)
    if newname:
        name = newname
    if STOP_DUPLICATE and not listener.isLeech:
        LOGGER.info('Checking File/Folder if already in Drive...')
        if listener.isZip:
            gname = f"{name}.zip"
        elif listener.extract:
            try:
                gname = get_base_name(name)
            except:
                gname = None
        if gname is not None:
            cap, f_name = GoogleDriveHelper().drive_list(gname, True)
            if cap:
                dupmsg = f"⚠️ {listener.tag} Download kamu dihentikan karena: <code>{gname}</code> <b><u>sudah ada di Drive</u></b>"
                sendFile(listener.bot, listener.message, f_name, dupmsg)
                return
    if any([ZIP_UNZIP_LIMIT, TORRENT_DIRECT_LIMIT]):
        arch = any([listener.extract, listener.isZip])
        limit = None
        if ZIP_UNZIP_LIMIT is not None and arch:
            mssg = f'Zip/Unzip limit {ZIP_UNZIP_LIMIT}GB'
            limit = ZIP_UNZIP_LIMIT
        elif TORRENT_DIRECT_LIMIT is not None:
            mssg = f'Torrent/Direct limit {TORRENT_DIRECT_LIMIT}GB'
            limit = TORRENT_DIRECT_LIMIT
        if limit is not None:
            LOGGER.info('Checking File/Folder Size...')
            if size > limit * 1024**3:
                msg = f'⚠️ {listener.tag} {mssg}.\nUkuran File/Folder kamu adalah {get_readable_file_size(size)}.'
                return sendMessage(msg, listener.bot, listener.message)
    LOGGER.info(f"Download Name: {name}")
    drive = GoogleDriveHelper(name, path, size, listener)
    gid = ''.join(SystemRandom().choices(ascii_letters + digits, k=12))
    download_status = GdDownloadStatus(drive, size, listener, gid)
    with download_dict_lock:
        download_dict[listener.uid] = download_status
    listener.onDownloadStart()
    sendStatusMessage(listener.message, listener.bot)
    drive.download(link)
    if gdrive_sharer:
        drive.deletefile(link)
