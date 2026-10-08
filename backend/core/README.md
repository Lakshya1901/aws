# backend/core

Deterministic decision engine (CLAUDE.md Section 9). Python standard library only; plain dicts in, plain dicts out. No AWS, no network. Every parameter is read from `config/`.

Floats in `recommend`, `plan` and `glut_radar` outputs are rounded to 4 decimals. `null` means "not yet estimated", never 0.

## Inputs

- `configs`: `config.load_configs(config_dir)` ->
  `{"model", "assumptions", "crops": {crop_id: profile}, "crop_errors": {crop_id: message}, "outlets": [...], "markets": [...]}`.
  Crop profiles with a null required field go to `crop_errors`, never `crops`.
- `market_days`: `[{"date": "YYYY-MM-DD", "market_id", "arrivals_t", "modal_price_kg", "crop"?}]`. Tonnes and Rs/kg (convert with `units`). Missing days are absent rows; `arrivals_t: null` means arrivals unavailable. Rows after `as_of_date` are ignored.
- `markets`: entries of `config/markets.json` (`market_id, name, state, lat, lon, coord_confidence?`). `coord_confidence: "low"` is skipped.
- `outlets`: `config/outlets.json` `outlets` (`outlet_id, type, name, state, lat, lon, crops, offer_price_kg, contact, verified, note`).
- `load`:
  ```
  {"crop": "tomato", "quantity_kg": 2000, "origin": {"lat", "lon", "place"},
   "harvest": "today" | "tomorrow" | "harvested", "temp_c": 31.0,     # mean forecast temperature over the trip
   "hours_since_harvest": 0,                                          # optional, default 0
   "routes": {outlet_id: {"distance_km", "drive_hours"}},             # optional, from the location adapter
   "load_id": "L1"}                                                   # optional, echoed in /plan
  ```
  Without a route, distance = haversine x `road_factor` (`distance_approx: true`) and drive time = distance / `truck_speed_kmph`.

## Errors

`config.CoreError(code, message)`; map to HTTP 422:

| code | when |
| --- | --- |
| `crop_profile_incomplete` | no profile, or a required field is null |
| `no_markets_in_radius` | no reporting market within `max_radius_km` |
| `drive_time_unavailable` | no routed `drive_hours` and `truck_speed_kmph` is null in config |

## Public functions

### recommend.py

`recommend(load, market_days, markets, outlets, configs, as_of_date) -> dict` (Section 13 `/recommend` without `plan_id`, `explanation`):
```
{"mode": "same_day", "data": {"as_of_date", "stale"}, "crop", "quantity_kg",
 "top": option, "default": option (nearest reporting mandi), "alternatives": [option, ...],
 "impact": {"redirected_kg", "waste_avoided_kg": {"low","mid","high"} | null,
            "extra_km", "diesel_l", "co2_kg", "water_l"},
 "advice": null | {"code": "delay_harvest" | "harvest_to_order", "best_net_rs_per_kg", "harvest_cost_rs_per_kg"},
 "assumptions_used": ["freight_rs_per_tonne_km", "dump_share_table", "tomato.alpha", ...]}   # non-sourced inputs only
```
`option` for a mandi:
```
{"outlet_id", "name", "type": "mandi", "state",
 "net_rs_per_kg": {"low","mid","high"}, "price_rs_per_kg": {"low","mid","high"},
 "distance_km", "distance_approx", "drive_hours", "spoilage_share", "spoilage_range": {"low","mid","high"},
 "freight_rs_per_kg", "freight_rs_load", "fee_pct", "commission_pct", "handling_pct",
 "risk_level", "arrival_ratio", "projected_arrival_ratio", "projected_risk_level", "price_change_3d",
 "elasticity_b", "stale", "latest_date", "data_complete"}
```
Second-life option (`type`: `processor` | `food_bank` | `feed_compost`): `outlet_id, name, type, state, net_rs_per_kg (null when offer price unknown), net_note, distance_km, distance_approx, drive_hours, spoilage_share, spoilage_range, freight_rs_per_kg, freight_rs_load, contact, verified, note`.
Hold option (storable crops only): `{"outlet_id": null, "type": "hold", "net_rs_per_kg": null, "net_note": "not yet estimated"}`.

