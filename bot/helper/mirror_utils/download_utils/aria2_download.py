from time import sleep, time
from os import remove

from bot import aria2, download_dict_lock, download_dict, STOP_DUPLICATE, SEED_LIMIT,TORRENT_DIRECT_LIMIT, ZIP_UNZIP_LIMIT, LOGGER, STORAGE_THRESHOLD, BASE_URL
from bot.helper.mirror_utils.upload_utils.gdriveTools import GoogleDriveHelper
from bot.helper.ext_utils.bot_utils import is_magnet, getDownloadByGid, new_thread, get_readable_file_size, bt_selection_buttons
from bot.helper.mirror_utils.status_utils.aria_download_status import AriaDownloadStatus
from bot.helper.telegram_helper.message_utils import sendMarkup, sendStatusMessage, sendMessage, deleteMessage, update_all_messages, sendFile
from bot.helper.ext_utils.fs_utils import get_base_name, check_storage_threshold, clean_unwanted


@new_thread
def __onDownloadStarted(api, gid):
    download = api.get_download(gid)
    if download.is_metadata:
        LOGGER.info(f'onDownloadStarted: {gid} Metadata')
        sleep(1)
        if dl := getDownloadByGid(gid):
            listener = dl.listener()
            if listener.select:
                metamsg = f"ℹ️ {listener.tag} Downloading Metadata, tunggu sebentar. Gunakan file .torrent untuk menghindari proses ini."
                meta = sendMessage(metamsg, listener.bot, listener.message)
                while True:
                    if download.is_removed or download.followed_by_ids:
                        deleteMessage(listener.bot, meta)
                        break
                    download = download.live
        return
    else:
        LOGGER.info(f'onDownloadStarted: {download.name} - Gid: {gid}')
    try:
        if any([STOP_DUPLICATE, TORRENT_DIRECT_LIMIT, ZIP_UNZIP_LIMIT, STORAGE_THRESHOLD]):
            sleep(1)
            if dl := getDownloadByGid(gid):
                listener = dl.listener()
                download = api.get_download(gid)
                LOGGER.info('Checking File/Folder Size...')
                limit = None
                size = download.total_length
                arch = any([listener.isZip, listener.extract])
                if STORAGE_THRESHOLD is not None:
                    acpt = check_storage_threshold(size, arch, True)
                    # True if files allocated, if allocation disabled remove True arg
                    if not acpt:
                        msg = f'You must leave {STORAGE_THRESHOLD}GB free storage.'
                        msg += f'\nYour File/Folder size is {get_readable_file_size(size)}'
                        listener.onDownloadError(msg)
                        api.remove([download], force=True, files=True)
                        return
                if ZIP_UNZIP_LIMIT is not None and arch:
                    mssg = f'Zip/Unzip limit {ZIP_UNZIP_LIMIT}GB'
                    limit = ZIP_UNZIP_LIMIT
                elif TORRENT_DIRECT_LIMIT is not None:
                    mssg = f'Torrent/Direct limit {TORRENT_DIRECT_LIMIT}GB'
                    limit = TORRENT_DIRECT_LIMIT
                if limit is not None:
                    if size > limit * 1024**3:
                        listener.onDownloadError(f'{mssg}. Ukuran file/folder kamu adalah {get_readable_file_size(size)}')
                        api.remove([download], force=True, files=True)
                        return
                if listener.isLeech or listener.select:
                    return
                if not download.is_torrent:
                    sleep(3)
                    download = download.live
                LOGGER.info('Checking File/Folder if already in Drive...')
                sname = download.name
                if listener.isZip:
                    sname = sname + ".zip"
                elif listener.extract:
                    try:
                        sname = get_base_name(sname)
                    except:
                        sname = None
                if sname is not None:
                    cap, f_name = GoogleDriveHelper().drive_list(sname, True)
                    if cap:
                        listener.onDownloadError(f'<code>{sname}</code> <b><u>sudah ada di Drive</u></b>', listfile=f_name)
                        api.remove([download], force=True, files=True)
                        return
    except Exception as e:
        LOGGER.error(f"{e} onDownloadStart: {gid} check duplicate and size check didn't pass")

