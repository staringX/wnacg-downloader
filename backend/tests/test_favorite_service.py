"""FavoriteService（フェーズ4: 収藏登録の requests 化）の単体テスト

MangaCrawler をフェイクに差し替え、HttpClient セッション経由の收藏フロー
（フォーム取得→分类マッチ→save_fav POST）を実ネットワーク非依存で検証する。
"""
import pytest

from app.services import favorite_service
from app.services.favorite_service import FavoriteService

BASE = "https://www.example-manga.test"
MANGA_URL = f"{BASE}/photos-index-aid-208661.html"

# select[name=favc_id] を持つ収藏フォーム HTML（作者カテゴリ 2 件）
ADDFAV_HTML = """
<form>
  <select name="favc_id">
    <option value="">請選擇收藏分類</option>
    <option value="11">さわたしゆん</option>
    <option value="22">別の作者</option>
  </select>
</form>
"""


class FakeResponse:
    def __init__(self, status_code=200, text=""):
        self.status_code = status_code
        self.text = text


class FakeClient:
    def __init__(self, base_url=BASE, save_response=None):
        self.base_url = base_url
        self.timeout = (10, 30)
        self._save_response = save_response or FakeResponse(200, "收藏成功")
        self.get_calls = []
        self.post_calls = []

    def get_html(self, url, **kwargs):
        self.get_calls.append(url)
        return ADDFAV_HTML

    def post(self, url, **kwargs):
        self.post_calls.append((url, kwargs))
        return self._save_response


class FakeCrawler:
    def __init__(self, client):
        self.client = client
        self.driver = None
        self.login_calls = 0

    def login(self, user, pwd):
        self.login_calls += 1
        return True

    def close(self):
        pass


@pytest.fixture
def service(monkeypatch):
    """HTTP バックエンドのフェイク MangaCrawler を注入した FavoriteService"""
    client = FakeClient()
    crawler = FakeCrawler(client)
    monkeypatch.setattr(favorite_service, "MangaCrawler", lambda: crawler)
    svc = FavoriteService()
    return svc, crawler, client


# ---------------------------------------------------------------------------
def test_extract_manga_id(service):
    svc, _, _ = service
    assert svc.extract_manga_id(MANGA_URL) == "208661"
    assert svc.extract_manga_id("https://x/none.html") is None


def test_get_favorite_categories_http(service):
    svc, _, client = service
    cats = svc.get_favorite_categories(MANGA_URL)
    assert cats == {"11": "さわたしゆん", "22": "別の作者"}
    # 收藏フォーム URL に ajax パラメータが付く
    assert any("users-addfav-id-208661" in u and "ajax=true" in u
               for u in client.get_calls)


def test_find_category_id_exact_and_fuzzy(service):
    svc, _, _ = service
    assert svc.find_category_id_by_author(MANGA_URL, "さわたしゆん") == "11"
    # 部分一致（模糊匹配）
    assert svc.find_category_id_by_author(MANGA_URL, "別の") == "22"
    assert svc.find_category_id_by_author(MANGA_URL, "未知作者") is None


def test_add_to_favorite_success(service):
    svc, crawler, client = service
    ok = svc.add_to_favorite(MANGA_URL, "さわたしゆん")
    assert ok is True
    # save_fav へ favc_id と XHR ヘッダ・Referer 付きで POST
    url, kwargs = client.post_calls[0]
    assert url == f"{BASE}/users-save_fav-id-208661.html"
    assert kwargs["data"] == {"favc_id": "11"}
    assert kwargs["headers"]["X-Requested-With"] == "XMLHttpRequest"
    assert kwargs["headers"]["Referer"] == MANGA_URL
    assert crawler.login_calls >= 1  # ログインを確実に行う


def test_add_to_favorite_assumes_success_on_200_without_marker(monkeypatch):
    client = FakeClient(save_response=FakeResponse(200, "{}"))
    crawler = FakeCrawler(client)
    monkeypatch.setattr(favorite_service, "MangaCrawler", lambda: crawler)
    svc = FavoriteService()
    assert svc.add_to_favorite(MANGA_URL, "さわたしゆん") is True


def test_add_to_favorite_fails_on_non_200(monkeypatch):
    client = FakeClient(save_response=FakeResponse(403, "forbidden"))
    crawler = FakeCrawler(client)
    monkeypatch.setattr(favorite_service, "MangaCrawler", lambda: crawler)
    svc = FavoriteService()
    assert svc.add_to_favorite(MANGA_URL, "さわたしゆん") is False


def test_add_to_favorite_fails_when_category_missing(service):
    svc, _, client = service
    assert svc.add_to_favorite(MANGA_URL, "存在しない作者") is False
    # カテゴリ未発見なら POST しない
    assert client.post_calls == []
