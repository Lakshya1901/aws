# AnnaSetu: CLAUDE.md (single source of truth)

This file is the complete specification for AnnaSetu. Read all of it before planning or coding. If something here is ambiguous, contradictory or silent on a decision you need, stop and ask; do not guess.

---

## 1. One-line summary

Pitch: "Every day, a city's mandis turn good food into garbage. AnnaSetu stops the glut before the truck leaves, rescues what's left before it's dumped, and turns the rest into energy, not landfill."

AnnaSetu is a farm-to-city surplus router centred on the city mandi. One engine, three entry points:

1. **Prevent:** tells farmer collectives anywhere in India where each load should go (sell fresh, hold, process, donate, feed, biogas or compost) using public mandi data, and allocates loads across markets so they don't all crash the same one.
2. **Rescue:** a trader at a city mandi logs unsold end-of-day stock; the router sends the edible part to food banks or processors before it is dumped.
3. **Recover:** what can't be eaten goes to animal feed, biogas or compost instead of landfill.

- Track: Waste and Energy. Fit: "close the loop on what a city throws away" (Rescue, Recover), "make the city lighter" (Prevent: less surplus reaches the city mandi), "power it cleaner" (Recover: biogas, energy shown only as a labelled estimate)
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
4. Few escape routes: most vegetables never touch a cold link; processors, food banks and biogas or compost units aren't connected to the moment of a glut or to a city mandi's unsold stock at the end of the day. Recommendations must work inside this constraint.

### 3.5 Where the problem sits in the journey

| Stage | Decision | Pain today | AnnaSetu |
| --- | --- | --- | --- |
| Pre-harvest | Harvest now? How much? | No view of the coming glut | Glut Radar |
| Harvest and load | Which market? Send or hold? | Old local price and hearsay | Dispatch Advisor: net value per outlet |
| On the road | Nothing left to decide | Shelf life lost, never counted | Spoilage cost in the ranking |
| At the mandi | Sell or dump? | Price below the cost of sending | Allocation keeps markets from glutting |
| After sale (city mandi, end of day) | Markdown or discard? | No channel for unsold food; dumped as city waste | Rescue: process, donate |
| Inedible remainder | Dump or recover? | Landfill | Recover: feed, biogas, compost |

The first two stages are the decision window where loss is set (Prevent). Interventions at the mandi gate are too late to prevent the surplus, so the last two stages are about where it goes instead of a city dump (Rescue, Recover).

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

**Rescue user: city mandi trader or wholesaler.** Holds unsold stock at a city mandi at the end of the day (demo cities in Section 6). Today the choice is a markdown or the dump. Uses a smartphone and the same app; does not need the Glut Radar.

**Secondary:** individual farmers asking by voice; district horticulture officers watching the Glut Radar to trigger diversion schemes such as Operation Greens.

**Job to be done (FPO manager):** When my members' crop is ready, I want to know where each load should go today and what it will actually earn after costs, so I can avoid sending food into a crash and explain the decision to my members.

**Job to be done (trader):** When stock is left unsold at the end of the day, I want to know who will take the edible part and where the rest can go, so it is not dumped.

---

## 5. Product

Three layers (Section 1) around one decision: where should this surplus go? One router: Rescue and Recover reuse the Dispatch Advisor and Second Life logic with a different entry point, not a second engine.

| Layer | Entry point | User | Parts |
| --- | --- | --- | --- |
| Prevent | New load (before harvest or loading) | FPO dispatch manager | Glut Radar, Dispatch Advisor |
| Rescue | "I have unsold stock at the market" | City mandi trader | Second Life (processor, food bank) |
| Recover | Inedible part of any load or rescued stock | Either | Second Life last rung (feed, biogas, compost) |

1. **Glut Radar.** Daily glut risk for every reporting mandi in India, per crop. Shows safe, watch or glut, and days of warning in predictive mode.
2. **Dispatch Advisor.** For one load (crop, quantity, origin, harvest timing), ranks every reachable outlet by net value per kg after freight, fees and spoilage, with ranges. Allocates multiple loads across outlets so AnnaSetu never pushes a market into glut itself.
3. **Second Life.** When no fresh market pays, or for rescued stock, walks down the food waste hierarchy: hold (storable crops only), processor, food bank, then (Recover) animal feed, biogas, compost. Never a dump.
4. **Impact Ledger.** Headline: kg kept out of landfill (Section 9, Step 6). Separate lines: Prevented (waste avoided, range), Rescued (kg), Recovered (kg to feed, biogas or compost; biogas energy as an estimate). Redirected is shown on its own line and never added to any of these. Plus extra km, diesel, CO2, embedded water.

AnnaSetu advises; people decide. Every recommendation can be overridden, and overrides are logged.

---

## 6. Scope: pan-India with demo regions

- **Architecture is national.** Ingest covers every AGMARKNET market reporting the configured crops. Any origin in India gets recommendations from markets within the reachable radius.
- **Crops (MVP):** tomato (fully tuned), onion, potato, banana. Adding a crop means adding a profile and copy, not code.
- **Glut Radar crops (D24):** every AGMARKNET commodity in `config/commodities.json` (about 400). The top 20 fruits and vegetables by number of reporting markets are loaded daily; any other is loaded on request (POST /crops/fetch). Routing (Dispatch Advisor, Rescue, Recover) needs a profile in `config/crops/`: all 50 preloaded fruits and vegetables have one (D33).
- **Demo regions** (real, documented gluts, replayed from historical data):
  - Kolar tomato belt (Karnataka and Andhra border): Kolar, Chintamani, Srinivaspura, Madanapalle, Bengaluru; January-April 2025 glut.
  - A second region to prove pan-India, chosen by the data check. Candidate: Nashik onion belt (Lasalgaon, Pimpalgaon, Nashik, Pune). Verify a documented glut and data density before committing.
