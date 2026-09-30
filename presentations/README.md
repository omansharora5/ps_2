# VAJRA SIH26072 presentation

- [PowerPoint deck](VAJRA_SIH26072.pptx)
- [Architecture and data flow](SIH26072_ARCHITECTURE_AND_DATA_FLOW.md)

The six slides follow the supplied `VMD-slide2-flow-updated.pptx` reference. Its SIH branding, team label, slide order, theme, diagram routing and layout are retained. The weather architecture, risk table, evaluation table and radar comparison chart remain editable. Speaker notes contain source URLs, implementation boundaries and measurement definitions.

The core proposal is a 30-minute regional predictive model with an officer website and a public React Native client. The deck separates that proposed integration from working research components. It does not claim established NCR lightning accuracy, superiority to Damini or a completed open Indian benchmark.

The source reference is not included in this repository. To reproduce the candidate, use the supplied reference and the bundled `@oai/artifact-tool` 2.8.79 runtime:

```powershell
$env:CODEX_PRESENTATION_RUNTIME = 'C:/Users/dell/.cache/codex-runtimes/codex-primary-runtime/dependencies/node'
& "$env:CODEX_PRESENTATION_RUNTIME/bin/node.exe" scripts/build_sih_presentation.mjs 'C:/Users/dell/Downloads/VMD-slide2-flow-updated.pptx'
```

The builder writes a candidate, six renders and layout snapshots to the ignored `.presentation-build/` directory. Inspect each render against the source before finalizing or replacing the published deck. It requires the existing `artifacts/observed-radar.png` screenshot. Numerical measurements come from [VALIDATION.md](../VALIDATION.md) and the [recorded synthetic run](../artifacts/regional-research/d95852635db7d3a663ea160588729f78a59c61607c0e300d5d377777bee46cbc/report.json).

The reference has no assigned team ID, so that field stays blank. Confirm the preserved team name before submission.
