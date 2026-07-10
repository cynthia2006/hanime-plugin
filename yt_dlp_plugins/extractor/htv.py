import json
import subprocess
import time

from base64 import urlsafe_b64encode, urlsafe_b64decode

from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes

from yt_dlp.extractor.common import InfoExtractor
from yt_dlp.utils import str_or_none, int_or_none, urljoin, ExtractorError

# NOTE Bun will not be supported because Anthropic's AI slop.
from yt_dlp.utils._jsruntime import DenoJsRuntime


def into_base64(o):
    return urlsafe_b64encode(o).decode('ascii').rstrip('=')

def from_base64(o):
    if isinstance(o, str):
        o = o.encode('ascii', errors='ignore')

    return urlsafe_b64decode(o.ljust((len(o) // 4 + 1) * 4, b'='))


class HanimeTVIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?hanime\.tv/(videos/hentai|hentai/video)/(?P<id>[a-z0-9\-]+)'
    _JS_PREAMBLE = '''
    delete globalThis.process;

    var window = new Proxy({
        top: { location: { origin: "https://hanime.tv" } },
        addEventListener: () => {},
        dispatchEvent: () => {},
    }, {
        set(o, k, v) {
            if (k == "ssignature" || k == "stime")
                console.log(k, v);
            
            o[k] = v;
            return true;
        }
    });

    globalThis.window = window;
    '''
    _AES_KEY = bytes.fromhex("5d657a4dcb0bad1c637ff2e221059b10ff17ae39fe855003e846918941f4ebe3")
    _AES_HEADER = bytes.fromhex("6874762d696e7365637572652d7631")
    
    # TODO add _TESTS

    def __init__(self):
        self._runtime = DenoJsRuntime()
        self._script = None

        if not self._runtime.info:
            raise ExtractorError("DenoJS is required for hanime.tv extractor")

    def _cache_credential_generator(self, url, video_id):
        self._script = self._JS_PREAMBLE
        self._script += self._download_webpage(url, video_id,
            headers={'Referer': 'https://hanime.tv/'}, note='Loading WASM authenticator')

    def _generate_credentials(self):
        output = subprocess.run([self._runtime.info.path, 'run', '-'],
            input=self._script, encoding='utf-8', text=True, capture_output=True)

        if output.returncode == 0:
            creds = dict(line.split(' ', 1) for line in output.stdout.split('\n', 1))
            return creds.get('ssignature'), creds.get('stime')
        else:
            raise ExtractorError("Signature and timestamp generation failed")

    @classmethod
    def _digest_token(cls, o):
        o = json.dumps(o)
        iv = get_random_bytes(12)

        cipher = AES.new(cls._AES_KEY, AES.MODE_GCM, iv)
        cipher.update(cls._AES_HEADER)
        ciphertext, tag = cipher.encrypt_and_digest(o.encode('utf-8'))

        return into_base64(json.dumps({
            'v': 1,
            'alg': 'AES-256-GCM',
            'iv': into_base64(iv),
            'tag': into_base64(tag),
            'data': into_base64(ciphertext)
        }).encode('utf-8'))

    @classmethod
    def _parse_token(cls, o):
        o = json.loads(from_base64(o))

        cipher = AES.new(cls._AES_KEY, AES.MODE_GCM, from_base64(o['iv']))
        cipher.update(cls._AES_HEADER)
        plaintext = cipher.decrypt_and_verify(from_base64(o['data']), from_base64(o['tag']))

        return json.loads(plaintext.decode('utf-8'))

    def _real_extract(self, url):
        video_id = self._match_id(url)
        page = self._download_webpage(url, video_id)

        # This script has to be downloaded once per instantiation of this extractor.
        if not self._script:
            script_url = self._search_regex( 
                r'<script.*src="(https://hanime-cdn\.com/js/vendor\.[^"]+)', page, "signature generator"
            )
            self._cache_credential_generator(script_url, video_id)
       
        ssignature, stime = self._generate_credentials()
        payload = self._digest_token({
            'timestamp_unix': time.time_ns() // 1000000000,
            'directive': 'htv_player_handshake',
            'slug': video_id,
        })
        _, handle = self._download_webpage_handle("https://auth.hanime.tv/api/v11/handshake", video_id,
            headers={
                'Accept': 'application/json',
                'Content-Type': 'application/json',
                'Origin': 'https://hanime.tv',
                'Referer': 'https://hanime.tv/',
                'X-Csrf-Token': 'null',
                'X-Signature': ssignature,
                'X-Time': stime,
                'X-Signature-Version': 'web2'
            },
            data=json.dumps({'token': payload}).encode('ascii'),
            note='Downloading video manifest')

        manifest = self._parse_token(handle.headers['X-Token'])
        formats = []

        for source in manifest['sources']:
            # NOTE Premium streams are not supported and will not be supported in future.
            if source['kind'] == 'normal':
                result = self._extract_m3u8_formats(
                    urljoin('https://hanime.tv', source['src']), video_id, ext='mp4', m3u8_id=source['label'])
                formats.extend(result)

        video_title = self._html_search_regex(r'<h1[^>]+?>([^<]+)', page, 'Video title')
        return {
            'id': video_id,
            'title': video_title,
            'formats': formats
        }
