# hanime-plugin

This yt-dlp plugin adds support for numerous hentai websites, including but not limited to **hanime.tv**, **hstream.moe** and **HentaiHaven**.

[![PyPI version](https://badge.fury.io/py/hanime-plugin.svg)](https://pypi.org/project/hanime-plugin/)

## Installation

You can install this package with pip:
```
pip install --user hanime-plugin
```

Can also be installed using [uv](https://astral.sh/uv).

```
uv tool install --with hanime-plugin yt-dlp
```

>[!WARNING]
>If a change/bug is committed but not released on PyPI, clone this repository directly, and see [installing yt-dlp plugins](https://github.com/yt-dlp/yt-dlp#installing-plugins) for how to point yt-dlp to load this plugin.

### Deno

**hanime.tv** extractor requires a JavaScript runtime. As of now, only [Deno](https://deno.com/) is supported. Install it using the following commands, and it would be available in `PATH` if you follow the onscreen instructions carefully.

```sh
# For Linux & MacOS
curl -fsSL https://deno.land/install.sh | sh
# For Windows (PowerShell)
irm https://deno.land/install.ps1 | iex
```

## Support

The following is the support matrix of sites and the respective video resolutions offered. **To request support for a site, or complain about a broken site, please open a Github issue.**

|                 | 720p  | 1080p | 4K    |
| --------------- | ----- | ----- | ----- |
| hstream.moe     | ✅    | ✅ †  | ✅ †  |
| oppai.stream    | ✅    | ✅ ‡  | ✅ ‡  |
| hentaihaven.com | ✅    | ✅    | ❌     |
| hanime.tv       | ✅    | ❌*    | ❌     |
| ohentai.org     | ✅    | ❌     | ❌     |
| hentaimama.io   | ✅    | ❌     | ❌     |
| hanime.red      | ❌     | ✅    | ❌     |

\* Requires paid membership, and is beyond the scope of this plugin.

† [AV1](https://en.wikipedia.org/wiki/AV1) codec. ‡ [VP9](https://en.wikipedia.org/wiki/VP9) codec.

## Examples

### Downloading a single video

```
$ yt-dlp https://hanime.tv/videos/hentai/fuzzy-lips-1
```

or 

```
$ yt-dlp -f - https://hentaihaven.com/video/soshite-watashi-wa-sensei-ni/episode-1
```

## FAQ

### `ERROR: Data must be padded to 16 byte boundary in CBC mode`

See https://github.com/yt-dlp/yt-dlp/issues/3810 and https://github.com/cynthia2006/hanime-plugin/issues/8

The issue is with yt-dlp's HLS fragment downloader, and a well-known fix is adding the `--downloader ffmpeg` option.

### Why supports for these sites are not already included in yt-dlp?

The foundations for hanime.tv scraping were first laid out by [rxqv](https://github.com/rxqv/htv) as a separate tool, but the development ceased in 2021. Had it become dysfunctional eventually, [an issue](https://github.com/yt-dlp/yt-dlp/issues/4007) was raised for adding support for hanime.tv in upstream yt-dlp. Unfortunately, it was turned down, citing that the website allows piracy. This may have to do with the fact that YouTubeDL (yt-dlp's predecessor) had quite a controversial past; so far as to be banned from GitHub in 2020 as the result of DMCA complaint by Google.

Meanwhile, xsbee maintained a fork of yt-dlp with a hanime.tv extractor he/she made, before ceasing development in 2023. This plugin was originally based off of that extractor code. Support for other sites have been added in late 2025.

### Earlier version had support for hanime.tv playlists, what happened?

These additional features were added in 2024 on top of xsbee's original code. However, franchise and playlist downloads have since been removed because of [code rot](https://en.wikipedia.org/wiki/Software_rot).
