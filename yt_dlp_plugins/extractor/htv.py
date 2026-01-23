import subprocess

from yt_dlp.extractor.common import InfoExtractor
from yt_dlp.utils import str_or_none, int_or_none
# TODO Allow any runtime not just Deno.
from yt_dlp.utils._jsruntime import DenoJsRuntime


class HanimeTVIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?hanime\.tv/(videos/hentai|hentai/video)/(?P<id>[a-z0-9\-]+)'
    _JS_PREAMBLE = '''
    delete globalThis.process;

    var window = new Proxy({
        top: { location: { origin: "https://hanime.tv" } },
        addEventListener: (e, cb) => {}
    }, {
        set(o, k, v) {
            if (k == "ssignature" || k == "stime")
                console.log(v);
            
            o[k] = v;
            return true;
        }
    });

    globalThis.window = window;
    '''
    
    # TODO add _TESTS

    def __init__(self):
        self._runtime = DenoJsRuntime()
        self._script = None

    def _cache_program(self, url, video_id):
        self._script = self._JS_PREAMBLE
        self._script += self._download_webpage(url, video_id,
            headers={'Referer': 'https://hanime.tv/'}, note='Caching generator script')

    def _generate_creds(self):
        info = self._runtime.info
        output = subprocess.run([info.path, 'run', '-'],
            input=self._script, text=True, capture_output=True)

        if output.returncode == 0:
            return output.stdout.split('\n', 1)
        else:
            return None

    def _real_extract(self, url):
        slug = self._match_id(url)

        page = self._download_webpage(url, slug)
        title = self._search_regex(r'<h1 class="tv-title">([^<]+)', page, "title")

        # Grab the letter used to indicate which field is the id
        id_offset = ord(self._search_regex(rf'hentai_video:{{id:([^,]+),', page, "id offset"))-ord('a')

        # Grab the fields and extract the video_id from the offset field
        rawfields = self._search_regex(rf'\((null,.*,"{slug}",.*)\)\);', page, "fields")
        fields = list(csv.reader(rawfields.splitlines()))
        video_id = fields[0][id_offset]

        # NOTE This script is unlikely to change, so better cache it.
        if not self._script:
            script_url = self._search_regex( 
                r'<script.*src="(https://hanime-cdn\.com/js/vendor\.[^"]+)', page, "signature generator"
            )
            self._cache_program(script_url, slug)

        ssignature, stime = self._generate_creds()
        self.to_screen(f'Signature: {ssignature}')

        manifest = self._download_json(
            f'https://cached.freeanimehentai.net/api/v8/guest/videos/{video_id}/manifest',
            slug, headers={
                'Accept': 'application/json',
                'Origin': 'https://hanime.tv',
                'Referer': 'https://hanime.tv/',
                'X-Signature': ssignature,
                'X-Time': stime,
                'X-Signature-Version': 'web2'
            }
        )

        formats = []
        servers = manifest['videos_manifest']['servers']
        for server in servers:
            for stream in server['streams']:
                formats.append({
                    'url': stream['url'],
                    'ext': 'mp4',
                    'format_id': str_or_none(stream['id']),
                    'width': int_or_none(stream.get('width')),
                    'height': int_or_none(stream.get('height')),
                    'filesize_approx': int_or_none(stream.get('filesize_mbs'), invscale=1000000),
                })

        return {
            'id': slug,
            'title': title,
            'formats': formats
        }
