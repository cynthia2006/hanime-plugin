# E2E tests

These are manual end-to-end tests for the new extractors in this repo
(currently `hanime1` and `rule34video`). They hit the live sites, so
they need a network connection and care should be taken not to run them
at high frequency against accounts you care about.

## Running

```bash
tests/run.sh                                               # all sites, all modes
tests/run.sh -k hanime1                                    # one site
tests/run.sh -k 'no-cookies-no-impersonate'                # one mode
tests/run.sh tests/sites/hanime1/test_hanime1.py::test_video
```

`run.sh` calls `python -m pytest` from the active environment. It
verifies that `pytest` is importable and otherwise prints the install
hint:

```bash
python -m pip install -e '.[test]'
```

That extra pulls in `pytest` and `curl_cffi`. `curl_cffi` is what
powers the `--impersonate chrome` modes, which most cookie-fronted
sites need.

You can override the interpreter with `PYTHON=/path/to/python tests/run.sh`.

## How a test is shaped

Each extractor has a list of `Case` records (URL + expected id / minimum
entries / flags). The test functions are parametrized over this list and
across **three modes**:

| Mode                          | `--cookies-from-browser` | `--impersonate chrome` |
| ---                           | :---:                    | :---:                  |
| `cookies-impersonate`         | yes                      | yes                    |
| `no-cookies-impersonate`      | no                       | yes                    |
| `minimal`                     | no                       | no                     |

Skip rules:

- A case marked `requires_cookies=True` runs only in `cookies-impersonate`.
- The `minimal` mode runs only cases marked `minimal=True` (a small smoke
  set, currently one video and one search).
- Any mode that asks for `--impersonate` is auto-skipped if `curl_cffi`
  failed to install.

What each test asserts:

| Test                          | What runs                                | Assertion |
| ---                           | ---                                      | --- |
| `test_video`                  | `yt-dlp --test`                          | yt-dlp exited 0, the expected id was printed, at least one file landed in the tmp output dir |
| `test_playlist`               | `yt-dlp --simulate --flat-playlist`      | yt-dlp exited 0, at least `min_entries` ids printed |
| `test_playlist_download_sample` | `yt-dlp --test --max-downloads 2`      | yt-dlp exited 0 or 101 (max-downloads hit), at least one file downloaded |
| `test_owner_subpage`          | `yt-dlp --simulate --flat-playlist`      | yt-dlp exited 0; URL is built from the logged-in user id discovered from the chrome profile (see *Owner-only subpages* below) |

`--test` is yt-dlp's built-in "tiny chunk" mode: lowest format, a few
seconds of the file. It still exercises the full extractor -> format
selection -> downloader path.

## Owner-only subpages

`/user/<id>/likes`, `/user/<id>/saves`, and `/user/<id>/histories` only
render content when the visitor is the profile owner. The harness fetches
`https://hanime1.me/` with the chrome-profile cookies, scrapes the
logged-in account's `/user/<id>` link, and uses that id when building the
test URLs. No personal id is hardcoded in the repo. If cookies are not
available the `test_owner_subpage` parametrisations skip.

## Cookies

The `cookies-impersonate` mode passes
`--cookies-from-browser chrome:<repo>/browser-profile`. There is no
`browser-profile/` checked into this repo (it is gitignored and treated
as live credentials), so you need to point that path at a real Chrome
profile directory before any cookie-required test will run.

Two options:

1. **Symlink your existing Chrome profile** into the repo:

   ```bash
   # Linux
   ln -s "$HOME/.config/google-chrome" browser-profile
   # macOS
   ln -s "$HOME/Library/Application Support/Google/Chrome" browser-profile
   # Windows (cmd.exe, as administrator)
   mklink /D browser-profile "%LOCALAPPDATA%\Google\Chrome\User Data"
   ```

2. **Use a dedicated profile.** Launch Chrome with
   `--user-data-dir="$PWD/browser-profile"`, log into the sites you want
   to test, close Chrome, then run the tests.

Log into hanime1.me / rule34video.com in that profile at least once so
the cookies exist on disk.

**Caveats:**

- Chrome / Chromium must be **closed** when you run the tests. yt-dlp
  cannot read cookies from a profile that the browser currently has
  open.
