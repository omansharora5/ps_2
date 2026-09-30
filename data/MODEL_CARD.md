# Simulator model card

`synthetic-logistic-v1` is a small learned demonstration model. It has not been trained on real Indian weather. Its intended use is testing the complete fitting, inference, verification and decision-record workflow.

## Training and targets

Twenty-four synthetic event seeds, 0–23, supply training examples. Six seeds, 40–45, select temperature scaling. Six other seeds, 60–65, are reserved for testing. Each head has 15 explicit features. Model weights, feature order, targets and split identifiers are stored in `model.json`.

The convective proxy is future simulated reflectivity of at least 35 dBZ. Lightning is at least one simulated flash within an 8 km disk in the 15-minute interval ending at the forecast lead. Heads are separate for 15, 30 and 60 minutes; they are not cumulative probabilities.

Training samples pixels uniformly rather than balancing positive labels. It includes complete observations and five source-removal patterns. SGD fits binary logistic heads with regularization; validation Brier score selects one of six temperatures. No feature attribution or causal explanation is claimed.

## Model inputs

Features include translated radar and cloud fields, current radar, radar change, cloud cooling, translated/recent flashes, environmental context, four availability flags, squared radar/cloud features and a bias. Global correlation estimates motion. This is a lightweight translation method, not a complete optical-flow implementation or pysteps integration.

Missing sources are represented by unavailable arrays and explicit flags. There is no operationally fitted source-age decay law. Stale-source experiments withhold that source. Without radar, satellite and lightning, the model abstains even if NWP context remains.

## Limits

- The generator creates Gaussian moving/growing cells with simplified correlations. It does not model atmospheric dynamics, electrification, real sensor errors or realistic regional climatology.
- Temperature selection used complete-source synthetic validation. Outage-specific calibration is unestablished.
- Six test seeds are too few for a meaningful real-weather confidence interval. Pixel counts are not independent storm counts.
- The +60-minute convective-proxy head has zero CSI at the displayed 0.5 threshold on the six test events; the motion baseline scores 0.097826. The model is not uniformly better, even on its own simulator.
- Spatial edges lack upstream context. Comparison uses the shared valid mask of the available forecasts.
- A low probability is not an all-clear. The prototype is not a public-warning service.
- No first-flash lead-time, Indian domain transfer, public impact, or superiority to IMD/Damini has been measured.

`evaluation.json` records actual results, including unavailable methods and all-source failure. The real French radar mode deliberately uses separate deterministic baselines and does not load this model for inference.
