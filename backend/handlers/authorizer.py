"""HTTP API Lambda authorizer (simple response): the demo app's x-api-key must match SSM /annasetu/app_api_key.

HTTP APIs have no native API keys (CLAUDE.md Section 15.1 asks for a simple key for the demo app).
"""
import hmac
import os

_key = None


def _expected():
    global _key
    if _key is None:
        import boto3
        _key = boto3.client("ssm").get_parameter(Name=os.environ["APP_API_KEY_PARAM"],
                                                 WithDecryption=True)["Parameter"]["Value"]
    return _key


def handler(event, context):
    given = (event.get("headers") or {}).get("x-api-key") or ""
    return {"isAuthorized": bool(given) and hmac.compare_digest(given, _expected())}
