"""Throttled HTTP client with robots.txt compliance, request budget, and media download."""

from __future__ import annotations

import mimetypes
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import requests

from .constants import REPO_ROOT

DEFAULT_USER_AGENT = "AcademicMarineResearch/1.0 (rhincodon-typus-occurrence-survey)"
RETRYABLE_STATUS = {429, 500, 502, 503, 504}
IMAGE_EXT_MAP = {
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
}


class RequestBudgetExceeded(RuntimeError):
    """Raised when a scraping run reaches its configured max_requests cap."""


class RobotsDisallowedError(RuntimeError):
    """Raised when robots.txt forbids fetching the target URL."""


@dataclass
class RobotsPolicy:
    parser: RobotFileParser | None
    allow_all: bool
    disallow_all: bool
    crawl_delay: float | None


class RobotsCache:
    """Per-host cache of parsed robots.txt rules."""

    def __init__(self, user_agent: str = DEFAULT_USER_AGENT) -> None:
        self.user_agent = user_agent
        self._cache: dict[str, RobotsPolicy] = {}

    def get_policy(self, client: "ThrottledHttpClient", url: str) -> RobotsPolicy:
        parsed = urlparse(url)
        origin = f"{parsed.scheme}://{parsed.netloc}"
        if origin in self._cache:
            return self._cache[origin]

        robots_url = f"{origin}/robots.txt"
        try:
            resp = client.raw_get(robots_url, timeout=10.0)
            if resp.status_code in (404, 410):
                policy = RobotsPolicy(parser=None, allow_all=True, disallow_all=False, crawl_delay=None)
            elif resp.status_code in (401, 403):
                policy = RobotsPolicy(parser=None, allow_all=False, disallow_all=True, crawl_delay=None)
            elif resp.status_code >= 500:
                policy = RobotsPolicy(parser=None, allow_all=False, disallow_all=True, crawl_delay=None)
            else:
                rp = RobotFileParser()
                rp.parse(resp.text.splitlines())
                delay = rp.crawl_delay(self.user_agent) or rp.crawl_delay("*")
                crawl_delay = float(delay) if delay is not None else None
                policy = RobotsPolicy(parser=rp, allow_all=False, disallow_all=False, crawl_delay=crawl_delay)
        except requests.RequestException:
            # Fail safe: if robots.txt cannot be reached, do not crawl that host.
            policy = RobotsPolicy(parser=None, allow_all=False, disallow_all=True, crawl_delay=None)

        self._cache[origin] = policy
        return policy

    def check(self, client: "ThrottledHttpClient", url: str) -> tuple[bool, float | None]:
        policy = self.get_policy(client, url)
        if policy.disallow_all:
            return False, None
        if policy.allow_all or policy.parser is None:
            return True, policy.crawl_delay
        return policy.parser.can_fetch(self.user_agent, url), policy.crawl_delay


