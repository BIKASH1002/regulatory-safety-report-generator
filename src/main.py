"""Unified entry point for the regulatory safety reporting prototype."""

import argparse
import json

from dotenv import load_dotenv

from .analysis import generate_evidence
from .context_builder import build_section_context, load_prompt_template
from .data_loader import load_dataset, profile_dataset, validate_dataset
from .grounding_check import check_grounding
from .llm_client import generate_section, initialize_client
from .report_generator import build_report, evaluate_report, write_report
from .review import review_sections


REPORT_SECTIONS = [
    "narrative_summary",
    "case_analysis",
    "reaction_analysis",
    "expedited_cases",
    "trends",
]


def generate_grounded_sections(evidence, client):
    """Generate and numerically validate all LLM-authored sections."""
    generated_sections = {}
    validation_results = {}

    system_prompt, error = load_prompt_template("system_prompt")
    if error:
        for section_name in REPORT_SECTIONS:
            validation_results[section_name] = {"status": "ERROR", "error": error}
        return generated_sections, validation_results

    for section_name in REPORT_SECTIONS:
        context_packet, error = build_section_context(section_name, evidence)
        if error:
            validation_results[section_name] = {"status": "ERROR", "error": error}
            continue

        generated_text, error = generate_section(
            client,
            system_prompt,
            context_packet.get("prompt", ""),
            max_tokens=1024,
        )
        if error:
            validation_results[section_name] = {"status": "ERROR", "error": error}
            continue

        grounding_validation, error = check_grounding(generated_text, context_packet, evidence)
        if error:
            grounding_validation = {"status": "ERROR", "error": error}

        generated_sections[section_name] = generated_text
        validation_results[section_name] = grounding_validation

    return generated_sections, validation_results


def generate_reviewed_report(
    validated_frame, client, output_path, input_func=input, output_func=print
):
    """Generate, review, evaluate, and write a grounded safety report."""
    evidence, error = generate_evidence(validated_frame)
    if error:
        return None, error

    generated_sections, validation_results = generate_grounded_sections(evidence, client)
    review_results = review_sections(
        generated_sections,
        validation_results,
        input_func=input_func,
        output_func=output_func,
    )
    report_text, error = build_report(evidence, generated_sections, review_results)
    if error:
        return None, error

    report_path, error = write_report(report_text, output_path)
    if error:
        return None, error

    return {
        "success": True,
        "phase": 4,
        "report_path": str(report_path),
        "review": review_results,
        "evaluation": evaluate_report(generated_sections, validation_results, review_results),
    }, None


def main():
    load_dotenv()

    parser = argparse.ArgumentParser(
        description="Analyze a regulatory safety dataset and generate a reviewed report."
    )
    parser.add_argument("dataset_path", help="Path to an XLSX or CSV dataset")
    parser.add_argument(
        "--phase",
        type=int,
        choices=[1, 2, 3, 4],
        default=1,
        help="1=profiling, 2=analysis, 3=Gemini generation, 4=reviewed Markdown report",
    )
    parser.add_argument(
        "--output",
        default="report_output.md",
        help="Reviewed Markdown report output path (default: report_output.md)",
    )
    arguments = parser.parse_args()

    dataset_frame, error = load_dataset(arguments.dataset_path)
    if error:
        print(json.dumps({"error": error}))
        return 1

    validated_frame, error = validate_dataset(dataset_frame)
    if error:
        print(json.dumps({"error": error}))
        return 1

    if arguments.phase == 1:
        profile, error = profile_dataset(validated_frame)
        command_result = {"success": True, "phase": 1, "profile": profile}
    elif arguments.phase == 2:
        evidence, error = generate_evidence(validated_frame)
        command_result = {"success": True, "phase": 2, "evidence": evidence}
    else:
        client, error = initialize_client()
        if error:
            print(json.dumps({"error": error}))
            return 1

        if arguments.phase == 3:
            evidence, error = generate_evidence(validated_frame)
            if not error:
                generated_sections, validation_results = generate_grounded_sections(evidence, client)
                command_result = {
                    "success": True,
                    "phase": 3,
                    "evidence": evidence,
                    "generated_sections": generated_sections,
                    "grounding_validation": validation_results,
                }
        else:
            command_result, error = generate_reviewed_report(validated_frame, client, arguments.output)

    if error:
        print(json.dumps({"error": error}))
        return 1

    print(json.dumps(command_result, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())