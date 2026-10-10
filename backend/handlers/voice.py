"""POST /voice/upload, POST /voice/parse, POST /speak (CLAUDE.md Section 13; shapes in app/api/types.ts)."""
import base64
import glob
import json
import logging
import os
import re
import uuid

from backend.adapters import bedrock, speech

log = logging.getLogger()
log.setLevel(logging.INFO)

CROP_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "config", "crops")
# Voice input: the app languages Amazon Transcribe batch supports (CLAUDE.md D27).
LANGS = tuple(speech.TRANSCRIBE_LANG)
EXT = {"audio/mp4": "m4a", "audio/m4a": "m4a", "audio/x-m4a": "m4a", "audio/wav": "wav", "audio/x-wav": "wav",
       "audio/wave": "wav", "audio/mpeg": "mp3", "audio/webm": "webm", "audio/ogg": "ogg", "audio/flac": "flac"}
KEY_RE = re.compile(r"^uploads/[0-9a-f]{32}\.(m4a|wav|mp3|webm|ogg|flac)$")
MAX_SPEAK_CHARS = 1000


def _resp(status, body):
    return {"statusCode": status, "headers": {"Content-Type": "application/json"},
            "body": json.dumps(body, ensure_ascii=False)}


def _err(status, code, message):
    return _resp(status, {"error": code, "message": message})


def _crops():
    """Every configured crop profile (incomplete ones too: /recommend reports those with a 422)."""
    crops = {}
    for path in sorted(glob.glob(os.path.join(CROP_DIR, "*.json"))):
        with open(path, encoding="utf-8") as fh:
            p = json.load(fh)
        crops[p["crop_id"]] = p
    return crops


def upload(body):
    lang, ctype = body.get("language"), body.get("content_type")
    if lang not in LANGS or ctype not in EXT:
        return _err(400, "bad_request", f"language must be one of {LANGS}; content_type one of {sorted(EXT)}")
    key = f"uploads/{uuid.uuid4().hex}.{EXT[ctype]}"
    return _resp(200, {"upload_url": speech.presign_upload(os.environ["AUDIO_BUCKET"], key, ctype),
                       "audio_key": key})


def parse(body):
    key, lang = body.get("audio_key"), body.get("language")
    if lang not in LANGS or not isinstance(key, str) or not KEY_RE.match(key):
        return _err(400, "bad_request", "audio_key from /voice/upload and language en, hi or kn required")
    try:
        transcript = speech.transcribe(os.environ["AUDIO_BUCKET"], key, lang)
    except Exception as e:
        log.exception("transcribe failed")
        return _err(502, "transcribe_failed", str(e))
    p = bedrock.parse_load(transcript, lang, _crops())
    log.info(json.dumps({"voice_parse": {"language": lang, "transcript": transcript, "parsed": p}}, ensure_ascii=False))
    return _resp(200, {"transcript": transcript,
                       "fields": {k: p[k] for k in ("crop", "quantity_kg", "origin_place", "harvest")},
                       "confidence": p["confidence"]})


def speak(body):
    text, lang = body.get("text"), body.get("language")
    if lang not in speech.POLLY:
        # Polly has no Kannada (or other regional) voice; the app shows the text only (Section 10).
        return _err(422, "speak_language_unsupported", "Spoken replies are available in Hindi and English only")
    if not isinstance(text, str) or not text.strip() or len(text) > MAX_SPEAK_CHARS:
        return _err(400, "bad_request", f"text required, at most {MAX_SPEAK_CHARS} characters")
    try:
        return _resp(200, {"audio_url": speech.synthesize(text, lang, os.environ["AUDIO_BUCKET"])})
    except Exception as e:
        log.exception("polly failed")
        return _err(502, "speak_failed", str(e))


ROUTES = {"POST /voice/upload": upload, "POST /voice/parse": parse, "POST /speak": speak}


def handler(event, context):
    route = event.get("routeKey") or f"{event.get('requestContext', {}).get('http', {}).get('method')} {event.get('rawPath')}"
    fn = ROUTES.get(route)
    if fn is None:
        return _err(404, "not_found", route)
    raw = event.get("body") or "{}"
    if event.get("isBase64Encoded"):
        raw = base64.b64decode(raw).decode()
    try:
        body = json.loads(raw)
    except ValueError:
        return _err(400, "bad_request", "body must be JSON")
    if not isinstance(body, dict):
        return _err(400, "bad_request", "body must be a JSON object")
    return fn(body)
