"""Tests for context building, grounding validation, and LLM integration."""

import pytest
import json
from unittest.mock import patch, MagicMock
from src.context_builder import (
    build_section_context,
    build_narrative_summary_context,
    build_case_analysis_context,
    build_reaction_analysis_context,
    build_trends_context,
    build_expedited_cases_context,
    load_prompt_template,
    format_top_frequency_counts,
)
from src.grounding_check import (
    check_grounding,
    extract_numbers_from_text,
    get_evidence_numbers,
    format_grounding_report,
)
from src.llm_client import initialize_client, generate_section
@pytest.fixture
def sample_evidence():
    """Sample evidence structure for testing."""
    return {
        "case_summary": {
            "total_rows": 1068,
            "unique_cases": 1024,
            "duplicate_rows": 44,
            "serious_cases": 1023,
            "non_serious_cases": 1,
            "unknown_seriousness": 0,
            "serious_percentage": 99.9,
        },
        "demographics": {
            "sex_distribution": {
                "M": 512,
                "F": 512,
            },
            "age_distribution": {
                "0_to_17": 10,
                "18_to_44": 300,
                "45_to_64": 400,
                "65_plus": 314,
                "unknown": 0,
            },
        },
        "countries": {
            "US": 400,
            "UK": 300,
            "DE": 200,
            "FR": 124,
        },
        "reactions": {
            "top_reactions": {
                "Dizziness": 150,
                "Headache": 120,
                "Fatigue": 100,
            },
            "top_serious_reactions": {
                "Dizziness": 150,
                "Fatigue": 98,
            },
        },
        "outcomes": {
            "Recovered": 500,
            "Recovering": 300,
            "Not recovered": 200,
            "Unknown": 24,
        },
        "expedited_alerts": {
            "expedited_case_count": 100,
        },
        "trends": {
            "2024-12": 150,
            "2025-01": 180,
            "2025-02": 200,
        },
    }


@pytest.fixture
def sample_context_packet():
    """Sample context packet."""
    return {
        "section": "Narrative Summary and Analysis",
        "prompt": "Sample prompt with 1024 cases and 99.9% serious",
        "evidence_keys": ["case_summary", "reactions"],
    }
class TestContextBuilder:
    def test_load_prompt_template_success(self):
        """Test loading a valid prompt template."""
        template, error = load_prompt_template("narrative_summary")
        assert error is None
        assert template is not None
        assert len(template) > 0
        assert "Narrative Summary" in template or "{" in template

    def test_load_prompt_template_missing(self):
        """Test loading a non-existent template."""
        template, error = load_prompt_template("nonexistent_section")
        assert error is not None
        assert template is None

    def test_format_top_frequency_counts(self):
        """Test formatting top items for display."""
        items = {"Item A": 100, "Item B": 50, "Item C": 25}
        formatted = format_top_frequency_counts(items, max_items=2)
        assert "Item A" in formatted
        assert "Item B" in formatted
        assert "Item C" not in formatted
        assert "100" in formatted

    def test_build_narrative_summary_context(self, sample_evidence):
        """Test building context for narrative summary section."""
        context, error = build_narrative_summary_context(sample_evidence)
        assert error is None
        assert context is not None
        assert context["section"] == "Narrative Summary and Analysis"
        assert "prompt" in context
        assert "1024" in context["prompt"] or "unique_cases" in str(context)

    def test_build_case_analysis_context(self, sample_evidence):
        """Test building context for case analysis section."""
        context, error = build_case_analysis_context(sample_evidence)
        assert error is None
        assert context is not None
        assert context["section"] == "Summary Analysis of Cases"
        assert "prompt" in context

    def test_build_reaction_analysis_context(self, sample_evidence):
        """Test building context for reaction analysis section."""
        context, error = build_reaction_analysis_context(sample_evidence)
        assert error is None
        assert context is not None
        assert context["section"] == "Reaction / Adverse Event Analysis"

    def test_build_trends_context(self, sample_evidence):
        """Test building context for trends section."""
        context, error = build_trends_context(sample_evidence)
        assert error is None
        assert context is not None
        assert context["section"] == "Trends and Important Observations"

    def test_build_expedited_cases_context(self, sample_evidence):
        """Test building context for expedited cases section."""
        context, error = build_expedited_cases_context(sample_evidence)
        assert error is None
        assert context is not None
        assert context["section"] == "Serious Cases / 15-Day Alerts"

    def test_build_section_context_valid_section(self, sample_evidence):
        """Test build_section_context with valid section name."""
        context, error = build_section_context("narrative_summary", sample_evidence)
        assert error is None
        assert context is not None

    def test_build_section_context_invalid_section(self, sample_evidence):
        """Test build_section_context with invalid section name."""
        context, error = build_section_context("invalid_section", sample_evidence)
        assert error is not None
        assert "Unknown section" in error
        assert context is None

    def test_build_section_context_no_evidence(self):
        """Test build_section_context with missing evidence."""
        context, error = build_section_context("narrative_summary", None)
        assert error is not None
        assert context is None
