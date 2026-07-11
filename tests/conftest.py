"""Pytest fixtures shared across site test modules."""

from __future__ import annotations

from pathlib import Path

import pytest

from harness import MODES, Mode, build_cmd, discover_hanime1_owner_uid, run_ytdlp


@pytest.fixture(params=MODES, ids=[m.id for m in MODES])
def mode(request) -> Mode:
    return request.param


@pytest.fixture(scope='session')
def hanime1_owner_uid() -> str:
    uid = discover_hanime1_owner_uid()
    if not uid:
        pytest.skip('could not discover hanime1 logged-in user id from cookies')
    return uid


@pytest.fixture
def ytdlp_runner(mode: Mode, tmp_path: Path):
    """Return a callable that builds a yt-dlp command and runs it."""
    def _run(
        url: str,
        *,
        simulate: bool,
        flat_playlist: bool = False,
        max_downloads: int | None = None,
        extra: tuple[str, ...] = (),
    ):
        output_dir = tmp_path if not simulate else None
        cmd = build_cmd(
            url, mode,
            simulate=simulate,
            flat_playlist=flat_playlist,
            output_dir=output_dir,
            max_downloads=max_downloads,
            extra=extra,
        )
        return run_ytdlp(cmd, output_dir=output_dir)
    return _run
