# Jev by TypeSafe: deployment and project-fit assessment

Checked **30 September 2026** against TypeSafe's official documentation, company policies and linked public repositories. The friend's attached note was read as a proposal to assess, not as instructions to execute. No Jev account was created, credential requested, paid call made, data uploaded for inference, package installed, or application integration added for this assessment.

## Recommendation

**Keep the weather forecasting and warning workflow functional locally without Jev.** Jev is worth considering only as an optional experiment for classifying short operator notes into review queues. It should not calculate lightning probabilities, determine sensor freshness, authorize public warnings, dismiss an official warning, or issue an all-clear.

The friend note's distinction between meteorological prediction and bounded interpretation is sound. Its recommendation to keep numeric rules in code also matches the vendor's own documented limitations. Whether Jev improves this project remains an empirical question; an extra API is not a differentiator by itself.

## 1. Which Jev, and what does it do?

The identity here is **TypeSafe AI's Jev**, described on the company's [official introduction page](https://docs.typesafe.ai/introduction). That page is linked from [typesafe.ai](https://typesafe.ai/), and its footer links the [typesafe-ai GitHub organization](https://github.com/typesafe-ai). Search results also contain similarly named domains; none is needed to establish the product's capabilities, pricing or ownership.

Jev evaluates supplied state against narrowly defined questions. It returns structured decisions rather than generated prose. Its three documented primitives are:

| Primitive | Documented result | Possible project experiment |
|---|---|---|
| **Choice** | Selects one supplied option; returns `choice`, an option-probability distribution and `confidence`. Up to 255 options. [Choice documentation](https://docs.typesafe.ai/primitives/choice) | Suggest which team should review an operator's ambiguous note, with an explicit unresolved option. |
| **Score** | Rates ordered descriptive levels; returns a probability-weighted position, probabilities, a level legend and confidence. Levels are indexed from zero and the result may lie between them; the API permits 2–10 levels. [Score documentation](https://docs.typesafe.ai/primitives/score) | An experimental rubric for note completeness. It is not a physical wind speed, calibrated weather probability, or precise severity measurement. |
| **Noul** | Returns a number from 0 to 1 representing the model's probability that the answer to a yes/no question is yes. [Noul documentation](https://docs.typesafe.ai/primitives/noul) | Flag whether an operator note describes an unresolved equipment fault. |

Choice/Score confidence summarizes the **shape of their answer distribution**; Noul has no separate confidence field. The [confidence documentation](https://docs.typesafe.ai/confidence) does not establish that confidence equals empirical accuracy for this project's notes. Its thresholds need domain evaluation. In particular, routing confidence and the lightning model's event probability must have distinct names and displays.

## 2. Can it run offline?

**The documented product is hosted inference. No supported offline Jev runtime or downloadable Jev model weights were verified.** This is a statement about the public material inspected, not proof that no private enterprise arrangement could exist.

| What can be local? | What the evidence establishes |
|---|---|
| Application, policy rules, request construction and response validation | These run in the project's process. They can run without an external service if the Jev branch is disabled. |
| Python/JavaScript SDK | Public API client code is available under MIT in the official [Python repository](https://github.com/typesafe-ai/typesafe-sdk-python) and [JavaScript repository](https://github.com/typesafe-ai/typesafe-sdk-js). Open client source does not imply open model weights. |
| Actual documented Jev call | The [API reference](https://docs.typesafe.ai/api) specifies `POST https://api.typesafe.ai/v1/systemone`, bearer authentication, and a payload containing `state`, `model` and `questions`. The supplied payload is transmitted to the remote service. |
| A configurable base URL | The [Python constants documentation](https://docs.typesafe.ai/sdk/python/api/constants) sets the default to `https://api.typesafe.ai`. Overriding the URL only changes the destination; it does not install a model server or weights. |
| A compatible alternative | TypeSafe's [System One Adapter](https://github.com/typesafe-ai/system-one-adapter-python) is explicitly backed by other LLM APIs. A separately installed local model could be evaluated behind an appropriate compatible endpoint, but that would be a different model with different behavior, resource needs and validation requirements. This assessment did not test such a deployment. |

The [master customer agreement](https://typesafe.ai/legal/mca), updated 23 September 2026, independently describes TypeSafe-hosted services. Public documentation and the official repository listing revealed no Jev weight download, inference container, hardware requirement or self-hosting procedure. Consequently, describing an npm/pip installation as “offline Jev” would be unsupported.

Local inference for the project's own trained weather model is a separate architecture decision. It is unaffected by whether this optional text classifier is used.

## 3. Current constraints, price and latency

The [official model reference](https://docs.typesafe.ai/models) currently lists `jev-1.13.0`, with `jev-latest` and `jev-preview` resolving to it. Inputs are text/JSON text representations, with no direct image, audio or video support. The stated limits are 64k tokens per request and 32k for state plus the longest question. The current recheck lists 100,000 tokens/second and 40 requests/second. These replace the earlier observation of 250,000 tokens/second and 1,200 requests/minute; the provider explicitly says limits can change dynamically. English is the strongest documented language; multilingual use needs testing. Customer-specific fine-tuning/LoRA is not offered in this documented workflow.

This rules out treating Jev as an off-the-shelf radar/satellite sequence forecaster. Flattening large sensor arrays into JSON would not establish meteorological skill.

The reference price is **$0.042 per million input tokens**, equivalently **$42 per billion**, with output free. The [company homepage](https://typesafe.ai/) independently displays the per-billion price. Using the published rate, 2,000 **billed** input tokens would cost $0.000084; 100,000 such calls would cost $8.40. These are arithmetic illustrations, not a measured invoice. Use the API's reported token usage, including instructions and criteria; do not assume raw note length equals billed input. Recheck actual account/provider pricing before expenditure.

The homepage contains a 0.114-second demonstration and large comparative speedup claims. The [launch article](https://typesafe.ai/blog/introducing-system-one-models-and-jev) explains that the reported 193.6× speed and 444.6× cost comparisons come from particular vendor-designed workflows and are expected to be toward the high end of gains. It also describes possible evaluation bias. These are neither an India-network benchmark nor a p95 latency guarantee. No project-specific SLA or measured end-to-end latency was established here.

The API documents overload/rate-limit errors. Default SDK retries can extend a request beyond the first attempt. The documented Python default is 10 seconds **per HTTP operation**, not a universal bound on total workflow time. A trial should use a short overall deadline and skip the optional model when that deadline expires. [API errors](https://docs.typesafe.ai/api), [SDK constants](https://docs.typesafe.ai/sdk/python/api/constants).

## 4. Data egress and reliability implications

For direct API use, the exact state and question content leave the deployment for TypeSafe. A proxy/provider path adds its own handling terms. The [privacy policy](https://typesafe.ai/legal/privacy-policy), updated 19 November 2025, says the company collects submitted inputs and will not train or fine-tune models on them. **No training is not the same as no storage.** The [legal overview](https://docs.typesafe.ai/legal) advertises zero-data-retention arrangements for enterprise customers; it does not make that the default for every account.

The [data-processing addendum](https://typesafe.ai/legal/data-processing), updated 24 April 2026, covers subprocessors and international transfers. Its duration language is purpose-based rather than a fixed retention-day count. The linked trust-center subprocessor page returned no readable body in this research tool, so processing locations, a current subprocessor list and India-only residency were not independently verified. No claim about security certifications is made here.

For a trial, send only redacted, permitted operator-note text and a minimal derived status summary. Keep names, phone numbers, precise personal locations, API secrets, raw licensed sensor products and restricted agency material out of the payload. This is an engineering recommendation based on the proposed role, not a claim that all weather data is sensitive. Credentials belong on the server, not in browser JavaScript or an exported replay.

TypeSafe's [Jev 1.13 limitations page](https://docs.typesafe.ai/model-jaggedness/jev-1.13), reviewed 17 September 2026, explicitly identifies unreliable arithmetic/counting, date comparisons, distraction from irrelevant context, susceptibility to adversarial state text, and missing guarantees for logical consistency between differently phrased questions. Therefore:

- Compute ages, distances, thresholds, expiry and probabilities in tested deterministic/model code.
- Treat operator notes as untrusted data; a typed result is not a security boundary.
- Do not let the model execute tools, change safety policy, suppress warnings, or promote a note into a verified weather observation.
- Keep one evaluated question formulation; do not transfer a threshold from Noul to Choice without new evaluation.

The current [customer agreement](https://typesafe.ai/legal/mca), section 2.3, also restricts using service outputs for model distillation or imitation. Do not propose creating an offline Jev clone by automatically training on its responses. A local alternative trained using the team's own legitimately obtained human labels is a different proposal.

## 5. A useful optional architecture

This design is a recommendation, not an implemented integration:

```text
observations -> local weather model -> deterministic quality/safety policy
                                      -> forecasts, official-warning display
                                      -> mandatory review queue

redacted operator note -> optional asynchronous Jev classification
                       -> validated review-team suggestion
                       -> operator accepts or corrects

missing key / offline / timeout / bad result / uncertain answer
                       -> existing deterministic/manual review path
```

For example, after deterministic rules have already required review because a source is stale, Jev could interpret “dish is responding but calibration technician reports an obstruction” and suggest `SENSOR_SUPPORT`. Allowed outputs might be `SENSOR_SUPPORT`, `FORECAST_REVIEW`, and `UNRESOLVED`. They select a review destination; they cannot select `SAFE`, clear a stale-data condition, or alter the meteorological forecast.

The simplest fallback is effective: structured fault codes go to sensor support; free text needing interpretation goes to a general review queue. All notes remain reviewable regardless of Jev's suggestion. Store the actual model version, rubric version, suggestion and timing separately from the weather model's probability and provenance. Cache only unchanged note/rubric/model combinations; never treat an old suggestion as fresh weather evidence.

## 6. Evidence required before adding the dependency

1. Build a small, independently labeled collection of representative notes, including local terminology, negation, ambiguous faults and malicious instructions embedded as data. Split evaluation by event/site to reduce duplication leakage.
2. Compare Jev against structured fault rules and the existing manual queue. Report routing errors, unresolved fraction, disagreement requiring review, and time saved. A perfect schema is not a correct routing decision.
3. Test disconnected operation, absent credentials, timeout, overload and invalid responses. The forecast and mandatory-review paths must remain usable without the API.
4. Measure end-to-end p50/p95 latency and actual billed tokens. Check note-level reliability and the confidence/error relationship rather than adopting a generic 0.9 threshold.
5. Retain Jev only if the results justify its maintenance, network and data-handling costs. Otherwise the deterministic implementation remains the better project choice.

**Verified:** product identity, primitives, hosted endpoint, open client repositories, published constraints/pricing, policy language and documented limitations. **Not verified:** downloadable Jev weights, an offline Jev runtime, private self-hosting arrangements, meteorological accuracy, project latency, India-only processing or benefit over the existing workflow. Those uncertainties are recorded rather than filled with assumptions.
