"""Bedrock adapter with a stubbed client (no network, no AWS). CLAUDE.md Sections 12 and 17.3."""
import json

import pytest

from backend.adapters import bedrock

CROPS = {"tomato": {"crop_id": "tomato", "unit_box_kg": 15}, "onion": {"crop_id": "onion", "unit_box_kg": None}}
FACTS = {"crop": "tomato", "quantity_kg": 2000, "data_stale": False,
         "top": {"name": "Madanapalle", "type": "mandi", "net_rs_per_kg": {"low": 7.8, "mid": 9.4, "high": 11.0}},
         "default": {"name": "Kolar", "risk_level": "glut", "net_rs_per_kg": {"low": -1.2, "mid": 0.4, "high": 1.6}}}


class StubClient:
    def __init__(self, reply=None, exc=None):
        self.reply, self.exc, self.calls = reply, exc, []

    def converse(self, **kw):
        self.calls.append(kw)
        if self.exc:
            raise self.exc
        text = self.reply if isinstance(self.reply, str) else json.dumps(self.reply, ensure_ascii=False)
        return {"output": {"message": {"role": "assistant", "content": [{"text": text}]}}}


@pytest.fixture
def enabled(monkeypatch):
    monkeypatch.setenv("BEDROCK_MODEL_ID", "stub-model")
    monkeypatch.setenv("BEDROCK_ENABLED", "true")

    def use(stub):
        monkeypatch.setattr(bedrock, "_client", lambda timeout_s: stub)
        return stub
    return use


@pytest.mark.parametrize("text,lang", [
    ("two tonnes tomato", "en"),
    ("do ton tamatar, aaj todenge", "hi"),
    ("दो टन टमाटर", "hi"),
    ("Holur-inda eradu ton tomato, ivattu koyilu", "kn"),
    ("ಎರಡು ಟನ್ ಟೊಮೆಟೊ", "kn"),
])
def test_fallback_parses_two_tonnes_tomato(monkeypatch, text, lang):
    monkeypatch.delenv("BEDROCK_MODEL_ID", raising=False)  # config model_id is null -> disabled
    p = bedrock.parse_load(text, lang, CROPS)
    assert (p["crop"], p["quantity_kg"], p["source"], p["confidence"]) == ("tomato", 2000, "fallback", "low")


def test_fallback_units_and_place():
    p = bedrock.fallback_parse("from Kolar 100 boxes tomato tomorrow", CROPS)
    assert (p["quantity_kg"], p["origin_place"], p["harvest"]) == (1500, "Kolar", "tomorrow")
    assert bedrock.fallback_parse("5 quintal onion", CROPS)["quantity_kg"] == 500
    assert bedrock.fallback_parse("10 boxes onion", CROPS)["quantity_kg"] is None  # box size unknown
    assert bedrock.fallback_parse("Holur-inda", CROPS)["origin_place"] == "Holur"
    assert bedrock.fallback_parse("banana 2 ton", CROPS)["crop"] is None  # not a configured crop


def test_bedrock_parse_high_confidence(enabled):
    stub = enabled(StubClient({"crop": "tomato", "quantity_kg": 2000, "origin_place": "Holur",
                               "harvest": "today", "confidence": "high"}))
    p = bedrock.parse_load("Holur-inda eradu ton tomato, ivattu koyilu", "kn", CROPS)
    assert p == {"crop": "tomato", "quantity_kg": 2000, "origin_place": "Holur", "harvest": "today",
                 "confidence": "high", "source": "bedrock"}
    call = stub.calls[0]
    assert call["inferenceConfig"]["temperature"] == 0 and call["system"] == [{"text": bedrock.PARSE_SYSTEM}]


def test_bedrock_parse_guards(enabled):
    enabled(StubClient({"crop": "mango", "quantity_kg": 2000, "origin_place": "Holur",
                        "harvest": "now", "confidence": "high"}))
    p = bedrock.parse_load("two tonnes mango", "en", CROPS)
    assert p["crop"] is None and p["harvest"] is None and p["confidence"] == "low"
    # Wrong unit conversion: rule parser reads 2 tonnes = 2000 kg, model says 2 -> null, low.
    enabled(StubClient({"crop": "tomato", "quantity_kg": 2, "origin_place": "Holur",
                        "harvest": "today", "confidence": "high"}))
    p = bedrock.parse_load("Holur two tonnes tomato today", "en", CROPS)
    assert p["quantity_kg"] is None and p["confidence"] == "low"


def test_bedrock_parse_failure_uses_fallback(enabled):
    enabled(StubClient(exc=TimeoutError("read timeout")))
    p = bedrock.parse_load("do ton tamatar", "hi", CROPS)
    assert (p["crop"], p["quantity_kg"], p["source"]) == ("tomato", 2000, "fallback")


def test_explain_grounded_uses_bedrock(enabled):
    enabled(StubClient({"text": "Send to Madanapalle: you would earn Rs 9.4 per kg, against Rs 0.4 at Kolar.",
                        "language": "en"}))
    e = bedrock.explain(FACTS, "en")
    assert e["source"] == "bedrock" and "9.4" in e["text"]


@pytest.mark.parametrize("text", [
    "Send to Madanapalle, it pays Rs 12 per kg.",           # 12 is not in the facts
    "मदनपल्ले भेजें, ₹१२ प्रति किलो।",                        # Devanagari 12
    "ಮದನಪಲ್ಲಿಗೆ ಕಳುಹಿಸಿ, ೫,೦೦೦ ಕೆಜಿ.",                          # Kannada 5,000
])
def test_explain_foreign_number_uses_template(enabled, text):
    enabled(StubClient({"text": text, "language": "en"}))
    e = bedrock.explain(FACTS, "en")
    assert e["source"] == "template"
    assert e["text"].startswith("Send to Madanapalle")


def test_explain_timeout_uses_template(enabled):
    enabled(StubClient(exc=TimeoutError("read timeout")))
    for lang in ("en", "hi", "kn"):
        e = bedrock.explain(FACTS, lang)
        assert e["source"] == "template" and e["language"] == lang


def test_explain_disabled_template_numbers_grounded(monkeypatch):
    monkeypatch.delenv("BEDROCK_MODEL_ID", raising=False)
    e = bedrock.explain(dict(FACTS, data_stale=True), "kn")
    assert e["source"] == "template" and "ಬೆಲೆಗಳು ಹಳೆಯದಾಗಿರಬಹುದು" in e["text"]
    assert bedrock.numbers_grounded(e["text"], FACTS)


def test_number_normalisation():
    assert bedrock.numbers_in("२,००० kg ೧೫.5") == [2000, 15.5]
    assert bedrock.numbers_grounded("about 9.4", {"x": 9.43})
    assert not bedrock.numbers_grounded("about 9.5", {"x": 9.43})
