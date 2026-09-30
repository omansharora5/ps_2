# SIH26072: problem evidence, existing services, and user needs

Research date: **29 September 2026**. This note separates verified observations from design proposals. It does not establish operational forecast performance, conduct interviews, or claim that the proposed system is unprecedented.

## 1. What the organizer actually asks

The official [SIH 2026 problem statement portal](https://www.sih.gov.in/sih2026PS), HTML modal `ViewProblemStatement26072`, was retrieved successfully using direct HTTPS on the research date. Its title is:

> AIML based Nowcasting of thunderstorm and lightning using atmospheric observation including multiple radars, satellite, lightning and model data.

The description repeats that title. The row identifies **Ministry of Earth Sciences**, **India Meteorological Department**, **Software**, and **Disaster Management**. The dataset and contact fields were empty when inspected. This confirms the supplied Markdown's statement identity. The portal does not specify a neural architecture, accuracy target, spatial resolution, forecast horizon, prototype region, dataset entitlement, or user interface.

The web extraction service initially failed on the portal; a separate direct-HTTP retrieval returned HTTP 200 and exposed the actual statement table. Therefore the identity is primary-source verified, rather than inferred from [the VUCE mirror](https://sih2026.vuce.in/). Search-engine copies and third-party popularity estimates are unnecessary to establish scope. Submission counters and deadlines are volatile and are not used as research evidence.

**Interpretation:** the hard requirement is a forecasting system that combines complementary observations. The product should answer what convective/lightning hazard may occur, where, over which future interval, and with what uncertainty. Alert delivery is valuable, but by itself it does not fulfill the forecasting requirement. Choices such as a 0–120-minute horizon, 5-minute output intervals, one-region prototype, storm tracking, and an operator console are proposed design decisions, not organizer mandates.

## 2. The problem as experienced by a user

An illustrative field supervisor has workers spread across outdoor sites. A broad warning does not settle whether a particular team should stop now, whether the warning is still current, how long it takes to reach a suitable shelter, or whether anybody acknowledged the instruction. An IMD forecaster faces a different problem: asynchronous inputs, moving and developing convection, conflicting evidence, and the need to explain an uncertain recommendation. These are **design scenarios**, not fabricated interviews.

There is primary evidence for communication and response difficulties. A [MoES workshop reported by PIB on 28 June 2021](https://www.pib.gov.in/PressReleasePage.aspx?PRID=1730978&lang=2&reg=48) explicitly identified last-mile communication as a problem despite improved monitoring and prediction. This establishes the relevance of dissemination; it does not prove every present-day app fails or quantify nationwide warning receipt.

Treat the full chain as the product:

```text
usable observations -> forecast with uncertainty -> official/operator decision
     -> intelligible local instruction -> acknowledgement -> protective action
     -> event verification and service improvement
```

The proposed system must measure the forecasting and action links separately. A sent SMS is not a person reached; a received alert is not a person sheltered; a successful drill is not a demonstrated reduction in mortality.

## 3. Quantitative evidence and its limits

| Claim suitable for a presentation | Reporting period and exact scope | Primary source and access status | Confidence and qualification |
|---|---|---|---|
| India recorded **2,357**, **2,876**, and **2,862** accidental deaths due to lightning in 2018, 2019, and 2020 respectively. | All-India annual totals, NCRB data supplied by States/UTs. | [PIB/MoES, 1 December 2021, Annexure I](https://www.pib.gov.in/Pressreleaseshare.aspx?PRID=1776751&lang=2&reg=48); full table read. Cross-check located in [Rajya Sabha response, 3 February 2022](https://www.moes.gov.in/sites/default/files/RS-in-English-183-02032022.pdf), whose older URL is intermittently unavailable. | High for the historical series. Do not present this as the latest annual count. It is administrative reporting, not a complete census of every injury or death. |
| **2,887 of 8,060 (35.82%)** deaths attributed to forces of nature in 2022 were due to lightning; the corresponding 2021 figures were **2,880 of 7,126 (40.42%)**. | National annual lightning category and total **forces-of-nature deaths**, reproduced from NCRB. | [MoSPI EnviStats India 2024, Vol. I, paragraph 4.6 / Statement 4.08](https://www.mospi.gov.in/sites/default/files/reports_and_publication/statistical_publication/EnviStats/Complete_ES1_2024.pdf), printed p. 200 / PDF p. 215. Full PDF downloaded into memory and table parsed by a second access method. | High for the dated series. The same table independently agrees with the 2018–2020 PIB totals. The denominator is neither all accidental deaths nor all deaths in India. Publication year 2024 does not make these 2024 deaths. |
| IMD's 2024 event compilation reports **1,643 human deaths**, **1,038 injuries**, and **8,899 livestock deaths** in its combined lightning/thunderstorm category. | Calendar 2024, **“Lightning associated with Thunderstorm and Thunderstorm”**, Table 23, printed page 187. | [IMD, Disastrous Weather Events 2024](https://imdpune.gov.in/library/public/DWE_2024.pdf); source table available in the search index; live host timed out during recheck. | Medium until a local copy of the primary PDF is retained. Combined event category and reporting method differ from NCRB lightning-only totals. Do not merge the series or infer a percentage decline. |
| Within that same IMD 2024 table, Bihar records 322 deaths, Madhya Pradesh 293, Uttar Pradesh 225, and Odisha 208. | The same combined hazard category, not all natural disasters. | Same IMD Table 23. | Candidate prioritization evidence only. A prototype location also needs data access and a willing operational partner. These counts alone do not establish a per-capita risk ranking. |
| IMD reported **1,211 nowcast stations** as of December 2025. | Status table comparing December 2014 and December 2025. | [PIB/MoES parliamentary answer, 11 February 2026](https://www.pib.gov.in/PressReleasePage.aspx?PRID=2226187&lang=2&reg=48), Annexure I; full text read. | High for the dated statement. Does not mean 1,211 radars, prediction grid cells, or all villages covered with equal forecast skill. |
| Mission Mausam has an approved **₹2,000 crore** cost for 2024–2026. | Government programme cost, not this project's budget or market size. | [PIB parliamentary answer, 31 July 2025](https://www.pib.gov.in/PressReleasePage.aspx?PRID=2150830&lang=2&reg=48); full text read. | High. Supports policy alignment with improved observations, AI/ML, decision support and last-mile services; does not imply project funding. |
| Early-warning coverage is associated with much lower disaster mortality. | WMO's 12 November 2025 statement describes disaster-related deaths as approximately six times lower where coverage is good. | [WMO report-launch statement](https://public.wmo.int/content/opening-remarks-setting-scene-collective-progress-toward-early-warnings-all); cross-check: [WMO/UNDRR 2025 report](https://www.undrr.org/reports/global-status-mhews-2025). | Strong global evidence for the value of warning systems; observational cross-country comparison, not this prototype's causal effect. |
| Global assessments estimate 24 hours of warning can reduce damage by around 30%; $800 million invested in developing-country early-warning systems could avoid $3–16 billion annually. | Broad multi-hazard economic estimates, not lightning-only nowcasting. | [UNEP climate information and early warning overview](https://www.unep.org/topics/climate-action/climate-transparency/climate-information-and-early-warning-systems); cross-check: [WMO EW4All brochure](https://wmo.int/sites/default/files/2025-10/FINAL%20VERSION%20-%20EW4All%20Brochure.pdf). | Useful context, poor project KPI. Do not transfer the 24-hour estimate to a 30-minute lightning warning or promise 30% savings. |

### Numbers not promoted to verified facts

- Later news coverage reports NCRB lightning totals for 2023 and 2024, but the retrieved reports disagree on the 2023 count (2,558 versus 2,560). The [official ADSI 2023 catalog](https://www.data.gov.in/catalog/accidental-deaths-suicides-india-adsi-2023) was confirmed, but the exact lightning table was not recovered here. Keep the newer values out of headline claims until the relevant original/revised NCRB tables are downloaded and versioned.
- Claims such as “96% of victims are rural” and “77% are farmers” must not be attributed to government merely because they appear in a parliamentary **question**. The [MHA answer of 27 July 2022, question 1184](https://www.mha.gov.in/MHA1/Par2017/pdfs/par2022-pdfs/RS27072022/1184.pdf) says the ministry does not maintain that centrally segregated dataset; it does not confirm the question's percentages.
- A [27 November 2025 announcement](https://www.moes.gov.in/sites/default/files/PIB2195385.pdf) and the February 2026 parliamentary annexure contain inconsistent language around the current radar count/expansion target. Do not repeat “126 operational radars” without resolving commissioned versus planned infrastructure.
- There is no verified evidence here for a universal percentage rise in lightning caused by climate change. Detection-network expansion, event definition, period and geography matter. Avoid converting a regional finding into a national causal claim.

## 4. Actual survey evidence

The IMD monograph *Expectation and Utilization Behaviour of the Intermediate Users of Weather and Climate Services in India* reports **515 responses** collected **5 January–28 February 2021**, using a Google Form distributed through IMD offices. Respondents included government and nongovernment intermediaries and media; 371 were government and 144 nongovernment. In the multi-select hazard-needs question, **511** answered; **63.4%** selected lightning and **67.1%** thunderstorms. Roughly half considered poor communication of forecast uncertainty an obstacle to appropriate response. These are reported preferences, not measured forecast errors. [Author-uploaded primary monograph, January 2022](https://www.researchgate.net/publication/359699450_Expectation_and_Utilization_Behaviour_of_the_IntermediateUsers_of_Weather_and_Climate_Services_in_India).

This was an online intermediary survey, not a representative sample of rural households or all Indian farmers. Selection bias and older service capabilities limit present-day generalization. IMD's [2022 annual report](https://metnet.imd.gov.in/docs/imdnews/ANNUAL_REPORT2022English.pdf) independently lists the monograph under report number `MoES/IMD/ASSD/FR/01(2022)/03` with the related “Information seeking...” title. The author copy uses `AASD` in its number; retain this bibliographic inconsistency rather than silently changing it.

**What this supports:** displaying uncertainty, clear action wording, and operator/intermediary workflows deserve user testing. **What it does not support:** claims that half of farmers ignore warnings, that Damini has a particular miss rate, or that the new app will save a quantified number of lives.

### User research still to conduct

No new interviews were conducted for this report. A practical initial discovery sample is 6–8 outdoor workers, 3–4 supervisors or teachers, 2 district disaster-management staff, and 1–2 meteorologists; these are proposed sample targets, not results. Ask about the last actual warning, its source/time, what the person understood, where shelter was, time needed to reach it, and what prevented action. Avoid leading questions such as whether an “AI app” would be helpful. Run a supervised tabletop drill with a clearly fictitious alert. Measure comprehension, decision latency, acknowledgement, and shelter-access constraints. Obtain consent and collect the minimum personal data.

## 5. Existing solutions and a defensible comparison

Absence of a capability from a public product page is not proof the capability is absent. The table identifies documented capabilities and proposed complementary work, not a claim to have audited competitors' internals.

| Existing service / prior art | Verified capability | Consequence for the project |
|---|---|---|
| **IITM Damini** | The [6 April 2022 MoES answer](https://www.pib.gov.in/PressReleasePage.aspx?PRID=1813993&lang=2&reg=48) describes GPS-based lightning warnings around 20/40 km, safety instructions and a warning validity of 40 minutes. The current [IITM Thunderstorm Dynamics project](https://www.tropmet.res.in/28-Thunderstorm%20Dynamics-project) links the app and guide. | A proximity-alert app is established prior art. The dated validity statement is not a universal guaranteed 40-minute lead before an individual strike. Benchmark forecasting skill and reliability instead. |
| **IITM's wider lightning prediction/nowcasting work** | A [2025 IITM briefing hosted by MHA](https://ndmindia.mha.gov.in/ndmi/arcc/viewDocument?uid=3++IITM_MHA_meeting_17June2025_VigyanBhawan.pdf), pp. 5–12 and 20, describes lightning propagation guidance, 21 app languages, and hybrid dynamical/AI research. App integration of forecasting/nowcasting model outputs, SMS, dangerous-thunderstorm alerts and cell identification appear in a **future-upgrades** slide. | Distinguish the research/visualization system from capabilities demonstrably integrated into the released app. Multilingual support and hybrid modeling are already documented prior art or development directions. The deck labels a June 2025 meeting, while several slide footers say 1 July 2025; treat it as a 2025 briefing, not a precisely dated product-release record. |
| **NDMA SACHET / CAP Integrated Alert System** | The [official portal](https://sachet.ndma.gov.in/) documents geotargeted multilingual alerts, SMS, mobile apps, browser notifications and an RSS channel. | Multilingual notifications and geofencing are necessary integration features, not stand-alone inventions. A prototype CAP payload does not confer authority or technical access to broadcast through SACHET. |
| **IMD GIS decision-support system** | The [11 February 2026 MoES answer](https://www.pib.gov.in/PressReleasePage.aspx?PRID=2226187&lang=2&reg=48) describes integration of radar, satellite, model, historical and real-time observations, plus exposure/hazard information for impact-based warnings. It cites 10-minute radar and 15-minute satellite availability in that system. | Do not pitch the first multimodal weather dashboard or first impact-based warning system. Prove a narrow forecast improvement and transparent failure handling within a complementary workflow. |
| **IMD district/station nowcasts** | The [official API reference](https://api.imd.gov.in/public/api_reference.html) documents issue/expiry times, messages, severity and cloud-to-ground lightning-probability categories. | Preserve official warnings, source identity and expiry. A forecast warning is not an observed lightning training label. Avoid undocumented assumptions about authentication, rate limits or unrestricted reuse. |
| **Operational polygon warnings and CAP messages** | The [IMD report dated 14 May 2026](https://mausam.imd.gov.in/Forecast/marquee_data/Thunderstorm%20Report%20for%20the%20weather%20events%20of%2013.05.2026.pdf) documents localized polygon nowcasts, radar/satellite monitoring and SACHET dissemination for Uttar Pradesh's 13 May event. | Polygon targeting already operates. Message counts demonstrate dissemination activity, not unique recipients, successful delivery, comprehension or safety outcomes. |
| **Lightning safety action planning** | [US National Weather Service guidance](https://www.weather.gov/mlb/lightning_safety) already considers travel time to shelter and warns that detectors cannot guarantee safety during overhead development. | “Time to shelter” is a sound implementation principle, not a novel scientific discovery. Differentiate through locally validated execution and measured response outcomes. |

**Concrete integration trap:** IMD's documented numeric color mappings differ by endpoint: district/station nowcast uses `1 = green` and `4 = red`; district-warning `Day*_Color` uses `1 = red` and `4 = green`. Normalize each product using its own schema, test it with saved responses, and preserve the original value. Reusing one numeric mapping could invert a warning. [Official IMD API reference](https://api.imd.gov.in/public/api_reference.html).

## 6. Recent event evidence worth using in the demonstration

The 13 May 2026 Uttar Pradesh episode is a documented candidate for **historical replay**, subject to acquiring permitted machine-readable observations. IMD describes moving, intensifying cells with wind, hail, lightning and rain. Its next-day report includes observation/forecast comparisons and warning issue times. For example, Table 2 reports a 130 km/h peak at a Bareilly station against a forecast maximum of 70 km/h. This is a specific event/station comparison, not an estimate of IMD's general accuracy. Many casualties were attributed to wind-related structural/tree damage, so presenting all incident casualties as lightning deaths would be false. [IMD event report](https://mausam.imd.gov.in/Forecast/marquee_data/Thunderstorm%20Report%20for%20the%20weather%20events%20of%2013.05.2026.pdf).

A useful replay asks: what was known by each issue time, what did a baseline predict, what did the candidate predict, and was a recommended action possible before the hazard window? Published report images illustrate an event but are not a replacement for calibrated sensor data or a training license.

## 7. The strongest unmet-needs hypotheses

These are **testable product/research proposals**, not externally verified claims that no existing organization has solved them.

| Proposed differentiator | Why it addresses the problem | Evidence required to defend it |
|---|---|---|
| **Source-aware forecast confidence** | A stale radar image must not silently look like current low risk. Carry observation age, quality, missing-source masks and support for each forecast. | Inject delayed/missing inputs; verify explicit degradation, fallback and abstention; evaluate skill separately by sensor availability. |
| **Initiation/growth model alongside motion baseline** | Extrapolating existing weather cannot by itself represent newly developing convection. Combine a transparent advection baseline with learnable evolution only where validation supports it. | Event-separated tests, motion-only baseline, lead-time skill, calibration, and failure cases. Demonstrate incremental value rather than model complexity. |
| **Decision deadline based on actual action time** | A worksite needing 15 minutes to move people has a different decision deadline from a person beside a suitable building. | Locally verified shelter/action times, forecast arrival uncertainty, operator-reviewed policy and drill results. Never show a precise guaranteed strike ETA. |
| **Acknowledgement and unresolved-action queue** | Operators need to see who still requires contact and which sites lack feasible shelter, not just counts of notifications emitted. | Measured simulated or pilot receipt and acknowledgement latency; idempotent escalation; offline/stale warning behavior. Keep recipients and real sends outside an unapproved demo. |
| **Replay with provenance and counterfactual sensor failures** | Judges and meteorologists can inspect why the system acted, what data it used, and what happened when a feed failed. | Immutable issue-time snapshots, input provenance, model/version IDs, observed outcomes and blind evaluation. Do not manufacture confidence scores or retrospective input availability. |
| **Official-warning coexistence** | A research model must be distinguishable from an authoritative warning; users should see both the official message and experimental supporting evidence. | Clearly identified issuers, expiry handling, conflict display and an operator approval boundary. |

An honest pitch is: **“A verifiable nowcasting and response prototype that makes forecast uncertainty, sensor failures and the time needed to act visible, then measures whether its forecasts improve on strong baselines.”** This is differentiated execution. “World first,” “most accurate,” “zero false alarms” and “guaranteed lives saved” remain unsupported.

## 8. Safety-critical product implications

Use vetted messages and shelter information. The [NWS lightning guidance](https://www.weather.gov/safety/lightning-tips) advises moving to a substantial building or enclosed metal-topped vehicle when thunder is heard, and staying sheltered for at least 30 minutes after the last thunder. A tree, open shelter or mere roof should not be labeled safe. These are general safety principles; deployment content and local shelter suitability require the responsible Indian authority's review.

A falling model probability is not an automatic “all clear.” An offline device cannot know that a new hazard has developed. Preserve visible timestamps, expiry, last-known information and authoritative warnings. If the data or model cannot support a forecast, show unavailable/degraded evidence and the applicable precautionary message. Do not turn missing data into zero lightning risk.

## 9. Verification ledger and remaining uncertainty

The research followed three checks where possible: (1) locate the source that owns the claim, (2) inspect the underlying text/table and its denominator, (3) seek a second document or alternate retrieval and record contradictions. This is not a claim that every fact was independently verified three times.

| Evidence group | Check performed | Residual uncertainty / next action |
|---|---|---|
| Official SIH identity | Compared user file with live official HTML modal and secondary mirrors. | Save a dated official snapshot before submission; don't assume a dataset agreement from the title. |
| Historical NCRB counts | Full PIB annexure read, old parliamentary cross-reference located. | Older PDF URLs may have moved. Preserve primary-source copies. |
| 2021/2022 NCRB counts and denominator | Complete official MoSPI reproduction fetched via direct HTTPS; Statement 4.08 parsed; preceding years independently agree with PIB. | Cite the original reporting year and the forces-of-nature denominator; newer revised NCRB values still need checking. |
| 2024 IMD combined losses | Exact source table indexed; labels and totals checked; live-host retries attempted. | Direct host unavailable during part of the research; retain qualified status until PDF download succeeds. |
| Damini and SACHET capabilities | Ministry description and official pages compared; 22-page 2025 IITM/MHA PDF directly fetched and parsed to separate current descriptions from future upgrades. | Product behavior, latency and delivery rates were not empirically tested. |
| IMD multimodal prior art | Parliamentary description cross-checked with a 2026 event report. | No internal model audit or current national skill benchmark acquired. |
| Survey evidence | Sample and dates inspected in primary author copy; publication existence cross-checked in IMD annual report. | Not nationally representative, dated 2021 fieldwork, author-hosted copy rather than official-hosted full text. |
| Economic benefits | WMO and UNEP statements compared with scope retained. | No project-specific cost-benefit estimate or causal mortality reduction established. |
| Proposed differentiation | Compared against documented services, separated hypothesis from fact. | Needs real data, held-out evaluation and stakeholder testing; no exhaustive global prior-art search claimed. |

The evidence supports a serious problem and a feasible focused research prototype. It does not remove the need for observation access, Indian-domain validation, and an authorized deployment partner before a public warning service can be claimed.
