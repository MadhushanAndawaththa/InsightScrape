import httpx
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from typing import Tuple, List
from models import PageMetrics

# ─── Page Fetching ────────────────────────────────────────────

async def _fetch_with_playwright(url: str) -> str:
    """Primary fetcher: uses a real Chromium browser to render JS-heavy pages
    and bypass bot-protection (Cloudflare, WAF). Returns fully rendered HTML."""
    from playwright.async_api import async_playwright

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
            ],
        )
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1440, "height": 900},
            java_script_enabled=True,
            locale="en-US",
            timezone_id="America/New_York",
        )
        # Remove the webdriver flag so sites don't detect automation
        await context.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )
        page = await context.new_page()

        try:
            # First load — wait for network to settle
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)

            # Wait for JS rendering: either networkidle or a reasonable timeout
            try:
                await page.wait_for_load_state("networkidle", timeout=10000)
            except Exception:
                pass  # Some SPAs never reach networkidle; that's OK

            # Extra wait for loading animations / spinners to disappear
            # Check if the page has minimal content yet; if not, wait longer
            for _ in range(5):
                body_text = await page.evaluate("document.body?.innerText?.length || 0")
                if body_text > 100:
                    break
                await page.wait_for_timeout(1000)

            html = await page.content()
        finally:
            await browser.close()

        return html


