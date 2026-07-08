"""HttpClient（フェーズ1: HTTP クライアント基盤）の単体テスト

実ネットワークには接続せず、requests.Session をフェイクに差し替えて検証する。
- ログイン成功/失敗
- 文字コード補正（charset 欠落時の apparent_encoding 回退）
- 取得のリトライ/タイムアウト（指数バックオフ）
- 発布ページからのドメイン解決
"""
import requests
import pytest

from app.crawler.http_client import HttpClient


# ---------------------------------------------------------------------------
# フェイク Session / Response
# ---------------------------------------------------------------------------
class FakeResponse:
    def __init__(self, text="", status_code=200, content=b"",
                 encoding=None, apparent_encoding="utf-8"):
        self.text = text
        self.status_code = status_code
        self.content = content or text.encode("utf-8", "ignore")
        self.encoding = encoding
        self.apparent_encoding = apparent_encoding
        self.headers = {}


class FakeSession:
    """requests.Session の最小フェイク。get/post の応答をスクリプト化できる。"""

    def __init__(self, get_responses=None, post_response=None):
        # get_responses: URL 部分文字列 → FakeResponse、または順次返す list
        self._get_map = get_responses or {}
        self._post_response = post_response
        self.headers = {}
        self.get_calls = []
        self.post_calls = []

    def get(self, url, **kwargs):
        self.get_calls.append((url, kwargs))
        resp = self._get_map
        if callable(resp):
            return resp(url, **kwargs)
        if isinstance(resp, dict):
            for key, value in resp.items():
                if key in url:
                    if isinstance(value, Exception):
                        raise value
                    return value
            raise AssertionError(f"想定外の GET URL: {url}")
        # list: 順次返す
        item = resp.pop(0)
        if isinstance(item, Exception):
            raise item
        return item

    def post(self, url, **kwargs):
        self.post_calls.append((url, kwargs))
        if isinstance(self._post_response, Exception):
            raise self._post_response
        return self._post_response

    def close(self):
        pass


BASE = "https://www.example-manga.test"


# ---------------------------------------------------------------------------
# ログイン
# ---------------------------------------------------------------------------
def test_login_success():
    shelf = '<a href="users-users_fav-c-1.html">作者A</a>'
    session = FakeSession(
        get_responses={"users-users_fav.html": FakeResponse(text=shelf)},
        post_response=FakeResponse(text="ok"),
    )
    client = HttpClient(base_url=BASE, session=session)

    assert client.login("user", "pwd") is True
    # ログインは POST /users-check_login.html へ規定フィールドで送る
    post_url, post_kwargs = session.post_calls[0]
    assert post_url == f"{BASE}/users-check_login.html"
    assert post_kwargs["data"] == {
        "normal": "1", "login_name": "user", "login_pass": "pwd"}
    assert "Referer" in post_kwargs["headers"]


def test_login_failure_when_shelf_marker_absent():
    # 書架マーカーも username も含まれない → 未ログイン
    session = FakeSession(
        get_responses={"users-users_fav.html": FakeResponse(text="<html>登入</html>")},
        post_response=FakeResponse(text="ok"),
    )
    client = HttpClient(base_url=BASE, session=session)
    assert client.login("user", "pwd") is False


def test_login_success_by_username_marker():
    # 書架マーカーは無いが username が出ていればログイン成立とみなす
    session = FakeSession(
        get_responses={"users-users_fav.html": FakeResponse(text="<b>myname さん</b>")},
        post_response=FakeResponse(text="ok"),
    )
    client = HttpClient(base_url=BASE, session=session)
    assert client.login("myname", "pwd") is True


def test_login_returns_false_when_post_raises():
    session = FakeSession(
        get_responses={},
        post_response=requests.ConnectionError("boom"),
    )
    client = HttpClient(base_url=BASE, session=session)
    assert client.login("user", "pwd") is False


# ---------------------------------------------------------------------------
# 文字コード補正
# ---------------------------------------------------------------------------
def test_get_soup_fixes_missing_encoding():
    html = "<h2>これからの夜</h2>"
    # charset 未指定（encoding=None）でも apparent_encoding で復号できる
    resp = FakeResponse(text=html, encoding=None, apparent_encoding="utf-8")
    session = FakeSession(get_responses={"detail": resp})
    client = HttpClient(base_url=BASE, session=session)

    soup = client.get_soup(f"{BASE}/detail")
    assert resp.encoding == "utf-8"
    assert soup.select_one("h2").get_text() == "これからの夜"


def test_get_soup_overrides_iso_8859_1_fallback():
    resp = FakeResponse(text="<p>中文</p>", encoding="ISO-8859-1",
                        apparent_encoding="utf-8")
    session = FakeSession(get_responses={"page": resp})
    client = HttpClient(base_url=BASE, session=session)
    client.get_soup(f"{BASE}/page")
    assert resp.encoding == "utf-8"


# ---------------------------------------------------------------------------
# リトライ / タイムアウト
# ---------------------------------------------------------------------------
def test_get_retries_then_succeeds(monkeypatch):
    monkeypatch.setattr("app.crawler.http_client.time.sleep", lambda *_: None)
    ok = FakeResponse(text="ok")
    session = FakeSession(get_responses=[requests.Timeout("t"),
                                         requests.ConnectionError("c"), ok])
    client = HttpClient(base_url=BASE, session=session, max_retries=3)
    resp = client.get(f"{BASE}/x")
    assert resp is ok
    assert len(session.get_calls) == 3


