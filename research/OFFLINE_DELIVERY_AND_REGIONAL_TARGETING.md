# Offline delivery and regional targeting

As of **30 September 2026**. This is a transport and targeting design, not evidence of an operational warning network. Sources are first-party repositories, platform documentation, standards and government releases. No BLE packets or real SMS messages were transmitted during this research.

The practical approach is a layered system: authorized regional alerts over internet and existing government channels; a separately tested nearby relay for signed public alerts; and a user-controlled SMS composer for citizen observations. Bluetooth, SMS and precise phone location solve different parts of the problem.

## What each channel can do

| Channel | Works without mobile data? | What it still needs | What receipt proves |
|---|---|---|---|
| Internet API/push | Yes over Wi-Fi; otherwise no internet means no new delivery | Internet path, reachable service and supported notification lifecycle | App receipt, not that someone read or acted |
| Ordinary SMS | Usually yes | A working operator SMS path; cellular service or a supported carrier alternative such as Wi-Fi Calling | Composer result is not proof of recipient delivery |
| BLE relay | Yes, including when there is no cell service | Compatible nearby participating devices, enabled radios/permissions and a viable chain or later encounter | A peer accepted a packet, not delivery to the whole region |
| Government cell broadcast | Does not require app internet | Operational cellular infrastructure and an authorized public-warning broadcast | Broadcast availability, not individual acknowledgement |
| Previously cached guidance/alerts | Yes | Already downloaded content and a valid freshness check | Cached information only; it cannot reveal a newly issued warning |

SMS is not a zero-coverage transport. Apple's support documentation distinguishes cellular SMS from internet messaging and notes a Wi-Fi Calling exception. Cell broadcast is an operator/public-authority facility, not an endpoint this app may arbitrarily invoke. [Apple messaging requirements](https://support.apple.com/en-us/118433), [DoT/PIB cell-broadcast launch, 2 May 2026](https://www.pib.gov.in/PressReleasePage.aspx?PRID=2257499&lang=2&reg=3).

## Bitchat findings and reuse decision

The official iOS/macOS repository is `permissionlesstech/bitchat`; the official Android repository is `permissionlesstech/bitchat-android`. GitHub commit metadata inspected for this cut-off identifies iOS commit `5e9287fae1e5fea80ca741d4ea669829dc16f144` dated 24 September 2026 and Android commit `1b8a8252d89770ab07ab11a3d72e682a9311adf7` dated 27 September 2026.

