from pathlib import Path
import requests
import subprocess
import json
import html
import re
import os

from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

m3u8DL_RE = 'N_m3u8DL-RE.exe'

files_to_delete = ["key.txt"]
for file_name in files_to_delete:
    if os.path.exists(file_name):
        os.remove(file_name)
        print(f"{file_name} file successfully deleted.")

link = input('Enter link here (dev menu -> Network -> Filter: smil): ')

token = re.findall(r'auth=(.*?)&', link)[0].strip()
headers = {
    'Accept': 'application/json, text/plain, */*',
    'Origin': 'https://mediasetinfinity.mediaset.it',
    'Referer': 'https://mediasetinfinity.mediaset.it/',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36',
}

response = requests.get(link, headers=headers).text

mpd = re.findall(r'<video src=\"(.*?)\"', response)[0].strip()
pid = re.findall(r'\|pid=(.*?)\|', response)[0].strip()
aid = re.findall(r'value=\"aid=(.*?)\|', response)[0].strip()
pgid = re.findall(r'\|pgid=(.*?)\|', response)[0].strip()

lic_url = f'https://widevine.entitlement.theplatform.eu/wv/web/ModularDrm/getRawWidevineLicense?releasePid={pid}&account=http%3A%2F%2Faccess.auth.theplatform.com%2Fdata%2FAccount%2F{aid}&schema=1.0&token={token}'


def format_episode_number(number):
    number_str = str(number)
    if len(number_str) == 1:
        return '0' + number_str
    return number_str


def replace_invalid_chars(title: str) -> str:
    invalid_chars = {'<': '\u02c2', '>': '\u02c3',
                     ':': '\u02d0', '"': '\u02ba', '/': '\u2044',
                     '\\': '\u29f9', '|': '\u01c0', '?': '\u0294',
                     '*': '\u2217'}

    return ''.join(invalid_chars.get(c, c) for c in title)


headers2 = {
    'Accept': 'application/json, text/plain, */*',
    'Connection': 'keep-alive',
    'Origin': 'https://mediasetinfinity.mediaset.it',
    'Referer': 'https://mediasetinfinity.mediaset.it/',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36',
}

params2 = {
    'form': 'cjson',
    'httpError': 'true',
}

response2 = requests.get('https://feed.entertainment.tv.theplatform.eu/f/PR1GhC/mediaset-prod-all-programs-v2/guid/-/' +
                         pgid+'', params=params2, headers=headers2).json()

try:
    show_title = response2['mediasetprogram$brandTitle']
    ep_title = response2['title']
    tvSeasonNumber = response2['tvSeasonNumber']
    tvSeasonEpisodeNumber = response2['tvSeasonEpisodeNumber']

    zerofill_seasonNumber = format_episode_number(tvSeasonNumber)
    zerofill_episodeNumber = format_episode_number(tvSeasonEpisodeNumber)

    title = f'{show_title} - S{zerofill_seasonNumber}E{zerofill_episodeNumber} - {ep_title}'
except KeyError:
    m_title = response2['title']

    title = f'{m_title}'

a_title = replace_invalid_chars(title)
# print(f'\n{a_title}')

# srt
try:
    pattern = r'(http.*?\.srt)\" lang=\"(.*?)\"'
    matches = re.findall(pattern, response)
    unique_links = set()
    srt_link_list = []

    for match in matches:
        srt_link, lang = match
        if srt_link not in unique_links:
            unique_links.add(srt_link)
            srt_link_list.append({"srt_link": srt_link, "lang": lang})

            import requests

            headers_srt = {
                'authority': 'statictxt.msf.cdn.mediaset.net',
                'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.0.0 Safari/537.36',
            }

            for srt in srt_link_list:
                srt_links = srt['srt_link']
                langs = srt['lang']

                response_srt = requests.get(
                    srt_links, headers=headers_srt).text

                with open(f"{a_title}.{langs}.srt", "w", encoding="utf-8") as file:
                    file.write(response_srt)
except IndexError:
    print('\n[no srt]\n')

####################

headers03 = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
    'Connection': 'keep-alive',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.0.0 Safari/537.36',
}

response03 = requests.get(mpd, headers=headers03, verify=False).text

try:
    pssh = re.findall(
        r'<cenc:pssh>(.{20,170})</cenc:pssh>', response03)[0].strip()

    api_url = "https://cdrm-project.com/api"
    headers = {
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (Ktesttemp, like Gecko) Chrome/90.0.4430.85 Safari/537.36'}
    r = requests.post(api_url, headers=headers, json={
        "license": lic_url, "pssh": pssh}).text

    keys = []
    extracted_keys = json.loads(r)["keys"]
    print(lic_url)
    print(pssh)
    print(a_title)
    print(mpd)
    for key in extracted_keys:
        key = "--key " + key["key"]
        print(key)
        print()
        print(
            f'N_m3u8DL-RE.exe "{mpd}" --save-name "{a_title}" {key} -M mkv -ss all -sv best -sa best')
        # append to command.txt
        with open("command.txt", "a") as file:
            file.write(
                f'N_m3u8DL-RE.exe "{mpd}" --save-name "{a_title}" {key} -M mkv -ss all -sv best -sa best\n\n')
    exit(0)
    for key in extracted_keys:
        keys.append("--key " + key["key"])

    for key in keys:
        print(key, file=open("key.txt", "w"))

    with open("key.txt", "r") as fs:
        ke_ys = fs.readlines()
        ke_ys = ke_ys[0].strip().split()

    print()
    subprocess.run([m3u8DL_RE,
                    '-M', 'format=mkv:muxer=ffmpeg',
                    '--auto-select',
                    '--concurrent-download',
                    '--del-after-done',
                    '--log-level', 'INFO',
                    '--save-name', 'video',
                    mpd, *ke_ys])
except IndexError:
    print('\n[INFO]drm free\n')
    subprocess.run([m3u8DL_RE,
                    '-M', 'format=mkv:muxer=ffmpeg',
                    '--auto-select',
                    '--concurrent-download',
                    '--del-after-done',
                    '--log-level', 'INFO',
                    '--save-name', 'video', mpd])

try:
    Path('video.mkv').rename(''+a_title+'.mkv')
    print(f'{a_title}.mkv \nall done!\n')
except FileNotFoundError:
    print("[ERROR] no mkv file")

for file_name in files_to_delete:
    if os.path.exists(file_name):
        os.remove(file_name)
        print(f"{file_name} file successfully deleted.")
