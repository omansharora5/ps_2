# VAJRA: feasibility, viability and sustainability evidence

Research cutoff: **30 September 2026**. Scope: the proposed storm-lifecycle and data-quality-aware website/PWA, with an officer decision-support workflow and a public information view. This note supports the proposal; it does not establish operational readiness, permission to publish official warnings, customer demand or commercial returns.

**Assessment:** VAJRA is a feasible research prototype and a plausible candidate for a bounded institutional pilot. Indian operational performance and a sustainable business remain hypotheses to test. Its strongest proposed value is making storm evolution, evidence freshness, uncertainty and action history usable in an existing decision workflow. Basic weather alerts, multilingual delivery and geographic targeting already have official alternatives.

Labels used below: **external fact** means a cited source establishes the claim; **local evidence** means the repository demonstrates a bounded capability; **recommendation** means a proposed next step; **hypothesis** means a benefit or commercial assumption not yet measured.

## 1. Existing services define the adoption problem

| External fact | Implication for VAJRA — interpretation, not a claim of adoption |
|---|---|
| IMD's MAUSAM India App Store listing is free and describes observations, forecasts, radar imagery and warnings. The IMD API gateway links to its official app listings. [MAUSAM listing](https://apps.apple.com/in/app/mausam/id1522893967), [IMD gateway](https://api.imd.gov.in/public/index.php). | A subscription for ordinary public weather information needs a stronger justification than a new interface. Compare the proposed workflow with what users already use. |
| Damini's India App Store listing is free. An official MoES parliamentary answer attributes the lightning application to IITM and describes location-related lightning information and safety guidance; the parliamentary description is dated 2021. [Damini listing](https://apps.apple.com/in/app/damini-lightning-alert/id1502385645), [MoES answer, 22 December 2021](https://moes.gov.in/sites/default/files/LS-in-English-22122021-3936.pdf). | Do not claim that location-aware lightning information is novel. Historical descriptions do not establish today's precise detection coverage, forecast skill or service level. |
| NDMA's SACHET portal describes CAP-based, geographically targeted, multilingual, multi-channel disaster warning dissemination. It offers mobile location subscriptions, browser notifications and an RSS feed for agencies. [SACHET](https://sachet.ndma.gov.in/). | Position VAJRA as complementary decision support. Linking to or displaying attributed official information is different from operating an authorized public warning system. |
| DoT announced the launch of its Cell Broadcast System on **2 May 2026**, integrated with CAP-based SACHET and developed with NDMA and C-DOT. [DoT/PIB launch announcement](https://www.pib.gov.in/PressReleasePage.aspx?PRID=2257499&lang=1&reg=3). | Use the launch announcement, rather than older testing news, when describing the landscape. A PWA is not itself cell broadcast and does not acquire access to this authority-controlled dissemination channel. |

**Recommended adoption question:** Can a district officer, control-room analyst or site safety manager understand a developing storm, recognize unreliable inputs and document an appropriate decision faster and more consistently using VAJRA alongside the existing official workflow?

This question is narrower and testable. It does not assume that official services are inadequate, that users want another app, or that the prototype improves warning accuracy.

## 2. Public investment and economic evidence: use the original scope

**External fact — India:** A MoES parliamentary reply on 13 August 2026 records Mission Mausam's approved **₹2,000 crore** outlay for FY2024–25 and FY2025–26, and a **₹1,342.29 crore Budget Estimate for FY2026–27**. Its objectives include observations, AI/ML nowcasting, decision support and warning dissemination. The reply describes proposed work for 2026–31. [MoES/PIB parliamentary reply](https://www.pib.gov.in/PressReleasePage.aspx?PRID=2298819&lang=1&reg=3).

**Interpretation:** This is evidence of public investment and strategic relevance. These sums are not VAJRA's addressable market, money available to the team, grant eligibility, expenditure already incurred or evidence of an eventual contract. The overlap also raises the bar for differentiation: a generic AI forecasting dashboard is not a sufficient novelty claim.

**External fact — global economic context:** WMO attributes to the Global Commission on Adaptation's **2019** assessment an estimate that an **US$800 million** investment in early-warning systems in developing countries could prevent **US$3–16 billion in annual losses**. [WMO account identifying the 2019 report](https://wmo.int/news/media-centre/early-warning-systems-must-protect-everyone-within-five-years), [original report landing page](https://gca.org/reports/adapt-now-a-global-call-for-leadership-on-climate-resilience/).

**Scope limitation:** This is a broad estimate for early-warning systems, including the observing, forecasting, communication and response chain. It is not measured VAJRA ROI, an Indian thunderstorm-specific benefit estimate, or evidence that a short-lead software forecast produces a particular reduction in deaths or damage. Do not apply it to a proposed subscription price or multiply it by project spending.

**External fact — implementation context:** The UNDRR/WMO 2025 global report links effective warning systems to warning reception, understanding, trust and action, with attention to local participation, accessible communication and sustained support. Its international comparisons of warning coverage and mortality are associations; they do not identify VAJRA's causal effect. [Global Status of Multi-Hazard Early Warning Systems 2025](https://www.undrr.org/reports/global-status-mhews-2025).

**Recommended use in a presentation:** Cite this evidence to establish why an end-to-end warning workflow matters, then show VAJRA's own measured contribution separately. Avoid borrowing national or global benefits as product results.

## 3. Indian data access and integration are feasibility gates

| Input or interface | Verified constraint | Minimum next step for an Indian pilot |
|---|---|---|
| IMD machine-readable services | The official gateway exposes registration and login for observation, forecast, warning and bulletin services. A public app or radar picture does not establish access to raw historical radar volumes or a bulk production feed. The earlier project audit recorded an unauthenticated district-nowcast request returning HTTP 401; this is a point-in-time access result, not proof every endpoint is closed. [IMD gateway](https://api.imd.gov.in/public/index.php), [dataset audit](DATA_SOURCES.md). | Identify exact datasets, credentials, authorized use, history, cadence and availability expectations. Demonstrate successful retrieval before promising live integration. |
| MOSDAC satellite products | Approved registration is required for downloads; the API manual states a maximum of **5,000 files per user per day**. [MOSDAC download API manual](https://www.mosdac.gov.in/downloadapi-manual). | Select specific product IDs and account entitlements; measure end-to-end latency and storage. A download quota is not an availability guarantee. |
| MOSDAC use and redistribution | The December 2020 guidelines distinguish public browse images from registered products; near-real-time privileges are considered case by case. They restrict raw-data resale/redistribution, discuss value-added products and industry use, permit charges for customization, and describe supply on a best-effort basis. [MOSDAC guidelines](https://www.mosdac.gov.in/look/DOCS/mosdac-data-guidelines_english.pdf). | Record the exact product terms before redistributing inputs or selling derived services. Public visibility does not mean unrestricted reuse. |
| Product-specific satellite restrictions | The inspected `3RIMG_L2C_CMP` product page includes research/noncommercial wording, illustrating why broad portal policy should not be treated as blanket commercial clearance for every product. [Product DOI page](https://www.mosdac.gov.in/doi/194/), [dataset audit](DATA_SOURCES.md). | Resolve any conflict with the provider for the actual products and intended deployment. This is a documentation requirement, not a legal conclusion about all MOSDAC data. |
| Indian radar and lightning labels | The repository has no demonstrated authorized Indian operational radar-plus-lightning feed or sufficiently representative Indian validation corpus. Foreign radar replay and synthetic lightning targets cannot establish Indian lightning skill. [Dataset audit](DATA_SOURCES.md), [project scope](../README.md). | Secure time-aligned Indian observations and independently observed labels, with quality flags and sufficient events, quiet periods, seasons and locations. |
| Official CAP warning consumption | SACHET publishes an agency guide for fetching CAP XML. It requires ETag caching and subsequent `If-None-Match` requests, with HTTP 304 reusing cached XML. [SACHET integration guide](https://sachet.ndma.gov.in/docs/Integration_Guide_For_Agencies.pdf). | Implement a documented consumer with source, identifier, issue/expiry times, updates/cancellations and caching. Verify the discovery/feed process separately; knowing an XML URL pattern is not a complete integration. |
| Public dissemination | Consumer integration documentation does not establish authority to originate official alerts or permission to use government telecom dissemination. [SACHET integration guide](https://sachet.ndma.gov.in/docs/Integration_Guide_For_Agencies.pdf), [DoT launch announcement](https://www.pib.gov.in/PressReleasePage.aspx?PRID=2257499&lang=1&reg=3). | Keep model output, official warnings and human decisions separately attributed. Agree operator responsibilities and permitted dissemination before a public pilot. |

**Recommended minimum viable data package:** For one agreed Indian region, obtain the model's required observation stream, a historical archive with timestamps and missing-data flags, and independent outcome labels. A rainfall model needs observed rainfall/reflectivity verification; a lightning model needs observed lightning labels. Add satellite and NWP inputs only when access, alignment and incremental value are demonstrated. An official CAP consumer can provide contextual warnings; CAP messages alone are not dense sensor observations or exhaustive ground truth.

If these requirements cannot be met, the credible deliverable remains a clearly labeled replay, training and decision-workflow tool. It should not be presented as an operational Indian AI nowcaster.

## 4. Recommended business model, with untested assumptions exposed

| Proposed route | Buyer, operator and beneficiary | Possible paid value | What remains untested |
|---|---|---|---|
| **B2G or public-institution pilot first** | Potential buyer: disaster-management or public-institution program owner; operator: authorized analyst/control room; beneficiary: exposed communities. | Integration, storm review workflow, input-quality monitoring, local training, audit exports and supported operation. | Actual procurement route, budget holder, workflow gap, data partnership, approval time, ownership and willingness to fund recurring support. No contract is established. |
| **Selective B2B site operations** | Potential buyer: a weather-exposed site or event operator; operator: safety manager; beneficiary: workers/visitors. | Site-specific review queues, response checklists, evidence receipts and integration with existing operational procedures. | Whether these features improve decisions enough to justify payment compared with official information and existing vendors. Safety thresholds must be agreed by competent operators. |
| **Free public information layer** | Beneficiary: residents; funding source could be institutional service revenue or a separately funded public program. | Attributed official information, accessible explanations, source freshness and links to local guidance. | Sustainable funding and whether users understand the difference between official alerts, model estimates and unavailable information. |

These are **recommendations**, not discovered customers or a validated market. Do not invent TAM/SAM/SOM, paying customer counts, prices, sales-cycle duration, conversion rates or ROI. Grants, competitions and CSR support can fund development if secured; they are not evidence of recurring operating revenue.

**Recommended willingness-to-pay test:** Interview prospective budget holders and actual operators separately. Observe their current workflow and record which decision is delayed, duplicated or poorly documented. Run a bounded replay/shadow evaluation against that workflow. Agree deliverables, data permissions, operator training and recurring responsibilities before any paid pilot. After the pilot, obtain a real renewal or procurement decision rather than treating positive feedback as demand.

The saleable unit, if validated, is a supported institutional workflow with documented service responsibilities. A new public alert app alone offers weak differentiation against existing free services.

## 5. Feasibility and operational risks

| Risk | Practical mitigation and decision gate — proposed |
|---|---|
| Data permission, latency or continuity fails | Store provenance and product terms; measure source age and gaps; expose degraded/unavailable states. Do not promise a live region until its required feed works consistently. |
| Foreign/synthetic performance fails to transfer | Use event-disjoint Indian evaluation, seasonal/geographic holdouts and operationally available inputs. Compare with persistence/advection and existing practice. Stop accuracy claims if incremental skill is absent. |
| A missing sensor is interpreted as no hazard | Make missingness visible; distinguish no detection from no valid observation. Test failure states and suppression of unsupported forecasts. |
| Uncalibrated probabilities or arbitrary action thresholds | Calibrate on representative held-out observations and assess reliability by lead time. Agree action thresholds with the responsible operator, including the costs of misses and unnecessary shutdowns. |
| Human review becomes a bottleneck | Measure review time and queue load during multi-cell events. A storm-lifecycle view should reduce repeated interpretation, but that advantage requires testing. |
| Role confusion or stale offline information | Clearly distinguish official warning, experimental forecast, human decision and historical receipt. Offline shell availability is not a fresh weather feed. |
| Delivery failure, digital exclusion or language misunderstanding | Test acknowledgement and comprehension with intended users. Fit institutional communication channels and local-language workflows; do not assume a PWA reaches every person at risk. |
| Prototype is exposed as a production service | Add authentication, authorization, secrets management, audit access, backup/restore, incident response and load monitoring before multi-user deployment. Current presentation views do not establish access control. |
| Project ends after demonstration | Name an operating owner, budget maintenance and retraining, document handover, retain exportable records, and establish support/renewal arrangements before expansion. |

The 2026 UNDRR/ITU guidance on AI in multi-hazard early warning emphasizes human oversight, interoperability, inclusion and sustained institutional capability. These support the proposed safeguards; citing the guidance does not establish that VAJRA has implemented them or achieved certification. [Leveraging AI to enhance multi-hazard early warning systems](https://www.undrr.org/publication/documents-and-publications/leveraging-ai-enhance-multi-hazard-early-warning-systems).

## 6. Impact: separate measured capability from proposed benefit

Local evidence below is bounded by the repository's documented scope. See [README](../README.md) and [validation record](../VALIDATION.md) for current results; this note does not introduce new scores.

| Area | Demonstrated or currently measured | Proposed pilot measure; not yet an impact result |
|---|---|---|
| Forecast computation | Synthetic fusion workflow and real French radar replay with computed verification. | Indian event-disjoint skill by hazard, region and lead time; probability calibration and comparison with simple baselines. Foreign radar scores do not measure Indian lightning performance. |
| Input quality | Sensor-failure experiments and explicit quality information in the prototype. | Fraction of forecasts with valid inputs; source-age percentiles; stale-input detection delay; behavior under outages; misses attributable to data gaps. |
| Decision traceability | Saved run/decision receipts. | Fraction of reviewed events with a complete source/model/decision record; time to reconstruct why an action was taken. |
| Officer usefulness | A reviewable interface and workflow exist. No representative operator study is established here. | Task-completion rate, review-time distribution, comprehension of uncertainty and decision consistency versus the existing workflow. |
| Response | No validated live public-warning or acknowledgement outcome. | Receipt-to-acknowledgement time, comprehension, action initiation and completion; examine missed events and unnecessary actions as well as successes. |
| Community/economic benefit | No attributable lives-saved, injuries-avoided or loss-reduction estimate. | Prospectively defined outcomes with a credible comparison design; distinguish reported actions from causally attributable avoided losses. |

Recommended evaluation design: agree the questions and metrics before examining results, preserve independent events as the test unit, report failures and subgroup coverage, and include uncertainty where the event count permits it. Raw accuracy or the number of notifications is insufficient evidence of useful early warning.

## 7. Resource and sustainability plan

**Recommended operating-cost model:**

`Recurring cost = data access + ingestion/storage/egress + inference + monitoring/backup + delivery + operator/support time + maintenance/security + evaluation/retraining`

All terms need measured usage and actual provider or partner terms. Free downloads do not remove compute, stewardship, support or reliability costs. No monthly price or cost-saving claim is established in this note.

| Resource or sustainability dimension | Current evidence | Proposed measurement and control |
|---|---|---|
| Compute | A local prototype runs; no production capacity or energy claim follows. | Record CPU/GPU type, peak memory, inference p50/p95 duration, forecasts per hour and actual billed usage. Benchmark a simple baseline before choosing a larger model. |
| Data transfer | SACHET documents conditional HTTP caching; MOSDAC documents a file quota. | Measure bytes downloaded per update and per valid forecast; use ETags, incremental retrieval and bounded regional products where permitted. Report observed savings only after comparison. |
| Storage | Local saved runs and data artifacts exist. | Measure growth per day, retention needs, backup size and restore time; separate source retention obligations from optional visualization caches. |
| Energy and emissions | No measured energy or carbon footprint. | Measure energy where instrumentation permits; disclose hardware, workload and any emissions-factor source. Smaller models and caching are efficiency hypotheses, not proof of carbon neutrality. |
| Financial continuity | No verified recurring revenue or funded operational SLA. | Track actual monthly cost, support hours, paying institutional commitments and renewal decisions. Scale only when responsibilities and recurring funding are credible. |
| Social sustainability | Public information and PWA views exist; accessibility and comprehension in target communities remain to be evaluated. | Test local-language understanding, low-connectivity behavior and assisted/offline institutional workflows. Keep essential public information accessible under the proposed funding model. |
| Institutional continuity | Research and provenance records are present. | Assign data/model/product owners; maintain versioned models, reproducible evaluation, handover instructions and incident reviews. |

Sustaining an early-warning service requires financing and institutional capacity beyond initial installation; UNDRR's 2025 Global Platform addressed these explicitly. This is policy guidance supporting an operating plan, not a project cost estimate. [UNDRR session on sustaining early-warning investment](https://globalplatform.undrr.org/2025/conference-event/ts6-solutions-scaling-and-sustaining-investments-multi-hazard-early-warning).

## 8. Evidence gates for a credible proposal

1. **Research demonstration:** explain the current synthetic and French-radar scope; show sensor failure and the evidence receipt. This is the current credible demonstration level.
2. **Indian shadow pilot:** obtain authorized inputs and independent labels; run without autonomously issuing public warnings; measure forecast and workflow performance against agreed baselines.
3. **Supported institutional deployment:** proceed only with demonstrated value, accountable operators, access control, documented data rights, monitoring and funded maintenance.
4. **Wider public service:** assess dissemination authority, reliability, comprehension, inclusive access and response capacity separately from model quality.

**Defensible proposal wording:** “VAJRA proposes storm-lifecycle decision support that makes evidence freshness and uncertainty visible and preserves a reviewable action record. The prototype demonstrates the workflow; Indian operational skill, adoption, recurring costs and willingness to pay will be established through an authorized institutional pilot.”

**Claims not supported by this research:** first-ever AI nowcasting; free unrestricted access to all Indian weather data; official warning authority; guaranteed nationwide delivery; validated Indian lightning prediction; a specific percentage reduction in deaths/losses; carbon neutrality; a market size inferred from Mission Mausam; or project ROI inferred from global early-warning economics.
