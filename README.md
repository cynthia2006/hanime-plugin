# hanime-plugin

This yt-dlp plugin adds support for numerous hentai websites, including but not limited to **hanime.tv**, **hstream.moe** and **HentaiHaven**.

[![PyPI version](https://badge.fury.io/py/hanime-plugin.svg)](https://pypi.org/project/hanime-plugin/)

## Installation

You can install this package with pip:
```
pip install --user hanime-plugin
```

>[!WARNING]
>If a bug is fixed or a feature is added, but not released on PyPI yet, do this instead:
> ```
> pip install "git+https://github.com/cynthia2006/hanime-plugin.git"
> ```

See [installing yt-dlp plugins](https://github.com/yt-dlp/yt-dlp#installing-plugins) for other methods of installation.

### Deno

hanime.tv extractor requires a JavaScript runtime. As of now, [Deno](https://deno.com/) is supported. Install it with these commands, and it would be available in `PATH` if you follow the onscreen instructions carefully.

```sh
# For Linux & MacOS
curl -fsSL https://deno.land/install.sh | sh
# For Windows (PowerShell)
irm https://deno.land/install.ps1 | iex
```

## Support

The following is the support matrix of sites and the respective video resolutions offered. **To request support for a site, or complain about a broken site, please open a [Github issue](https://github.com/cynthia2006/hanime-plugin/issues).**

|                 | 720p  | 1080p | 4K   |
| --------------- | ----- | ----- | ---- |
| hstream.moe     | ✅    | ✅ †  | ✅ † |
| oppai.stream    | ✅    | ✅ ‡  | ✅ ‡ |
| hentaihaven.com | ✅    | ✅    | ❌    |
| hanime.tv       | ✅    | ❌*    | ❌    |
| hanime1.me      | ✅    | ✅    | ❌    |
| rule34video.com | ✅    | ✅    | ✅   |
| ohentai.org     | ✅    | ❌     | ❌    |
| hentaimama.io   | ✅    | ❌     | ❌    |
| hanime.red      | ❌     | ✅    | ❌    |

\* Requires paid membership, and is beyond the scope of this plugin.

† [AV1](https://en.wikipedia.org/wiki/AV1) codec. ‡ [VP9](https://en.wikipedia.org/wiki/VP9) codec.


| Site             | Video | Playlist | User profile / channel | Search | Subscriptions | Works without cookies                          | Works without `--impersonate chrome` | Notes |
| ---              | :---: | :---:    | :---:                  | :---:  | :---:         | ---                                            |--------------------------------------| --- |
| hanime1.me       | ✅    | ✅       | ✅                     | ✅     | ✅            | Public videos, search, public user pages       | Usually yes                          | cookies required for `/subscriptions`, `/user/<id>/{likes,saves,histories}` |
| rule34video.com  | ✅    | ✅       | ✅                     | ✅     | ✅            | Public videos, search, public member tabs      | Yes                                  | cookies required for `/my/*` tabs |


## Examples

### Downloading a single video

```
$ yt-dlp https://hanime.tv/videos/hentai/fuzzy-lips-1
```

or 

```
$ yt-dlp -f - https://hentaihaven.com/video/soshite-watashi-wa-sensei-ni/episode-1
```

### Downloading a playlist / search

```
$ yt-dlp --impersonate chrome 'https://hanime1.me/search?query=Somato'
$ yt-dlp 'https://rule34video.com/models/seejaydj/'
```

## FAQ

### `ERROR: Data must be padded to 16 byte boundary in CBC mode`

See https://github.com/yt-dlp/yt-dlp/issues/3810 and https://github.com/cynthia2006/hanime-plugin/issues/8

The issue is with yt-dlp's HLS fragment downloader, and a well-known fix is adding the `--downloader ffmpeg` option.

### Why support for these sites aren't added to yt-dlp?

yt-dlp has a policy against piracy sites; hentai sites belong to that category. The original extractor for hanime.tv was a [separate tool](https://github.com/rxqv/htv), unmaintained since 2021. I raised [a feature request](https://github.com/yt-dlp/yt-dlp/issues/4007), but it was declined. I had maintained a fork of yt-dlp with a hanime.tv extractor adapted from the original code, before I lost access to that account. This plugin had initially been based off of that. Support for other sites have been added in late 2025.

### Why doesn't the hanime.tv extractor work?

Please make sure Deno is installed, and the install directory (folder) is in `PATH`; if it's not, add it, following the instructions for your operating system, because otherwise it would not work.
