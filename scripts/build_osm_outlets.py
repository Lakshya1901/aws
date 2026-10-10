"""Add Second Life outlets mapped in OpenStreetMap to config/outlets.json (CLAUDE.md Sections 6 and 18, D31).

Source: OpenStreetMap through the Overpass API mirror https://maps.mail.ru/osm/tools/overpass/api/interpreter
(overpass-api.de resets connections from this repo's build network). Data (c) OpenStreetMap contributors, Open
Database License (ODbL) 1.0, https://www.openstreetmap.org/copyright; every outlet carries its OSM URL and this
attribution in `source`.

One query per tag filter over India (area ISO3166-1=IN, admin_level 2), nodes, ways and relations, `out center tags`:
- food_bank: social_facility=food_bank, amenity=food_bank
- biogas: plant:source=biogas, generator:source=biogas, man_made=biogas_plant
- compost: amenity=recycling with recycling:organic, recycling:green_waste or recycling:compost = yes, except
  recycling_type=container (bins) not named "compost..."; man_made=composting_plant (any man_made value containing
  "compost"); a waste transfer station, man_made, landuse or industrial feature named "compost..." (clearly
  composting only: roads, toilets, shops and shelters named "compost..." are skipped)
Queries run 30 s apart, with one retry each: the mirror answers 504 to back-to-back queries.
Food processors are not taken: OSM does not say which produce they accept.

In India social_facility=food_bank is mostly put on ration shops, canteens, caterers and small food units, so a
food bank is kept only when its name, operator or description says "food bank" (or "roti bank").
Only real mapped places: an element without coordinates, a closed, disused, proposed or under-construction one
(lifecycle tags or prefixes), or one with no name (biogas and compost: no name and no operator) is skipped.
state = the state of the nearest market in config/markets.json (haversine). crops = every crop with a profile in
config/crops/ whose second_life lists the type. An OSM outlet within 1 km of an existing outlet of the same type is
dropped; existing entries are kept untouched; earlier OSM entries (outlet_id "osm-...") are replaced.
A filter whose query fails twice is reported (exit 1); its type keeps what the other filters found plus the OSM
entries of an earlier run. Nothing is invented.

Usage: python scripts/build_osm_outlets.py [--raw DIR]   (--raw saves each Overpass response and reuses saved ones)
"""
import argparse
import json
import math
import pathlib
import re
import sys
import time
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
OVERPASS = "https://maps.mail.ru/osm/tools/overpass/api/interpreter"
ATTRIBUTION = "OpenStreetMap contributors, ODbL"
QUERIES = {
    "food_bank": ['nwr["social_facility"="food_bank"](area.in);', 'nwr["amenity"="food_bank"](area.in);'],
    "biogas": ['nwr["plant:source"="biogas"](area.in);', 'nwr["generator:source"="biogas"](area.in);',
               'nwr["man_made"="biogas_plant"](area.in);'],
    "compost": ['nwr["amenity"="recycling"]["recycling:organic"="yes"](area.in);',
                'nwr["amenity"="recycling"]["recycling:green_waste"="yes"](area.in);',
                'nwr["amenity"="recycling"]["recycling:compost"="yes"](area.in);',
                'nwr["man_made"~"compost"](area.in);',
                'nwr["name"~"compost",i](area.in);'],
}
FOOD_BANK_NAME = re.compile(r"food\s*bank|roti\s*bank", re.I)
PAUSE_S = 30
# Reviewed October 10 and left out (OSM element -> reason); not deleted from OSM, only not used here.
EXCLUDE = {
    "way/283807712": "untagged 'Bio-Gas Plant' near Ghazipur dairy, Delhi: likely cattle dung, no sign it takes vegetable waste",
    "node/12595635486": "'food bank' near Abu Road tagged operator '#iit bhu': looks like a mapping exercise",
}
LIFECYCLE = ("disused", "abandoned", "proposed", "construction", "planned", "demolished", "removed", "razed",
             "destroyed", "was", "dismantled")


