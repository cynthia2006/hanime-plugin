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

## Support

The following is the support matrix of sites and the respective video resolutions offered. **To request support for a site, or complain about a broken site, please open a [Github issue](https://github.com/cynthia2006/hanime-plugin/issues).**

|                 | 720p  | 1080p | 4K    |
| --------------- | ----- | ----- | ----- |
| hstream.moe     | ✅    | ✅ †  | ❌     |
| oppai.stream    | ✅    | ✅ ‡  | ✅ ‡  |
| hentaihaven.com | ✅ ‡  | ✅ ‡  | ❌     |
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


### Is Deno still required for hanime.tv?
No, Deno is no longer required for extracting from **hanime.tv**. 

### `ERROR: Data must be padded to 16 byte boundary in CBC mode`

See [https://github.com/yt-dlp/yt-dlp/issues/3810](https://github.com/yt-dlp/yt-dlp/issues/1297#issuecomment-2408580037) and https://github.com/cynthia2006/hanime-plugin/issues/8

[CBC mode](https://en.wikipedia.org/wiki/Block_cipher_mode_of_operation#Cipher_block_chaining_(CBC)) is an AES mode used to encrypt HLS streams. Since AES is a symmetric block cipher operating on 128-bit (16 byte) blocks, data is required to align to 16-bit block boundaries for successful decryption. The issue is with yt-dlp's AES decryption routines that does not add PKCS7 padding to ciphertext whose padding has been stripped, and the underlying library [pycryptodomex](https://www.pycryptodome.org/)'s `AES.decrypt()` method expects padded data. A workaround is to use the `--downloader ffmpeg` option.

```sh
$ yt-dlp --download-ffmpeg https://hanime.tv/videos/hentai/fuzzy-lips-1
```

### Why support for these sites aren't added to yt-dlp?

yt-dlp has a policy against piracy sites, and hentai sites belong to that category. The original extractor for hanime.tv was a [separate tool](https://github.com/rxqv/htv), unmaintained since 2021. I raised [a feature request](https://github.com/yt-dlp/yt-dlp/issues/4007), but it was declined. I had maintained a fork of yt-dlp with a hanime.tv extractor adapted from the original code, before I lost access to that account. This plugin had initially been based off of that. Support for other sites have been added in late 2025.

## Contribution

The hentai sites this plugin scrapes off of are subject to abrupt changes from the upstream without notice, and are highly likely break support. I wouldn't be aware unless an issue ticket is created, and even then I might be slow to respond. 

In such a case, follow the workflow described [here](./CONTRIBUTING.md). It might be somewhat different depending on the enviroment, but the core process is more or less the same.