import itertools
import re
import urllib.parse

from yt_dlp.extractor.common import InfoExtractor
from yt_dlp.utils import (
    ExtractorError,
    clean_html,
    int_or_none,
    traverse_obj,
    unescapeHTML,
    update_url_query,
    url_or_none,
)


_BASE = 'https://rule34video.com'


def _split_csv(s):
    return [p.strip() for p in (s or '').split(',') if p.strip()]


def _extract_video_ids(webpage):
    # Cards repeat each id (overlay link + thumbnail link), so dedupe while
    # keeping document order to preserve the listing order.
    return list(dict.fromkeys(re.findall(r'/video/(\d+)/', webpage)))


def _extract_playlist_ids(webpage):
    return list(dict.fromkeys(re.findall(r'/playlists/(\d+)/', webpage)))


def _video_url_result(extractor, video_id):
    return extractor.url_result(
        f'{_BASE}/video/{video_id}/', Rule34VideoIE, video_id)


def _playlist_url_result(extractor, playlist_id):
    return extractor.url_result(
        f'{_BASE}/playlists/{playlist_id}/', Rule34VideoPlaylistIE, playlist_id)


class Rule34VideoIE(InfoExtractor):
    IE_NAME = 'rule34video'
    _VALID_URL = r'https?://(?:www\.)?rule34video\.com/video/(?P<id>\d+)(?:/(?P<slug>[^/?#]*))?/?'
    _TESTS = [{
        'url': 'https://rule34video.com/video/4321530/god-s-blessing-on-this-wonderful-kiss-embedded-subtitles/',
        'info_dict': {
            'id': '4321530',
            'ext': 'mp4',
            'title': "God's Blessing on This Wonderful Kiss! (Embedded Subtitles)",
            'duration': 373,
            'timestamp': 1775433600,
            'upload_date': '20260406',
            'age_limit': 18,
            'thumbnail': r're:^https?://.+\.jpg',
            'view_count': int,
            'like_count': int,
            'channel': 'Shiina Ecchi',
            'uploader': 'Shiina Ecchi',
            'categories': ['kono subarashii sekai ni shukufuku wo!', '2D'],
            'tags': list,
        },
        'params': {'skip_download': True},
    }, {
        # Has a 2160p (4K) variant via video_alt_url4
        'url': 'https://rule34video.com/video/3434961/loyalty-nude-drills3d-extended/',
        'info_dict': {
            'id': '3434961',
            'ext': 'mp4',
            'title': 'Loyalty [Nude][Drills3D][Extended]',
            'age_limit': 18,
            'channel': 'Drills3D',
            'categories': ['3D', 'The Last of Us 2'],
        },
        'params': {'skip_download': True},
    }, {
        'url': 'https://rule34video.com/video/4321530/',
        'only_matching': True,
    }]

    # `<key>: 'value'` literal scraped from the flashvars JS block on the
    # video page. Values are single-quoted JS strings, so backslash escapes
    # (e.g. \') must be unwrapped before use.
    _FLASHVAR_RE = re.compile(r"\b{key}\s*:\s*'((?:\\.|[^\\'])*)'")

    @classmethod
    def _flashvar(cls, key, webpage):
        m = cls._FLASHVAR_RE.pattern.format(key=re.escape(key))
        match = re.search(m, webpage)
        if not match:
            return None
        return re.sub(r"\\(['\\])", r'\1', match.group(1))

    def _real_extract(self, url):
        m = self._match_valid_url(url)
        video_id = m.group('id')
        # The site rejects /video/<id>/ with 404 and 301-redirects any non-empty
        # slug to the canonical /video/<id>/<canonical-slug>/. Pass through the
        # user's slug when present so we hit the canonical URL on the first
        # request; otherwise use a placeholder and let the redirect resolve it.
        webpage = self._download_webpage(
            f'{_BASE}/video/{video_id}/{m.group("slug") or "x"}/', video_id)

        # JSON-LD VideoObject is the friendliest metadata source when present,
        # but pages re-rendered through the ad-refresh path drop it, so every
        # field below is also recoverable from the flashvars block or markup.
        ld = self._search_json_ld(webpage, video_id, default={})

        formats = []
        # video_url is the bare-360p stream; video_alt_url{,2,3,4} carry the
        # alternates with `_text` labels like 360p/480p/720p/1080p/4k.
        for key, height_hint in [
            ('video_url', None),
            ('video_alt_url', None),
            ('video_alt_url2', None),
            ('video_alt_url3', None),
            ('video_alt_url4', None),
        ]:
            src = url_or_none(self._flashvar(key, webpage))
            if not src:
                continue
            label = (self._flashvar(f'{key}_text', webpage) or '').lower()
            # `_text` is e.g. '360p', '1080p', '4k'. The bare video_url has no
            # _text - read its height from the filename suffix. 4k carries no
            # numeric height in its label, so handle it explicitly.
            if label == '4k':
                height = 2160
            else:
                m = re.match(r'(\d+)p?$', label)
                height = int_or_none(m.group(1)) if m else None
            if not height:
                fn_match = re.search(r'_(\d+)p?\.mp4', src)
                if fn_match:
                    height = int_or_none(fn_match.group(1))
            formats.append({
                'url': src,
                'ext': 'mp4',
                'format_id': f'{height}p' if height else label or None,
                'height': height,
            })
        if not formats:
            raise ExtractorError('No video sources found', expected=True)

        title = (
            traverse_obj(ld, 'title')
            or self._flashvar('video_title', webpage)
            or self._html_extract_title(webpage, default=video_id))

        thumbnail = (
            url_or_none(traverse_obj(ld, ('thumbnails', 0, 'url')))
            or url_or_none(self._flashvar('preview_url', webpage)))

        duration = int_or_none(traverse_obj(ld, 'duration'))

        # _search_json_ld normalises VideoObject.uploadDate to a unix timestamp.
        timestamp = traverse_obj(ld, 'timestamp', expected_type=int_or_none)

        view_count = traverse_obj(ld, 'view_count', expected_type=int_or_none)
        like_count = traverse_obj(ld, 'like_count', expected_type=int_or_none)

        # flashvars give us comma-separated strings; the first model is the
        # uploading studio/artist, treat it as the channel.
        categories = _split_csv(self._flashvar('video_categories', webpage))
        tags = _split_csv(self._flashvar('video_tags', webpage))
        models = _split_csv(self._flashvar('video_models', webpage))
        channel = models[0] if models else None

        description = clean_html(traverse_obj(ld, 'description')) or None

        return {
            'id': video_id,
            'title': title,
            'description': description,
            'thumbnail': thumbnail,
            'duration': duration,
            'timestamp': timestamp,
            'view_count': view_count,
            'like_count': like_count,
            'age_limit': 18,
            'channel': channel,
            'uploader': channel,
            'formats': formats,
            'categories': categories or None,
            'tags': tags or None,
        }


