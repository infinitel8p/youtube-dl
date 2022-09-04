import youtube_dl
import logging

logger = logging.getLogger(__name__)


class MyLogger(object):
    def debug(self, msg):
        logger.info(msg)

    def warning(self, msg):
        logger.warning(msg)

    def error(self, msg):
        logger.error(msg)


def run(video_url):
    try:
        video_info = youtube_dl.YoutubeDL().extract_info(
            url=video_url, download=False
        )
    except youtube_dl.utils.DownloadError as e:
        logger.error(f'{video_url} is not a valid URL.')
    filename = f"{video_info['title']}.mp3"
    options = {
        'format': 'bestaudio/best',
        'keepvideo': False,
        'outtmpl': filename,
        'writethumbnail': True,
        # 'postprocessors': [
        #    {'key': 'EmbedThumbnail', 'already_have_thumbnail': False, }]
        'logger': MyLogger(),
    }

    try:
        with youtube_dl.YoutubeDL(options) as ydl:
            ydl.download([video_info['webpage_url']])
        logger.info("Download complete:{}".format(filename))
    except youtube_dl.utils.DownloadError as e:
        print("https://github.com/wez/atomicparsley/releases/latest")

# https://www.youtube.com/watch?v=M4vRIizuXF4
