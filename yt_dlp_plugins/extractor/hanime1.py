import itertools
import re
import urllib.parse

from yt_dlp.extractor.common import InfoExtractor
from yt_dlp.utils import (
    ExtractorError,
    clean_html,
    extract_attributes,
    int_or_none,
    orderedSet,
    traverse_obj,
    unified_strdate,
    url_or_none,
    urljoin,
)


class Hanime1IE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.)?hanime1\.me/watch\?(?:[^#]*&)?v=(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://hanime1.me/watch?v=405849',
        'info_dict': {
            'id': '405849',
            'ext': 'mp4',
            'title': 'ボクの理想の異世界生活 第4話 [中文字幕]',
            'description': 'md5:bf5621c5550daf3796358a5e9b82edfc',
            'duration': 991,
            'age_limit': 18,
            'channel': 'メリー・ジェーン',
            'channel_url': 'https://hanime1.me/search?query=メリー・ジェーン&genre=裏番',
            'uploader': 'メリー・ジェーン',
            'thumbnail': r're:^https?://.+\.jpg',
            'upload_date': '20260417',
            'view_count': int,
            'like_count': int,
            'dislike_count': int,
            'comment_count': int,
            'tags': list,
            'categories': ['裏番'],
        },
        'params': {'skip_download': True},
    }, {
        # Older entry by the same studio, only 720p / 480p available
        'url': 'https://hanime1.me/watch?v=22673',
        'info_dict': {
            'id': '22673',
            'ext': 'mp4',
            'title': 'ショッキングピンク！ 第2話 長坂の戦い  [中文字幕]',
            'channel': 'メリー・ジェーン',
            'categories': ['裏番'],
            'age_limit': 18,
            'duration': 987,
            'upload_date': '20110805',
        },
        'params': {'skip_download': True},
    }, {
        'url': 'https://hanime1.me/watch?v=99690',
        'only_matching': True,
    }, {
        # /watch URL with extra query params (?v=ID&list=...&sort=...)
        'url': 'https://hanime1.me/watch?v=155209&list=435600&sort=latest',
        'only_matching': True,
    }]

    _COUNT_UNITS = {'千': 1_000, '萬': 10_000, '万': 10_000, '億': 100_000_000}

    @classmethod
    def _parse_cjk_count(cls, text):
        if not text:
            return None
        m = re.search(r'([\d.,]+)\s*([千萬万億])?', text)
        if not m:
            return None
        try:
            value = float(m.group(1).replace(',', ''))
        except ValueError:
            return None
        return int(value * cls._COUNT_UNITS.get(m.group(2), 1))

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)

        formats = []
        for tag in re.findall(r'<source\b[^>]*>', webpage):
            attrs = extract_attributes(tag)
            src = url_or_none(attrs.get('src'))
            if not src:
                continue
            height = int_or_none(attrs.get('size'))
            formats.append({
                'url': src,
                'ext': 'mp4',
                'format_id': f'{height}p' if height else None,
                'height': height,
            })
        if not formats:
            raise ExtractorError('No video sources found', expected=True)

        title = self._og_search_title(webpage, default=None)
        if title:
            title = re.sub(r'\s*[-|]\s*Hanime1(?:\.me)?\s*$', '', title)
        else:
            title = self._html_extract_title(webpage, default=video_id)

        channel_href, channel = self._html_search_regex(
            r'<a[^>]*id="video-artist-name"[^>]*href="([^"]+)"[^>]*>\s*([^<]+?)\s*</a>',
            webpage, 'channel', group=(1, 2), default=(None, None))
        channel_url = urljoin(url, channel_href) if channel_href else None

        # The video's genre is the genre param on the artist link, not the
        # genre nav menu at the top of the page (that lists every site genre).
        genre = None
        if channel_url:
            genre = traverse_obj(
                urllib.parse.parse_qs(urllib.parse.urlsplit(channel_url).query),
                ('genre', 0))

        # The view count and upload date are colocated in a single span, e.g.:
        #   觀看次數：183.5萬次  2026-04-17
        # 萬 means 10000 in Chinese - parse_count only handles K/M.
        stats_match = re.search(
            r'觀看次數[：:]\s*([\d.,]+\s*[千萬万億]?)次(?:\s|&nbsp;)*(\d{4}-\d{1,2}-\d{1,2})',
            webpage)
        view_count = self._parse_cjk_count(stats_match.group(1)) if stats_match else None
        upload_date = unified_strdate(stats_match.group(2)) if stats_match else None

        # Hidden form inputs carry raw like/dislike counts, but only render
        # when the visitor is logged in. For logged-out requests fall back to
        # the visible button: `thumb_up</i>100%&nbsp;&nbsp;<span>(16769)</span>`
        # where the parenthesized number is the like count and the percent is
        # likes / (likes + dislikes).
        like_count = int_or_none(self._search_regex(
            r'name="likes-count"[^>]*value="(\d+)"', webpage, 'like count', default=None))
        dislike_count = int_or_none(self._search_regex(
            r'name="unlikes-count"[^>]*value="(\d+)"', webpage, 'dislike count', default=None))
        if like_count is None:
            like_visible = re.search(
                r'thumb_up\s*</i>\s*(\d+)\s*%\s*(?:&nbsp;|\s)*<span>\s*\(\s*(\d+)\s*\)',
                webpage)
            if like_visible:
                like_percent = int(like_visible.group(1))
                like_count = int(like_visible.group(2))
                if dislike_count is None and like_percent > 0:
                    # L + D = L * 100 / percent
                    dislike_count = max(0, round(like_count * 100 / like_percent) - like_count)
        comment_count = int_or_none(self._search_regex(
            r'id="tab-comments-count"[^>]*>\s*(\d+)', webpage, 'comment count', default=None))

        # Prefer the on-page description block (the OG description truncates).
        description = clean_html(self._search_regex(
            r'<div class="video-caption-text[^"]*"[^>]*>([\s\S]*?)</div>',
            webpage, 'description', default=None))
        if not description:
            description = self._og_search_description(webpage, default=None)

        keywords = self._html_search_meta('keywords', webpage, default='') or ''
        tags = [t.strip() for t in keywords.split(',') if t.strip()]

        return {
            'id': video_id,
            'title': title,
            'description': description,
            'thumbnail': self._og_search_thumbnail(webpage, default=None),
            'duration': int_or_none(self._og_search_property(
                'video:duration', webpage, default=None)),
            'formats': formats,
            'age_limit': 18,
            'channel': channel,
            'channel_url': channel_url,
            'uploader': channel,
            'view_count': view_count,
            'like_count': like_count,
            'dislike_count': dislike_count,
            'comment_count': comment_count,
            'upload_date': upload_date,
            'tags': tags,
            'categories': [genre] if genre else None,
        }


