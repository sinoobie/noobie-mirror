from time import sleep

from bot import aria2, download_dict_lock, download_dict, STOP_DUPLICATE, TORRENT_DIRECT_LIMIT, ZIP_UNZIP_LIMIT, LOGGER, STORAGE_THRESHOLD, BASE_URL
from bot.helper.mirror_utils.upload_utils.gdriveTools import GoogleDriveHelper
from bot.helper.ext_utils.bot_utils import is_magnet, getDownloadByGid, new_thread, get_readable_file_size, bt_selection_buttons
from bot.helper.mirror_utils.status_utils.aria_download_status import AriaDownloadStatus
from bot.helper.telegram_helper.message_utils import sendMarkup, sendStatusMessage, sendMessage, deleteMessage
from bot.helper.ext_utils.fs_utils import get_base_name, check_storage_threshold, clean_unwanted


@new_thread
def __onDownloadStarted(api, gid):
    download = api.get_download(gid)
    dl = getDownloadByGid(gid)
    if download.is_metadata:
        LOGGER.info(f'onDownloadStarted: {gid} Metadata')
        if dl.listener().select:
            metamsg = f"ℹ️ {dl.listener().tag} Downloading Metadata, tunggu sebentar. Gunakan file .torrent untuk menghindari proses ini."
            meta = sendMessage(metamsg, dl.listener().bot, dl.listener().message)
            while True:
                download = api.get_download(gid)
                if download.followed_by_ids:
                    deleteMessage(dl.listener().bot, meta)
                    break
                sleep(1)
        return
    else:
        LOGGER.info(f'onDownloadStarted: {gid}')
    try:
        if any([STOP_DUPLICATE, TORRENT_DIRECT_LIMIT, ZIP_UNZIP_LIMIT, STORAGE_THRESHOLD]):
            if not dl or dl.listener().isLeech or dl.listener().select:
                return
            if not download.is_torrent:
                sleep(3)
                download = api.get_download(gid)
            LOGGER.info('Checking File/Folder if already in Drive...')
            sname = download.name
            if dl.listener().isZip:
                sname = f"{sname}.zip"
            elif dl.listener().extract:
                try:
                    sname = get_base_name(sname)
                except:
                    sname = None
            if sname is not None:
                smsg, button = GoogleDriveHelper().drive_list(sname, True)
                if smsg:
                    api.remove([download], force=True, files=True)
                    dl.listener().onDownloadError(f'<code>{sname}</code> <b><u>sudah ada di Drive</u></b>', markup=True, button=button)
                    return
            if any([ZIP_UNZIP_LIMIT, TORRENT_DIRECT_LIMIT, STORAGE_THRESHOLD]):
                LOGGER.info('Checking File/Folder Size...')
                sleep(1)
                limit = None
                size = download.total_length
                arch = any([dl.listener().isZip, dl.listener().extract])
                if STORAGE_THRESHOLD is not None:
                    acpt = check_storage_threshold(size, arch, True)
                    # True if files allocated, if allocation disabled remove True arg
                    if not acpt:
                        msg = f'You must leave {STORAGE_THRESHOLD}GB free storage.'
                        msg += f'\nYour File/Folder size is {get_readable_file_size(size)}'
                        dl.listener().onDownloadError(msg)
                        return api.remove([download], force=True, files=True)
                if ZIP_UNZIP_LIMIT is not None and arch:
                    mssg = f'Zip/Unzip limit is {ZIP_UNZIP_LIMIT}GB'
                    limit = ZIP_UNZIP_LIMIT
                elif TORRENT_DIRECT_LIMIT is not None:
                    mssg = f'Torrent/Direct limit {TORRENT_DIRECT_LIMIT}GB'
                    limit = TORRENT_DIRECT_LIMIT
                if limit is not None:
                    if size > limit * 1024**3:
                        dl.listener().onDownloadError(f'{mssg}.\nUkuran file/folder kamu adalah {get_readable_file_size(size)}')
                        return api.remove([download], force=True, files=True)
    except Exception as e:
        LOGGER.error(f"{e} onDownloadStart: {gid} check duplicate and size check didn't pass")

@new_thread
def __onDownloadComplete(api, gid):
    download = api.get_download(gid)
    if download.followed_by_ids:
        new_gid = download.followed_by_ids[0]
        LOGGER.info(f'Gid changed from {gid} to {new_gid}')
        if BASE_URL is not None:
            dl = getDownloadByGid(new_gid)
            if dl and dl.listener().select:
                api.client.force_pause(new_gid)
                SBUTTONS = bt_selection_buttons(new_gid)
                msg = f"⛔️ {dl.listener().tag} Download kamu dijeda. Silahkan pilih file kemudian tekan tombol Selesai Memilih untuk memulai download."
                sendMarkup(msg, dl.listener().bot, dl.listener().message, SBUTTONS)
    elif dl := getDownloadByGid(gid):
        LOGGER.info(f"onDownloadComplete: {gid}")
        if dl.listener().select:
            clean_unwanted(dl.path())
        dl.listener().onDownloadComplete()

@new_thread
def __onDownloadStopped(api, gid):
    sleep(6)
    if dl := getDownloadByGid(gid):
        download = api.get_download(gid)
        dl.listener().onDownloadError(f'<code>{download.name.replace("[METADATA]","")}</code> adalah <b><u>Dead torrent</u></b>')

@new_thread
def __onDownloadError(api, gid):
    LOGGER.info(f"onDownloadError: {gid}")
    try:
        download = api.get_download(gid)
        error = download.error_message
        LOGGER.info(f"Download Error: {error}")
    except:
        pass
    if dl := getDownloadByGid(gid):
        dl.listener().onDownloadError(f"Oops terjadi error atau sepertinya link kamu bukan direct link.\n\n<code>aria2_onDownload_error: {error}</code>")

def start_listener():
    aria2.listen_to_notifications(threaded=True,
                                  on_download_start=__onDownloadStarted,
                                  on_download_error=__onDownloadError,
                                  on_download_stop=__onDownloadStopped,
                                  on_download_complete=__onDownloadComplete,
                                  timeout=30)

def add_aria2c_download(link: str, path, listener, filename, auth, select):
    if is_magnet(link):
        download = aria2.add_magnet(link, {'dir': path})
    else:
        if 'static.romsget.io' in link:
            download = aria2.add_uris([link], {'dir': path, 'out': filename, 'header':'Referer: https://www.romsget.io/'})
        else:
            download = aria2.add_uris([link], {'dir': path, 'out': filename, 'header': f"authorization: {auth}"})
    if download.error_message:
        error = str(download.error_message).replace('<', ' ').replace('>', ' ')
        LOGGER.info(f"Download Error: {error}")
        return sendMessage(f"⚠️ {listener.tag} Oops terjadi error atau sepertinya link kamu bukan direct link.\n\n<code>aria2_addDownload_error: {error}</code>", listener.bot, listener.message)
    with download_dict_lock:
        download_dict[listener.uid] = AriaDownloadStatus(download.gid, listener)
        LOGGER.info(f"Started: {download.gid} DIR: {download.dir} ")
    listener.onDownloadStart()
    if not select:
        sendStatusMessage(listener.message, listener.bot)

start_listener()
