#!/usr/bin/env python3
# RSS.app の Instagram フィードを取得し、画像を assets/insta/ に保存して
# index.html の最新情報セクション( <!-- INSTA:START --> 〜 <!-- INSTA:END --> )に
# 投稿カードを書き込む。GitHub Actions から定期実行される想定。
# 外部ライブラリ不要（Python 標準ライブラリのみ）。

import os
import re
import sys
import html
import urllib.request
import xml.etree.ElementTree as ET

FEED_URL = os.environ.get(
    "FEED_URL", "https://rss.app/feeds/JRTiVTLveGseBf9S.xml"
)
MAX_POSTS = 6          # 表示する最新投稿の件数
CAP_LEN = 70           # キャプションの最大文字数
ACCOUNT_URL = "https://www.instagram.com/datumo_yokohama/"

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX = os.path.join(ROOT, "index.html")
IMG_DIR = os.path.join(ROOT, "assets", "insta")

NS = {"media": "http://search.yahoo.com/mrss/"}


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def shortcode(link):
    m = re.search(r"/p/([^/?#]+)", link or "")
    return m.group(1) if m else None


def get_image(item):
    mc = item.find("media:content", NS)
    if mc is not None and mc.get("url"):
        return mc.get("url")
    desc = item.findtext("description") or ""
    m = re.search(r'<img[^>]+src="([^"]+)"', desc)
    return m.group(1) if m else None


def truncate(text, n):
    text = re.sub(r"\s+", " ", text or "").strip()
    return text if len(text) <= n else text[:n].rstrip() + "…"


def main():
    data = fetch(FEED_URL)
    root = ET.fromstring(data)
    items = root.findall("./channel/item")[:MAX_POSTS]

    os.makedirs(IMG_DIR, exist_ok=True)
    for f in os.listdir(IMG_DIR):
        if f.lower().endswith((".jpg", ".jpeg", ".png")):
            os.remove(os.path.join(IMG_DIR, f))

    cards = []
    for it in items:
        link = (it.findtext("link") or "").strip()
        sc = shortcode(link) or (it.findtext("guid") or "post")
        sc = re.sub(r"[^A-Za-z0-9_-]", "", sc)[:40] or "post"
        img_url = get_image(it)
        if not img_url:
            continue
        try:
            img_data = fetch(img_url)
        except Exception as e:
            print("image download failed:", e, file=sys.stderr)
            continue
        fname = sc + ".jpg"
        with open(os.path.join(IMG_DIR, fname), "wb") as f:
            f.write(img_data)
        cap = html.escape(truncate(it.findtext("title") or "", CAP_LEN))
        href = html.escape(link or ACCOUNT_URL)
        cards.append(
            '<div class="insta-card">'
            f'<a href="{href}" target="_blank" rel="noopener">'
            f'<img src="assets/insta/{fname}" alt="エピリタのInstagram投稿" loading="lazy"></a>'
            f'<div class="insta-cap">{cap}</div>'
            f'<div class="insta-more"><a href="{href}" target="_blank" rel="noopener">Instagramで見る →</a></div>'
            "</div>"
        )

    if not cards:
        print("no cards generated; index.html left unchanged", file=sys.stderr)
        return

    block = "\n".join(cards)
    with open(INDEX, encoding="utf-8") as f:
        htmltext = f.read()
    new = re.sub(
        r"(<!-- INSTA:START -->).*?(<!-- INSTA:END -->)",
        lambda m: m.group(1) + "\n" + block + "\n" + m.group(2),
        htmltext,
        flags=re.S,
    )
    if new == htmltext:
        print("markers not found; nothing replaced", file=sys.stderr)
    with open(INDEX, "w", encoding="utf-8") as f:
        f.write(new)
    print(f"updated index.html with {len(cards)} posts")


if __name__ == "__main__":
    main()
