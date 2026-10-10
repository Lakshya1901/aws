"""Voice handler and speech adapter with stubbed boto3 clients (no network, no AWS)."""
import io
import json

import pytest

from backend.adapters import speech
from backend.handlers import voice

BUCKET = "test-audio-bucket"


class StubS3:
    def __init__(self, transcript="do ton tamatar, aaj todenge"):
        self.objects, self.transcript = {}, transcript

    def generate_presigned_url(self, op, Params, ExpiresIn):
        return f"https://s3.example/{op}/{Params['Key']}"

    def put_object(self, Bucket, Key, Body, ContentType):
        self.objects[Key] = Body

    def get_object(self, Bucket, Key):
        body = {"results": {"transcripts": [{"transcript": self.transcript}]}}
        return {"Body": io.BytesIO(json.dumps(body).encode())}


class StubTranscribe:
    def __init__(self, statuses):
        self.statuses, self.started = list(statuses), None

    def start_transcription_job(self, **kw):
        self.started = kw

    def get_transcription_job(self, TranscriptionJobName):
        return {"TranscriptionJob": {"TranscriptionJobStatus": self.statuses.pop(0)}}


class StubPolly:
    def __init__(self):
        self.calls = []

    def synthesize_speech(self, **kw):
        self.calls.append(kw)
        return {"AudioStream": io.BytesIO(b"mp3")}


@pytest.fixture
def aws(monkeypatch):
    monkeypatch.setenv("AUDIO_BUCKET", BUCKET)
    monkeypatch.delenv("BEDROCK_MODEL_ID", raising=False)
    stubs = {"s3": StubS3(), "transcribe": StubTranscribe(["IN_PROGRESS", "COMPLETED"]), "polly": StubPolly()}
    monkeypatch.setattr(speech, "_client", lambda name: stubs[name])
    monkeypatch.setattr(speech.time, "sleep", lambda s: None)
    return stubs


def call(route, body):
    method, path = route.split(" ")
    resp = voice.handler({"routeKey": route, "rawPath": path, "body": json.dumps(body)}, None)
    return resp["statusCode"], json.loads(resp["body"])


def test_upload_shape(aws):
    status, body = call("POST /voice/upload", {"language": "hi", "content_type": "audio/mp4"})
    assert status == 200 and set(body) == {"upload_url", "audio_key"}
    assert voice.KEY_RE.match(body["audio_key"]) and body["audio_key"].endswith(".m4a")
    assert call("POST /voice/upload", {"language": "ta", "content_type": "audio/mp4"})[0] == 200  # Transcribe ta-IN
    assert call("POST /voice/upload", {"language": "ur", "content_type": "audio/mp4"})[0] == 400  # no Transcribe Urdu


def test_parse_shape(aws):
    key = call("POST /voice/upload", {"language": "hi", "content_type": "audio/mp4"})[1]["audio_key"]
    status, body = call("POST /voice/parse", {"audio_key": key, "language": "hi"})
    assert status == 200
    assert body == {"transcript": "do ton tamatar, aaj todenge",
                    "fields": {"crop": "tomato", "quantity_kg": 2000, "origin_place": None, "harvest": "today"},
                    "confidence": "low"}
    started = aws["transcribe"].started
    assert started["LanguageCode"] == "hi-IN" and started["Media"]["MediaFileUri"] == f"s3://{BUCKET}/{key}"


def test_parse_kannada(aws):
    aws["s3"].transcript = "Holur-inda eradu ton tomato, ivattu koyilu"
    key = call("POST /voice/upload", {"language": "kn", "content_type": "audio/mp4"})[1]["audio_key"]
    status, body = call("POST /voice/parse", {"audio_key": key, "language": "kn"})
    assert aws["transcribe"].started["LanguageCode"] == "kn-IN"
    assert body["fields"] == {"crop": "tomato", "quantity_kg": 2000, "origin_place": "Holur", "harvest": "today"}


def test_parse_rejects_foreign_key_and_reports_transcribe_failure(aws):
    assert call("POST /voice/parse", {"audio_key": "../secret", "language": "hi"})[0] == 400
    aws["transcribe"].statuses = ["FAILED"]
    key = call("POST /voice/upload", {"language": "en", "content_type": "audio/wav"})[1]["audio_key"]
    status, body = call("POST /voice/parse", {"audio_key": key, "language": "en"})
    assert status == 502 and body["error"] == "transcribe_failed"


def test_transcribe_timeout(aws):
    aws["transcribe"].statuses = ["IN_PROGRESS"] * 1000
    with pytest.raises(TimeoutError):
        speech.transcribe(BUCKET, "uploads/x.m4a", "hi", timeout_s=0)


def test_speak_hindi_and_english(aws):
    for lang, code in (("hi", "hi-IN"), ("en", "en-IN")):
        status, body = call("POST /speak", {"text": "Madanapalle भेजें", "language": lang})
        assert status == 200 and set(body) == {"audio_url"} and body["audio_url"].startswith("https://")
        assert aws["polly"].calls[-1]["LanguageCode"] == code
        assert aws["polly"].calls[-1]["OutputFormat"] == "mp3"


def test_speak_kannada_unsupported(aws):
    status, body = call("POST /speak", {"text": "ಮದನಪಲ್ಲಿಗೆ ಕಳುಹಿಸಿ", "language": "kn"})
    assert status == 422 and body["error"] == "speak_language_unsupported"
    assert aws["polly"].calls == []


def test_unknown_route_and_bad_body(aws):
    assert voice.handler({"routeKey": "GET /voice/upload"}, None)["statusCode"] == 404
    assert voice.handler({"routeKey": "POST /speak", "body": "not json"}, None)["statusCode"] == 400
