"""Web search through Tavily, with a server-wide daily cap and a short cache."""
import logging
import threading
import time
from dataclasses import dataclass
from datetime import date
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse

import httpx

from config import Config

logger = logging.getLogger(__name__)

TAVILY_URL = "https://api.tavily.com/search"
CHUNK_SEPARATOR = "[...]"  # Tavily joins the snippets it picked from one page with this
MAX_CACHED_QUERIES = 500


class WebSearchError(RuntimeError):
    """Search failed; the message is safe to show the user."""


@dataclass
class WebResult:
    url: str
    title: str
    site: str
    content: str
    published: Optional[str] = None
    score: Optional[float] = None

    def chunks(self) -> List[str]:
        return [c.strip() for c in self.content.split(CHUNK_SEPARATOR) if c.strip()]


def is_web_url(url: str) -> bool:
    parsed = urlparse(url or "")
    return parsed.scheme in ("http", "https") and bool(parsed.hostname)


def site_of(url: str) -> str:
    host = (urlparse(url).hostname or "").lower()
    return host[4:] if host.startswith("www.") else host


class TavilyProvider:
    def __init__(self, api_key: str, client: Optional[httpx.Client] = None):
        self.api_key = api_key
        self.client = client or httpx.Client(timeout=Config.WEB_TIMEOUT)

    def search(self, query: str, max_results: int) -> List[WebResult]:
        payload = {
            "query": query[:400],
            "search_depth": "basic",
            "max_results": max_results,
            "chunks_per_source": 3,
            "include_published_date": True,
        }
        if Config.WEB_BLOCKED_DOMAINS:
            payload["exclude_domains"] = Config.WEB_BLOCKED_DOMAINS
        headers = {"Authorization": f"Bearer {self.api_key}"}

        resp = None
        for attempt in range(2):
            try:
                resp = self.client.post(TAVILY_URL, json=payload, headers=headers)
            except httpx.HTTPError as e:
                logger.warning(f"Web search request failed: {type(e).__name__}")
                resp = None
                continue
            if resp.status_code < 500:
                break
        if resp is None:
            raise WebSearchError("Web search is unavailable right now. Try again shortly.")
        if resp.status_code == 401:
            raise WebSearchError("The web search API key is invalid.")
        if resp.status_code == 429:
            raise WebSearchError("Web search is rate limited right now. Try again in a minute.")
        if resp.status_code in (432, 433):
            raise WebSearchError("The web search plan's credit limit has been reached.")
        if resp.status_code >= 400:
            raise WebSearchError(f"Web search failed (HTTP {resp.status_code}).")

        results = []
        for r in (resp.json() or {}).get("results") or []:
            url = r.get("url") or ""
            content = (r.get("content") or "").strip()
            if not is_web_url(url) or not content:
                continue
            results.append(WebResult(
                url=url,
                title=(r.get("title") or site_of(url)).strip()[:200],
                site=site_of(url),
                content=content,
                published=r.get("published_date"),
                score=r.get("score"),
            ))
        return results


class WebSearch:
    """Shared by every run in this process, so the cap and cache cover the whole server."""

    def __init__(self, provider):
        self.provider = provider
        self._cache: Dict[str, Tuple[float, List[WebResult]]] = {}
        self._day: Optional[date] = None
        self._count = 0
        self._lock = threading.Lock()

    def search(self, query: str) -> List[WebResult]:
        key = " ".join(query.lower().split())
        now = time.time()
        with self._lock:
            hit = self._cache.get(key)
            if hit and now - hit[0] < Config.WEB_CACHE_SECONDS:
                return hit[1]
            today = date.today()
            if self._day != today:
                self._day, self._count = today, 0
            if self._count >= Config.WEB_DAILY_SEARCH_CAP:
                raise WebSearchError("The daily web search limit has been reached. Try again tomorrow.")
            # Counted before the call, so failed searches also use up the cap.
            self._count += 1

        results = self.provider.search(query, Config.WEB_RESULTS_PER_QUERY)

        with self._lock:
            if len(self._cache) >= MAX_CACHED_QUERIES:
                self._cache.pop(min(self._cache, key=lambda k: self._cache[k][0]))
            self._cache[key] = (now, results)
        return results


_web: Optional[WebSearch] = None
_web_lock = threading.Lock()


def get_web_search() -> Optional[WebSearch]:
    """The shared web search, or None when no API key is configured."""
    global _web
    if not Config.TAVILY_API_KEY:
        return None
    with _web_lock:
        if _web is None:
            _web = WebSearch(TavilyProvider(Config.TAVILY_API_KEY))
        return _web
