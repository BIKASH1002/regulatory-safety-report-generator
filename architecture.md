# Architecture

## System flow

```mermaid
flowchart LR
    A[CSV or XLSX Safety Dataset]

    subgraph Deterministic[Deterministic Python Boundary]
        B[Load and Validate]
        C[Case-Level and Reaction-Level Analysis]
        D[Structured Evidence]
        E[Section Context Builder]
    end

    subgraph AI[Controlled AI Boundary]
        F[Gemini Section Generation]
    end

    subgraph Controls[Validation and Human Control]
        G[Numerical Grounding Check]
        H{Human Review}
        I[Approval or Flag]
    end

    J[PADER-Style Markdown Report]
    K[Evaluation Metrics]

    A --> B --> C --> D --> E --> F --> G --> H --> I
    I --> J
    G --> K
    I --> K
```

## Component responsibilities

| Component | Responsibility | Trust boundary |
| --- | --- | --- |
| `data_loader.py` | Load XLSX/CSV, validate required fields, parse dates | Deterministic |
| `analysis.py` | Deduplicate cases, calculate metrics, build evidence and listing | Deterministic |
| `context_builder.py` | Select relevant evidence and fill section prompts | Deterministic |
| `llm_client.py` | Call one configured Gemini model with conservative settings | AI |
| `grounding_check.py` | Compare generated numerical claims with supplied evidence | Deterministic control |
| `review.py` | Require explicit approval or flagging | Human control |
| `report_generator.py` | Assemble Markdown and compute evaluation metrics | Deterministic |
| `main.py` | Coordinate the CLI workflow | Orchestration |

## Counting boundary

```mermaid
flowchart TD
    A[Validated rows] --> B{Metric type}
    B -->|Case-level| C[Deduplicate by safetyreportid]
    B -->|Reaction-level| D[Retain reaction rows]
    C --> E[Cases, seriousness, demographics, country, months, expedited]
    D --> F[Reaction frequency, outcomes, case listing]
    E --> G[Structured evidence]
    F --> G
```

Gemini receives structured evidence rather than the spreadsheet. It is therefore downstream of all factual calculation and cannot become the source of record for counts or percentages.

## Finalization rule

```text
final section = generated text
                AND grounding status PASS
                AND human approval
```

If generation fails, numerical grounding flags a claim, or a reviewer rejects a section, the report marks it as not finalized.
