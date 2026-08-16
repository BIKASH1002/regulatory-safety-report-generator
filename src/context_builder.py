"""Build section-specific evidence packets for Gemini."""

import json
from pathlib import Path


PROMPT_DIRECTORY = Path(__file__).parent.parent / "prompts"


def load_prompt_template(section_name):
    """Load a prompt template by name."""
    template_path = PROMPT_DIRECTORY / (section_name + ".txt")
    if not template_path.is_file():
        return None, "Prompt template not found: " + str(template_path)

    try:
        return template_path.read_text(encoding="utf-8"), None
    except OSError as error:
        return None, "Could not read prompt template '" + str(template_path) + "': " + str(error)


def get_reporting_period(evidence):
    """Return the exact reporting period stored in evidence."""
    period = evidence.get("reporting_period", {}) if evidence else {}
    start = period.get("start", "unknown")
    end = period.get("end", "unknown")
    return str(start) + " to " + str(end)


def format_top_frequency_counts(frequency_counts, max_items=5):
    """Format the most frequent dictionary items for a prompt."""
    if not frequency_counts:
        return "No data available"

    ordered_counts = sorted(
        frequency_counts.items(),
        key=lambda count_pair: count_pair[1],
        reverse=True,
    )
    formatted_items = []
    for name, count in ordered_counts[:max_items]:
        formatted_items.append(str(name) + " (n=" + str(count) + ")")
    return ", ".join(formatted_items)


def _load_section_template(section_name):
    template, error = load_prompt_template(section_name)
    if error:
        return None, error
    return template, None


def build_narrative_summary_context(evidence):
    """Build the narrative-summary evidence packet."""
    if not evidence:
        return None, "Evidence required for narrative summary context"

    template, error = _load_section_template("narrative_summary")
    if error:
        return None, error

    case_summary = evidence.get("case_summary", {})
    reactions = evidence.get("reactions", {})
    countries = evidence.get("countries", {})
    reporting_period = get_reporting_period(evidence)
    dates = reporting_period.split(" to ", maxsplit=1)

    ordered_countries = sorted(
        countries.items(), key=lambda item: item[1], reverse=True
    )
    primary_countries = [name for name, _ in ordered_countries[:3]]

    prompt = template.format(
        reporting_period=reporting_period,
        total_cases=case_summary.get("unique_cases", 0),
        serious_cases=case_summary.get("serious_cases", 0),
        serious_percentage=case_summary.get("serious_percentage", 0),
        non_serious_cases=case_summary.get("non_serious_cases", 0),
        period_start=dates[0],
        period_end=dates[-1],
        top_reactions=format_top_frequency_counts(reactions.get("top_reactions", {}), 5),
        primary_countries=", ".join(primary_countries) or "not available",
    )
    return {
        "section": "Narrative Summary and Analysis",
        "prompt": prompt,
        "evidence_keys": [
            "case_summary",
            "reactions",
            "countries",
            "reporting_period",
        ],
    }, None


def build_case_analysis_context(evidence):
    """Build the case-analysis evidence packet."""
    if not evidence:
        return None, "Evidence required for case analysis context"

    template, error = _load_section_template("case_analysis")
    if error:
        return None, error

    summary = evidence.get("case_summary", {})
    demographics = evidence.get("demographics", {})
    period = evidence.get("reporting_period", {})
    prompt = template.format(
        total_rows=summary.get("total_rows", 0),
        unique_cases=summary.get("unique_cases", 0),
        duplicate_rows=summary.get("duplicate_rows", 0),
        serious_cases=summary.get("serious_cases", 0),
        non_serious_cases=summary.get("non_serious_cases", 0),
        unknown_seriousness=summary.get("unknown_seriousness", 0),
        serious_percentage=summary.get("serious_percentage", 0),
        sex_distribution=json.dumps(
            demographics.get("sex_distribution", {}), indent=2
        ),
        age_distribution=json.dumps(
            demographics.get("age_distribution", {}), indent=2
        ),
        min_date=period.get("start", "unknown"),
        max_date=period.get("end", "unknown"),
    )
    return {
        "section": "Summary Analysis of Cases",
        "prompt": prompt,
        "evidence_keys": ["case_summary", "demographics", "reporting_period"],
    }, None