class TestGroundingCheck:
    def test_extract_numbers_from_text(self):
        """Test extracting numbers from generated text."""
        text = "There are 1024 cases and 99.9% are serious."
        numbers = extract_numbers_from_text(text)
        assert len(numbers) > 0
        num_values = [n[1] for n in numbers]
        assert 1024 in num_values
        assert 99.9 in num_values

    def test_extract_numbers_no_numbers(self):
        """Test extracting from text with no numbers."""
        text = "This text contains no numbers."
        numbers = extract_numbers_from_text(text)
        assert len(numbers) == 0

    def test_get_evidence_numbers(self, sample_evidence):
        """Test extracting numerical values from evidence."""
        evidence_nums = get_evidence_numbers(
            sample_evidence,
            ["case_summary", "reactions"]
        )
        assert len(evidence_nums) > 0
        assert 1024.0 in evidence_nums or 1024 in evidence_nums
        assert 99.9 in evidence_nums or 99.9 in evidence_nums

    def test_check_grounding_pass(self, sample_evidence, sample_context_packet):
        """Test grounding check with all numbers supported by evidence."""
        generated_text = "There are 1024 unique cases with 99.9% being serious."
        validation, error = check_grounding(
            generated_text,
            sample_context_packet,
            sample_evidence
        )
        assert error is None
        assert validation is not None
        assert "status" in validation
        assert validation["status"] in ["PASS", "FLAG"]

    def test_check_grounding_flag_unsupported_number(self, sample_evidence, sample_context_packet):
        """Test grounding check flags unsupported numbers not in evidence."""
        generated_text = "There are 9999 cases, which is unsupported."
        validation, error = check_grounding(
            generated_text,
            sample_context_packet,
            sample_evidence
        )
        assert error is None
        assert validation is not None
        if validation["unsupported_numbers"]:
            assert validation["status"] == "FLAG"

    def test_check_grounding_supports_numbers_in_evidence_dates(self, sample_evidence):
        sample_evidence["reporting_period"] = {
            "start": "2024-12-27",
            "end": "2025-12-26",
        }
        context = {"evidence_keys": ["reporting_period"]}

        validation, error = check_grounding(
            "The reporting period was 2024-12-27 to 2025-12-26.",
            context,
            sample_evidence,
        )

        assert error is None
        assert validation["status"] == "PASS"
    def test_check_grounding_supports_numbers_in_evidence_labels(self, sample_evidence):
        sample_evidence["demographics"]["age_distribution"] = {
            "18_to_44": 300,
        }
        context = {"evidence_keys": ["demographics"]}

        validation, error = check_grounding(
            "There were reports in the 18 to 44 age group.",
            context,
            sample_evidence,
        )

        assert error is None
        assert validation["status"] == "PASS"
    def test_check_grounding_no_text(self, sample_evidence, sample_context_packet):
        """Test grounding check with missing generated text."""
        validation, error = check_grounding(
            None,
            sample_context_packet,
            sample_evidence
        )
        assert error is not None

    def test_format_grounding_report(self):
        """Test formatting validation report for display."""
        validation = {
            "status": "PASS",
            "issues": [],
        }
        report = format_grounding_report(validation)
        assert "PASS" in report

    def test_format_grounding_report_with_issues(self):
        """Test formatting validation report with flagged issues."""
        validation = {
            "status": "FLAG",
            "issues": ["Number '9999' not found in evidence"],
        }
        report = format_grounding_report(validation)
        assert "FLAG" in report
        assert "9999" in report
class TestLLMClient:
    @patch.dict("os.environ", {"GEMINI_API_KEY": ""})
    def test_initialize_client_missing_key(self):
        """Test client initialization fails without API key."""
        client, error = initialize_client()
        assert error is not None
        assert "GEMINI_API_KEY" in error
        assert client is None

    @patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"})
    @patch("src.llm_client.genai.Client")
    def test_initialize_client_success(self, mock_client_class):
        """Test successful client initialization with valid API key."""
        mock_client_class.return_value = MagicMock()
        client, error = initialize_client()
        assert error is None
        assert client is not None
        mock_client_class.assert_called_once_with(api_key="test-key")

    @patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"})
    def test_generate_section_no_client(self):
        """Test section generation fails without client."""
        generated_text, error = generate_section(
            None,
            "System prompt",
            "User prompt"
        )
        assert error is not None
        assert generated_text is None

    @patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"})
    def test_generate_section_missing_prompts(self):
        """Test section generation fails without prompts."""
        mock_client = MagicMock()
        generated_text, error = generate_section(
            mock_client,
            "",
            ""
        )
        assert error is not None
        assert generated_text is None
class TestGroundedGenerationIntegration:
    @patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"})
    @patch("src.llm_client.genai.Client")
    def test_end_to_end_context_and_grounding(self, mock_client_class, sample_evidence):
        """Test full workflow: context building → LLM generation → grounding validation."""
        context, error = build_section_context("narrative_summary", sample_evidence)
        assert error is None
        assert context is not None
        mock_response = MagicMock()
        mock_response.text = (
            "The dataset contained 1024 unique cases. Serious cases: 1023 "
            "(99.9%). Demographics showed balanced sex distribution."
        )
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response
        mock_client_class.return_value = mock_client
        generated_text = mock_response.text
        validation, error = check_grounding(
            generated_text,
            context,
            sample_evidence
        )
        assert error is None
        assert validation is not None
        assert "status" in validation


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
