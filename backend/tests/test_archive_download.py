"""一括ダウンロード（ZIP 直取得）のユニットテスト

対象:
- ArchiveDownloadCrawler: 線路の解決・フォールバック・ZIP 検証（requests はモック）
- MangaDownloader.convert_zip_to_cbz: ZIP → CBZ 変換（ComicInfo.xml 追記・封面抽出）

ネットワークには一切アクセスしない。
"""
import io
import json
import zipfile
from pathlib import Path

import pytest

from app.crawler.archive_download import ArchiveDownloadCrawler, zip_image_names
from app.services.download_service import MangaDownloader


# ---------------------------------------------------------------------------
# フェイク（requests モック）
# ---------------------------------------------------------------------------
class FakeResponse:
    def __init__(self, status_code=200, content=b"", headers=None, json_data=None):
        self.status_code = status_code
        self._content = content
        self.headers = headers or {}
        self._json = json_data

    def json(self):
        if self._json is None:
            raise ValueError("no json")
        return self._json

    def iter_content(self, chunk_size=1024):
        for i in range(0, len(self._content), chunk_size):
            yield self._content[i:i + chunk_size]

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class FakeDownloadSession:
    """URL → FakeResponse / Exception のマッピングで応答する（curl_cffi の代役）"""

    def __init__(self, get_responses=None, post_responses=None):
        self._get = get_responses or {}
        self._post = post_responses or {}
        self.requested = []

    def get(self, url, **kwargs):
        self.requested.append(url)
        resp = self._get.get(url)
        if resp is None:
            raise ConnectionError(f"unexpected url: {url}")
        if isinstance(resp, Exception):
            raise resp
        return resp

    def post(self, url, **kwargs):
        resp = self._post.get(url)
        if resp is None:
            raise ConnectionError(f"unexpected post: {url}")
        if isinstance(resp, Exception):
            raise resp
        return resp

    def close(self):
        pass


class FakeClient:
    def __init__(self, htmls=None):
        self.base_url = "https://example.test"
        self._htmls = htmls or {}

    def get_html(self, url, **kwargs):
        if url not in self._htmls:
            raise ConnectionError(f"unexpected url: {url}")
        return self._htmls[url]


def _crawler(get_responses=None, post_responses=None, htmls=None):
    return ArchiveDownloadCrawler(
        FakeClient(htmls=htmls),
        download_session=FakeDownloadSession(get_responses, post_responses))


def _make_zip_bytes(num_images=3):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for i in range(1, num_images + 1):
            zf.writestr(f"{i:03d}.jpg", b"\xff\xd8\xff" + bytes([i]) * 10)
    return buf.getvalue()


ZIP_BYTES = _make_zip_bytes()


# ---------------------------------------------------------------------------
# get_download_routes
# ---------------------------------------------------------------------------
DOWNLOAD_PAGE_HTML = """
<html><body>
<button onclick="directDownload()">點擊下載 (Server 1)</button>
<a class="ads" href="//dl1.backup.example/down/1/abc.zip?n=t">備用線路 (Server 2)</a>
<script>
const CONFIG = {
    WORKER_API: "https://worker.example/api/generate-link",
    FILE_KEY: "down/1/abc.zip",
    FILE_NAME: "t.zip"
};
</script>
</body></html>
"""


def test_get_download_routes_resolves_aid_and_parses():
    crawler = _crawler(htmls={
        "https://example.test/download-index-aid-12345.html": DOWNLOAD_PAGE_HTML,
    })
    routes = crawler.get_download_routes(
        "https://example.test/photos-index-aid-12345.html")
    assert [r["type"] for r in routes] == ["api", "direct"]
    assert routes[0]["worker_api"] == "https://worker.example/api/generate-link"
    assert routes[1]["url"].startswith("https://dl1.backup.example/")


def test_get_download_routes_returns_empty_on_fetch_error():
    assert _crawler().get_download_routes(
        "https://example.test/photos-index-aid-99.html") == []


def test_get_download_routes_returns_empty_without_aid():
    assert _crawler().get_download_routes("https://example.test/unknown.html") == []


# ---------------------------------------------------------------------------
# download_archive（線路フォールバック）
# ---------------------------------------------------------------------------
API_ROUTE = {"type": "api", "worker_api": "https://worker.example/api",
             "file_key": "down/1/abc.zip", "file_name": "t.zip"}
DIRECT_ROUTE = {"type": "direct", "url": "https://dl1.backup.example/abc.zip"}


def test_download_archive_api_route_success(tmp_path):
    signed = "https://cdn.example/signed.zip"
    crawler = _crawler(
        post_responses={"https://worker.example/api": FakeResponse(
            json_data={"success": True, "url": signed})},
        get_responses={signed: FakeResponse(
            content=ZIP_BYTES,
            headers={"content-length": str(len(ZIP_BYTES)),
                     "content-type": "application/zip"})},
    )
    dest = tmp_path / "out.zip.part"
    progress = []
    ok = crawler.download_archive(
        [API_ROUTE, DIRECT_ROUTE], dest,
        progress_cb=lambda done, total: progress.append((done, total)))
    assert ok
    assert zip_image_names(dest) == ["001.jpg", "002.jpg", "003.jpg"]
    assert progress and progress[-1] == (len(ZIP_BYTES), len(ZIP_BYTES))
    # 線路 1 で成功したため備用線路は呼ばれない
    assert crawler._dl_session.requested == [signed]