- yt-dlp interprets `--cookies-from-browser chrome:PATH` as a profile
  directory. The harness passes the absolute `browser-profile/` path.
  If yt-dlp ever rejects the path, edit `tests/harness.py::build_cmd`
  to point at the inner profile dir (likely `browser-profile/Default`).

## Known issues

- **Python 3.14 + curl_cffi.** `curl_cffi` may not have prebuilt wheels
  for Python 3.14 yet. If `pip install -e '.[test]'` fails on
  `curl_cffi`, the impersonate-required modes will auto-skip with a
  clear reason. To exercise them, use Python 3.12 or 3.13 in a separate
  venv.
- **Cloudflare / hCaptcha.** hanime1.me sits behind Cloudflare and
  occasionally serves an hCaptcha to anonymous traffic. The
  `no-cookies-no-impersonate` mode is the most likely to be challenged.
  A flake here is information about the site's bot defences, not a bug
  in the extractor.

## Case index — hanime1.me

All cases live in `tests/sites/hanime1/test_hanime1.py`. The URLs below
are the ones the tests will hit; if any of them stop being available,
update the case list and bump `min_entries` only when the site's actual
catalogue size justifies it.

### Videos (`test_video`)

| Case id                     | URL                                                          | Why |
| ---                         | ---                                                          | --- |
| `watch-405849`              | `https://hanime1.me/watch?v=405849`                          | Recent video, full 1080p path. Minimal smoke set. |
| `watch-22673-old`           | `https://hanime1.me/watch?v=22673`                           | Older video with only 480p/720p. Guards against assuming 1080p exists. |
| `watch-via-list`            | `https://hanime1.me/watch?v=155209&list=435600&sort=latest`  | URL with extra query params - the regex must still match. |

### Playlists, searches, user pages (`test_playlist`)

