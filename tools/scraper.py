"""tools/scraper.py — Motor de scraping dinámico para Thor (Prompt #06).

AMD-01: Todo caché se escribe bajo output/scrape_cache/{mission_id}/ via file_tools.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import httpx
from bs4 import BeautifulSoup
from pydantic import BaseModel

from tools.file_tools import safe_write_text

MAX_CONTENT_CHARS: int = 10_000
_STRIP_TAGS: tuple[str, ...] = ("script", "style", "noscript")


class ScrapedPage(BaseModel):
    url: str
    content: str
    status_code: int
    scraped_at: datetime


class ScraperConfig(BaseModel):
    max_retries: int = 3
    timeout: float = 10.0
    backoff_base: float = 2.0
    max_content_chars: int = MAX_CONTENT_CHARS


class DynamicScraper:
    def __init__(self, config: ScraperConfig | None = None) -> None:
        self._cfg = config or ScraperConfig()

    def _extract_text(self, html: str) -> str:
        soup = BeautifulSoup(html, "lxml")
        for tag in soup(list(_STRIP_TAGS)):
            tag.decompose()
        text = soup.get_text(separator=" ", strip=True)
        return text[: self._cfg.max_content_chars]

    async def scrape(self, url: str) -> ScrapedPage:
        last_exc: Exception = RuntimeError("No attempts made")
        async with httpx.AsyncClient(timeout=self._cfg.timeout) as client:
            for attempt in range(self._cfg.max_retries):
                try:
                    resp = await client.get(url, follow_redirects=True)
                    if resp.status_code == 429:
                        wait = float(
                            resp.headers.get("Retry-After", self._cfg.backoff_base**attempt)
                        )
                        await asyncio.sleep(wait)
                        continue
                    resp.raise_for_status()
                    return ScrapedPage(
                        url=url,
                        content=self._extract_text(resp.text),
                        status_code=resp.status_code,
                        scraped_at=datetime.now(tz=timezone.utc),  # noqa: UP017
                    )
                except httpx.HTTPStatusError as exc:
                    last_exc = exc
                    await asyncio.sleep(self._cfg.backoff_base**attempt)
                except httpx.RequestError as exc:
                    last_exc = exc
                    await asyncio.sleep(self._cfg.backoff_base**attempt)
        raise last_exc

    async def scrape_many(self, urls: list[str], mission_id: str) -> list[ScrapedPage]:
        pages = await asyncio.gather(*[self.scrape(u) for u in urls])
        for page in pages:
            slug = (
                page.url.replace("https://", "").replace("http://", "").replace("/", "_")[:80]
            )
            safe_write_text(
                f"output/scrape_cache/{mission_id}/{slug}.json",
                page.model_dump_json(indent=2),
            )
        return list(pages)
