from pathlib import Path

import pandas as pd
import pytest

from src.data_loader import load_dataset, profile_dataset, validate_dataset


def sample_frame():
    return pd.DataFrame(
        {
            "safetyreportid": [1001, 1001, 1002],
            "patient_reaction_reactionmeddrapt": [
                "Dizziness",
                "Fatigue",
                "Hypotension",
            ],
            "serious": ["serious", "serious", "not serious"],
            "receivedate": [20241227, 20241227, 20250102],
            "patient_patientsex": ["female", "female", None],
        }
    )


def test_load_xlsx_successfully(tmp_path):
    path = tmp_path / "sample.xlsx"
    sample_frame().to_excel(path, index=False)

    loaded, error = load_dataset(path)

    assert error is None
    assert loaded is not None
    assert len(loaded) == 3
    validated, val_error = validate_dataset(loaded)
    assert val_error is None
    assert pd.api.types.is_datetime64_any_dtype(validated["receivedate"])


def test_load_csv_successfully(tmp_path):
    path = tmp_path / "sample.csv"
    sample_frame().to_csv(path, index=False)

    loaded, error = load_dataset(path)

    assert error is None
    assert loaded is not None
    assert len(loaded) == 3


def test_empty_dataset_is_rejected():
    empty = sample_frame().iloc[0:0]

    validated, error = validate_dataset(empty)

    assert error is not None
    assert "Dataset is empty" in error
    assert validated is None


def test_missing_required_column_is_rejected():
    frame = sample_frame().drop(columns=["serious"])

    validated, error = validate_dataset(frame)

    assert error is not None
    assert "serious" in error or "missing required column" in error
    assert validated is None


def test_invalid_received_date_is_rejected():
    frame = sample_frame()
    frame["receivedate"] = frame["receivedate"].astype(object)
    frame.loc[0, "receivedate"] = "not-a-date"

    validated, error = validate_dataset(frame)

    assert error is not None
    assert "invalid date" in error or "date" in error.lower()
    assert validated is None


def test_profile_distinguishes_rows_from_unique_cases():
    frame = sample_frame()
    validated, val_error = validate_dataset(frame)
    
    assert val_error is None
    
    profile, error = profile_dataset(validated)

    assert error is None
    assert profile is not None
    assert profile["row_count"] == 3
    assert profile["unique_case_count"] == 2
    assert profile["duplicate_case_rows"] == 1
    assert profile["reporting_period"] == {
        "start": "2024-12-27",
        "end": "2025-01-02",
    }


def test_missing_file_has_clear_error(tmp_path):
    loaded, error = load_dataset(tmp_path / "missing.xlsx")

    assert error is not None
    assert "Dataset file not found" in error or "not found" in error
    assert loaded is None
