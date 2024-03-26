import yt_dlp


def list_formats(video_url):
    ydl_opts = {
        'listformats': True,  # Command line option equivalent: --list-formats
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([video_url])


if __name__ == '__main__':
    # Replace VIDEO_URL with your actual video URL
    video_url = 'https://open.spotify.com/intl-de/track/0WtQtjAiPA115TTqHQmbLN?si=c605a1b733e84f1d'
    list_formats(video_url)
