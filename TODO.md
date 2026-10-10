# AnnaSetu: to do (handoff for a fresh Claude Code session)

Deadline: Sunday October 11, 2026, 8:00 PM IST.
Branch: `edit/beautiful-ritchie-ij5zmf` (`edit/festive-darwin-bd1y1i` was merged to `main` on October 9). Spec and every decision so far: `CLAUDE.md` (D1-D25 in Section 19.1; D24 and D25 are the latest).

## How to start the next session

1. Environment settings already hold `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_DEFAULT_REGION=ap-south-1` and `EXPO_TOKEN` (all verified October 10).
2. Start a new Claude Code cloud session on this repo and branch and paste:

```
Read CLAUDE.md and TODO.md completely. Start at "Next session (October 10)" in TODO.md.
Ask me the three open decisions first. Confirm with me before any `sam deploy`, any
change to GitHub repo settings (rename, visibility), and any merge to main. Tick items
in TODO.md as they are done and commit TODO.md with the work.
```

3. Container setup the new session needs (tools are not persisted): `pip install --ignore-installed PyYAML boto3 aws-sam-cli awscli pytest matplotlib`; `cd app && npm ci`.

## Current state (October 10)

- Deployed: stack `annasetu` in ap-south-1, `UPDATE_COMPLETE`. API `https://udlpm9qppa.execute-api.ap-south-1.amazonaws.com`; key in SSM `/annasetu/app_api_key` (never print or commit it). Bucket suffix `abcd11`. Bedrock off; no alarm email.
- Data (D24): India Data Portal market-level AGMARKNET, 400 commodities, 4,142 markets, 2021-01 to 2026-05. Per-commodity files in `s3://annasetu-data-abcd11/idp/` (rebuild: download the two CSVs listed in `data/snapshot/idp_manifest.json`, then `scripts/build_idp.py` and `scripts/build_idp_config.py`). MarketRisk holds the 20 preload crops for as-of 2023-09-06 plus guava (fetched on request).
- Routing crops: tomato, onion. Radar only: everything else (potato and banana lack a sourced harvest cost).
- Checks: 105 backend tests pass; `tsc` clean; `sam validate --lint` passes; backtest 937fb04f9baf reproducible (still `same_day`).
- Live smoke test passed on every endpoint (October 10), including `/crops/fetch` for guava.
- Not yet done anywhere: UI design pass, APK, any run on a phone, native-speaker review (new crop-picker strings too), usability test, README update for D24.

## Next session (October 10)

### A. Three decisions to ask the user first
- [x] A1 Headline replay day (D18). Oct 10: user chose the strongest figures: 2023-09-29 (10 loads: Binny Mill 11.2 t + Vayalapadu 4.8 t, waste avoided mid 732 kg, range -216 to 3,269; 2023-09-15 mid 499). `replay_date` set, D18 updated, replay test updated. Redeploy + ingest pending confirmation.
  - Was: Market-level results with 10 demo loads from Kolar: 2023-09-06 waste avoided about -8 kg, no split; 2023-09-15 and 2023-09-29 split the loads (Binny Mill + Punganur / Vayalapadu) with waste avoided mid about 500-730 kg; 2025-03-19 (second replay) 365-812 kg per 2 t load. After choosing: set `replay_date` in `config/model.json`, record in CLAUDE.md D18, redeploy (confirm first), invoke ingest with `{"crops": [...preload], "as_of_date": "<day>"}` or the plain `{}` fan-out, check the weather snapshot covers the day (`data/snapshot/weather_power_*`).
- [x] A2 Expo account for the EAS project (Oct 10: `lakshya1901-team`): `lakshya1901` or `lakshya1901-team` (`eas init` writes the project id into `app/app.json`).
- [x] A3 UI design approach (Oct 10: canvases first): recommended, design the Today radar and Recommendation card first as design canvases here, then apply to the Expo screens.

