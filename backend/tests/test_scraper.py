"""Tests for the scraper module — CTA detection, metrics extraction, and content validation."""

import pytest
from services.scraper import (
    determine_if_cta,
    extract_metrics,
    _is_binary_content,
    _is_inside_nav,
)
from bs4 import BeautifulSoup


# ═══════════════════ _is_binary_content ═══════════════════════


class TestIsBinaryContent:
    def test_normal_html_is_not_binary(self):
        html = "<html><body><h1>Hello World</h1></body></html>"
        assert _is_binary_content(html) is False

    def test_binary_content_detected(self):
        # Simulate compressed/garbled content
        binary_str = "\x00\x01\x02\x03\x04" * 100
        assert _is_binary_content(binary_str) is True

    def test_unicode_text_is_not_binary(self):
        text = "Héllo wörld — this is text with àccénts"
        assert _is_binary_content(text) is False

    def test_empty_string(self):
        assert _is_binary_content("") is False


# ═══════════════════ _is_inside_nav ═══════════════════════════


class TestIsInsideNav:
    def test_element_inside_nav_tag(self):
        soup = BeautifulSoup('<nav><a href="/">Home</a></nav>', "html.parser")
        a = soup.find("a")
        assert _is_inside_nav(a) is True

    def test_element_inside_role_navigation(self):
        soup = BeautifulSoup('<div role="navigation"><a href="/">Home</a></div>', "html.parser")
        a = soup.find("a")
        assert _is_inside_nav(a) is True

    def test_element_not_inside_nav(self):
        soup = BeautifulSoup('<main><a href="/">Click</a></main>', "html.parser")
        a = soup.find("a")
        assert _is_inside_nav(a) is False


# ═══════════════════ determine_if_cta ═════════════════════════


class TestDetermineIfCta:
    def test_keyword_match(self):
        soup = BeautifulSoup('<a href="/signup">Sign up now</a>', "html.parser")
        assert determine_if_cta(soup.find("a")) is True

    def test_get_started_keyword(self):
        soup = BeautifulSoup('<a href="/start">Get Started</a>', "html.parser")
        assert determine_if_cta(soup.find("a")) is True

    def test_learn_more_keyword(self):
        soup = BeautifulSoup('<button>Learn More</button>', "html.parser")
        assert determine_if_cta(soup.find("button")) is True

    def test_no_cta_keyword(self):
        soup = BeautifulSoup('<a href="/about">About Us</a>', "html.parser")
        assert determine_if_cta(soup.find("a")) is False

    def test_cta_class(self):
        soup = BeautifulSoup('<a href="/" class="btn-primary">Click</a>', "html.parser")
        assert determine_if_cta(soup.find("a")) is True

    def test_cta_class_inside_nav_rejected(self):
        soup = BeautifulSoup('<nav><a href="/" class="btn">Home</a></nav>', "html.parser")
        assert determine_if_cta(soup.find("a")) is False

    def test_too_short_text_rejected(self):
        soup = BeautifulSoup('<a href="/">X</a>', "html.parser")
        assert determine_if_cta(soup.find("a")) is False

    def test_too_long_text_rejected(self):
        long_text = "A" * 61
        soup = BeautifulSoup(f'<a href="/">{long_text}</a>', "html.parser")
        assert determine_if_cta(soup.find("a")) is False

    def test_role_button(self):
        soup = BeautifulSoup('<div role="button">Submit Form</div>', "html.parser")
        assert determine_if_cta(soup.find("div")) is True

    def test_role_button_inside_nav_rejected(self):
        soup = BeautifulSoup('<nav><div role="button">Menu</div></nav>', "html.parser")
        assert determine_if_cta(soup.find("div")) is False

    def test_free_trial_keyword(self):
        soup = BeautifulSoup('<a href="/trial">Start Free Trial</a>', "html.parser")
        assert determine_if_cta(soup.find("a")) is True


# ═══════════════════ extract_metrics ══════════════════════════


SAMPLE_HTML = """<!DOCTYPE html>
<html>
<head>
    <title>Test Page Title</title>
    <meta name="description" content="A test page for unit testing.">
</head>
<body>
    <nav>
        <a href="/" class="btn">Home</a>
        <a href="/about">About</a>
    </nav>
    <main>
        <h1>Main Heading</h1>
        <p>This is a paragraph with some content for testing purposes. It has multiple words
        to ensure the word count is properly calculated by the extraction function.</p>
        <h2>Subheading One</h2>
        <p>More content under the first subheading with additional text for depth.</p>
        <a href="/contact" class="btn-primary">Contact Us</a>
        <a href="/signup">Get Started</a>
        <h2>Subheading Two</h2>
        <img src="image1.jpg" alt="A test image">
        <img src="image2.jpg">
        <img src="decorative.jpg" alt="">
        <a href="https://external.com">External Link</a>
    </main>
</body>
</html>"""


