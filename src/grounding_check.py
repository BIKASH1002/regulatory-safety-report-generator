"""Validate generated numbers against deterministic evidence."""

import re


NUMBER_PATTERN = re.compile(r"\b\d+(?:\.\d+)?\b")


def extract_numbers_from_text(text):
    """Return numeric strings and values found in text."""
    if not text:
        return []

    numbers = []
    for match in NUMBER_PATTERN.finditer(str(text)):
        number_text = match.group(0)
        if "." in number_text:
            number = float(number_text)
        else:
            number = int(number_text)
        numbers.append((number_text, number))
    return numbers


def _collect_evidence_numbers(value, evidence_numbers):
    """Recursively collect numeric values into the supplied evidence set."""
    if isinstance(value, bool):
        return
    if isinstance(value, (int, float)):
        evidence_numbers.add(float(value))
        return
    if isinstance(value, dict):
        for key, nested_value in value.items():
            _collect_evidence_numbers(key, evidence_numbers)
            _collect_evidence_numbers(nested_value, evidence_numbers)
        return
    if isinstance(value, (list, tuple)):
        for nested_value in value:
            _collect_evidence_numbers(nested_value, evidence_numbers)
        return
    if isinstance(value, str):
        searchable_value = value.replace("_", " ")
        for _, number in extract_numbers_from_text(searchable_value):
            evidence_numbers.add(float(number))


def get_evidence_numbers(evidence, evidence_keys):
    """Collect numbers from the evidence assigned to a report section."""
    evidence_numbers = set()
    for key in evidence_keys:
        if key in evidence:
            _collect_evidence_numbers(evidence[key], evidence_numbers)
    return evidence_numbers


def check_grounding(generated_text, context_packet, evidence):
    """Flag generated numbers that are absent from the section evidence."""
    if not generated_text or not context_packet or not evidence:
        return None, (
            "Generated text, context packet, and evidence are required for "
            "grounding validation"
        )

    text_numbers = extract_numbers_from_text(generated_text)
    evidence_keys = context_packet.get("evidence_keys", [])
    evidence_numbers = get_evidence_numbers(evidence, evidence_keys)

    for number in context_packet.get("allowed_numbers", []):
        evidence_numbers.add(float(number))

    unsupported = []
    for number_text, number in text_numbers:
        supported = False
        for evidence_number in evidence_numbers:
            if abs(float(number) - evidence_number) <= 0.1:
                supported = True
                break
        if not supported:
            unsupported.append((number_text, number))

    issues = []
    for number_text, number in unsupported:
        issues.append(
            "Number '" + number_text + "' not found in evidence (" + str(number) + ")"
        )

    return {
        "status": "FLAG" if unsupported else "PASS",
        "numbers_found": text_numbers,
        "unsupported_numbers": unsupported,
        "issues": issues,
    }, None


def format_grounding_report(validation_result):
    """Format a grounding result for terminal output."""
    if not validation_result:
        return "No validation result"

    status = validation_result.get("status", "UNKNOWN")
    issues = validation_result.get("issues", [])
    lines = ["Grounding Status: " + status]
    if issues:
        lines.append("Issues (" + str(len(issues)) + "):")
        for issue in issues:
            lines.append("  - " + issue)
    else:
        lines.append("No issues detected.")
    return "\n".join(lines) + "\n"