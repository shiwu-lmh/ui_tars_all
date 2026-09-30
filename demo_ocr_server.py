#!/usr/bin/env python3
"""Local OpenAI-compatible OCR stub for offline pipeline tests.

It deliberately does not inspect or persist image data. Its purpose is to
exercise the HTTP/OCR/output plumbing without sending anything externally.
"""

from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any


def build_completion_response(model: str) -> dict[str, Any]:
    return {
        "id": "demo-ocr-response",
        "object": "chat.completion",
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "本地演示 OCR 结果\n截图已由本地模拟服务接收。\n请人工核对原始截图。",
                },
                "finish_reason": "stop",
            }
        ],
    }


class DemoOcrHandler(BaseHTTPRequestHandler):
    server_version = "DemoOCR/1.0"

    def _send_json(self, status: int, payload: dict[str, Any]) -> None:
        encoded = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def do_GET(self) -> None:  # noqa: N802 - required by BaseHTTPRequestHandler
        if self.path == "/health":
            self._send_json(200, {"status": "ok", "service": "demo-ocr"})
            return
        self._send_json(404, {"error": "not found"})

    def do_POST(self) -> None:  # noqa: N802 - required by BaseHTTPRequestHandler
        if self.path != "/v1/chat/completions":
            self._send_json(404, {"error": "not found"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > 20 * 1024 * 1024:
                raise ValueError("invalid request size")
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            model = str(payload.get("model") or "demo-ocr")[:100]
        except (ValueError, TypeError, json.JSONDecodeError):
            self._send_json(400, {"error": "invalid JSON request"})
            return
        self._send_json(200, build_completion_response(model))

    def log_message(self, format: str, *args: object) -> None:
        # Do not log request bodies or image data.
        super().log_message(format, *args)


def main() -> int:
    parser = argparse.ArgumentParser(description="Local offline OCR API demo server")
    parser.add_argument("--port", type=int, default=8787)
    args = parser.parse_args()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), DemoOcrHandler)
    print(f"Local demo OCR server: http://127.0.0.1:{args.port}/v1")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        return 0
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
