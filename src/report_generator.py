"""Assemble the reviewed Markdown report and evaluation summary."""

from pathlib import Path


SECTION_TITLES = {
    "narrative_summary": "Narrative Summary and Analysis",
    "case_analysis": "Summary Analysis of Cases",
    "reaction_analysis": "Reaction / Adverse Event Analysis",
    "expedited_cases": "Serious Cases / 15-Day Alerts",
    "trends": "Trends and Important Observations",
}


def _build_markdown_table(headers, rows):
    lines = ["| " + " | ".join(headers) + " |"]
    lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
    for row in rows:
        values = []
        for value in row:
            values.append(str(value).replace("|", "\\|"))
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def _build_count_rows(counts_by_name, limit=None):
    rows = []
    for name, count in counts_by_name.items():
        rows.append((name, count))
        if limit is not None and len(rows) == limit:
            break
    return rows


def _append_case_tables(lines, evidence):
    case_summary = evidence.get("case_summary", {})
    lines.extend([
        _build_markdown_table(
            ["Case metric", "Value"],
            [
                ("Unique cases", case_summary.get("unique_cases", 0)),
                ("Serious cases", case_summary.get("serious_cases", 0)),
                ("Non-serious cases", case_summary.get("non_serious_cases", 0)),
                (
                    "Serious percentage",
                    str(case_summary.get("serious_percentage", 0)) + "%",
                ),
            ],
        ),
        "",
        "### Demographics",
        "",
    ])

    demographics = evidence.get("demographics", {})
    lines.append(
        _build_markdown_table(
            ["Sex", "Count"],
            _build_count_rows(demographics.get("sex_distribution", {})),
        )
    )
    lines.extend(["", "### Age Groups", ""])
    lines.append(
        _build_markdown_table(
            ["Age group", "Count"],
            _build_count_rows(demographics.get("age_distribution", {})),
        )
    )
    lines.extend(["", "### Countries", ""])
    lines.append(
        _build_markdown_table(
            ["Country", "Count"],
            _build_count_rows(evidence.get("countries", {}), limit=20),
        )
    )
    lines.append("")


def _append_reaction_tables(lines, evidence):
    reactions = evidence.get("reactions", {})
    lines.extend(["### Most Common Reactions", ""])
    lines.append(
        _build_markdown_table(
            ["Reaction", "Count"],
            _build_count_rows(reactions.get("top_reactions", {}), limit=20),
        )
    )
    lines.extend(["", "### Reaction Outcomes", ""])
    lines.append(
        _build_markdown_table(
            ["Outcome", "Count"],
            _build_count_rows(evidence.get("outcomes", {}), limit=20),
        )
    )
    lines.extend([
        "",
        (
            "SOC-level analysis was not performed because System Organ Class "
            "information was not supplied in the dataset. Expectedness was not "
            "assessed because a product label or CCDS reference was not supplied."
        ),
        "",
    ])


def _append_trend_tables(lines, evidence):
    lines.append(
        _build_markdown_table(
            ["Month", "Case count"],
            _build_count_rows(evidence.get("monthly_trends", {})),
        )
    )
    lines.extend(["", "### Reaction Trends by Month", ""])

    reaction_rows = []
    for month, reactions in evidence.get("reaction_trends", {}).items():
        for reaction, count in reactions.items():
            reaction_rows.append((month, reaction, count))
    lines.append(_build_markdown_table(["Month", "Reaction", "Count"], reaction_rows))
    lines.append("")


def _append_case_listing(lines, evidence, max_case_rows):
    case_listing = evidence.get("case_listing", [])
    listing_rows = []
    for case_record in case_listing[:max_case_rows]:
        listing_rows.append((
            case_record.get("safetyreportid", ""),
            case_record.get("patient_reaction_reactionmeddrapt", ""),
            case_record.get("serious", ""),
            case_record.get("receivedate", ""),
            case_record.get("occurcountry", ""),
            case_record.get("patient_reaction_reactionoutcome", ""),
        ))

    lines.append(
        _build_markdown_table(
            ["Case ID", "Reaction", "Seriousness", "Received", "Country", "Outcome"],
            listing_rows,
        )
    )
    if len(case_listing) > len(listing_rows):
        lines.extend([
            "",
            "Showing "
            + str(len(listing_rows))
            + " of "
            + str(len(case_listing))
            + " reaction-level listing rows. This table is a preview; "
            "the complete listing is available from the deterministic evidence output.",
        ])


def build_report(evidence, generated_sections, review_results, max_case_rows=10):
    """Build a PADER-style Markdown report from evidence and approved prose."""
    if not evidence:
        return None, "Evidence required to build report"

    period = evidence.get("reporting_period", {})
    period_text = (
        str(period.get("start", "unknown"))
        + " to "
        + str(period.get("end", "unknown"))
    )
    lines = [
        "# PADER-Style Safety Report - Bisoprolol",
        "",
        "## Reporting Period",
        "",
        period_text,
        "",
    ]

    for section_name, title in SECTION_TITLES.items():
        lines.extend(["## " + title, ""])
        review = review_results.get(section_name, {})
        if review.get("status") == "approved":
            lines.extend([generated_sections.get(section_name, ""), ""])
        else:
            reason = review.get("reason", "Section was not reviewed")
            lines.extend(["**Not finalized:** " + reason + ".", ""])

        if section_name == "case_analysis":
            _append_case_tables(lines, evidence)
        elif section_name == "reaction_analysis":
            _append_reaction_tables(lines, evidence)
        elif section_name == "expedited_cases":
            alerts = evidence.get("expedited_alerts", {})
            rows = [("Expedited cases", alerts.get("expedited_case_count", 0))]
            lines.extend([_build_markdown_table(["Alert metric", "Value"], rows), ""])
        elif section_name == "trends":
            _append_trend_tables(lines, evidence)

    lines.extend([
        "## History of Actions",
        "",
        (
            "No history-of-actions information was supplied for this exercise. "
            "No regulatory actions, labeling changes, studies, risk-minimization "
            "measures, or safety communications are inferred."
        ),
        "",
        "## Case Index / Listing",
        "",
        "### Listing Preview",
        "",
    ])
    _append_case_listing(lines, evidence, max_case_rows)
    return "\n".join(lines).rstrip() + "\n", None


def write_report(report_text, output_path):
    """Write a Markdown report to disk."""
    report_path = Path(output_path)
    try:
        report_path.write_text(report_text, encoding="utf-8")
    except OSError as error:
        return None, "Could not write report to '" + str(report_path) + "': " + str(error)
    return report_path, None


def evaluate_report(generated_sections, validation_results, review_results):
    """Return generation, grounding, completeness, and approval metrics."""
    required_sections = set(SECTION_TITLES)
    generated_names = set(generated_sections)

    passing_count = 0
    unsupported_count = 0
    for validation_result in validation_results.values():
        if validation_result.get("status") == "PASS":
            passing_count += 1
        unsupported_count += len(validation_result.get("unsupported_numbers", []))

    approved_count = 0
    for review_result in review_results.values():
        if review_result.get("status") == "approved":
            approved_count += 1

    approval_rate = round(
        (approved_count / len(required_sections)) * 100,
        1,
    )
    return {
        "sections_generated": len(generated_names),
        "sections_passing_grounding": passing_count,
        "sections_flagged": len(required_sections) - approved_count,
        "unsupported_numerical_claims": unsupported_count,
        "missing_required_sections": sorted(required_sections - generated_names),
        "sections_approved": approved_count,
        "human_approval_rate": approval_rate,
    }