def overpass(kind, i, raw_dir):
    """Elements for one tag filter of a type; one retry after a pause (the mirror often answers 504 at once)."""
    cached = raw_dir and raw_dir / f"osm_{kind}_{i}.json"
    if cached and cached.exists():
        return json.loads(cached.read_text(encoding="utf-8"))["elements"]
    q = '[out:json][timeout:300];area["ISO3166-1"="IN"][admin_level=2]->.in;' + QUERIES[kind][i] + "out center tags;"
    body = urllib.parse.urlencode({"data": q}).encode()
    last = None
    for attempt in range(2):
        time.sleep(PAUSE_S)
        try:
            with urllib.request.urlopen(urllib.request.Request(OVERPASS, data=body), timeout=360) as r:
                text = r.read().decode("utf-8")
            data = json.loads(text)
            if data.get("remark") and "error" in data["remark"].lower():
                raise RuntimeError(data["remark"])
            if cached:
                cached.write_text(text, encoding="utf-8")
            return data["elements"]
        except Exception as e:  # noqa: BLE001 - report any failure, never invent
            last = e
    raise RuntimeError(f"{kind} {QUERIES[kind][i]} {last}")


def closed(tags):
    for k, v in tags.items():
        head = k.split(":", 1)[0]
        if head in LIFECYCLE and (":" in k or v not in ("no",)):
            return True
        if v in LIFECYCLE and k in ("power", "amenity", "man_made", "landuse", "industrial", "social_facility",
                                    "building", "plant:source", "generator:source", "lifecycle"):
            return True
    return "end_date" in tags


def compost_site(tags):
    """A site that takes a load of organic waste: a recycling centre for organic waste (not a bin), a composting plant,
    or a waste facility, works, landfill or industrial area named "compost..."."""
    named = "compost" in tags.get("name", "").lower()
    if tags.get("amenity") == "recycling":
        return tags.get("recycling_type") != "container" or named
    if "compost" in tags.get("man_made", ""):
        return True
    return named and (tags.get("amenity") == "waste_transfer_station" or "man_made" in tags
                      or "landuse" in tags or "industrial" in tags)


def haversine_km(a_lat, a_lon, b_lat, b_lon):
    p1, p2 = math.radians(a_lat), math.radians(b_lat)
    h = (math.sin((p2 - p1) / 2) ** 2
         + math.cos(p1) * math.cos(p2) * math.sin(math.radians(b_lon - a_lon) / 2) ** 2)
    return 2 * 6371.0 * math.asin(math.sqrt(h))


def to_outlet(kind, el, markets, crops):
    tags = el.get("tags", {})
    lat = el.get("lat", (el.get("center") or {}).get("lat"))
    lon = el.get("lon", (el.get("center") or {}).get("lon"))
    if lat is None or lon is None or closed(tags) or f"{el['type']}/{el['id']}" in EXCLUDE:
        return None
    if kind == "compost" and not compost_site(tags):
        return None
    name = tags.get("name") or tags.get("name:en")
    if kind == "food_bank" and not FOOD_BANK_NAME.search(" ".join(
            tags.get(k, "") for k in ("name", "name:en", "operator", "description"))):
        return None  # in India the tag is mostly on ration shops, canteens, caterers and food units
    operator = tags.get("operator")
    if not name:
        if kind == "food_bank" or not operator:
            return None
        name = f"{'Biogas plant' if kind == 'biogas' else 'Composting site'} ({operator})"
    nearest = min(markets, key=lambda m: haversine_km(lat, lon, m["lat"], m["lon"]))
    osm_type = el["type"]
    url = f"https://www.openstreetmap.org/{osm_type}/{el['id']}"
    contact = (tags.get("website") or tags.get("contact:website") or tags.get("phone")
               or tags.get("contact:phone") or tags.get("email") or tags.get("contact:email"))
    note = "Not yet partnered. Mapped in OpenStreetMap; not checked on the ground."
    if operator:
        note += f" Operator: {operator}."
    return {"outlet_id": f"osm-{kind}-{osm_type[0]}{el['id']}", "type": kind, "name": name, "state": nearest["state"],
            "town": tags.get("addr:city") or tags.get("addr:district") or tags.get("addr:town") or tags.get("addr:village"),
            "lat": round(lat, 5), "lon": round(lon, 5),
            "coord_source": f"OpenStreetMap {osm_type} {el['id']}" + (" (centre)" if osm_type != "node" else ""),
            "crops": [c for c, sl in crops.items() if kind in sl], "min_qty_kg": None, "offer_price_kg": None,
            "contact": contact, "verified": False, "seeded": True, "note": note,
            "source": f"{url} ({ATTRIBUTION})"}


