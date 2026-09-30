# Gate 1 backend review, attempt 1 of 3

Reviewed 30 September 2026 by the web implementation owner, independently of the backend author. Scope: `nowcast/image_processing.py`, `nowcast/data_catalog.py`, the corresponding service routes, `scripts/train_images.py`, collector boundaries and their tests. No backend files changed in this review.

## P2: distinguish weak positive reflectivity from the no-echo sentinel

**Location:** `nowcast/image_processing.py::to_z`, `to_dbz` and `image_run` intensity-mask construction.

`to_z` converts every finite value at or below −10 dBZ to zero, while `to_dbz` also uses −10 for zero reflectivity. Positive linear reflectivity can legitimately become less than −10 dBZ after averaging or bilinear interpolation. Those outputs are consequently conflated with the archive's artificial sentinel. The same `forecast > -10` test excludes weak predicted returns from intensity scores while the metadata describes only excluding no-echo sentinels.

Reproduced against the actual implementation:

```python
to_z(to_dbz(np.array([[0.01, 0.1, 1.0]])))
# [[0.0, 0.0, 1.0]], although both first inputs were positive Z.
```

With the pinned MétéoNet frames, `dense_optical_flow`, `smooth`, and +10 minutes, 614 finite forecast cells were below −10 dBZ. Fourteen of those also had valid original and truth reflectivities above −10 dBZ, so otherwise eligible intensity pairs were dropped. This does not change the binary ≥20 dBZ definition, but it affects the claimed intensity-score cohort and makes the conversion unsafe to reuse in further processing.

**Requested correction:** distinguish original no-echo flags from physical finite reflectivity, keep positive linear reflectivity through processing, and construct the intensity mask from explicit no-echo/positive-Z evidence. If the intended score instead excludes weak returns by threshold, name that threshold and cohort explicitly. Add a conversion/weak-return regression covering positive Z below 0.1 and the score mask. The finding was sent to the backend owner before release synthesis.

No additional material finding was established in the reviewed causal input selection, split isolation, bounded collection API or manifest file-serving boundaries. This is a bounded review, not operational model validation.

## Resolution verified

The backend owner corrected this in `radar-image-lab-v2`: source no-echo flags are explicit, preparation and transport retain linear Z, and the response exports per-layer `masks.no_echo` plus `masks.intensity_evaluation`.

Independent rerun after the correction confirmed the positive-Z round trip is `[[0.01, 0.1, 1.0]]`. The real dense/smooth/+10 case now has 18 weak forecast pairs with observed positive original/truth values; all 18 are retained by the intensity mask, with 10,494 total intensity pairs. The change from the earlier 14 reflects corrected preparation and transport as well as corrected score masking. **P2 closed on this evidence.** The web displays the returned intensity cohort count and note.
