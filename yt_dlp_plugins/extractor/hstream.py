import json
import urllib.parse

import yarl

from Cryptodome.Hash import SHA1
from yt_dlp.extractor.common import InfoExtractor
from ..utils import urljoinpath

# Git-style hashes
def domain_hash(url):
    url = yarl.URL(url)
    return SHA1.new(url.host.encode('ascii')).hexdigest()[:6]

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

        formats = []
        for domain in video['stream_domains']:
            cdn_url = urljoinpath(domain, video['stream_url'].replace('\\', '/'))

            for quality in ('720', '1080'):
                manifest_url = urljoinpath(cdn_url, f'./{quality}/manifest.mpd')
                results = self._extract_mpd_formats(manifest_url, video_id,
                                                    mpd_id=f'{quality}-{domain_hash(manifest_url)}')
                formats.extend(results)

        subtitles = {
            'en': [{
                'url': urljoinpath(cdn_url, './eng.ass'),
                'ext': 'ass'
            }]
        }

        # These are AI-translated subtitles; so expect slop ;)
        extra_subtitles = video.get('extra_subtitles') or {}
        for lang in extra_subtitles:
            if lang != 'en':
                subtitles[lang] = [{
                    'url': urljoinpath(cdn_url, f'./autotrans/{lang}.ass'),
                    'ext': 'ass'
                }]

        return {
            'id': e_id,
            'title': video.get('title'),
            'formats': formats,
            'subtitles': subtitles
        }
