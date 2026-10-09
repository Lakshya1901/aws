# AnnaSetu: to do (handoff for a fresh Claude Code session)

Deadline: Sunday October 11, 2026, 8:00 PM IST.
Branch: `edit/beautiful-ritchie-ij5zmf` (`edit/festive-darwin-bd1y1i` was merged to `main` on October 9). Spec and every decision so far: `CLAUDE.md` (D1-D18 in Section 19.1).

## How to start the new session

1. Do steps 1.1-1.4 below first (credentials only reach a new session).
2. Start a new Claude Code cloud session on this repo and branch.
3. Paste this as the first message:

```
Read CLAUDE.md and TODO.md completely. Work through TODO.md in order, starting at
the first unchecked item. Confirm with me before any `sam deploy`, any change to
GitHub repo settings (rename, visibility), and any merge to main. Tick items in
TODO.md as they are done and commit TODO.md with the work.
```

## Current state (October 9)

- Backend: 85 tests pass (`python -m pytest backend/tests -q`). App: `npx tsc --noEmit` passes, Android export builds.
- Data: CEDA tomato snapshot 2022-2025 (7 Kolar-region markets, district level), NASA POWER weather for both replay windows.
- Demo replays (D18): 2023-09-06 (documented arrival glut at Kolar; headline) and 2025-03-19 (Kolar's 2025 low, below harvest cost).
- Blocking: `data/routes_cache.json` is empty, so `/recommend` and `/plan` return 422 `drive_time_unavailable` until step 2.1 runs (D11).
- Not yet done anywhere: AWS deploy, any run on a phone, native-speaker review, usability test.

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

### 2. Routes and deploy
- [ ] 2.1 Cache routes from the Kolar demo origin: `python scripts/cache_routes.py 13.137,78.134`. Add the demo FPO villages as `<village_id>=lat,lon` if used. Commit `data/routes_cache.json`.
- [ ] 2.2 Re-run both replay days locally (`python -m backend.handlers.local_server`, `REPLAY_DATE=2025-03-19` for the second) and record the real figures (top outlet, net ranges, waste avoided, redirected, extra km, 10-load split).
- [ ] 2.3 `cd infra && sam build && sam deploy --guided` (confirm first; creates billable resources). Pass `BedrockModelId` / `BedrockModelArns`.
  - Oct 9: `sam build` passes; 99 backend tests pass. Deploy waits for confirmation. Bedrock off (both parameters empty).
  - Oct 9: first deploy (NameSuffix abcd11, no AlarmEmail) failed: `annasetu-deployer` was denied `iam:CreateRole` (with tags) and `iam:DeleteRolePolicy` on `annasetu-*` roles; stack is `ROLLBACK_FAILED`. Needs the inline IAM policy fixed in the console (CreateRole, TagRole, DeleteRolePolicy and related on `role/annasetu-*`), then delete the stack and redeploy.
- [ ] 2.4 `python scripts/geocode_markets.py` (review the diff, commit), `python scripts/seed.py`, invoke ingest once with `{"as_of_date": "2023-09-06"}`, confirm MarketRisk rows.

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
- [x] 5.1 Full checks: `python -m pytest backend/tests -q`, `cd app && npx tsc --noEmit`, `cd infra && sam validate --lint`. Oct 9: 85 passed, tsc clean, template valid. Re-run after any later change.
- [x] 5.2 Reproducibility: re-run `python analysis/backtest.py --crop tomato` and `python analysis/second_replay.py`; outputs must be byte-identical to the committed files. Oct 9: JSON and both PNGs byte-identical (charts need matplotlib).
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
- [ ] 11. Demo video, 3 minutes or less: the live app on a phone, the 2025 Kolar price crash (2025-03-19), and the second case study (2023-09-06 arrival glut, ten loads split). Show "Replaying <date> data", label counterfactuals as modelled, waste avoided separate from redirected. Then fill the video link in README.md (replace "TBD").
- [ ] 12. Short writeup (submission form): problem, build, AWS usage (name the SAM CLI and every AWS service; CLAUDE.md Section 22.1).
  List the AI coding tools used (Claude Code), as the rules require: "You can use AI coding tools. List the ones you used in your writeup." (https://www.wemakedevs.org/aws/env/rules). Add the same line to README.md.

- [ ] 12b. Blog post (public, e.g. AWS Builder Center or Hashnode): the Kolar and city-mandi story, Prevent / Rescue / Recover, architecture diagram, how SAM CLI and each AWS service are used, what is real vs simulated (CLAUDE.md Section 18), limits, and "Built with Claude Code". Link it from README.md and the submission.

## Sunday (October 11)

- [ ] 13. Submission before 8:00 PM IST: public repo, video, writeup. Both team members have AWS Builder Center profiles with student verification.
