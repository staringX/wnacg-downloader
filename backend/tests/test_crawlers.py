"""HTTP 版クローラ（フェーズ2: collection/details/search）の単体テスト

保存済みフィクスチャ（tests/fixtures/*.html）を HttpClient のフェイクから返し、
HTTP 版クローラの出力がゴールデン（parsers の結果）と一致すること、
および公開 API の型契約（updated_at が datetime 等）を検証する。
"""
import os
import json
from datetime import datetime

import pytest

from app.crawler import parsers
from app.crawler.collection import CollectionCrawler
from app.crawler.manga_details import MangaDetailsCrawler
from app.crawler.search import SearchCrawler

HERE = os.path.dirname(os.path.abspath(__file__))
FIX = os.path.join(HERE, "fixtures")
GOLD = os.path.join(HERE, "golden")

pytestmark = pytest.mark.skipif(
    not os.path.exists(os.path.join(GOLD, "_manifest.json")),
    reason="ゴールデン未生成。先に scripts/capture_golden.py を実行してください。",
)


def _read(name):
    with open(os.path.join(FIX, name), encoding="utf-8") as f:
        return f.read()


def _gold(name):
    with open(os.path.join(GOLD, name), encoding="utf-8") as f:
        return json.load(f)


def _base():
    return _gold("_manifest.json")["base_url"]


class FakeClient:
    """HttpClient のフェイク。URL 部分文字列 → HTML 文字列でルーティング。"""

    def __init__(self, base_url, routes):
        self.base_url = base_url
        self._routes = routes
        self.calls = []

    def get_html(self, url, **kwargs):
        self.calls.append(url)
        for key, html in self._routes.items():
            if key in url:
                return html
        raise AssertionError(f"想定外の URL: {url}")


# ---------------------------------------------------------------------------
# collection
# ---------------------------------------------------------------------------
def test_collection_stream_matches_golden_single_page():
    base = _base()
    shelf = _read("shelf.html")
    # 書架にカテゴリが無い構成（fixture 依存）か有る構成かで挙動を分けず、
    # 「shelf を 1 ページとして辿った時の漫画集合」がゴールデンと一致することを検証する。
    cats = parsers.parse_favorite_categories(shelf)

    if cats:
        # カテゴリページも shelf を返すフェイク（1 ページで打ち切り＝次ページ無し想定）。
        # next_url の循環は visited で防がれるため、各カテゴリ 1 回ずつ shelf を解析する。
        routes = {"users-users_fav": shelf}
        client = FakeClient(base, routes)
        crawler = CollectionCrawler(client)
        got = list(crawler.get_collection_stream())
        # 全件が shelf 由来の漫画。重複排除済みで golden の mangas と URL 集合が一致。
        golden_urls = {m["manga_url"] for m in _gold("collection_page.json")["mangas"]}
        got_urls = {g["manga_url"] for g in got}
        assert got_urls == golden_urls
        # author は各カテゴリ名のいずれか（システム名は除外済み）
        for g in got:
            assert g["author"] in cats
    else:
        routes = {"users-users_fav": shelf}
        client = FakeClient(base, routes)
        crawler = CollectionCrawler(client)
        got = list(crawler.get_collection_stream())
        golden = _gold("collection_page.json")["mangas"]
        assert [g["manga_url"] for g in got] == [m["manga_url"] for m in golden]
        for g in got:
            assert g["author"] == "未知"


def test_collection_stream_dedup_and_shape():
    base = _base()
    shelf = _read("shelf.html")
    client = FakeClient(base, {"users-users_fav": shelf})
    got = list(CollectionCrawler(client).get_collection_stream())
    urls = [g["manga_url"] for g in got]
    assert len(urls) == len(set(urls))  # 重複なし
    for g in got:
        assert set(g.keys()) == {"title", "author", "manga_url", "page_count"}
        assert g["manga_url"].startswith("http")
        assert g["title"]