| Case id                       | URL                                                                 | Auth? | Notes |
| ---                           | ---                                                                  | :---: | --- |
| `search-query-Somato`         | `https://hanime1.me/search?query=Somato`                            | -     | Studio search, paginated. Minimal smoke set. |
| `search-studio-genre`         | `https://hanime1.me/search?query=メリー・ジェーン&genre=裏番` (URL-encoded)               | -     | Matches the `_TESTS` entry in the extractor. Asserts `>=50` entries (extractor expects 120; we're conservative). |
| `search-tag-genre`            | `https://hanime1.me/search?tags[]=接吻&genre=裏番` (URL-encoded)                      | -     | Bracket-style array tag param. |
| `user-uploaded`               | `https://hanime1.me/user/689220/uploaded`                            | -     | Public uploader page. May be empty if the account has no uploads (`min_entries=0`). |
| `user-playlists`              | `https://hanime1.me/user/854091/playlists`                           | -     | Public playlists tab. Account picked because it has at least one public playlist, so `min_entries=1`. Entries are `url_result`s to `Hanime1PlaylistIE`. |
| `playlist-public`             | `https://hanime1.me/playlist?list=30618`                             | -     | Public playlist (~234 videos as of writing). `min_entries=5`. |
| `subscriptions`               | `https://hanime1.me/subscriptions`                                  | yes   | Feed of subscribed studios; paginated; auth-only. |

### Owner-only tabs (`test_owner_subpage`)

| Case id                  | URL template                                | Auth? | Notes |
| ---                      | ---                                          | :---: | --- |
| `user-owner-likes`       | `https://hanime1.me/user/<owner>/likes`     | yes   | URL built from the logged-in user id discovered from the chrome profile. |
| `user-owner-saves`       | `https://hanime1.me/user/<owner>/saves`     | yes   | Same. |
| `user-owner-histories`   | `https://hanime1.me/user/<owner>/histories` | yes   | Same. |

### Playlist download-sample (`test_playlist_download_sample`)

Runs only on the public playlists with `min_entries > 0`. Downloads up to
two entries with `--test` to prove the playlist -> video -> downloader
chain works end-to-end.

## Case index — rule34video.com

All cases live in `tests/sites/rule34video/test_rule34video.py`. Member ids
in test URLs are *not* the logged-in account behind the chrome profile;
they were picked from public members observed during API exploration so
nothing personal is checked into the repo.

### Videos (`test_video`)

| Case id              | URL                                                                                                | Why |
| ---                  | ---                                                                                                | --- |
| `watch-4321530`      | `https://rule34video.com/video/4321530/god-s-blessing-on-this-wonderful-kiss-embedded-subtitles/`  | Standard public video. Exercises the common path: flashvars parse, JSON-LD timestamp/counts, channel/categories. Minimal smoke set. |
| `watch-3434961-4k`   | `https://rule34video.com/video/3434961/loyalty-nude-drills3d-extended/`                            | Has a 2160p variant in `video_alt_url4` with the `4k` text label. Guards against the `4k` label being parsed as height=4. |
| `watch-bare-id`      | `https://rule34video.com/video/4321530/`                                                            | Bare-id URL (no slug). The site 404s `/video/<id>/`; the extractor must supply a placeholder slug and follow the 301 to the canonical URL. |

### Lists, search, member tabs (`test_playlist`)

| Case id                       | URL                                                            | Auth? | Notes |
| ---                           | ---                                                             | :---: | --- |
| `model-seejaydj`              | `https://rule34video.com/models/seejaydj/`                     | -     | ~24 videos for this model. Minimal smoke set. |
| `category-dress-up-darling`   | `https://rule34video.com/categories/dress-up-darling/`         | -     | Multi-page category. `min_entries=24` to keep it a smoke check rather than a full crawl. |
| `tag-1877`                    | `https://rule34video.com/tags/1877/`                            | -     | Numeric tag id. |
| `search-ayaka`                | `https://rule34video.com/search/ayaka/`                         | -     | Query-based search, paginated. Smoke set. |
| `search-model-filter`         | `https://rule34video.com/search/?model_ids=283`                | -     | Filter-only search (no query). Async pagination uses `from_videos`+`from_albums`. |
| `playlist-124556`             | `https://rule34video.com/playlists/124556/2d-animations27/`     | -     | Public playlist owned by member 180930. |
| `member-uploads`              | `https://rule34video.com/members/180930/videos/`                | -     | Public uploader tab. |
| `member-favourites`           | `https://rule34video.com/members/106821/favourites/videos/`     | -     | Public favorites tab. `106821` was picked because most other public members in the area had empty/private favs. |
| `member-playlists`            | `https://rule34video.com/members/180930/playlists/`             | -     | Public playlists tab; entries are `url_result`s to `Rule34VideoPlaylistIE`. |

### /my/* tabs (`test_my_tab`)

| Case id            | URL                                              | Auth? | Notes |
| ---                | ---                                              | :---: | --- |
| `my-favourites`    | `https://rule34video.com/my/favourites/videos/`  | yes   | The site renders content for `/my/*` only when the visitor is logged in. Anonymous and stale-session requests get redirected to `/?login`; the extractor detects this and raises a clear error. |
| `my-videos`        | `https://rule34video.com/my/videos/`             | yes   | Same. May legitimately be empty if the account has no uploads. |
| `my-history`       | `https://rule34video.com/my/history/`            | yes   | Same. |
| `my-subscriptions` | `https://rule34video.com/my/subscriptions/`      | yes   | Same. |
| `my-playlists`     | `https://rule34video.com/my/playlists/`          | yes   | Same. Entries are `url_result`s to `Rule34VideoPlaylistIE`. |

The /my/* tests only run in `cookies-impersonate` mode and only pass when
the browser-profile session is fresh. The site invalidates server-side
sessions on a relatively short timer; if the tests start failing with the
"requires login" error, log into rule34video.com in the chrome profile
again to refresh the session.

### Playlist download-sample (`test_playlist_download_sample`)

Same as for hanime1: runs on every public list case (skipping
`member-playlists`, whose entries are themselves playlists, and any case
that requires cookies) and downloads up to two videos per case with
`--test`.

## Adding a new site

1. Create `tests/sites/<site>/test_<site>.py`.
2. Define `VIDEO_CASES`, `PLAYLIST_CASES` (and any other categories that
   apply) using `harness.Case`.
3. Reuse the `mode` and `ytdlp_runner` fixtures and the `maybe_skip`
   helper. Use `harness.fmt_failure(result)` in assertion messages so the
   stderr tail of a failed yt-dlp run is included in the test output.
4. Update the root `README.md` site support table.
