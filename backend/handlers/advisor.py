"""Advisor Lambda: GET /risk, POST /recommend, POST /plan, GET /impact (CLAUDE.md Section 13).

API Gateway HTTP API, payload v2. Thin: validation, data access, response shaping; the decisions are in
backend/core. CoreError -> 422 {"error", "message"}; crop_profile_incomplete is sent as crop_not_configured.
"""
import hashlib
import importlib
import json
import os
import traceback
import uuid
from datetime import datetime, timedelta, timezone
from functools import lru_cache

from backend.adapters import location, store
from backend.core.allocate import SECOND_LIFE_ORDER
from backend.core.config import CoreError, assumption, crop_mode, get_crop, radar_crop
from backend.core.impact import total_impact
from backend.core.netvalue import haversine_km
from backend.core.recommend import glut_radar, plan, recommend, rescue

LANGS = ("en", "hi", "kn")
HARVEST = ("today", "tomorrow", "harvested")
SOURCES = ("farm", "mandi_unsold")
ERROR_CODES = {"crop_profile_incomplete": "crop_not_configured"}


class ApiError(Exception):
    def __init__(self, status, code, message):
        super().__init__(message)
        self.status, self.code, self.message = status, code, message


def replay_date():
    return os.environ.get("REPLAY_DATE") or store.configs()["model"].get("replay_date")


def as_of_date():
    """Replay date when set, else today in IST."""
    return replay_date() or (datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)).date().isoformat()


# ---------- explanation ----------

@lru_cache(maxsize=8)
def _copy(path, lang):
    with open(os.path.join(path, "copy", f"{lang}.json"), encoding="utf-8") as fh:
        return json.load(fh)


def _fill(s, **kw):
    for k, v in kw.items():
        s = s.replace("{" + k + "}", str(v))
    return s


def _rs(x):
    return f"{x:.1f}"


def _ratio_driven(option, cfg):
    """True when the option's watch/glut level comes from its arrival ratio (D10: only then cite R)."""
    r = option.get("arrival_ratio")
    return (option.get("risk_level") in ("watch", "glut") and r is not None
            and r >= cfg["model"]["risk"]["watch_ratio"])


def explanation_facts(r, crop, lang, cfg):
    """Computed facts only; the arrival ratio is included only when it drives the default's risk level."""
    top, d = r["top"], r["default"]
    best = max((o for o in [top] + r["alternatives"] if o["type"] == "mandi"),
               key=lambda o: o["net_rs_per_kg"]["mid"], default=None)
    return {
        "crop": crop["names"][lang].lower() if lang == "en" else crop["names"].get(lang, crop["crop_id"]),
        "quantity_kg": r["quantity_kg"],
        "top": {k: top.get(k) for k in ("outlet_id", "name", "type", "net_rs_per_kg", "distance_km", "risk_level")},
        "default": dict({k: d.get(k) for k in ("outlet_id", "name", "net_rs_per_kg", "risk_level", "price_change_3d")},
                        **({"arrival_ratio": d["arrival_ratio"]} if _ratio_driven(d, cfg) else {})),
        "best_fresh_net_rs_per_kg": best["net_rs_per_kg"] if best else None,
        "waste_avoided_kg": r["impact"]["waste_avoided_kg"], "redirected_kg": r["impact"]["redirected_kg"],
        "advice": (r["advice"] or {}).get("code"), "harvest_cost_rs_per_kg": crop["harvest_cost_rs_per_kg"],
        "data_stale": r["data"]["stale"],
    }