### B. UI and UX design, then APK (user asked: design first, then export the APK)
- [x] B1 (Oct 10: impeccable init wrote PRODUCT.md (FPO manager primary, farmer-level wording, reads short text, Android first); CLAUDE.md 14.3 now earnings first; Today, Recommendation and Foundations canvases rebuilt (Material 3, sourcebook palette, spec copy words), real 2023-09-29 figures; polish pass then light beige page #FAF6EE with Material 3 tonal surfaces and one soft elevation shadow (user choice), consistent market-row fields, Material type scale, contrast all >= 4.5:1; Today and Recommendation approved; New load, Confirm, Unsold stock, Today's plan, Impact drafted on the same system; awaiting review) Design pass on Today (radar, crop chips, Other crop), Recommendation card (Section 14.3 rules), then the remaining screens. Keep Section 14.6 rules (16 pt base, 24 pt card numbers, 48 dp targets, colour + word + icon).
- [x] B2 Apply to `app/`; `npx tsc --noEmit`; Android export builds.
  - Oct 10: all screens rebuilt (Material 3 on light beige, react-native-svg icons, Noto Sans in all three scripts, bottom navigation bar for Today / Today's plan / Impact). tsc clean, Android export bundles, 105 backend tests pass. Checked in a browser (react-native-web, mock data), not yet on a phone or emulator. New copy keys await native review (listed under `_review`). Unsold stock has no "Use this" (it logged nothing).
- [x] B3 `app/.env` written; `eas init` (lakshya1901-team/annasetu); EAS preview env: EXPO_PUBLIC_API_URL (plaintext), EXPO_PUBLIC_API_KEY (sensitive; EAS does not allow secret for EXPO_PUBLIC_ vars, and it ships inside the APK anyway); build 2377f6c6 finished, APK 107 MB with the live API URL and the new strings in the bundle; README links https://expo.dev/artifacts/eas/BygXbwO-2GY_xedOPQo8k5jfkWs5yDkbset9HNDhyO8.apk. GitHub Release: no release tool in this session, team attaches it (3.5).

### C. Delhi, languages, crops (user request, October 10; D26-D28)
- [x] C1 21 languages (English + 20 most spoken): copy files, Noto fonts per script, RTL text for Urdu/Kashmiri/Sindhi, voice input only where Transcribe supports it (12). All new text machine-drafted, pending native review (Kashmiri, Santali, Manipuri, Dogri need a rewrite).
- [x] C2 Typed "City, town or village" resolves to a market or district in config/markets.json (API); the app no longer replaces a typed place with GPS. Unsold stock has a place field.
- [x] C3 Glut Radar preload top 50 fruits and vegetables (config/commodities.json); routing stays tomato and onion (no other crop has a full sourced profile, D28).
- [x] C4 Delhi outlet: India FoodBanking Network seeded in config/outlets.json (only Delhi outlet with a fetched source). No Delhi biogas/compost/feed/processor found with a source.
- [x] C5 Routes cached from Azadpur (534 routes, data/routes_cache.json). Delhi Rescue checked locally: typed "Azadpur" resolves; no split -> 422 split_required (no Delhi weather, D19); trader split 420/80 kg -> India FoodBanking Network 5.5 km, kept out of landfill 420 kg; spoiled part "No biogas or compost unit near you yet"; Urdu template explanation works.
- [x] C5b Weather (D29): NOAA GHCN-Daily via AWS Open Data for Delhi replay windows; live Open-Meteo forecast / GHCN on the Lambda (WEATHER_LIVE=1). Delhi Rescue now estimates the split. 108 tests pass.
- [x] C5c Lifetime dashboard on the phone (D30): Impact tab "Since you started": kg kept out of landfill, % of produce saved, Total money saved, composition bar; 9 new strings in 21 languages (pending review). Checked in a browser with mock data.
- [x] C5d Pan-India outlets (D31): 15 real biogas, compost and processor units in 7 more states seeded from desk research (sources re-fetched, Amazon Location coordinates); Rescue radius 100 km. 112 tests pass. Food banks outside Bengaluru/Delhi: none with a fresh-produce source (team: ask IFBN for its hub list).
- [x] C5e Any typed place in India (D31): Amazon Location place search when the name is not a market or district (live on the Lambda, cached offline for 9 cities); Rescue routes cached for Chennai, Hyderabad, Surat, Indore, Ujjain, Kochi, Gwalior, Agra, Bengaluru. Checked locally: all 10 cities (with Azadpur) return a Rescue route. 113 tests pass.
- [x] C6 Redeploy (confirmed by the user, Oct 10): reviewed change set (9 resources modified, none replaced or deleted) executed, stack UPDATE_COMPLETE; `scripts/seed.py` wrote 20 outlets; ingest for 2023-09-29 queued 50 crops, queue and dead-letter queue drained to 0. Live smoke test: Rescue with an estimated split (live weather) at Azadpur -> IFBN, Chennai -> Chetpet, Hyderabad -> Bowenpally, Agra -> Raj Nagar, Gurugram (live place search) -> IFBN, Thanjavur -> no outlet in radius; Kolar 2 t farm load -> Binny Mill Rs 7.5-11.5/kg (stale banner); onion radar near Azadpur 291 markets.
- [x] C9 Icon (bridge + sprout) in app, README, PRODUCT.md; APK limited to arm64-v8a and armeabi-v7a (next build); merge conflict with main resolved (main was a squash of 57ac772).
- [x] C10 Backtest result JSON moved to S3 backtest/ (52k lines out of git); README tech stack table with AWS per layer; one "All numbers are estimates" line per screen (D32); Mumbai weather (8 nearest NOAA stations).
- [x] C11 Advice for all 50 preloaded crops (D33); harvest cost optional; Settings screen with My crops; crop chips from the API; typed place clears stale coordinates. 115 tests, tsc and Android export pass; not yet checked on a simulator or phone.
- [x] C12 Settings: Live / Demo data switch (D34). Deployed and checked October 10: live Agmarknet prices dated 8 Oct for tomato (Kolar), onion (Pune), potato (Agra); demo still replays 29 Sep 2023; Expo Go update published.
- [x] C13 Redeploy: weather fix, 48 crop profiles, /crops names (done October 10; live /crops lists 50 routable crops). Next: simulator pass on the Mac, then the APK build.
- [ ] C14 iOS simulator pass on the Mac (Expo SDK 57). Oct 10: branch checked out, `npm install` done. Blocked:
  - `app/.env` not written: no AWS CLI or credentials on this Mac, so the key in SSM `/annasetu/app_api_key` can't be read here; the user supplies it.
  - Xcode 27.0 first-launch components missing (CoreSimulator absent, `simctl` fails, `xcodebuild -checkFirstLaunchStatus` exits 69) and no iOS simulator runtime. User runs `sudo xcodebuild -runFirstLaunch`, then `xcodebuild -downloadPlatform iOS`.
  - Then: `npx expo start --ios`, screenshot Language, Today, New load, Unsold stock, Recommendation, Today's plan, Impact, Settings; check first: New load "Crop" label clipped under the header (seen on Android), doubled chip / segmented-button borders (Android; check iOS), long Hindi/Kannada strings, overall polish.
- [ ] C7 Voice parse in languages other than en/hi/kn needs Bedrock (D23, still blocked); until then those transcripts land on Confirm with fields highlighted.
- [ ] C8 Video beat 1 (D22): no recent Delhi dumping report found; best fetched: INPECS 2012 (Azadpur "approximately 2 000 tons of waste ... daily"), Tribune 2025-05-17 (CM: "garbage dump"). Team to choose.

## Today (October 9)

### 1. Connect AWS keys and set up the workflow
- [x] 1.1 Create an AWS Budget alert (e.g. USD 10) in Billing.
- [x] 1.2 Create IAM user `annasetu-deployer` (not root): `PowerUserAccess` plus an inline policy allowing `iam:CreateRole`, `iam:PutRolePolicy`, `iam:AttachRolePolicy`, `iam:DetachRolePolicy`, `iam:PassRole`, `iam:GetRole`, `iam:DeleteRole*` on `arn:aws:iam::*:role/annasetu-*`. Create an access key. Delete it after the hackathon.
- [ ] 1.3 Bedrock console, ap-south-1: enable a small Claude model; note its model ID and whether it needs an APAC inference profile (`infra/README.md`).
  - Oct 9: blocked. Anthropic use-case form: "Your account is not authorized"; Nova 2 Lite playground: "ValidationException: Operation not allowed", also after upgrading to the Paid plan. Adapter now uses the Converse API (D23), so any model works once allowed. Open a support case (Account and billing); deploy with Bedrock off (rule parser + templates) meanwhile.
- [x] 1.4 Environment settings (session title bar, cloud environment menu, Edit): add `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_DEFAULT_REGION=ap-south-1`. Never paste keys in chat or commit them.
  - Oct 9: both keys are set, but STS rejects them (`InvalidClientTokenId`: key deleted, inactive, mistyped, or has stray whitespace/quotes). `AWS_DEFAULT_REGION` is not set. Re-enter the key pair, then start a new session. Blocks 1.5, 2.1, 2.3, 2.4.
  - Oct 9 (new session): STS OK as `annasetu-deployer`, region ap-south-1.
- [ ] 1.5 Create SSM SecureStrings `/annasetu/datagov_key` and `/annasetu/app_api_key` (`infra/README.md`).
  - Oct 9: `/annasetu/app_api_key` created (random). `/annasetu/datagov_key` not created: no key yet; no code reads it (IAM grant only), so deploy does not need it.
  - Oct 10: data now comes from the India Data Portal bulk files (D24), so the data.gov.in key is not needed at all.

### 2. Routes and deploy
- [x] 2.1 Cache routes from the Kolar demo origin: `python scripts/cache_routes.py 13.137,78.134`. Add the demo FPO villages as `<village_id>=lat,lon` if used. Commit `data/routes_cache.json`.
  - Oct 9: cached from Kolar (13.137,78.134) and the Bengaluru mandi (12.977,77.575) to all 7 markets and 4 outlets. Delhi and Mumbai skipped: no city mandi chosen and no outlet within 300 km yet (D20); add them once outlets are seeded.
- [x] 2.2 Re-run both replay days locally (`python -m backend.handlers.local_server`, `REPLAY_DATE=2025-03-19` for the second) and record the real figures (top outlet, net ranges, waste avoided, redirected, extra km, 10-load split).
  - Oct 9, snapshot mode, origin Kolar, loads 3000/2500/2000/2000/1500/1500/1200/1000/800/500 kg (demo loads). Both days report `stale: true`; check before the video.
    - 2023-09-06, one 2,000 kg load: top Mandya net Rs 14.0-30.8/kg (mid 21.0) vs default Kolar Rs 5.2-7.2 (mid 6.1); waste avoided -36 to 403 kg (mid 85; range crosses zero); redirected 2,000 kg; extra 184 km, 25.7 l diesel, 68.9 kg CO2. Ten loads: Mandya 5,500, Bengaluru 5,300, Madanapalle 5,200 kg; waste avoided -234 to 3,254 kg (mid 717); redirected 16,000 kg; extra 978 km.
    - 2025-03-19, one 2,000 kg load: top Bengaluru Rs 7.3-10.6/kg (mid 8.8) vs Kolar Rs 3.6-5.0 (mid 4.2, below harvest cost 4.7); waste avoided 365-812 kg (mid 789; placeholder dump share, D12); extra 73 km, 10.2 l diesel. Ten loads: all 16,000 kg to Bengaluru (not capped); waste avoided 2,921-6,494 kg (mid 6,314); extra 727 km.
- [x] 2.3 `cd infra && sam build && sam deploy --guided` (confirm first; creates billable resources). Pass `BedrockModelId` / `BedrockModelArns`.
  - Oct 9: `sam build` passes; 99 backend tests pass. Deploy waits for confirmation. Bedrock off (both parameters empty).
  - Oct 9: first deploy (NameSuffix abcd11, no AlarmEmail) failed: `annasetu-deployer` was denied `iam:CreateRole` (with tags) and `iam:DeleteRolePolicy` on `annasetu-*` roles; stack is `ROLLBACK_FAILED`. Needs the inline IAM policy fixed in the console (CreateRole, TagRole, DeleteRolePolicy and related on `role/annasetu-*`), then delete the stack and redeploy.
  - Oct 9: policy fixed, stack deleted and redeployed: `CREATE_COMPLETE`. API `https://udlpm9qppa.execute-api.ap-south-1.amazonaws.com`. Smoke test found two bugs, fixed in code (MarketDay query used key `pk` instead of `market_crop`; authorizer timed out cold at 128 MB, now 256 MB); redeploy pending confirmation.
  - Oct 10: redeployed with D24 (SQS fetch queue + DLQ alarm, /crops, /crops/fetch) and D25: `UPDATE_COMPLETE`. 400 commodity files in `s3://annasetu-data-abcd11/idp/`; 20 preload crops in MarketRisk (~14,500 market rows) via the SQS fan-out; tomato ingest 7.4 s, 109 MB. Live smoke test: every endpoint 200 (wrong key 403), recommend/plan match the local replay, guava fetched on demand (available -> fetching -> ready < 30 s), radar 42 rows near Kolar.
- [x] 2.4 `python scripts/geocode_markets.py` (review the diff, commit), `python scripts/seed.py`, invoke ingest once with `{"as_of_date": "2023-09-06"}`, confirm MarketRisk rows.
  - Oct 9: geocoded (7/7 relevance 1.00, within about 1.6 km of manual coords), seeded 4 outlets and 6,802 MarketDay rows, snapshot in S3; ingest for 2023-09-06 wrote 7 MarketRisk rows (Kolar glut, R 1.76, -28.7% in 3 days, matches D14).

### 2b. All crops, pan-India (D24, D25; October 10)
- [x] Market-level AGMARKNET data for every commodity from the India Data Portal; `config/markets.json` (4,142 markets) and `config/commodities.json` (400); offline snapshot for tomato and onion near Kolar.
- [x] Glut Radar for any crop; top 20 fruits and vegetables preloaded; any other fetched on request (SQS). App: crop chips from `/crops`, Other crop screen with fetch-later.
- [x] Onion profile sourced (routing on). Potato and banana: no sourced harvest cost; radar only until one is supplied.
- [x] Headline replay day (D18), chosen Oct 10: 2023-09-29 (see A1). On market-level data 2023-09-06 gives waste avoided about -8 kg and no load split; 2023-09-15 and 2023-09-29 split the ten loads with positive waste avoided. Team to choose; then set `replay_date` and re-run ingest.

### 3. iPhone and Android test
- [ ] 3.1 Put the API URL and key in `app/.env` (from `app/.env.example`); never commit it.
- [ ] 3.2 Android: `app/eas.json` has a `preview` profile that builds an APK (EAS environment `preview`). Needs an Expo account (`eas login`). EAS does not upload the git-ignored `app/.env`, so set `EXPO_PUBLIC_API_URL` and `EXPO_PUBLIC_API_KEY` with `eas env:create --environment preview` (key as a secret). Then `eas build -p android --profile preview`; install the APK; one typed and one voice recommendation end to end (target under 15 s from release to card).
- [ ] 3.3 iPhone: run through Expo Go (no App Store / TestFlight). Same two flows.
- [ ] 3.5 Build the APK file (steps in `app/README.md`, Build): `eas build -p android --profile preview`, download the `.apk`, attach it to a GitHub Release (not committed; large binary) and use that link for README "Android APK".
- [ ] 3.6 iOS build (steps in `app/README.md`, Build): Expo Go on a real iPhone; optional simulator build `eas build -p ios --profile preview` on a Mac. No `.ipa` for real devices without a paid Apple Developer account.
- [ ] 3.4 Check Listen (Hindi and English only; Kannada shows the note), Second Life screen, stale banner, 422 messages.

### 4. Suggestions, improvements, re-iterations
- [ ] 4.1 Fix whatever the phone tests break. Keep changes minimal; record any decision change in `CLAUDE.md` in the same commit.
- [ ] 4.2 Native-speaker review of every Hindi and Kannada string in `config/copy/` (keys listed under `_review`); clear `_review` when approved.
- [ ] 4.3 Usability test with a few volunteers (first-time user gets a recommendation by voice and can repeat the reason). Then update the "Users" row in README.md and CLAUDE.md Section 18.

- [x] 4.4 Farm-to-city reframe (CLAUDE.md D19): M8 (Rescue and Recover) implemented: engine, API, Unsold stock screen, Impact Ledger lines, 99 backend tests, `tsc` and Android export pass. Not yet run on a phone.
- [ ] 4.5 Fill open decisions D20 (real outlets per Rescue city: Bengaluru, Delhi, Mumbai), D21 (biogas yield source), D22 (video beat 1 source of dumping at a city mandi).

### 5. Verification
- [x] 5.1 Full checks (Oct 10: 105 passed, tsc clean, template valid): `python -m pytest backend/tests -q`, `cd app && npx tsc --noEmit`, `cd infra && sam validate --lint`. Oct 9: 85 passed, tsc clean, template valid. Re-run after any later change.
- [x] 5.2 Reproducibility (Oct 10: backtest 937fb04f9baf JSON and both PNGs byte-identical on re-run): re-run `python analysis/backtest.py --crop tomato` and `python analysis/second_replay.py`; outputs must be byte-identical to the committed files. Oct 9: JSON and both PNGs byte-identical (charts need matplotlib).
- [ ] 5.3 Every number on screen traces to `config/` or computed data with its status (CLAUDE.md Section 20). No Section 3.3 claims anywhere. No "days early" wording (mode is `same_day`).
  - Oct 9: no Section 3.3 claims in app, config, backend or README; `glut_in_days` renders only in `predictive` mode. Number tracing waits on 2.2 figures and phone screens.

### 6. Stat report generation
- [ ] 6.1 One report of the final numbers for both replay days from the live or local API: per load and 10-load plan, waste avoided (range), redirected, extra km, diesel, CO2, net value default vs advised. Save as `analysis/out/demo_report.json` (+ a readable `.md`).

### 7. Result verification and classification
- [ ] 7.1 Label every figure in the report as observed (CEDA prices and arrivals, NASA POWER weather, Amazon Location routes), model output (R, net value, spoilage, waste avoided) or assumption (Section 10 placeholders).
- [ ] 7.2 Two numbers judges may question; keep them labelled:
  - Waste avoided on 2025-03-19 is driven mostly by the placeholder 40% dump share (D12). Always "(estimate)".
  - Price sensitivity: every market uses the spec's fallback b = -0.5 because price barely tracks arrivals in this data (D15). Stated in the README.

### 8. Branding and repo rename
- [ ] 8.1 App name, icon and splash in `app/app.json` / `app/assets/`.
- [ ] 8.2 Rename the GitHub repo (e.g. `annasetu`) in GitHub settings; then `git remote set-url origin https://github.com/Lakshya1901/<new-name>` and update any URLs in README.md.

### 9. README, final push, public repo
- [ ] 9.1 Update README.md with the stat report figures, screenshots in `docs/`, and the APK link (replace "TBD").
- [ ] 9.2 Merge the working branch into `main` (via a PR; confirm first). `edit/festive-darwin-bd1y1i` already merged on October 9.
- [ ] 9.3 Make the repo public. Check nothing secret is committed (no keys, `samconfig.toml`, `.env`).

## Tomorrow (October 10)

- [x] 10. Commit history check: clear messages, no secrets, no model identifiers, no `node_modules` or build output. Oct 9: no keys, `.env`, `samconfig.toml`, `node_modules`, build output or model IDs in any commit. Early messages (`v1`, `merge (#1)`) are terse; left as is (rewriting `main` is not worth it). Re-check before 9.3.
- [ ] 11. Demo video, 3 minutes or less: the live app on a phone, the 2025 Kolar price crash (2025-03-19), and the second case study (2023-09-29, documented Sept 2023 arrival glut, ten loads split; D18). Show "Replaying <date> data", label counterfactuals as modelled, waste avoided separate from redirected. Then fill the video link in README.md (replace "TBD").
- [ ] 12. Short writeup (submission form): problem, build, AWS usage (name the SAM CLI and every AWS service; CLAUDE.md Section 22.1).
  List the AI coding tools used (Claude Code), as the rules require: "You can use AI coding tools. List the ones you used in your writeup." (https://www.wemakedevs.org/aws/env/rules). Add the same line to README.md.

- [ ] 12b. Blog post (public, e.g. AWS Builder Center or Hashnode): the Kolar and city-mandi story, Prevent / Rescue / Recover, architecture diagram, how SAM CLI and each AWS service are used, what is real vs simulated (CLAUDE.md Section 18), limits, and "Built with Claude Code". Link it from README.md and the submission.

## Sunday (October 11)

- [ ] 13. Submission before 8:00 PM IST: public repo, video, writeup. Both team members have AWS Builder Center profiles with student verification.
