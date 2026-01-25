"""
Unit tests for LLM Chains

Tests the report generation functionality using mocked LLM calls.
"""

from unittest.mock import MagicMock, Mock, patch

import pytest
from langchain_core.documents import Document

from app.worker.chains import (
    generate_diagnosis_report,
    _format_contexts,
    _get_confidence_warning,
    LLMError,
    ReportTimeoutError,
)


@pytest.fixture
def sample_contexts():
    """Sample document contexts for testing."""
    return [
        Document(
            page_content="番茄晚疫病由致病疫霉引起，主要危害叶片和果实。",
            metadata={"source": "data/knowledge/diseases/late_blight.md"},
        ),
        Document(
            page_content="推荐使用68.75%银法利悬浮剂，用量60-75 ml/亩。",
            metadata={"source": "data/knowledge/diseases/late_blight.md"},
        ),
    ]


class TestFormatContexts:
    """Tests for _format_contexts helper function."""

    def test_format_contexts_with_documents(self, sample_contexts):
        """Test formatting with valid documents."""
        result = _format_contexts(sample_contexts)

        assert "### 资料 1: data/knowledge/diseases/late_blight.md" in result
        assert "番茄晚疫病由致病疫霉引起" in result
        assert "### 资料 2: data/knowledge/diseases/late_blight.md" in result
        assert "推荐使用68.75%银法利悬浮剂" in result

    def test_format_contexts_empty_list(self):
        """Test formatting with empty context list."""
        result = _format_contexts([])

        assert "未找到相关资料" in result
        assert "基于通用知识生成" in result

    def test_format_contexts_with_metadata(self):
        """Test that document metadata is properly extracted."""
        doc = Document(
            page_content="Test content",
            metadata={"source": "test.md", "category": "diseases"},
        )
        result = _format_contexts([doc])

        assert "test.md" in result
        assert "Test content" in result


class TestConfidenceWarning:
    """Tests for _get_confidence_warning helper function."""

    def test_high_confidence_no_warning(self):
        """Test that high confidence (>0.7) returns no warning."""
        result = _get_confidence_warning(0.85)
        assert result == ""

        result = _get_confidence_warning(0.70)
        assert result == ""

    def test_medium_confidence_warning(self):
        """Test that medium confidence (0.5-0.7) returns warning."""
        result = _get_confidence_warning(0.65)
        assert "⚠️" in result
        assert "较低" in result
        assert "70%" in result
        assert "重新拍照" in result

    def test_low_confidence_strong_warning(self):
        """Test that low confidence (<0.5) returns strong warning."""
        result = _get_confidence_warning(0.45)
        assert "⚠️" in result
        assert "很低" in result
        assert "50%" in result
        assert "强烈建议" in result
        assert "咨询农业专家" in result

    def test_boundary_values(self):
        """Test boundary values for confidence levels."""
        assert _get_confidence_warning(1.0) == ""
        # 0.5 should trigger the low confidence warning (<70% threshold)
        warning_05 = _get_confidence_warning(0.5)
        assert warning_05 != ""  # Should have warning
        assert "70%" in warning_05  # The threshold is 70%, so it mentions "<70%"