def template_text(f, lang):
    """Per-language template from config/copy; every number comes from the facts.

    Reason for moving off the default (D10): its arrival multiple only when the ratio drives its risk level,
    else its 3-day price drop when that drives it; then the net-value comparison.
    """
    c = _copy(store.config_dir(), lang)
    top, d = f["top"], f["default"]
    parts = []
    if top["type"] == "mandi":
        parts += [_fill(c["send_to"], outlet=top["name"]),
                  _fill(c["earn_value"], low=_rs(top["net_rs_per_kg"]["low"]), high=_rs(top["net_rs_per_kg"]["high"]))]
    elif top["type"] != "hold":
        parts.append(_fill(c["second_life_body"], type=c[f"type_{top['type']}"]))
        if top.get("name"):
            parts.append(_fill(c["send_to"], outlet=top["name"]))
    if d["outlet_id"] != top["outlet_id"]:
        if "arrival_ratio" in d:
            parts.append(_fill(c["glut_reason"], market=d["name"], ratio=f"{d['arrival_ratio']:.1f}", crop=f["crop"]))
        elif d["risk_level"] in ("watch", "glut") and d["price_change_3d"] is not None and d["price_change_3d"] < 0:
            parts.append(f"{d['name']}: " + _fill(c["change_3d"], change=round(d["price_change_3d"] * 100)))
        n = d["net_rs_per_kg"]
        parts.append(_fill(c["default_compare"], market=d["name"], low=_rs(n["low"]), high=_rs(n["high"])))
    if f["advice"] and f["best_fresh_net_rs_per_kg"]:
        b = f["best_fresh_net_rs_per_kg"]
        parts.append(_fill(c[f["advice"]], low=_rs(b["low"]), high=_rs(b["high"]), cost=_rs(f["harvest_cost_rs_per_kg"])))
    if f["data_stale"]:
        parts.append(c["stale"])
    return ". ".join(p.rstrip(".") for p in parts) + "."


def rescue_text(r, lang):
    """Rescue explanation from the template only (no Bedrock, D19): edible kg and outlet, then spoiled kg and the
    Recover outlet, which also takes the edible part when no processor or food bank is in radius."""
    c = _copy(store.config_dir(), lang)
    split, top, rec = r["split"], r["top"], r["recover"]

    est = f" ({c['estimate']})" if split["source"] == "estimate" else ""

    def kg(x):
        return _fill(c["kg_value"], v=round(x)) + est

    def dest(o):
        return _fill(c["send_to"], outlet=o.get("name") or c[f"type_{o['type']}"])
    parts = []
    if split["edible_kg"] > 0:
        parts += [f"{c['edible']}: {kg(split['edible_kg'])}"] + ([dest(top)] if top else [])
    if split["spoiled_kg"] > 0:
        parts.append(f"{c['spoiled']}: {kg(split['spoiled_kg'])}")
    if split["spoiled_kg"] > 0 or not top:  # the Recover rung takes the spoiled part, and the edible part too
        parts.append(dest(rec) if rec else c["no_recover_outlet"])  # when no processor or food bank is near
    return ". ".join(p.rstrip(".") for p in parts) + "."


def explain(facts, lang):
    """Bedrock (adapters/bedrock.py, when present and BEDROCK_ENABLED=1) else the template."""
    if os.environ.get("BEDROCK_ENABLED", "").lower() in ("1", "true"):
        try:
            bedrock = importlib.import_module("backend.adapters.bedrock")
            out = bedrock.explain(facts, lang)
            if out and out.get("text") and out.get("source") == "bedrock":
                return {"language": lang, "text": out["text"], "source": out.get("source", "bedrock")}
        except Exception:  # missing module, timeout or guard failure: template (Section 12)
            traceback.print_exc()
    return {"language": lang, "text": template_text(facts, lang), "source": "template"}


# ---------- request helpers ----------

def _language(body):
    lang = body.get("language", "en")
    if lang not in LANGS:
        raise ApiError(400, "bad_request", f"language must be one of {', '.join(LANGS)}")
    return lang


def _float(v, name):
    try:
        return float(v)
    except (TypeError, ValueError):
        raise ApiError(400, "bad_request", f"{name} must be a number") from None


def _destinations(cfg, outlets, origin, market_ctx=None):
    """Destinations to route from origin (Section 8.4): markets and outlets within max_radius_km straight-line; with
    market_ctx (a crop's reporting markets), only its nearest `nearest_markets`, the set allocation considers."""
    radius = assumption(cfg["assumptions"], "max_radius_km")

    def near(items):
        scored = sorted((haversine_km(origin["lat"], origin["lon"], x["lat"], x["lon"]), x["id"], x) for x in items
                        if x["lat"] is not None)
        return [x for d, _, x in scored if d <= radius]
    markets = ([c["market"] for c in market_ctx] if market_ctx is not None else cfg["markets"])
    markets = near([{"id": m["market_id"], "lat": m.get("lat"), "lon": m.get("lon")} for m in markets])
    if market_ctx is not None:
        markets = markets[:cfg["model"]["nearest_markets"]]
    return markets + near([{"id": o["outlet_id"], "lat": o["lat"], "lon": o["lon"]} for o in outlets])