`alternatives` = the other fresh mandis ranked by net mid (highest first), then second-life outlets in hierarchy order (processor, food bank, feed/compost; nearest first within a type).

`plan(loads, market_days, markets, outlets, configs, as_of_date) -> dict` (`/plan`):
```
{"mode": {crop_id: mode}, "data": {"as_of_date", "stale"},
 "allocations": [{"load_id", "crop", "quantity_kg", "top", "default", "alternatives", "impact", "advice"}, ...],  # input order
 "dA_kg": {crop_id: {market_id: kg}},
 "impact": totals (a total is null if any load's value is null),
 "assumptions_used": [...]}
```

`glut_radar(crop_id, market_days, markets, configs, as_of_date) -> dict` (`/risk`):
`{"mode", "data": {"as_of_date", "stale"}, "markets": [risk dict + name, state, lat, lon, elasticity_b]}`.

`market_context(crop_id, market_days, markets, configs, as_of_date) -> [{"market", "risk", "fit"}]` (reporting markets; used by ingest to write MarketRisk).

### Building blocks

- `config.load_configs(dir)`, `config.validate_crop(profile)`, `config.get_crop(configs, crop_id)`, `config.assumption(assumptions, key, state=None)`, `config.assumption_entry(...)` (entry with status/source), `config.crop_mode(model, crop_id)`.
- `units.price_quintal_to_kg(rs)`, `units.quantity_to_kg(q, unit, crop=None)` with unit `kg | quintal | tonne | box`.
- `risk.market_risk(rows, as_of_date, model, assumptions) -> {market_id, as_of_date, latest_date, stale, data_complete, days_of_last_7, a7_t, a7_sum_t, baseline_t, arrival_ratio, price_kg, arrivals_t, price_change_3d, risk_level}`; `risk.risk_level(ratio, dp, thresholds)`; `risk.projected_ratio(risk, added_t)`; `risk.baseline(rows_by_date, anchor_date)`.
- `pricing.fit_elasticity(rows, as_of_date, model) -> {b, r2, resid_sd, n, b_source: fit|clipped|fallback}`; `pricing.price_on_arrival(price_kg, arrivals_t, added_t, b, resid_sd, sd_multiplier=1) -> {low, mid, high}`.
- `spoilage.shelf_life_hours(temp_c, sl_ref_hours, q10, t_ref_c)`; `spoilage.spoilage_share(hours, temp_c, crop) -> {low, mid, high}`.
- `netvalue.haversine_km(...)`, `netvalue.route(origin, dest_id, dest, routes, assumptions) -> (km, hours, approx)`, `netvalue.net_value(price, spoil, distance_km, freight_rate, deduct_pct)`, `netvalue.fresh_option(...)`, `netvalue.second_life_option(...)`.
- `allocate.allocate(loads, crops, market_ctx, outlets, configs)`, `allocate.allocate_load(...)`.
- `impact.impact(quantity_kg, default, advised, crop, assumptions)`, `impact.waste_avoided(...)`, `impact.total_impact(impacts)`.

## Model choices not fixed by the spec

- The 7-day window (A7, data_complete) ends at the market's latest reported date on or before `as_of_date`, so stale markets still get a ratio; staleness is flagged separately.
- Price range is in log space: `P_hat * exp(+/- k * resid_sd)`, k = 1, or `stale_range_multiplier` when the market is stale. resid_sd is computed for the b actually used (after clip or fallback).
- Net range: low = low price with high spoilage; high = high price with low spoilage. Spoilage range comes from `sl_ref_hours_range` (long end -> low).
- A market whose projected level is glut is skipped while a paying non-glut market exists; if every paying market would be in glut, the best of them is used.
- Second-life outlets: no mandi wait, fee, commission or handling. In W, processor and food bank have u = 0; feed/compost counts as fully lost as food (L = 1). Hold: W null.
- No harvest advice when the load is already harvested.
- Predictive-mode forward projection of R is not implemented; `mode` is passed through from `config/model.json`.
- Price-below-cost dump (D12): when the default mandi's mid net per kg is below the crop's `harvest_cost_rs_per_kg`, the default side of W uses u = max(u(R), `below_cost_dump_share`) for each of low/mid/high (`config/assumptions.json`, placeholder) and `assumptions_used` lists `below_cost_dump_share`. The advised side is unchanged.
