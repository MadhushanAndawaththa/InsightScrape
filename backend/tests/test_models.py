"""Tests for the models module — Pydantic model validation."""

import pytest
from models import PageMetrics, SectionAnalysis, SEOAnalysis, Recommendation, PromptLog, AuditResult


class TestPageMetrics:
    def test_default_values(self):
        m = PageMetrics(
            word_count=100,
            headings_count={"h1": 1, "h2": 2, "h3": 0, "h4": 0, "h5": 0, "h6": 0},
            heading_hierarchy=[("H1", "Main")],
            cta_count=2,
            internal_links=5,
            external_links=3,
            image_count=4,
            images_missing_alt_count=1,
            images_decorative_alt_count=0,
            images_missing_alt_pct=25.0,
        )
        assert m.scrape_method == "httpx"
        assert m.content_quality_warning is None
        assert m.meta_title is None

    def test_optional_fields(self):
        m = PageMetrics(
            word_count=100,
            headings_count={"h1": 1, "h2": 0, "h3": 0, "h4": 0, "h5": 0, "h6": 0},
            heading_hierarchy=[],
            cta_count=0,
            internal_links=0,
            external_links=0,
            image_count=0,
            images_missing_alt_count=0,
            images_decorative_alt_count=0,
            images_missing_alt_pct=0.0,
            meta_title="Test",
            meta_description="A description",
            scrape_method="playwright",
            content_quality_warning="Some warning",
        )
        assert m.meta_title == "Test"
        assert m.scrape_method == "playwright"
        assert m.content_quality_warning == "Some warning"

    def test_serialization_roundtrip(self):
        m = PageMetrics(
            word_count=50,
            headings_count={"h1": 1, "h2": 0, "h3": 0, "h4": 0, "h5": 0, "h6": 0},
            heading_hierarchy=[("H1", "Title")],
            cta_count=1,
            internal_links=2,
            external_links=1,
            image_count=3,
            images_missing_alt_count=0,
            images_decorative_alt_count=0,
            images_missing_alt_pct=0.0,
        )
        data = m.model_dump()
        m2 = PageMetrics(**data)
        assert m2.word_count == m.word_count


class TestSectionAnalysis:
    def test_valid_scores(self):
        sa = SectionAnalysis(score=5, findings="Good", evidence="Evidence here")
        assert sa.score == 5

    def test_score_too_low(self):
        with pytest.raises(Exception):
            SectionAnalysis(score=0, findings="Bad", evidence="E")

    def test_score_too_high(self):
        with pytest.raises(Exception):
            SectionAnalysis(score=11, findings="Bad", evidence="E")


class TestSEOAnalysis:
    def _make_section(self, score=5):
        return SectionAnalysis(score=score, findings="Finding", evidence="Evidence")

    def test_valid_analysis(self):
        a = SEOAnalysis(
            structure_score=7, messaging_score=6, cta_score=5,
            content_depth_score=4, ux_score=8, overall_score=6,
            structure_analysis=self._make_section(7),
            messaging_analysis=self._make_section(6),
            cta_analysis=self._make_section(5),
            content_depth_analysis=self._make_section(4),
            ux_analysis=self._make_section(8),
        )
        assert a.overall_score == 6

    def test_score_range_validation(self):
        with pytest.raises(Exception):
            SEOAnalysis(
                structure_score=0, messaging_score=6, cta_score=5,
                content_depth_score=4, ux_score=8, overall_score=6,
                structure_analysis=self._make_section(),
                messaging_analysis=self._make_section(),
                cta_analysis=self._make_section(),
                content_depth_analysis=self._make_section(),
                ux_analysis=self._make_section(),
            )


class TestRecommendation:
    def test_valid_recommendation(self):
        r = Recommendation(
            priority=1,
            category="seo",
            title="Fix Meta Tags",
            description="Missing meta tags",
            grounded_metric="Meta Title: MISSING",
            action="Add meta title tag",
            expected_impact="Better SEO ranking",
        )
        assert r.priority == 1

    def test_invalid_category(self):
        with pytest.raises(Exception):
            Recommendation(
                priority=1,
                category="invalid",
                title="T",
                description="D",
                grounded_metric="M",
                action="A",
                expected_impact="E",
            )

    def test_priority_range(self):
        with pytest.raises(Exception):
            Recommendation(
                priority=0,
                category="seo",
                title="T",
                description="D",
                grounded_metric="M",
                action="A",
                expected_impact="E",
            )


