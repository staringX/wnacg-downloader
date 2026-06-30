"""ゴールデンマスター・キャプチャ（移行前の現状動作を固定する）

実行: backend ディレクトリで
    .venv/bin/python scripts/capture_golden.py

処理:
1. ログインし、代表的なページの生 HTML を tests/fixtures/ に保存
2. app.crawler.parsers の純関数で解析し、結果を tests/golden/ に JSON 保存

保存物は移行のリグレッション基準。実装完了後に
    .venv/bin/python -m pytest tests/test_crawler_golden.py
で同一出力を再現できることを確認する。

注意: フィクスチャには対象サイトの HTML が含まれる。リポジトリ管理方針は利用者判断。
"""
import os
import sys
import json
import time
import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.crawler import parsers  # noqa: E402

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
DELAY = 1.2

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIX_DIR = os.path.join(ROOT, "tests", "fixtures")
GOLD_DIR = os.path.join(ROOT, "tests", "golden")


def load_env():
    env = {}
    for line in open(os.path.join(ROOT, "..", ".env"), encoding="utf-8"):
        line = line.strip()
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    return env


def save_html(name, text):
    os.makedirs(FIX_DIR, exist_ok=True)
    with open(os.path.join(FIX_DIR, name), "w", encoding="utf-8") as f:
        f.write(text)
    print(f"  fixture 保存: {name} ({len(text)}B)")


def save_golden(name, obj):
    os.makedirs(GOLD_DIR, exist_ok=True)
    with open(os.path.join(GOLD_DIR, name), "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2, sort_keys=True)
    print(f"  golden 保存: {name}")


def main():
    env = load_env()
    s = requests.Session()
    s.headers.update({"User-Agent": UA})

    # base_url 解決（手動 or 発布ページ）。簡略化のため発布ページから取得。
    pub = env.get("PUBLISH_PAGE_URL", "https://wn01.link")
    from bs4 import BeautifulSoup
    r = requests.get(pub, timeout=12, headers={"User-Agent": UA})
    r.encoding = "utf-8"
    soup = BeautifulSoup(r.text, "html.parser")
    base = None
    for ul in soup.find_all("ul"):
        for li in ul.find_all("li"):
            for a in li.find_all("a", {"target": "_blank"}, href=True):
                href = a.get("href", "")
                if "wn01.link" in href or "google.cn" in href:
                    continue
                if a.find("i") and href.startswith("http"):
                    try:
                        if requests.get(f"{href}/", timeout=8,
                                        headers={"User-Agent": UA}).status_code == 200:
                            base = href.rstrip("/")
                            break
                    except Exception:
                        pass
            if base:
                break
        if base:
            break
    if not base:
        print("base_url 解決失敗")
        sys.exit(1)
    print(f"base_url = {base}")

    # ログイン
    s.post(f"{base}/users-check_login.html",
           data={"normal": "1", "login_name": env["MANGA_USERNAME"],
                 "login_pass": env["MANGA_PASSWORD"]},
           timeout=15, headers={"Referer": f"{base}/users-login.html"})
    time.sleep(DELAY)

    def get(url):
        time.sleep(DELAY)
        rr = s.get(url, timeout=15)
        rr.encoding = rr.apparent_encoding or "utf-8"
        return rr.text

    manifest = {"base_url": base, "captured_at": time.strftime("%Y-%m-%d %H:%M:%S")}

    # 1) 書架（カテゴリ + 1ページ目漫画）
    print("\n[1] 書架")
    shelf = get(f"{base}/users-users_fav.html")
    save_html("shelf.html", shelf)
    cats = parsers.parse_favorite_categories(shelf)
    coll = parsers.parse_collection_page(shelf, base)
    save_golden("categories.json", cats)
    save_golden("collection_page.json", coll)
    manifest["shelf_categories"] = len(cats)
    manifest["shelf_mangas"] = len(coll["mangas"])

    # 代表漫画 URL（1件目）
    sample_url = coll["mangas"][0]["manga_url"] if coll["mangas"] else None
    manifest["sample_manga_url"] = sample_url

    # 2) 詳細
    if sample_url:
        print("\n[2] 詳細")
        detail = get(sample_url)
        save_html("detail.html", detail)
        d = parsers.parse_details(detail, manga_url=sample_url, base=base)
        save_golden("details.json", d)

        # 3) view（原図）
        print("\n[3] view / 原図")
        views = parsers.parse_view_links(detail, base)
        manifest["detail_view_links"] = len(views)
        if views:
            view_html = get(views[0])
            save_html("view.html", view_html)
            orig = parsers.parse_original_image(view_html)
            save_golden("original_image.json", {"view_url": views[0], "original_url": orig})

    # 4) 検索（最初のカテゴリ名で）
    if cats:
        print("\n[4] 検索")
        from urllib.parse import quote
        author = next(iter(cats))
        surl = f"{base}/q/?q={quote(author)}&f=_all&s=create_time_DESC&syn=yes"
        search_html = get(surl)
        save_html("search.html", search_html)
        sres = parsers.parse_search_page(search_html, base, author=author)
        save_golden("search.json", {"author": author, "results": sres})
        manifest["search_results"] = len(sres)

    # 5) 収藏フォーム（best-effort）
    if sample_url:
        print("\n[5] 収藏フォーム")
        import re
        m = re.search(r"photos-index-aid-(\d+)\.html", sample_url)
        if m:
            aid = m.group(1)
            fav_html = get(f"{base}/users-addfav-id-{aid}.html?ajax=true&_t={int(time.time()*1000)}")
            save_html("addfav.html", fav_html)
            save_golden("addfav.json", parsers.parse_addfav_form(fav_html))

    save_golden("_manifest.json", manifest)
    print("\n完了。tests/fixtures/ と tests/golden/ を確認してください。")


if __name__ == "__main__":
    main()
