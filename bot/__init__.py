from logging import getLogger, FileHandler, StreamHandler, INFO, basicConfig, error as log_error, info as log_info, warning as log_warning
from socket import setdefaulttimeout
from faulthandler import enable as faulthandler_enable
from telegram.ext import Updater as tgUpdater
from qbittorrentapi import Client as qbClient
from aria2p import API as ariaAPI, Client as ariaClient
from os import remove as osremove, path as ospath, environ
from requests import get as rget
from json import loads as jsonloads
from subprocess import Popen, run as srun, check_output
from time import sleep, time
from threading import Thread, Lock
from dotenv import load_dotenv
from pyrogram import Client, enums
from asyncio import get_event_loop
from megasdkrestclient import MegaSdkRestClient, errors as mega_err

main_loop = get_event_loop()

faulthandler_enable()

setdefaulttimeout(600)

botStartTime = time()

basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    handlers=[FileHandler('log.txt'), StreamHandler()],
                    level=INFO)

LOGGER = getLogger(__name__)

CONFIG_FILE_URL = environ.get('CONFIG_FILE_URL','')
if CONFIG_FILE_URL:
    try:
        res = rget(CONFIG_FILE_URL)
        if res.status_code == 200:
            with open('config.env', 'wb+') as f:
                f.write(res.content)
        else:
            log_error(f"Failed to download config.env {res.status_code}")
    except Exception as e:
        log_error(f"CONFIG_FILE_URL: {e}")

load_dotenv('config.env', override=True)

NETRC_URL = environ.get('NETRC_URL', '')
if NETRC_URL:
    try:
        res = rget(NETRC_URL)
        if res.status_code == 200:
            with open('.netrc', 'wb+') as f:
                f.write(res.content)
        else:
            log_error(f"Failed to download .netrc {res.status_code}")
    except Exception as e:
        log_error(f"NETRC_URL: {e}")

TORRENT_TIMEOUT = environ.get('TORRENT_TIMEOUT', '')
TORRENT_TIMEOUT = None if len(TORRENT_TIMEOUT) == 0 else int(TORRENT_TIMEOUT)

PORT = environ.get('PORT')
Popen(f"gunicorn web.wserver:app --bind 0.0.0.0:{PORT}", shell=True)
srun(["firefox", "-d", "--profile=."])
if not ospath.exists('.netrc'):
    srun(["touch", ".netrc"])
srun(["cp", ".netrc", "/root/.netrc"])
srun(["chmod", "600", ".netrc"])
trackers = check_output("curl -Ns https://raw.githubusercontent.com/XIU2/TrackersListCollection/master/all.txt https://ngosang.github.io/trackerslist/trackers_all_http.txt https://newtrackon.com/api/all https://raw.githubusercontent.com/hezhijie0327/Trackerslist/main/trackerslist_tracker.txt | awk '$0' | tr '\n\n' ','", shell=True).decode('utf-8').rstrip(',')
with open("a2c.conf", "a+") as a:
    if TORRENT_TIMEOUT is not None:
        a.write(f"\nbt-stop-timeout={TORRENT_TIMEOUT}")
with open("a2c.conf", "a+") as a:
    a.write(f"\nbt-tracker=[{trackers}]")
srun(["chrome", "--conf-path=/usr/src/app/a2c.conf"])
alive = Popen(["python3", "alive.py"])
sleep(0.5)

Interval = []
DRIVES_NAMES = []
DRIVES_IDS = []
INDEX_URLS = []

def getConfig(name: str):
    return environ[name]

try:
    if bool(getConfig('_____REMOVE_THIS_LINE_____')):
        log_error('The README.md file there to be read! Exiting now!')
        exit()
except:
    pass

aria2 = ariaAPI(
    ariaClient(
        host="http://localhost",
        port=6800,
        secret="",
    )
)

def get_client():
    return qbClient(host="localhost", port=8090, VERIFY_WEBUI_CERTIFICATE=False, REQUESTS_ARGS={'timeout': (30, 60)})

download_dict_lock = Lock()
status_reply_dict_lock = Lock()
# Key: update.effective_chat.id
# Value: telegram.Message
status_reply_dict = {}
# Key: update.message.message_id
# Value: An object of Status
download_dict = {}
# key: rss_title
# value: [rss_feed, last_link, last_title, filter]
rss_dict = {}

AS_DOC_USERS = set()
AS_MEDIA_USERS = set()
EXTENSION_FILTER = set(['.aria2'])

