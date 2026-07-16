import re
import json
import urllib.parse

from yt_dlp.extractor.common import InfoExtractor


class HstreamIE(InfoExtractor):
    _VALID_URL = r'https?://hstream\.moe/hentai/(?P<id>[a-z0-9\-]+)'

    def _extract_cookie(self, name):
        for cookie in self._downloader.cookiejar:
            if cookie.name == name:
                return cookie.value

    def _real_extract(self, url):
        # NOTE This has no use in the API itself; just a part of the webpage URL.
        video_id = self._match_id(url)

        page = self._download_webpage(url, video_id)
        e_id = self._search_regex(r'e_id" type="hidden" value="([^"]*)', page, 'episode id')

        payload = json.dumps({'episode_id': e_id})
        xsrf_token = self._extract_cookie('XSRF-TOKEN')

        video = self._download_json('https://hstream.moe/player/api', video_id, headers={
                    'Content-Type': 'application/json',
                    'Referer': url,
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-Xsrf-Token': urllib.parse.unquote(xsrf_token)
                }, data=payload.encode('utf-8'))

        # NOTE Although all CDNs essentially provide same resources, based on the client's
        # country, the speeds may differ.
        orig_urlopen = self._downloader.urlopen

        def _urlopen_with_normalized_path(req, *args, **kwargs):
            if isinstance(req, str):
                req = req.replace('\\', '/').replace('%5C', '/').replace('%5c', '/')
            elif hasattr(req, 'url') and isinstance(req.url, str):
                req.url = req.url.replace('\\', '/').replace('%5C', '/').replace('%5c', '/')
            return orig_urlopen(req, *args, **kwargs)

        self._downloader.urlopen = _urlopen_with_normalized_path

        cdn_url = '{}/{}'.format(video['stream_domains'][0], video['stream_url']).replace('\\', '/')
        formats = []
        
        for res in ('720', '1080', '2160'):
            results = self._extract_mpd_formats('{}/{}/manifest.mpd'.format(cdn_url, res),
                                                 video_id, mpd_id=res)

            formats.extend(results)

        poster_url = '{}/{}'.format('https://hstream.moe', video.get('poster'))

        subtitles = {}
        subtitles['en'] = [{
            'url': f'{cdn_url}/eng.ass',
            'ext': 'ass'
        }]

        extra_subtitles = video.get('extra_subtitles') or {}
        for lang in extra_subtitles:
            if lang != 'en':
                subtitles[lang] = [{
                    'url': f'{cdn_url}/autotrans/{lang}.ass',
                    'ext': 'ass'
                }]

        return {
            'id': e_id,
            'title': video.get('title'),
            'thumbnail': poster_url,
            'formats': formats,
            'subtitles': subtitles
        }
