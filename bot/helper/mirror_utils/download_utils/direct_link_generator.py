# Copyright (C) 2019 The Raphielscape Company LLC.
#
# Licensed under the Raphielscape Public License, Version 1.c (the "License");
# you may not use this file except in compliance with the License.
#
""" Helper Module containing various sites direct links generators. This module is copied and modified as per need
from https://github.com/AvinashReddy3108/PaperplaneExtended . I hereby take no credit of the following code other
than the modifications. See https://github.com/AvinashReddy3108/PaperplaneExtended/commits/master/userbot/modules/direct_links.py
for original authorship. """

import requests
import re

from base64 import b64decode
from urllib.parse import urlparse, unquote
from json import loads as jsnloads
from lk21 import Bypass
from cfscrape import create_scraper
from bs4 import BeautifulSoup
from base64 import standard_b64encode
from time import sleep

from bot import LOGGER, UPTOBOX_TOKEN, CRYPT
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.ext_utils.bot_utils import is_gdtot_link
from bot.helper.ext_utils.exceptions import DirectDownloadLinkException

fmed_list = ['fembed.net', 'fembed.com', 'femax20.com', 'fcdn.stream', 'feurl.com', 'layarkacaxxi.icu',
             'naniplay.nanime.in', 'naniplay.nanime.biz', 'naniplay.com', 'mm9842.com']


def direct_link_generator(link: str, host):
    """ direct links generator """
    if 'youtube.com' in host or 'youtu.be' in host:
        raise DirectDownloadLinkException(f"ERROR: Use /{BotCommands.WatchCommand} to mirror Youtube link\nUse /{BotCommands.ZipWatchCommand} to make zip of Youtube playlist")
    elif 'zippyshare.com' in host:
        return zippy_share(link)
    elif 'yadi.sk' in host or 'disk.yandex.com' in host or 'disk.yandex.ru' in host:
        return yandex_disk(link)
    elif 'mediafire.com' in host:
        return mediafire(link)
    elif 'uptobox.com' in host:
        return uptobox(link)
    elif 'uploadhaven.com' in host:
        return uploadhaven(link)
    elif 'osdn.net' in host:
        return osdn(link)
    elif 'github.com' in host:
        return github(link)
    elif 'hxfile.co' in host:
        return hxfile(link)
    elif 'anonfiles.com' in host:
        return anonfiles(link)
    elif 'letsupload.io' in host:
        return letsupload(link)
    elif '1drv.ms' in host:
        return onedrive(link)
    elif 'pixeldrain.com' in host:
        return pixeldrain(link)
    elif 'antfiles.com' in host:
        return antfiles(link)
    elif 'streamtape.com' in host:
        return streamtape(link)
    elif 'bayfiles.com' in host:
        return anonfiles(link)
    elif 'racaty.net' in host:
        return racaty(link)
    elif '1fichier.com' in host:
        return fichier(link)
    elif 'solidfiles.com' in host:
        return solidfiles(link)
    elif 'krakenfiles.com' in host:
        return krakenfiles(link)
    elif 'romsget.io' in host:
        return link if host == 'static.romsget.io' else romsget(link)
    elif is_gdtot_link(link):
        return gdtot(link)
    elif any(x in host for x in fmed_list):
        return fembed(link)
    elif any(x in host for x in ['sbembed.com', 'watchsb.com', 'streamsb.net', 'sbplay.org']):
        return sbembed(link)
    else:
        raise DirectDownloadLinkException(f'No Direct link function found for {link}')

def romsget(url: str) -> str:
    try:
        req = requests.get(url)
        bs1 = BeautifulSoup(req.text, 'html.parser')
#        LOGGER.info(req.text)

        upos = bs1.find('form', {'id':'download-form'}).get('action')
        meid = bs1.find('input', {'id':'mediaId'}).get('name')
        try:
            dlid = bs1.find('button', {'data-callback':'onDLSubmit'}).get('dlid')
        except:
            dlid = bs1.find('div', {'data-callback':'onDLSubmit'}).get('dlid')

        pos = requests.post("https://www.romsget.io"+upos, data={meid:dlid})
        bs2 = BeautifulSoup(pos.text, 'html.parser')
        udl = bs2.find('form', {'name':'redirected'}).get('action')
        prm = bs2.find('input', {'name':'attach'}).get('value')
        return f"{udl}?attach={prm}"
    except Exception as e:
        LOGGER.error(e)
        raise DirectDownloadLinkException("ERROR: Can't extract the link")

