from yt_dlp.extractor.common import InfoExtractor
from yt_dlp.networking.common import Request

class OppaiStreamIE(InfoExtractor):
    _VALID_URL = r'https://oppai\.stream/watch\?e=(?P<id>[\w-]+)'
    _MANIFEST_RE = r"(?:')(https://s2\.myspacecat\.pictures/[^']+)(?:'\+startsource\+')/([^']+)"
    _TITLE_RE = r'<h1.*line-2">(.*)</h1>'
    _POSTER_RE = r"class='cover-img-in' src='(https://myspacecat\.pictures.*?png)"

    def _real_extract(self, url):
        video_id = self._match_id(url)
        page = self._download_webpage(url, video_id)
        base_url, manifest = self._search_regex(self._MANIFEST_RE, page, 'manifest url', group=(1, 2))
        title = self._html_search_regex(self._TITLE_RE, page, 'title')
        poster = self._search_regex(self._POSTER_RE, page, 'poster', default=None)

        formats = []

        for res in ('720', '1080', '4k'):
            result = self._extract_mpd_formats(
                '{}/{}/{}'.format(base_url, res, manifest), video_id, mpd_id=res, headers=headers)
            
            for fmt in result:
                fmt['http_headers'] = {'Referer': 'https://oppai.stream/'}
            
            formats.extend(result)
            
        return {
            'id': video_id,
            'title': title,
            'formats': formats,
            'thumbnail': poster
        }
