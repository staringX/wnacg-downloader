"""実環境 E2E: 漫画を1冊ダウンロードする検証スクリプト（requests + BeautifulSoup）

DB（download_service）に依存せず、MangaCrawler と素の requests で
ログイン → 詳細 → 原図リスト → 画像 DL → CBZ 化までを通しで確認する。

実行（backend ディレクトリで）:
    .venv/bin/python scripts/e2e_download_requests.py [漫画URL] [最大DL枚数]
- 漫画URL 省略時は収藏夹の先頭作品を使用。
- 最大DL枚数 省略時は全ページ（0 で全件）。

認証情報・発布ページはプロジェクトルート .env から読み込む。礼儀的に各画像 DL 間に小休止。
"""
import os
import sys
import time
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_env_into_os():
    path = os.path.join(ROOT, "..", ".env")
    with open(os.path.abspath(path), encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


load_env_into_os()
sys.path.insert(0, ROOT)

import requests  # noqa: E402
from app.crawler.base import MangaCrawler  # noqa: E402
from app.config import settings  # noqa: E402

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
OUT_DIR = os.path.join(ROOT, "scripts", "_e2e_out")


def main():
    manga_url = sys.argv[1] if len(sys.argv) > 1 else None
    max_dl = int(sys.argv[2]) if len(sys.argv) > 2 else 0  # 0=全件

    crawler = MangaCrawler()
    print(f"crawler type: collection={type(crawler.collection).__name__} "
          f"details={type(crawler.details).__name__}")

    print("\n[1] ログイン...")
    if not crawler.login(settings.manga_username, settings.manga_password):
        print("✗ ログイン失敗")
        sys.exit(1)
    print(f"✓ ログイン成功 base_url={crawler.base_url}")

    # 対象漫画の決定
    if not manga_url:
        print("\n[2] 収藏夹の先頭作品を取得...")
        for item in crawler.get_collection_stream():
            manga_url = item["manga_url"]
            print(f"✓ 対象: {item['title'][:50]} | author={item['author']} | "
                  f"page_count(list)={item['page_count']}")
            break
        if not manga_url:
            print("✗ 収藏夹が空")
            sys.exit(1)
    else:
        print(f"\n[2] 指定 URL: {manga_url}")

    print("\n[3] 詳細取得...")
    details = crawler.get_manga_details(manga_url)
    if not details:
        print("✗ 詳細取得失敗")
        sys.exit(1)
    print(f"✓ title={details['title']!r}")
    print(f"  page_count={details['page_count']} updated_at={details['updated_at']}")
    print(f"  cover={details['cover_image_url']}")
    print(f"  category={details['category']} tags={details['tags']}")

    print("\n[4] 原図リスト取得（並行 HTTP）...")
    t0 = time.time()
    images = crawler.get_manga_images(manga_url)
    print(f"✓ 原図 {len(images)} 件 取得 ({time.time()-t0:.1f}s)")
    if not images:
        print("✗ 原図ゼロ")
        sys.exit(1)
    # 先頭3件の整合性確認（index 昇順・/data/・非 /t/）
    for im in images[:3]:
        print(f"  - {im['index']:>3} {im['filename']}  {im['url']}")
        assert "/data/" in im["url"] and "/t/" not in im["url"], "原図でない URL"
    assert [im["index"] for im in images] == list(range(1, len(images) + 1)), "index 不連続"

    # DL 枚数の決定
    targets = images if max_dl <= 0 else images[:max_dl]
    print(f"\n[5] 画像ダウンロード（{len(targets)}/{len(images)} 枚）...")
    os.makedirs(OUT_DIR, exist_ok=True)
    sess = requests.Session()
    sess.headers.update({"User-Agent": UA})
    saved = []
    for im in targets:
        path = os.path.join(OUT_DIR, im["filename"])
        try:
            r = sess.get(im["url"], timeout=30)
            if r.status_code == 200 and r.content:
                with open(path, "wb") as f:
                    f.write(r.content)
                saved.append((im["filename"], len(r.content)))
            else:
                print(f"  ✗ {im['filename']} status={r.status_code}")
        except Exception as e:
            print(f"  ✗ {im['filename']} {type(e).__name__}: {e}")
        time.sleep(0.25)
    print(f"✓ {len(saved)}/{len(targets)} 枚 保存")
    print(f"  先頭: {saved[:3]}")

    # CBZ 化
    print("\n[6] CBZ 化...")
    cbz_path = os.path.join(OUT_DIR, "manga.cbz")
    with zipfile.ZipFile(cbz_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for fn, _ in sorted(saved):
            zf.write(os.path.join(OUT_DIR, fn), fn)
    size = os.path.getsize(cbz_path)
    print(f"✓ CBZ: {cbz_path} ({size} bytes, {len(saved)} pages)")

    # サマリ
    print("\n" + "=" * 60)
    print("E2E サマリ（requests バックエンド）")
    print("=" * 60)
    print(f"  原図リンク数        : {len(images)}")
    print(f"  詳細 page_count     : {details['page_count']}")
    print(f"  DL 成功枚数         : {len(saved)} (対象 {len(targets)})")
    match = details["page_count"] in (None, len(images))
    print(f"  page_count == 原図数 : {match} "
          f"({details['page_count']} vs {len(images)})")
    print(f"  CBZ                 : {size} bytes")
    print("  判定: " + ("✓ OK（ブラウザ非依存で DL 完走）"
                        if len(saved) == len(targets) and images else "✗ 要確認"))


if __name__ == "__main__":
    main()
