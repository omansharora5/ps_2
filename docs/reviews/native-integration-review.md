# Gate 1 native integration and module-boundary review

30 September 2026, attempt 1 of 3. The parent integrator reviewed the native specialist's implementation; it did not implement these native modules. Browser-preview evidence is recorded separately after export.

Reviewed `mobile/src/app`, `mobile/src/components`, `mobile/src/hooks/use-speech.ts`, `mobile/src/lib`, `mobile/src/state/preferences.tsx`, `shared/earth-math.ts` and the shared locale contract.

## Findings and resolution

1. The operator result initially showed probabilities without the target and lead/window context. Requested the actual API target, lead, issue/valid times and synthetic-time note alongside the result. The specialist added boundary validation and visible metadata; the browser integration check must verify the resulting real response.
2. The globe initially imported `useIsFocused` from a transitive navigation dependency. The Expo 57 export subsequently identified the supported boundary: import this hook from `expo-router`. The specialist applied that SDK-specific correction and removed the direct navigation dependency. Doctor, lint and type checks passed; the corrected bundle export is checked separately.

The language preference is loaded before rendering the navigation, and writes are serialized. Important message keys exist in all twelve Indian languages plus English. Completeness is a software property; linguistic accuracy still needs native-speaker review.

The speech controller enumerates installed voices, accepts only an exact locale or same-language match, serializes stops and ignores superseded asynchronous requests. The hook cancels on text/language change, screen blur and backgrounding. Unit tests cover absent voices, late enumeration, replacement requests, expiry and engine failures. The app does not claim those mocks prove physical-device audio or offline voice availability.

The public practice message remains labelled, and simulation probabilities come only from a response explicitly tagged `simulation`. Source links accept HTTPS only. Requests time out; cancellation prevents unmounted requests from installing a result. Provider text is retained as research metadata rather than presented as translated public warnings.

## Structure scan

- `src/` owns the React website and Three.js rendering. It calls public API contracts; it does not import Python implementation or the native React runtime.
- `mobile/` owns its Expo dependency tree and native screens. Shared imports are limited to data, translations and pure geography math.
- `shared/` contains no platform runtime dependency. Metro resolves the native React version from the mobile tree, avoiding the root website's different React version.
- `nowcast/` owns computation and HTTP contracts. Optional training scripts remain separate and import PyTorch only for neural operations.
- `data/government/` owns bounded source files and manifests. The collection API maps fixed IDs to registered scripts and manifest-listed downloads.
- Root documentation distinguishes implemented research behavior from the proposed operational architecture.

No architectural dependency cycle or implicit native authentication boundary was found in these paths. At source-review time, export and browser checks were pending; their results follow. Actual device acceptance remains separate.

## Integration evidence

The parent's exported-client browser flow passed with the real local API: city search and pause, thirteen language choices, Hindi persistence across reload, Urdu text alignment, displayed simulation target/time context, source catalogue, outage and retry. No page JavaScript errors occurred. The absent-browser-voice test exposed an unbounded Expo voice lookup; the specialist added a three-second deadline and a never-resolving-provider regression. The browser now reaches the translated audio-failure fallback. Native source checks/export passed; real-device audio and installation remain untested.

Visual inspection also found clipped bottom-tab labels in the browser preview. The native owner corrected tab height, line height and safe-area/font-scale spacing. The final browser flow passed again, including label bounding checks at 390 × 844; refreshed Earth and Urdu screenshots show complete labels. All material implementation findings from this gate are closed. This does not certify every native accessibility configuration.