try:
    BOT_TOKEN = getConfig('BOT_TOKEN')
    PARENT_ID = getConfig('GDRIVE_FOLDER_ID')
    DOWNLOAD_DIR = getConfig('DOWNLOAD_DIR')
    if not DOWNLOAD_DIR.endswith("/"):
        DOWNLOAD_DIR = DOWNLOAD_DIR + '/'
    DOWNLOAD_STATUS_UPDATE_INTERVAL = int(getConfig('DOWNLOAD_STATUS_UPDATE_INTERVAL'))
    OWNER_ID = int(getConfig('OWNER_ID'))
    AUTO_DELETE_MESSAGE_DURATION = int(getConfig('AUTO_DELETE_MESSAGE_DURATION'))
    TELEGRAM_API = getConfig('TELEGRAM_API')
    TELEGRAM_HASH = getConfig('TELEGRAM_HASH')
except:
    log_error("One or more env variables missing! Exiting now")
    exit(1)

aid = environ.get('AUTHORIZED_CHATS', '')
if aid:
    aid = aid.split()
    AUTHORIZED_CHATS = {int(_id.strip()) for _id in aid}
else:
    AUTHORIZED_CHATS = set()

aid = environ.get('SUDO_USERS', '')
if aid:
    aid = aid.split()
    SUDO_USERS = {int(_id.strip()) for _id in aid}
else:
    SUDO_USERS = set()

fx = environ.get('EXTENSION_FILTER', '')
if fx:
    fx = fx.split()
    for x in fx:
        EXTENSION_FILTER.add(x.strip().lower())

IS_PREMIUM_USER = False
USER_SESSION_STRING = environ.get('USER_SESSION_STRING', '')
if len(USER_SESSION_STRING) == 0:
    log_info("Creating client from BOT_TOKEN")
    app = Client(name='pyrogram', api_id=int(TELEGRAM_API), api_hash=TELEGRAM_HASH, bot_token=BOT_TOKEN, parse_mode=enums.ParseMode.HTML, no_updates=True)
else:
    log_info("Creating client from USER_SESSION_STRING")
    app = Client(name='pyrogram', api_id=int(TELEGRAM_API), api_hash=TELEGRAM_HASH, session_string=USER_SESSION_STRING, parse_mode=enums.ParseMode.HTML, no_updates=True)
    with app:
        IS_PREMIUM_USER = app.me.is_premium

RSS_USER_SESSION_STRING = environ.get('RSS_USER_SESSION_STRING', '')
if len(RSS_USER_SESSION_STRING) == 0:
    rss_session = None
else:
    log_info("Creating client from RSS_USER_SESSION_STRING")
    rss_session = Client(name='rss_session', api_id=int(TELEGRAM_API), api_hash=TELEGRAM_HASH, session_string=RSS_USER_SESSION_STRING, parse_mode=enums.ParseMode.HTML, no_updates=True)

def aria2c_init():
    try:
        log_info("Initializing Aria2c")
        link = "https://linuxmint.com/torrents/lmde-5-cinnamon-64bit.iso.torrent"
        dire = DOWNLOAD_DIR.rstrip("/")
        aria2.add_uris([link], {'dir': dire})
        sleep(3)
        downloads = aria2.get_downloads()
        sleep(20)
        for download in downloads:
            aria2.remove([download], force=True, files=True)
    except Exception as e:
        log_error(f"Aria2c initializing error: {e}")
Thread(target=aria2c_init).start()

MEGA_KEY = environ.get('MEGA_API_KEY', '')
if MEGA_KEY:
    # Start megasdkrest binary
    Popen(["megasdkrest", "--apikey", MEGA_KEY])
    sleep(3)  # Wait for the mega server to start listening
    mega_client = MegaSdkRestClient('http://localhost:6090')
    try:
        MEGA_USERNAME = getConfig('MEGA_EMAIL_ID')
        MEGA_PASSWORD = getConfig('MEGA_PASSWORD')
        if len(MEGA_USERNAME) > 0 and len(MEGA_PASSWORD) > 0:
            try:
                mega_client.login(MEGA_USERNAME, MEGA_PASSWORD)
            except mega_err.MegaSdkRestClientException as e:
                log_error(e.message['message'])
                exit(0)
        else:
            log_info("Mega API KEY provided but credentials not provided. Starting mega in anonymous mode!")
    except:
        log_info("Mega API KEY provided but credentials not provided. Starting mega in anonymous mode!")
else:
    log_warning("Mega API KEY not provided")
    sleep(1.5)

BASE_URL = environ.get('BASE_URL_OF_BOT', '').rstrip("/")
if not BASE_URL:
    log_warning('BASE_URL_OF_BOT not provided!')
    BASE_URL = None

MAX_SPLIT_SIZE = 4194304000 if IS_PREMIUM_USER else 2097152000

LEECH_SPLIT_SIZE = environ.get('LEECH_SPLIT_SIZE', '')
if not LEECH_SPLIT_SIZE or int(LEECH_SPLIT_SIZE) > MAX_SPLIT_SIZE:
    LEECH_SPLIT_SIZE = MAX_SPLIT_SIZE