def uploadhaven(url: str) -> str:
    ses = requests.Session()
    ses.headers = {'Referer':'https://uploadhaven.com/'}
    req = ses.get(url)
    bs = BeautifulSoup(req.text, 'lxml')
    try:
        form = bs.find("form", {'id':'form-download'})
        postdata = {
            "_token": form.find("input", attrs={"name": "_token"}).get("value"),
            "key": form.find("input", attrs={"name": "key"}).get("value"),
            "time": form.find("input", attrs={"name": "time"}).get("value"),
            "hash": form.find("input", attrs={"name": "hash"}).get("value")
        }
        wait = form.find("span", {'class':'download-timer-seconds d-inline'}).text
        sleep(int(wait.replace('seconds', '').strip()))
        post = ses.post(url, data=postdata)
        dl_url = re.findall('"src", "(.*?)"', post.text)
        return dl_url[0]
    except Exception as e:
        LOGGER.error(e)
        raise DirectDownloadLinkException("ERROR: Can't extract the link")

def uptobox(url: str) -> str:
    """ Uptobox direct link generator
    based on https://github.com/jovanzers/WinTenCermin """
    try:
        link = re.findall(r'\bhttps?://.*uptobox\.com\S+', url)[0]
    except IndexError:
        raise DirectDownloadLinkException("No Uptobox links found\n")
    if UPTOBOX_TOKEN is None:
        LOGGER.error('UPTOBOX_TOKEN not provided!')
        dl_url = link
    else:
        try:
            link = re.findall(r'\bhttp?://.*uptobox\.com/dl\S+', url)[0]
            dl_url = link
        except:
            file_id = re.findall(r'\bhttps?://.*uptobox\.com/(\w+)', url)[0]
            file_link = f'https://uptobox.com/api/link?token={UPTOBOX_TOKEN}&file_code={file_id}'
            req = requests.get(file_link)
            result = req.json()
            if result['message'].lower() == 'success':
                dl_url = result['data']['dlLink']
            elif result['message'].lower() == 'waiting needed':
                waiting_time = result["data"]["waiting"] + 1
                waiting_token = result["data"]["waitingToken"]
                sleep(waiting_time)
                req2 = requests.get(f"{file_link}&waitingToken={waiting_token}")
                result2 = req2.json()
                dl_url = result2['data']['dlLink']
            elif result['message'].lower() == 'you need to wait before requesting a new download link':
                cooldown = divmod(result['data']['waiting'], 60)
                raise DirectDownloadLinkException(f"ERROR: Uptobox sedang cooldown {cooldown[0]} menit {cooldown[1]} detik")
            else:
                LOGGER.info(f"UPTOBOX_ERROR: {result}")
                raise DirectDownloadLinkException(f"ERROR: {result['message']}")
    return dl_url

def zippy_share(url: str) -> str:
    """ Zippyshare direct link generator
    Based on https://github.com/zevtyardt/lk21
    """
    return Bypass().bypass_zippyshare(url)

def yandex_disk(url: str) -> str:
    """ Yandex.Disk direct link generator
    Based on https://github.com/wldhx/yadisk-direct """
    try:
        link = re.findall(r'\b(https?://(yadi.sk|disk.yandex.com|disk.yandex.ru)\S+)', url)[0][0]
    except IndexError:
        return "No Yandex.Disk links found\n"
    api = 'https://cloud-api.yandex.net/v1/disk/public/resources/download?public_key={}'
    try:
        return requests.get(api.format(link)).json()['href']
    except KeyError:
        raise DirectDownloadLinkException("ERROR: File not found/Download limit reached\n")

