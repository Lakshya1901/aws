"""Amazon Transcribe (voice in) and Amazon Polly (voice out), via the private audio bucket (CLAUDE.md Sections 10, 14.4).

Transcribe batch languages (checked 2026-10-08, https://docs.aws.amazon.com/transcribe/latest/dg/supported-languages.html):
hi-IN, kn-IN and en-IN support batch. Batch accepts M4A, WAV, MP3, FLAC, Ogg, WebM, AMR, MP4
(https://docs.aws.amazon.com/transcribe/latest/dg/how-input.html).

Polly voices (checked 2026-10-08, https://docs.aws.amazon.com/polly/latest/dg/available-voices.html):
Kajal is a bilingual female voice listed for both en-IN and hi-IN with the neural engine (Aditi and
Raveena are standard-only). Polly has no Kannada voice, so Kannada speech is not offered.
"""
import json
import os
import time
import uuid

REGION = os.environ.get("AWS_REGION", "ap-south-1")
TRANSCRIBE_LANG = {"hi": "hi-IN", "kn": "kn-IN", "en": "en-IN"}
POLLY = {"hi": {"VoiceId": "Kajal", "LanguageCode": "hi-IN", "Engine": "neural"},
         "en": {"VoiceId": "Kajal", "LanguageCode": "en-IN", "Engine": "neural"}}
URL_TTL_S = 900


class UnsupportedLanguage(Exception):
    pass


def _client(name):
    import boto3
    return boto3.client(name, region_name=REGION)


def presign_upload(bucket, key, content_type):
    """Presigned PUT URL for the app to upload a recording."""
    return _client("s3").generate_presigned_url(
        "put_object", Params={"Bucket": bucket, "Key": key, "ContentType": content_type}, ExpiresIn=URL_TTL_S)


def transcribe(bucket, key, language, timeout_s=20, poll_s=1.0, sleep=time.sleep):
    """Batch-transcribe s3://bucket/key; returns the transcript text. Raises on failure or timeout."""
    if language not in TRANSCRIBE_LANG:
        raise UnsupportedLanguage(language)
    tr = _client("transcribe")
    job = f"annasetu-{uuid.uuid4().hex}"
    out_key = f"transcripts/{job}.json"
    tr.start_transcription_job(TranscriptionJobName=job, LanguageCode=TRANSCRIBE_LANG[language],
                               Media={"MediaFileUri": f"s3://{bucket}/{key}"},
                               OutputBucketName=bucket, OutputKey=out_key)
    deadline = time.monotonic() + timeout_s
    while True:
        status = tr.get_transcription_job(TranscriptionJobName=job)["TranscriptionJob"]["TranscriptionJobStatus"]
        if status == "COMPLETED":
            break
        if status == "FAILED":
            raise RuntimeError(f"transcription job {job} failed")
        if time.monotonic() >= deadline:
            raise TimeoutError(f"transcription job {job} not done after {timeout_s} s")
        sleep(poll_s)
    body = json.loads(_client("s3").get_object(Bucket=bucket, Key=out_key)["Body"].read())
    return " ".join(t["transcript"] for t in body["results"]["transcripts"]).strip()


def synthesize(text, language, bucket):
    """Polly MP3 written to the audio bucket; returns a presigned GET URL. Hindi and Indian English only."""
    if language not in POLLY:
        raise UnsupportedLanguage(language)
    audio = _client("polly").synthesize_speech(Text=text, OutputFormat="mp3", **POLLY[language])["AudioStream"].read()
    key = f"speech/{uuid.uuid4().hex}.mp3"
    s3 = _client("s3")
    s3.put_object(Bucket=bucket, Key=key, Body=audio, ContentType="audio/mpeg")
    return s3.generate_presigned_url("get_object", Params={"Bucket": bucket, "Key": key}, ExpiresIn=URL_TTL_S)
