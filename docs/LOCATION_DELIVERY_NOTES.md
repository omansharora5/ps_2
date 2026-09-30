# Foreground location delivery

The public native app can use a device location after the user taps **Use my location**. Manual city search remains available. Device coordinates select the globe focus and geographic context; they do not create a weather forecast or imply an operational warning service.

## Implemented behavior

- Permission is requested from the operating system only from the explicit button handler. No location request runs at startup.
- The app asks for foreground permission. It obtains one usable fix through a foreground subscription and removes that subscription immediately after success.
- Cancel, manual city selection, leaving the public screen, and backgrounding invalidate pending callbacks and remove an established subscription. A subscription that finishes registering after cancellation is also removed. An already open operating-system permission dialog cannot be dismissed by this app; its later response cannot restart a cancelled request.
- Permission waiting is bounded to 45 seconds. After permission is granted, the service/position request is bounded to 15 seconds. Denied, unavailable, cancelled, stale and inaccurate outcomes retain the readable manual fallback.
- A fix needs finite latitude/longitude in valid ranges, a timestamp no more than two minutes old or ten seconds into the future, and reported accuracy of at most 5,000 metres. Missing accuracy is rejected. Stale or inaccurate first updates may be replaced by a fresh fix before the deadline. These are interface acceptance limits, not validated warning-resolution thresholds.
- Accepted coordinates are displayed with their reported uncertainty and capture time. After two minutes the displayed fix is labelled stale and must be refreshed. The app keeps its selected fix in memory, clears that selection on leaving the public screen or backgrounding, and never writes coordinates to AsyncStorage, logs, the research API or a reverse-geocoding service. The Expo/browser location implementation may retain an in-memory last-known fix, and the operating system's provider may cache locations or use network services. Clearing the app selection does not promise to erase those platform caches.
- Device points show **Administrative region is not resolved for this coordinate**. No country, district or nearest city is inferred. Coordinates outside India remain unchanged. City-list points have an explicit approximate-city-point label and their supplied state/country metadata.
- Permission text describes the result of the last request; the app does not continuously monitor permission changes. A new request checks permission again.
- All 13 dictionaries include the new buttons, state messages, precision/time labels and live-coverage limitation. These remain translation drafts requiring native-speaker review.

## Alert and operator scope

Every selected location currently shows that live regional warnings are not connected, with the existing official-warning link available below. No location is mapped to the synthetic Bihar experiment, and the location is not sent to `/api/runs`.

The operator view continues to show its fixed **synthetic Bihar** experiment, target, lead, and synthetic timestamps. It is a research view, not an authenticated all-India operational console. A future real regional alert flow needs an authorized warning feed, defined coverage/polygons, validity and cancellation handling, and spatial matching with explicit uncertainty. No such feed is claimed in this delivery.

## Configuration and primary references

`expo-location` is installed through the Expo SDK-compatible installer. The config plugin sets a purpose-specific iOS when-in-use message and disables background-location modes, background permissions, foreground service and motion activity. No TaskManager or background location task is registered. Native configuration changes require a new native build; an already installed binary does not receive them through JavaScript alone.

The [Expo SDK 57 Location documentation](https://docs.expo.dev/versions/v57.0.0/sdk/location/) documents foreground permission, foreground-only position subscriptions, removable subscriptions, coordinate uncertainty in metres, and timestamps in milliseconds. The implementation follows those APIs and adds the bounded request policy above. The [versioned Expo location source](https://github.com/expo/expo/tree/sdk-57/packages/expo-location) and the installed plugin were inspected to verify the permission configuration. Browser location requires a supported secure context, such as HTTPS or localhost; see the [browser geolocation documentation](https://developer.mozilla.org/en-US/docs/Web/API/Geolocation_API).

## Verification scope

The location unit tests exercise no startup request, denial, cancellation during permission and subscription setup, exact foreign coordinates, stale/future/invalid/inaccurate readings, replacement of a stale first update, bounded failure, disabled services and coordinate clearing. Existing translation, speech and API tests continue to run.

Final static checks and export results are recorded in `artifacts/mobile-build-check.json`. Parent integration checks use a browser geolocation override and do not establish native sensor quality or actual phone permission-dialog behavior. No Android emulator/SDK or physical phone, and no iOS build environment, was available here. Phone acceptance still needs allow-once, approximate/precise permission, deny/permanent-deny, GPS-off, indoor timeout, cancel/background, Urdu, and stale-fix checks on supported devices.
