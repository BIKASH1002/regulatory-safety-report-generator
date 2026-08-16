"""Tests for report generation, review, and evaluation."""

from unittest.mock import patch

import pandas as pd

from src.data_loader import validate_dataset
from src.main import generate_reviewed_report
from src.report_generator import SECTION_TITLES, build_report, evaluate_report
from src.review import review_sections


def sample_evidence():
    return {
        "reporting_period": {"start": "2024-12-27", "end": "2025-01-02"},
        "case_summary": {
            "unique_cases": 2,
            "serious_cases": 1,
            "non_serious_cases": 1,
            "serious_percentage": 50.0,
        },
        "demographics": {
            "sex_distribution": {"female": 1, "male": 1},
            "age_distribution": {"18_to_44": 2},
        },
        "countries": {"US": 2},
        "reactions": {
            "top_reactions": {"Dizziness": 1},
            "top_serious_reactions": {"Dizziness": 1},
        },
        "outcomes": {"recovered": 1},
        "expedited_alerts": {"expedited_case_count": 1},
        "monthly_trends": {"2024-12": 1, "2025-01": 1},
        "case_listing": [
            {
                "safetyreportid": "1001",
                "patient_reaction_reactionmeddrapt": "Dizziness",
                "serious": "serious",
                "receivedate": "2024-12-27",
                "occurcountry": "US",
                "patient_reaction_reactionoutcome": "recovered",
            }
        ],
    }


def sample_frame():
    frame = pd.DataFrame(
        {
            "safetyreportid": [1001, 1002],
            "patient_reaction_reactionmeddrapt": ["Dizziness", "Fatigue"],
            "serious": ["serious", "not serious"],
            "receivedate": [20241227, 20250102],
            "patient_patientsex": ["female", "male"],
            "patient_patientonsetage": [40, 50],
            "occurcountry": ["US", "US"],
            "patient_reaction_reactionoutcome": ["recovered", "unknown"],
            "fulfillexpeditecriteria": ["y", "n"],
        }
    )
    validated, error = validate_dataset(frame)
    assert error is None
    return validated


def test_review_only_approves_grounded_sections():
    generated = {"narrative_summary": "Grounded text", "case_analysis": "Flagged text"}
    validations = {
        "narrative_summary": {"status": "PASS"},
        "case_analysis": {"status": "FLAG"},
    }
    reviews = review_sections(
        generated,
        validations,
        input_func=lambda _: "1",
        output_func=lambda _: None,
    )

    assert reviews["narrative_summary"]["status"] == "approved"
    assert reviews["case_analysis"]["status"] == "flagged"


def test_build_report_contains_required_sections_and_controls():
    generated = {name: "Approved grounded narrative." for name in SECTION_TITLES}
    reviews = {name: {"status": "approved"} for name in SECTION_TITLES}

    report, error = build_report(sample_evidence(), generated, reviews)

    assert error is None
    for title in SECTION_TITLES.values():
        assert "## " + title in report
    assert "## History of Actions" in report
    assert "## Case Index / Listing" in report
    assert "### Listing Preview" in report
    assert "SOC-level analysis was not performed" in report
    assert "Expectedness was not assessed" in report


def test_case_listing_defaults_to_ten_row_preview():
    evidence = sample_evidence()
    evidence["case_listing"] = evidence["case_listing"] * 12
    generated = {name: "Approved grounded narrative." for name in SECTION_TITLES}
    reviews = {name: {"status": "approved"} for name in SECTION_TITLES}

    report, error = build_report(evidence, generated, reviews)

    assert error is None
    assert "Showing 10 of 12 reaction-level listing rows." in report
    assert report.count("| 1001 | Dizziness | serious |") == 10

def test_evaluation_reports_missing_and_flagged_sections():
    generated = {"narrative_summary": "text"}
    validation_results = {"narrative_summary": {"status": "FLAG", "unsupported_numbers": [("9", 9)]}}
    reviews = {"narrative_summary": {"status": "flagged"}}

    metrics = evaluate_report(generated, validation_results, reviews)

    assert metrics["sections_generated"] == 1
    assert metrics["sections_flagged"] == 5
    assert metrics["unsupported_numerical_claims"] == 1
    assert len(metrics["missing_required_sections"]) == 4


@patch("src.main.generate_section", return_value=("The dataset was reviewed.", None))
def test_end_to_end_pipeline_builds_report_with_mocked_gemini(mock_generate, tmp_path):
    output_path = tmp_path / "report_output.md"

    report_result, error = generate_reviewed_report(
        sample_frame(),
        client=object(),
        output_path=output_path,
        input_func=lambda _: "1",
        output_func=lambda _: None,
    )

    assert error is None
    assert report_result["success"] is True
    assert report_result["evaluation"]["sections_generated"] == 5
    assert report_result["evaluation"]["sections_approved"] == 5
    assert output_path.is_file()
    assert "# PADER-Style Safety Report" in output_path.read_text(encoding="utf-8")
    assert mock_generate.call_count == 5
