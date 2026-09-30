# React Native application guide

`mobile/` is a separate Expo React Native client. It uses native components and Expo Router, with a browser preview for development. It is not a WebView wrapper around the website.

The app has a public information view and an operator research view. Both are demonstrations: the role switch is navigation, not authentication. Current official warnings are not connected. Spoken practice messages are labelled as practice; research model results stay labelled as simulations.

## Start on this computer

Start the Python service using the root README. Then:

```powershell
cd mobile
npm.cmd ci
npx.cmd expo start
```

For the React Native browser preview:

```powershell
npx.cmd expo start --web --port 8081
```

The app can show bundled geography, translations and guidance without an API configuration. To enable its research catalogue and simulation, copy `.env.example` to `.env`, set `EXPO_PUBLIC_API_URL` and restart Expo. For a browser on this computer:

```text
EXPO_PUBLIC_API_URL=http://127.0.0.1:8000
```

An `EXPO_PUBLIC_` variable is included in client bundles. It must never contain a secret or provider credential.

## Connect a physical phone

1. Put the development computer and phone on a trusted reachable network.
2. Run the Python backend with `--host 0.0.0.0 --port 8000` instead of loopback-only binding.
3. Set `EXPO_PUBLIC_API_URL` to the computer's LAN address, for example `http://192.168.1.20:8000`, substituting the actual address.
4. Restart Expo and use its printed device instructions or a compatible development build.
5. Verify catalogue loading and the labelled simulation before testing speech.

`localhost` on the phone means the phone. Native HTTP transport policies and the local firewall can also affect connectivity; a production deployment needs HTTPS. Browser previews on a different origin may need `VAJRA_CORS_ORIGINS` configured on the backend before startup. This variable replaces the default allowlist, so include every intended browser origin.

The collection write endpoint remains loopback-only even when the service listens on the LAN. No authenticated remote operator service is implemented.

## Languages and readable messages

The shared dictionaries cover Hindi, Bengali, Tamil, Telugu, Marathi, Gujarati, Kannada, Malayalam, Punjabi, Odia, Assamese and Urdu, plus English. Language choice is saved on the device using AsyncStorage. Urdu uses right-to-left text presentation. Provider names and raw scientific metadata can remain in the provider's original language.

The translations are working drafts. Key-completeness tests establish software coverage, not linguistic correctness. Arrange native-speaker review of the public safety wording, script shaping, numbers and pronunciation before a real public trial.

The place search uses the bundled 19-city gazetteer and aliases shared with the website. It does not need geocoding or access to the user's location. Its animated geography and clouds are illustrative. Choosing a place does not make a simulation into a forecast for that city.

## Spoken messages

The app uses `expo-speech`. It checks available device voices, prefers an exact language/locale match and otherwise accepts a voice of the same language. It does not silently choose an unrelated language. If a matching voice is absent, the app retains readable text and shows a voice-unavailable message.

Voice discovery has a three-second deadline. If the platform never returns its voice list, the app shows the translated audio-failure message instead of leaving the user waiting indefinitely. The browser preview tests this actual failure path; mocked unit tests separately cover a resolved empty voice list.

Listen/Stop controls start and cancel speech. Changing the message or language, leaving the screen or moving the app to the background stops the old utterance. This implementation does not provide background push notifications or automatically read official alerts. The controller also supports expiry checks for future timestamped integrations.

A voice may require installation, and a listed voice does not establish that speech works offline. On physical iOS devices, silent mode can suppress Expo speech. These behaviors are described in the [versioned Expo speech documentation](https://docs.expo.dev/versions/v57.0.0/sdk/speech/).

## Build and verification

Use the locked versions and run the app's scripts for local checks. The underlying commands are:

```powershell
npx.cmd tsc --noEmit
npm.cmd test
npx.cmd expo lint
npx.cmd expo-doctor
npx.cmd expo export --platform all --max-workers 2
```

For the exported web preview, run `python scripts/serve_mobile_preview.py` from the repository root and open `http://127.0.0.1:8081`. Export with `EXPO_PUBLIC_API_URL=http://127.0.0.1:8000` configured when checking against the local backend. With both services running, `node --experimental-strip-types scripts/verify-mobile-preview.mjs` exercises place selection, language persistence, absent-voice behavior, the research API and retry handling in Chromium.

Export creates web assets and native JavaScript bundles. It does not create a signed APK, AAB or iOS application. Native binaries require Android/iOS build tooling or an EAS build configured under the team's account. Follow the [Expo build guide](https://docs.expo.dev/build/introduction/) when that account and signing configuration are available. Do not commit signing credentials.

The workspace used for delivery has no Android SDK, emulator or adb, and no iOS build environment. The exact checks completed here are recorded in [VALIDATION.md](../VALIDATION.md); no physical-device audio or native installation is certified.

## Device acceptance before a public pilot

| Check | Evidence to record |
|---|---|
| Native install and cold start | Device, OS, build identifier and launch result |
| Each intended language | Native-speaker review of visible text and spoken practice message |
| Missing voice | Clear readable fallback; no unrelated language spoken |
| Offline speech | Airplane-mode test after installing the required voice |
| Cancellation | Stop, rapid language changes, leaving screen and backgrounding stop stale speech |
| Accessibility | Screen reader labels, large font, Urdu layout and reduced motion on actual phones |
| API failure | Loading terminates; useful error/retry; no stale result presented as current |
| Battery and animation | Low-end phone frame pacing, pause/background behavior and thermal impact |

Future real-warning delivery additionally needs an authorized warning feed, issue/expiry and cancellation handling, notification permissions, authenticated operator access, delivery monitoring and user testing. Those integrations are separate from rendering a message or speaking text.

## Source map

- `mobile/src/app/`: Expo Router screens and navigation.
- `mobile/src/state/preferences.tsx`: persisted locale and reduced-motion preference.
- `mobile/src/lib/api.ts`: API boundary validation and bounded requests.
- `mobile/src/lib/speech-controller.ts`: voice selection, cancellation and expiry logic.
- `shared/translations.ts`: language catalogue and text dictionaries.
- `shared/locations.json`, `shared/earth-land.json`: shared geography.
- [Geography provenance](../shared/geography-provenance.json): source links and transformations.

The stack follows the [Expo SDK 57 reference](https://docs.expo.dev/versions/v57.0.0/) and [Expo Router installation guidance](https://docs.expo.dev/router/installation/). The original Expo template's MIT notice is retained in `mobile/LICENSE`.