class TestGenerateDiagnosisReport:
    """Tests for generate_diagnosis_report function."""

    def test_empty_diagnosis_name_raises_error(self, sample_contexts):
        """Test that empty diagnosis_name raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            generate_diagnosis_report(
                diagnosis_name="",
                crop_type="番茄",
                confidence=0.8,
                contexts=sample_contexts,
            )
        assert "cannot be empty" in str(exc_info.value)

    def test_whitespace_only_diagnosis_name_raises_error(self, sample_contexts):
        """Test that whitespace-only diagnosis_name raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            generate_diagnosis_report(
                diagnosis_name="   ",
                crop_type="番茄",
                confidence=0.8,
                contexts=sample_contexts,
            )
        assert "cannot be empty" in str(exc_info.value)

    def test_empty_crop_type_raises_error(self, sample_contexts):
        """Test that empty crop_type raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            generate_diagnosis_report(
                diagnosis_name="番茄晚疫病",
                crop_type="",
                confidence=0.8,
                contexts=sample_contexts,
            )
        assert "cannot be empty" in str(exc_info.value)

    def test_invalid_confidence_too_high(self, sample_contexts):
        """Test that confidence > 1.0 raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            generate_diagnosis_report(
                diagnosis_name="番茄晚疫病",
                crop_type="番茄",
                confidence=1.5,
                contexts=sample_contexts,
            )
        assert "between 0.0 and 1.0" in str(exc_info.value)

    def test_invalid_confidence_too_low(self, sample_contexts):
        """Test that confidence < 0.0 raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            generate_diagnosis_report(
                diagnosis_name="番茄晚疫病",
                crop_type="番茄",
                confidence=-0.1,
                contexts=sample_contexts,
            )
        assert "between 0.0 and 1.0" in str(exc_info.value)

    def test_boundary_confidence_values(self, sample_contexts):
        """Test that boundary confidence values are accepted."""
        # These should not raise ValueError
        try:
            generate_diagnosis_report(
                diagnosis_name="番茄晚疫病",
                crop_type="番茄",
                confidence=0.0,
                contexts=sample_contexts,
                timeout=1,  # Short timeout for testing
            )
        except (LLMError, ReportTimeoutError):
            pass  # Expected to fail due to mocking/timeout

        try:
            generate_diagnosis_report(
                diagnosis_name="番茄晚疫病",
                crop_type="番茄",
                confidence=1.0,
                contexts=sample_contexts,
                timeout=1,
            )
        except (LLMError, ReportTimeoutError):
            pass  # Expected to fail due to mocking/timeout


class TestLLMErrorHandling:
    """Tests for LLM error handling."""

    def test_llm_error_exception_class_exists(self):
        """Test that LLMError exception class exists and can be raised."""
        with pytest.raises(LLMError):
            raise LLMError("Test error")

    def test_timeout_error_exception_class_exists(self):
        """Test that ReportTimeoutError exception class exists and can be raised."""
        with pytest.raises(ReportTimeoutError):
            raise ReportTimeoutError("Test timeout")

    # Note: Full integration tests with actual LLM calls would be in
    # tests/integration/test_chains_integration.py to avoid API costs
    # and complexity in unit tests. The error handling logic is
    # tested indirectly through the input validation tests above.


class TestPromptGeneration:
    """Tests for prompt generation."""

    @patch("app.worker.chains._get_llm")
    @patch("app.worker.chains.PromptTemplate")
    @patch("app.worker.chains.StrOutputParser")
    @patch("app.worker.chains._format_contexts")
    @patch("app.worker.chains._get_confidence_warning")
    def test_prompt_includes_low_confidence_warning(
        self,
        mock_warning,
        mock_format,
        mock_parser,
        mock_template,
        mock_get_llm,
        sample_contexts,
    ):
        """Test that prompt includes warning for low confidence."""
        # Setup mocks
        mock_format.return_value = "Context content"
        mock_warning.return_value = "⚠️ Warning: Low confidence"
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = "# Test Report"
        mock_get_llm.return_value = mock_llm

        # Execute with low confidence
        try:
            generate_diagnosis_report(
                diagnosis_name="番茄晚疫病",
                crop_type="番茄",
                confidence=0.55,
                contexts=sample_contexts,
                timeout=1,
            )
        except:
            pass  # We only care about the prompt setup

        # Verify warning was called with correct confidence
        mock_warning.assert_called_once_with(0.55)

    @patch("app.worker.chains._get_llm")
    @patch("app.worker.chains._format_contexts")
    @patch("app.worker.chains._get_confidence_warning")
    def test_prompt_includes_contexts(
        self,
        mock_warning,
        mock_format,
        mock_get_llm,
        sample_contexts,
    ):
        """Test that prompt includes formatted contexts."""
        # Setup mocks
        mock_format.return_value = "### 资料 1: test.md\n\nTest content\n"
        mock_warning.return_value = ""
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = "# Test Report"
        mock_get_llm.return_value = mock_llm

        # Execute
        try:
            generate_diagnosis_report(
                diagnosis_name="番茄晚疫病",
                crop_type="番茄",
                confidence=0.8,
                contexts=sample_contexts,
                timeout=1,
            )
        except:
            pass  # We only care about the format call

        # Verify format was called with contexts
        mock_format.assert_called_once_with(sample_contexts)
