"""E2E tests for the rule34video.com extractor set.

Run from the repo root via `tests/run.sh` (or `python -m pytest`). See
`tests/README.md` for the list of URLs exercised here and what each case
proves.
"""

from __future__ import annotations

import pytest

from harness import Case, fmt_failure, maybe_skip


VIDEO_CASES: list[Case] = [
    # Standard public video. Common code path: flashvars parse, JSON-LD
    # timestamp / counts, channel / categories. Part of the minimal smoke set.
    Case(
        id='watch-4321530',
        url='https://rule34video.com/video/4321530/god-s-blessing-on-this-wonderful-kiss-embedded-subtitles/',
        kind='video',
        expected_id='4321530',
        minimal=True,
    ),
    # Has a 2160p (4K) variant in video_alt_url4 with the `4k` text label.
    # Guards against the "4k" label being parsed as height=4.
    Case(
        id='watch-3434961-4k',
        url='https://rule34video.com/video/3434961/loyalty-nude-drills3d-extended/',
        kind='video',
        expected_id='3434961',
    ),
    # Bare-id URL (no slug). The extractor must supply a placeholder slug and
    # follow the 301 to the canonical URL.
    Case(
        id='watch-bare-id',
        url='https://rule34video.com/video/4321530/',
        kind='video',
        expected_id='4321530',
    ),
]


PLAYLIST_CASES: list[Case] = [
    # Public playlist owned by member 180930. Owner-curated; pagination may
    # or may not be needed depending on current length.
    Case(
        id='playlist-124556',
        url='https://rule34video.com/playlists/124556/2d-animations27/',
        kind='playlist',
        min_entries=5,
    ),
    # Model page. ~24 videos for this model (1 page). Smoke set.
    Case(
        id='model-seejaydj',
        url='https://rule34video.com/models/seejaydj/',
        kind='playlist',
        min_entries=10,
        minimal=True,
    ),
    # Category page. Heavily paginated (~100+ pages). Cap with min_entries=24
    # so it stays a smoke test rather than a deep crawl.
    Case(
        id='category-dress-up-darling',
        url='https://rule34video.com/categories/dress-up-darling/',
        kind='playlist',
        min_entries=24,
    ),
    # Tag page (numeric tag id).
    Case(
        id='tag-1877',
        url='https://rule34video.com/tags/1877/',
        kind='playlist',
        min_entries=10,
    ),
    # Query-based search. ~400+ results, easily paginated. Smoke set.
    Case(
        id='search-ayaka',
        url='https://rule34video.com/search/ayaka/',
        kind='playlist',
        min_entries=24,
        minimal=True,
    ),
    # Filter-only search (model filter).
    Case(
        id='search-model-filter',
        url='https://rule34video.com/search/?model_ids=283',
        kind='playlist',
        min_entries=24,
    ),
    # Public member uploads tab. Member 180930 has ~50 uploads.
    Case(
        id='member-uploads',
        url='https://rule34video.com/members/180930/videos/',
        kind='playlist',
        min_entries=10,
    ),
    # Public member favourites tab. Member 106821 has ~24 public favourites
    # as of test authoring; other ids in the area have empty/private favs.
    Case(
        id='member-favourites',
        url='https://rule34video.com/members/106821/favourites/videos/',
        kind='playlist',
        min_entries=5,
    ),
    # Public member playlists tab. Entries are url_results to
    # Rule34VideoPlaylistIE.
    Case(
        id='member-playlists',
        url='https://rule34video.com/members/180930/playlists/',
        kind='playlist',
        min_entries=1,
        notes='lists user-owned playlists; entries are url_results to Rule34VideoPlaylistIE',
    ),
]


# /my/* tabs render content only for the logged-in account. The site
# redirects anonymous (and stale-session) requests to `/?login` while
# returning 200; the extractor detects the redirect and raises a clear
# error. These tests therefore only run in cookies-impersonate mode and
# require a fresh browser-profile login.
MY_TABS: list[tuple[str, str]] = [
    ('my-favourites', 'https://rule34video.com/my/favourites/videos/'),
    ('my-videos', 'https://rule34video.com/my/videos/'),
    ('my-history', 'https://rule34video.com/my/history/'),
    ('my-subscriptions', 'https://rule34video.com/my/subscriptions/'),
    ('my-playlists', 'https://rule34video.com/my/playlists/'),
]


@pytest.mark.parametrize('case', VIDEO_CASES, ids=[c.id for c in VIDEO_CASES])
def test_video(case: Case, mode, ytdlp_runner):
    maybe_skip(case, mode)

    result = ytdlp_runner(case.url, simulate=False)
    assert result.returncode == 0, fmt_failure(result)
    assert case.expected_id in result.printed_ids, (
        f'expected id {case.expected_id!r} in printed ids, got {result.printed_ids!r}\n'
        + fmt_failure(result)
    )
    files = result.downloaded_files
    assert files, f'no file downloaded in --test mode\n{fmt_failure(result)}'


@pytest.mark.parametrize('case', PLAYLIST_CASES, ids=[c.id for c in PLAYLIST_CASES])
def test_playlist(case: Case, mode, ytdlp_runner):
    maybe_skip(case, mode)

    result = ytdlp_runner(case.url, simulate=True, flat_playlist=True)
    assert result.returncode == 0, fmt_failure(result)

    entries = result.printed_ids
    assert len(entries) >= case.min_entries, (
        f'expected at least {case.min_entries} entries, got {len(entries)}: {entries[:5]}\n'
        + fmt_failure(result)
    )


@pytest.mark.parametrize(
    'case',
    # Skip the member-playlists case here - entries are playlist url_results,
    # so descending into them would download an unknown number of videos.
    [c for c in PLAYLIST_CASES
     if c.min_entries > 0
     and c.id != 'member-playlists'
     and not c.requires_cookies],
    ids=lambda c: c.id,
)
def test_playlist_download_sample(case: Case, mode, ytdlp_runner):
    """Prove the playlist -> video -> download chain works end-to-end."""
    maybe_skip(case, mode)

    result = ytdlp_runner(case.url, simulate=False, max_downloads=2)
    # yt-dlp exits 101 when --max-downloads is hit. Treat that as success.
    assert result.returncode in (0, 101), fmt_failure(result)

    files = result.downloaded_files
    assert files, f'no files downloaded from playlist\n{fmt_failure(result)}'


@pytest.mark.parametrize('case_id,url', MY_TABS, ids=[c for c, _ in MY_TABS])
def test_my_tab(case_id, url, mode, ytdlp_runner):
    """/my/* tabs require a valid logged-in session.

    The site redirects stale or missing sessions to `/?login`; the extractor
    detects that and raises ExtractorError, which surfaces here as a non-zero
    yt-dlp exit. If you've recently re-logged into the browser profile this
    should pass; otherwise the test is informative about session staleness
    rather than a bug.
    """
    if not mode.cookies:
        pytest.skip(f'{case_id} requires --cookies-from-browser')

    result = ytdlp_runner(url, simulate=True, flat_playlist=True)
    assert result.returncode == 0, fmt_failure(result)
