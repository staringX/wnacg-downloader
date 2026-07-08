"""調査用: 収藏夹の全シェルフから漫画タイトル一覧を本番と同一ロジックで取得する

途中からシェルフが 0 冊になる問題（160 冊前後で発生）の再現・原因特定のため、
CollectionCrawler.get_collection_stream() をそのまま回し、取得できた全タイトルと
作者（シェルフ）別の冊数を表示する。0 冊ページの応答内容は collection.py の
診断ログ（HTTP status / title / CF マーカー等）として出力される。

実行（backend ディレクトリで）:
    .venv/bin/python scripts/dump_collection_titles.py
認証情報はプロジェクトルート .env（MANGA_USERNAME / MANGA_PASSWORD）から読み込む。
"""
import os
import sys
import time
from collections import OrderedDict

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

from app.crawler.base import MangaCrawler  # noqa: E402
from app.config import settings  # noqa: E402


def main():
    crawler = MangaCrawler()

    print("[1] ログイン...")
    if not crawler.login(settings.manga_username, settings.manga_password):
        print("✗ ログイン失敗")
        sys.exit(1)
    print(f"✓ ログイン成功 base_url={crawler.base_url}")

    print("\n[2] 収藏夹ストリーム取得（本番と同一ロジック）...")
    start = time.time()
    per_author = OrderedDict()
    total = 0
    try:
        for item in crawler.get_collection_stream():
            total += 1
            per_author.setdefault(item["author"], []).append(item["title"])
            print(f"[{total:4d}] {item['author']} | {item['title'][:70]}")
    finally:
        crawler.close()

    print("\n" + "=" * 70)
    print(f"合計 {total} 冊 / {len(per_author)} シェルフ（{time.time() - start:.0f} 秒）")
    print("=" * 70)
    for author, titles in per_author.items():
        print(f"  {len(titles):4d} 冊  {author}")


if __name__ == "__main__":
    main()