# ---------------------------------------------------------------------------
# details
# ---------------------------------------------------------------------------
def test_details_matches_golden_with_datetime_conversion():
    base = _base()
    g = _gold("details.json")
    detail = _read("detail.html")
    client = FakeClient(base, {g["manga_url"]: detail, "detail": detail})
    out = MangaDetailsCrawler(client).get_manga_details(g["manga_url"])

    # updated_at 以外は parsers のゴールデンと一致
    expected = dict(g)
    for k, v in expected.items():
        if k == "updated_at":
            continue
        assert out[k] == v, f"{k} 不一致: {out[k]!r} != {v!r}"

    # updated_at は datetime（または None）に変換されている
    if g["updated_at"] is None:
        assert out["updated_at"] is None
    else:
        assert isinstance(out["updated_at"], datetime)
        assert out["updated_at"].strftime("%Y-%m-%d") == g["updated_at"]


def test_get_manga_images_orders_and_shapes(monkeypatch):
    """view リンク収集 → 各 view から原図取得 → index 昇順・filename 整形を検証"""
    import app.config as cfg
    monkeypatch.setattr(cfg.settings, "image_fetch_threads", 3, raising=False)

    base = _base()
    # view リンクを 5 件持つ詳細ページ（ページ送り無し）を合成
    detail_html = (
        "<html><body>"
        + "".join(f'<a href="photos-view-id-{i}.html">p{i}</a>' for i in range(1, 6))
        + "</body></html>"
    )
    detail_url = f"{base}/photos-index-aid-239091.html"
    view_html = _read("view.html")  # 実フィクスチャ（原図 URL を含む）
    client = FakeClient(base, {detail_url: detail_html, "photos-view-id-": view_html})

    images = MangaDetailsCrawler(client).get_manga_images(detail_url)

    original = parsers.parse_original_image(view_html)
    assert original  # フィクスチャに原図がある前提
    ext = original.rsplit(".", 1)[-1].split("?")[0]

    assert len(images) == 5
    # index は 1..5 昇順、filename は 4 桁ゼロ詰め
    assert [im["index"] for im in images] == [1, 2, 3, 4, 5]
    for im in images:
        assert im["url"] == original
        assert im["filename"] == f"{im['index']:04d}.{ext}"
        assert set(im.keys()) == {"index", "url", "filename"}


def test_get_manga_images_empty_when_no_view_links():
    base = _base()
    client = FakeClient(base, {"photos-index-aid-9": "<html><body>no links</body></html>"})
    out = MangaDetailsCrawler(client).get_manga_images(
        f"{base}/photos-index-aid-9.html")
    assert out == []


# ---------------------------------------------------------------------------
# search
# ---------------------------------------------------------------------------
def test_search_matches_golden_and_filters_by_date():
    base = _base()
    g = _gold("search.json")
    author = g["author"]
    search_html = _read("search.html")
    # since_date を十分過去にして全件通す（打ち切り無し）
    client = FakeClient(base, {"/q/": search_html, "q=": search_html})
    crawler = SearchCrawler(client)
    out = crawler.search_author_updates(author, datetime(2000, 1, 1))

    golden_results = g["results"]
    # updated_at が None でない golden 件のみが返る（HTTP 版は None をスキップ）
    expected_dated = [r for r in golden_results if r["updated_at"]]
    assert len(out) == len(expected_dated)
    for o, e in zip(out, expected_dated):
        assert o["manga_url"] == e["manga_url"]
        assert o["title"] == e["title"]
        assert o["author"] == author
        assert isinstance(o["updated_at"], datetime)


def test_search_stops_at_old_entries():
    base = _base()
    g = _gold("search.json")
    author = g["author"]
    dated = [r for r in g["results"] if r["updated_at"]]
    if not dated:
        pytest.skip("日付付き検索結果が無いフィクスチャ")
    # 最新作品の日付を since にすると、それ以下は打ち切られ 0 件のはず
    newest = max(r["updated_at"] for r in dated)
    since = datetime.strptime(newest[:10], "%Y-%m-%d")
    client = FakeClient(base, {"/q/": _read("search.html"), "q=": _read("search.html")})
    out = SearchCrawler(client).search_author_updates(author, since)
    for o in out:
        assert o["updated_at"] > since


def test_search_no_base_url_returns_empty():
    client = FakeClient(None, {})
    assert SearchCrawler(client).search_author_updates("x", datetime(2000, 1, 1)) == []
