"""Deterministic safety-data analysis and evidence generation."""

import pandas as pd


CASE_ID_COLUMN = "safetyreportid"
REACTION_COLUMN = "patient_reaction_reactionmeddrapt"
RECEIVED_DATE_COLUMN = "receivedate"


def _count_delimited_values(value_series, limit=None):
    """Count individual comma-separated values in a pandas Series."""
    counts = {}
    for value in value_series.dropna():
        for delimited_value in str(value).split(","):
            delimited_value = delimited_value.strip()
            if delimited_value:
                counts[delimited_value] = counts.get(delimited_value, 0) + 1

    ordered_counts = sorted(
        counts.items(),
        key=lambda count_pair: count_pair[1],
        reverse=True,
    )
    if limit is not None:
        ordered_counts = ordered_counts[:limit]
    return dict(ordered_counts)


def _get_unique_case_rows(frame):
    """Return one row per safety report for case-level calculations."""
    return frame.drop_duplicates(subset=[CASE_ID_COLUMN])


def analyze_cases(frame):
    """Calculate case-level counts and seriousness metrics."""
    if frame is None or frame.empty:
        return None, "Frame is empty or None"

    try:
        case_frame = _get_unique_case_rows(frame)
        unique_cases = int(len(case_frame))
        serious_values = case_frame["serious"].fillna("unknown").astype(str).str.lower()
        serious_cases = int((serious_values == "serious").sum())
        non_serious_cases = int((serious_values == "not serious").sum())

        analysis = {
            "total_rows": int(len(frame)),
            "unique_cases": unique_cases,
            "duplicate_rows": int(len(frame) - unique_cases),
            "serious_cases": serious_cases,
            "non_serious_cases": non_serious_cases,
            "unknown_seriousness": unique_cases - serious_cases - non_serious_cases,
            "serious_percentage": round((serious_cases / unique_cases) * 100, 1),
        }
    except Exception as error:
        return None, "Error analyzing cases: " + str(error)

    return analysis, None


def analyze_demographics(frame):
    """Calculate case-level sex and age distributions."""
    if frame is None or frame.empty:
        return None, "Frame is empty or None"

    try:
        case_frame = _get_unique_case_rows(frame)
        sex_distribution = {}
        age_distribution = {}

        if "patient_patientsex" in case_frame.columns:
            counts = case_frame["patient_patientsex"].value_counts()
            for sex, count in counts.items():
                sex_distribution[str(sex)] = int(count)

        if "patient_patientonsetage" in case_frame.columns:
            ages = pd.to_numeric(case_frame["patient_patientonsetage"], errors="coerce")
            age_distribution = {
                "0_to_17": int(((ages >= 0) & (ages < 18)).sum()),
                "18_to_44": int(((ages >= 18) & (ages < 45)).sum()),
                "45_to_64": int(((ages >= 45) & (ages < 65)).sum()),
                "65_plus": int((ages >= 65).sum()),
                "unknown": int(ages.isna().sum()),
            }

        return {
            "sex_distribution": sex_distribution,
            "age_distribution": age_distribution,
        }, None
    except Exception as error:
        return None, "Error analyzing demographics: " + str(error)


def analyze_countries(frame):
    """Calculate the case-level occurrence-country distribution."""
    if frame is None or frame.empty:
        return None, "Frame is empty or None"

    try:
        countries = {}
        case_frame = _get_unique_case_rows(frame)
        if "occurcountry" in case_frame.columns:
            for country, count in case_frame["occurcountry"].value_counts().items():
                countries[str(country)] = int(count)
        return countries, None
    except Exception as error:
        return None, "Error analyzing countries: " + str(error)


def analyze_reactions(frame):
    """Calculate reaction-level frequencies."""
    if frame is None or frame.empty:
        return None, "Frame is empty or None"

    try:
        all_reactions = _count_delimited_values(frame[REACTION_COLUMN])
        top_reactions = dict(list(all_reactions.items())[:20])
        serious_rows = frame[
            frame["serious"].fillna("").astype(str).str.lower() == "serious"
        ]
        top_serious_reactions = _count_delimited_values(
            serious_rows[REACTION_COLUMN], limit=20
        )
        return {
            "top_reactions": top_reactions,
            "unique_reaction_count": len(all_reactions),
            "top_serious_reactions": top_serious_reactions,
        }, None
    except Exception as error:
        return None, "Error analyzing reactions: " + str(error)


def analyze_outcomes(frame):
    """Calculate reaction-level outcome frequencies."""
    if frame is None or frame.empty:
        return None, "Frame is empty or None"

    try:
        if "patient_reaction_reactionoutcome" not in frame.columns:
            return {}, None
        outcomes = _count_delimited_values(frame["patient_reaction_reactionoutcome"])
        return outcomes, None
    except Exception as error:
        return None, "Error analyzing outcomes: " + str(error)


