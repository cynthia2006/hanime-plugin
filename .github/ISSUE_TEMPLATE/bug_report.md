---
name: Bug report
about: Report bugs regarding the site extractors
title: "[Bug]"
labels: bug
assignees: cynthia2006

---

# Description
Describe the bug in detail in a helpful manner to help diagnosis.

# CLI Logs
Verbose terminal logs. Ensure `--verbose` flag is provided to yt-dlp.

```
$ yt-dlp --verbose https://hanime.tv/videos/hentai/fuzzy-lips-1
[debug] Command-line config: ['-vF', 'https://hanime.tv/videos/hentai/fuzzy-lips-1']
[debug] Encodings: locale UTF-8, fs utf-8, pref UTF-8, out utf-8, error utf-8, screen utf-8
[debug] yt-dlp version stable@2026.03.17 from yt-dlp/yt-dlp [04d6974f5] (pip)
[debug] Python 3.14.3 (CPython x86_64 64bit) - Linux-6.19.12-200.fc43.x86_64-x86_64-with-glibc2.42 (OpenSSL 3.5.4 30 Sep 2025, glibc 2.42)
[debug] exe versions: ffmpeg 7.1.2 (setts), ffprobe 7.1.2
[debug] Optional libraries: certifi-2025.07.09, curl_cffi-0.14.0, requests-2.32.5, sqlite3-3.50.2, urllib3-2.6.3
[debug] JS runtimes: deno-2.7.14
[debug] Proxy map: {}
[debug] Request Handlers: urllib, requests, curl_cffi
[debug] Extractor Plugins: HanimeRedIE, HanimeTVIE, HentaiHavenIE, HentaimamaIE, HstreamIE, OhentaiIE, OppaiStreamIE
[debug] Plugin directories: /home/cynthia/.local/lib/python3.14/site-packages/yt_dlp_plugins
[debug] Loaded 1871 extractors
[HanimeTV] Extracting URL: https://hanime.tv/videos/hentai/fuzzy-lips-1
[HanimeTV] fuzzy-lips-1: Downloading webpage
[HanimeTV] fuzzy-lips-1: Caching generator script
[HanimeTV] fuzzy-lips-1: Downloading JSON metadata
[debug] Formats sorted by: hasvid, ie_pref, lang, quality, res, fps, hdr:12(7), vcodec, channels, acodec, size, br, asr, proto, vext, aext, hasaud, source, id
...
```