def build_reaction_analysis_context(evidence):
    """Build the reaction-analysis evidence packet."""
    if not evidence:
        return None, "Evidence required for reaction analysis context"

    template, error = _load_section_template("reaction_analysis")
    if error:
        return None, error

    reactions = evidence.get("reactions", {})
    outcomes = evidence.get("outcomes", {})
    outcome_lines = []
    for outcome, count in sorted(
        outcomes.items(), key=lambda item: item[1], reverse=True
    ):
        outcome_lines.append("- " + str(outcome) + ": " + str(count))

    prompt = template.format(
        top_reactions=format_top_frequency_counts(reactions.get("top_reactions", {}), 10),
        unique_reaction_count=reactions.get("unique_reaction_count", 0),
        top_serious_reactions=format_top_frequency_counts(
            reactions.get("top_serious_reactions", {}), 10
        ),
        outcomes_list="\n".join(outcome_lines) or "No outcome data available",
    )
    return {
        "section": "Reaction / Adverse Event Analysis",
        "prompt": prompt,
        "evidence_keys": ["reactions", "outcomes"],
    }, None


def build_trends_context(evidence):
    """Build the temporal and geographic trends evidence packet."""
    if not evidence:
        return None, "Evidence required for trends context"

    template, error = _load_section_template("trends")
    if error:
        return None, error

    monthly = evidence.get("monthly_trends", {})
    reaction_trends = evidence.get("reaction_trends", {})
    countries = evidence.get("countries", {})
    observations = evidence.get("trend_observations", [])

    if monthly:
        peak_month = max(monthly, key=monthly.get)
        low_month = min(monthly, key=monthly.get)
    else:
        peak_month = "unknown"
        low_month = "unknown"

    ordered_countries = sorted(
        countries.items(), key=lambda item: item[1], reverse=True
    )
    primary_countries = [name for name, _ in ordered_countries[:3]]

    prompt = template.format(
        monthly_trends=json.dumps(monthly, indent=2),
        reaction_trends=json.dumps(reaction_trends, indent=2),
        peak_month=peak_month,
        low_month=low_month,
        countries_distribution=json.dumps(countries, indent=2),
        primary_countries=", ".join(primary_countries) or "not available",
        observations="\n".join(observations) or "No observations available",
    )
    return {
        "section": "Trends and Important Observations",
        "prompt": prompt,
        "evidence_keys": [
            "monthly_trends",
            "reaction_trends",
            "trend_observations",
            "countries",
        ],
    }, None


def build_expedited_cases_context(evidence):
    """Build the serious and expedited-case evidence packet."""
    if not evidence:
        return None, "Evidence required for expedited cases context"

    template, error = _load_section_template("expedited_cases")
    if error:
        return None, error

    summary = evidence.get("case_summary", {})
    reactions = evidence.get("reactions", {})
    expedited = evidence.get("expedited_alerts", {})
    total_cases = summary.get("unique_cases", 0)
    expedited_count = expedited.get("expedited_case_count", 0)
    expedited_percentage = 0
    if total_cases:
        expedited_percentage = round((expedited_count / total_cases) * 100, 1)

    prompt = template.format(
        serious_cases=summary.get("serious_cases", 0),
        serious_percentage=summary.get("serious_percentage", 0),
        serious_reactions=format_top_frequency_counts(
            reactions.get("top_serious_reactions", {}), 10
        ),
        expedited_count=expedited_count,
        expedited_percentage=expedited_percentage,
        serious_findings="Cases meeting expedited criteria require human review.",
    )
    return {
        "section": "Serious Cases / 15-Day Alerts",
        "prompt": prompt,
        "evidence_keys": ["case_summary", "reactions", "expedited_alerts"],
        "allowed_numbers": [15],
    }, None


def build_section_context(section_name, evidence):
    """Build the evidence packet for a named report section."""
    context_builders = {
        "narrative_summary": build_narrative_summary_context,
        "case_analysis": build_case_analysis_context,
        "reaction_analysis": build_reaction_analysis_context,
        "trends": build_trends_context,
        "expedited_cases": build_expedited_cases_context,
    }
    context_builder = context_builders.get(section_name)
    if context_builder is None:
        valid_names = ", ".join(context_builders)
        return None, "Unknown section: " + section_name + ". Valid sections: " + valid_names
    return context_builder(evidence)