def mediafire(url: str) -> str:
    """ MediaFire direct link generator """
    try:
        link = re.findall(r'\bhttps?://.*mediafire\.com\S+', url)[0]
    except IndexError:
        raise DirectDownloadLinkException("No MediaFire links found\n")
    try:
        page = BeautifulSoup(requests.get(link).content, 'lxml')
        info = page.find('a', {'aria-label': 'Download file'})
        dl_url = info.get('href')
        return dl_url
    except Exception as e:
        LOGGER.error(e)
        raise DirectDownloadLinkException("ERROR: Can't extract the link")

def osdn(url: str) -> str:
    """ OSDN direct link generator """
    osdn_link = 'https://osdn.net'
    try:
        link = re.findall(r'\bhttps?://.*osdn\.net\S+', url)[0]
    except IndexError:
        raise DirectDownloadLinkException("No OSDN links found\n")
    page = BeautifulSoup(
        requests.get(link, allow_redirects=True).content, 'lxml')
    info = page.find('a', {'class': 'mirror_link'})
    link = unquote(osdn_link + info['href'])
    mirrors = page.find('form', {'id': 'mirror-select-form'}).findAll('tr')
    urls = []
    for data in mirrors[1:]:
        mirror = data.find('input')['value']
        urls.append(re.sub(r'm=(.*)&f', f'm={mirror}&f', link))
    return urls[0]

def github(url: str) -> str:
    """ GitHub direct links generator """
    try:
        re.findall(r'\bhttps?://.*github\.com.*releases\S+', url)[0]
    except IndexError:
        raise DirectDownloadLinkException("No GitHub Releases links found\n")
    download = requests.get(url, stream=True, allow_redirects=False)
    try:
        return download.headers["location"]
    except KeyError:
        raise DirectDownloadLinkException("ERROR: Can't extract the link\n")

def hxfile(url: str) -> str:
    """ Hxfile direct link generator
    Based on https://github.com/zevtyardt/lk21
    """
    return Bypass().bypass_filesIm(url)

def anonfiles(url: str) -> str:
    """ Anonfiles direct link generator
    Based on https://github.com/zevtyardt/lk21
    """
    return Bypass().bypass_anonfiles(url)

def letsupload(url: str) -> str:
    """ Letsupload direct link generator
    Based on https://github.com/zevtyardt/lk21
    """
    dl_url = ''
    try:
        link = re.findall(r'\bhttps?://.*letsupload\.io\S+', url)[0]
    except IndexError:
        raise DirectDownloadLinkException("No Letsupload links found\n")
    return Bypass().bypass_url(link)

def fembed(link: str) -> str:
    """ Fembed direct link generator
    Based on https://github.com/zevtyardt/lk21
    """
    dl_url= Bypass().bypass_fembed(link)
    count = len(dl_url)
    lst_link = [dl_url[i] for i in dl_url]
    return lst_link[count-1]

def sbembed(link: str) -> str:
    """ Sbembed direct link generator
    Based on https://github.com/zevtyardt/lk21
    """
    session = requests.Session()
    raw = session.get(url)
    soup = BeautifulSoup(raw)

    dl_url = {}
    for a in soup.findAll("a", onclick=re.compile(r"^download_video[^>]+")):
        data = dict(zip(["id", "mode", "hash"], re.findall(
            r"[\"']([^\"']+)[\"']", a["onclick"])))
        data["op"] = "download_orig"

        raw = session.get("https://sbembed.com/dl", params=data)
        soup = BeautifulSoup(raw)

        if (direct := soup.find("a", text=re.compile("(?i)^direct"))):
            dl_url[a.text] = direct["href"]

    count = len(dl_url)
    lst_link = [dl_url[i] for i in dl_url]
    return lst_link[count-1]

def onedrive(link: str) -> str:
    """ Onedrive direct link generator
    Based on https://github.com/UsergeTeam/Userge """
    link_without_query = urlparse(link)._replace(query=None).geturl()
    direct_link_encoded = str(standard_b64encode(bytes(link_without_query, "utf-8")), "utf-8")
    direct_link1 = f"https://api.onedrive.com/v1.0/shares/u!{direct_link_encoded}/root/content"
    resp = requests.head(direct_link1)
    if resp.status_code != 302:
        raise DirectDownloadLinkException("ERROR: Unauthorized link, the link may be private")
    dl_link = resp.next.url
    file_name = dl_link.rsplit("/", 1)[1]
    resp2 = requests.head(dl_link)
    return dl_link