class TestPromptLog:
    def test_default_model(self):
        log = PromptLog(
            stage="Stage 1",
            system_prompt="sys",
            user_prompt="usr",
            raw_response="raw",
            parsed_response="parsed",
            timestamp="2026-03-19T00:00:00Z",
        )
        assert log.model == "gemini-2.5-flash-lite"


class TestAuditResult:
    def test_full_result(self):
        section = SectionAnalysis(score=5, findings="F", evidence="E")
        result = AuditResult(
            url="https://test.com",
            metrics=PageMetrics(
                word_count=100,
                headings_count={"h1": 1, "h2": 0, "h3": 0, "h4": 0, "h5": 0, "h6": 0},
                heading_hierarchy=[],
                cta_count=0, internal_links=0, external_links=0,
                image_count=0, images_missing_alt_count=0,
                images_decorative_alt_count=0, images_missing_alt_pct=0.0,
            ),
            analysis=SEOAnalysis(
                structure_score=5, messaging_score=5, cta_score=5,
                content_depth_score=5, ux_score=5, overall_score=5,
                structure_analysis=section, messaging_analysis=section,
                cta_analysis=section, content_depth_analysis=section,
                ux_analysis=section,
            ),
            recommendations=[],
            prompt_logs=[],
            audit_duration_ms=1000,
        )
        assert result.url == "https://test.com"
        assert result.audit_duration_ms == 1000

    def test_optional_ai_error(self):
        result = AuditResult(
            url="https://test.com",
            metrics=PageMetrics(
                word_count=100,
                headings_count={"h1": 1, "h2": 0, "h3": 0, "h4": 0, "h5": 0, "h6": 0},
                heading_hierarchy=[],
                cta_count=0, internal_links=0, external_links=0,
                image_count=0, images_missing_alt_count=0,
                images_decorative_alt_count=0, images_missing_alt_pct=0.0,
            ),
            prompt_logs=[],
            audit_duration_ms=500,
            ai_error="Rate limited",
        )
        assert result.analysis is None
        assert result.ai_error == "Rate limited"


class TestPageMetricsRichMedia:
    """Tests for the rich media and technical SEO fields."""

    def test_rich_media_defaults(self):
        m = PageMetrics(
            word_count=100,
            headings_count={"h1": 1, "h2": 0, "h3": 0, "h4": 0, "h5": 0, "h6": 0},
            heading_hierarchy=[],
            cta_count=0, internal_links=0, external_links=0,
            image_count=0, images_missing_alt_count=0,
            images_decorative_alt_count=0, images_missing_alt_pct=0.0,
        )
        assert m.svg_count == 0
        assert m.has_video is False
        assert m.has_canvas is False
        assert m.has_css_animations is False
        assert m.has_lottie is False
        assert m.has_webgl_or_3d is False
        assert m.structured_data_types == []
        assert m.has_viewport_meta is False
        assert m.has_canonical is False
        assert m.has_open_graph is False
        assert m.has_twitter_card is False
        assert m.meta_title_length is None
        assert m.meta_description_length is None

    def test_rich_media_set_values(self):
        m = PageMetrics(
            word_count=500,
            headings_count={"h1": 1, "h2": 2, "h3": 0, "h4": 0, "h5": 0, "h6": 0},
            heading_hierarchy=[("H1", "Title")],
            cta_count=3, internal_links=10, external_links=2,
            image_count=5, images_missing_alt_count=1,
            images_decorative_alt_count=0, images_missing_alt_pct=20.0,
            svg_count=4,
            has_video=True,
            has_canvas=True,
            has_css_animations=True,
            has_lottie=True,
            has_webgl_or_3d=True,
            has_viewport_meta=True,
            has_canonical=True,
            has_open_graph=True,
            has_twitter_card=True,
            structured_data_types=["Organization", "WebPage"],
            meta_title_length=55,
            meta_description_length=140,
        )
        assert m.svg_count == 4
        assert m.has_video is True
        assert m.structured_data_types == ["Organization", "WebPage"]
        assert m.meta_title_length == 55

    def test_rich_media_roundtrip(self):
        m = PageMetrics(
            word_count=100,
            headings_count={"h1": 1, "h2": 0, "h3": 0, "h4": 0, "h5": 0, "h6": 0},
            heading_hierarchy=[],
            cta_count=0, internal_links=0, external_links=0,
            image_count=0, images_missing_alt_count=0,
            images_decorative_alt_count=0, images_missing_alt_pct=0.0,
            svg_count=3, has_video=True, has_css_animations=True,
            structured_data_types=["Article"],
        )
        data = m.model_dump()
        m2 = PageMetrics(**data)
        assert m2.svg_count == 3
        assert m2.has_video is True
        assert m2.structured_data_types == ["Article"]
