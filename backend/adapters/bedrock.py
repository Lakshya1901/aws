"""Bedrock: parse a spoken load and explain a recommendation (CLAUDE.md Section 12). Nothing else.

Bedrock never calculates or chooses. Every output is validated; on any failure the caller gets the
deterministic fallback parser (parse_load) or the per-language template (explain).

The model ID comes from config/model.json `bedrock.model_id` (or the BEDROCK_MODEL_ID env var set at
deploy time). While it is null, or BEDROCK_ENABLED=false, Bedrock is disabled and fallbacks are used.
"""
import json
import logging
import os
import re

log = logging.getLogger(__name__)

CONFIG_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "config")
REGION = os.environ.get("AWS_REGION", "ap-south-1")
LANG_NAMES = {"en": "English", "hi": "Hindi", "kn": "Kannada"}
HARVEST = ("today", "tomorrow", "harvested")

PARSE_SYSTEM = """You extract a produce load from a spoken request in Hindi, Kannada or English.
Return only JSON:
  crop: one of the configured crop_ids, or null
  quantity_kg: number or null (boxes at the crop's unit_box_kg, quintal = 100 kg, tonne = 1000 kg)
  origin_place: string or null
  harvest: "today" | "tomorrow" | "harvested" | null
  confidence: "high" | "low"
If a field is not clearly stated, return null. Never guess."""

EXPLAIN_SYSTEM = """You explain a dispatch recommendation to an FPO manager.
Use ONLY facts in the JSON. Add no numbers, places or claims not in it.
At most two short sentences in {language}.
Sentence 1: where to send and the most important reason, citing one number.
Sentence 2 (optional): the main tradeoff or uncertainty.
If data_stale is true, say prices may be out of date.
Return JSON: {{"text": "...", "language": "<code>"}}"""