def core_load(l, cfg, outlets, day, ctx=None):
    """Validate one load from the request and add temperature and routes (ctx: {crop: market_context} limits
    routing to the markets allocation considers)."""
    if not isinstance(l.get("crop"), str):
        raise ApiError(400, "bad_request", "crop is required")
    q = l.get("quantity_kg")
    if isinstance(q, bool) or not isinstance(q, (int, float)) or q <= 0:
        raise ApiError(400, "bad_request", "quantity_kg must be a positive number")
    if l.get("harvest") not in HARVEST:
        raise ApiError(400, "bad_request", f"harvest must be one of {', '.join(HARVEST)}")
    get_crop(cfg, l["crop"])
    o = l.get("origin") or {}
    if o.get("lat") is None or o.get("lon") is None:
        raise ApiError(422, "origin_unknown",
                       "Origin needs lat and lon; place names are not geocoded. Send the device location.")
    origin = {"lat": _float(o["lat"], "origin.lat"), "lon": _float(o["lon"], "origin.lon"), "place": o.get("place")}
    radius = assumption(cfg["assumptions"], "max_radius_km")
    if not any(haversine_km(origin["lat"], origin["lon"], m["lat"], m["lon"]) <= radius
               for m in cfg["markets"] if m.get("lat") is not None):
        raise CoreError("no_markets_in_radius", "No reporting markets near you for this crop")
    temp = store.temperature_c(origin["lat"], origin["lon"], day)
    if temp is None:
        raise ApiError(422, "temperature_unavailable", f"No weather data near this origin for {day}")
    return {"crop": l["crop"], "quantity_kg": q, "origin": origin, "harvest": l["harvest"], "temp_c": temp,
            "routes": location.routes_for(origin, _destinations(cfg, outlets, origin, (ctx or {}).get(l["crop"]))),
            "load_id": l.get("load_id")}


def _plan_id(body, day):
    """Hash of the request and as_of_date; a random salt unless PLAN_ID_DETERMINISTIC=1 (tests), so two
    sessions sending the same first load never share a plan."""
    salt = "" if os.environ.get("PLAN_ID_DETERMINISTIC") == "1" else uuid.uuid4().hex
    digest = hashlib.sha256((json.dumps(body, sort_keys=True) + day + salt).encode()).hexdigest()[:10]
    return f"p_{day.replace('-', '')}_{digest}"


def _outlet(o):
    """Core option plus partnered (second-life outlets only; seeded outlets are not partnered)."""
    if o is None:
        return None
    if o["type"] in SECOND_LIFE_ORDER:
        return dict(o, partnered=o.get("verified") is True)
    return o


def _single_mode(modes):
    vals = set(modes.values())
    return vals.pop() if len(vals) == 1 else "same_day"  # mixed crops: no "days early" claims


def _envelope():
    return {"replay_date": replay_date(), "demo_loads": replay_date() is not None}


def _save(plan_id, day, lang, update):
    """Merge into the Plans record and recompute its impact (latest /plan total, else sum of /recommend)."""
    rec = store.get_plan(plan_id) or {"plan_id": plan_id, "created_at": datetime.now(timezone.utc).isoformat(),
                                      "as_of_date": day, "recommendations": [], "plan": None, "overrides": []}
    rec["language"] = lang
    update(rec)
    farm = [x["impact"] for x in rec["recommendations"] if x.get("source", "farm") == "farm"]
    rescued = [x["impact"] for x in rec["recommendations"] if x.get("source", "farm") != "farm"]
    rec["impact"] = total_impact(([rec["plan"]["impact"]] if rec["plan"] else farm) + rescued)
    store.put_plan(rec)


# ---------- routes ----------

