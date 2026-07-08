"""実環境 E2E: 一括ダウンロード（ZIP 直取得 → CBZ 変換）の検証スクリプト

DB（download_service の DB 更新）に依存せず、
下載頁の線路解析 → ZIP ストリーミング取得（線路フォールバック）→ CBZ 変換
までを通しで確認する。ログインは不要（下載頁は非ログインで取得可能）。

実行（backend ディレクトリで）:
    .venv/bin/python scripts/e2e_archive_download.py [漫画URL]
- 漫画URL 省略時はサイトのトップページ先頭の作品を使用。

発布ページ URL 等はプロジェクトルート .env から読み込む。
出力は scripts/_e2e_out/ 配下（リポジトリ非管理）。
"""
import os
import re
import sys
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
# ローカル実行用: .env の Docker 向けパス（/app/...）を E2E 出力先に上書き
os.environ["DOWNLOAD_DIR"] = os.path.join(ROOT, "scripts", "_e2e_out", "downloads")
os.environ["COVER_DIR"] = os.path.join(ROOT, "scripts", "_e2e_out", "covers")
sys.path.insert(0, ROOT)

from pathlib import Path  # noqa: E402

from app.crawler.base import MangaCrawler  # noqa: E402
from app.services.download_service import MangaDownloader  # noqa: E402

OUT_DIR = Path(ROOT) / "scripts" / "_e2e_out"


def main():
    manga_url = sys.argv[1] if len(sys.argv) > 1 else None

    crawler = MangaCrawler()
    try:
        base = crawler.get_available_url()
        if not base:
            print("✗ base_url 解決失敗")
            sys.exit(1)
        crawler.client.base_url = base
        print(f"base_url = {base}")

        if not manga_url:
            html = crawler.client.get_html(f"{base}/")
            m = re.search(r"photos-index-aid-\d+\.html", html)
            if not m:
                print("✗ トップページから作品が見つからない")
                sys.exit(1)
            manga_url = f"{base}/{m.group(0)}"
        print(f"対象: {manga_url}")

        # 詳細（メタデータ。ComicInfo.xml 用）
        details = crawler.get_manga_details(manga_url) or {}
        details["manga_url"] = manga_url
        title = details.get("title") or "e2e_test"
        print(f"タイトル: {title} / 頁数(詳細): {details.get('page_count')}")

        # 線路解決
        routes = crawler.get_download_routes(manga_url)
        print(f"線路: {len(routes)} 件")
        for i, r in enumerate(routes, 1):
            print(f"  [{i}] {r['type']}: "
                  f"{r.get('worker_api') or r.get('url', '')[:80]}")
        if not routes:
            print("✗ 線路が取得できない（従来方式へのフォールバック対象）")
            sys.exit(1)

        # ZIP 取得（フォールバック込み）
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        zip_part = OUT_DIR / "e2e.zip.part"

        def progress(done, total):
            if total and done % (10 * 1024 * 1024) < 1024 * 1024:
                print(f"  ... {done / 1048576:.1f}MB / {total / 1048576:.1f}MB")

        if not crawler.download_archive(routes, zip_part, progress):
            print("✗ 全線路失敗")
            sys.exit(1)
        print(f"✓ ZIP 取得: {zip_part.stat().st_size / 1048576:.1f}MB")

        # CBZ 変換
        downloader = MangaDownloader()
        downloader.download_dir = OUT_DIR / "downloads"
        downloader.cover_dir = OUT_DIR / "covers"
        result = downloader.convert_zip_to_cbz(
            zip_part, title, author=details.get("uploader") or "e2e", manga_metadata=details)
        if not result:
            print("✗ CBZ 変換失敗")
            sys.exit(1)

        cbz = Path(result["cbz_path"])
        with zipfile.ZipFile(cbz) as zf:
            names = zf.namelist()
        print(f"✓ CBZ: {cbz}")
        print(f"  page_count={result['page_count']} file_size={result['file_size']}"
              f" cover={result['cover_path']}")
        print(f"  entries={len(names)} ComicInfo.xml={'ComicInfo.xml' in names}")
        print("\nE2E 成功")
    finally:
        crawler.close()


if __name__ == "__main__":
    main()
