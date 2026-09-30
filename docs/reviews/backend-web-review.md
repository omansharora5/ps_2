# Gate 1 independent backend-owner review of web delivery

Review date: 30 September 2026. Attempt 1 of 3. Scope: `src/earth.jsx`, `src/earth-scene.js`, `src/image-lab.jsx`, `src/data-catalog.jsx`, `src/service-client.js` and relevant motion CSS. This reviewer implemented the backend, not these web modules. Review method: complete source inspection against the actual endpoint contracts and scientific metric definitions. Browser execution remains the web/parent lane's separate evidence.

## Material findings

1. **P2 — The image score table omits the intensity cohort.** `src/image-lab.jsx`, the “Compare on the same valid pixels” panel, reports only `metrics.selected.samples`. That count belongs to binary echo verification. MAE/RMSE exclude no-echo sentinels in selected forecast, persistence and truth and therefore use the separate `intensity_samples` cohort. Display both counts and the supplied `intensity_note` near the table. Otherwise the visible denominator suggests the image errors include misses/new echoes that they actually exclude. The endpoint already returns the required fields.

2. **P2 — Rotating after selecting a city overwrites the requested direction.** In `src/earth.jsx`, west/east handlers call `setSelected(null)` followed by `scene.current.rotate(direction)`. The subsequent `useEffect([selected])` calls `focus(null)`, and `src/earth-scene.js::focus` overwrites the target quaternion with the default India view. Consequently, the first east/west command from a selected city can become the same reset rather than the requested relative rotation. Keep clearing the selection separate from a new focus command, or coordinate rotation after the state update. Verify both directions after selecting a non-default city.

Both findings were sent to the web owner and parent; this review did not edit web files.

## Resolution check

Both findings are closed against the revised source. The image table now reports binary `samples` separately from `intensity_samples`; the nearby wording explains exclusion of no-echo values. The backend separately corrected weak positive reflectivity handling and now supplies an explicit intensity cohort and no-echo masks, preserving finite weak echoes below −10 dBZ.

City selection now calls `scene.focus(place)` directly inside `choose()`. There is no selection effect that resets a subsequent rotation. The west/east handlers clear the selection and retain their requested rotation. The regression in `tests/browser/exploration.spec.js` selects Patna, checks the rendered front-facing geographic point, rotates west, and checks that east returns the view-centre longitude to its previous value. It also exercises reduced motion, mobile width, font enlargement and the WebGL fallback. The web owner reported all four exploration browser tests passing after these fixes. This reviewer inspected the revised code and assertions; final integrated release validation remains the parent's separate gate.

## Boundaries checked without a material finding

- The globe identifies static NASA imagery and decorative clouds; selecting a city explicitly does not load a local forecast. It does not imply observed live clouds or location-specific risk.
- Reduced-motion media changes suppress automatic rendering motion and make focus transitions immediate. Explicit pause, keyboard-focus interruption, document visibility and offscreen suspension are implemented. Textual coordinates/search survive WebGL failure.
- Image inputs are identified as historical French radar, and future truth is identified as held out. Object segmentation is described as connected regions, not persistent storm tracks or lightning detections.
- Requests use the implemented image/catalog/jobs endpoints. Collection POST sends JSON `{}`, satisfying the backend content-type contract; mutation remains opt-in and direct-loopback-only on the server. File links use manifest IDs rather than arbitrary filesystem paths.
- The data view marks the starter corpus as not training-ready and reports pending source access. Catalog local status is presented as a size check, with SHA verification performed by file download; it is not labelled complete scientific validation.

No claim is made here that accessibility, browser layout or request latency has been exhaustively tested. These findings concern the specific source paths and scientific/API contracts reviewed.
