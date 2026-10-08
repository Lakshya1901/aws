"""Local dev server for the advisor routes, no AWS needed: python -m backend.handlers.local_server [--host H] [--port P]

Wraps advisor.handler in an API Gateway HTTP API (payload v2) shaped event, adds CORS. Defaults to
127.0.0.1:8787, DATA_SOURCE=snapshot and PLANS_FILE=/tmp/annasetu_plans.json. Use --host 0.0.0.0 to reach it
from a phone on the same network. `sam local start-api` is the AWS-shaped path.
"""
import argparse
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qsl, urlsplit

os.environ.setdefault("DATA_SOURCE", "snapshot")
os.environ.setdefault("PLANS_FILE", "/tmp/annasetu_plans.json")

from backend.handlers.advisor import handler  # noqa: E402

CORS = {"Access-Control-Allow-Origin": "*", "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, x-api-key"}


class Handler(BaseHTTPRequestHandler):
    def _send(self, status, headers, body=b""):
        self.send_response(status)
        for k, v in {**CORS, **headers}.items():
            self.send_header(k, v)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _invoke(self, method):
        url = urlsplit(self.path)
        length = int(self.headers.get("Content-Length") or 0)
        event = {"version": "2.0", "rawPath": url.path, "rawQueryString": url.query,
                 "queryStringParameters": dict(parse_qsl(url.query)) or None,
                 "requestContext": {"http": {"method": method, "path": url.path}},
                 "body": self.rfile.read(length).decode() if length else None, "isBase64Encoded": False}
        r = handler(event, None)
        self._send(r["statusCode"], r.get("headers", {}), r["body"].encode())

    def do_GET(self):
        self._invoke("GET")

    def do_POST(self):
        self._invoke("POST")

    def do_OPTIONS(self):
        self._send(204, {})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8787)
    args = ap.parse_args()
    print(f"AnnaSetu advisor on http://{args.host}:{args.port} (DATA_SOURCE={os.environ['DATA_SOURCE']})")
    HTTPServer((args.host, args.port), Handler).serve_forever()


if __name__ == "__main__":
    main()