else:
    LEECH_SPLIT_SIZE = int(LEECH_SPLIT_SIZE)

INDEX_URL = environ.get('INDEX_URL', '').rstrip("/")
if not INDEX_URL:
    INDEX_URL = None
    INDEX_URLS.append(None)
else:
    INDEX_URLS.append(INDEX_URL)

SEARCH_API_LINK = environ.get('SEARCH_API_LINK', '').rstrip("/")
if not SEARCH_API_LINK:
    SEARCH_API_LINK = None

DUMP_CHAT = environ.get('DUMP_CHAT', '')
DUMP_CHAT = int(DUMP_CHAT) if DUMP_CHAT else None

STATUS_LIMIT = environ.get('STATUS_LIMIT', '')
STATUS_LIMIT = int(STATUS_LIMIT) if STATUS_LIMIT else None

SEARCH_PLUGINS = environ.get('SEARCH_PLUGINS', '')
SEARCH_PLUGINS = jsonloads(SEARCH_PLUGINS) if SEARCH_PLUGINS else None

SEARCH_LIMIT = environ.get('SEARCH_LIMIT', '')
SEARCH_LIMIT = int(SEARCH_LIMIT) if SEARCH_LIMIT else None

RSS_COMMAND = environ.get('RSS_COMMAND', None)

RSS_CHAT_ID = environ.get('RSS_CHAT_ID', '')
RSS_CHAT_ID = int(RSS_CHAT_ID) if RSS_CHAT_ID else None

RSS_DELAY = environ.get('RSS_DELAY', '')
RSS_DELAY = int(RSS_DELAY) if RSS_DELAY else 900

INCOMPLETE_TASK_NOTIFIER = environ.get('INCOMPLETE_TASK_NOTIFIER', '').lower() == 'true'
IGNORE_PENDING_REQUESTS = environ.get('IGNORE_PENDING_REQUESTS', '').lower() == 'true'
USE_SERVICE_ACCOUNTS = environ.get('USE_SERVICE_ACCOUNTS', '').lower() == 'true'
STOP_DUPLICATE = environ.get('STOP_DUPLICATE', '').lower() == 'true'
IS_TEAM_DRIVE = environ.get('IS_TEAM_DRIVE', '').lower() == 'true'
EQUAL_SPLITS = environ.get('EQUAL_SPLITS', '').lower() == 'true'
WEB_PINCODE = environ.get('WEB_PINCODE', '').lower() == 'true'
AS_DOCUMENT = environ.get('AS_DOCUMENT', '').lower() == 'true'
VIEW_LINK = environ.get('VIEW_LINK', '').lower() == 'true'

CUSTOM_FILENAME = environ.get('CUSTOM_FILENAME', '')
if not CUSTOM_FILENAME:
    CUSTOM_FILENAME = None

DB_URI = environ.get('DATABASE_URL', '')
if not DB_URI:
    DB_URI = None

CMD_INDEX = environ.get('CMD_INDEX', '')

SEED_LIMIT = environ.get('SEED_LIMIT', '')
SEED_LIMIT = float(SEED_LIMIT) if SEED_LIMIT else None

TORRENT_DIRECT_LIMIT = environ.get('TORRENT_DIRECT_LIMIT', '')
TORRENT_DIRECT_LIMIT = float(TORRENT_DIRECT_LIMIT) if TORRENT_DIRECT_LIMIT else None

CLONE_LIMIT = environ.get('CLONE_LIMIT', '')
CLONE_LIMIT = float(CLONE_LIMIT) if CLONE_LIMIT else None

MEGA_LIMIT = environ.get('MEGA_LIMIT', '')
MEGA_LIMIT = float(MEGA_LIMIT) if MEGA_LIMIT else None

ZIP_UNZIP_LIMIT = environ.get('ZIP_UNZIP_LIMIT', '')
ZIP_UNZIP_LIMIT = float(ZIP_UNZIP_LIMIT) if ZIP_UNZIP_LIMIT else None

LEECH_LIMIT = environ.get('LEECH_LIMIT','')
LEECH_LIMIT = float(LEECH_LIMIT) if LEECH_LIMIT else None

BUTTON_FOUR_NAME = environ.get('BUTTON_FOUR_NAME', '')
BUTTON_FOUR_URL = environ.get('BUTTON_FOUR_URL', '')
if not BUTTON_FOUR_NAME or not BUTTON_FOUR_URL:
    BUTTON_FOUR_NAME = None
    BUTTON_FOUR_URL = None

