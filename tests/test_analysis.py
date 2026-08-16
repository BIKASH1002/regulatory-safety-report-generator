"""Tests for deterministic safety analysis functions."""

from pathlib import Path
import pandas as pd
import pytest

from src.data_loader import load_dataset, validate_dataset
from src.analysis import (
    analyze_cases,
    analyze_demographics,
    analyze_countries,
    analyze_reactions,
    analyze_outcomes,
    analyze_expedited_cases,
    analyze_monthly_trends,
    analyze_reaction_trends,
    describe_monthly_trends,
    generate_case_listing,
    generate_evidence,
)


def sample_frame():
    return pd.DataFrame(
        {
            "safetyreportid": [1001, 1001, 1002, 1003],
            "patient_reaction_reactionmeddrapt": [
                "Dizziness",
                "Fatigue",
                "Hypotension",
                "Dizziness",
            ],
            "serious": ["serious", "serious", "not serious", "serious"],
            "receivedate": pd.to_datetime([
                "2024-12-27",
                "2024-12-27",
                "2025-01-02",
                "2025-01-15",
            ]),
            "occurcountry": ["US", "US", "CA", "US"],
            "patient_reaction_reactionoutcome": ["recovered", "recovered", "recovered", "unknown"],
            "patient_patientsex": ["female", "female", "male", "female"],
            "patient_patientonsetage": [45, 67, 22, 15],
            "fulfillexpeditecriteria": ["y", "n", "n", "y"],
        }
    )


def test_analyze_cases_total_count():
    frame = sample_frame()
    analysis, error = analyze_cases(frame)

    assert error is None
    assert analysis is not None
    assert analysis["unique_cases"] == 3
    assert analysis["serious_cases"] == 2
    assert analysis["non_serious_cases"] == 1


def test_analyze_cases_serious_percentage():
    frame = sample_frame()
    analysis, error = analyze_cases(frame)

    assert error is None
    assert analysis["serious_percentage"] == 66.7


def test_analyze_cases_duplicate_rows():
    frame = sample_frame()
    analysis, error = analyze_cases(frame)

    assert error is None
    assert analysis["duplicate_rows"] == 1


def test_analyze_demographics_sex_distribution():
    frame = sample_frame()
    demographics, error = analyze_demographics(frame)

    assert error is None
    assert demographics is not None
    assert "female" in demographics["sex_distribution"]
    assert demographics["sex_distribution"]["female"] == 2


def test_analyze_demographics_age_buckets():
    frame = sample_frame()
    demographics, error = analyze_demographics(frame)

    assert error is None
    assert demographics is not None
    assert "age_distribution" in demographics
    assert demographics["age_distribution"]["0_to_17"] == 1
    assert demographics["age_distribution"]["18_to_44"] == 1
    assert demographics["age_distribution"]["45_to_64"] == 1
    assert demographics["age_distribution"]["65_plus"] == 0


def test_analyze_countries():
    frame = sample_frame()
    countries, error = analyze_countries(frame)

    assert error is None
    assert countries is not None
    assert countries["US"] == 2
    assert countries["CA"] == 1


def test_analyze_reactions():
    frame = sample_frame()
    reactions, error = analyze_reactions(frame)

    assert error is None
    assert reactions is not None
    assert "Dizziness" in reactions["top_reactions"]
    assert reactions["top_reactions"]["Dizziness"] == 2


def test_analyze_outcomes():
    frame = sample_frame()
    outcomes, error = analyze_outcomes(frame)

    assert error is None
    assert outcomes is not None
    assert outcomes["recovered"] == 3
    assert outcomes["unknown"] == 1


def test_analyze_outcomes_splits_comma_separated_values():
    frame = sample_frame()
    frame.loc[0, "patient_reaction_reactionoutcome"] = "recovered,unknown"

    outcomes, error = analyze_outcomes(frame)

    assert error is None
    assert outcomes["recovered"] == 3
    assert outcomes["unknown"] == 2

def test_analyze_expedited_cases():
    frame = sample_frame()
    expedited, error = analyze_expedited_cases(frame)

    assert error is None
    assert expedited is not None
    assert expedited["expedited_case_count"] == 2


def test_analyze_monthly_trends():
    frame = sample_frame()
    trends, error = analyze_monthly_trends(frame)

    assert error is None
    assert trends is not None
    assert "2024-12" in trends
    assert trends["2024-12"] == 1
    assert "2025-01" in trends
    assert trends["2025-01"] == 2


def test_analyze_reaction_trends():
    trends, error = analyze_reaction_trends(sample_frame())

    assert error is None
    assert trends["2024-12"] == {"Dizziness": 1, "Fatigue": 1}
    assert trends["2025-01"]["Dizziness"] == 1

def test_describe_monthly_trends_includes_large_changes():
    observations = describe_monthly_trends({
        "2025-01": 10,
        "2025-02": 35,
        "2025-03": 30,
    })

    assert "Case volume increased from 10 in 2025-01 to 35 in 2025-02 (change=25)" in observations
    assert len(observations) == 3

def test_generate_case_listing():
    frame = sample_frame()
    listing, error = generate_case_listing(frame)

    assert error is None
    assert listing is not None
    assert len(listing) == 4
    assert listing[0]["safetyreportid"] == "1001"
    assert listing[0]["serious"] == "serious"


def test_generate_evidence():
    frame = sample_frame()
    evidence, error = generate_evidence(frame)

    assert error is None
    assert evidence is not None
    assert "case_summary" in evidence
    assert "demographics" in evidence
    assert "countries" in evidence
    assert "reactions" in evidence
    assert "outcomes" in evidence
    assert "expedited_alerts" in evidence
    assert "monthly_trends" in evidence
    assert "reaction_trends" in evidence
    assert "trend_observations" in evidence


def test_analyze_with_empty_frame():
    empty = sample_frame().iloc[0:0]

    analysis, error = analyze_cases(empty)
    assert error is not None


def test_analyze_cases_with_real_dataset(tmp_path):
    path = tmp_path / "test.xlsx"
    sample_frame().to_excel(path, index=False)

    loaded, load_error = load_dataset(path)
    assert load_error is None

    validated, val_error = validate_dataset(loaded)
    assert val_error is None

    evidence, error = generate_evidence(validated)
    assert error is None
    assert evidence["case_summary"]["unique_cases"] == 3
