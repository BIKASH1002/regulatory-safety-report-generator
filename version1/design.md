# Version 1 Design: Configurable Regulatory Reports

Version 0 implements one PADER-style report with explicit Python functions and section prompts. Version 1 should preserve the deterministic/AI boundary while making report composition configurable enough to support PADER, PSUR, PBRER, DSUR, and CSR without rewriting core analyses.

## Configuration-driven report types

A small YAML or JSON configuration could define sections, evidence dependencies, prompts, and review rules:

```yaml
report_type: PADER
version: 1
sections:
  narrative_summary:
    analyses:
      - case_summary
      - demographics
      - top_reactions
      - countries
    prompt: narrative_summary
    requires_grounding: true
    requires_human_approval: true
  history_of_actions:
    analyses:
      - supplied_actions
    generator: deterministic
```

Other report types would select different sections and instructions while reusing the same validated evidence. Configuration should describe composition, not contain calculation code.

## Reusable deterministic analyses

The following analyses can serve several report types:

- unique and serious case counts
- age and sex distributions
- geographic distributions
- reaction frequencies and outcomes
- monthly case and reaction trends
- expedited-reporting counts
- case listings

Each analysis should return JSON-serializable evidence with a stable key and calculation metadata. Report sections declare which keys they need; the context builder sends only those keys to the model.

## Section dependencies

A section registry can map configuration names to normal Python functions. Before generation, the orchestrator should verify that every required evidence key exists. Missing dependencies should create an explicit section error rather than an incomplete prompt.

This remains simpler and easier to test than a general workflow framework. No agent orchestration, vector database, or RAG layer is needed for the current data flow.

## Version and audit metadata

Each report run should record:

- report type and configuration version
- source dataset identifier and checksum
- analysis-code version
- prompt-template version
- Gemini model name/version
- generation timestamp
- grounding results
- reviewer identity, decision, and timestamp
- final report checksum

These fields make results reproducible and support controlled prompt/model upgrades.

## Better evidence tracing

Version 0 traces section numbers to an evidence dictionary. Version 1 could attach IDs to evidence items and retain the contributing aggregation and case IDs:

```text
generated sentence
  -> evidence item ID
  -> calculation and source columns
  -> contributing safetyreportid values
```

Sentence-level citations could be requested as structured model output, then verified against allowed evidence IDs. The deterministic report builder would remove internal IDs from reader-facing prose while preserving them in an audit record.

## Scaled evaluation

For 1,000 reports, run a fixed regression corpus across report types and compare:

- deterministic totals against expected fixtures
- generated numbers against scoped evidence
- required-section completeness
- generation and grounding failure rates
- unsupported-claim rate
- human rejection and edit rates
- latency and cost by section/report type
- differences across prompt and model versions

High-risk or failed reports should receive mandatory expert review. A stratified random sample of passing reports should also be reviewed so the system measures false passes, not only known failures.

## Deliberate boundaries

Version 1 should not infer SOC without a supplied mapping, expectedness without an approved label source, causality from spontaneous reports, or regulatory actions without action-history data. Adding a report type must not weaken these evidence requirements.
