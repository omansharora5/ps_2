# Image, collection and mobile delivery checks

This checklist records the evidence required for the September 2026 implementation. Completion results belong in `VALIDATION.md`; an unchecked item is not a claim of success.

## Scientific image methods

- [x] Real historical radar input, correct units and explicit timezone limitation.
- [x] Raw, cleaned and smoothed fields preserve missing coverage rather than filling unknown pixels as clear weather.
- [x] Persistence, global motion and dense flow use only input frames; future truth is read for evaluation separately.
- [x] Displayed method, target and metrics match the actual server response.
- [x] Forecasts remain radar-echo experiments, with no inferred Indian lightning accuracy.

## Data and training

- [x] Catalogue links directly to provider API/catalog/documentation and identifies access requirements.
- [x] Local downloads use manifest-listed files, reject traversal and retain hashes/provenance.
- [x] Collection jobs accept only registered collectors, bound concurrency and reject untrusted remote writes.
- [x] Training input contract fixes units, target, event groups, time/availability and coverage.
- [x] Dataset validation and a small training smoke exercise run; toy results stay labelled synthetic.
- [x] Readme commands match implemented scripts and optional ML dependencies remain separate.

## Globe and mobile

- [x] Search selects a supported place and animates geographic focus/zoom to its coordinates.
- [x] Decorative clouds are labelled; no live-cloud claim is made.
- [x] Reduced motion, animation pause and unavailable-WebGL behavior work.
- [x] React Native app exports Android/iOS bundles and web preview; this does not prove a signed native binary.
- [x] Twelve Indian language dictionaries and English fallback have complete important message keys.
- [x] TTS selects an available matching voice, handles missing voices, and cancels old utterances.
- [x] Public/operator switching does not imply authenticated authority.
- [x] Mobile layout, API failure, preference persistence and source links work in browser preview.
- [x] Real-device audio, notification delivery and native installation are reported separately if untested.

## Repository

- [x] Only project code, docs, permitted sample data and useful verification artifacts are staged.
- [x] Credentials, .env values, virtual environments, native-generated build directories and local databases are excluded.
- [x] Initial repository is private and named `ps_2` under the authenticated account.
- [x] Push uses a normal branch update, without force, and the remote commit matches local HEAD.