class _Hanime1ListBaseIE(InfoExtractor):
    """Shared bits for list/playlist-style extractors.

    Hanime1 has two list-page styles:

    - Paginated (search, subscriptions): the page embeds `urlParams.get('page')
      < TOTAL - 1` in its inline script.
    - Single-page (playlists, user subpages): no pagination JS, every entry is
      rendered up front.

    Subclasses set `_PAGINATED` accordingly. The paginated path mirrors the
    behavior of the original Hanime1SearchIE.
    """
    _PAGINATED = False

    @staticmethod
    def _extract_video_ids(webpage):
        # Cards repeat IDs in thumbnail, title, and overlay links; dedupe in
        # document order so the playlist comes back in the order it was rendered.
        return orderedSet(re.findall(r'/watch\?v=(\d+)', webpage))

    def _video_url_result(self, video_id):
        return self.url_result(
            f'https://hanime1.me/watch?v={video_id}', Hanime1IE, video_id)

    def _paginated_entries(self, base_url, playlist_id):
        seen = set()
        for page_num in itertools.count(1):
            webpage = self._download_webpage(
                base_url, playlist_id, note=f'Downloading page {page_num}',
                fatal=page_num == 1, query={'page': page_num})
            if not webpage:
                return

            found_new = False
            for vid in self._extract_video_ids(webpage):
                if vid in seen:
                    continue
                seen.add(vid)
                found_new = True
                yield self._video_url_result(vid)

            total = int_or_none(self._search_regex(
                r"urlParams\.get\(['\"]page['\"]\)\s*<\s*(\d+)\s*-\s*1",
                webpage, 'total pages', default=None))
            if total is not None:
                if page_num >= total:
                    return
            elif not found_new:
                return

    def _single_page_entries(self, webpage):
        for vid in self._extract_video_ids(webpage):
            yield self._video_url_result(vid)

    def _parse_username(self, webpage, fallback):
        # User pages share an H1 with the display name; fall back to the bare
        # ID when it's absent.
        return self._html_search_regex(
            r'<h1[^>]*>([^<]+)</h1>', webpage, 'username', default=None) or fallback


