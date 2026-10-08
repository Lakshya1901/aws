# AnnaSetu mobile app

React Native + Expo (SDK 57) + TypeScript, expo-router. Android is the primary target; iOS runs in Expo Go or a simulator.

## Layout

```
app/
├── app/          screens (expo-router): language, today (Glut Radar), new-load, confirm, recommendation, plan, impact
├── components/   RecommendationCard, CompareSheet, RiskList, MicButton, LoadForm, ImpactRows, ui (primitives)
├── api/          typed client for the API contract (CLAUDE.md Section 13), mock mode, fixtures/
├── i18n/         reads ../config/copy/{en,hi,kn}.json (Metro watches that folder, see metro.config.js)
└── lib/          session state, AsyncStorage cache, theme
```

## Run

```bash
cd app
npm ci
```

### Mock mode (no backend)

```bash
EXPO_PUBLIC_API_MOCK=1 npx expo start --clear
```

Every screen shows a purple "FIXTURE DATA" banner. Fixtures live in `api/fixtures/*.fixture.json` and carry `"_fixture": true`.
They are for development only: the real-mode bundle does not include them, and the real client rejects any response containing `_fixture`.
Use `--clear` when switching between mock and real mode so Metro re-inlines the env var.

Mock behaviour by crop on the New load screen:

| Crop | State exercised |
| --- | --- |
| Tomato | Glut-day recommendation, replay banner, demo loads, alternatives, "Why not" sheet |
| Onion | Second Life (processor), stale banner, same_day, delay-harvest warning, template text |
| Potato | 422 "No reporting markets near you for this crop" |
| Banana | 422 "This crop isn't set up yet" |

`/speak` always fails in mock mode, so Listen stays hidden (the "audio hidden" state). Voice upload/parse returns a low-confidence parse with a missing place, so Confirm highlights fields.

### Real mode

Create `app/.env.local` (git-ignored) from `.env.example`:

```
EXPO_PUBLIC_API_URL=https://<api-id>.execute-api.ap-south-1.amazonaws.com
EXPO_PUBLIC_API_KEY=<demo api key>
```

```bash
npx expo start --clear
```

The app sends the key as the `x-api-key` header. It never calls AWS services directly and holds no AWS credentials.

### Checks

```bash
npx tsc --noEmit
npx expo export --platform android
```

The Android APK is built with EAS (`eas build -p android --profile preview`), see the root README.

## Voice

Hold the mic, speak, release. The app records m4a (AAC), calls `POST /voice/upload`, PUTs the file to the presigned URL, then calls `POST /voice/parse` and opens Confirm. If any step fails, the typed form below the mic stays available with a message.

Spoken replies (Listen) use Amazon Polly, which has **Hindi and Indian English voices only**. In Kannada, Listen speaks an English sentence built from `config/copy/en.json`, and the app says so next to the button and on the language screen.

## Copy

All UI text comes from `config/copy/<lang>.json`. Keys from CLAUDE.md Section 14.5 are used verbatim; every other key is listed in each file's `_review.keys` and needs native-speaker review before the demo.
