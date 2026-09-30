# Optional STLDM reference inference

This isolated command uses official STLDM source commit `49b23485734b5c00a2388febb657543afb12d6cf` and its public HKO reference checkpoint. It does not change the website, mobile app or ConvLSTM trainer.

## Design and verification scope

Two integration shapes were considered: load STLDM inside the existing image API, or run a separate reference CLI with pinned external source, explicit input metadata and outputs on disk. The CLI is selected because the current API uses two five-minute French radar frames, while this checkpoint expects five normalized HKO-shaped frames and predicts twenty. The existing endpoint's data contract is not a valid pretrained input adapter.

The evidence path is one real official-example inference using modern Torch, plus boundary tests for shape, numeric range, metadata and past/future separation. The inference environment and model cache remain separate from the app. Verification does not establish pretrained transfer skill, physical units for the supplied example, lightning probabilities or ensemble reliability. Both the actual inference and boundary tests passed.

## Setup and caller usage

Use the existing optional `.venv-ml` environment, or create a separate environment with a compatible PyTorch build. The verified dependency attempt used Python 3.14.4 and Torch 2.14.0 CPU. It added `einops==0.8.2`, `huggingface_hub==2.0.0`, `safetensors==0.8.0` and `tqdm==4.70.1`. It did not install the author's large legacy training requirements or change the root Python environment.

```powershell
.\.venv-ml\Scripts\python.exe -m pip install einops==0.8.2 huggingface_hub==2.0.0 safetensors==0.8.0 tqdm==4.70.1
.\.venv-ml\Scripts\python.exe scripts/run_stldm.py prepare
.\.venv-ml\Scripts\python.exe scripts/run_stldm.py infer --output data/training_runs/stldm-reference/cpu-example-v1 --device cpu --threads 4 --seed 17
python -m unittest tests.test_stldm_boundary -v
```

`prepare` clones the official repository under ignored `tools/stldm/`, checks out the exact source commit, and downloads pinned model configuration, licence and safetensors under ignored `data/training_runs/stldm-reference/cache/`. It verifies fixed SHA-256 identities. Repeating preparation reuses valid cached files; altered artifacts fail instead of being accepted or silently overwritten. Run output requires a fresh empty directory.

`infer` performs no network requests. It verifies the checkout and cache, loads the official model class, strictly loads safetensors, then runs one stochastic member at 20 sampling steps from the configured 50-step diffusion schedule and CFG strength 1.0. It uses the pinned constructor directly to keep checkpoint selection offline and hash-verified instead of the author's moving `from_pretrained` call. No author source files are patched. CUDA is optional and is rejected explicitly if unavailable.

The official sample has shape `[2,25,1,480,480]` and normalized float32 pixels. This bounded command selects the first example only, separates its first five images from the twenty subsequent reference images, and resizes each frame to 128 x 128 with bilinear interpolation and `align_corners=False`. Only the five past images enter the model. The future images remain separate and are resized for scoring after inference. Fixed weights return `[1,20,1,128,128]`.

Input units are `normalized_hko_reference`. The sample does not provide verified observation timestamps, availability, physical grid or coverage masks. The command refuses other metadata or units. It does not accept the app's French dBZ arrays, public lightning probabilities or live user data by silently rescaling them. Normalized image values are not meteorological probabilities.

## Artifacts and verification boundaries

Each successful run writes `predictions.npz` with the generated sequence, resized past frames and separate reference future, and `report.json` with identities, settings, dependency versions, shape, normalized MAE/MSE and a persistence comparison. These numeric image errors share finite support but have no verified meteorological coverage semantics. There is no CSI/lightning score, physical lead-time claim or calibration claim. Failed inference writes a report with the actual exception and `status=failed`; it never substitutes synthetic outputs.

The fixed checkpoint SHA-256 is `ed003bc16f59ac7f88ea5b81de8809b0ad28ceb4b0f8bd28c47907e958eafbbd`, from model revision `cdb543e4f42ee754cb88f2c15abb74f0f987c98b`. Its file is 324,054,852 bytes. The code and model repository use MIT notices; downloaded datasets and future operational inputs retain their own terms. [Official source](https://github.com/sqfoo/stldm_official), [model manifest](https://huggingface.co/api/models/sqfoo/STLDM_official/tree/main?recursive=false), [model licence](https://huggingface.co/sqfoo/STLDM_official/resolve/main/LICENSE).

Seven boundary tests cover incorrect sequence/channel layout, finite normalized-value limits, unit/scope relabeling, past/future isolation, hand-computed shared-support errors, refusal of changed cached weights, and a real CLI error that leaves a failed report without predictions. The scientific integration plan and alternatives are in [STLDM, rapid updates and controlled learning](../research/STLDM_STREAMING_AND_LEARNING.md).

Timing from this attempt is one local run while the parent also performs browser/API verification. It is not an isolated hardware benchmark, a throughput measurement or p95 latency. GPU paper timings do not describe this CPU run.

## Actual compatibility result

The real run completed on 30 September 2026 using the environment and command above, with unmodified official source and strict weight loading. Model computation took **113.386315 seconds**; the measured in-function pipeline including verification, model preparation and saving took **150.564177 seconds**. CPU peak memory was not measured. The loaded model has 80,980,769 trainable parameter elements; the provider's larger safetensors element count also includes stored buffers. Deprecation warnings concern the author's legacy AMP API; they did not prevent this run.

| Finite normalized image metric, one example | STLDM member | Persistence |
|---|---:|---:|
| MAE | 0.0226243087 | 0.0200102524 |
| MSE | 0.0081866016 | 0.0079289055 |

Both methods were scored over 327,680 image values. Persistence has lower error in this case. The result establishes that the optional integration executes, not that STLDM improves VAJRA. It provides no basis for automatically promoting the model or describing its field values as lightning probabilities.

The compact tracked [execution summary](../artifacts/stldm-reference-summary.json) includes source, checkpoint and input hashes, output hash, settings, package versions and scores. Full output remains in ignored `data/training_runs/stldm-reference/cpu-example-v1/`. No model weights or generated array archive are added to Git. A repeat with the same seed records the intended random initialization, but cross-version and cross-hardware bitwise reproducibility has not been established.
