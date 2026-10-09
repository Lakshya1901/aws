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
Risk, recommend (glut day, price crash), plan and impact fixtures are copied from the backend's stored responses in
`backend/tests/api_fixtures/` (synthetic test data), so they have the real response shapes; the Second Life and voice
fixtures are hand-written in the same shapes.
They are for development only: the real-mode bundle does not include them, and the real client rejects any response containing `_fixture`.
Use `--clear` when switching between mock and real mode so Metro re-inlines the env var.

Mock behaviour by crop on the New load screen:

| Crop | State exercised |
| --- | --- |
| Tomato | Glut-day recommendation (arrival multiple cited), replay banner, demo loads, alternatives, "Why not" sheet |
| Tomato, harvest "Tomorrow" | Price crash with normal arrivals (D10): no arrival multiple, the API explanation is shown (Hindi text in this fixture), negative waste avoided |
| Onion | Second Life (processor without an offer: "not yet estimated"), stale banner, same_day, delay-harvest warning, template text |
| Potato | 422 "No reporting markets near you for this crop" |
| Banana | 422 "This crop isn't set up yet" |

`/speak` always fails in mock mode, so Listen stays hidden (the "audio hidden" state). Voice upload/parse returns a low-confidence parse with a missing place, so Confirm highlights fields.

### Local backend

Run the API on your machine (from the repo root) and point the app at your computer's LAN IP, so a phone on the same
Wi-Fi can reach it:

```bash
python -m backend.handlers.local_server --host 0.0.0.0 --port 8787
```

```
EXPO_PUBLIC_API_URL=http://<lan-ip>:8787
```

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

### Origin

`/recommend` and `/plan` need origin `lat`/`lon`; place names are not geocoded and the API answers 422 `origin_unknown`
without coordinates. The app uses the device location (expo-location). If permission is denied, it says so and the
load form accepts typed coordinates ("13.14, 78.13").

### Checks

```bash
npx tsc --noEmit
npx expo export --platform android
```

## Build

Both builds run on Expo's EAS servers (free Expo account). `app/.env.local` is git-ignored and EAS does not upload it,
so set the API URL and key once as EAS environment variables:

```bash
npm i -g eas-cli
eas login
eas init                       # links the project to your Expo account (writes the project ID into app.json)
eas env:create --environment preview --name EXPO_PUBLIC_API_URL --value https://<api-id>.execute-api.ap-south-1.amazonaws.com --visibility plaintext
eas env:create --environment preview --name EXPO_PUBLIC_API_KEY --value <demo api key> --visibility sensitive
```

### Android APK

```bash
eas build -p android --profile preview
```

EAS prints a download link for the `.apk`. Install it on a phone (allow installs from unknown sources), then attach it
to a GitHub Release and put that link in the root README. The APK is not committed: it is a large binary.

### iOS

Installing on a real iPhone outside Expo Go needs a paid Apple Developer account, which this project does not use.

- **Real iPhone:** Expo Go. Install Expo Go from the App Store, run `npx expo start --clear` with `.env.local` set,
  scan the QR code with the Camera app (phone and computer on the same Wi-Fi, or `npx expo start --tunnel`).
- **Simulator build (Mac with Xcode):** `eas build -p ios --profile preview` makes a simulator `.app`
  (`ios.simulator: true` in `eas.json`, no Apple account needed). Download and unpack the `.tar.gz`, open the iOS
  Simulator, and drag the `.app` onto it.

## Voice

Hold the mic, speak, release. The app records m4a (AAC), calls `POST /voice/upload`, PUTs the file to the presigned URL, then calls `POST /voice/parse` and opens Confirm. If any step fails, the typed form below the mic stays available with a message.

Spoken replies (Listen) use Amazon Polly, which has **Hindi and Indian English voices only**. In Kannada, Listen speaks an English sentence built from `config/copy/en.json`, and the app says so next to the button and on the language screen.

## Copy

All UI text comes from `config/copy/<lang>.json`. Keys from CLAUDE.md Section 14.5 are used verbatim; every other key is listed in each file's `_review.keys` and needs native-speaker review before the demo.