class ThrottledHttpClient:
    """Requests session wrapper enforcing per-host throttling, robots.txt, and request caps."""

    def __init__(
        self,
        min_delay_sec: float = 1.5,
        max_requests: int = 25,
        max_retries: int = 3,
        user_agent: str = DEFAULT_USER_AGENT,
        session: requests.Session | None = None,
        respect_robots: bool = True,
    ) -> None:
        self.min_delay_sec = max(0.0, float(min_delay_sec))
        self.max_requests = int(max_requests)
        self.max_retries = int(max_retries)
        self.user_agent = user_agent
        self.respect_robots = respect_robots
        self.session = session or requests.Session()
        self.session.headers.setdefault("User-Agent", self.user_agent)
        self.robots = RobotsCache(user_agent=self.user_agent)
        self._last_host_request: dict[str, float] = {}
        self.requests_made = 0

    def _consume_budget(self) -> None:
        if self.max_requests > 0 and self.requests_made >= self.max_requests:
            raise RequestBudgetExceeded(f"Reached max_requests cap ({self.max_requests})")
        self.requests_made += 1

    def _throttle_host(self, url: str, extra_delay: float | None = None) -> None:
        host = urlparse(url).netloc.lower()
        delay = max(self.min_delay_sec, extra_delay or 0.0)
        if delay <= 0 or host not in self._last_host_request:
            self._last_host_request[host] = time.monotonic()
            return
        elapsed = time.monotonic() - self._last_host_request[host]
        wait = delay - elapsed
        if wait > 0:
            time.sleep(wait)
        self._last_host_request[host] = time.monotonic()

    def raw_get(
        self,
        url: str,
        params: dict[str, Any] | None = None,
        timeout: float = 20.0,
        stream: bool = False,
        extra_delay: float | None = None,
    ) -> requests.Response:
        last_err: Exception | None = None
        for attempt in range(self.max_retries + 1):
            self._consume_budget()
            self._throttle_host(url, extra_delay=extra_delay)
            try:
                resp = self.session.get(url, params=params, timeout=timeout, stream=stream)
                if resp.status_code in RETRYABLE_STATUS:
                    retry_after = resp.headers.get("Retry-After")
                    wait = float(retry_after) if retry_after and retry_after.isdigit() else (1.5 * (2**attempt))
                    if attempt < self.max_retries:
                        time.sleep(min(wait, 30.0))
                        continue
                return resp
            except requests.RequestException as exc:
                last_err = exc
                if attempt == self.max_retries:
                    break
                time.sleep(1.5 * (2**attempt))
        raise RuntimeError(f"GET {url} failed after {self.max_retries + 1} attempts: {last_err}")

    def get(
        self,
        url: str,
        params: dict[str, Any] | None = None,
        timeout: float = 20.0,
        check_robots: bool | None = None,
        stream: bool = False,
    ) -> requests.Response:
        do_robots = self.respect_robots if check_robots is None else check_robots
        crawl_delay: float | None = None
        if do_robots:
            allowed, crawl_delay = self.robots.check(self, url)
            if not allowed:
                raise RobotsDisallowedError(f"robots.txt disallows {url}")
        resp = self.raw_get(url, params=params, timeout=timeout, stream=stream, extra_delay=crawl_delay)
        resp.raise_for_status()
        return resp

    def download_media(
        self,
        media_url: str,
        dest_dir: Path,
        sighting_id: str,
        max_bytes: int = 10_000_000,
        check_robots: bool | None = None,
    ) -> str | None:
        if not media_url:
            return None
        dest_dir.mkdir(parents=True, exist_ok=True)
        for existing_ext in (".jpg", ".jpeg", ".png", ".webp", ".gif"):
            candidate = dest_dir / f"{sighting_id}{existing_ext}"
            if candidate.exists():
                return _to_repo_relative_posix(candidate)

        resp = self.get(media_url, timeout=20.0, check_robots=check_robots, stream=True)
        ctype = (resp.headers.get("Content-Type") or "").split(";")[0].strip().lower()
        if ctype and not ctype.startswith("image/"):
            return None

        ext = IMAGE_EXT_MAP.get(ctype)
        if not ext:
            guessed = mimetypes.guess_extension(ctype) if ctype else None
            if not guessed:
                path_ext = Path(urlparse(media_url).path).suffix.lower()
                guessed = path_ext if path_ext in (".jpg", ".jpeg", ".png", ".webp", ".gif") else ".jpg"
            ext = ".jpg" if guessed == ".jpe" else guessed

        out_path = dest_dir / f"{sighting_id}{ext}"
        total = 0
        chunks: list[bytes] = []
        for chunk in resp.iter_content(chunk_size=65536):
            if not chunk:
                continue
            total += len(chunk)
            if total > max_bytes:
                raise ValueError(f"Media {media_url} exceeded max_bytes={max_bytes}")
            chunks.append(chunk)
        if not chunks:
            return None
        out_path.write_bytes(b"".join(chunks))
        return _to_repo_relative_posix(out_path)


def _to_repo_relative_posix(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return path.as_posix()
