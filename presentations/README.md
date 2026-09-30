# VAJRA SIH26072 presentation

- [Revised PowerPoint deck](VAJRA_SIH26072_v2.pptx)
- [Previous deck](VAJRA_SIH26072.pptx)
- [Architecture and data flow](SIH26072_ARCHITECTURE_AND_DATA_FLOW.md)
- [Feature keywords and implementation status](REVISION_2_DESIGN.md)
- [Delhi NCR satellite image provenance](assets/README.md)

The six slides follow the supplied `VMD-slide2-flow-updated.pptx` reference. Its SIH branding, team label, slide order and theme are retained. Revision 2 rebuilds slide 3 around the weather workflow, with separate forecast and reviewed-learning loops. It keeps the reference's blue connectors, pastel processing boxes, database cylinders and decision diamond. The architecture, risk table, evaluation table and radar comparison chart remain editable. Speaker notes contain source URLs, implementation boundaries and measurement definitions.

Slide 2 uses short Key Value Proposition labels and a genuine NASA VIIRS satellite backdrop over Delhi NCR, dated 27 June 2024. The Dwarka sample cell, approaching path and future rain changes are editable illustrative annotations. They are not a measured cloud track or an output of the prediction model. The image and the slide label that distinction explicitly.

The core proposal is a 30-minute regional predictive model with an officer website and a public React Native client. The deck separates that proposed integration from working research components. It does not claim established NCR lightning accuracy, superiority to Damini or a completed open Indian benchmark.

The source reference is not included in this repository. To reproduce the candidate, use the supplied reference and the bundled `@oai/artifact-tool` 2.8.79 runtime:

```powershell
$env:CODEX_PRESENTATION_RUNTIME = 'C:/Users/dell/.cache/codex-runtimes/codex-primary-runtime/dependencies/node'
& "$env:CODEX_PRESENTATION_RUNTIME/bin/node.exe" scripts/build_sih_presentation.mjs 'C:/Users/dell/Downloads/VMD-slide2-flow-updated.pptx'
```

The builder writes a candidate, six renders and layout snapshots to the ignored `.presentation-build/` directory. Inspect each render against the source before finalizing or replacing the published deck. It requires the existing `artifacts/observed-radar.png` screenshot. Numerical measurements come from [VALIDATION.md](../VALIDATION.md) and the [recorded synthetic run](../artifacts/regional-research/d95852635db7d3a663ea160588729f78a59c61607c0e300d5d377777bee46cbc/report.json).

To reproduce revision 2 from the previous published deck:

```powershell
& "$env:CODEX_PRESENTATION_RUNTIME/bin/node.exe" scripts/revise_sih_presentation.mjs presentations/VAJRA_SIH26072.pptx
```

This writes `.presentation-build/revision2/candidate.pptx` and six slide renders. It changes slides 2 and 3, preserves the previous final deck, and uses the versioned satellite asset in `presentations/assets/`. Validate the package and layout, then finalize to a new filename. Public alert transport, mesh relay and the rolling live NCR pipeline remain deployment targets. This presentation revision does not implement backend features.

The revision builder also calls `scripts/restore_unchanged_presentation_chart.py`. The presentation runtime preserves chart formula references during export but omits their embedded workbook. The repair copies the exact original chart and workbook after checking that series values and formula ranges are unchanged. It does not invent source data. Set `CODEX_PRESENTATION_PYTHON` if the bundled Python path differs.

Revision 2 verification: all six slides rendered and were reviewed. Slides 1, 4, 5 and 6 are pixel-identical to the previous renders. The final package passed integrity, declared layout/font and first-party import checks. It contains three native tables and one editable chart with its original embedded workbook. Fourteen geometry warnings concern retained template elements, including hidden footer overlaps and conservative table bounds; the visible renders were inspected. Native Microsoft PowerPoint execution was not available. The final PPTX SHA-256 is `736182d1fc309e20eff591badd086573741853c636055ff0b271db6c45bde8d2`.

The reference has no assigned team ID, so that field stays blank. Confirm the preserved team name before submission.