- **Headline city: Delhi (D26).** Rescue and Recover at Azadpur; Kolar stays the Prevent replay.
- **Rescue demo cities:** Bengaluru, Delhi, Mumbai. Rescue routes from the trader's location to Second Life outlets only, so it needs no mandi price data for the city. Each city needs real seeded outlets before it is shown (Section 19, D20).
- **Second Life outlets** (processor, food bank, feed, biogas, compost) are seeded wherever a real organisation with a source was found (D31): the demo regions plus biogas, compost and processor units in other states; the schema is national.
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
| AGMARKNET price and arrival reports | date, state, district, market, commodity, variety, arrivals, min/max/modal price | Daily, plus one-time 3-year history | Undocumented public backend (client: https://github.com/makrand999/agmarknet-api); may rate-limit or block cloud IPs. Live mode (D34): last-week prices per market (no captcha, answers from AWS ap-south-1); arrivals and state-wide reports need a captcha | Snapshot CSV in S3; data.gov.in for prices |
| India Data Portal AGMARKNET bulk files (D24), https://ckandev.indiadataportal.com/dataset/agriculture-marketing | Market-level daily arrivals (tonnes) and min/max/modal price (Rs/quintal), every commodity, with market coordinates; 2021-01-01 to 2026-05-31 | Periodic refresh by the portal | Two public CSVs, Open Data Commons Attribution License (`scripts/build_idp.py`) | Per-commodity files in S3 |
| CEDA Agri Market Data (Ashoka University), https://agmarknet.ceda.ashoka.edu.in | AGMARKNET daily min/max/modal price (Rs/quintal) and arrivals (tonnes), aggregated per Census 2011 district | Monthly refresh by CEDA | Public JSON API, no key (`backend/adapters/ceda.py`) | Snapshot CSV |
| data.gov.in mandi prices, resource 9ef84268-d588-465a-a308-a864a43d0070 | state, district, market, commodity, variety, grade, arrival_date, min/max/modal price (no arrivals) | Daily | Free API key | Snapshot |
| Open-Meteo | Hourly temperature, relative humidity; forecast and history | Per request, cached 6 h | Free, no key | NASA POWER hourly T2M/RH2M (MERRA-2, free, no key; D16), then monthly averages per state in config |
| NOAA GHCN-Daily on the AWS Registry of Open Data (D29), s3://noaa-ghcn-pds | Daily mean temperature per station (TAVG, else (TMAX + TMIN) / 2), e.g. New Delhi Safdarjung IN022021900 | Daily, about a year behind for Indian stations | Public S3 bucket, unsigned requests, no account | Open-Meteo forecast for today; none for a past day with no station within 50 km |
| Amazon Location Service | Market geocoding (once); typed places not in markets.json (D31); route distance and drive time | Geocode once; routes cached per pair | AWS | Haversine distance x road factor 1.3, flagged as estimate |

### 8.2 Cleaning and units

- Prices are Rs per quintal; divide by 100 for Rs per kg.
- Verify arrival units on first pull (tonnes vs quintals); store tonnes.
- Aggregate varieties per market-day: arrivals summed, modal price weighted by arrivals.
- Market-level data (D24) replaces the CEDA district snapshot below: `scripts/build_idp.py` splits the India Data Portal files into one market-level file per commodity (varieties aggregated per market-day as above; bundle- and unit-priced rows dropped, never converted). `market_id` = census state code + normalised market name (official city renames folded), so a market keeps its history across the portal's two files. Coordinates come from the data; disputed or missing ones are checked with Amazon Location (`scripts/build_idp_config.py`), and low-confidence markets are left out of routing.
- Demo snapshot (D1, superseded by D24): agmarknet.gov.in and api.data.gov.in refuse connections from cloud IPs, so the 2022-2025 history comes from CEDA, which is district level. Each "market" in `config/markets.json` is one district aggregate, named after its main tomato market town (Kolar district = Kolar, Chittoor = Madanapalle, Chikkaballapura = Chintamani). CEDA's district price is its own aggregate, not arrival-weighted by us. Market-level AGMARKNET data replaces it when available; the engine is unchanged. Districts with a unit problem or no prior-year baseline are excluded and listed in `config/markets.json`.
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
| Outlets | `outlet_id` | - | type (mandi, processor, food_bank, feed, biogas, compost), name, state, lat, lon, crops, min_qty_kg, offer_price_kg, contact, verified, seeded |
| Plans | `plan_id` | - | created_at, source (farm, mandi_unsold), loads, allocations, impact, language, explanation inputs and outputs |

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
b fitted per market by regressing ln(price) on ln(arrivals), clipped to [-1.5, -0.1]; if R^2 < 0.2 use -0.5. Range = P_hat x exp(+/- sd), where sd is the standard deviation of day-to-day changes in ln(modal price) between reported days at most 3 days apart (D15). dA = quantity AnnaSetu has already allocated there.

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
Second-life outlets use offer price (processor) or 0 (food bank, feed, biogas, compost) for P_hat.

### Step 5. Allocation (anti-herding)

1. Sort the day's loads by quantity, largest first.
2. For each load, compute net(j) for all reachable outlets using current dA.
3. Assign to the best outlet unless it pushes that market's projected R into glut; then the next best. A market whose projected R is unknown (fewer than 5 of the last 7 days, or no prior-year baseline) cannot be checked, so it is listed as an alternative but never chosen (D17). Projected R = A7 recomputed with today's arrivals plus dA(j), divided by B (same definition as Step 1).
4. Add to that market's dA; repeat.
5. If no fresh market has net > 0: processor, then food bank, then feed, then biogas, then compost (food recovery hierarchy; nearest first within a type).
6. If best net < harvest cost per kg: advise delaying harvest (storable crops) or harvesting only what has a buyer (non-storable).

Greedy is sufficient. No optimiser.

### Step 5b. Rescue (source = mandi_unsold)

Same router, different entry point. Origin is the trader's location at the city mandi; harvest timing does not apply.

1. Split: the engine proposes a spoiled share with Step 3, s = min(1, alpha * f), where f = hours since harvest / SL(T) and T is the current temperature at the origin. Proposed spoiled_kg = Q * s, edible_kg = Q - spoiled_kg, labelled "(estimate)". The trader confirms or edits both; trader values replace the estimate and are logged as such.
2. Edible part: another mandi within `rescue_radius_km` (100 km, D31) that still pays after freight, fees and the extra spoilage, is not in glut and has fresh data, best net first (D36; the trader's own mandi, within `own_mandi_km`, is skipped: the stock already failed there); else Second Life (processor, then food bank), nearest first within a type, within the same radius. If none is in radius, it goes to the Recover rung.
3. Spoiled part: Recover rung only (feed, then biogas, then compost).
4. Delay-harvest advice and allocation dA do not apply.

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

Impact Ledger lines (all kg; each kept separate):
- Prevented = W (range) from Prevent loads.
- Rescued = edible kg routed to a processor or food bank in Rescue (the trader's value, or the proposed split if the trader accepted it).
- Recovered = kg routed to feed, biogas or compost, from either entry point.
- Kept out of landfill (headline) = Prevented + Rescued + Recovered, as a range, labelled "(estimate)". Redirected is never added to it.
- Biogas energy = kg to biogas x `biogas_yield` (Section 10), labelled "(estimate)"; while the yield is null it renders "not yet estimated". No national energy-savings claims (Section 3.3).

Range for W: mid uses u(R) of the band R falls in; low and high use u of the band below and above for the default market, combined with the low and high spoilage estimate. Labelled "(estimate)".

### Resource accounting

- extra_km vs default market
- diesel_l = extra_km * litres_per_km (placeholder)
- co2_kg = diesel_l * 2.68
- water_l = W * crop water footprint (to source per crop)

Null values render "not yet estimated", never zero.

---

## 10. India context inputs

All in `config/assumptions.json`, each with `value`, `unit`, `status` (sourced | assumption | placeholder), `source`, and optional per-state overrides. Screens that show figures built on them carry one "All numbers are estimates" line (D32).

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
| Rescue radius (D31) | 100 km | assumption | Config; unsold stock goes to outlets in and around its city |
| Stale-data range widening | 1.5x the residual standard deviation | assumption | Config |
| Max data age to be chosen (D25) | 7 days | assumption | Config; older markets are listed, never chosen |
| R a price-only risk level stands for (D34) | safe 1.0, watch 1.3, glut 2.0 | assumption | Config (`price_only_ratio`); picks the u(R) band for live prices, which have no arrivals |
| Biogas yield per kg of fruit and vegetable waste | null (to source) | placeholder | Published anaerobic digestion yield for vegetable waste, or the partner unit's figure (D21) |

### Languages

| Function | Support |
| --- | --- |
| App text | English plus India's 20 most spoken languages (D27): Hindi, Bengali, Marathi, Telugu, Tamil, Gujarati, Urdu, Kannada, Odia, Malayalam, Punjabi, Assamese, Maithili, Santali, Kashmiri, Nepali, Sindhi, Dogri, Konkani, Manipuri; one `config/copy/<code>.json` each. All but English are pending native review; all but English, Hindi and Kannada are machine-drafted |
| Voice in (Transcribe) | The app languages Transcribe batch supports (checked 2026-10-10): English, Hindi, Bengali, Gujarati, Kannada, Malayalam, Marathi, Odia, Punjabi, Tamil, Telugu, Nepali. Others: typed form only (the mic is hidden) |
| Voice out (Polly) | Hindi and Indian English only. No other Indian voices; other languages hear English; say this openly in settings and README |

The user picks a language on first launch. Recommendation text appears in that language; spoken replies in Hindi or English.

---

## 11. Crop profiles

One JSON file per crop in `config/crops/`. A profile with a null required field is rejected with a clear message; never guessed.

| Parameter | Tomato | Onion | Potato | Banana |
| --- | --- | --- | --- | --- |
| Recommended storage | ~10 C ripe, ~13 C mature green | ~0 C, 70-75% RH | to source | 12-15 C |
| Good-condition storage life | days to ~2 weeks | ~6-8 months | months (cold store) | weeks, ripening-dependent |
| SL_ref at T_ref (25 C) | 132 h, range 96-168 h (4-7 days holding at ambient for ripening stages; https://www.researchgate.net/publication/294485852) | 2,880 h (4 months ambient storage), range 2,490-3,350 h (Gorrepati et al., Indian J. Hort., https://journal.iahs.org.in/index.php/ijh/article/view/321) | placeholder | placeholder |
| Q10 | 2.0, derived from UC Davis respiration rates for mature-green tomato: 8-14 mL CO2/kg.h at 15 C, 18-26 at 25 C (https://postharvest.ucdavis.edu/produce-facts-sheets/tomato; page read through a search excerpt, verify) | 2.4, derived from UC Davis whole dry onion: 3-4 mL CO2/kg.h at 0-5 C, 27-29 at 25-27 C (search excerpt, verify) | placeholder | placeholder |
| alpha | 0.31, placeholder: calibrated so a 14 h trip (6 h since harvest + 2 h drive + 6 h wait) at 25 C gives 3.25% loss, the market-stage tomato loss in Section 3.2 | 0.31, placeholder: mean total loss after 4 months ambient storage (26.66% and 35.87%, same Gorrepati et al. trial) | placeholder | placeholder |
| Storable (hold option) | no | yes | yes | limited |
| Water footprint | 184 L/kg world average, tropical production 200-900 L/kg (Hoekstra, cited in Nederhoff and Stanghellini 2010, https://edepot.wur.nl/156932) | 345 L/kg | 287 L/kg | 790 L/kg (onion, potato, banana: Mekonnen and Hoekstra 2010, Value of Water Report 47, Table 4, global averages) |
| Harvest cost per kg | ~Rs 4.7 (Kolar) | ~Rs 3.5, placeholder: Rs 300-400/quintal harvest labour plus transport, one Nashik farmer, FreshPlaza 2016 | not found (optional since D33; no harvest advice) | not found (optional since D33; no harvest advice) |
| Second life | puree/paste, food bank; Recover: biogas, compost | dehydration, food bank; Recover: biogas, compost | processing, food bank; Recover: biogas, compost | ripening/retail, chips, food bank; Recover: feed, biogas, compost |

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
  "second_life": ["processor", "food_bank", "biogas", "compost"],
  "sources": {"harvest_cost_rs_per_kg": "Outlook Business, Apr 2025"}
}
```

---

## 12. Bedrock

Two jobs only. It never calculates, chooses outlets or adds numbers. One small fast model called through the Bedrock Converse API (model-agnostic): Amazon Nova Lite, or a Claude Haiku model if Anthropic access is granted (D23); model ID from the deploy parameter (`config/model.json` keeps null); temperature 0; 3 s timeout.

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
| POST /recommend | One load (Prevent) or unsold stock (Rescue) | crop, quantity_kg, origin {lat, lon, place}, harvest, language, plan_id?, source? ("farm" default, or "mandi_unsold"); for mandi_unsold: hours_since_harvest, edible_kg?, spoiled_kg? (both or neither; omitted = engine proposes the split) | ranked outlets, default outlet, impact, explanation, data freshness, assumptions_used; for mandi_unsold also split {edible_kg, spoiled_kg, source: estimate or trader} and recover (outlet for the spoiled part) |
| POST /plan | All loads together | loads[], language | allocation per load, dA per market, total impact |
| POST /speak | Spoken reply | text, language (hi or en) | presigned MP3 URL |
| GET /crops?crop= | Crop catalogue (D24) | optional crop | crops [{crop_id, name, category, markets, preload, routing}]; with crop also status (ready, fetching, available) |
| POST /crops/fetch | Load one crop's data (D24) | crop | crop, status; asynchronous: SQS -> ingest -> MarketRisk; poll GET /crops?crop= |
| GET /impact?plan_id= | Impact Ledger | plan_id | kept_out_of_landfill_kg range, waste_avoided_kg range (Prevented), rescued_kg, recovered_kg, biogas_energy (estimate or null), redirected_kg, extra_km, diesel_l, co2_kg, water_l |

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
| Rescue: no processor or food bank in radius | edible part goes to the Recover rung | Recover outlet shown with the reason |
| Rescue: no Recover outlet in radius | recover: null | "No biogas or compost unit near you yet" |
| Rescue: no split and no weather at the origin (Delhi, Mumbai) | 422 split_required | Edible and spoiled fields highlighted; the trader enters both |
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
| Settings | Which language, data and crops are mine? | Language row; Data: Live (today's mandi prices, default) or Demo (the saved glut day, 29 Sep 2023; D34); My crops (search every crop with a routing profile, check the ones I sell; kept on the phone); Clear saved data (confirm first: lifetime totals and today's plan; language and crops stay) | My crops show first in New load, Unsold stock and Today (D33) |
| Today (Glut Radar) | Is a glut coming near me? | Nearby markets for the chosen crop, colour + word + icon, ratio, price | Loading, stale, same_day, market not reported |
| New load | What am I sending? | Big mic button; form below (crop, qty, place, harvest) | Recording, processing, parse failed |
| Unsold stock (Rescue) | I have unsold stock at the market | Crop, quantity, hours since harvest; proposed edible/spoiled split, editable | Estimate vs trader values, no outlet in radius |
| Confirm | Did we hear you right? | Editable chips | Low confidence: all highlighted |
| Recommendation | Where should this load go? | The card, plus two alternatives | Stale, Second Life, delay harvest, template text |
| Today's loads (was Today's plan; D39) | How do I split all loads, and what have I sent before? | New load button; today's loads with outlets, added qty per market; previous loads by day (saved on the phone), filter by sold / not sold and crop; tick a load as sold | Market capped |
| Impact | What did we keep out of landfill? | Headline kg kept out of landfill, then Prevented, Rescued, Recovered (biogas energy estimate), Redirected on separate lines | "Not yet estimated" values |

### 14.3 Recommendation card

```
Send 2,000 kg to Madanapalle
Kolar is receiving 3.1x its usual tomatoes today.

You'd earn      Rs 9-12 per kg   (Kolar: Rs 0-2)

Waste avoided   about 600 kg   (likely 400-800 kg)
Redirected      2,000 kg away from a likely glut
Extra distance  +37 km, about X litres diesel

[Why not Kolar?]  [Listen]  [Use this]
```

Rules: earnings first (what the farmer keeps, compared with the default market), then waste avoided (changed October 10 for farmer-level reading, PRODUCT.md); never merge waste avoided and redirected; ranges on prices, net value and waste avoided, and one "All numbers are estimates" line per screen instead of "(estimate)" on every figure (D32); "Why not X?" opens a before/after comparison of default vs recommended on the same load; "Use this" and overrides are logged.

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

Rescue and Recover keys (unsold_stock, hours_since_harvest, edible, spoiled, kept_out_of_landfill, prevented, rescued, recovered, biogas_energy, type_feed, type_biogas, type_compost, no_recover_outlet, err_split_required, split_hint, split_sum) are in `config/copy/<lang>.json` under `_review` until approved.

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
| Lambda | advisor | 512 MB, 29 s; /risk, /recommend, /plan, /impact |
| Lambda | voice | 256 MB, 30 s; /voice/*, /speak |
| API Gateway | HTTP API | throttle 10 rps; simple API key for the demo app |
| S3 | annasetu-data-<suffix> | private |
| S3 | annasetu-audio-<suffix> | private; lifecycle delete after 1 day |
| DynamoDB | MarketDay, MarketRisk, Outlets, Plans | on-demand |
| Transcribe | batch jobs | hi-IN, kn-IN, en-IN |
| Polly | SynthesizeSpeech | Hindi and Indian English voices, MP3 |
| Bedrock | Converse (InvokeModel permission) | one small model: Amazon Nova Lite (D23) |
| Location Service | place index, route calculator | geocode markets once; routes cached |
| SQS | fetch queue + dead-letter queue (D24) | one message per crop to load: daily preload fan-out and POST /crops/fetch; ingest consumes (batch 1); alarm on the dead-letter queue |
| SSM Parameter Store | /annasetu/datagov_key | SecureString |
| CloudWatch | logs, alarm | alarm on ingest failure |

If ingest exceeds Lambda limits nationally, split by state with a Step Functions map or one invocation per state; do not add this unless needed.

### 15.2 IAM (one role per function, least privilege)

| Role | Allowed |
| --- | --- |
| ingest-role | S3 put/get data bucket; DynamoDB write MarketDay, MarketRisk; SQS send to the fetch queue (and receive, as its consumer); SSM get key |
| advisor-role | DynamoDB read all, write Plans, put MarketRisk "#status" rows; SQS send to the fetch queue; Bedrock InvokeModel (one model); Location CalculateRoute |
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
├── scripts/                  build_idp.py  build_idp_config.py  build_snapshot.py  cache_routes.py  geocode_markets.py  seed.py
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
- Rescue demo: one simulated unsold lot at a Rescue demo city mandi (Section 6), routed to real seeded outlets only (D20).

Demo video, three beats (3 minutes or less):
1. Produce dumped at a city mandi: "this was thrown away by a city" (footage or a documented source, D22).
2. Trace back and prevent: glut forming on the radar, the FPO manager gets advice by voice, loads split across markets.
3. Rescue and recover: a trader logs unsold stock, a food bank takes the edible part, a biogas unit takes the rest; Impact Ledger totals.

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
| Rescue, no split given | Split proposed from Step 3, labelled estimate; edible to processor or food bank, spoiled to feed, biogas or compost |
| Rescue, trader split | Trader values used, split source trader |
| Rescue, no processor or food bank in radius | Edible part goes to the Recover rung |
| Recover order | Feed before biogas before compost |
| Impact lines | Headline = Prevented + Rescued + Recovered; redirected separate; biogas energy null until yield sourced |

### 17.4 Acceptance

- Voice to card under 15 s on a real Android phone against the live API.
- Card shows waste avoided, redirected, extra km, earnings, each with range or estimate label.
- Backtest and its charts reproducible from the repo.
- Works in at least two demo regions to show pan-India.

---

## 18. Disclosure: what is real and what is simulated

| Element | Status | Disclosure |
| --- | --- | --- |
| Mandi prices and arrivals | Real: replayed (Demo) or today's Agmarknet prices without arrivals (Live, D34) | Demo: "Replaying <date> data" |
| Glut events | Real, documented | Sources in README |
| Weather, routes | Real | README |
| Crop parameters | Published references; some placeholders | "Reference parameters"; placeholders marked |
| Freight, fees, commission, handling, diesel | Desk-research values; placeholders until FPO interviews | "(estimate)" |
| Dump share u(R) | Placeholder heuristic | "(estimate)" |
| Processors, food banks, biogas and compost units | Real organisations, not contacted | "Not yet partnered" |
| Unsold stock at a city mandi | Simulated lot | "Demo stock" |
| Biogas energy | Estimate from a sourced yield (D21) | "(estimate)" |
| Loads and villages | Simulated loads, real villages | "Demo loads" |
| Users | Volunteers in a usability test | Stated as such |
| Spoilage | Estimated, not measured | On card and in README |

Seeded Second Life outlets (Kolar region, from desk research): SNR Foods (processor, Srinivaspura, https://snrfoods.in/about), Feel Fresh Foods (processor, Chittoor belt, https://www.feelfreshfoods.com/about-us.html), Kolar Food Bank (https://kolarfoodbank.1ngo.in/), Bangalore Food Bank fresh produce recovery (https://bangalorefoodbank.com/). Kolar horticulture FPOs: https://coefpo.org/publications/fpo-list-english.pdf. Seed the second demo region's outlets the same way once chosen. Biogas and compost units, and Delhi and Mumbai outlets, are open (D20); none are seeded until a real organisation and source are given. Pan-India outlets added October 10 are listed in D31.

---

## 19. Open decisions (resolve in order; ask the user if unresolved)

1. Arrivals pull works, units confirmed, backtest run: sets mode per crop.
2. Second demo region chosen and its glut verified.
3. FPO interview(s): freight, fees, commission, handling, truck type, dump share in a bad week.
4. Voice accuracy test in Hindi and Kannada on real sentences; if poor, make text input primary.
5. Bedrock model and quota confirmed in ap-south-1.
6. National ingest volume fits in Lambda, or split by state.
7. D20-D22 (farm-to-city reframe): real outlets per Rescue city, biogas yield source, beat 1 source.

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

| D10 | Demo story | Both. Headline: Kolar Jan-Apr 2025 is a price crash with normal arrivals (backtest: median R 0.75, max 1.26; modal price down to Rs 4.60/kg, 7 days below harvest cost; alternatives Rs 9.6-13.5/kg). The card cites the price drop and net-value gap, never an arrival multiple. Candidate day 2025-02-07 (Kolar Rs 7.37 vs Madanapalle Rs 18.20/kg). Second replay: an arrival-driven glut, only if a news source documents it. |
| D11 | Drive time | No speed default. Drive time comes from Amazon Location routes cached in `data/routes_cache.json`; a request without a cached or live route returns 422 `drive_time_unavailable`. |
| D12 | Waste avoided when arrivals are normal | Price-below-cost dump rule added to Section 9 Step 6. |
| D13 | Mode | Tomato `same_day`. Re-run on market-level data (D24), run 937fb04f9baf: 1,818 scorable crash episodes in 319 markets within 350 km of Kolar; flags at least 2 days ahead on 44.5% (full rule) and 22.6% (arrival ratio only); strongest negative lag 4 days, correlation -0.002. Still `same_day`. Earlier CEDA run: Backtest run 78dc0a403b99 (after the ISO-week baseline fix): flags at least 2 days ahead on 46.3% of 123 scorable crash episodes (full rule) and 26.8% (arrival ratio only); arrival ratio does not lead price (strongest negative lag 1 day, correlation +0.003). No "days early" claims. |
| D15 | Price range | The level-regression residual spanned seasons (Madanapalle net Rs 5-45/kg). The range now uses day-to-day ln price changes: about +/-13% (Madanapalle) to +/-40% (Mandya) on the 2025-02-07 history. Also: the ln(price) on ln(arrivals) fit has R^2 below 0.2 at every demo market, so all use the fallback b = -0.5; state this in the README. |
| D16 | Weather snapshot | Open-Meteo returned 429 (daily limit on the shared IP), so the replay windows (2025-01-01..2025-05-31, 2023-09-01..2023-09-30) use NASA POWER hourly temperature and humidity at each market's coordinates: `data/snapshot/weather_power_*.json`. Trip temperature = mean of the day's hours at the nearest point. |
| D17 | Markets with unknown risk | Never chosen as the destination, only listed. Found when Doddaballapura (about 1 t/day, latest price 15 days old on 2023-09-06) absorbed 16 t in a 10-load plan. |
| D18 | Demo replay days | Headline 2023-09-29 (October 10, re-chosen on market-level data, D24; `config/model.json` replay_date): inside the documented September 2023 Kolar glut (D14); Kolar R 1.59 (watch), modal net Rs 4.8-6.4/kg vs Binny Mill, Bengaluru Rs 7.5-11.5/kg; the ten demo loads split Binny Mill 11.2 t, Vayalapadu 4.8 t; waste avoided -216 to 3,269 kg (mid 732, estimate), redirected 16,000 kg, extra 878 km. Chosen over 2023-09-15 (mid 499 kg, range -452 to 3,039) and 2023-09-06 (mid -61 kg, no split). Data for these days is `stale: true` at some markets; the app shows the banner. Earlier headline 2023-09-06 (CEDA district data): ten loads spread over several markets. Second 2025-03-19 (Kolar's 2025 low, Rs 4.60/kg, below harvest cost; run with `REPLAY_DATE=2025-03-19`). 2025-02-07 dropped: Kolar still paid above harvest cost, so waste avoided was negative. Final figures wait for Amazon Location routes (D11); waste avoided on 2025-03-19 is driven by the placeholder dump share (D12) and must carry "(estimate)". |
| D14 | Second replay (D10) | Kolar 2023-09-06, an arrival-driven glut: R 1.76 (glut), 3-day price change -28.7%, modal Rs 6.64/kg; Madanapalle Rs 10.60/kg, 61 km. Documented: Deccan Herald 2023-09-26 (https://www.deccanherald.com/india/karnataka/rs-200-to-rs-10-tomato-farmers-hopes-crash-2700660, officials attribute the crash to "the arrival of a large quantity of tomatoes"; 4.21 vs 2.31 lakh quintals year on year) and FreshPlaza/New Indian Express 2023-09-04. Baseline uses one prior year (2022). `analysis/second_replay.py`. |
| D19 | Farm-to-city reframe (October 9) | Prevent, Rescue, Recover on one router (Sections 1, 5, 9). Rescue reuses POST /recommend with source mandi_unsold. Edible split: engine proposes from Step 3, trader confirms or edits. Recover order: feed, biogas, compost (`feed_compost` split into `feed` and `compost`). Headline kg kept out of landfill = Prevented + Rescued + Recovered. Rescue demo cities: Bengaluru, Delhi, Mumbai. Delhi and Mumbai use trader-entered splits only (no weather snapshot there; 422 split_required without one). Rescue explanations use the per-language template only, not Bedrock. |
| D20 | Rescue city outlets | **Open, for the team.** For each of Bengaluru, Delhi, Mumbai: the city mandi to use (name; candidates to confirm: Bengaluru district market in `config/markets.json`, Delhi Azadpur, Mumbai Vashi APMC), and real processors, food banks, and biogas or compost units with a source URL each. Bengaluru already has Bangalore Food Bank seeded. Nothing is seeded without a source. |
| D21 | Biogas yield | **Open, for the team.** A sourced yield per kg of fruit and vegetable waste (or the partner unit's figure) and its unit, for `biogas_yield` in `config/assumptions.json`. Until then energy renders "not yet estimated". |
| D22 | Video beat 1 | **Open, for the team.** Footage or a documented news source of produce dumped at a city mandi (Bengaluru, Delhi or Mumbai). |
| D24 | All crops, pan-India, market level (October 10) | Data: India Data Portal AGMARKNET bulk CSVs (market level, every commodity, 2021-01 to 2026-05, ODC-By) replace the CEDA district snapshot; `scripts/build_idp.py` writes one file per commodity to `s3://annasetu-data-<suffix>/idp/`. Engine: ingest computes each market's risk and price fit (b, resid_sd) from that file and writes MarketRisk; the advisor reads MarketRisk instead of querying history per market (scales to ~4,000 markets). Crops: Glut Radar for every commodity; top 20 fruits and vegetables by reporting markets preloaded daily (schedule fans out over SQS, one invocation per crop); any other on request via POST /crops/fetch (SQS, retries, dead-letter alarm). Routing still needs a complete profile: tomato and onion now; potato and banana stay radar-only until a harvest cost is sourced. Ranking by arrival tonnage was rejected: some commodities report counts as tonnes (live poultry shows 149 Mt). Backtest, mode (D13) and replay figures (D14, D18) are re-run on market-level data. Market-level replay, 10 demo loads from Kolar (13.137, 78.134): 2025-03-19 recommends Binny Mill, Bengaluru (net Rs 9.0-13.5/kg vs Kolar Rs 3.6-4.8, below harvest cost), waste avoided 365-812 kg per 2 t load; 2023-09-06 recommends Madanapalli (Rs 14.1-19.6 vs Kolar Rs 5.8-7.8, glut) but waste avoided is about -8 kg (range -126 to 309): Kolar's R 1.62 is in the same dump-share band as Madanapalli's 1.34, so only the longer trip counts; the ten loads do not split. Other documented-glut days split the loads (2023-09-15: Binny Mill 11.2 t, Punganur 4.8 t; 2023-09-29: Binny Mill 11.2 t, Vayalapadu 4.8 t). Headline day to be re-chosen by the team (D18). |
| D25 | Old market data (October 10) | With ~300 markets in radius, many report sporadically; a month-old price (Mulakalacheruvu, last report 2023-06-30 in the national price spike, Rs 77/kg net) won the 2023-09-06 ranking. A market whose latest report is older than `max_data_age_days` (7, assumption, `config/assumptions.json`) is listed but never chosen, as D17 does for unknown R. Section 8.6 widening for stale data (> 2 days) is unchanged. |
| D26 | Delhi headline, city-centric origin (October 10) | The submission is for a Delhi city hackathon: the headline demo is Delhi. Rescue/Recover at Azadpur (a trader types "Azadpur" as the place) is the headline beat; Kolar (2023-09-29) stays the Prevent replay, because no documented glut at a Delhi mandi was found for Jan 2021 - May 2026 (the Oct-Nov 2024 Azadpur tomato price fall in the press had normal arrivals, R about 1.0, and prices Rs 30-58/kg: not a glut). Origin: a typed "City, town or village" is resolved by the API to a market name, then a district name, in `config/markets.json` (exact match, case, spacing and a trailing "mandi"/"market" ignored; a district = mean of its markets, `place_approx`; a name in two states or no match = 422 origin_unknown). Coordinates from the device still win when given. Delhi outlets (D20): India FoodBanking Network (fresh produce recovery, works with Azadpur) is the only one with a fetched source; no Delhi biogas, compost, feed or processor outlet with a source was found (IGL Ghazipur bio-CNG is planned, not operating), so Delhi Recover shows "No biogas or compost unit near you yet". |
| D27 | Languages (October 10) | English plus the 20 most spoken Indian languages (Census 2011). Text for the 18 new languages is machine-drafted, every key under `_review`; Kashmiri, Santali, Manipuri and Dogri are low confidence and need a native rewrite. Fonts: Noto per script (Naskh Arabic for Urdu, Kashmiri, Sindhi; Ol Chiki for Santali; Bengali script for Manipuri). Right-to-left: text is right-aligned with RTL writing direction; screen layout stays left-to-right. |
| D28 | Crops (October 10) | Glut Radar preloads the top 50 fruits and vegetables daily (was 20); all 400 commodities on request. Routing stays tomato and onion: sourcing found a full profile for no other crop (cauliflower has harvest cost Rs 1.5/kg, Tribune 2025, shelf life 6-10 days at 30 C, Q10 2.0 from USDA AH-66, water 285 L/kg, but no sourced spoilage rate alpha; potato, banana, cabbage, brinjal, okra, bottle gourd and green chilli have no sourced harvest cost). |
| D29 | Weather from AWS Open Data + live forecast (October 10) | AWS has no weather API. Replay snapshots for Delhi come from NOAA GHCN-Daily on the AWS Registry of Open Data (s3://noaa-ghcn-pds; New Delhi Safdarjung and Palam; `data/snapshot/weather_ghcn_delhi_*.json`, built by `backend/adapters/weather.py ... ghcn`), so Delhi Rescue now gets an estimated split (2023-09-29: 27.8 C, 500 kg -> 457 kg edible, 43 kg spoiled, estimate) instead of 422 split_required. Kolar keeps NASA POWER (D16). Deployed (WEATHER_LIVE=1), a day no snapshot covers uses the Open-Meteo forecast for today or later, else the nearest GHCN station within 50 km; a failure falls back to the existing 422 / trader-split path. D19's 'Delhi uses trader splits only' is superseded. |
| D30 | Lifetime dashboard (October 10) | Impact tab has "Since you started" (default) and "Today's plan". Lifetime totals live on the phone (AsyncStorage, `app/lib/ledger.ts`; no accounts, Section 21): every load or unsold lot confirmed with "Use this" adds its API figures. Today's plan counts too (user request, October 11): its GET /impact kg replace that plan's confirmed entries, so unsold lots logged in the plan but not confirmed are included and nothing is counted twice; money saved stays from confirmed entries (the plan total has none). Shown: kg kept out of landfill (range; Prevented + Rescued + Recovered, Prevented counted only when the recommended outlet was used), share of produce saved (kept / kg sent through the app, estimate), "Total money saved" (user's label) = what AnnaSetu added: for the recommended outlet the API's `money_saved_rs` (Section 9 Step 6 terms: expected earnings = net per kg x (1 - u, with the D12 floor at the default) x quantity, advised minus nearest mandi; better price plus produce a glut leaves unsold, spoilage counted once), for an override net at the chosen outlet minus net at the nearest mandi (farm), or the chosen outlet's net for unsold stock (otherwise dumped), summed, with range and that definition shown under it (changed October 10 after the phone test; it had summed total earnings), and a Prevented / Rescued / Recovered bar (palette checked with the dataviz validator). Unsold stock regains "Use this": it records the lot. |
| D31 | Pan-India outlets (October 10) | Desk research (four parallel searches, each source re-fetched) seeded 15 real organisations in `config/outlets.json`, all "Not yet partnered", coordinates from Amazon Location (locality, not premises). Biogas (7): Indore Devguradia bio-CNG, Surat APMC (fruit and vegetable waste), Bowenpally vegetable market Hyderabad, Ujjain Smart City, Chetpet Chennai (Koyambedu waste), BPCL Brahmapuram Kochi, Adarsh Gaushala Gwalior (mandi scraps). Compost (2): Agra Transport Nagar and Raj Nagar (market fruit and vegetable waste). Processors (6): onion dehydration in Mahuva, Gujarat (Panchvati Foods, Maharaja Dehydration, Asian Food Export, Century Foods); tomato: ShimlaRed (Shimla), ABC Fruits (Krishnagiri). Not seeded: food banks outside Bengaluru and Delhi (the city groups found rescue cooked or leftover food; none showed fresh produce intake; IFBN's nine produce hubs are not named publicly), feed (tomato and onion have no feed rung; no gaushala with a current source), plants that are planned, closed or only dated 2014-2018. Rescue looks within `rescue_radius_km` (100 km, assumption) instead of the 300 km market radius, so a Delhi trader is not sent to Shimla or Gwalior: Delhi edible goes to IFBN, spoiled shows "No biogas or compost unit near you yet". Any place in India: a typed city, town or village not found in `config/markets.json` is looked up with Amazon Location place search (relevance at least 0.9, else 422 origin_unknown; marked place_approx), live on the deployed advisor (`LOCATION_PLACE_INDEX`, IAM geo:SearchPlaceIndexForText) and from `data/places_cache.json` offline (`python backend/adapters/location.py <index> <place>...`; nine cities cached). Rescue routes for Chennai, Hyderabad, Surat, Indore, Ujjain, Kochi, Gwalior, Agra and Bengaluru are cached (`scripts/cache_routes.py --rescue`), so the offline replay routes unsold stock there; without a trader split those cities get 422 split_required offline (no weather snapshot), live they use the forecast (D29). |
| D32 | Fewer "(estimate)" labels (October 10) | The word repeated on every figure was noise for farmers. Ranges stay where Section 9 defines them; the per-figure "(estimate)" is replaced by one line, "All numbers are estimates" (`est_note`, 21 languages, pending review), on the recommendation card, the Why-not sheet, Today's plan, Unsold stock and both Impact tabs. Fresh data does not remove it: spoilage, waste avoided, freight and dump share are modelled, not measured. The engine's proposed edible/spoiled split keeps its "(estimate)" tag because it tells the trader the split can be edited. |
| D33 | Advice for all 50 preloaded crops (October 10) | User request: "do calculations for everything". Research (five parallel searches; sources in each profile) gave: post-harvest loss by stage for 29 crops (NABCONS 2022 via PIB, Rajya Sabha reply 1 Aug 2025), water footprint for 40 (Mekonnen and Hoekstra 2010, Report 47), shelf life and respiration rates mostly from USDA Agriculture Handbook 66, Indian harvest cost for 3 only. `config/crops/<id>.json` for 48 new crops (tomato and onion unchanged) are built by one rule set: Q10 from respiration rates at two temperatures at least 10 C apart (warmest pair, kept only within 1.5-4.0); shelf life at 25 C from the ambient life (unstated temperature taken as 25 C), else extrapolated from cold-storage life with Q10, kept only within 24 h - 90 days; alpha calibrated like tomato (a 14 h trip at 25 C gives the NABCONS market-level loss), capped at 1; any value still missing is the median of the crop's category (fruits or vegetables) and marked `assumption`; derived values are `placeholder`. Harvest cost is now optional: green peas (Rs 6/kg, Amritsar 2023) and cauliflower (Rs 1.5/kg, Tribune 2025) are sourced, green chilli (Rs 4/kg picking) placeholder; the NHB model-project figures (Rs 70/man-day, about 2001) were not used. Without a harvest cost the crop gets no delay-harvest / harvest-to-order advice and no below-cost dump rule (D12), so waste avoided is conservative. Hindi and Kannada names come from the research and need native review. The other ~350 commodities (grains, spices, livestock, flowers) stay radar-only: the trip-spoilage model does not fit them. |
| D34 | Live or demo data (October 10) | User request: a live running build, with a Settings switch to the saved demo glut day. Every request carries header `x-annasetu-data`: `live` (the app's default) uses today's date (IST); anything else replays `replay_date` (29 Sep 2023, D18), as before. Sources checked October 10 from AWS ap-south-1: India Data Portal (refreshed 8 Oct) and CEDA still end by 31 May 2026; data.gov.in refuses the connection (and no key was stored); agmarknet.gov.in (Agmarknet 2.0, live to 10 Oct 2026) answers, but only per-market last-week prices are public: arrivals and state-wide reports need a captcha. So Live is prices only: the advisor fetches last-week prices (`backend/adapters/agmarknet.py`, 4 at a time) for the `nearest_markets` (15) with the crop's history nearest each origin; Agmarknet answers 429 after about 60 calls in a few minutes, so each market's prices are cached for the day in MarketRisk (`live#<market_id>` rows) and a 429 stops further calls in that request; Agmarknet ids come from the IDP New Source file (its market code is the Agmarknet market id) and exact name matches for commodities (`scripts/build_agmarknet_ids.py`: 3,066 of 4,142 markets, 380 of 400 commodities; elephant yam has no exact match). Risk is price-only (watch below -15% in 3 days, glut below -25%; same `same_day` mode); the price range uses the week's day-to-day changes, else the market's history. Without arrivals there is no own-load price effect and no projected ratio, so a market with a live price can be chosen (D17 applies to demo only) and the ten-load split (Step 5) does not happen in Live. Waste avoided uses the u(R) band its price-only level stands for (`price_only_ratio`, assumption). Live radar needs the user's location (422 origin_required). After the first phone test: the price change compares with the latest report on or before 3 days back this week, else the week's first report (Agmarknet skips days); a week with no price change uses the market's historical range; the out-of-date banner follows only the recommended and nearest markets (both modes), and the app shows "Prices from <date>" (`data.prices_date`) in Live; "away from a likely glut" shows only when the nearest market is watch or glut. Rescue and Recover need no prices; Live uses today's forecast temperature (D29). |
| D35 | No negative claims in the app (October 10) | User request after the phone test: the app never shows a loss. Water saved that is 0 or negative hides its row; waste avoided at or below 0 reads "No waste avoided" (no extra-spoilage line); ranges for waste avoided and kept out of landfill start at 0; each load's money saved and waste avoided count from 0 up in the lifetime total (a load with none never cancels another's); a range whose ends round to the same value shows the value only; a biogas energy of 0 hides its row. The API keeps the signed values (Plans, tests); only the display clamps. Extra distance and diesel stay on the card (a trip cost, Section 14.3). |
| D36 | Phone-test batch 2 (October 10) | Unsold stock could recommend nothing in Mumbai (no seeded outlet in 100 km): the edible part now first tries other mandis within `rescue_radius_km` from the 4,142 mapped markets, live or demo prices (Step 5b), skipping the trader's own mandi (`own_mandi_km` 2, assumption). Harvest age: farmers give days, not hours; the API accepts `days_since_harvest` (x 24; 0 = `harvested_today_hours` 6, assumption, same 6 h as the tomato alpha calibration) or `hours_since_harvest` for farm loads (harvest "harvested", previously counted as 0 h) and unsold stock. A planned harvest stays today or tomorrow: Live has no price forecast, so a later date would not change the advice (same_day, D13). Location: no coordinates field; "Use my location" fills the place name (reverse geocode on the phone); a typed or spoken place replaces GPS. Advisor timeout 29 s (a cold Mumbai request took 13.8 s). Outlets from OpenStreetMap (`scripts/build_osm_outlets.py`, ODbL, each with its OSM URL, "Not yet partnered"): OSM India has little Second Life data: 14 kept (11 compost, 2 food banks, 1 biogas) of 233 tagged elements (most `social_facility=food_bank` tags are ration shops and canteens); two reviewed and excluded (an untagged Delhi 'Bio-Gas Plant' near Ghazipur dairy, so Delhi Recover still shows no unit; a mapping-exercise 'food bank'). Voice: the recording is uploaded with expo-file-system (fetch blob uploads sent nothing on Android); a pulsing ring and timer show recording. Language change remounts the navigation stack (in-place header font changes crashed Android). Settings button on every screen. |
| D37 | Demo day at Azadpur (October 11) | User request: Demo mode fills itself. On start in demo, on switching to demo and after Clear saved data, the app (`app/lib/demo.ts`) runs a fixed demo day through the API on the replay day (29 Sep 2023) and saves it as if each item was confirmed: six farm loads from Azadpur (banana, papaya, guava, pumpkin, capsicum, cabbage, 5,000 kg each; Today's plan) and five unsold lots at Azadpur (onion 3,000 kg 3 days, tomato 3,000 kg 1 day, cabbage 2,000 kg 1 day, banana 2,000 kg 2 days, cauliflower 1,500 kg 1 day). Crops picked from a scan of every routable crop from Azadpur (largest waste avoided with money saved above 0). Checked October 11 against the deployed API: kept out of landfill about 13,100 kg (11,100-18,000) of 41,500 kg, waste avoided mid 2,187 kg, rescued 10,908 kg, money saved about Rs 4.2 lakh (estimate). Loads and lots are simulated ("Demo loads"); prices, routes and weather are real. Live and demo keep separate lifetime totals on the phone, so the demo never mixes with real use. |
| D38 | 2026 replay and stat report (October 11) | User request: simulate a couple of months of 2026. `analysis/simulate_2026.py` runs the advisor's own /plan and /recommend (snapshot mode, REPLAY_DATE per day) on every day of 1 March - 31 May 2026 (the last data in the IDP files): ten Kolar tomato loads (D9), five 5 t loads from Azadpur (tomato, onion, banana, cabbage, cauliflower) and one 2 t unsold tomato lot at Azadpur; NASA POWER temperature at both origins; routes cached (OSM outlets added to the cache). Results (`analysis/sim_summary.py`; JSON in git-ignored `analysis/out/` and `s3://annasetu-data-<suffix>/backtest/sim_2026*.json`; report `docs/stat-report-2026.html`, data embedded): 1,380 loads, 0 errors, deterministic; 94.6% sent away from the nearest mandi; money saved Rs 2.20 crore (1.73-2.96, estimate); waste avoided net +11 t (range -65 to +238 t: Delhi +18 t, mostly banana on 39 Azadpur arrival-glut days; Kolar -6 t, longer trips with no glut this spring); 169 t of 184 t unsold stock rescued to mandis within 100 km. Out-of-sample check (next real price at both markets within 7 days, freight-adjusted): the advice held on 1,248 of 1,279 diverted loads; weak spot Delhi cauliflower (14 of 35). Case study (`analysis/simulate_farm_2026.py`, `docs/case-study-narela-2026.html`): one simulated 8-acre farm near Narela (28.840, 77.060; tomato 3 acres, bottle gourd 2, okra 2 from 15 April, cauliflower 1 in March; quantities from typical yields, labelled simulated in the report), routes cached from the farm; Narela mandi does not report these crops, so the nearest reporting mandi is Azadpur: 112 loads (127 t), 0 errors, 85.7% sent elsewhere, money saved Rs 5.2 lakh (3.7-7.7), waste avoided +844 kg net, 3,576 kg of 3,900 kg unsold stock rescued, advice held on 79 of 92 diverted loads (cauliflower 4 of 10). |
| D39 | Load history and demo date (October 11) | After the phone test: in Demo the Impact page dated records by the phone's day ("Since 11 Oct 2026"), which read as if the demo used today's data; it never did (the API replays 29 Sep 2023). Records now carry the replayed day in demo mode (`stampFor`, live keeps now). The Today's plan tab becomes Today's loads (user's wording): New load on top, today's loads (the current plan's saved loads and unsold lots), then previous loads from earlier days grouped by date, filterable by sold / not sold and crop; each saved load has a sold tick (kept on the phone with the record, with crop and destination). New strings machine-drafted in 17 languages; Santali, Kashmiri, Manipuri and Dogri fall back to English for them. |
| D23 | Bedrock model (October 9) | The account was refused Anthropic model access ("Your account is not authorized" on the use-case form). The adapter now uses the Converse API, so the model is a deploy parameter: Amazon Nova Lite in ap-south-1 (model or APAC inference profile ID confirmed in the console at deploy). Claude Haiku can replace it with no code change if a support case grants access. Without any model, templates and the rule parser run as before. |

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

Cold storage booking, photo quality grading, sensors, payments, real user accounts, App Store or TestFlight submission, retail and household waste, routing for crops without a complete profile (they get the Glut Radar only, D24).

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
| M8 | Rescue and Recover | Oct 10 | `source: mandi_unsold` in /recommend, split proposal, Recover rung (feed, biogas, compost), Impact Ledger lines and headline, "Unsold stock" screen | pytest covers the Section 17.3 Rescue rows; `tsc` passes |

Second demo region (D8) starts after M3 if time allows.