| Finding | Evidence and consequence |
|---|---|
| Two different transports | Nearby communication uses BLE peer discovery and multi-hop relay. Geographic/geohash channels use **internet Nostr relays**. The documented mesh limit is seven hops; that is not a distance or delivery guarantee. [Pinned iOS README](https://github.com/permissionlesstech/bitchat/blob/5e9287fae1e5fea80ca741d4ea669829dc16f144/README.md) |
| Separate native applications | Android documents Kotlin mesh services, fragmentation, TTL, deduplication and a foreground service, and claims protocol compatibility with iOS. Those claims still need device-level verification for a selected version. These are not drop-in Expo SDK components. [Pinned Android README](https://github.com/permissionlesstech/bitchat-android/blob/1b8a8252d89770ab07ab11a3d72e682a9311adf7/README.md) |
| Material licensing inconsistency | iOS has an Unlicense/public-domain dedication. Android's README says public domain, but its actual `LICENSE.md` contains **GNU GPL version 3**. Do not transplant Android code under an assumption that it has the iOS licence; resolve the file/version-specific obligations first. [iOS licence](https://github.com/permissionlesstech/bitchat/blob/5e9287fae1e5fea80ca741d4ea669829dc16f144/LICENSE), [Android licence](https://github.com/permissionlesstech/bitchat-android/blob/1b8a8252d89770ab07ab11a3d72e682a9311adf7/LICENSE.md) |
| Encryption is not authority verification | The project documents private-message encryption, while public announcements/channels and proximity are observable. The privacy assessment describes persistent application identifiers despite BLE address randomization. This does not make a nearby sender a disaster authority. [Security policy](https://github.com/permissionlesstech/bitchat/blob/main/SECURITY.md), [project privacy assessment](https://github.com/permissionlesstech/bitchat/blob/main/docs/privacy-assessment.md) |
| Security status is bounded | The current security policy describes vulnerability reporting and latest-release fixes. It is not an independent certification. This review did not establish an independent audit certifying the exact current iOS/Android builds or their suitability for public warnings; the Android top-level `SECURITY.md` request returned 404. Do not repeat an old “never audited” claim as a verified current fact. |

**Recommendation:** borrow the delivery ideas and study the versioned protocol. Build a small, reviewed public-alert transport adapter with an explicit licence decision. Do not assume interoperability with installed Bitchat clients merely because both applications use Bluetooth. A VAJRA-specific envelope also requires compatible participating clients or a deliberately implemented gateway.

## Mobile platform limits

On iOS, Core Bluetooth background modes alter scanning and advertising: duplicate discoveries are coalesced, scanning/advertising can slow, and background service UUID discovery has restrictions. Apple's archived guide describes roughly ten seconds of work when awakened and offers state restoration; none of this promises a continuously running JavaScript mesh. Use a user-visible relay session and native lifecycle handling. [Apple Core Bluetooth background guide](https://developer.apple.com/library/archive/documentation/NetworkingInternetWeb/Conceptual/CoreBluetooth_concepts/CoreBluetoothBackgroundProcessingForIOSApps/PerformingTasksWhileYourAppIsInTheBackground.html).

Android 12+ separates scan, advertise and connect permissions. Background BLE still depends on process/lifecycle behavior; a killed process loses connections. Foreground services have start restrictions, and a `connectedDevice` service or companion-device APIs suit different use cases. Associating a known companion is not the same as discovering arbitrary disaster-relay peers. [Android Bluetooth permissions](https://developer.android.com/develop/connectivity/bluetooth/bt-permissions), [Android background BLE guide](https://developer.android.com/develop/connectivity/bluetooth/ble/background).

For Expo, a BLE adapter must support both the required central and peripheral roles, not merely connect to a sensor. It needs native modules/configuration and development builds. A web preview, Expo JavaScript export or simulator cannot prove radio range, background recovery, battery cost or cross-platform forwarding. Initial acceptance should use physical Android↔Android, Android↔iOS and iOS↔iOS pairs, then a three-device chain with direct A↔C communication physically prevented. Test locked screens, force-stop, permission removal, airplane mode with Bluetooth restored, distance/obstacles, crowded radio conditions, cancellation and expired packets. Record delivery ratio and latency distribution, not an unsupported range claim.

## Regional warnings and the NCR concern

SACHET already uses CAP and geo-targeted SMS. The government announced its cell-broadcast launch on 2 May 2026; the launch notice explicitly included Delhi/NCR in a broad **test** exercise. This is one documented reason for broad messages, not evidence that the user's particular NCR warning was that test or was inaccurate. Its original text, issue/expiry time, source, channel and polygon are needed to assess it. [DoT/PIB announcement, 30 April 2026](https://www.pib.gov.in/PressReleasePage.aspx?PRID=2257102&lang=1&reg=3).

**Design inference:** broad warnings can also reflect a genuine broad hazard area, administrative warning units, forecast uncertainty/movement, or the difference between a hazard polygon and a transmitter's footprint. The launch description discusses individual towers or clusters. More precise GPS does not add spatial skill to a coarse forecast. Do not silently discard an official regional warning because no rain is visible at one user's point, and do not relabel a district forecast as a verified street forecast. [Government description of targeting](https://www.pib.gov.in/PressReleasePage.aspx?PRID=2257499&lang=2&reg=3).

CAP carries area descriptions, polygons/circles/geocodes, issue/effective/expiry information and message status. `Update` and `Cancel` reference previous messages. Preserve these relationships; distinguish `Actual` from `Test`/`Exercise`. A modern UI should state **issuer, hazard, affected area, valid interval, source coverage and why this location matches**, with a separate “near the boundary / location uncertain” state. [OASIS CAP 1.2](https://docs.oasis-open.org/emergency/cap/v1.2/CAP-v1.2-os.html).

## Scalable targeting without a precise-location database

Recommended architecture, still planned:

1. Ingest authorized alerts once. Validate geometry, time, issuer and update/cancellation relationships; store canonical alert objects and spatial indexes in PostGIS.
2. Publish immutable, versioned regional bundles through a cache/CDN. Group subscriptions by coarse H3 or S2 cell, or user-selected district. Compute alert-to-cell coverage when alerts change, rather than running a whole-country user scan for every location update.
3. Keep a recent precise fix and accuracy radius on the phone. Download candidate alerts for the coarse region and neighbors, then make the final polygon/accuracy-circle decision locally. This is in-app geometry matching, not a promise of OS background geofencing. Continuous/background reception is a separate implementation and permission decision.
4. Only change a coarse subscription after meaningful cell movement and hysteresis. Expire server-side tokens/subscriptions, limit retention, and aggregate operator counts instead of showing individuals. A coarse cell still reveals location information; it is data minimization, not anonymity.

| Tool | Suitable role | Important boundary |
|---|---|---|
| H3 | Cell-keyed subscriptions, aggregation and bundle caching | Default `polygonToCells` uses **cell centres**, so it can omit cells that intersect a polygon only at their edges. Use a verified conservative overlap covering plus exact final checks; do not use centre membership as a safety boundary. [H3 region API](https://h3geo.org/docs/api/regions/) |
| S2 | Hierarchical spherical cells and region coverings | Cell hierarchy is an indexing choice, not a weather-resolution claim. Select/test one grid rather than adding both without need. [S2 cell hierarchy](https://s2geometry.io/devguide/s2cell_hierarchy.html) |
| PostGIS | Authoritative spatial storage, validated polygons, indexed candidate matching | `ST_Covers` includes polygon boundaries and uses available indexes; invalid geometries require repair/rejection. Accuracy-circle intersection needs an explicit metric/geography policy. [PostGIS ST_Covers](https://postgis.net/docs/ST_Covers.html) |

Do not hardcode “one H3 cell equals one village.” Areas vary by resolution and position; H3's tables quantify this. Choose resolution using alert size, privacy, payload volume and measured battery/bandwidth. [H3 cell statistics](https://h3geo.org/docs/core-library/restable/).

## Proposed signed relay envelope and processing

Public warnings and private citizen reports are separate message classes. Relays should forward a compact **public alert object**, not each recipient's GPS coordinate or movement history.

```text
Authorized feed -> validated canonical alert -> reviewed signing gateway
   -> regional internet bundle -> nearby BLE cache/relay -> local verification
   -> authorized government/operator channels (separate integration)

Citizen observation -> visible editable preview -> user-selected SMS recipient
   -> receiving organisation verifies it; it does not become an official alert
```

Proposed immutable signed fields: schema version; unique source message identity; source authority and gateway signer separately; verification basis; original message hash/reference; alert/update/cancel type and references; issue/effective/expiry times; hazard/severity; compact geographic scope or a hash-addressed scope already cached; approved language/text/template version; signing key ID; payload hash; signed relay policy. A gateway signature authenticates that gateway's statement. It must not imply an authority signed the original when the source was only fetched from a validated official feed.

Each recipient should verify size/schema, key trust, signature, status/time, references and geography **before** presenting a current alert. Maintain a bounded exact deduplication cache keyed by source identity and revision/hash. Preserve cancellation tombstones until the old alert could no longer be valid, and prevent an older revision from reviving it. An offline device may miss a cancellation; expiry and visible last-sync age remain essential. An uncertain device clock needs a conservative freshness state, not a confident “current” label.

Use bounded fragmentation/reassembly, per-peer quotas, jitter/backoff, short store-and-forward queues, and priority for updates/cancellations. Hop count and transport TTL reduce ordinary flooding but are not cryptographic protection against a malicious peer resetting counters. Never depend on peer acknowledgement as proof of regional delivery. Lost acknowledgements must be safe to retry. Start with a deliberately small payload budget measured against negotiated BLE MTU; do not invent a universal BLE message size or kilometres-per-hop figure.

Allow a relay to carry an alert for neighboring cells without notifying its own user when outside scope. Otherwise a boundary relay could unintentionally prevent a valid warning reaching people beyond it. Keep display relevance separate from the bounded forwarding policy. Public signed content need not be confidential; private reports require a different consent, encryption and metadata design before any future mesh forwarding.

## Bounded SMS composer for this Expo app

Use the SDK-compatible `expo-sms` installer, then `isAvailableAsync()` and an explicit button calling `sendSMSAsync([], body)`. The empty recipient list leaves recipient choice to the operating-system composer. Do not hardcode an emergency number without a verified receiving workflow. Prefill only a clearly marked **unverified citizen observation**, manually entered locality and note; do not attach the precise location or turn the practice warning into a real report.

The SDK57 source says `sent` may mean sent or scheduled, Android always returns `unknown`, and availability is false in a browser and iOS simulator. Show cancelled/unavailable/error/unknown outcomes; never claim “delivered.” A composer availability result does not test coverage or receipt. The default messaging application may choose its supported messaging transport. Device/carrier testing is required for ordinary SMS behavior. [Expo SDK57 SMS source](https://github.com/expo/expo/blob/sdk-57/packages/expo-sms/src/SMS.ts), [versioned SMS reference](https://docs.expo.dev/versions/v57.0.0/sdk/sms/).

Implementation shape:

```ts
// Only inside the user's explicit button handler, after preview and validation.
if (!(await SMS.isAvailableAsync())) return showUnavailable();
const result = await SMS.sendSMSAsync([], reviewedCitizenObservation);
showComposerResultWithoutDeliveryClaim(result.result);
```

The interface should explain that recipient choice and final sending occur in the SMS app and carrier charges may apply. Bound an availability lookup that hangs, prevent duplicate composer launches, preserve readable text on failure, and test with a fake composer without dispatching a real message.

## Current implementation versus next steps

The app has opt-in foreground location, manual city context, draft translations, practice speech and a fixed synthetic Bihar operator experiment. The accompanying mobile change adds the citizen-observation composer with SDK-compatible `expo-sms` 57.0.2. Its manual locality starts empty even when a city or device location is selected. The localized preview is generated only from that typed locality and note, with an unverified-observation title and an explicit statement that it is not an official warning. No recipient is prefilled, and no precise device coordinate is automatically included.

The composer has draft copy in all 13 supported languages. An explicit button checks availability with a three-second deadline and then opens the OS composer with the same preview. It prevents duplicate launches and abandons a pending availability check when the user leaves the screen or backgrounds the app. It distinguishes cancellation, unavailability, failure, sending/scheduling acceptance and unknown status, without claiming receipt. Report fields stay in component memory; this app does not upload or persist them. The OS messaging app may retain a draft after the user opens it.

The mobile suite passes 28 tests, including eight new SMS contract/lifecycle tests using a fake composer. TypeScript, lint and all 21 Expo Doctor checks pass. Export and browser evidence are recorded in `artifacts/mobile-build-check.json` and the separately recorded preview checks. No actual SMS was sent, and no physical Android/iOS composer or carrier receipt was tested. The SDK57 documentation URL was attempted but inaccessible through the web reader; behavior was checked against official SDK57 source and installed native source instead.

There remains **no** official live-warning feed, BLE relay, CAP trust/signing gateway, or H3/S2 subscription service connected to the public app. These are proposed integrations, not completed delivery capabilities.

Order of delivery: (1) reviewed citizen SMS composer and honest source states; (2) authorized alert ingestion and local geometry matching; (3) an isolated signed-relay protocol with replay/cancel/expiry tests; (4) a native foreground BLE pilot on real devices; (5) measured background/lifecycle work and an independently reviewed security/privacy/licence posture. The research does not establish radio delivery, carrier receipt, or public-warning authority.
