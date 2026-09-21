# -*- coding: utf-8 -*-
import os
import time
from flask import Flask, request, jsonify, Response
from flask_cors import CORS
import requests

app = Flask(__name__)
CORS(app)

TOOL247_BASE = "https://api.tool247.fun/api/pred-log"

# Cache đơn giản (in-memory): cache[game] = {"body":..., "ts": time}
_cache = {}
CACHE_TTL = 3  # giây

http = requests.Session()
http.headers.update({
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0 (compatible; APIProxy/1.0)"
})


@app.route("/")
def root():
    return jsonify({"status": "ok", "service": "prediction-api"}), 200


@app.route("/health")
def health():
    return "OK", 200


@app.route("/api/pred-log")
def pred_log():
    """
    Proxy gọi tool247, trả về y nguyên response.
    Client chỉ thấy API của bạn, không biết nguồn tool247.
    """
    game = (request.args.get("game") or "").strip()
    limit = (request.args.get("limit") or "50").strip()

    if not game:
        # Không truyền game → trả danh sách game hợp lệ (giống format tool247)
        return jsonify({
            "error": "Thiếu ?game=<key>",
            "available": [
                "68tx", "789club",
                "b52_md5", "b52_tx",
                "betvip_md5", "betvip_tx",
                "hitclub_md5", "hitclub_tx",
                "lc79_hu", "lc79_md5",
                "luck8_md5", "luck8_tx",
                "max789_md5", "max789_tx",
                "rikvip_hu", "rikvip_md5",
                "son789_md5", "son789_tx"
            ]
        }), 400

    # Kiểm tra cache
    now = time.time()
    cache_key = f"{game}_{limit}"
    cached = _cache.get(cache_key)
    if cached and (now - cached["ts"] < CACHE_TTL):
        return Response(
            cached["body"],
            status=cached["status"],
            content_type=cached["content_type"]
        )

    # Gọi tool247
    url = f"{TOOL247_BASE}?game={game}&limit={limit}&t={int(now * 1000)}"
    try:
        r = http.get(url, timeout=10)
        content_type = r.headers.get("Content-Type", "application/json")

        # Lưu cache
        _cache[cache_key] = {
            "body": r.content,
            "status": r.status_code,
            "content_type": content_type,
            "ts": now
        }

        return Response(
            r.content,
            status=r.status_code,
            content_type=content_type
        )

    except requests.exceptions.Timeout:
        # Nếu có cache cũ → trả cache dù hết hạn
        if cached:
            return Response(
                cached["body"],
                status=cached["status"],
                content_type=cached["content_type"]
            )
        return jsonify({"error": "Upstream timeout"}), 504

    except requests.exceptions.RequestException as e:
        if cached:
            return Response(
                cached["body"],
                status=cached["status"],
                content_type=cached["content_type"]
            )
        return jsonify({"error": "Upstream error"}), 502


@app.route("/api/games")
def games():
    """Trả về danh sách 18 game."""
    return jsonify({
        "total": 18,
        "games": [
            "68tx", "789club",
            "b52_md5", "b52_tx",
            "betvip_md5", "betvip_tx",
            "hitclub_md5", "hitclub_tx",
            "lc79_hu", "lc79_md5",
            "luck8_md5", "luck8_tx",
            "max789_md5", "max789_tx",
            "rikvip_hu", "rikvip_md5",
            "son789_md5", "son789_tx"
        ]
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
