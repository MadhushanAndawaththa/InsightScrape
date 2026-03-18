import httpx
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from typing import Tuple, List
from models import PageMetrics

async def fetch_page(url: str) -> str:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
    }
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.get(url, headers=headers)
        response.raise_for_status()
        return response.text

def determine_if_cta(element) -> bool:
    cta_keywords = {"get started", "sign up", "contact", "buy", "try", "learn more", "schedule", "book", "request", "download", "register"}
    text = element.get_text(separator=' ', strip=True).lower()
    
    if any(keyword in text for keyword in cta_keywords) and len(text) < 50:
        return True
    
    classes = element.get("class", [])
    if isinstance(classes, str):
        classes = [classes]
    
    cta_classes = {"btn", "cta", "button", "primary"}
    if any(any(c_part in cls.lower() for c_part in cta_classes) for cls in classes):
        return True
    
    role = element.get("role")
    if role in {"button", "link"} and text:
        return True

    return False

def extract_metrics(html: str, base_url: str) -> Tuple[PageMetrics, str]:
    soup = BeautifulSoup(html, "html.parser")
    
    # Remove scripts, styles, etc.
    for script in soup(["script", "style", "noscript", "svg", "path"]):
        script.extract()
    
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
    
    # Links
    base_domain = urlparse(base_url).netloc
    internal_links = 0
    external_links = 0
    cta_count = 0
    
    for a in soup.find_all("a"):
        href = a.get("href", "")
        if href and not href.startswith(("javascript:", "mailto:", "tel:", "#")):
            parsed_href = urlparse(href)
            if not parsed_href.netloc or parsed_href.netloc == base_domain:
                internal_links += 1
            else:
                external_links += 1
                
        if determine_if_cta(a):
            cta_count += 1
            
    # Buttons/Roles CTAs
    for btn in soup.find_all(["button", "div", "span"]):
        if btn.name != "a" and determine_if_cta(btn):
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
        meta_description=meta_description
    )
    
    visible_text = f"Title: {meta_title}\nDescription: {meta_description}\n\n{text}"
    # Truncate visible text to ~50K characters for Gemini limits just in case
    if len(visible_text) > 50000:
        visible_text = visible_text[:50000] + "\n...[TRUNCATED]"
        
    return metrics, visible_text