class Hanime1PlaylistIE(_Hanime1ListBaseIE):
    IE_NAME = 'hanime1:playlist'
    _VALID_URL = r'https?://(?:www\.)?hanime1\.me/playlist\?(?:[^#]*&)?list=(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://hanime1.me/playlist?list=30618',
        'only_matching': True,
    }, {
        'url': 'https://hanime1.me/playlist?list=30618&sort=latest',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        playlist_id = self._match_id(url)
        webpage = self._download_webpage(url, playlist_id)

        title = self._html_search_regex(
            r'<h1[^>]*class="[^"]*playlist-title[^"]*"[^>]*>([^<]+)</h1>',
            webpage, 'playlist title', default=None) or playlist_id

        owner_match = re.search(
            r'class="playlist-author-info"[\s\S]*?href="([^"]*?/user/(\d+))"[^>]*>\s*([^<]+?)\s*</a>',
            webpage)
        uploader = owner_match.group(3).strip() if owner_match else None
        uploader_id = owner_match.group(2) if owner_match else None
        uploader_url = urljoin(url, owner_match.group(1)) if owner_match else None

        playlist_count = int_or_none(self._search_regex(
            r'id="sidebar-video-count"[^>]*>\s*(\d+)', webpage, 'video count',
            default=None))

        return self.playlist_result(
            self._single_page_entries(webpage), playlist_id, title,
            uploader=uploader, uploader_id=uploader_id, uploader_url=uploader_url,
            playlist_count=playlist_count)


class _Hanime1UserListBaseIE(_Hanime1ListBaseIE):
    """A user subpage with a single inline list of videos (no pagination).

    Concrete subclasses set `_TAB` (URL suffix, '' for the bare profile),
    `_TAB_LABEL` (human label appended to the playlist title), and `IE_NAME`.
    """
    _TAB = ''
    _TAB_LABEL = ''

    def _real_extract(self, url):
        user_id = self._match_id(url)
        page_url = f'https://hanime1.me/user/{user_id}'
        if self._TAB:
            page_url += f'/{self._TAB}'
        webpage = self._download_webpage(page_url, user_id)

        username = self._parse_username(webpage, user_id)
        playlist_id = f'{user_id}-{self._TAB}' if self._TAB else user_id
        title = f'{username} - {self._TAB_LABEL}' if self._TAB_LABEL else username

        return self.playlist_result(
            self._single_page_entries(webpage), playlist_id, title,
            uploader=username, uploader_id=user_id, uploader_url=page_url)


class Hanime1UserIE(_Hanime1UserListBaseIE):
    """Videos uploaded by a user - the closest hanime1 has to a "model" channel."""
    IE_NAME = 'hanime1:user'
    _VALID_URL = r'https?://(?:www\.)?hanime1\.me/user/(?P<id>\d+)(?:/uploaded)?/?(?:\?|$)'
    _TAB = 'uploaded'
    _TAB_LABEL = 'Uploaded'
    _TESTS = [{
        'url': 'https://hanime1.me/user/689220/uploaded',
        'only_matching': True,
    }, {
        'url': 'https://hanime1.me/user/689220',
        'only_matching': True,
    }]


class Hanime1UserLikesIE(_Hanime1UserListBaseIE):
    IE_NAME = 'hanime1:user:likes'
    _VALID_URL = r'https?://(?:www\.)?hanime1\.me/user/(?P<id>\d+)/likes/?(?:\?|$)'
    _TAB = 'likes'
    _TAB_LABEL = 'Likes'
    _TESTS = [{
        'url': 'https://hanime1.me/user/979597/likes',
        'only_matching': True,
    }]


class Hanime1UserSavesIE(_Hanime1UserListBaseIE):
    IE_NAME = 'hanime1:user:saves'
    _VALID_URL = r'https?://(?:www\.)?hanime1\.me/user/(?P<id>\d+)/saves/?(?:\?|$)'
    _TAB = 'saves'
    _TAB_LABEL = 'Saves'
    _TESTS = [{
        'url': 'https://hanime1.me/user/1262549/saves',
        'only_matching': True,
    }]


class Hanime1UserHistoryIE(_Hanime1UserListBaseIE):
    IE_NAME = 'hanime1:user:history'
    _VALID_URL = r'https?://(?:www\.)?hanime1\.me/user/(?P<id>\d+)/histories/?(?:\?|$)'
    _TAB = 'histories'
    _TAB_LABEL = 'History'
    _TESTS = [{
        'url': 'https://hanime1.me/user/666925/histories',
        'only_matching': True,
    }]


class Hanime1UserPlaylistsIE(_Hanime1ListBaseIE):
    IE_NAME = 'hanime1:user:playlists'
    _VALID_URL = r'https?://(?:www\.)?hanime1\.me/user/(?P<id>\d+)/playlists/?(?:\?|$)'
    _TESTS = [{
        'url': 'https://hanime1.me/user/854091/playlists',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        user_id = self._match_id(url)
        webpage = self._download_webpage(url, user_id)
        username = self._parse_username(webpage, user_id)

        def entries():
            seen = set()
            for m in re.finditer(r'/playlist\?list=(\d+)', webpage):
                pl_id = m.group(1)
                if pl_id in seen:
                    continue
                seen.add(pl_id)
                yield self.url_result(
                    f'https://hanime1.me/playlist?list={pl_id}',
                    Hanime1PlaylistIE, pl_id)

        return self.playlist_result(
            entries(), f'{user_id}-playlists', f'{username} - Playlists',
            uploader=username, uploader_id=user_id)


class Hanime1SubscriptionsIE(_Hanime1ListBaseIE):
    IE_NAME = 'hanime1:subscriptions'
    _VALID_URL = r'https?://(?:www\.)?hanime1\.me/subscriptions(?:\?[^#]*)?/?$'
    _PAGINATED = True
    _TESTS = [{
        'url': 'https://hanime1.me/subscriptions',
        'only_matching': True,
    }, {
        'url': 'https://hanime1.me/subscriptions?genre=Cosplay',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        playlist_id = 'subscriptions'
        return self.playlist_result(
            self._paginated_entries(url, playlist_id), playlist_id, 'Subscriptions')


class Hanime1SearchIE(_Hanime1ListBaseIE):
    IE_NAME = 'hanime1:search'
    # Match /search with at least one query parameter. This catches studio
    # (?query=...), tag (?tags[]=...), and genre (?genre=...) URLs.
    _VALID_URL = r'https?://(?:www\.)?hanime1\.me/search\?(?P<query>[^#]+)'
    _PAGINATED = True
    _TESTS = [{
        'url': 'https://hanime1.me/search?query=%E3%83%A1%E3%83%AA%E3%83%BC%E3%83%BB%E3%82%B8%E3%82%A7%E3%83%BC%E3%83%B3&genre=%E8%A3%8F%E7%95%AA',
        'info_dict': {
            'id': 'query=メリー・ジェーン&genre=裏番',
            'title': 'メリー・ジェーン - 裏番',
        },
        'playlist_mincount': 120,
    }, {
        # Studio query (no genre)
        'url': 'https://hanime1.me/search?query=Somato',
        'only_matching': True,
    }, {
        # Tag (note the bracket-style array param)
        'url': 'https://hanime1.me/search?tags%5B%5D=%E6%8E%A5%E5%90%BB&genre=%E8%A3%8F%E7%95%AA',
        'only_matching': True,
    }, {
        # Genre only
        'url': 'https://hanime1.me/search?genre=%E8%A3%8F%E7%95%AA',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        query = self._match_valid_url(url).group('query')
        playlist_id = urllib.parse.unquote(query)
        title = self._playlist_title(playlist_id) or playlist_id
        return self.playlist_result(
            self._paginated_entries(url, playlist_id), playlist_id, title)

    @staticmethod
    def _playlist_title(query_str):
        parsed = urllib.parse.parse_qs(query_str)
        parts = traverse_obj(parsed, ('query', 0)) or traverse_obj(parsed, ('tags[]',))
        if isinstance(parts, str):
            parts = [parts]
        parts = list(parts or [])
        genre = traverse_obj(parsed, ('genre', 0))
        if genre:
            parts.append(genre)
        return ' - '.join(parts) if parts else None