def pixeldrain(url: str) -> str:
    """ Based on https://github.com/yash-dk/TorToolkit-Telegram """
    url = url.strip("/ ")
    file_id = url.split("/")[-1]
    info_link = f"https://pixeldrain.com/api/file/{file_id}/info"
    dl_link = f"https://pixeldrain.com/api/file/{file_id}"
    resp = requests.get(info_link).json()
    if resp["success"]:
        return dl_link
    else:
        raise DirectDownloadLinkException("ERROR: Cant't download due {}.".format(resp["message"]))

def antfiles(url: str) -> str:
    """ Antfiles direct link generator
    Based on https://github.com/zevtyardt/lk21
    """
    return Bypass().bypass_antfiles(url)

def streamtape(url: str) -> str:
    """ Streamtape direct link generator
    Based on https://github.com/zevtyardt/lk21
    """
    return Bypass().bypass_streamtape(url)

def racaty(url: str) -> str:
    """ Racaty direct link generator
    based on https://github.com/SlamDevs/slam-mirrorbot"""
    dl_url = ''
    try:
        link = re.findall(r'\bhttps?://.*racaty\.net\S+', url)[0]
    except IndexError:
        raise DirectDownloadLinkException("No Racaty links found\n")
    scraper = create_scraper()
    r = scraper.get(url)
    soup = BeautifulSoup(r.text, "lxml")
    op = soup.find("input", {"name": "op"})["value"]
    ids = soup.find("input", {"name": "id"})["value"]
    rpost = scraper.post(url, data = {"op": op, "id": ids})
    rsoup = BeautifulSoup(rpost.text, "lxml")
    dl_url = rsoup.find("a", {"id": "uniqueExpirylink"})["href"].replace(" ", "%20")
    return dl_url

def fichier(link: str) -> str:
    """ 1Fichier direct link generator
    Based on https://github.com/Maujar
    """
    link = link.split('&af=')[0]
    regex = r"^([http:\/\/|https:\/\/]+)?.*1fichier\.com\/\?.+"
    gan = re.match(regex, link)
    if not gan:
        raise DirectDownloadLinkException("ERROR: The link you entered is wrong!")
    if "::" in link:
        pswd = link.split("::")[-1]
        url = link.split("::")[-2]
    else:
        pswd = None
        url = link
    try:
        if pswd is None:
            req = requests.post(url)
        else:
            pw = {"pass": pswd}
            req = requests.post(url, data=pw)
    except:
        raise DirectDownloadLinkException("ERROR: Unable to reach 1fichier server!")
    if req.status_code == 404:
        raise DirectDownloadLinkException("ERROR: File not found/The link you entered is wrong!")
    soup = BeautifulSoup(req.content, 'lxml')
    if soup.find("a", {"class": "ok btn-general btn-orange"}) is not None:
        dl_url = soup.find("a", {"class": "ok btn-general btn-orange"})["href"]
        if dl_url is None:
            raise DirectDownloadLinkException("ERROR: Unable to generate Direct Link 1fichier!")
        else:
            return dl_url
    elif len(soup.find_all("div", {"class": "ct_warn"})) == 2:
        str_2 = soup.find_all("div", {"class": "ct_warn"})[-1]
        if "you must wait" in str(str_2).lower():
            numbers = [int(word) for word in str(str_2).split() if word.isdigit()]
            if not numbers:
                raise DirectDownloadLinkException("ERROR: 1fichier is on a limit. Please wait a few minutes/hour.")
            else:
                raise DirectDownloadLinkException(f"ERROR: 1fichier is on a limit. Please wait {numbers[0]} minute.")
        elif "protect access" in str(str_2).lower():
            raise DirectDownloadLinkException(f"ERROR: This link requires a password!\n\n<b>This link requires a password!</b>\n- Insert sign <b>::</b> after the link and write the password after the sign.\n\n<b>Example:</b>\n<code>/{BotCommands.MirrorCommand} https://1fichier.com/?smmtd8twfpm66awbqz04::love you</code>\n\n* No spaces between the signs <b>::</b>\n* For the password, you can use a space!")
        else:
            raise DirectDownloadLinkException("ERROR: Error trying to generate Direct Link from 1fichier!")
    elif len(soup.find_all("div", {"class": "ct_warn"})) == 3:
        str_1 = soup.find_all("div", {"class": "ct_warn"})[-2]
        str_3 = soup.find_all("div", {"class": "ct_warn"})[-1]
        if "you must wait" in str(str_1).lower():
            numbers = [int(word) for word in str(str_1).split() if word.isdigit()]
            if not numbers:
                raise DirectDownloadLinkException("ERROR: 1fichier is on a limit. Please wait a few minutes/hour.")
            else:
                raise DirectDownloadLinkException(f"ERROR: 1fichier is on a limit. Please wait {numbers[0]} minute.")
        elif "bad password" in str(str_3).lower():
            raise DirectDownloadLinkException("ERROR: The password you entered is wrong!")
        else:
            raise DirectDownloadLinkException("ERROR: Error trying to generate Direct Link from 1fichier!")
    else:
        raise DirectDownloadLinkException("ERROR: Error trying to generate Direct Link from 1fichier!")