class _Rule34VideoListBaseIE(InfoExtractor):
    """Pagination helpers for the KVS-style listing pages on rule34video.

    Every list page (categories, models, tags, search, member tabs, /my/*)
    renders the first batch of cards inline and exposes a
    `<div id="<block_id>_pagination">` block when more pages exist. The same
    URL with `?mode=async&function=get_block&block_id=<block_id>&from=NN`
    returns the HTML of page NN as a partial fragment. Search uses
    `from_videos` + `from_albums` instead of `from`.
    """

    def _paginate(
        self, base_url, playlist_id, *, ids_from=_extract_video_ids,
        async_pagination_keys=('from',), first_page=None,
    ):
        # ``first_page`` lets the caller hand in a webpage they already had
        # to fetch (e.g. to extract a title) so we don't request page 1 twice.
        webpage = first_page if first_page is not None else self._download_webpage(
            base_url, playlist_id)

        seen = set()
        for vid in ids_from(webpage):
            if vid not in seen:
                seen.add(vid)
                yield vid

        block_id = self._search_regex(
            r'id="([a-z_]+)_pagination"', webpage, 'block id', default=None)
        if not block_id:
            return
        # The pagination block exposes one anchor per visible page with a
        # `from*:NN` data-parameter. The parameter name varies by page type
        # (`from`, `from_videos`, `from_videos+from_albums`), so match any
        # name beginning with `from`. Take the max as the last page.
        page_numbers = [
            int(n) for n in re.findall(
                r'data-parameters="(?:[^"]*;)?from[a-z_+]*:0*(\d+)"', webpage)
        ]
        total_pages = max(page_numbers) if page_numbers else 0
        if total_pages <= 1:
            return

        for page_num in itertools.count(2):
            if page_num > total_pages:
                return
            query = {
                'mode': 'async',
                'function': 'get_block',
                'block_id': block_id,
                'sort_by': 'post_date',
            }
            for k in async_pagination_keys:
                query[k] = f'{page_num:02d}'
            page_url = update_url_query(base_url, query)
            chunk = self._download_webpage(
                page_url, playlist_id, note=f'Downloading page {page_num}',
                fatal=False)
            if not chunk:
                return
            new_ids = [vid for vid in ids_from(chunk) if vid not in seen]
            if not new_ids:
                return
            for vid in new_ids:
                seen.add(vid)
                yield vid

    def _video_entries(self, base_url, playlist_id, **kwargs):
        for vid in self._paginate(base_url, playlist_id, **kwargs):
            yield _video_url_result(self, vid)

    def _playlist_entries(self, base_url, playlist_id, **kwargs):
        for pid in self._paginate(
            base_url, playlist_id,
            ids_from=_extract_playlist_ids, **kwargs,
        ):
            yield _playlist_url_result(self, pid)


