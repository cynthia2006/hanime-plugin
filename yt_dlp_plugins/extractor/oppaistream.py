from yt_dlp.extractor.common import InfoExtractor

from ..utils import urljoinpath

class OppaiStreamIE(InfoExtractor):
    _VALID_URL = r'https://oppai\.stream/watch\?e=(?P<id>[\w-]+)'

    def _real_extract(self, url):
        video_id = self._match_id(url)
        page = self._download_webpage(url, video_id)
        base_url, manifest = self._search_regex(
            r"(?:')(https://s2\.myspacecat\.pictures/[^']+)(?:'\+startsource\+')/([^']+)", page, 'manifest url', group=(1, 2))
        title = self._html_search_regex(r'<h1.*line-2">(.*)</h1>', page, 'title')
        poster = self._search_regex(r"class='cover-img-in' src='(https://myspacecat\.pictures.*?png)", page, 'poster', default=None)

        formats = []

        for res in ('720', '1080', '4k'):
            result = self._extract_mpd_formats(
                urljoinpath(base_url, res, manifest), video_id, mpd_id=res)
            
            for fmt in result:
                fmt['http_headers'] = {'Referer': 'https://oppai.stream/'}
            
            formats.extend(result)
            
        return {
            'id': video_id,
            'title': title,
            'formats': formats,
            'thumbnail': poster
        }
