"""Shared scaffolding for the e2e extractor tests.

The harness invokes yt-dlp as a subprocess so each test exercises the same
code path a user runs from the command line. Tests are parameterised over
three modes:

  - cookies-impersonate:        --cookies-from-browser + --impersonate chrome
  - no-cookies-impersonate:     --impersonate chrome only
  - minimal:                    neither flag (bare yt-dlp)

A test case marked ``requires_cookies`` is skipped in any mode without
``--cookies-from-browser``. A case not marked ``minimal`` is skipped in the
minimal mode (so the minimal mode stays a small smoke set).
"""

from __future__ import annotations

import dataclasses
import re
import shutil
import subprocess
import sys
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal


REPO_ROOT = Path(__file__).resolve().parents[1]
BROWSER_PROFILE = REPO_ROOT / 'browser-profile'

CaseKind = Literal['video', 'playlist', 'match_only']


def discover_hanime1_owner_uid() -> str | None:
    """Return the user id whose session lives in browser-profile/, or None.

    Hits ``https://hanime1.me/`` with the chrome-profile cookies and scrapes
    the ``/user/NNNNN`` link the site renders for the logged-in account.
    Used by tests that read owner-only tabs (likes / saves / histories) so no
    personal id needs to be checked into the repo.
    """
    if not BROWSER_PROFILE.exists():
        return None
    try:
        from curl_cffi import requests as cffi_requests
        from yt_dlp.cookies import extract_cookies_from_browser
    except ImportError:
        return None

    import logging
    cookie_jar = extract_cookies_from_browser(
        'chrome', profile=str(BROWSER_PROFILE), logger=logging.getLogger('hanime1.cookies'))
    cookies = {c.name: c.value for c in cookie_jar if 'hanime1' in c.domain}
    if not cookies:
        return None

    resp = cffi_requests.get(
        'https://hanime1.me/', impersonate='chrome', cookies=cookies, timeout=30)
    m = re.search(r'href="https?://(?:www\.)?hanime1\.me/user/(\d+)"', resp.text)
    return m.group(1) if m else None


@dataclass(frozen=True)
class Case:
    id: str
    url: str
    kind: CaseKind
    expected_id: str = ''
    min_entries: int = 1
    requires_cookies: bool = False
    minimal: bool = False
    notes: str = ''


@dataclass(frozen=True)
class Mode:
    id: str
    cookies: bool
    impersonate: bool


MODES: tuple[Mode, ...] = (
    Mode('cookies-impersonate', cookies=True, impersonate=True),
    Mode('no-cookies-impersonate', cookies=False, impersonate=True),
    Mode('minimal', cookies=False, impersonate=False),
)


def can_impersonate() -> bool:
    try:
        import curl_cffi  # noqa: F401
    except ImportError:
        return False
    return True


def maybe_skip(case: Case, mode: Mode) -> None:
    """Pytest-skip when the (case, mode) pair is not exercisable."""
    import pytest

    reason = skip_reason(case, mode)
    if reason:
        pytest.skip(reason)


def skip_reason(case: Case, mode: Mode) -> str:
    if case.requires_cookies and not mode.cookies:
        return f'case {case.id} requires --cookies-from-browser'
    if mode.id == 'minimal' and not case.minimal:
        return f'case {case.id} is not part of the minimal smoke set'
    if mode.impersonate and not can_impersonate():
        return 'curl_cffi not installed; --impersonate chrome unavailable'
    if mode.cookies and not BROWSER_PROFILE.exists():
        return f'no browser profile at {BROWSER_PROFILE}'
    return ''


def build_cmd(
    url: str,
    mode: Mode,
    *,
    simulate: bool,
    flat_playlist: bool = False,
    output_dir: Path | None = None,
    max_downloads: int | None = None,
    extra: Sequence[str] = (),
) -> list[str]:
    cmd: list[str] = [
        sys.executable, '-m', 'yt_dlp',
        '-v',
        '--ignore-config',
        '--no-warnings',
        '--newline',
    ]
    if mode.cookies:
        # PROFILE accepts an absolute path to a profile directory. Playwright's
        # persistent context writes a full user-data-dir layout at the path we
        # pass to launch_persistent_context, so the profile dir itself is the
        # right argument here. If yt-dlp ever changes to require a profile
        # subdir name (e.g. "Default"), this is the place to adjust.
        cmd += ['--cookies-from-browser', f'chrome:{BROWSER_PROFILE}']
    if mode.impersonate:
        cmd += ['--impersonate', 'chrome']
    if flat_playlist:
        cmd += ['--flat-playlist']
    if simulate:
        cmd += ['--simulate']
    else:
        # --print on its own forces simulate mode, which would suppress the
        # download. --no-simulate restores the actual --test download path.
        cmd += ['--no-simulate', '--test']
    if max_downloads is not None:
        cmd += ['--max-downloads', str(max_downloads)]
    if output_dir is not None:
        cmd += ['-P', str(output_dir)]
    cmd += ['--print', 'id']
    cmd += list(extra)
    cmd.append(url)
    return cmd


@dataclass
class RunResult:
    cmd: list[str]
    returncode: int
    stdout: str
    stderr: str
    output_dir: Path | None

    @property
    def printed_ids(self) -> list[str]:
        # `--print id` writes one id per line to stdout. yt-dlp also writes
        # progress / verbose lines to stderr, so stdout stays parseable.
        return [line.strip() for line in self.stdout.splitlines() if line.strip()]

    @property
    def downloaded_files(self) -> list[Path]:
        if self.output_dir is None:
            return []
        return [p for p in self.output_dir.iterdir() if p.is_file() and p.stat().st_size > 0]


def run_ytdlp(cmd: Sequence[str], *, output_dir: Path | None, timeout: int = 240) -> RunResult:
    proc = subprocess.run(
        list(cmd),
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    return RunResult(
        cmd=list(cmd),
        returncode=proc.returncode,
        stdout=proc.stdout,
        stderr=proc.stderr,
        output_dir=output_dir,
    )


def fmt_failure(result: RunResult) -> str:
    return (
        f'yt-dlp exited with {result.returncode}\n'
        f'cmd: {" ".join(result.cmd)}\n'
        f'--- stdout ---\n{result.stdout}\n'
        f'--- stderr (tail) ---\n{"".join(result.stderr.splitlines(keepends=True)[-40:])}'
    )