def _title_text(webpage, fallback):
    title = clean_html(unescapeHTML(re.sub(
        r'\s+', ' ',
        next(iter(re.findall(r'<title>([^<]+)</title>', webpage)), ''),
    ))).strip()
    return title or fallback


def _h1_text(webpage, fallback):
    h1 = next(iter(re.findall(
        r'<h1[^>]*class="title(?:_video)?"[^>]*>([\s\S]*?)</h1>', webpage)), '')
    h1 = re.sub(r'<span\s+class="total_results">[^<]+</span>', '', h1)
    return clean_html(re.sub(r'\s+', ' ', h1)).strip() or fallback


class Rule34VideoPlaylistIE(_Rule34VideoListBaseIE):
    IE_NAME = 'rule34video:playlist'
    _VALID_URL = r'https?://(?:www\.)?rule34video\.com/playlists/(?P<id>\d+)(?:/[^/?#]*)?/?'
    _TESTS = [{
        'url': 'https://rule34video.com/playlists/124556/2d-animations27/',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        playlist_id = self._match_id(url)
        webpage = self._download_webpage(url, playlist_id)
        title = _h1_text(webpage, playlist_id)
        return self.playlist_result(
            self._video_entries(url, playlist_id, first_page=webpage),
            playlist_id, title)


class Rule34VideoModelIE(_Rule34VideoListBaseIE):
    IE_NAME = 'rule34video:model'
    _VALID_URL = r'https?://(?:www\.)?rule34video\.com/models/(?P<id>[a-z0-9\-]+)/?(?:\?|$)'
    _TESTS = [{
        'url': 'https://rule34video.com/models/seejaydj/',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        slug = self._match_id(url)
        return self.playlist_result(
            self._video_entries(url, slug), slug, slug)


class Rule34VideoCategoryIE(_Rule34VideoListBaseIE):
    IE_NAME = 'rule34video:category'
    _VALID_URL = r'https?://(?:www\.)?rule34video\.com/categories/(?P<id>[a-z0-9\-]+)/?(?:\?|$)'
    _TESTS = [{
        'url': 'https://rule34video.com/categories/2d/',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        slug = self._match_id(url)
        return self.playlist_result(
            self._video_entries(url, slug), slug, slug)


class Rule34VideoTagIE(_Rule34VideoListBaseIE):
    IE_NAME = 'rule34video:tag'
    _VALID_URL = r'https?://(?:www\.)?rule34video\.com/tags/(?P<id>\d+)/?(?:\?|$)'
    _TESTS = [{
        'url': 'https://rule34video.com/tags/1877/',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        tag_id = self._match_id(url)
        return self.playlist_result(
            self._video_entries(url, tag_id), tag_id, f'tag-{tag_id}')


class Rule34VideoMemberUploadsIE(_Rule34VideoListBaseIE):
    IE_NAME = 'rule34video:member:uploads'
    # Match both the bare profile and the explicit /videos/ tab. The bare
    # profile renders extra cards (sidebar suggestions) - paginating the
    # canonical /videos/ tab keeps results uniform.
    _VALID_URL = r'https?://(?:www\.)?rule34video\.com/members/(?P<id>\d+)(?:/videos)?/?(?:\?|$)'
    _TESTS = [{
        'url': 'https://rule34video.com/members/180930/videos/',
        'only_matching': True,
    }, {
        'url': 'https://rule34video.com/members/180930/',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        member_id = self._match_id(url)
        videos_url = f'{_BASE}/members/{member_id}/videos/'
        webpage = self._download_webpage(videos_url, member_id)
        username = _title_text(webpage, member_id).removesuffix("'s Videos")
        return self.playlist_result(
            self._video_entries(videos_url, member_id, first_page=webpage),
            member_id, f"{username}'s Videos",
            uploader=username, uploader_id=member_id, uploader_url=videos_url)


class Rule34VideoMemberFavoritesIE(_Rule34VideoListBaseIE):
    IE_NAME = 'rule34video:member:favorites'
    _VALID_URL = r'https?://(?:www\.)?rule34video\.com/members/(?P<id>\d+)/favourites/videos/?(?:\?|$)'
    _TESTS = [{
        'url': 'https://rule34video.com/members/98965/favourites/videos/',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        member_id = self._match_id(url)
        return self.playlist_result(
            self._video_entries(url, member_id),
            f'{member_id}-favorites', f'member-{member_id}-favorites')


class Rule34VideoMemberPlaylistsIE(_Rule34VideoListBaseIE):
    IE_NAME = 'rule34video:member:playlists'
    _VALID_URL = r'https?://(?:www\.)?rule34video\.com/members/(?P<id>\d+)/playlists/?(?:\?|$)'
    _TESTS = [{
        'url': 'https://rule34video.com/members/180930/playlists/',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        member_id = self._match_id(url)
        return self.playlist_result(
            self._playlist_entries(url, member_id),
            f'{member_id}-playlists', f'member-{member_id}-playlists')


class Rule34VideoSearchIE(_Rule34VideoListBaseIE):
    IE_NAME = 'rule34video:search'
    # Three shapes from the site: /search/<query>/, /search/?<filters>, and
    # /search/<query>/?<filters>. The path query is hyphenated (spaces ->
    # dashes), filters are repeated `tag_ids`, `category_ids`, `model_ids`.
    _VALID_URL = (
        r'https?://(?:www\.)?rule34video\.com/search/'
        r'(?:(?P<id>[^/?#]+)/?)?(?:\?(?P<query>[^#]+))?')
    _TESTS = [{
        'url': 'https://rule34video.com/search/ayaka/',
        'only_matching': True,
    }, {
        'url': 'https://rule34video.com/search/?model_ids=283',
        'only_matching': True,
    }, {
        'url': 'https://rule34video.com/search/?tag_ids=all,423&category_ids=all,2',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        m = self._match_valid_url(url)
        path_query = m.group('id') or ''
        filter_query = m.group('query') or ''
        playlist_id = urllib.parse.unquote(path_query) or filter_query or 'search'
        # Search pagination needs both `from_videos` and `from_albums`. The
        # site sends them as the same number but rejects requests with only
        # one of them, so we mirror them.
        return self.playlist_result(
            self._video_entries(
                url, playlist_id,
                async_pagination_keys=('from_videos', 'from_albums')),
            playlist_id, playlist_id)


class _Rule34VideoMyBaseIE(_Rule34VideoListBaseIE):
    """The /my/* tabs require auth cookies. The site redirects anonymous
    requests to `/?login` while still returning 200, so detect the final
    URL and raise a clear error instead of silently extracting the homepage.
    """
    _PATH = ''
    _PLAYLIST_ID = ''

    def _real_extract(self, url):
        _, urlh = self._download_webpage_handle(url, self._PLAYLIST_ID)
        if '/my/' not in urlh.url:
            raise ExtractorError(
                f'{self._PATH} requires login. Pass --cookies or '
                '--cookies-from-browser', expected=True)
        return self.playlist_result(
            self._entries(url), self._PLAYLIST_ID, self._PLAYLIST_ID)

    def _entries(self, url):  # pragma: no cover - subclasses override
        raise NotImplementedError


class Rule34VideoMyFavoritesIE(_Rule34VideoMyBaseIE):
    IE_NAME = 'rule34video:my:favorites'
    _VALID_URL = r'https?://(?:www\.)?rule34video\.com/my/favourites/videos/?(?:\?|$)'
    _PATH = '/my/favourites/videos/'
    _PLAYLIST_ID = 'my-favorites'
    _TESTS = [{
        'url': 'https://rule34video.com/my/favourites/videos/',
        'only_matching': True,
    }]

    def _entries(self, url):
        return self._video_entries(url, self._PLAYLIST_ID)


class Rule34VideoMyVideosIE(_Rule34VideoMyBaseIE):
    IE_NAME = 'rule34video:my:videos'
    _VALID_URL = r'https?://(?:www\.)?rule34video\.com/my/videos/?(?:\?|$)'
    _PATH = '/my/videos/'
    _PLAYLIST_ID = 'my-videos'
    _TESTS = [{
        'url': 'https://rule34video.com/my/videos/',
        'only_matching': True,
    }]

    def _entries(self, url):
        return self._video_entries(url, self._PLAYLIST_ID)


class Rule34VideoMyHistoryIE(_Rule34VideoMyBaseIE):
    IE_NAME = 'rule34video:my:history'
    _VALID_URL = r'https?://(?:www\.)?rule34video\.com/my/history/?(?:\?|$)'
    _PATH = '/my/history/'
    _PLAYLIST_ID = 'my-history'
    _TESTS = [{
        'url': 'https://rule34video.com/my/history/',
        'only_matching': True,
    }]

    def _entries(self, url):
        return self._video_entries(url, self._PLAYLIST_ID)


class Rule34VideoMySubscriptionsIE(_Rule34VideoMyBaseIE):
    IE_NAME = 'rule34video:my:subscriptions'
    _VALID_URL = r'https?://(?:www\.)?rule34video\.com/my/subscriptions/?(?:\?|$)'
    _PATH = '/my/subscriptions/'
    _PLAYLIST_ID = 'my-subscriptions'
    _TESTS = [{
        'url': 'https://rule34video.com/my/subscriptions/',
        'only_matching': True,
    }]

    def _entries(self, url):
        return self._video_entries(url, self._PLAYLIST_ID)


class Rule34VideoMyPlaylistsIE(_Rule34VideoMyBaseIE):
    IE_NAME = 'rule34video:my:playlists'
    _VALID_URL = r'https?://(?:www\.)?rule34video\.com/my/playlists/?(?:\?|$)'
    _PATH = '/my/playlists/'
    _PLAYLIST_ID = 'my-playlists'
    _TESTS = [{
        'url': 'https://rule34video.com/my/playlists/',
        'only_matching': True,
    }]

    def _entries(self, url):
        return self._playlist_entries(url, self._PLAYLIST_ID)
