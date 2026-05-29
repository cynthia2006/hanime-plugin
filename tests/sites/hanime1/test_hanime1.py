"""E2E tests for the hanime1.me extractor set.

Run from the repo root via `tests/run.sh` (or `python -m pytest`). See
`tests/README.md` for the list of URLs exercised here and what each case
proves.
"""

from __future__ import annotations

import pytest

from harness import Case, fmt_failure, maybe_skip


VIDEO_CASES: list[Case] = [
    # Public video from the active in-flight catalogue. Included in the
    # minimal smoke set because it exercises the common code path (formats
    # parse, channel/genre extraction, view count parse).
    Case(
        id='watch-405849',
        url='https://hanime1.me/watch?v=405849',
        kind='video',
        expected_id='405849',
        minimal=True,
    ),
    # Older video, only 480p/720p formats available - guards against assuming
    # every video has 1080p.
    Case(
        id='watch-22673-old',
        url='https://hanime1.me/watch?v=22673',
        kind='video',
        expected_id='22673',
    ),
    # `/watch?v=ID&list=...&sort=...` shape - the URL regex must still match
    # when the watch page is reached from inside a playlist.
    Case(
        id='watch-via-list',
        url='https://hanime1.me/watch?v=155209&list=435600&sort=latest',
        kind='video',
        expected_id='155209',
    ),
]


# Owner-private tabs (likes / saves / histories). The site only renders these
# for the logged-in account; using a hardcoded user id would either leak a
# personal id or assert against empty pages. The fixture discovers the id from
# the cookies at session start.
OWNER_TABS: list[tuple[str, str]] = [
    ('user-owner-likes', 'likes'),
    ('user-owner-saves', 'saves'),
    ('user-owner-histories', 'histories'),
]


PLAYLIST_CASES: list[Case] = [
    # Studio search. Single-token query, paginated.
    Case(
        id='search-query-Somato',
        url='https://hanime1.me/search?query=Somato',
        kind='playlist',
        min_entries=5,
        minimal=True,
    ),
    # Studio + genre. The _TESTS entry in the extractor expects >=120 entries
    # for this exact URL; we keep the same query but assert a lower bound so
    # the test is not flaky if the catalogue shrinks.
    Case(
        id='search-studio-genre',
        url=(
            'https://hanime1.me/search?'
            'query=%E3%83%A1%E3%83%AA%E3%83%BC%E3%83%BB%E3%82%B8%E3%82%A7%E3%83%BC%E3%83%B3'
            '&genre=%E8%A3%8F%E7%95%AA'
        ),
        kind='playlist',
        min_entries=50,
    ),
    # Tag-style search (array param).
    Case(
        id='search-tag-genre',
        url=(
            'https://hanime1.me/search?'
            'tags%5B%5D=%E6%8E%A5%E5%90%BB'
            '&genre=%E8%A3%8F%E7%95%AA'
        ),
        kind='playlist',
        min_entries=10,
    ),
    # Public user profile page (uploaded tab). The uploaded list is public for
    # every account; most regular users have no uploads so min_entries stays 0
    # and the test just proves the page parses without errors.
    Case(
        id='user-uploaded',
        url='https://hanime1.me/user/689220/uploaded',
        kind='playlist',
        min_entries=0,
        notes='public uploader page; may be empty if the account has no uploads',
    ),
    # User's playlists tab. Public. 854091 was picked because the account has
    # one public playlist, so min_entries=1 actually exercises entry parsing.
    Case(
        id='user-playlists',
        url='https://hanime1.me/user/854091/playlists',
        kind='playlist',
        min_entries=1,
        notes='lists user-owned playlists; entries are url_results to Hanime1PlaylistIE',
    ),
    # Public playlist with a healthy number of videos (~234 at the time of
    # writing). Lower bound kept conservative so a few removals do not flake.
    Case(
        id='playlist-public',
        url='https://hanime1.me/playlist?list=30618',
        kind='playlist',
        min_entries=5,
    ),
    # Subscriptions feed. Requires auth.
    Case(
        id='subscriptions',
        url='https://hanime1.me/subscriptions',
        kind='playlist',
        min_entries=0,
        requires_cookies=True,
    ),
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

    # Flat-playlist: list entries without descending into each video page.
    result = ytdlp_runner(case.url, simulate=True, flat_playlist=True)
    assert result.returncode == 0, fmt_failure(result)

    entries = result.printed_ids
    assert len(entries) >= case.min_entries, (
        f'expected at least {case.min_entries} entries, got {len(entries)}: {entries[:5]}\n'
        + fmt_failure(result)
    )


@pytest.mark.parametrize(
    'case',
    [c for c in PLAYLIST_CASES if c.min_entries > 0 and not c.requires_cookies],
    ids=lambda c: c.id,
)
def test_playlist_download_sample(case: Case, mode, ytdlp_runner):
    """Prove the playlist -> video -> download chain works end-to-end.

    Restricts to one or two entries via --max-downloads so the test stays
    fast and gentle on the site.
    """
    maybe_skip(case, mode)

    result = ytdlp_runner(case.url, simulate=False, max_downloads=2)
    # yt-dlp exits 101 when --max-downloads is hit. Treat that as success.
    assert result.returncode in (0, 101), fmt_failure(result)

    files = result.downloaded_files
    assert files, f'no files downloaded from playlist\n{fmt_failure(result)}'


@pytest.mark.parametrize('case_id,tab', OWNER_TABS, ids=[c for c, _ in OWNER_TABS])
def test_owner_subpage(case_id, tab, mode, ytdlp_runner, hanime1_owner_uid):
    """Owner-only tabs (likes / saves / histories).

    The site renders content for these only when the visitor is the profile
    owner, so the user id is taken from the logged-in account behind the
    cookies rather than a hardcoded value.
    """
    if not mode.cookies:
        pytest.skip(f'{case_id} requires --cookies-from-browser')

    url = f'https://hanime1.me/user/{hanime1_owner_uid}/{tab}'
    result = ytdlp_runner(url, simulate=True, flat_playlist=True)
    assert result.returncode == 0, fmt_failure(result)
