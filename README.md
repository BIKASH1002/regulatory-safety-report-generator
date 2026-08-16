# Grounded Regulatory Safety Reporting Prototype

This project generates a reviewed, PADER-style Markdown safety report from an ICSR dataset. It is a Version 0 assessment prototype: deterministic Python code calculates and owns every factual metric, while Gemini converts small, section-specific evidence packets into neutral regulatory prose.

The source dataset contains reaction-level rows, so several rows can belong to one safety case. The pipeline deduplicates case-level analyses by `safetyreportid` while preserving reaction-level counting for reaction frequencies, outcomes, and the case listing.

## Requirements

- Python 3.12 recommended
- A Gemini API key
- An XLSX or CSV dataset with the required safety-report columns

## Setup

```bash
cd /home/bikash/quickhire_assignment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Set the key in `.env`:

```dotenv
GEMINI_API_KEY=your_api_key
```

`.env` is ignored by Git and must never be included in the submission ZIP.

## Run the report

```bash
python -m src.main \
  dataset/Bisoprolol_icsr_sample_1068rows.xlsx \
  --phase 4 \
  --output report_output.md
```

The CLI displays each generated section, its grounding result, and an approval prompt. Enter `1` to approve a grounded section or `2` to flag it. A section is final only when numerical grounding passes and a human approves it.

To verify API connectivity without processing the dataset:

```bash
python -m src.llm_client
```

## Run tests

Tests use mocked Gemini responses and do not require paid API calls:

```bash
python -m pytest -W error
```

## Other CLI operations

```bash
# Load, validate, and profile
python -m src.main <dataset.xlsx> --phase 1

# Produce deterministic evidence as JSON
python -m src.main <dataset.xlsx> --phase 2

# Generate and ground sections without report review/assembly
python -m src.main <dataset.xlsx> --phase 3
```

## Architecture

```text
Dataset
  -> loader and validation
  -> deterministic analysis
  -> structured evidence
  -> section-specific context builder
  -> Gemini prose generation
  -> numerical grounding check
  -> human approval or flagging
  -> Markdown report and evaluation metrics
```

See [architecture.md](architecture.md) for component boundaries and data flow.

### Python owns the facts

Python performs:

- case deduplication by `safetyreportid`
- serious and non-serious case counts
- percentages
- demographic and geographic aggregation
- reaction and outcome frequency calculation
- monthly case aggregation
- expedited-case analysis
- reporting-period derivation
- case-listing construction

Gemini never receives the raw spreadsheet and is not relied upon for arithmetic.

### Gemini owns controlled language generation

Gemini receives only the evidence needed for one section and produces:

- neutral regulatory prose
- supported summaries of observed patterns
- conservative descriptions that avoid causality and signal declarations

The system uses `gemini-2.5-flash` through the supported `google-genai` SDK. The model name is defined once in `src/llm_client.py`.

## Prompt and context design

The common safety rules are stored in `prompts/system_prompt.txt`. The key instructions are:

```text
Use ONLY the evidence provided. Never invent or assume data.
Do NOT perform arithmetic.
Do NOT claim causality.
Do NOT declare or suggest a safety signal exists.
Do NOT infer expectedness without explicit data.
When information is unavailable, state that clearly.
```

Each generated section has its own template:

- `narrative_summary.txt`: reporting period, case totals, seriousness, reactions, countries
- `case_analysis.txt`: rows versus cases, demographics, seriousness, dates
- `reaction_analysis.txt`: reaction frequencies, serious reactions, outcomes
- `expedited_cases.txt`: serious cases and expedited-reporting evidence
- `trends.txt`: monthly and geographic distributions

`src/context_builder.py` fills these templates from approved evidence. Unrelated evidence is not sent to every call.

## Grounding and traceability

`src/grounding_check.py` extracts numerical claims from generated prose and compares them with numbers in the evidence packet supplied to that section. Unsupported numbers produce a `FLAG` and the section cannot be approved as final.

Traceability is intentionally simple:

```text
generated section
  -> context packet evidence_keys
  -> deterministic evidence dictionary
  -> source aggregation in analysis.py
```

This catches unsupported numerical claims but is not a complete semantic factuality checker.

## Human control

The report workflow displays generated prose and grounding status before accepting a decision. Grounding failures are automatically flagged. Human decisions and evaluation metrics are returned by the CLI and unapproved report sections are marked `Not finalized`.

## Evaluation

The current evaluation reports:

- sections generated
- sections passing grounding
- sections flagged
- unsupported numerical claims
- missing required sections
- sections approved
- human approval rate

For 1,000 reports, the same records could be stored per report and aggregated into numerical-consistency rate, unsupported-claim rate, section-completeness rate, grounding-failure rate, human-rejection rate, generation-failure rate, latency, and cost. A stratified sample should also receive blinded domain-expert review. Prompt, model, dataset, and analysis versions should be retained so regressions can be traced and reproduced.

## Important data rules

- Case-level calculations deduplicate by `safetyreportid`.
- Reaction frequencies and outcomes use reaction-level rows.
- `occurcountry` is the primary geographic field.
- System Organ Class analysis is not performed because SOC is not supplied.
- Expectedness is not determined because no product label or CCDS is supplied.
- History of Actions is deterministic text stating that no source information was supplied.
- The sample PADER is a style reference, not factual evidence.

## Generalization beyond PADER

The current PADER workflow is the first configured report type, not a separate architecture that must be replaced for every regulatory document. The loader, deterministic analyses, evidence dictionary, grounding validator, review gate, and report evaluation can be reused for PSUR, PBRER, DSUR, and CSR workflows.

A future report-type configuration would declare:

- required sections and their order
- deterministic analyses required by each section
- section-specific prompt templates
- required source data and unavailable-data rules
- grounding and human-approval requirements

For example, PSUR and PBRER could reuse case counts, demographics, reaction frequencies, outcomes, and temporal trends while adding benefit-risk and cumulative-exposure evidence. DSUR could reuse safety analyses while adding development-program and study evidence. CSR could select study-level analyses and section templates without changing the grounding or review components.

The proposed configuration, versioning, evidence tracing, and scaled-evaluation design is documented in `version1/design.md`.
## Limitations

- Numerical grounding does not guarantee complete semantic faithfulness.
- Trend detection uses simple deterministic aggregation, not statistical signal detection.
- The report shows a 10-row case-listing preview to keep the Markdown report readable; the complete listing remains available in the deterministic evidence output.
- Only a PADER-style Version 0 report is implemented.
- There is no production authentication, audit database, job queue, or deployment infrastructure.
- SOC, expectedness, causal assessment, and regulatory actions cannot be derived from the supplied sources.

## Submission packaging

Include:

```text
src/
prompts/
tests/
version1/design.md
README.md
architecture.md
report_output.md
requirements.txt
.env.example
```

Exclude:

```text
.env
venv/
.pytest_cache/
.benchmarks/
__pycache__/
*.pyc
dataset/
quickhire prompt.docx
local development notes and temporary files
```
