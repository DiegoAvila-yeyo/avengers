"""tests/tools/test_scraper.py — 6 casos de prueba para DynamicScraper."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from tools.scraper import DynamicScraper, ScrapedPage, ScraperConfig

_HTML_HELLO = "<html><body><p>Hello World</p><script>bad()</script></body></html>"


def _build_mock_client(responses: list[MagicMock]) -> MagicMock:
    """Construye un AsyncClient mock que devuelve *responses* en orden."""
    client = AsyncMock()
    client.get = AsyncMock(side_effect=responses)
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=client)
    cm.__aexit__ = AsyncMock(return_value=None)
    return cm


def _ok_resp(text: str = _HTML_HELLO) -> MagicMock:
    r = MagicMock()
    r.status_code = 200
    r.text = text
    r.headers = {}
    r.raise_for_status = MagicMock()
    return r


# ── Caso 1: Scrape exitoso ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_scrape_success() -> None:
    scraper = DynamicScraper()
    with patch("tools.scraper.httpx.AsyncClient", return_value=_build_mock_client([_ok_resp()])):
        page = await scraper.scrape("https://example.com")

    assert isinstance(page, ScrapedPage)
    assert page.status_code == 200
    assert "Hello World" in page.content
    assert "bad()" not in page.content  # script eliminado


# ── Caso 2: Concurrencia — scrape_many devuelve todas las páginas ───────────


@pytest.mark.asyncio
async def test_scrape_many_concurrent() -> None:
    urls = ["https://a.com", "https://b.com"]
    scraper = DynamicScraper()

    resps = [_ok_resp(), _ok_resp()]
    with (
        patch(
            "tools.scraper.httpx.AsyncClient",
            return_value=_build_mock_client(resps),
        ),
        patch("tools.scraper.safe_write_text") as mock_write,
    ):
        pages = await scraper.scrape_many(urls, mission_id="m-001")

    assert len(pages) == 2
    assert mock_write.call_count == 2


# ── Caso 3: Retry en 429 con cabecera Retry-After ──────────────────────────


@pytest.mark.asyncio
async def test_scrape_retry_429_with_retry_after() -> None:
    r429 = MagicMock()
    r429.status_code = 429
    r429.headers = {"Retry-After": "0"}
    r429.raise_for_status = MagicMock()

    scraper = DynamicScraper(ScraperConfig(max_retries=3))
    with (
        patch(
            "tools.scraper.httpx.AsyncClient",
            return_value=_build_mock_client([r429, _ok_resp()]),
        ),
        patch("tools.scraper.asyncio.sleep") as mock_sleep,
    ):
        page = await scraper.scrape("https://example.com")

    mock_sleep.assert_called_once_with(0.0)
    assert page.status_code == 200


# ── Caso 4: Retry en error de red con backoff exponencial ──────────────────


@pytest.mark.asyncio
async def test_scrape_retry_on_request_error() -> None:
    scraper = DynamicScraper(ScraperConfig(max_retries=3, backoff_base=2.0))
    net_err = httpx.RequestError("timeout", request=MagicMock())

    with (
        patch(
            "tools.scraper.httpx.AsyncClient",
            return_value=_build_mock_client([net_err, _ok_resp()]),
        ),
        patch("tools.scraper.asyncio.sleep") as mock_sleep,
    ):
        page = await scraper.scrape("https://example.com")

    mock_sleep.assert_called_once_with(1.0)  # 2.0 ** 0 = 1.0
    assert page.status_code == 200


# ── Caso 5: Root Jail — archivos escritos bajo output/scrape_cache/ ─────────


@pytest.mark.asyncio
async def test_scrape_many_root_jail() -> None:
    scraper = DynamicScraper()
    with (
        patch("tools.scraper.httpx.AsyncClient", return_value=_build_mock_client([_ok_resp()])),
        patch("tools.scraper.safe_write_text") as mock_write,
    ):
        await scraper.scrape_many(["https://test.com/page"], mission_id="mission-42")

    written_path: str = mock_write.call_args[0][0]
    assert written_path.startswith("output/scrape_cache/mission-42/")
    assert written_path.endswith(".json")


# ── Caso 6: Truncado de contenido a max_content_chars ──────────────────────


@pytest.mark.asyncio
async def test_content_truncation() -> None:
    long_text = "A" * 20_000
    big_html = f"<html><body><p>{long_text}</p></body></html>"
    cfg = ScraperConfig(max_content_chars=10_000)
    scraper = DynamicScraper(cfg)

    with patch(
        "tools.scraper.httpx.AsyncClient",
        return_value=_build_mock_client([_ok_resp(big_html)]),
    ):
        page = await scraper.scrape("https://example.com")

    assert len(page.content) <= 10_000