def entry(o):
    """One outlet in the file's layout: an indented block of short lines."""
    groups = [("outlet_id", "type", "name", "state"), ("town", "lat", "lon", "coord_source"),
              ("crops", "min_qty_kg", "offer_price_kg"), ("contact", "verified", "seeded"), ("note", "source")]
    rows = [", ".join(f"{json.dumps(k)}: {json.dumps(o[k], ensure_ascii=False)}" for k in g) for g in groups]
    return "    {" + ",\n      ".join(rows) + "}"


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--raw", type=pathlib.Path, help="save Overpass responses here and reuse saved ones")
    a = p.parse_args()
    if a.raw:
        a.raw.mkdir(parents=True, exist_ok=True)
    markets = [m for m in json.loads((ROOT / "config/markets.json").read_text(encoding="utf-8"))["markets"]
               if m.get("lat") is not None and m.get("coord_confidence") != "low"]
    crops = {}
    for f in sorted((ROOT / "config/crops").glob("*.json")):
        c = json.loads(f.read_text(encoding="utf-8"))
        crops[c["crop_id"]] = c.get("second_life") or []
    path = ROOT / "config/outlets.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    old_osm = {o["outlet_id"]: o for o in doc["outlets"] if o["outlet_id"].startswith("osm-")}
    existing = [o for o in doc["outlets"] if not o["outlet_id"].startswith("osm-")]

    added, failed = [], []
    for kind in QUERIES:
        elements, n_failed = [], 0
        for i in range(len(QUERIES[kind])):
            try:
                elements += overpass(kind, i, a.raw)
            except RuntimeError as e:
                failed.append(str(e))
                n_failed += 1
        if n_failed:  # an incomplete type keeps the OSM entries of an earlier run too
            added += [o for o in old_osm.values() if o["type"] == kind]
        if n_failed == len(QUERIES[kind]):
            continue
        seen, n_skip, n_near = set(), 0, 0
        for el in elements:
            o = to_outlet(kind, el, markets, crops)
            if o is None or o["outlet_id"] in seen or o["outlet_id"] in old_osm and n_failed:
                n_skip += o is None
                continue
            if any(e["type"] == kind and haversine_km(o["lat"], o["lon"], e["lat"], e["lon"]) <= 1.0
                   for e in existing):
                n_near += 1
                continue
            seen.add(o["outlet_id"])
            added.append(o)
        print(f"{kind}: {len(elements)} elements, {len(seen)} added, {n_skip} skipped "
              f"(no coordinates, name or operator; closed or proposed), {n_near} within 1 km of an existing outlet")
    # Existing entries keep their exact text: OSM entries go after them (earlier OSM entries are cut first).
    text = path.read_text(encoding="utf-8")
    cut = text.find(',\n    {"outlet_id": "osm-')
    head = text[:cut] if cut >= 0 else text[:text.rindex("\n  ]")]
    path.write_text(head + "".join(",\n" + entry(o) for o in added) + "\n  ]\n}\n", encoding="utf-8")
    print(f"config/outlets.json: {len(existing)} existing + {len(added)} from OpenStreetMap")
    if failed:
        print("FAILED (left as before): " + "; ".join(failed), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
