"""A read-only file object over HTTP range requests, so h5py can read a few chunks of a large remote netCDF-4
file without downloading it (used by pipeline/fetch/chirps.py; requests and h5py are already approved).

Blocks are cached; a read spanning several missing blocks is one request. HTTP 429 (too many requests) and 5xx
answers are retried with a doubling wait (2 s up to 60 s). An optional deadline (a time.time() value) stops a
read cleanly with DeadlineReached. Counts requests, bytes and seconds for the data card.
"""
import io
import time


class DeadlineReached(RuntimeError):
    """The owner's stop time passed (rain check B: CHIRPS stops by Saturday 08:00)."""


class RangeFile(io.RawIOBase):
    def __init__(self, url, block_size=262144, max_retry=10, deadline=None, user_agent="khet-sathi-pipeline"):
        import requests
        self.url, self.block_size, self.max_retry, self.deadline = url, block_size, max_retry, deadline
        self.session = requests.Session()
        self.session.headers["User-Agent"] = user_agent
        self.pos, self.cache = 0, {}
        self.n_requests = self.n_retries = self.bytes = 0
        self.seconds = 0.0
        self.size = int(self._get(None).headers["Content-Length"])

    def _check_deadline(self):
        if self.deadline is not None and time.time() >= self.deadline:
            raise DeadlineReached(f"deadline passed while reading {self.url}")

    def _get(self, rng):
        delay = 2.0
        for _ in range(self.max_retry + 1):
            self._check_deadline()
            t0 = time.time()
            if rng is None:
                r = self.session.head(self.url, timeout=120, allow_redirects=True)
            else:
                r = self.session.get(self.url, headers={"Range": f"bytes={rng[0]}-{rng[1]}"}, timeout=300)
            self.n_requests += 1
            self.seconds += time.time() - t0
            if r.status_code in (429, 500, 502, 503, 504):
                self.n_retries += 1
                time.sleep(delay)
                delay = min(delay * 2, 60.0)
                continue
            r.raise_for_status()
            if rng is not None:
                if r.status_code != 206:
                    raise RuntimeError(f"the server ignored the Range header (HTTP {r.status_code}) for {self.url}")
                self.bytes += len(r.content)
            return r
        raise RuntimeError(f"no answer after {self.max_retry} retries: {self.url}")

    def readable(self):
        return True

    def seekable(self):
        return True

    def seek(self, offset, whence=io.SEEK_SET):
        self.pos = {io.SEEK_SET: offset, io.SEEK_CUR: self.pos + offset, io.SEEK_END: self.size + offset}[whence]
        return self.pos

    def tell(self):
        return self.pos

    def _fetch_blocks(self, first, last):
        missing = [i for i in range(first, last + 1) if i not in self.cache]
        if not missing:
            return
        s = missing[0] * self.block_size
        e = min((missing[-1] + 1) * self.block_size, self.size) - 1
        data = self._get((s, e)).content
        for i in range(missing[0], missing[-1] + 1):
            off = i * self.block_size - s
            self.cache.setdefault(i, data[off: off + self.block_size])

    def readinto(self, b):
        n = min(len(b), max(0, self.size - self.pos))
        if n == 0:
            return 0
        end = self.pos + n
        self._fetch_blocks(self.pos // self.block_size, (end - 1) // self.block_size)
        out, pos = bytearray(), self.pos
        while pos < end:
            i = pos // self.block_size
            blk = self.cache[i]
            off = pos - i * self.block_size
            take = min(len(blk) - off, end - pos)
            out += blk[off: off + take]
            pos += take
        b[:n] = out
        self.pos = end
        return n

    def stats(self):
        return {"requests": self.n_requests, "retries": self.n_retries, "bytes": self.bytes,
                "http_seconds": round(self.seconds, 1)}