def _read(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _settings():
    cfg = _read(os.path.join(CONFIG_DIR, "model.json"))["bedrock"]
    model_id = os.environ.get("BEDROCK_MODEL_ID") or cfg.get("model_id")
    enabled = bool(model_id) and os.environ.get("BEDROCK_ENABLED", "true").lower() != "false"
    return {"enabled": enabled, "model_id": model_id, "temperature": cfg.get("temperature", 0),
            "timeout_s": cfg.get("timeout_s", 3)}


def _client(timeout_s):
    import boto3
    from botocore.config import Config
    return boto3.client("bedrock-runtime", region_name=REGION,
                        config=Config(connect_timeout=timeout_s, read_timeout=timeout_s,
                                      retries={"max_attempts": 0}))


def _invoke(system, user, s):
    """One Converse call (model-agnostic: Amazon Nova or Claude, D23); returns the first JSON object in the reply."""
    resp = _client(s["timeout_s"]).converse(
        modelId=s["model_id"], system=[{"text": system}], messages=[{"role": "user", "content": [{"text": user}]}],
        inferenceConfig={"maxTokens": 300, "temperature": s["temperature"]})
    text = resp["output"]["message"]["content"][0]["text"]
    match = re.search(r"\{.*\}", text, re.S)
    if not match:
        raise ValueError("no JSON in model output")
    return json.loads(match.group(0))


# ---------- numbers ----------

_DIGITS = str.maketrans("०१२३४५६७८९೦೧೨೩೪೫೬೭೮೯", "01234567890123456789")
_NUM = re.compile(r"\d+(?:\.\d+)?")


def numbers_in(text):
    """Numbers in a string: Devanagari and Kannada digits normalised, thousands commas removed."""
    text = str(text).translate(_DIGITS)
    text = re.sub(r"(?<=\d),(?=\d)", "", text)
    return [float(n) for n in _NUM.findall(text)]


def _fact_numbers(obj):
    if isinstance(obj, bool) or obj is None:
        return []
    if isinstance(obj, (int, float)):
        return [abs(float(obj))]
    if isinstance(obj, dict):
        return [n for v in obj.values() for n in _fact_numbers(v)]
    if isinstance(obj, (list, tuple)):
        return [n for v in obj for n in _fact_numbers(v)]
    return numbers_in(obj)


def numbers_grounded(text, facts):
    """True if every number in text equals a number in facts (or that number rounded to the text's precision)."""
    allowed = _fact_numbers(facts)
    for raw in _NUM.findall(re.sub(r"(?<=\d),(?=\d)", "", str(text).translate(_DIGITS))):
        n, places = float(raw), len(raw.split(".")[1]) if "." in raw else 0
        if not any(abs(f - n) < 1e-9 or round(f, places) == n for f in allowed):
            return False
    return True


# ---------- Job 1: parse a spoken load ----------

def parse_load(transcript, language, crops):
    """Fields from a transcript: {crop, quantity_kg, origin_place, harvest, confidence, source}.

    crops: {crop_id: profile}. Bedrock when enabled, else (or on any failure) the fallback parser.
    """
    fallback = fallback_parse(transcript, crops)
    s = _settings()
    if not s["enabled"] or not transcript.strip():
        return fallback
    try:
        user = json.dumps({"crop_ids": sorted(crops), "language": language, "transcript": transcript},
                          ensure_ascii=False)
        out = _invoke(PARSE_SYSTEM, user, s)
    except Exception as e:  # timeout, throttling, bad JSON: never block the user
        log.warning("bedrock parse failed: %s", e)
        return fallback
    return _validate_parse(out, crops, fallback)


def _validate_parse(out, crops, fallback):
    crop = out.get("crop") if out.get("crop") in crops else None
    qty = out.get("quantity_kg")
    qty = float(qty) if isinstance(qty, (int, float)) and not isinstance(qty, bool) and qty > 0 else None
    # Units guard: if the rule parser read an explicit quantity and unit, Bedrock's kg must match it.
    if qty is not None and fallback["quantity_kg"] is not None and abs(qty - fallback["quantity_kg"]) > 1e-6:
        qty, confident = None, False
    else:
        confident = out.get("confidence") == "high"
    place = out.get("origin_place")
    place = place.strip() if isinstance(place, str) and place.strip() else None
    harvest = out.get("harvest") if out.get("harvest") in HARVEST else None
    fields = {"crop": crop, "quantity_kg": qty, "origin_place": place, "harvest": harvest}
    complete = confident and all(v is not None for v in fields.values())
    return {**fields, "confidence": "high" if complete else "low", "source": "bedrock"}


# Fallback rule parser (used when Bedrock is disabled or fails). Small on purpose: digits, number words
# one to ten, units, crop names and day words in English, Hindi and Kannada (romanised and native script).
_NUMBER_WORDS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "ek": 1, "do": 2, "teen": 3, "char": 4, "chaar": 4, "paanch": 5, "panch": 5, "chhe": 6, "che": 6,
    "saat": 7, "aath": 8, "nau": 9, "das": 10,
    "एक": 1, "दो": 2, "तीन": 3, "चार": 4, "पांच": 5, "पाँच": 5, "छह": 6, "छः": 6, "सात": 7, "आठ": 8, "नौ": 9, "दस": 10,
    "ondu": 1, "eradu": 2, "yeradu": 2, "mooru": 3, "muru": 3, "naalku": 4, "nalku": 4, "aidu": 5, "aaru": 6,
    "elu": 7, "entu": 8, "ombattu": 9, "hattu": 10,
    "ಒಂದು": 1, "ಎರಡು": 2, "ಮೂರು": 3, "ನಾಲ್ಕು": 4, "ಐದು": 5, "ಆರು": 6, "ಏಳು": 7, "ಎಂಟು": 8, "ಒಂಬತ್ತು": 9, "ಹತ್ತು": 10,
}
_UNITS = {
    "tonne": ("ton", "tons", "tonne", "tonnes", "टन", "ಟನ್"),
    "quintal": ("quintal", "quintals", "kwintal", "kuintal", "क्विंटल", "ಕ್ವಿಂಟಾಲ್", "ಕ್ವಿಂಟಲ್"),
    "kg": ("kg", "kgs", "kilo", "kilos", "kilogram", "kilograms", "किलो", "ಕೆಜಿ", "ಕಿಲೋ"),
    "box": ("box", "boxes", "crate", "crates", "peti", "petti", "पेटी", "ಬಾಕ್ಸ್", "ಪೆಟ್ಟಿಗೆ"),
}
_UNIT_OF = {w: u for u, words in _UNITS.items() for w in words}
_KG_PER = {"tonne": 1000, "quintal": 100, "kg": 1}
_CROP_WORDS = {
    "tomato": ("tomato", "tomatoes", "tamatar", "tamato", "टमाटर", "ಟೊಮೆಟೊ", "ಟೊಮ್ಯಾಟೊ", "ಟೊಮೇಟೊ"),
    "onion": ("onion", "onions", "pyaz", "pyaaz", "kanda", "प्याज", "eerulli", "erulli", "ಈರುಳ್ಳಿ"),
    "potato": ("potato", "potatoes", "aloo", "alu", "आलू", "aalugadde", "alugadde", "ಆಲೂಗಡ್ಡೆ"),
    "banana": ("banana", "bananas", "kela", "केला", "baale", "bale", "ಬಾಳೆ", "ಬಾಳೆಹಣ್ಣು"),
}
_HARVEST_WORDS = {
    "today": ("today", "aaj", "आज", "ivattu", "indu", "ಇವತ್ತು", "ಇಂದು"),
    "tomorrow": ("tomorrow", "naale", "nale", "ನಾಳೆ"),
    "harvested": ("harvested",),
}


