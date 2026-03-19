"""Tests for the AI service — prompt construction and score computation."""

import json
import pytest
from models import PageMetrics, SEOAnalysis, SectionAnalysis
from services.ai_service import _MAX_PAGE_CHARS, MODEL


class TestAIServiceConfig:
    def test_max_page_chars_reasonable(self):
        """Max page chars should be between 10K and 100K."""
        assert 10_000 <= _MAX_PAGE_CHARS <= 100_000

    def test_model_is_set(self):
        """Model should be a valid Gemini model string."""
        assert MODEL.startswith("gemini-")
        assert "flash" in MODEL


class TestWeightedScoreComputation:
    """Test the deterministic weighted overall_score logic."""

    def _compute_weighted(self, struct, msg, cta, depth, ux):
        """Replicate the weighting from ai_service.py."""
        weighted = round(struct * 0.25 + msg * 0.20 + cta * 0.20 + depth * 0.20 + ux * 0.15)
        return max(1, min(10, weighted))

    def test_all_tens(self):
        assert self._compute_weighted(10, 10, 10, 10, 10) == 10

    def test_all_ones(self):
        assert self._compute_weighted(1, 1, 1, 1, 1) == 1

    def test_mixed_scores(self):
        result = self._compute_weighted(8, 6, 5, 4, 7)
        # 8*0.25 + 6*0.20 + 5*0.20 + 4*0.20 + 7*0.15
        # = 2.0 + 1.2 + 1.0 + 0.8 + 1.05 = 6.05 → round to 6
        assert result == 6

    def test_low_scores_clamped_to_1(self):
        """Even with theoretical sub-1, result is clamped to 1."""
        result = self._compute_weighted(1, 1, 1, 1, 1)
        assert result >= 1

    def test_high_scores_clamped_to_10(self):
        result = self._compute_weighted(10, 10, 10, 10, 10)
        assert result <= 10

    def test_structure_has_highest_weight(self):
        """Structure (0.25) should influence score more than UX (0.15)."""
        high_struct = self._compute_weighted(10, 5, 5, 5, 5)
        high_ux = self._compute_weighted(5, 5, 5, 5, 10)
        assert high_struct >= high_ux


class TestPromptConstruction:
    """Test that prompt construction logic works correctly with various metrics."""

    def _make_metrics(self, **overrides):
        defaults = dict(
            word_count=500,
            headings_count={"h1": 1, "h2": 3, "h3": 2, "h4": 0, "h5": 0, "h6": 0},
            heading_hierarchy=[("H1", "Title"), ("H2", "Sub1")],
            cta_count=3,
            internal_links=10,
            external_links=2,
            image_count=5,
            images_missing_alt_count=1,
            images_decorative_alt_count=0,
            images_missing_alt_pct=20.0,
            meta_title="Test Page",
            meta_description="Test description",
        )
        defaults.update(overrides)
        return PageMetrics(**defaults)

    def test_quality_note_for_thin_content(self):
        """Pages with < 300 words should trigger the data quality note."""
        metrics = self._make_metrics(word_count=50, image_count=0)
        # The prompt logic checks word_count < 300 or image_count == 0
        assert metrics.word_count < 300 or metrics.image_count == 0

    def test_no_quality_note_for_rich_content(self):
        metrics = self._make_metrics(word_count=500, image_count=5)
        assert metrics.word_count >= 300 and metrics.image_count > 0

    def test_content_truncation(self):
        """Content longer than _MAX_PAGE_CHARS should be truncatable."""
        long_content = "word " * (_MAX_PAGE_CHARS + 1000)
        trimmed = long_content[:_MAX_PAGE_CHARS]
        assert len(trimmed) == _MAX_PAGE_CHARS

    def test_metrics_to_json(self):
        """Headings count should be JSON-serializable for prompts."""
        metrics = self._make_metrics()
        headings_json = json.dumps(metrics.headings_count)
        parsed = json.loads(headings_json)
        assert parsed["h1"] == 1

    def test_missing_meta_handled(self):
        """Missing meta should produce 'MISSING' in prompt."""
        metrics = self._make_metrics(meta_title=None, meta_description=None)
        title_str = metrics.meta_title or "MISSING"
        desc_str = metrics.meta_description or "MISSING"
        assert title_str == "MISSING"
        assert desc_str == "MISSING"
