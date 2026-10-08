# AnnaSetu: CLAUDE.md (single source of truth)

This file is the complete specification for AnnaSetu. Read all of it before planning or coding. If something here is ambiguous, contradictory or silent on a decision you need, stop and ask; do not guess.

---

## 1. One-line summary

AnnaSetu stops edible fruit and vegetables from becoming waste before the truck leaves the farm. It tells farmer collectives anywhere in India where each load should go (sell fresh, hold, process, donate, feed or compost) using public mandi data, and allocates loads across markets so they don't all crash the same one.

- Track: Waste and Energy (food waste prevention)
- Platform: mobile app for Android and iOS, backed by AWS
- Scope: pan-India architecture; demo replays real, documented 2025 gluts

---

## 2. Hackathon constraints

- Event: WeMakeDevs x AWS Environmental Hacks, https://www.wemakedevs.org/aws/env
- Dates: October 8-11, 2026. Submission deadline: Sunday October 11, 8:00 PM IST.
- Submission: public repo, demo video of 3 minutes or less, short writeup (problem, build, AWS usage).
- There is no live demo. Judges score only what is submitted. A feature not shown in the video does not count.
- Judging: idea and impact, AWS usage, design and usability.
- AWS must be central to how the product works, not bolted on.
- Prize eligibility (rules page, https://www.wemakedevs.org/aws/env/rules): the project must use at least one AWS open-source tool or be deployed on AWS. The event page's AWS stack names SAM CLI, LocalStack, Lambda, API Gateway and Step Functions. AnnaSetu meets both conditions: it is deployed on AWS (Section 15) and built, run locally and deployed with the AWS SAM CLI (open source). See Section 22.
- Both team members need AWS Builder Center profiles with student verification.

---

## 3. The problem

### 3.1 What is broken

India's fresh produce is lost mostly at or near the farm gate, and mostly because its market value collapses before the food itself spoils. The decision that causes the loss (whether to harvest, where to send the truck) is made by the actor with the least information. The data that could prevent it (mandi prices and arrivals) is public but never turned into a per-load decision before loading.

### 3.2 Evidence (use these figures exactly as stated)

| Fact | Figure | Grade | Source |
| --- | --- | --- | --- |
| Total post-harvest loss, all agri produce | About Rs 1.53 lakh crore a year (2020-22) | Established | NABCONS 2022, https://insights.dataful.in/articles/from-guava-to-milk-what-food-loss-reveals-about-indias-supply-chains |
| Fruit and vegetable loss | Fruits 6.02-15.05%, vegetables 4.87-11.61%; 7.36 Mt and 11.97 Mt a year | Established | Rajya Sabha Feb 2025, https://rsdebate.nic.in/bitstream/123456789/758453/1/PQ_267_07022025_U572_p312_p312.pdf |
| Where tomato loss happens | 8.37% on farm vs 3.25% at market | Established | https://www.freshplaza.com/asia/article/9756104/india-reports-high-guava-and-tomato-losses/ |
| Where guava loss happens | 11.59% on farm vs 3.46% at market | Established | Same |
| Kolar 2025 glut | Harvest and transport about Rs 70 per 15 kg box vs sale price as low as Rs 30; crops left unharvested | Documented | https://www.outlookbusiness.com/explainers/farmers-in-india-struggle-with-falling-tomato-prices-whats-behind-the-price-drop |
| Same food, different value | Udumalaipettai tomatoes dumped while the same box sells about 5x more across the Kerala border | Documented | https://www.onmanorama.com/news/kerala/2025/09/04/tomato-farmers-discarding-produce-roadside.html |
| Share of fresh produce the cold chain serves | About 10% | Established | NCCD Sept 2025, https://nccd.gov.in/uploads/ET_in_cold_chain_sector_in_India_v8_3bfe3b8148.pdf |
| Cold storage built for potatoes | Over 75% of capacity | Established | Same |
| Whole cold chain energy use | About 5 TWh a year, mostly old potato stores | Established | Same |

Scale anchor: 1% of the 19.3 Mt of fruit and vegetables lost each year is about 193,000 tonnes of food.

### 3.3 Claims we never make

- "40% of food is wasted" (unsupported; the government answered with far lower figures).
- That AnnaSetu addresses the full Rs 1.53 lakh crore (it includes cereals, sugarcane, spices). We target perishables.
- National energy savings (cold chain energy is small; the evidence doesn't support it).
- A percentage reduction in loss before it is measured.

### 3.4 Root causes

1. Blind dispatch: decisions use yesterday's local price and a trader's word. Software can fix this.
2. Everyone moves at once: growers in a belt harvest together and ship to the nearest mandi; arrivals spike, prices crash. Software can fix this only if it allocates, not just predicts.
3. Nobody is paid to prevent loss: commission agents, cold stores and transporters earn on volume, rent or trips. Software can only give the risk-bearer better options.
4. Few escape routes: most vegetables never touch a cold link; processors and food banks aren't connected to the moment of a glut. Recommendations must work inside this constraint.

### 3.5 Where the problem sits in the journey

| Stage | Decision | Pain today | AnnaSetu |
| --- | --- | --- | --- |
| Pre-harvest | Harvest now? How much? | No view of the coming glut | Glut Radar |
| Harvest and load | Which market? Send or hold? | Old local price and hearsay | Dispatch Advisor: net value per outlet |
| On the road | Nothing left to decide | Shelf life lost, never counted | Spoilage cost in the ranking |
| At the mandi | Sell or dump? | Price below the cost of sending | Allocation keeps markets from glutting |
| After sale | Markdown or discard? | No channel for unsold food | Second Life: process, donate |

The first two stages are the decision window where loss is set. Interventions at the mandi gate are too late.

### 3.6 What we are not building, and why

| Rejected idea | Reason |
| --- | --- |
| Cold storage booking | NCCD is building a national booking platform |
| Photo quality grading | Solved by startups (Intello Labs, Agrograde) |
| In-transit sensors | Needs hardware |
| Retail or household waste | No data, weak demo |
| Generic spoilage predictor | Loss mechanisms differ too much by crop |

---

## 4. Users

**Primary: FPO dispatch manager.** Runs daily dispatch for a farmer producer organisation of a few hundred growers. Decides each morning who harvests, how much and where each truck goes. Uses WhatsApp and phone calls, comfortable with a smartphone, not dashboards. Speaks a regional language. Bears the blame when a load sells below cost. Chosen first because they control enough volume to split loads across markets, which is what prevents herding.

**Secondary:** individual farmers asking by voice; district horticulture officers watching the Glut Radar to trigger diversion schemes such as Operation Greens.

**Job to be done:** When my members' crop is ready, I want to know where each load should go today and what it will actually earn after costs, so I can avoid sending food into a crash and explain the decision to my members.

---

## 5. Product

Four parts around one decision: where should this load go?

1. **Glut Radar.** Daily glut risk for every reporting mandi in India, per crop. Shows safe, watch or glut, and days of warning in predictive mode.
2. **Dispatch Advisor.** For one load (crop, quantity, origin, harvest timing), ranks every reachable outlet by net value per kg after freight, fees and spoilage, with ranges. Allocates multiple loads across outlets so AnnaSetu never pushes a market into glut itself.
3. **Second Life.** When no fresh market pays, walks down the food waste hierarchy: hold (storable crops only), processor, food bank, animal feed or compost. Never a dump.
4. **Impact Ledger.** For every decision: kg waste avoided (expected) and kg redirected (shown separately), extra km, diesel, CO2, embedded water.

AnnaSetu advises; people decide. Every recommendation can be overridden, and overrides are logged.

---

## 6. Scope: pan-India with demo regions

- **Architecture is national.** Ingest covers every AGMARKNET market reporting the configured crops. Any origin in India gets recommendations from markets within the reachable radius.
- **Crops (MVP):** tomato (fully tuned), onion, potato, banana. Adding a crop means adding a profile and copy, not code.
- **Demo regions** (real, documented gluts, replayed from historical data):
  - Kolar tomato belt (Karnataka and Andhra border): Kolar, Chintamani, Srinivaspura, Madanapalle, Bengaluru; January-April 2025 glut.
  - A second region to prove pan-India, chosen by the data check. Candidate: Nashik onion belt (Lasalgaon, Pimpalgaon, Nashik, Pune). Verify a documented glut and data density before committing.
- **Second Life outlets** are seeded for the demo regions only; the schema is national.
- **Cost inputs** are configured per state, with national defaults.

---

## 7. Operating modes

| Mode | When | Behaviour |
| --- | --- | --- |
| `predictive` | Backtest shows arrivals rising at least 2 days before prices fall, on most crashes | Radar projects risk `lead_days` ahead; recommendations use projected arrivals |
| `same_day` | Arrivals don't lead price, or arrivals unavailable | Radar shows today's risk only; no "days early" claims anywhere in the app or video |

One flag in `config/model.json`, settable per crop. All other components are identical. If unknown, default to `same_day`.

---

## 8. Data layer

### 8.1 Sources

| Source | Fields | Refresh | Access | Fallback |
| --- | --- | --- | --- | --- |
| AGMARKNET price and arrival reports | date, state, district, market, commodity, variety, arrivals, min/max/modal price | Daily, plus one-time 3-year history | Undocumented public backend (client: https://github.com/makrand999/agmarknet-api); may rate-limit or block cloud IPs | Snapshot CSV in S3; data.gov.in for prices |
| CEDA Agri Market Data (Ashoka University), https://agmarknet.ceda.ashoka.edu.in | AGMARKNET daily min/max/modal price (Rs/quintal) and arrivals (tonnes), aggregated per Census 2011 district | Monthly refresh by CEDA | Public JSON API, no key (`backend/adapters/ceda.py`) | Snapshot CSV |
| data.gov.in mandi prices, resource 9ef84268-d588-465a-a308-a864a43d0070 | state, district, market, commodity, variety, grade, arrival_date, min/max/modal price (no arrivals) | Daily | Free API key | Snapshot |
| Open-Meteo | Hourly temperature, relative humidity; forecast and history | Per request, cached 6 h | Free, no key | Monthly averages per state in config |
| Amazon Location Service | Market geocoding (once); route distance and drive time | Geocode once; routes cached per pair | AWS | Haversine distance x road factor 1.3, flagged as estimate |

### 8.2 Cleaning and units

- Prices are Rs per quintal; divide by 100 for Rs per kg.
- Verify arrival units on first pull (tonnes vs quintals); store tonnes.
- Aggregate varieties per market-day: arrivals summed, modal price weighted by arrivals.
- Demo snapshot (D1): agmarknet.gov.in and api.data.gov.in refuse connections from cloud IPs, so the 2022-2025 history comes from CEDA, which is district level. Each "market" in `config/markets.json` is one district aggregate, named after its main tomato market town (Kolar district = Kolar, Chittoor = Madanapalle, Chikkaballapura = Chintamani). CEDA's district price is its own aggregate, not arrival-weighted by us. Market-level AGMARKNET data replaces it when available; the engine is unchanged. Districts with a unit problem or no prior-year baseline are excluded and listed in `config/markets.json`.
- Market names map to internal IDs through `config/markets.json`; never fuzzy-match at runtime.
- Missing days stay missing, never zero. Compute risk only when at least 5 of the last 7 days exist.

### 8.3 Market geocoding (pan-India)

AGMARKNET has no coordinates. `scripts/geocode_markets.py` geocodes each market once with Amazon Location place search using "market, district, state, India", writes lat/lon and a confidence to `config/markets.json`, and supports manual overrides. Low-confidence markets are excluded from routing until fixed. Commit the result.

### 8.4 Reachable outlets

Prefilter markets within `max_radius_km` (default 300, config) by straight-line distance, keep the nearest 15, then route. Interstate sales are allowed; fees follow the destination state.

### 8.5 Storage

S3 bucket `annasetu-data-<suffix>`:
```
raw/agmarknet/<crop>/<yyyy-mm-dd>.json
raw/datagov/<yyyy-mm-dd>.json
snapshot/agmarknet_<crop>_<from>_<to>.csv
backtest/results_<run_id>.json
```

DynamoDB (on-demand):

| Table | PK | SK | Attributes |
| --- | --- | --- | --- |
| MarketDay | `market_id#crop` | `date` | arrivals_t, min/max/modal_price_kg, source, ingested_at |
| MarketRisk | `crop` | `market_id` | as_of_date, arrival_ratio, price_change_3d, risk_level, lead_days, elasticity_b, baseline_t, data_complete, state, lat, lon |
| Outlets | `outlet_id` | - | type (mandi, processor, food_bank, feed_compost), name, state, lat, lon, crops, min_qty_kg, offer_price_kg, contact, verified, seeded |
| Plans | `plan_id` | - | created_at, loads, allocations, impact, language, explanation inputs and outputs |

Crop profiles, cost assumptions, markets and copy live in versioned JSON in `config/`, not the database.

### 8.6 Freshness

- If a market's latest data is more than 2 days old: `stale: true`, ranges widened, banner shown.
- If AGMARKNET fails: switch to data.gov.in for prices, mark arrivals unavailable, force `same_day` for affected crops.

---

## 9. Model

Pure Python in `backend/core/`. Every parameter in `config/model.json`. No deep learning.

### Step 1. Glut risk per market (daily)

```
R(m,t)  = A7(m,t) / B(m,t)
A7      = 7-day average arrivals
B       = median arrivals for ISO weeks w-1..w+1 in prior years
dP(m,t) = (P(m,t) - P(m,t-3)) / P(m,t-3)
```

| Level | Default rule (tuned by backtest) |
| --- | --- |
| safe | R < 1.3 |
| watch | 1.3 <= R < 2.0, or dP < -15% |
| glut | R >= 2.0, or (R > 1.5 and dP < -25%) |

Predictive mode also projects R forward `lead_days` from the 3-day trend and neighbouring markets' ratios.

### Step 2. Price on arrival, including AnnaSetu's own loads

```
P_hat(j) = P(j) * ((A(j) + dA(j)) / A(j)) ^ b(j)
```
b fitted per market by regressing ln(price) on ln(arrivals), clipped to [-1.5, -0.1]; if R^2 < 0.2 use -0.5. Range = +/- one residual standard deviation. dA = quantity AnnaSetu has already allocated there.

### Step 3. Spoilage on the trip (no sensors)

```
SL(T) = SL_ref * Q10 ^ (-(T - T_ref) / 10)
f(j)  = (t_since_harvest + t_drive(j) + t_wait) / SL(T)
s(j)  = min(1, alpha * f(j))
```
T = mean forecast temperature over the trip. t_wait default 6 h at mandis.

### Step 4. Net value per kg

```
net(j) = P_hat(j) * (1 - s(j))
         - freight_rs_per_tonne_km * distance_km(j) / 1000
         - P_hat(j) * (fee_pct(state) + commission_pct(state))
         - P_hat(j) * handling_pct(state)
```
Second-life outlets use offer price (processor) or 0 (food bank, feed, compost) for P_hat.

### Step 5. Allocation (anti-herding)

1. Sort the day's loads by quantity, largest first.
2. For each load, compute net(j) for all reachable outlets using current dA.
3. Assign to the best outlet unless it pushes that market's projected R into glut; then the next best. Projected R = A7 recomputed with today's arrivals plus dA(j), divided by B (same definition as Step 1).
4. Add to that market's dA; repeat.
5. If no fresh market has net > 0: processor, then food bank, then feed or compost.
6. If best net < harvest cost per kg: advise delaying harvest (storable crops) or harvesting only what has a buyer (non-storable).

Greedy is sufficient. No optimiser.

### Step 6. Waste avoided

```
W     = Q * (L_default - L_advised)
L(j)  = s(j) + u(R(j))
```
Default = nearest mandi. u = unsold or dumped share, a placeholder heuristic until calibrated by an FPO interview:

| R | u |
| --- | --- |
| < 1.3 | 0% |
| 1.3-2.0 | 5% |
| 2.0-3.0 | 20% |
| > 3.0 | 40% |

Price-below-cost dump (D12): if the default market's mid net value per kg is below the crop's harvest cost, the load counts as likely dumped or left unharvested there (documented Kolar 2025, Section 3.2). Then u_default = max(u(R), 0.40), with low 0.20 and high 0.40 (values reused from the u(R) table; placeholder). Applies only to the default side.

Always show both W (waste avoided, range) and Q (redirected). Never merge them.

Range for W: mid uses u(R) of the band R falls in; low and high use u of the band below and above for the default market, combined with the low and high spoilage estimate. Labelled "(estimate)".

### Resource accounting

- extra_km vs default market
- diesel_l = extra_km * litres_per_km (placeholder)
- co2_kg = diesel_l * 2.68
- water_l = W * crop water footprint (to source per crop)

Null values render "not yet estimated", never zero.

---

## 10. India context inputs

All in `config/assumptions.json`, each with `value`, `unit`, `status` (sourced | assumption | placeholder), `source`, and optional per-state overrides. The UI adds "(estimate)" to anything not sourced.

| Input | Default | Status | Source / how to fill |
| --- | --- | --- | --- |
| Tomato harvest + local transport | Rs 70 per 15 kg box (~Rs 4.7/kg) | sourced (Kolar 2025) | Outlook Business |
| Freight, small truck | Rs 11 per tonne-km | placeholder | 14 ft LCV quoted at Rs 20-35 per km (Indian truck-rate guides, 2025-26) divided by an assumed 2.5 t payload; FPO interviews per region |
| Market fee | Karnataka 0% on fruit and vegetables (sourced: Karnataka APMC Act 1966 s.65, https://indiankanoon.org/doc/117259766/; user charges not found). Andhra Pradesh 1% (sourced: AP Agricultural Marketing Dept, levied on purchases, https://spsnellore.ap.gov.in/agricultural-marketing-department/; deducting it from the seller is an assumption). Default 1% (assumption) | per state | State APMC rules |
| Commission | Karnataka 5% (https://citizenmatters.in/how-bengaluru-apmc-system-works-farm-laws-yeshwanthpur-yard-commission-agents-farmers-cartelisation/); Andhra Pradesh 4%, reported range 4-10% (https://www.thenewsminute.com/article/how-social-capital-enabled-tomato-farmers-andhra-sell-produce-during-lockdown-123892); default 5% | placeholder | FPO interviews |
| Handling (hamali) | 1% of sale (`handling_pct`; Deccan Herald: "5% commission and 1% hamali", https://www.deccanherald.com/india/karnataka/state-not-denotify-fruits-veggies-1993495) | placeholder | FPO interviews |
| Diesel use | 0.14 litres per km (Tata 407-class, published 7-10 km/l, lower end for loaded running; https://trucksbuses.com/trucks/cargo-truck/tata-sfc-407-bsiv/mileage) | placeholder | Vehicle type |
| Wait at mandi | 6 h | assumption | FPO interviews |
| Dump share table u(R) | Section 9 | placeholder | FPO interviews |
| Reachable radius | 300 km | assumption | Config |
| Stale-data range widening | 1.5x the residual standard deviation | assumption | Config |

### Languages

| Function | Support |
| --- | --- |
| App text (MVP) | English, Hindi, Kannada; add others via `config/copy/<lang>.json` |
| Voice in (Transcribe) | Hindi, Kannada, Indian English for MVP; Transcribe supports more Indian languages; verify each before enabling |
| Voice out (Polly) | Hindi and Indian English only. No Kannada or other regional voices; say this openly in settings and README |

The user picks a language on first launch. Recommendation text appears in that language; spoken replies in Hindi or English.

---

## 11. Crop profiles

One JSON file per crop in `config/crops/`. A profile with a null required field is rejected with a clear message; never guessed.

| Parameter | Tomato | Onion | Potato | Banana |
| --- | --- | --- | --- | --- |
| Recommended storage | ~10 C ripe, ~13 C mature green | ~0 C, 70-75% RH | to source | 12-15 C |
| Good-condition storage life | days to ~2 weeks | ~6-8 months | months (cold store) | weeks, ripening-dependent |
| SL_ref at T_ref (25 C) | 132 h, range 96-168 h (4-7 days holding at ambient for ripening stages; https://www.researchgate.net/publication/294485852) | placeholder | placeholder | placeholder |
| Q10 | 2.0, derived from UC Davis respiration rates for mature-green tomato: 8-14 mL CO2/kg.h at 15 C, 18-26 at 25 C (https://postharvest.ucdavis.edu/produce-facts-sheets/tomato; page read through a search excerpt, verify) | placeholder | placeholder | placeholder |
| alpha | 0.31, placeholder: calibrated so a 14 h trip (6 h since harvest + 2 h drive + 6 h wait) at 25 C gives 3.25% loss, the market-stage tomato loss in Section 3.2 | placeholder | placeholder | placeholder |
| Storable (hold option) | no | yes | yes | limited |
| Water footprint | 184 L/kg world average, tropical production 200-900 L/kg (Hoekstra, cited in Nederhoff and Stanghellini 2010, https://edepot.wur.nl/156932) | placeholder | placeholder | placeholder |
| Harvest cost per kg | ~Rs 4.7 (Kolar) | placeholder | placeholder | placeholder |
| Second life | puree/paste, food bank, compost | dehydration, food bank | processing, food bank | ripening/retail, chips, food bank, feed |

Sources: ASHRAE vegetables chapter (https://handbook.ashrae.org/Handbooks/R26/IP/r26_ch37/r26_ch37_ip.aspx), Indian tomato supply chain study (https://www.mdpi.com/2071-1050/15/2/1331), USDA Handbook 66, ICAR-NRCB (https://nrcb.org.in/Pages/achievements_pht). Present these in the app as "reference post-harvest parameters" and state that spoilage is estimated from outside temperature and travel time.

Profile shape:
```json
{
  "crop_id": "tomato",
  "names": {"en": "Tomato", "hi": "टमाटर", "kn": "ಟೊಮೆಟೊ"},
  "agmarknet_commodity": "Tomato",
  "t_ref_c": 25,
  "sl_ref_hours": null,
  "q10": null,
  "alpha": null,
  "storable": false,
  "harvest_cost_rs_per_kg": 4.7,
  "unit_box_kg": 15,
  "water_l_per_kg": null,
  "second_life": ["processor", "food_bank", "feed_compost"],
  "sources": {"harvest_cost_rs_per_kg": "Outlook Business, Apr 2025"}
}
```

---

## 12. Bedrock

Two jobs only. It never calculates, chooses outlets or adds numbers. Small fast Claude model available in ap-south-1; model ID in `config/model.json`; temperature 0; 3 s timeout.

**Job 1: parse a spoken load.**
```
System: You extract a produce load from a spoken request in Hindi, Kannada or English.
Return only JSON:
  crop: one of the configured crop_ids, or null
  quantity_kg: number or null (boxes at the crop's unit_box_kg, quintal = 100 kg, tonne = 1000 kg)
  origin_place: string or null
  harvest: "today" | "tomorrow" | "harvested" | null
  confidence: "high" | "low"
If a field is not clearly stated, return null. Never guess.
```
Any null or low confidence opens the Confirm screen.

**Job 2: explain a recommendation.** Input is a JSON of computed facts only.
```
System: You explain a dispatch recommendation to an FPO manager.
Use ONLY facts in the JSON. Add no numbers, places or claims not in it.
At most two short sentences in {language}.
Sentence 1: where to send and the most important reason, citing one number.
Sentence 2 (optional): the main tradeoff or uncertainty.
If data_stale is true, say prices may be out of date.
Return JSON: {"text": "...", "language": "<code>"}
```

**Guardrails:** every number in the output must appear in the input, else use the template; template per language for failures and timeouts; log input and output to Plans.

---

## 13. API contract

All JSON via API Gateway. The app never calls AWS services directly.

| Method and path | Purpose | Request | Response |
| --- | --- | --- | --- |
| GET /risk?crop=&state=&lat=&lon= | Glut Radar | crop, optional state or location | markets with risk_level, ratio, price, change_3d, as_of_date, mode |
| POST /voice/upload | Upload slot | language, content_type | presigned S3 URL, audio_key |
| POST /voice/parse | Transcribe + parse | audio_key, language | transcript, fields, confidence |
| POST /recommend | One load | crop, quantity_kg, origin {lat, lon, place}, harvest, language, plan_id? | ranked outlets, default outlet, impact, explanation, data freshness, assumptions_used |
| POST /plan | All loads together | loads[], language | allocation per load, dA per market, total impact |
| POST /speak | Spoken reply | text, language (hi or en) | presigned MP3 URL |
| GET /impact?plan_id= | Impact Ledger | plan_id | redirected_kg, waste_avoided_kg range, extra_km, diesel_l, co2_kg, water_l |

Example `/recommend` response (illustrative values):
```json
{
  "plan_id": "p_20250404_01",
  "mode": "predictive",
  "data": {"as_of_date": "2025-04-04", "stale": false},
  "top": {"outlet_id": "madanapalle", "type": "mandi",
          "net_rs_per_kg": {"low": 7.8, "mid": 9.4, "high": 11.0},
          "distance_km": 62, "drive_hours": 1.6, "spoilage_share": 0.03,
          "risk_level": "safe", "arrival_ratio": 1.1},
  "default": {"outlet_id": "kolar", "net_rs_per_kg": {"low": -1.2, "mid": 0.4, "high": 1.6},
              "risk_level": "glut", "arrival_ratio": 3.1},
  "alternatives": [{"outlet_id": "bengaluru", "net_rs_per_kg": {"low": 6.0, "mid": 8.1, "high": 9.9}}],
  "impact": {"redirected_kg": 2000,
             "waste_avoided_kg": {"low": 400, "mid": 600, "high": 800},
             "extra_km": 37, "diesel_l": null, "co2_kg": null, "water_l": null},
  "explanation": {"language": "kn", "text": "...", "source": "bedrock"},
  "assumptions_used": ["freight_rs_per_tonne_km", "dump_share_table"]
}
```

| Case | API | User sees |
| --- | --- | --- |
| Data > 2 days old | stale: true, wider ranges | Yellow banner |
| No arrivals | mode: same_day | No "days early" |
| No fresh market pays | top is processor/food bank | Second Life screen |
| Harvest doesn't pay | advice: delay_harvest or harvest_to_order | Plain warning with numbers |
| Voice not understood | null fields, low confidence | Confirm screen, fields highlighted |
| No reporting markets in radius | 422 | "No reporting markets near you for this crop" |
| Crop profile incomplete | 422 | "This crop isn't set up yet" |
| Bedrock/Polly fails | template text, no audio | Text shown, audio hidden |
| Routing fails | haversine estimate | Distance marked "approx." |

---

## 14. Mobile app design

### 14.1 Platform

- React Native with Expo, TypeScript; one codebase for Android and iOS.
- Android is the primary demo device (most FPO staff and farmers use Android). iOS runs via Expo Go or simulator; no App Store or TestFlight submission.
- Android APK via EAS Build, linked in the README.
- Libraries: expo-audio (record, play), expo-location (origin), expo-font (Noto Sans Kannada, Noto Sans Devanagari), AsyncStorage (cache last risk data and language).
- Map is optional and needs an Expo development build. Ship the market list first.

### 14.2 Screens

| Screen | Question | Default | Other states |
| --- | --- | --- | --- |
| Language (first launch) | Which language? | Large buttons | - |
| Today (Glut Radar) | Is a glut coming near me? | Nearby markets for the chosen crop, colour + word + icon, ratio, price | Loading, stale, same_day, market not reported |
| New load | What am I sending? | Big mic button; form below (crop, qty, place, harvest) | Recording, processing, parse failed |
| Confirm | Did we hear you right? | Editable chips | Low confidence: all highlighted |
| Recommendation | Where should this load go? | The card, plus two alternatives | Stale, Second Life, delay harvest, template text |
| Today's plan | How do I split all loads? | Loads with outlets, added qty per market | Market capped |
| Impact | What did we save? | Session totals | "Not yet estimated" values |

### 14.3 Recommendation card

```
Send 2,000 kg to Madanapalle
Kolar is receiving 3.1x its usual tomatoes today.

Waste avoided   about 600 kg   (likely 400-800 kg)
Redirected      2,000 kg away from a likely glut
Extra distance  +37 km, about X litres diesel

You'd earn      Rs 9-12 per kg   (Kolar: Rs 0-2)

[Why not Kolar?]  [Listen]  [Use this]
```

Rules: waste avoided first, earnings after; never merge waste avoided and redirected; ranges or "(estimate)" on every figure; "Why not X?" opens a before/after comparison of default vs recommended on the same load; "Use this" and overrides are logged.

### 14.4 Voice flow

1. Hold the mic, speak ("Holur-inda eradu ton tomato, ivattu koyilu" / "do ton tamatar, aaj todenge").
2. Release; upload to S3 via presigned URL; "Listening..." state.
3. Transcribe, then Bedrock parse; Confirm screen.
4. User confirms or edits.
5. Card in the chosen language; "Listen" plays Polly audio in Hindi or English.

Target under 15 s from release to card. Clips under 20 s. Record AAC/m4a; if Transcribe rejects it, record WAV.

### 14.5 Copy (native-speaker review required before the demo)

| Key | English | Hindi | Kannada |
| --- | --- | --- | --- |
| new_load | New load | नया लोड | ಹೊಸ ಲೋಡ್ |
| speak | Hold to speak | बोलने के लिए दबाकर रखें | ಮಾತನಾಡಲು ಒತ್ತಿ ಹಿಡಿಯಿರಿ |
| send_to | Send to {outlet} | {outlet} भेजें | {outlet}ಗೆ ಕಳುಹಿಸಿ |
| glut_reason | {market} is receiving {ratio}x its usual {crop} today | आज {market} में सामान्य से {ratio} गुना {crop} की आवक है | ಇಂದು {market}ಗೆ ಸಾಮಾನ್ಯಕ್ಕಿಂತ {ratio} ಪಟ್ಟು {crop} ಆವಕವಿದೆ |
| waste_avoided | Waste avoided | टाली गई बर्बादी | ತಪ್ಪಿಸಿದ ವ್ಯರ್ಥ |
| redirected | Redirected | दूसरी जगह भेजा गया | ಬೇರೆಡೆ ಕಳುಹಿಸಿದ್ದು |
| earnings | You'd earn | अनुमानित कमाई | ಅಂದಾಜು ಆದಾಯ |
| extra_km | Extra distance | अतिरिक्त दूरी | ಹೆಚ್ಚುವರಿ ದೂರ |
| stale | Prices may be out of date | कीमतें पुरानी हो सकती हैं | ಬೆಲೆಗಳು ಹಳೆಯದಾಗಿರಬಹುದು |
| risk levels | Safe / Watch / Glut | सुरक्षित / ध्यान दें / अधिक आवक | ಸುರಕ್ಷಿತ / ಗಮನಿಸಿ / ಅತಿಯಾದ ಆವಕ |
| why_not | Why not {market}? | {market} क्यों नहीं? | {market} ಏಕೆ ಬೇಡ? |
| estimate | estimate | अनुमान | ಅಂದಾಜು |

### 14.6 Visual and accessibility

- Base text 16 pt minimum; card numbers 24 pt bold; touch targets at least 48 dp.
- Risk always colour + word + icon.
- High contrast, readable in sunlight.
- Works on slow connections: cached last risk data, small payloads, clear loading states.
- Before recording the demo: a first-time user gets a recommendation by voice without help and can repeat the reason; a native speaker approves every string.

---

## 15. AWS

### 15.1 Services (all in ap-south-1)

| Service | Resource | Config |
| --- | --- | --- |
| EventBridge Scheduler | daily-ingest | 21:00 IST daily |
| Lambda | ingest | 1024 MB, 15 min; all markets for configured crops; computes MarketRisk |
| Lambda | advisor | 512 MB, 15 s; /risk, /recommend, /plan, /impact |
| Lambda | voice | 256 MB, 30 s; /voice/*, /speak |
| API Gateway | HTTP API | throttle 10 rps; simple API key for the demo app |
| S3 | annasetu-data-<suffix> | private |
| S3 | annasetu-audio-<suffix> | private; lifecycle delete after 1 day |
| DynamoDB | MarketDay, MarketRisk, Outlets, Plans | on-demand |
| Transcribe | batch jobs | hi-IN, kn-IN, en-IN |
| Polly | SynthesizeSpeech | Hindi and Indian English voices, MP3 |
| Bedrock | InvokeModel | one small Claude model |
| Location Service | place index, route calculator | geocode markets once; routes cached |
| SSM Parameter Store | /annasetu/datagov_key | SecureString |
| CloudWatch | logs, alarm | alarm on ingest failure |

If ingest exceeds Lambda limits nationally, split by state with a Step Functions map or one invocation per state; do not add this unless needed.

### 15.2 IAM (one role per function, least privilege)

| Role | Allowed |
| --- | --- |
| ingest-role | S3 put/get data bucket; DynamoDB write MarketDay, MarketRisk; SSM get key |
| advisor-role | DynamoDB read all, write Plans; Bedrock InvokeModel (one model); Location CalculateRoute |
| voice-role | S3 put/get audio bucket; Transcribe start/get; Polly SynthesizeSpeech; Bedrock InvokeModel (one model) |

No AWS credentials in the app or the repo.

### 15.3 Cost

- AWS Budget alert (e.g. USD 10) before deploying.
- Lambda, DynamoDB, S3 stay within free-tier levels at demo scale; Transcribe and Polly have 12-month free tiers for new accounts; Bedrock costs cents. Verify on AWS pricing pages.
- Cache routes, weather and geocodes.

### 15.4 Deploy

1. Enable Bedrock model access in ap-south-1; test one prompt.
2. Put the data.gov.in key in Parameter Store.
3. `sam build && sam deploy --guided` in `infra/`.
4. Run `scripts/geocode_markets.py`; commit `config/markets.json`.
5. Upload snapshots; run `scripts/seed.py` for Outlets.
6. Invoke ingest once; confirm MarketRisk rows.
7. Set API URL and key in the app's env; `eas build -p android --profile preview`.
8. Smoke test on a real Android phone: one text and one voice recommendation.

---

## 16. Repository structure

```
annasetu/
├── CLAUDE.md
├── README.md                 problem, demo video, APK link, architecture, AWS usage, limits
├── infra/template.yaml       SAM: Lambdas, API, tables, buckets, schedule, IAM
├── backend/
│   ├── core/                 pure Python, no AWS imports
│   │   ├── risk.py  pricing.py  spoilage.py  netvalue.py  allocate.py  impact.py
│   ├── adapters/             all external calls
│   │   ├── ceda.py  agmarknet.py  datagov.py  weather.py  location.py  bedrock.py  speech.py
│   ├── handlers/             thin Lambda wrappers
│   │   ├── ingest.py  advisor.py  voice.py
│   └── tests/
├── config/
│   ├── model.json  assumptions.json  markets.json  outlets.json
│   ├── crops/                tomato.json onion.json potato.json banana.json
│   └── copy/                 en.json hi.json kn.json
├── data/
│   ├── snapshot/             or a script that rebuilds it
│   └── distance_fallback.json
├── analysis/
│   ├── backtest.py           deterministic CLI: lead-lag, thresholds, price gaps; writes results JSON and charts
│   └── backtest.ipynb        viewer only: loads backtest.py outputs, video charts
├── scripts/                  build_snapshot.py  geocode_markets.py  seed.py
├── app/                      Expo app
│   ├── app/                  screens (expo-router)
│   ├── components/           RecommendationCard, RiskList, MicButton, CompareSheet
│   ├── i18n/                 reads config/copy
│   └── api/                  typed client for the API contract
└── docs/                     architecture.png, screenshots
```

---

## 17. Demo, backtest and tests

### 17.1 Demo dataset

- 3 years of daily arrivals and prices for configured crops nationally (or at least the demo regions if national history is too slow to pull).
- Demo day chosen from the backtest: the clearest gap between the glutted default market and an alternative.
- Historical weather for that day.
- Five demo loads from real FPO villages in the demo region.
- App shows "Replaying <date> data" openly in replay mode.

### 17.2 Backtest (analysis/backtest.ipynb)

1. Daily table of arrivals and modal price per market.
2. Arrival ratio vs seasonal baseline.
3. Cross-correlate ratio with 1-7 day forward price change; record the strongest lag.
4. Crash days: price down > 25% in 3 days, or below harvest cost per kg.
5. For each crash, first watch/glut flag; days between = lead.
6. On crash days, net-of-cost gap to alternative markets.
7. Tune thresholds for early flags vs false alarms; report both.
8. Export charts for the video.

| Result | Action |
| --- | --- |
| Lead >= 2 days on most crashes, alternative pays | predictive; video claims "warned N days early" |
| Lead < 2 days, alternative pays | same_day; video claims "avoids sending into a glut today" |
| No alternative pays | lead with Second Life and delay-harvest advice |

### 17.3 Automated tests (backend/tests)

| Test | Expected |
| --- | --- |
| Normal week, one load | Nearest mandi; no diversion (proves we don't always divert) |
| Glut day, 2,000 kg | Alternative; 0 < waste avoided < 2,000 |
| Glut day, ten loads | Split across markets; AnnaSetu never pushes a market into glut |
| All fresh markets negative | Processor or food bank |
| Harvest cost > best net | Delay or harvest-to-order advice |
| Stale data | stale flag; wider ranges |
| Units | Rs/quintal to Rs/kg; boxes to kg |
| Null crop field | Rejected |
| Explanation with a foreign number | Template used |
| Interstate outlet | Destination state's fees applied |
| Kannada/Hindi voice parse of "two tonnes tomato" | crop tomato, 2,000 kg |

### 17.4 Acceptance

- Voice to card under 15 s on a real Android phone against the live API.
- Card shows waste avoided, redirected, extra km, earnings, each with range or estimate label.
- Backtest and its charts reproducible from the repo.
- Works in at least two demo regions to show pan-India.

---

## 18. Disclosure: what is real and what is simulated

| Element | Status | Disclosure |
| --- | --- | --- |
| Mandi prices and arrivals | Real, replayed | "Replaying <date> data" |
| Glut events | Real, documented | Sources in README |
| Weather, routes | Real | README |
| Crop parameters | Published references; some placeholders | "Reference parameters"; placeholders marked |
| Freight, fees, commission, handling, diesel | Desk-research values; placeholders until FPO interviews | "(estimate)" |
| Dump share u(R) | Placeholder heuristic | "(estimate)" |
| Processors and food banks | Real organisations, not contacted | "Not yet partnered" |
| Loads and villages | Simulated loads, real villages | "Demo loads" |
| Users | Volunteers in a usability test | Stated as such |
| Spoilage | Estimated, not measured | On card and in README |

Seeded Second Life outlets (Kolar region, from desk research): SNR Foods (processor, Srinivaspura, https://snrfoods.in/about), Feel Fresh Foods (processor, Chittoor belt, https://www.feelfreshfoods.com/about-us.html), Kolar Food Bank (https://kolarfoodbank.1ngo.in/), Bangalore Food Bank fresh produce recovery (https://bangalorefoodbank.com/). Kolar horticulture FPOs: https://coefpo.org/publications/fpo-list-english.pdf. Seed the second demo region's outlets the same way once chosen.

---

## 19. Open decisions (resolve in order; ask the user if unresolved)

1. Arrivals pull works, units confirmed, backtest run: sets mode per crop.
2. Second demo region chosen and its glut verified.
3. FPO interview(s): freight, fees, commission, handling, truck type, dump share in a bad week.
4. Voice accuracy test in Hindi and Kannada on real sentences; if poor, make text input primary.
5. Bedrock model and quota confirmed in ap-south-1.
6. National ingest volume fits in Lambda, or split by state.

### 19.1 Decisions resolved (October 8, 2026)

| # | Decision | Resolution |
| --- | --- | --- |
| D1 | Data access | Done. agmarknet.gov.in (403) and api.data.gov.in (TLS reset) refuse cloud IPs. Tomato daily prices and arrivals, Jan 2022 - Jun 2025, pulled from CEDA at district level (Section 8.2) with `scripts/build_snapshot.py`; manifest records hashes. Open-Meteo and Nominatim reachable. No data is invented. |
| D2 | Placeholder costs | Filled from desk research (Section 10), each with its source and status; shown as "(estimate)". Handling became `handling_pct` (hamali is quoted as % of sale). Replace with FPO interview values. |
| D3 | Tomato sl_ref_hours, q10, alpha, water_l_per_kg | Filled (Section 11): SL_ref 132 h (96-168), Q10 2.0 derived, alpha 0.31 calibrated placeholder, water 184 L/kg. ASHRAE and USDA HB66 were not reachable; sources used are listed. |
| D4 | Projected R in allocation | Defined in Section 9, Step 5. |
| D5 | Waste-avoided range | Defined in Section 9, Step 6. |
| D6 | Backtest format | `analysis/backtest.py` deterministic CLI; notebook is a viewer (Section 16). |
| D7 | Market coordinates | Team runs `scripts/geocode_markets.py` in its AWS account. Until then demo markets use manual coordinates with a source per market; distances are haversine x 1.3 and marked "approx.". |
| D8 | Second demo region | Started only after Kolar works end to end. If it does not fit, the README says so. |
| D9 | Demo loads | Tests use 10 loads (Section 17.3); the video uses the count that the chosen backtest day shows most clearly. |

| D10 | Demo story | Both. Headline: Kolar Jan-Apr 2025 is a price crash with normal arrivals (backtest: median R 0.80, max 1.25; modal price down to Rs 4.60/kg, 7 days below harvest cost; alternatives Rs 9.6-13.5/kg). The card cites the price drop and net-value gap, never an arrival multiple. Candidate day 2025-02-07 (Kolar Rs 7.37 vs Madanapalle Rs 18.20/kg). Second replay: an arrival-driven glut, only if a news source documents it. |
| D11 | Drive time | No speed default. Drive time comes from Amazon Location routes cached in `data/routes_cache.json`; a request without a cached or live route returns 422 `drive_time_unavailable`. |
| D12 | Waste avoided when arrivals are normal | Price-below-cost dump rule added to Section 9 Step 6. |
| D13 | Mode | Tomato `same_day`. Backtest run 78dc0a403b99: flags at least 2 days ahead on 49.6% of 123 crash episodes (full rule) and 29.3% (arrival ratio only); arrival ratio does not lead price (lag 1 correlation -0.001). No "days early" claims. |

Known risk: one FPO's volume may barely move Kolar's ratio or price, so load spreading may come mostly from price impact at smaller markets. Report what the data shows; never tune the model to force a split.

Risks: AGMARKNET blocks cloud IPs (use snapshot + data.gov.in); placeholders drive the headline number (ranges, labels, calibration); wrong regional strings (native review); slow batch transcription (short clips, progress state); geocoding errors (confidence filter, overrides).

---

## 20. Rules for working in this repo

- Never invent numbers. Every UI value comes from `config/` or computed data, with its status.
- Waste avoided and redirected are always separate.
- Ranges, not points, for prices, net value and waste avoided.
- Bedrock only parses and explains; number check or template.
- The demo must run with no live third-party calls (snapshot, fallbacks, templates).
- Region ap-south-1. No credentials in the app or repo.
- `backend/core/` has no AWS imports; adapters hold all external calls; handlers stay thin.
- Minimum code that solves the task. No speculative features, abstractions or configurability.
- Surgical changes only; don't touch unrelated code, comments or formatting; match existing style.
- State assumptions; if ambiguous, ask instead of guessing.
- Define how each change is verified (tests, sample requests, screen states) and run the checks before calling it done.
- Commit small and often with clear messages.
- If you change a decision recorded here, update this file in the same commit.

## 21. Out of scope

Cold storage booking, photo quality grading, sensors, payments, real user accounts, App Store or TestFlight submission, retail and household waste, crops without a complete profile.

---

## 22. Build plan (October 8-11, 2026)

Build from the decision engine outward. Each milestone ends with a check that must pass before the next starts. Deadline: October 11, 8:00 PM IST.

### 22.1 AWS tooling (prize eligibility)

| Requirement | How AnnaSetu meets it |
| --- | --- |
| Deployed on AWS | API Gateway, Lambda, S3, DynamoDB, EventBridge Scheduler, Transcribe, Polly, Bedrock, Location Service, SSM, CloudWatch in ap-south-1 (Section 15) |
| At least one AWS open-source tool | AWS SAM CLI: `infra/template.yaml`, `sam build`, `sam deploy`, and `sam local start-api` for local runs of the handlers |

Not added: Strands Agents (Bedrock only parses and explains; no agent), Step Functions (only if national ingest exceeds Lambda limits, Section 15.1), LocalStack (adapters are tested with stubbed clients; add only if a test needs it). Name SAM CLI and every AWS service in the README and the writeup.

### 22.2 Milestones

| # | Milestone | Day | Output | Check |
| --- | --- | --- | --- | --- |
| M0 | Data snapshot | Oct 8 | `backend/adapters/agmarknet.py`, `datagov.py`: fetch, Rs/quintal to Rs/kg, arrival units verified and stored in tonnes, varieties aggregated with arrival-weighted modal price, IDs from `config/markets.json`. `data/snapshot/agmarknet_tomato_<from>_<to>.csv` plus a manifest (source, pull date, row counts, sha256) | Coverage report per market; missing days stay missing |
| M1 | Kolar backtest | Oct 8-9 | `analysis/backtest.py` runs Section 17.2 steps 1-8; `results_<run_id>.json` split into observed, model, assumptions, simulated; charts | The documented Jan-Apr 2025 crash appears in observed prices, or work stops and is reported. Mode per crop set in `config/model.json` from this evidence (default `same_day`). Demo day chosen |
| M2 | Core engine | Oct 9 | `backend/core/` risk, pricing, spoilage, netvalue, allocate, impact; `config/` model, assumptions (status on every value), crops/tomato, outlets (Section 18 outlets, "Not yet partnered") | pytest covers Section 17.3 and: normal week, glut day, 10 loads, market overloaded, all fresh negative, hold, second-life fallback, harvest-cost threshold, stale data, null crop, unit conversion, transport cost, spoilage, interstate fees. Deterministic |
| M3 | API and replay | Oct 9 | `backend/handlers/advisor.py`: /risk, /recommend, /plan, /impact per Section 13, including 422 and stale cases. `DATA_SOURCE=snapshot\|dynamodb`; `replay_date` drives "Replaying <date> data". Local runs via `sam local start-api` | Sample requests stored as fixtures and asserted in tests |
| M4 | Bedrock and voice | Oct 10 | `adapters/bedrock.py` (parse, explain, number guard, per-language templates), `adapters/speech.py`, `handlers/voice.py`. Typed form input is the fallback | Stubbed-client tests: explanation with a foreign number uses the template; "two tonnes tomato" parses to tomato, 2,000 kg |
| M5 | Mobile app | Oct 10 | Expo + TypeScript, 7 screens (Section 14.2), Recommendation card first (Section 14.3), i18n from `config/copy` (en, hi, kn; native review pending), typed API client | `tsc` passes; Android export builds; team tests on a real phone |
| M6 | AWS | Oct 10 | `infra/template.yaml` (Section 15.1 resources, Section 15.2 roles), `scripts/seed.py`, `scripts/geocode_markets.py` | `sam validate` passes. Team sets the budget alert, deploys and runs the Section 15.4 smoke test (no credentials in this repo) |
| M7 | Demo and README | Oct 11 | Replay of the backtest day: radar, loads, nearest-mandi default vs AnnaSetu allocation, impact; counterfactuals labelled as modelled. README: data provenance, Section 18 disclosure, model, architecture, AWS and SAM usage, limitations (no Kannada Polly voice, placeholders) | Every UI figure traces to `config/` or computed data with its status |

Second demo region (D8) starts after M3 if time allows.