def analyze_expedited_cases(frame):
    """Count unique cases marked for expedited reporting."""
    if frame is None or frame.empty:
        return None, "Frame is empty or None"

    try:
        expedited_count = 0
        case_frame = _get_unique_case_rows(frame)
        if "fulfillexpeditecriteria" in case_frame.columns:
            expedite_values = case_frame["fulfillexpeditecriteria"].fillna("").astype(str).str.lower()
            expedited_count = int(expedite_values.isin(["y", "yes"]).sum())
        return {"expedited_case_count": expedited_count}, None
    except Exception as error:
        return None, "Error analyzing expedited cases: " + str(error)


def _add_month_column(frame):
    dated = frame.copy()
    if not pd.api.types.is_datetime64_any_dtype(dated[RECEIVED_DATE_COLUMN]):
        dated[RECEIVED_DATE_COLUMN] = pd.to_datetime(dated[RECEIVED_DATE_COLUMN], errors="coerce")
    dated["year_month"] = dated[RECEIVED_DATE_COLUMN].dt.strftime("%Y-%m")
    return dated


def analyze_monthly_trends(frame):
    """Calculate monthly unique-case counts."""
    if frame is None or frame.empty:
        return None, "Frame is empty or None"

    try:
        case_frame = _add_month_column(_get_unique_case_rows(frame))
        monthly_counts = {}
        counts = case_frame["year_month"].value_counts().sort_index()
        for month, count in counts.items():
            monthly_counts[str(month)] = int(count)
        return monthly_counts, None
    except Exception as error:
        return None, "Error analyzing monthly trends: " + str(error)


def analyze_reaction_trends(frame):
    """Return the five most frequent reactions for each reporting month."""
    if frame is None or frame.empty:
        return None, "Frame is empty or None"

    try:
        dated = _add_month_column(frame)
        trends = {}
        months = sorted(dated["year_month"].dropna().unique())
        for month in months:
            month_rows = dated[dated["year_month"] == month]
            trends[str(month)] = _count_delimited_values(
                month_rows[REACTION_COLUMN], limit=5
            )
        return trends, None
    except Exception as error:
        return None, "Error analyzing reaction trends: " + str(error)


def describe_monthly_trends(monthly_counts):
    """Create conservative observations from monthly case counts."""
    if not monthly_counts:
        return []

    peak_month = max(monthly_counts, key=monthly_counts.get)
    low_month = min(monthly_counts, key=monthly_counts.get)
    observations = [
        "Highest case volume: " + peak_month + " (n=" + str(monthly_counts[peak_month]) + ")",
        "Lowest case volume: " + low_month + " (n=" + str(monthly_counts[low_month]) + ")",
    ]

    months = sorted(monthly_counts)
    for index in range(1, len(months)):
        previous_month = months[index - 1]
        current_month = months[index]
        previous_count = monthly_counts[previous_month]
        current_count = monthly_counts[current_month]
        change = current_count - previous_count
        if abs(change) < 20:
            continue

        direction = "increased" if change > 0 else "decreased"
        observation = (
            "Case volume "
            + direction
            + " from "
            + str(previous_count)
            + " in "
            + previous_month
            + " to "
            + str(current_count)
            + " in "
            + current_month
            + " (change="
            + str(abs(change))
            + ")"
        )
        observations.append(observation)

    return observations


def generate_case_listing(frame):
    """Create a JSON-serializable reaction-level case listing."""
    if frame is None or frame.empty:
        return None, "Frame is empty or None"

    columns = [
        CASE_ID_COLUMN,
        REACTION_COLUMN,
        "serious",
        RECEIVED_DATE_COLUMN,
        "occurcountry",
        "patient_reaction_reactionoutcome",
    ]
    available_columns = [column for column in columns if column in frame.columns]

    try:
        case_listing = []
        for _, row in frame.iterrows():
            record = {}
            for column in available_columns:
                value = row[column]
                if pd.isna(value):
                    record[column] = None
                elif hasattr(value, "isoformat"):
                    record[column] = value.isoformat()
                else:
                    record[column] = str(value)
            case_listing.append(record)
        return case_listing, None
    except Exception as error:
        return None, "Error generating case listing: " + str(error)


def generate_evidence(frame):
    """Run all analyses and return one serializable evidence dictionary."""
    if frame is None or frame.empty:
        return None, "Frame is empty or None"

    analyses = [
        ("case_summary", analyze_cases),
        ("demographics", analyze_demographics),
        ("countries", analyze_countries),
        ("reactions", analyze_reactions),
        ("outcomes", analyze_outcomes),
        ("expedited_alerts", analyze_expedited_cases),
        ("monthly_trends", analyze_monthly_trends),
        ("reaction_trends", analyze_reaction_trends),
        ("case_listing", generate_case_listing),
    ]

    evidence = {}
    for key, analysis_function in analyses:
        value, error = analysis_function(frame)
        if error:
            return None, error
        evidence[key] = value

    evidence["reporting_period"] = {
        "start": frame[RECEIVED_DATE_COLUMN].min().date().isoformat(),
        "end": frame[RECEIVED_DATE_COLUMN].max().date().isoformat(),
    }
    evidence["trend_observations"] = describe_monthly_trends(
        evidence["monthly_trends"]
    )
    return evidence, None