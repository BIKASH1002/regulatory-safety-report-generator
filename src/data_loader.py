"""Load, validate, and profile regulatory safety datasets."""

from pathlib import Path

import pandas as pd


CASE_ID_COLUMN = "safetyreportid"
REACTION_COLUMN = "patient_reaction_reactionmeddrapt"
SERIOUSNESS_COLUMN = "serious"
RECEIVED_DATE_COLUMN = "receivedate"

REQUIRED_COLUMNS = (
    CASE_ID_COLUMN,
    REACTION_COLUMN,
    SERIOUSNESS_COLUMN,
    RECEIVED_DATE_COLUMN,
)

PROFILE_COLUMNS = (
    CASE_ID_COLUMN,
    REACTION_COLUMN,
    SERIOUSNESS_COLUMN,
    RECEIVED_DATE_COLUMN,
    "patient_patientonsetage",
    "patient_patientsex",
    "occurcountry",
    "patient_reaction_reactionoutcome",
    "fulfillexpeditecriteria",
)


def load_dataset(dataset_path):
    """Load an XLSX or CSV dataset."""
    dataset_file = Path(dataset_path).expanduser()
    if not dataset_file.is_file():
        return None, "Dataset file not found: " + str(dataset_file)

    try:
        if dataset_file.suffix.lower() == ".xlsx":
            frame = pd.read_excel(dataset_file, engine="openpyxl")
        elif dataset_file.suffix.lower() == ".csv":
            frame = pd.read_csv(dataset_file)
        else:
            suffix = dataset_file.suffix or "<none>"
            return None, (
                "Unsupported dataset format '" + suffix + "'. Use .xlsx or .csv."
            )
    except (OSError, ValueError) as error:
        message = (
            "Could not read dataset '"
            + str(dataset_file)
            + "'. Check that it is accessible and is a valid XLSX or CSV file. "
            + "Error: "
            + str(error)
        )
        return None, message

    return frame, None


def validate_dataset(frame):
    """Validate required fields and parse received dates."""
    if frame is None or frame.empty:
        return None, "Dataset is empty. Provide at least one safety-report row."

    missing_columns = []
    for column in REQUIRED_COLUMNS:
        if column not in frame.columns:
            missing_columns.append(column)
    if missing_columns:
        return None, "Dataset is missing required column(s): " + ", ".join(
            missing_columns
        )

    if frame[CASE_ID_COLUMN].isna().any():
        return None, "Column 'safetyreportid' contains missing case identifiers."
    if frame[REACTION_COLUMN].isna().all():
        return None, "Column '" + REACTION_COLUMN + "' contains no usable values."
    if frame[SERIOUSNESS_COLUMN].isna().all():
        return None, "Column 'serious' contains no usable values."

    validated_frame = frame.copy()
    try:
        normalized_dates = validated_frame[RECEIVED_DATE_COLUMN].astype("string").str.strip()
        normalized_dates = normalized_dates.str.replace(r"\.0$", "", regex=True)
        parsed = pd.to_datetime(normalized_dates, format="%Y%m%d", errors="coerce")

        unresolved = parsed.isna() & normalized_dates.notna()
        if unresolved.any():
            parsed.loc[unresolved] = pd.to_datetime(
                normalized_dates.loc[unresolved], errors="coerce"
            )
        validated_frame[RECEIVED_DATE_COLUMN] = parsed
    except (TypeError, ValueError) as error:
        return None, "Error parsing received dates: " + str(error)

    invalid_count = int(validated_frame[RECEIVED_DATE_COLUMN].isna().sum())
    if invalid_count:
        message = (
            "Column '"
            + RECEIVED_DATE_COLUMN
            + "' contains "
            + str(invalid_count)
            + " missing or invalid date value(s). Expected YYYYMMDD or a standard date."
        )
        return None, message

    return validated_frame, None


def profile_dataset(frame):
    """Return deterministic dataset quality and coverage metrics."""
    validated_frame, error = validate_dataset(frame)
    if error:
        return None, error

    missing_values = {}
    for column in PROFILE_COLUMNS:
        if column in validated_frame.columns:
            missing_values[column] = int(validated_frame[column].isna().sum())

    profile = {
        "row_count": int(len(validated_frame)),
        "unique_case_count": int(validated_frame[CASE_ID_COLUMN].nunique()),
        "duplicate_case_rows": int(
            validated_frame.duplicated(subset=[CASE_ID_COLUMN]).sum()
        ),
        "reporting_period": {
            "start": validated_frame[RECEIVED_DATE_COLUMN].min().date().isoformat(),
            "end": validated_frame[RECEIVED_DATE_COLUMN].max().date().isoformat(),
        },
        "missing_values": missing_values,
    }
    return profile, None