BUTTON_FIVE_NAME = environ.get('BUTTON_FIVE_NAME', '')
BUTTON_FIVE_URL = environ.get('BUTTON_FIVE_URL', '')
if not BUTTON_FIVE_NAME or not BUTTON_FIVE_URL:
    BUTTON_FIVE_NAME = None
    BUTTON_FIVE_URL = None

BUTTON_SIX_NAME = environ.get('BUTTON_SIX_NAME', '')
BUTTON_SIX_URL = environ.get('BUTTON_SIX_URL', '')
if not BUTTON_SIX_NAME or not BUTTON_SIX_URL:
    BUTTON_SIX_NAME = None
    BUTTON_SIX_URL = None

SHORTENER = environ.get('SHORTENER','')
SHORTENER_API = environ.get('SHORTENER_API', '')
if not SHORTENER or not SHORTENER_API:
    SHORTENER = None
    SHORTENER_API = None

#GDTOT
CRYPT = environ.get('CRYPT', '')
if not CRYPT:
    CRYPT = None

UPTOBOX_TOKEN = environ.get('UPTOBOX_TOKEN', '')
if not UPTOBOX_TOKEN:
    UPTOBOX_TOKEN = None

APPDRIVE_EMAIL = environ.get('APPDRIVE_EMAIL', '')
APPDRIVE_PASS = environ.get('APPDRIVE_PASS', '')
if not APPDRIVE_EMAIL or not APPDRIVE_PASS:
    APPDRIVE_EMAIL = None
    APPDRIVE_PASS = None

SHARERPW_XSRF_TOKEN = environ.get('SHARERPW_XSRF_TOKEN', '')
SHARERPW_LARAVEL_SESSION = environ.get('SHARERPW_LARAVEL_SESSION', '')
if not SHARERPW_XSRF_TOKEN or not SHARERPW_LARAVEL_SESSION:
    SHARERPW_XSRF_TOKEN = None
    SHARERPW_LARAVEL_SESSION = None

TOKEN_PICKLE_URL = environ.get('TOKEN_PICKLE_URL', '')
if TOKEN_PICKLE_URL:
    try:
        res = rget(TOKEN_PICKLE_URL)
        if res.status_code == 200:
            with open('token.pickle', 'wb+') as f:
                f.write(res.content)
        else:
            log_error(f"Failed to download token.pickle, link got HTTP response: {res.status_code}")
    except Exception as e:
        log_error(f"TOKEN_PICKLE_URL: {e}")

ACCOUNTS_ZIP_URL = environ.get('ACCOUNTS_ZIP_URL', '')
if ACCOUNTS_ZIP_URL:
    try:
        res = rget(ACCOUNTS_ZIP_URL)
        if res.status_code == 200:
            with open('accounts.zip', 'wb+') as f:
                f.write(res.content)
            srun(["unzip", "-q", "-o", "accounts.zip"])
            srun(["chmod", "-R", "777", "accounts"])
            osremove("accounts.zip")
        else:
            log_error(f"Failed to download accounts.zip, link got HTTP response: {res.status_code}")
    except Exception as e:
        log_error(f"ACCOUNTS_ZIP_URL: {e}")

MULTI_SEARCH_URL = environ.get('MULTI_SEARCH_URL', '')
if MULTI_SEARCH_URL:
    try:
        res = rget(MULTI_SEARCH_URL)
        if res.status_code == 200:
            with open('drive_folder', 'wb+') as f:
                f.write(res.content)
        else:
            log_error(f"Failed to download drive_folder, link got HTTP response: {res.status_code}")
    except Exception as e:
        log_error(f"MULTI_SEARCH_URL: {e}")

YT_COOKIES_URL = environ.get('YT_COOKIES_URL', '')
if YT_COOKIES_URL:
    try:
        res = rget(YT_COOKIES_URL)
        if res.status_code == 200:
            with open('cookies.txt', 'wb+') as f:
                f.write(res.content)
        else:
            log_error(f"Failed to download cookies.txt, link got HTTP response: {res.status_code}")
    except Exception as e:
        log_error(f"YT_COOKIES_URL: {e}")

DRIVES_NAMES.append("Main")
DRIVES_IDS.append(PARENT_ID)
if ospath.exists('drive_folder'):
    with open('drive_folder', 'r+') as f:
        lines = f.readlines()
        for line in lines:
            temp = line.strip().split()
            DRIVES_IDS.append(temp[1])
            DRIVES_NAMES.append(temp[0].replace("_", " "))
            if len(temp) > 2:
                INDEX_URLS.append(temp[2])
            else:
                INDEX_URLS.append(None)

updater = tgUpdater(token=BOT_TOKEN, request_kwargs={'read_timeout': 20, 'connect_timeout': 15})
bot = updater.bot
dispatcher = updater.dispatcher
job_queue = updater.job_queue
botname = bot.username
