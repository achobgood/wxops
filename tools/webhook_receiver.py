#!/usr/bin/env python3
"""
Webhook test receiver for verifying Webex webhook delivery mechanics.

Usage:
    python3 tools/webhook_receiver.py [--port 5001] [--delay 0] [--fail-code 0] [--fail-count 0]

Options:
    --port          Local port (default: 5001)
    --delay         Response delay in seconds — set high to find Webex's timeout (default: 0)
    --fail-code     HTTP status code to return for the first N requests (e.g., 500)
    --fail-count    How many requests to fail before returning 200 (use with --fail-code)

The receiver logs every incoming request to stdout and to webhook_events.jsonl.
Start ngrok separately: ngrok http 5001
"""
import argparse
import hashlib
import hmac
import json
import time
from datetime import datetime, timezone

from flask import Flask, request

app = Flask(__name__)

LOG_FILE = "webhook_events.jsonl"
fail_remaining = 0
fail_code = 500
response_delay = 0
webhook_secret = None


@app.route("/webhook", methods=["POST"])
def handle_webhook():
    global fail_remaining

    received_at = datetime.now(timezone.utc).isoformat()
    payload = request.get_json(silent=True) or {}

    data = payload.get("data", {})
    event_type = data.get("eventType", payload.get("event", "unknown"))
    call_id = data.get("callId", "")
    session_id = data.get("callSessionId", "")
    resource = payload.get("resource", "unknown")
    actor = data.get("actorPersonId", "")[:20]

    sig = request.headers.get("X-Spark-Signature", "")
    sig_valid = None
    if webhook_secret and sig:
        expected = hmac.new(
            webhook_secret.encode(), request.data, hashlib.sha1
        ).hexdigest()
        sig_valid = hmac.compare_digest(expected, sig)

    entry = {
        "received_at": received_at,
        "resource": resource,
        "event": payload.get("event"),
        "event_type": event_type,
        "call_id": call_id,
        "call_session_id": session_id,
        "actor": actor,
        "signature_valid": sig_valid,
        "response_delay": response_delay,
    }

    print(
        f"[{received_at}] {resource}/{event_type}"
        f"  callId={call_id[:20]}  session={session_id[:20]}"
        f"  sig={'OK' if sig_valid else 'NONE' if sig_valid is None else 'FAIL'}"
    )

    with open(LOG_FILE, "a") as f:
        full = {**entry, "payload": payload}
        f.write(json.dumps(full) + "\n")

    if response_delay > 0:
        print(f"  ... sleeping {response_delay}s to test timeout")
        time.sleep(response_delay)

    if fail_remaining > 0:
        fail_remaining -= 1
        print(f"  -> returning {fail_code} ({fail_remaining} failures left)")
        return "", fail_code

    return "", 200


@app.route("/health", methods=["GET"])
def health():
    return {"status": "ok"}, 200


def main():
    global fail_remaining, fail_code, response_delay, webhook_secret

    parser = argparse.ArgumentParser(description="Webhook test receiver")
    parser.add_argument("--port", type=int, default=5001)
    parser.add_argument("--delay", type=float, default=0)
    parser.add_argument("--fail-code", type=int, default=500)
    parser.add_argument("--fail-count", type=int, default=0)
    parser.add_argument("--secret", type=str, default=None)
    args = parser.parse_args()

    response_delay = args.delay
    fail_code = args.fail_code
    fail_remaining = args.fail_count
    webhook_secret = args.secret

    print(f"Webhook receiver starting on port {args.port}")
    print(f"  Endpoint: http://localhost:{args.port}/webhook")
    print(f"  Log file: {LOG_FILE}")
    if args.delay:
        print(f"  Response delay: {args.delay}s")
    if args.fail_count:
        print(f"  Will return {args.fail_code} for first {args.fail_count} requests")
    if args.secret:
        print(f"  HMAC verification: enabled")
    print("  Waiting for events...\n")

    app.run(host="0.0.0.0", port=args.port, debug=False)


if __name__ == "__main__":
    main()
