import ada_url
import base64

from yt_dlp.extractor.common import InfoExtractor, ExtractorError
from yt_dlp.utils import multipart_encode

class HentaiHavenIE(InfoExtractor):
    _VALID_URL = r'https?://hentaihaven\.com/video/(?P<id>[\w\-_]+).*'
    _CIPHER_MAP = bytes.maketrans(b'NOPQRSTUVWXYZABCDEFGHIJKLMnopqrstuvwxyzabcdefghijklm',
                                  b'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz')

    def _decipher_sec_token(self, s):
        b = s.encode('ascii')
        for _ in range(3):
            b = b.translate(self._CIPHER_MAP)
            b = base64.b64decode(b)
        return b.decode('ascii')

    def _real_extract(self, url):
        video_id = self._match_id(url)

        page = self._download_webpage(url, video_id)
        video_title = self._html_search_regex(r'chapter-heading" class="h3">([^<]+)', page, 'title')
        embed_url = self._search_regex(r'([^"]+/wp-content/plugins/player-logic/player\.php[^"]+)' , page, 'embed')

        real_page = self._download_webpage(embed_url, video_id)
        cipher_text = self._html_search_meta('x-secure-token', real_page).lstrip('sha512-')
        interim = self._parse_json(self._decipher_sec_token(cipher_text), video_id)
        raw_payload, mime = multipart_encode({
            'action': 'zarat_get_data_player_ajax',
            'a': interim['en'],
            'b': interim['iv']
        })
        
        result = self._download_json(ada_url.join_url(interim['uri'], './api.php'), video_id,
                                     headers={'Content-Type': mime}, data=raw_payload)

        if not result['status']:
            raise ExtractorError("Unable to extract JWPlayer data", video_id, ie=HentaiHavenIE.ie_key())

        formats = []
        subtitles = {}

        # MP4 source; sometimes limited to 720p
        source = result['data']['sources'][0]['src']

        fmts, subs = self._extract_m3u8_formats_and_subtitles(source, video_id, m3u8_id='h264')
        formats.extend(fmts)
        subtitles.update(subs)

        if result['data']['isOctopus']:
            fmts, subs = self._extract_m3u8_formats_and_subtitles(
                ada_url.join_url(source, './playlist_vp9.m3u8'), video_id, m3u8_id='vp9')
            formats.extend(fmts)
            subtitles.update(subs)            

        return {
            'id': video_id,
            'title': video_title,
            'formats': formats,
            'subtitles': subtitles 
        }
