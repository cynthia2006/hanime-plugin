import re
import json
import urllib.parse

from yt_dlp.extractor.common import InfoExtractor


class HstreamIE(InfoExtractor):
    _VALID_URL = r'https?://hstream\.moe/hentai/(?P<id>[a-z0-9\-]+)'

    def _extract_cookie(self, name):
        for cookie in self._downloader.cookiejar:
            if cookie.name == name:
                return cookie.value

    def _real_extract(self, url):
        # NOTE This has no use in the API itself; just a part of the webpage URL.
        video_id = self._match_id(url)

        page = self._download_webpage(url, video_id)
        e_id = self._search_regex(r'e_id" type="hidden" value="([^"]*)', page, 'episode id')

        payload = json.dumps({'episode_id': e_id})
        xsrf_token = self._extract_cookie('XSRF-TOKEN')

        video = self._download_json('https://hstream.moe/player/api', video_id, headers={
                    'Content-Type': 'application/json',
                    'Referer': url,
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-Xsrf-Token': urllib.parse.unquote(xsrf_token)
                }, data=payload.encode('utf-8'))

        # NOTE Although all CDNs essentially provide same resources, based on the client's
        # country, the speeds may differ.
        stream_domains = video.get('stream_domains') or []
        domains = [domain.rstrip('/') for domain in stream_domains if domain]

        if domains:
            orig_urlopen = self._downloader.urlopen
            current_domain = [domains[0]]

            def custom_urlopen(req, *args, **kwargs):
                url_str = req if isinstance(req, str) else req.url
                
                matched_domain = None
                for domain in domains:
                    if domain in url_str:
                        matched_domain = domain
                        break
                
                if not matched_domain:
                    return orig_urlopen(req, *args, **kwargs)
                
                active_domain = current_domain[0]
                if matched_domain != active_domain:
                    url_str = url_str.replace(matched_domain, active_domain, 1)
                    matched_domain = active_domain
                    if not isinstance(req, str):
                        req.url = url_str
                
                try:
                    start_idx = domains.index(matched_domain)
                except ValueError:
                    start_idx = 0
                
                ordered_domains = domains[start_idx:] + domains[:start_idx]
                
                last_err = None
                for domain in ordered_domains:
                    new_url = url_str.replace(matched_domain, domain, 1)
                    
                    if isinstance(req, str):
                        test_req = new_url
                    else:
                        req.url = new_url
                        test_req = req
                    
                    try:
                        self.to_screen(f'[hstream] Trying CDN download link: {new_url}')
                        res = orig_urlopen(test_req, *args, **kwargs)
                        current_domain[0] = domain
                        return res
                    except Exception as err:
                        self.report_warning(f'[hstream] Failed to download from {new_url}: {err}')
                        last_err = err
                        continue
                
                if last_err:
                    raise last_err
                raise Exception("All stream domains failed")

            self._downloader.urlopen = custom_urlopen

        cdn_url = '{}/{}'.format(domains[0] if domains else video['stream_domains'][0], video['stream_url'])
        formats = []
        
        for res in ('720', '1080', '2160'):
            results = self._extract_mpd_formats('{}/{}/manifest.mpd'.format(cdn_url, res),
                                                 video_id, mpd_id=res)

            formats.extend(results)

        poster_url = '{}/{}'.format('https://hstream.moe', video.get('poster'))
        return {
            'id': e_id,
            'title': video.get('title'),
            'thumbnail': poster_url,
            'formats': formats
        }