@new_thread
def __onDownloadComplete(api, gid):
    try:
        download = api.get_download(gid)
    except:
        return
    if download.followed_by_ids:
        new_gid = download.followed_by_ids[0]
        LOGGER.info(f'Gid changed from {gid} to {new_gid}')
        if dl := getDownloadByGid(new_gid):
            listener = dl.listener()
            if BASE_URL is not None and listener.select:
                api.client.force_pause(new_gid)
                SBUTTONS = bt_selection_buttons(new_gid)
                msg = f"⛔️ {listener.tag} Download kamu dijeda. Silahkan pilih file kemudian tekan tombol Selesai Memilih untuk memulai download."
                sendMarkup(msg, listener.bot, listener.message, SBUTTONS)
    elif download.is_torrent:
        if dl := getDownloadByGid(gid):
            if hasattr(dl, 'listener'):
                listener = dl.listener()
                if hasattr(listener, 'uploaded'):
                    LOGGER.info(f"Cancelling Seed: {download.name} onDownloadComplete")
                    listener.onUploadError(f"Seeding stopped with Ratio: {dl.ratio()} and Time: {dl.seeding_time()}")
                    api.remove([download], force=True, files=True)
    else:
        LOGGER.info(f"onDownloadComplete: {download.name} - Gid: {gid}")
        if dl := getDownloadByGid(gid):
            dl.listener().onDownloadComplete()
            api.remove([download], force=True, files=True)

@new_thread
def __onBtDownloadComplete(api, gid):
    seed_start_time = time()
    sleep(1)
    download = api.get_download(gid)
    LOGGER.info(f"onBtDownloadComplete: {download.name} - Gid: {gid}")
    if dl := getDownloadByGid(gid):
        listener = dl.listener()
        if listener.select:
            res = download.files
            for file_o in res:
                if not file_o.selected:
                    try:
                        remove(file_o.path)
                    except:
                        pass
            clean_unwanted(download.dir)
        if listener.seed:
            try:
                api.set_options({'max-upload-limit': '0'}, [download])
            except Exception as e:
                LOGGER.error(f'{e} You are not able to seed because you added global option seed-time=0 without adding specific seed_time for this torrent')
        else:
            api.client.force_pause(gid)
        listener.onDownloadComplete()
        if listener.seed:
            if SEED_LIMIT is not None:
                _ratio = float(api.client.get_option(gid).get('seed-ratio'))
                LOGGER.info(f"SEED_LIMIT seeding ratio: {_ratio}")
                size = (download.total_length * _ratio) if _ratio != 0 else download.total_length
                if size > SEED_LIMIT * 1024**3:
                    listener.onUploadError(f"Seeding torrent limit {SEED_LIMIT} GB. Ukuran File/folder yang akan di seeding adalah {get_readable_file_size(size)}")
                    api.remove([download], force=True, files=True)
                    return
            with download_dict_lock:
                if listener.uid not in download_dict:
                    api.remove([download], force=True, files=True)
                    return
                download_dict[listener.uid] = AriaDownloadStatus(gid, listener)
                download_dict[listener.uid].start_time = seed_start_time
            LOGGER.info(f"Seeding started: {download.name} - Gid: {gid}")
            download = download.live
            if download.is_complete:
                if dl := getDownloadByGid(gid):
                    LOGGER.info(f"Cancelling Seed: {download.name}")
                    listener.onUploadError(f"Seeding stopped with Ratio: {dl.ratio()} and Time: {dl.seeding_time()}")
                    api.remove([download], force=True, files=True)
            else:
                listener.uploaded = True
                update_all_messages()
        else:
            api.remove([download], force=True, files=True)

@new_thread
def __onDownloadStopped(api, gid):
    sleep(6)
    if dl := getDownloadByGid(gid):
        download = api.get_download(gid)
        dl.listener().onDownloadError(f'<code>{download.name.replace("[METADATA]","")}</code> adalah <b><u>Dead torrent</u></b>')

@new_thread
def __onDownloadError(api, gid):
    LOGGER.info(f"onDownloadError: {gid}")
    error = "None"
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
                                  on_bt_download_complete=__onBtDownloadComplete,
                                  timeout=60)

def add_aria2c_download(link: str, path, listener, filename, auth, select, ratio, seed_time):
    args = {'dir': path, 'max-upload-limit': '1K'}
    if filename:
        args['out'] = filename
    if auth:
        args['header'] = f"authorization: {auth}"
    if ratio:
        args['seed-ratio'] = ratio
    if seed_time:
        args['seed-time'] = seed_time
    if 'static.romsget.io' in link:
        args['header'] = "Referer: https://www.romsget.io/"

    if is_magnet(link):
        download = aria2.add_magnet(link, args)
    else:
        download = aria2.add_uris([link], args)

    if download.error_message:
        error = str(download.error_message).replace('<', ' ').replace('>', ' ')
        LOGGER.info(f"Download Error: {error}")
        return sendMessage(f"⚠️ {listener.tag} Oops terjadi error atau sepertinya link kamu bukan direct link.\n\n<code>aria2_addDownload_error: {error}</code>", listener.bot, listener.message)
    with download_dict_lock:
        download_dict[listener.uid] = AriaDownloadStatus(download.gid, listener)
        LOGGER.info(f"Aria2Download started: {download.gid}")
    listener.onDownloadStart()
    if not select:
        sendStatusMessage(listener.message, listener.bot)

start_listener()
