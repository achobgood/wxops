#!/usr/bin/env bash
# WebRTC needs a secure context. file:// is not one; http://localhost IS.
#
# Serves with Cache-Control: no-store. Without it the browser reuses a cached
# live.js and you end up debugging code that is not the code on disk — that
# cost a real debugging cycle, so it is not optional.
cd "$(dirname "$0")"
PORT="${1:-8099}"
echo "NAPA PROCall prototype → http://localhost:$PORT/"
echo "(WebRTC/mic requires this origin, not file://)"
exec python3 - "$PORT" <<'PY'
import sys, http.server, socketserver

class NoCache(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Expires', '0')
        super().end_headers()

port = int(sys.argv[1])
socketserver.TCPServer.allow_reuse_address = True
with socketserver.TCPServer(("", port), NoCache) as httpd:
    httpd.serve_forever()
PY