def test_get_retries_on_5xx(monkeypatch):
    monkeypatch.setattr("app.crawler.http_client.time.sleep", lambda *_: None)
    session = FakeSession(get_responses=[FakeResponse(status_code=503),
                                         FakeResponse(text="ok", status_code=200)])
    client = HttpClient(base_url=BASE, session=session, max_retries=3)
    resp = client.get(f"{BASE}/x")
    assert resp.status_code == 200
    assert len(session.get_calls) == 2


def test_get_raises_after_exhausting_retries(monkeypatch):
    monkeypatch.setattr("app.crawler.http_client.time.sleep", lambda *_: None)
    session = FakeSession(get_responses=[requests.Timeout("t")] * 5)
    client = HttpClient(base_url=BASE, session=session, max_retries=3)
    with pytest.raises(requests.Timeout):
        client.get(f"{BASE}/x")
    assert len(session.get_calls) == 3


# ---------------------------------------------------------------------------
# 429（レート制限）リトライ
# ---------------------------------------------------------------------------
def test_get_retries_on_429_then_succeeds(monkeypatch):
    slept = []
    monkeypatch.setattr("app.crawler.http_client.time.sleep", lambda s: slept.append(s))
    r429 = FakeResponse(status_code=429)
    r429.headers = {"Retry-After": "3"}
    ok = FakeResponse(text="ok", status_code=200)
    session = FakeSession(get_responses=[r429, ok])
    client = HttpClient(base_url=BASE, session=session)
    resp = client.get(f"{BASE}/x")
    assert resp is ok
    assert len(session.get_calls) == 2
    # Retry-After: 3 を尊重して 3 秒待機（下限 2.0 より大きいのでそのまま）
    assert slept == [3.0]


def test_get_429_respects_retry_after_cap(monkeypatch):
    slept = []
    monkeypatch.setattr("app.crawler.http_client.time.sleep", lambda s: slept.append(s))
    r429 = FakeResponse(status_code=429)
    r429.headers = {"Retry-After": "99999"}  # 過大値
    ok = FakeResponse(text="ok", status_code=200)
    session = FakeSession(get_responses=[r429, ok])
    client = HttpClient(base_url=BASE, session=session)
    client.get(f"{BASE}/x")
    # retry_after_cap（既定 30s）でクランプされる
    assert slept and slept[0] <= 30.0


def test_get_429_without_header_applies_min_wait_floor(monkeypatch):
    slept = []
    monkeypatch.setattr("app.crawler.http_client.time.sleep", lambda s: slept.append(s))
    r429 = FakeResponse(status_code=429)  # Retry-After 無し
    ok = FakeResponse(text="ok", status_code=200)
    session = FakeSession(get_responses=[r429, ok])
    client = HttpClient(base_url=BASE, session=session, backoff=0.5, min_wait_429=2.0)
    client.get(f"{BASE}/x")
    # 指数バックオフ 0.5s より待機下限 2.0s が優先される（CF 制限窓を跨ぐため）
    assert slept == [2.0]


def test_get_429_uses_independent_budget(monkeypatch):
    """429 は接続リトライ(max_retries)とは別予算(max_retries_429)で粘る"""
    monkeypatch.setattr("app.crawler.http_client.time.sleep", lambda *_: None)
    r429 = FakeResponse(status_code=429)
    ok = FakeResponse(text="ok", status_code=200)
    # max_retries=3 でも 429 は max_retries_429=5 まで粘り、4 回目で成功できる
    session = FakeSession(get_responses=[r429, r429, r429, ok])
    client = HttpClient(base_url=BASE, session=session,
                        max_retries=3, max_retries_429=5)
    resp = client.get(f"{BASE}/x")
    assert resp is ok
    assert len(session.get_calls) == 4


def test_get_returns_last_429_when_not_resolved(monkeypatch):
    """429 が最後まで解消しない場合は例外ではなく 429 レスポンスを返す（診断ログ用）"""
    monkeypatch.setattr("app.crawler.http_client.time.sleep", lambda *_: None)
    session = FakeSession(get_responses=[FakeResponse(status_code=429)] * 5)
    client = HttpClient(base_url=BASE, session=session, max_retries_429=3)
    resp = client.get(f"{BASE}/x")
    assert resp.status_code == 429
    assert len(session.get_calls) == 3


# ---------------------------------------------------------------------------
# ドメイン解決（発布ページ）
# ---------------------------------------------------------------------------
def test_resolve_from_publish_page_picks_first_reachable():
    publish_html = """
    <ul><li><a target="_blank" href="https://good.test"><i>入口</i></a></li>
        <li><a target="_blank" href="https://wn01.link/x"><i>本家</i></a></li></ul>
    """

    def get(url, **kwargs):
        if "publish" in url or url.endswith(".link") or "wn01" in url:
            # 発布ページ本体
            return FakeResponse(text=publish_html)
        if "good.test" in url:
            return FakeResponse(status_code=200)
        return FakeResponse(status_code=404)

    session = FakeSession(get_responses=get)
    client = HttpClient(session=session)
    # publish_page_url を発布ページ応答に向ける
    import app.crawler.http_client as mod
    saved = mod.settings.publish_page_url
    try:
        mod.settings.publish_page_url = "https://publish.test"
        url = client._resolve_from_publish_page()
    finally:
        mod.settings.publish_page_url = saved
    assert url == "https://good.test"


def test_login_resolves_base_url_when_missing(monkeypatch):
    """base_url 未設定なら get_available_url で解決してからログインする"""
    shelf = '<a href="users-users_fav-c-1.html">作者</a>'
    session = FakeSession(
        get_responses={"users-users_fav.html": FakeResponse(text=shelf)},
        post_response=FakeResponse(text="ok"),
    )
    client = HttpClient(session=session)
    monkeypatch.setattr(client, "get_available_url", lambda: BASE)
    assert client.login("user", "pwd") is True
    assert client.base_url == BASE