class TestExtractMetrics:
    def test_basic_extraction(self):
        metrics, visible_text = extract_metrics(SAMPLE_HTML, "https://test.com", "playwright")
        assert metrics.meta_title == "Test Page Title"
        assert metrics.meta_description == "A test page for unit testing."

    def test_heading_counts(self):
        metrics, _ = extract_metrics(SAMPLE_HTML, "https://test.com", "playwright")
        assert metrics.headings_count["h1"] == 1
        assert metrics.headings_count["h2"] == 2
        assert metrics.headings_count["h3"] == 0

    def test_heading_hierarchy_order(self):
        metrics, _ = extract_metrics(SAMPLE_HTML, "https://test.com", "playwright")
        assert len(metrics.heading_hierarchy) == 3
        assert metrics.heading_hierarchy[0][0] == "H1"
        assert metrics.heading_hierarchy[0][1] == "Main Heading"
        assert metrics.heading_hierarchy[1][0] == "H2"

    def test_image_counts(self):
        metrics, _ = extract_metrics(SAMPLE_HTML, "https://test.com", "playwright")
        assert metrics.image_count == 3
        assert metrics.images_missing_alt_count == 1  # image2.jpg
        assert metrics.images_decorative_alt_count == 1  # decorative.jpg

    def test_missing_alt_percentage(self):
        metrics, _ = extract_metrics(SAMPLE_HTML, "https://test.com", "playwright")
        assert abs(metrics.images_missing_alt_pct - 33.33) < 0.1

    def test_link_counts(self):
        metrics, _ = extract_metrics(SAMPLE_HTML, "https://test.com", "playwright")
        # Internal links: /, /about, /contact, /signup = 4
        assert metrics.internal_links >= 3
        # External: external.com = 1
        assert metrics.external_links == 1

    def test_cta_detection_in_full_page(self):
        metrics, _ = extract_metrics(SAMPLE_HTML, "https://test.com", "playwright")
        # CTAs: "Contact Us" (btn-primary class), "Get Started" (keyword)
        # Nav links with .btn class should be excluded
        assert metrics.cta_count >= 2

    def test_nav_ctas_excluded(self):
        """Buttons/links inside nav should NOT count as CTAs."""
        metrics, _ = extract_metrics(SAMPLE_HTML, "https://test.com", "playwright")
        # "Home" inside nav with class="btn" should be excluded
        assert metrics.cta_count <= 3  # Only main CTAs

    def test_word_count_positive(self):
        metrics, _ = extract_metrics(SAMPLE_HTML, "https://test.com", "playwright")
        assert metrics.word_count > 20

    def test_visible_text_contains_content(self):
        _, visible_text = extract_metrics(SAMPLE_HTML, "https://test.com", "playwright")
        assert "Test Page Title" in visible_text
        assert "paragraph" in visible_text

    def test_scrape_method_stored(self):
        metrics, _ = extract_metrics(SAMPLE_HTML, "https://test.com", "playwright")
        assert metrics.scrape_method == "playwright"
        metrics2, _ = extract_metrics(SAMPLE_HTML, "https://test.com", "httpx")
        assert metrics2.scrape_method == "httpx"

    def test_content_quality_warning_httpx_thin(self):
        """httpx with thin content should trigger a quality warning."""
        thin_html = "<html><body><p>Short</p></body></html>"
        metrics, _ = extract_metrics(thin_html, "https://test.com", "httpx")
        assert metrics.content_quality_warning is not None
        assert "JavaScript rendering" in metrics.content_quality_warning

    def test_no_quality_warning_playwright_rich(self):
        """Playwright with rich content should NOT trigger warning."""
        metrics, _ = extract_metrics(SAMPLE_HTML, "https://test.com", "playwright")
        assert metrics.content_quality_warning is None

    def test_missing_meta_title(self):
        html = "<html><body><p>No title here</p></body></html>"
        metrics, _ = extract_metrics(html, "https://test.com", "playwright")
        assert metrics.meta_title is None

    def test_og_title_fallback(self):
        html = '<html><head><meta property="og:title" content="OG Title"></head><body><p>text</p></body></html>'
        metrics, _ = extract_metrics(html, "https://test.com", "playwright")
        assert metrics.meta_title == "OG Title"

    def test_empty_html(self):
        metrics, _ = extract_metrics("", "https://test.com", "playwright")
        assert metrics.word_count == 0
        assert metrics.image_count == 0
        assert metrics.cta_count == 0


# ═══════════════════ Edge Cases ═══════════════════════════════


class TestEdgeCases:
    def test_script_tags_excluded_from_text(self):
        html = '<html><body><script>var x = "hello";</script><p>Visible</p></body></html>'
        metrics, visible_text = extract_metrics(html, "https://test.com", "playwright")
        assert "var x" not in visible_text
        assert "Visible" in visible_text

    def test_style_tags_excluded(self):
        html = '<html><body><style>.cls { color: red }</style><p>Content</p></body></html>'
        _, visible_text = extract_metrics(html, "https://test.com", "playwright")
        assert "color" not in visible_text
        assert "Content" in visible_text

    def test_mailto_and_tel_links_not_counted(self):
        html = """<html><body>
            <a href="mailto:test@test.com">Email</a>
            <a href="tel:+1234567890">Call</a>
            <a href="/page">Internal</a>
        </body></html>"""
        metrics, _ = extract_metrics(html, "https://test.com", "playwright")
        assert metrics.internal_links == 1
        assert metrics.external_links == 0
