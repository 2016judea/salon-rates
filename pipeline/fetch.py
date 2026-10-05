"""Polite cached GET. Every response body is written gzipped to pipeline/cache/<source>/
before anything parses it, so a parser change never costs a second request."""
import gzip
import hashlib
import time
import urllib.error
import urllib.request
from pathlib import Path

CACHE = Path(__file__).resolve().parent / "cache"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/128.0 Safari/537.36")
MIN_GAP = 1.0  # seconds between live requests, per process
_last = [0.0]


def path_for(source, url):
    return CACHE / source / (hashlib.sha1(url.encode()).hexdigest() + ".html.gz")


def get(source, url, refresh=False):
    """Return (status, text). Cached 200s are reused; 404s are cached as empty."""
    p = path_for(source, url)
    if p.exists() and not refresh:
        body = gzip.decompress(p.read_bytes()).decode("utf-8", "replace")
        return (404 if body == "" else 200), body
    wait = MIN_GAP - (time.time() - _last[0])
    if wait > 0:
        time.sleep(wait)
    for attempt in range(3):
        _last[0] = time.time()
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "en-US"})
            with urllib.request.urlopen(req, timeout=40) as r:
                text = r.read().decode("utf-8", "replace")
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(gzip.compress(text.encode()))
            return 200, text
        except urllib.error.HTTPError as e:
            if e.code in (404, 410):
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_bytes(gzip.compress(b""))
                return e.code, ""
            if e.code in (403, 429) or e.code >= 500:
                time.sleep(10 * (attempt + 1))
                continue
            return e.code, ""
        except Exception:
            time.sleep(5 * (attempt + 1))
    return 0, ""
