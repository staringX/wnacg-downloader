"""クローラ解析のゴールデンマスター・テスト

目的: Selenium → requests+BeautifulSoup 移行の前後で、HTML 解析結果が変わらないことを保証する。

構造:
1. ゴールデン比較（ドリフト検出）: tests/fixtures/*.html を app.crawler.parsers で解析し、
   tests/golden/*.json と完全一致することを検証。移行で解析ロジックを差し替えても
   同一出力なら緑、ズレたら赤。
2. オラクル検証（正しさのアンカー）: 既知の真値をハードコードで検証。
   ゴールデンが「緑だが間違い」になるのを防ぐ。

フィクスチャ/ゴールデンは scripts/capture_golden.py で生成する。
実行: backend で  .venv/bin/python -m pytest tests/test_crawler_golden.py -v
"""
import os
import json
import pytest

from app.crawler import parsers

HERE = os.path.dirname(os.path.abspath(__file__))
FIX = os.path.join(HERE, "fixtures")
GOLD = os.path.join(HERE, "golden")

pytestmark = pytest.mark.skipif(
    not os.path.isdir(GOLD) or not os.path.exists(os.path.join(GOLD, "_manifest.json")),
    reason="ゴールデン未生成。先に scripts/capture_golden.py を実行してください。",
)


def _read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def _gold(name):
    with open(os.path.join(GOLD, name), encoding="utf-8") as f:
        return json.load(f)


def _manifest():
    return _gold("_manifest.json")


def _base():
    return _manifest()["base_url"]


# ---------------------------------------------------------------------------
# 1. ゴールデン比較（ドリフト検出）
# ---------------------------------------------------------------------------
def test_categories_match_golden():
    out = parsers.parse_favorite_categories(_read(os.path.join(FIX, "shelf.html")))
    assert out == _gold("categories.json")


def test_collection_page_match_golden():
    out = parsers.parse_collection_page(_read(os.path.join(FIX, "shelf.html")), _base())
    assert out == _gold("collection_page.json")


def test_details_match_golden():
    g = _gold("details.json")
    out = parsers.parse_details(_read(os.path.join(FIX, "detail.html")),
                                manga_url=g["manga_url"], base=_base())
    assert out == g


def test_original_image_match_golden():
    g = _gold("original_image.json")
    out = parsers.parse_original_image(_read(os.path.join(FIX, "view.html")))
    assert out == g["original_url"]


def test_search_match_golden():
    g = _gold("search.json")
    out = parsers.parse_search_page(_read(os.path.join(FIX, "search.html")),
                                    _base(), author=g["author"])
    assert {"author": g["author"], "results": out} == g


def test_addfav_match_golden():
    out = parsers.parse_addfav_form(_read(os.path.join(FIX, "addfav.html")))
    assert out == _gold("addfav.json")


# ---------------------------------------------------------------------------
# 2. オラクル検証（正しさの独立アンカー）
#    ゴールデンが緑でも内容が壊れていないことを担保する不変条件。
# ---------------------------------------------------------------------------
def test_oracle_details_fields_are_sane():
    g = _gold("details.json")
    assert g["title"] and len(g["title"]) > 3
    # 頁数は正の整数
    assert isinstance(g["page_count"], int) and g["page_count"] > 0
    # 封面は絶対 URL（協議相対でない）
    assert g["cover_image_url"] and g["cover_image_url"].startswith("http")
    # 改版後 CDN: サムネは wnimg ではない（旧セレクタ劣化の再発防止）
    assert "/data/" in g["cover_image_url"]
    # 更新日は YYYY-MM-DD 形式
    assert g["updated_at"] is None or \
        (len(g["updated_at"]) == 10 and g["updated_at"][4] == "-")
    assert isinstance(g["tags"], list)


def test_oracle_original_image_is_full_not_thumb():
    """原図 URL はサムネ(/t/)でなく原図(/data/ 直下)であること（移行の最重要契約）"""
    g = _gold("original_image.json")
    url = g["original_url"]
    assert url, "原図 URL が取得できていない"
    assert "/data/" in url
    assert "/t/" not in url, "サムネイル URL を誤って原図として取得している"
    assert url.startswith("http")


def test_oracle_collection_has_items_with_urls():
    g = _gold("collection_page.json")
    assert len(g["mangas"]) > 0
    for m in g["mangas"]:
        assert m["manga_url"].startswith("http")
        assert "photos-index-aid-" in m["manga_url"]
        assert m["title"]


def test_oracle_categories_exclude_system_names():
    g = _gold("categories.json")
    assert len(g) > 0
    for name in g:
        assert name not in parsers.EXCLUDED_CATEGORY_NAMES


# ---------------------------------------------------------------------------
# 3. 純粋性（同一入力 → 同一出力）の確認
# ---------------------------------------------------------------------------
def test_parsers_are_deterministic():
    html = _read(os.path.join(FIX, "detail.html"))
    a = parsers.parse_details(html, manga_url="x", base=_base())
    b = parsers.parse_details(html, manga_url="x", base=_base())
    assert a == b