def get_risk(q):
    cfg, day = store.configs(), as_of_date()
    crop_id = q.get("crop")
    if not crop_id:
        raise ApiError(400, "bad_request", "crop is required")
    crop = radar_crop(cfg, crop_id)
    out = glut_radar(crop_id, [], cfg["markets"], cfg, day, ctx=store.contexts(crop_id, day))
    by_id = {m["market_id"]: m for m in out["markets"]}
    origin = None
    if q.get("lat") not in (None, "") and q.get("lon") not in (None, ""):
        origin = {"lat": _float(q["lat"], "lat"), "lon": _float(q["lon"], "lon"), "place": q.get("place")}
        routes = location.routes_for(origin, _destinations(cfg, [], origin), live=False)  # radar: no paid routing
    a = cfg["assumptions"]
    rows = []
    # Without an origin or a state, only markets reporting this crop (the national list is long).
    candidates = cfg["markets"] if origin or q.get("state") else [m for m in cfg["markets"] if m["market_id"] in by_id]
    for m in candidates:
        if m.get("lat") is None or m.get("coord_confidence") == "low" or (q.get("state") and m["state"] != q["state"]):
            continue
        dist, approx = None, False
        if origin:
            straight = haversine_km(origin["lat"], origin["lon"], m["lat"], m["lon"])
            if straight > assumption(a, "max_radius_km"):
                continue
            r = routes.get(m["market_id"])
            dist, approx = (r["distance_km"], False) if r else (round(straight * assumption(a, "road_factor"), 1), True)
        r = by_id.get(m["market_id"]) or {}
        rows.append({"market_id": m["market_id"], "name": m["name"], "state": m["state"],
                     "risk_level": r.get("risk_level"), "arrival_ratio": r.get("arrival_ratio"),
                     "modal_price_rs_per_kg": r.get("price_kg"), "price_change_3d": r.get("price_change_3d"),
                     "as_of_date": r.get("latest_date"), "stale": bool(r.get("stale")),
                     "data_complete": r.get("data_complete"), "lead_days": None,
                     "distance_km": dist, "distance_approx": approx})
    if origin:
        rows.sort(key=lambda x: x["distance_km"])
    return {"crop": crop_id, "mode": out["mode"], **_envelope(), "unit_box_kg": crop.get("unit_box_kg"),
            "data": {"as_of_date": day, "stale": any(x["stale"] for x in rows)}, "markets": rows}


def rescue_request(b, cfg, outlets, day):
    """Validate a mandi_unsold request (Step 5b) and add temperature (may be None) and cached routes."""
    if not isinstance(b.get("crop"), str):
        raise ApiError(400, "bad_request", "crop is required")
    q = b.get("quantity_kg")
    if isinstance(q, bool) or not isinstance(q, (int, float)) or q <= 0:
        raise ApiError(400, "bad_request", "quantity_kg must be a positive number")
    h = b.get("hours_since_harvest")
    if isinstance(h, bool) or not isinstance(h, (int, float)) or h < 0:
        raise ApiError(400, "bad_request", "hours_since_harvest must be a number >= 0")
    e, sp = b.get("edible_kg"), b.get("spoiled_kg")
    split = None
    if e is not None or sp is not None:
        if any(isinstance(x, bool) or not isinstance(x, (int, float)) or x < 0 for x in (e, sp)):
            raise ApiError(400, "bad_request", "edible_kg and spoiled_kg must both be numbers >= 0, or both omitted")
        if abs(e + sp - q) > 0.5:
            raise ApiError(400, "bad_request", "edible_kg + spoiled_kg must equal quantity_kg")
        split = {"edible_kg": e, "spoiled_kg": sp}
    get_crop(cfg, b["crop"])
    o = b.get("origin") or {}
    if o.get("lat") is None or o.get("lon") is None:
        raise ApiError(422, "origin_unknown",
                       "Origin needs lat and lon; place names are not geocoded. Send the device location.")
    origin = {"lat": _float(o["lat"], "origin.lat"), "lon": _float(o["lon"], "origin.lon"), "place": o.get("place")}
    return {"crop": b["crop"], "quantity_kg": q, "origin": origin, "hours_since_harvest": h, "split": split,
            "temp_c": store.temperature_c(origin["lat"], origin["lon"], day),
            "routes": location.routes_for(origin, _destinations(dict(cfg, markets=[]), outlets, origin))}


def post_rescue(body):
    cfg, day = store.configs(), as_of_date()
    lang, outlets = _language(body), store.outlets()
    load = rescue_request(body, cfg, outlets, day)
    r = rescue(load, outlets, cfg, day)
    expl = {"language": lang, "text": rescue_text(r, lang), "source": "template"}
    plan_id = body.get("plan_id") or _plan_id(body, day)
    _save(plan_id, day, lang, lambda rec: rec["recommendations"].append(
        {"source": "mandi_unsold", "load": load, "split": r["split"],
         "top": (r["top"] or {}).get("outlet_id"), "recover": (r["recover"] or {}).get("outlet_id"),
         "impact": r["impact"], "explanation": expl}))
    return {"plan_id": plan_id, "source": "mandi_unsold", **_envelope(), "data": r["data"],
            "crop": r["crop"], "quantity_kg": r["quantity_kg"], "split": r["split"],
            "top": _outlet(r["top"]), "recover": _outlet(r["recover"]),
            "alternatives": [_outlet(o) for o in r["alternatives"]],
            "impact": r["impact"], "explanation": expl, "assumptions_used": r["assumptions_used"]}