def test_download_archive_falls_back_to_direct_route(tmp_path):
    """api 線路が接続エラー → direct 線路で成功"""
    crawler = _crawler(
        post_responses={"https://worker.example/api": ConnectionError("dns fail")},
        get_responses={DIRECT_ROUTE["url"]: FakeResponse(content=ZIP_BYTES)},
    )
    dest = tmp_path / "out.zip.part"
    assert crawler.download_archive([API_ROUTE, DIRECT_ROUTE], dest)
    assert zip_image_names(dest)


def test_download_archive_rejects_non_zip_response(tmp_path):
    """HTML エラーページ（PK で始まらない）は失敗扱い → 次線路へ"""
    crawler = _crawler(
        post_responses={"https://worker.example/api": FakeResponse(
            json_data={"success": True, "url": "https://cdn.example/err"})},
        get_responses={
            "https://cdn.example/err": FakeResponse(
                content=b"<html>error</html>",
                headers={"content-type": "text/html"}),
            DIRECT_ROUTE["url"]: FakeResponse(content=ZIP_BYTES),
        },
    )
    dest = tmp_path / "out.zip.part"
    assert crawler.download_archive([API_ROUTE, DIRECT_ROUTE], dest)
    assert zip_image_names(dest)


def test_download_archive_rejects_truncated_zip(tmp_path):
    """content-length より短い（途中切断）ZIP は失敗扱い"""
    crawler = _crawler(get_responses={DIRECT_ROUTE["url"]: FakeResponse(
        content=ZIP_BYTES[:100],
        headers={"content-length": str(len(ZIP_BYTES))})})
    dest = tmp_path / "out.zip.part"
    assert not crawler.download_archive([DIRECT_ROUTE], dest)
    assert not dest.exists()  # 中途ファイルは残さない


def test_download_archive_all_routes_fail(tmp_path):
    crawler = _crawler(
        post_responses={"https://worker.example/api": FakeResponse(
            json_data={"success": False, "msg": "quota"})},
        get_responses={DIRECT_ROUTE["url"]: ConnectionError("refused")},
    )
    dest = tmp_path / "out.zip.part"
    assert not crawler.download_archive([API_ROUTE, DIRECT_ROUTE], dest)
    assert not dest.exists()


# ---------------------------------------------------------------------------
# convert_zip_to_cbz
# ---------------------------------------------------------------------------
@pytest.fixture
def downloader(tmp_path):
    d = MangaDownloader()
    d.download_dir = tmp_path / "downloads"
    d.cover_dir = tmp_path / "covers"
    d.download_dir.mkdir()
    d.cover_dir.mkdir()
    return d


def test_convert_zip_to_cbz(downloader, tmp_path):
    zip_path = tmp_path / "work.zip.part"
    zip_path.write_bytes(ZIP_BYTES)

    result = downloader.convert_zip_to_cbz(
        zip_path, "Test Manga", author="作者A",
        manga_metadata={"tags": ["中文翻譯"], "uploader": "up",
                        "category": "同人誌／漢化",
                        "manga_url": "https://example.test/photos-index-aid-1.html"})
    assert result is not None
    cbz = Path(result["cbz_path"])
    assert cbz.exists() and cbz.suffix == ".cbz"
    assert cbz.parent.name == "作者A"  # downloads/{作者}/{标题}.cbz
    assert result["page_count"] == 3
    assert result["file_size"] == cbz.stat().st_size
    assert not zip_path.exists()  # 原 ZIP は改名済み

    with zipfile.ZipFile(cbz) as zf:
        names = zf.namelist()
        assert "ComicInfo.xml" in names
        xml = zf.read("ComicInfo.xml").decode("utf-8")
        assert "Test Manga" in xml
        assert "作者A" in xml
        # 画像はそのまま保持
        assert "001.jpg" in names

    # 封面は先頭画像から抽出
    cover = Path(result["cover_path"])
    assert cover.exists()
    assert cover.read_bytes() == zipfile.ZipFile(cbz).read("001.jpg")


def test_convert_zip_to_cbz_rejects_zip_without_images(downloader, tmp_path):
    zip_path = tmp_path / "bad.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("readme.txt", "no images")
    assert downloader.convert_zip_to_cbz(zip_path, "t", author="a") is None


def test_convert_zip_to_cbz_rejects_broken_file(downloader, tmp_path):
    broken = tmp_path / "broken.zip"
    broken.write_bytes(b"not a zip at all")
    assert downloader.convert_zip_to_cbz(broken, "t", author="a") is None


def test_zip_image_names_sorted_and_filtered(tmp_path):
    p = tmp_path / "mix.zip"
    with zipfile.ZipFile(p, "w") as zf:
        zf.writestr("002.png", b"b")
        zf.writestr("001.jpg", b"a")
        zf.writestr("ComicInfo.xml", "<x/>")
    assert zip_image_names(p) == ["001.jpg", "002.png"]
