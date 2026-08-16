"""Simple human approval gate for generated report sections."""


def review_sections(generated_sections, validation_results, input_func=input, output_func=print):
    """Prompt a reviewer to approve grounded sections or flag them."""
    review_results = {}

    for section_name, generated_text in generated_sections.items():
        validation = validation_results.get(section_name, {})
        grounding_status = validation.get("status", "ERROR")

        output_func("\nGenerated: " + section_name)
        output_func(generated_text)
        output_func("Grounding status: " + grounding_status)

        if grounding_status != "PASS":
            output_func("Section automatically flagged because grounding did not pass.")
            review_results[section_name] = {
                "status": "flagged",
                "reason": "Grounding status: " + grounding_status,
            }
            continue

        reviewer_choice = input_func("Approve section? [1=Approve, 2=Flag]: ").strip().lower()
        if reviewer_choice in {"1", "approve", "y", "yes"}:
            review_results[section_name] = {"status": "approved"}
        else:
            review_results[section_name] = {
                "status": "flagged",
                "reason": "Flagged by human reviewer",
            }

    return review_results