def post_recommend(body):
    source = body.get("source", "farm")
    if source not in SOURCES:
        raise ApiError(400, "bad_request", f"source must be one of {', '.join(SOURCES)}")
    if source == "mandi_unsold":
        return post_rescue(body)
    cfg, day = store.configs(), as_of_date()
    lang, outlets = _language(body), store.outlets()
    crop_id = body.get("crop")
    ctx = {crop_id: store.contexts(crop_id, day)} if crop_id in cfg["crops"] else {}
    load = core_load(body, cfg, outlets, day, ctx)
    r = recommend(load, [], cfg["markets"], outlets, cfg, day, ctx=ctx)
    crop = get_crop(cfg, load["crop"])
    facts = explanation_facts(r, crop, lang, cfg)
    expl = explain(facts, lang)
    plan_id = body.get("plan_id") or _plan_id(body, day)
    _save(plan_id, day, lang, lambda rec: rec["recommendations"].append(
        {"load": load, "top": r["top"]["outlet_id"], "default": r["default"]["outlet_id"],
         "impact": r["impact"], "advice": r["advice"], "explanation_inputs": facts, "explanation": expl}))
    return {"plan_id": plan_id, "mode": r["mode"], **_envelope(), "data": r["data"],
            "crop": r["crop"], "quantity_kg": r["quantity_kg"],
            "top": _outlet(r["top"]), "default": _outlet(r["default"]),
            "alternatives": [_outlet(o) for o in r["alternatives"]],
            "impact": r["impact"], "explanation": expl,
            "advice": (r["advice"] or {}).get("code"), "harvest_cost_rs_per_kg": crop["harvest_cost_rs_per_kg"],
            "assumptions_used": r["assumptions_used"]}


def _capped(allocations):
    """Markets passed over only because this plan's loads would push them into glut (Section 9 Step 5)."""
    out = set()
    for a in allocations:
        top_mid = (a["top"].get("net_rs_per_kg") or {}).get("mid", float("-inf"))
        out.update(o["outlet_id"] for o in a["alternatives"]
                   if o["type"] == "mandi" and o["projected_risk_level"] == "glut" and o["risk_level"] != "glut"
                   and o["net_rs_per_kg"]["mid"] > max(top_mid, 0))
    return out


def post_plan(body):
    cfg, day = store.configs(), as_of_date()
    lang, outlets = _language(body), store.outlets()
    loads = body.get("loads")
    if not isinstance(loads, list) or not loads:
        raise ApiError(400, "bad_request", "loads must be a non-empty list")
    if any(l.get("source", "farm") != "farm" for l in loads):
        raise ApiError(400, "bad_request", "/plan takes farm loads only; send unsold stock to /recommend")
    ctx = {c: store.contexts(c, day) for c in sorted({l.get("crop") for l in loads if l.get("crop") in cfg["crops"]})}
    core_loads = [core_load(dict(l, load_id=l.get("load_id") or f"L{i + 1}"), cfg, outlets, day, ctx)
                  for i, l in enumerate(loads)]
    p = plan(core_loads, [], cfg["markets"], outlets, cfg, day, ctx=ctx)
    names = {m["market_id"]: m["name"] for m in cfg["markets"]}
    capped = _capped(p["allocations"])
    markets = [{"market_id": m, "name": names.get(m), "crop": c, "added_kg": kg, "capped": m in capped}
               for c, added in p["dA_kg"].items() for m, kg in added.items()]
    markets += [{"market_id": m, "name": names.get(m), "crop": None, "added_kg": 0, "capped": True}
                for m in sorted(capped - {x["market_id"] for x in markets})]
    allocations = [{"load_id": a["load_id"], "crop": a["crop"], "quantity_kg": a["quantity_kg"],
                    "outlet": _outlet(a["top"]), "default": _outlet(a["default"]),
                    "advice": (a["advice"] or {}).get("code"), "impact": a["impact"]} for a in p["allocations"]]
    overrides = [{"load_id": cl["load_id"], "recommended_outlet_id": a["top"]["outlet_id"],
                  "chosen_outlet_id": l["chosen_outlet_id"], "override": bool(l.get("override"))}
                 for l, cl, a in zip(loads, core_loads, p["allocations"]) if l.get("chosen_outlet_id")]
    plan_id = body.get("plan_id") or _plan_id(body, day)

    def update(rec):
        rec["plan"] = {"loads": core_loads, "allocations": [
            {"load_id": a["load_id"], "top": a["top"]["outlet_id"], "default": a["default"]["outlet_id"],
             "impact": a["impact"], "advice": a["advice"]} for a in p["allocations"]],
            "dA_kg": p["dA_kg"], "impact": p["impact"]}
        rec["overrides"] = overrides
    _save(plan_id, day, lang, update)
    return {"plan_id": plan_id, "mode": _single_mode(p["mode"]), "modes": p["mode"], **_envelope(),
            "data": p["data"], "allocations": allocations, "markets": markets, "impact": p["impact"],
            "assumptions_used": p["assumptions_used"]}


