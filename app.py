import os
import shutil
import tempfile
from urllib.parse import urlparse

import yt_dlp
from flask import (Flask, after_this_request, jsonify, request, send_file,
                   send_from_directory)

app = Flask(__name__)
BASE = os.path.dirname(os.path.abspath(__file__))
ALLOWED = ("facebook.com", "fb.watch", "instagram.com", "tiktok.com")


def valid(url):
    p = urlparse(url)
    host = (p.hostname or "").lower()
    return p.scheme in ("http", "https") and any(
        host == d or host.endswith("." + d) for d in ALLOWED
    )


@app.get("/")
def home():
    return send_from_directory(BASE, "index.html")


@app.post("/api/info")
def info():
    url = ((request.get_json(silent=True) or {}).get("url") or "").strip()
    if not valid(url):
        return jsonify(error="Link tidak didukung. Pakai link Facebook, Instagram, atau TikTok."), 400
    try:
        with yt_dlp.YoutubeDL({"quiet": True, "skip_download": True, "noplaylist": True}) as y:
            d = y.extract_info(url, download=False)
        return jsonify(title=d.get("title"), thumbnail=d.get("thumbnail"),
                       uploader=d.get("uploader"))
    except Exception:
        return jsonify(error="Gagal membaca link. Pastikan postingannya publik."), 400


@app.get("/api/download")
def download():
    url = (request.args.get("url") or "").strip()
    kind = request.args.get("kind", "video")
    if not valid(url):
        return "Link tidak valid", 400

    tmp = tempfile.mkdtemp()
    opts = {"quiet": True, "noplaylist": True,
            "outtmpl": os.path.join(tmp, "%(id)s.%(ext)s")}
    if kind == "audio":
        opts.update(format="bestaudio/best", postprocessors=[
            {"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "192"}])
    elif kind == "photo":
        opts.update(skip_download=True, writethumbnail=True)
    else:
        opts.update(format="best[ext=mp4]/best")

    try:
        with yt_dlp.YoutubeDL(opts) as y:
            y.extract_info(url, download=True)
        files = os.listdir(tmp)
        if not files:
            raise RuntimeError("kosong")
        path = os.path.join(tmp, files[0])
    except Exception:
        shutil.rmtree(tmp, ignore_errors=True)
        return "Gagal mengunduh", 400

    @after_this_request
    def cleanup(resp):
        shutil.rmtree(tmp, ignore_errors=True)
        return resp

    return send_file(path, as_attachment=True)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