_TOKEN = r"\d+(?:\.\d+)?|[a-z]+|[\u0900-\u0963\u0970-\u097F]+|[\u0C80-\u0CE5\u0CF0-\u0CFF]+"


def _tokens(text):
    text = text.lower().translate(_DIGITS)
    text = re.sub(r"(?<=\d),(?=\d)", "", text)
    text = re.sub(r"(\d)([^\d\s.])", r"\1 \2", text)  # "2000kg" -> "2000 kg"
    return re.findall(r"\d+(?:\.\d+)?|[^\W\d_]+(?:[ऀ-ॿಀ-೿]*)", text)


def fallback_parse(transcript, crops):
    """Rule-based parse; always confidence "low" so the user confirms every field."""
    toks = _tokens(transcript or "")
    crop = next((c for c, words in _CROP_WORDS.items() if c in crops and any(t in words for t in toks)), None)
    qty = None
    for i, t in enumerate(toks[:-1]):
        n = float(t) if t[0].isdigit() else _NUMBER_WORDS.get(t)
        unit = _UNIT_OF.get(toks[i + 1])
        if n is None or unit is None:
            continue
        if unit == "box":
            box = (crops.get(crop) or {}).get("unit_box_kg")
            qty = n * box if box else None
        else:
            qty = n * _KG_PER[unit]
        break
    harvest = next((h for h, words in _HARVEST_WORDS.items() if any(t in words for t in toks)), None)
    text = transcript or ""
    m = (re.search(r"\bfrom\s+([a-z]+)", text, re.I) or re.search(r"\b([a-z]+)[- ]inda\b", text, re.I)
         or re.search(r"([\u0900-\u0963\u0970-\u097F]+)\s+से(?:\s|$)", text))
    place = m.group(1).capitalize() if m else None
    return {"crop": crop, "quantity_kg": qty, "origin_place": place, "harvest": harvest,
            "confidence": "low", "source": "fallback"}


# ---------- Job 2: explain a recommendation ----------

def explain(facts, language):
    """{"text", "language", "source": "bedrock" | "template"}.

    facts: computed facts only, e.g.
      {"crop": "tomato", "quantity_kg": 2000, "data_stale": false,
       "top": {"name": "Madanapalle", "type": "mandi", "net_rs_per_kg": {"low", "mid", "high"}, ...},
       "default": {"name": "Kolar", "net_rs_per_kg": {...}, "risk_level": "glut", ...}}
    The template needs top.name, and uses top/default net_rs_per_kg and data_stale when present.
    """
    s = _settings()
    if s["enabled"]:
        try:
            out = _invoke(EXPLAIN_SYSTEM.format(language=LANG_NAMES.get(language, "English")),
                          json.dumps(facts, ensure_ascii=False), s)
            text = out.get("text")
            if isinstance(text, str) and text.strip() and numbers_grounded(text, facts):
                return {"text": text.strip(), "language": language, "source": "bedrock"}
            log.warning("bedrock explanation rejected by number guard: %r", text)
        except Exception as e:
            log.warning("bedrock explain failed: %s", e)
    return template(facts, language)


def _fmt(x):
    return f"{x:.1f}".rstrip("0").rstrip(".")


def template(facts, language):
    """Deterministic explanation from config/copy/<language>.json strings."""
    if language not in LANG_NAMES:
        language = "en"
    copy = _read(os.path.join(CONFIG_DIR, "copy", f"{language}.json"))
    top, default = facts.get("top") or {}, facts.get("default") or {}
    parts = [copy["send_to"].format(outlet=top.get("name") or top.get("outlet_id") or "")]
    net = top.get("net_rs_per_kg")
    if net and net.get("low") is not None and net.get("high") is not None:
        earn = copy["earnings"] + ": " + copy["earn_value"].format(low=_fmt(net["low"]), high=_fmt(net["high"]))
        dnet = default.get("net_rs_per_kg")
        if dnet and dnet.get("low") is not None and default.get("name") and default.get("name") != top.get("name"):
            earn += " " + copy["default_compare"].format(market=default["name"], low=_fmt(dnet["low"]),
                                                         high=_fmt(dnet["high"]))
        parts.append(earn)
    if facts.get("data_stale"):
        parts.append(copy["stale"])
    return {"text": ". ".join(parts) + ".", "language": language, "source": "template"}