def solidfiles(url: str) -> str:
    """ Solidfiles direct link generator
    Based on https://github.com/Xonshiz/SolidFiles-Downloader
    By https://github.com/Jusidama18 """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/36.0.1985.125 Safari/537.36'
    }
    pageSource = requests.get(url, headers = headers).text
    mainOptions = str(re.search(r'viewerOptions\'\,\ (.*?)\)\;', pageSource).group(1))
    return jsnloads(mainOptions)["downloadUrl"]

def krakenfiles(page_link: str) -> str:
    """ krakenfiles direct link generator
    Based on https://github.com/tha23rd/py-kraken
    By https://github.com/junedkh """
    page_resp = requests.session().get(page_link)
    soup = BeautifulSoup(page_resp.text, "lxml")
    try:
        token = soup.find("input", id="dl-token")["value"]
    except:
        raise DirectDownloadLinkException(f"Page link is wrong: {page_link}")

    hashes = [
        item["data-file-hash"]
        for item in soup.find_all("div", attrs={"data-file-hash": True})
    ]
    if not hashes:
        raise DirectDownloadLinkException(
            f"Hash not found for : {page_link}")

    dl_hash = hashes[0]

    payload = f'------WebKitFormBoundary7MA4YWxkTrZu0gW\r\nContent-Disposition: form-data; name="token"\r\n\r\n{token}\r\n------WebKitFormBoundary7MA4YWxkTrZu0gW--'
    headers = {
        "content-type": "multipart/form-data; boundary=----WebKitFormBoundary7MA4YWxkTrZu0gW",
        "cache-control": "no-cache",
        "hash": dl_hash,
    }

    dl_link_resp = requests.session().post(
        f"https://krakenfiles.com/download/{hash}", data=payload, headers=headers)

    dl_link_json = dl_link_resp.json()

    if "url" in dl_link_json:
        return dl_link_json["url"]
    else:
        raise DirectDownloadLinkException(
            f"Failed to acquire download URL from kraken for : {page_link}")

def gdtot(url: str) -> str:
    """ Gdtot google drive link generator
    By https://github.com/xcscxr """

    if CRYPT is None:
        raise DirectDownloadLinkException("ERROR: CRYPT cookie not provided")

    match = re.findall(r'https?://(.+)\.gdtot\.(.+)\/\S+\/\S+', url)[0]

    with requests.Session() as client:
        client.cookies.update({'crypt': CRYPT})
        res = client.get(url)
        res = client.get(f"https://{match[0]}.gdtot.{match[1]}/dld?id={url.split('/')[-1]}")
    matches = re.findall('gd=(.*?)&', res.text)
    try:
        decoded_id = b64decode(str(matches[0])).decode('utf-8')
    except:
        raise DirectDownloadLinkException("ERROR: Try in your broswer, mostly file not found! or user limit exceeded!")
    return f'https://drive.google.com/open?id={decoded_id}'