async def _fetch_with_httpx(url: str) -> str:
    """Lightweight fallback: fast but cannot render JS or bypass bot-protection."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/131.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Connection": "keep-alive",
    }
    async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
        response = await client.get(url, headers=headers)
        response.raise_for_status()

        # Guard against binary responses (compressed without decompression, PDFs, etc.)
        content_type = response.headers.get("content-type", "")
        if "text" not in content_type and "html" not in content_type and "xml" not in content_type:
            raise ValueError(f"Non-HTML content-type: {content_type}")

        text = response.text
        # Detect if the "text" is actually binary garbage
        if text and _is_binary_content(text):
            raise ValueError("Response appears to be binary/compressed — cannot parse as HTML")

        return text


def _is_binary_content(text: str, sample_size: int = 500) -> bool:
    """Heuristic: if more than 15% of chars in the first N chars are non-printable,
    the content is likely binary/compressed."""
    sample = text[:sample_size]
    non_printable = sum(
        1 for ch in sample
        if not ch.isprintable() and ch not in ('\n', '\r', '\t')
    )
    return (non_printable / max(len(sample), 1)) > 0.15


async def fetch_page(url: str) -> Tuple[str, str]:
    """Fetch a page's HTML. Returns (html, scrape_method).
    Tries Playwright first for JS-rendered content; falls back to httpx."""
    pw_error = None
    try:
        html = await _fetch_with_playwright(url)
        # Validate we actually got meaningful HTML
        if html and len(html.strip()) > 100 and not _is_binary_content(html):
            return html, "playwright"
        pw_error = "Playwright returned empty or binary content"
    except Exception as e:
        pw_error = str(e)

    print(f"[scraper] Playwright failed ({pw_error}), falling back to httpx…")

    try:
        html = await _fetch_with_httpx(url)
        return html, "httpx"
    except Exception as httpx_err:
        # Both methods failed — raise the more informative error
        raise RuntimeError(
            f"Both scrapers failed.\n"
            f"  Playwright: {pw_error}\n"
            f"  httpx: {httpx_err}"
        )


# ─── CTA Detection ───────────────────────────────────────────

_CTA_KEYWORDS = {
    "get started", "sign up", "contact", "buy", "try", "learn more",
    "schedule", "book", "request", "download", "register",
    "shop now", "order now", "subscribe", "explore", "call now",
    "start free", "free trial", "demo",
}


def _is_inside_nav(element) -> bool:
    """Check if an element is nested inside a <nav> or element with role=navigation."""
    for parent in element.parents:
        if parent.name == "nav" or parent.get("role") == "navigation":
            return True
    return False


def determine_if_cta(element) -> bool:
    text = element.get_text(separator=' ', strip=True).lower()

    # Skip tiny icon-only buttons and excessively long text
    if len(text) < 2 or len(text) > 60:
        return False

    # Keyword match
    if any(kw in text for kw in _CTA_KEYWORDS):
        return True

    # CSS class match — but skip if inside <nav> (nav links aren't CTAs)
    classes = element.get("class", [])
    if isinstance(classes, str):
        classes = [classes]

    cta_classes = {"btn", "cta", "button", "primary"}
    has_cta_class = any(
        any(part in cls.lower() for part in cta_classes) for cls in classes
    )
    if has_cta_class and not _is_inside_nav(element):
        return True

    # Role match — only for non-nav elements
    role = element.get("role")
    if role == "button" and text and not _is_inside_nav(element):
        return True

    return False


# ─── Metrics Extraction ──────────────────────────────────────

def extract_metrics(html: str, base_url: str, scrape_method: str = "httpx") -> Tuple[PageMetrics, str]:
    soup = BeautifulSoup(html, "html.parser")

    # Remove scripts, styles, etc.
    for tag in soup(["script", "style", "noscript", "svg", "path"]):
        tag.extract()

    text = soup.get_text(separator='\n', strip=True)
    word_count = len(text.split())

    # Headings
    headings_count = {"h1": 0, "h2": 0, "h3": 0, "h4": 0, "h5": 0, "h6": 0}
    heading_hierarchy = []

    for heading in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"]):
        tag_name = heading.name
        headings_count[tag_name] += 1
        heading_text = heading.get_text(separator=' ', strip=True)
        if heading_text:
            heading_hierarchy.append((tag_name.upper(), heading_text[:100]))

    # Meta
    meta_title = soup.title.string if soup.title else None
    if not meta_title:
        meta_title_tag = soup.find("meta", property="og:title") or soup.find("meta", attrs={"name": "twitter:title"})
        if meta_title_tag:
            meta_title = meta_title_tag.get("content")

    meta_desc_tag = soup.find("meta", attrs={"name": "description"}) or soup.find("meta", property="og:description")
    meta_description = meta_desc_tag.get("content") if meta_desc_tag else None

    # Links & CTAs — de-duplicate by tracking seen elements
    base_domain = urlparse(base_url).netloc
    internal_links = 0
    external_links = 0
    cta_count = 0
    seen_cta_ids: set = set()

    for a in soup.find_all("a"):
        href = a.get("href", "")
        if href and not href.startswith(("javascript:", "mailto:", "tel:", "#")):
            parsed_href = urlparse(href)
            if not parsed_href.netloc or parsed_href.netloc == base_domain:
                internal_links += 1
            else:
                external_links += 1

        if determine_if_cta(a):
            seen_cta_ids.add(id(a))
            cta_count += 1

    # Non-anchor CTAs (buttons, divs, spans) — skip if already counted
    for btn in soup.find_all(["button", "div", "span"]):
        if id(btn) not in seen_cta_ids and determine_if_cta(btn):
            seen_cta_ids.add(id(btn))
            cta_count += 1

    # Images
    images = soup.find_all("img")
    image_count = len(images)
    images_missing_alt_count = 0
    images_decorative_alt_count = 0

    for img in images:
        if not img.has_attr("alt"):
            images_missing_alt_count += 1
        elif img["alt"].strip() == "":
            images_decorative_alt_count += 1

    images_missing_alt_pct = (images_missing_alt_count / image_count * 100) if image_count > 0 else 0.0

    # Content quality warning
    content_quality_warning = None
    if scrape_method == "httpx" and (word_count < 200 or image_count == 0):
        content_quality_warning = (
            "Limited content extracted — this page likely uses JavaScript rendering. "
            "Some text, images, and interactive elements may not have been captured. "
            "Scores may be lower than the actual page quality."
        )
    elif scrape_method == "playwright" and word_count < 50:
        content_quality_warning = (
            "Very little content was found even with full JS rendering. "
            "The page may use advanced loading techniques or may have minimal content."
        )

    metrics = PageMetrics(
        word_count=word_count,
        headings_count=headings_count,
        heading_hierarchy=heading_hierarchy,
        cta_count=cta_count,
        internal_links=internal_links,
        external_links=external_links,
        image_count=image_count,
        images_missing_alt_count=images_missing_alt_count,
        images_decorative_alt_count=images_decorative_alt_count,
        images_missing_alt_pct=round(images_missing_alt_pct, 2),
        meta_title=meta_title,
        meta_description=meta_description,
        scrape_method=scrape_method,
        content_quality_warning=content_quality_warning,
    )

    visible_text = f"Title: {meta_title}\nDescription: {meta_description}\n\n{text}"
    if len(visible_text) > 50000:
        visible_text = visible_text[:50000] + "\n...[TRUNCATED]"

    return metrics, visible_text