def get_impact(q):
    plan_id = q.get("plan_id")
    if not plan_id:
        raise ApiError(400, "bad_request", "plan_id is required")
    rec = store.get_plan(plan_id)
    if rec is None:
        raise ApiError(404, "plan_not_found", f"No plan {plan_id}")
    return {"plan_id": plan_id, **rec["impact"]}


def get_crops(q):
    """Every commodity in config/commodities.json: name, category, markets, whether routing is set up
    (full profile) and its data status (ready | fetching | available, D24)."""
    cfg = store.configs()
    rows = [{"crop_id": c["crop_id"], "name": c["name"], "category": c.get("category"), "markets": c["markets"],
             "preload": bool(c.get("preload")), "routing": c["crop_id"] in cfg["crops"]}
            for c in cfg["commodities"].values()]
    if q.get("crop"):
        rows = [r for r in rows if r["crop_id"] == q["crop"]]
        if not rows:
            raise ApiError(404, "crop_not_found", f"No commodity {q['crop']}")
        rows[0]["status"] = store.crop_status(q["crop"], as_of_date())
    return {"crops": rows}


def post_fetch(body):
    """Load one commodity's data for the radar (and routing, if it has a full profile). Asynchronous: poll
    GET /crops?crop=<id> until status is ready."""
    crop = body.get("crop")
    if crop not in store.configs()["commodities"]:
        raise ApiError(404, "crop_not_found", f"No commodity {crop}")
    status = store.crop_status(crop, as_of_date())
    if status == "available":
        if os.environ.get("DATA_SOURCE") != "dynamodb":
            raise ApiError(422, "fetch_unavailable", "Fetching needs the deployed API (snapshot mode has no queue)")
        status = store.request_fetch(crop, as_of_date())
    return {"crop": crop, "status": status}


ROUTES = {("GET", "/crops"): get_crops, ("POST", "/fetch"): post_fetch, ("GET", "/risk"): get_risk, ("POST", "/recommend"): post_recommend,
          ("POST", "/plan"): post_plan, ("GET", "/impact"): get_impact}


def _response(status, body):
    return {"statusCode": status, "headers": {"Content-Type": "application/json"},
            "body": json.dumps(body, ensure_ascii=False)}


def handler(event, context):
    method = event.get("requestContext", {}).get("http", {}).get("method", "GET")
    path = "/" + (event.get("rawPath") or "/").rstrip("/").rsplit("/", 1)[-1]
    fn = ROUTES.get((method, path))
    if fn is None:
        return _response(404, {"error": "not_found", "message": f"{method} {path}"})
    try:
        if method == "GET":
            arg = event.get("queryStringParameters") or {}
        else:
            raw = event.get("body") or "{}"
            if event.get("isBase64Encoded"):
                import base64
                raw = base64.b64decode(raw).decode()
            arg = json.loads(raw)
            if not isinstance(arg, dict):
                raise ApiError(400, "bad_request", "body must be a JSON object")
        return _response(200, fn(arg))
    except ApiError as e:
        return _response(e.status, {"error": e.code, "message": e.message})
    except CoreError as e:
        return _response(422, {"error": ERROR_CODES.get(e.code, e.code), "message": e.message})
    except json.JSONDecodeError:
        return _response(400, {"error": "bad_request", "message": "body is not valid JSON"})
    except Exception:
        traceback.print_exc()
        return _response(500, {"error": "internal_error", "message": "Something went wrong"})
