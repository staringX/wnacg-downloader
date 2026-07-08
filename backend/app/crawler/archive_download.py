"""一括ダウンロード（ZIP アーカイブ）モジュール

2026-07 のサイト改版で詳細ページに「下載漫畫」ボタン（/download-index-aid-{aid}.html）が
追加された。ダウンロードページには複数の線路（Server 1: WORKER_API 経由の署名付き URL、
Server 2+: .zip 直接リンク）があり、失敗した線路は順次スキップして次を試す。

線路の抽出は parsers.parse_download_routes（純関数）に委譲し、本モジュールは
「線路の解決」と「ZIP のストリーミング取得・検証」に専念する。

ZIP 配信ホスト（WORKER_API / CDN）は Cloudflare の TLS 指紋判定で通常の requests を
403 で弾くため（実測）、取得には curl_cffi（Chrome 偽装）セッションを使う。
サイト本体へのアクセスは従来どおり HttpClient（requests）。
"""
import re
import zipfile
from pathlib import Path
from typing import Callable, Dict, List, Optional

from app.crawler import parsers
from app.crawler.rate_limiter import site_limiter, image_limiter
from app.utils.logger import logger, get_error_message

try:
    from curl_cffi import requests as curl_requests
    CURL_CFFI_AVAILABLE = True
except ImportError:  # 未導入環境では requests で代替（CF 保護線路は通らない可能性）
    CURL_CFFI_AVAILABLE = False

# ZIP 内で「画像」とみなす拡張子（CBZ 化対象の判定にも使う）
IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".avif")

# ストリーミング書き込みのチャンクサイズ
CHUNK_SIZE = 1024 * 1024  # 1MB

# ZIP バイナリ取得のタイムアウト（接続, 読取）秒
DOWNLOAD_TIMEOUT = (10.0, 60.0)

_AID_RE = re.compile(r"photos-index-aid-(\d+)")


def zip_image_names(zip_path) -> List[str]:
    """ZIP 内の画像エントリ名を名前順で返す（不正 ZIP は空リスト）"""
    try:
        if not zipfile.is_zipfile(zip_path):
            return []
        with zipfile.ZipFile(zip_path) as zf:
            return sorted(
                n for n in zf.namelist()
                if not n.endswith("/") and n.lower().endswith(IMAGE_EXTS)
            )
    except (OSError, zipfile.BadZipFile):
        return []


class ArchiveDownloadCrawler:
    """一括ダウンロード爬取器（線路フォールバック付き）"""

    def __init__(self, client, download_session=None):
        self.client = client
        # ZIP 取得用セッション（テストでは fake を注入可能）
        self._dl_session = download_session

    @property
    def base_url(self):
        return self.client.base_url

    def _download_session(self):
        """ZIP 配信ホスト用セッション（Cloudflare TLS 指紋対策）"""
        if self._dl_session is None:
            if CURL_CFFI_AVAILABLE:
                self._dl_session = curl_requests.Session(impersonate="chrome")
            else:
                logger.warning(
                    "curl_cffi が未導入のため requests で代替します"
                    "（Cloudflare 保護線路は 403 になる可能性）")
                self._dl_session = self.client.session
        return self._dl_session

    def get_download_routes(self, manga_url: str) -> List[Dict]:
        """詳細 URL からダウンロードページを解決し、線路リストを返す

        線路が取得できない（改版・404・ボタン未対応の作品）場合は [] を返し、
        呼び出し側は従来の 1 ページずつ方式へフォールバックする。
        """
        m = _AID_RE.search(manga_url or "")
        if not m:
            logger.warning(f"下載頁 URL を導出できません（aid 不明）: {manga_url}")
            return []
        base = (self.base_url or parsers._origin(manga_url)).rstrip("/")
        download_url = f"{base}/download-index-aid-{m.group(1)}.html"
        try:
            site_limiter.acquire()  # ダウンロード時のサイト負荷配慮
            html = self.client.get_html(download_url)
        except Exception as e:
            logger.warning(f"下載頁の取得に失敗: {download_url}: {get_error_message(e)}")
            return []
        routes = parsers.parse_download_routes(html, base)
        logger.info(f"下載線路を {len(routes)} 件検出: {download_url}")
        return routes

    def download_archive(
        self,
        routes: List[Dict],
        dest_path: Path,
        progress_cb: Optional[Callable[[int, int], None]] = None,
    ) -> bool:
        """線路を順に試して ZIP を dest_path へ取得する

        成功判定: HTTP 200 かつ ZIP マジック（PK）で始まり、完走後に
        zipfile として開けて画像エントリが 1 件以上あること。
        いずれかの線路で成功したら True、全滅なら False。
        """
        dest_path = Path(dest_path)
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        total = len(routes)
        for idx, route in enumerate(routes, 1):
            label = f"線路 {idx}/{total} ({route.get('type')})"
            try:
                url = self._resolve_route_url(route)
                if not url:
                    logger.warning(f"{label} ✗ ダウンロード URL を解決できず")
                    continue
                logger.info(f"{label} ZIP 取得開始")
                if self._stream_to_file(url, dest_path, progress_cb):
                    if zip_image_names(dest_path):
                        logger.info(f"{label} ✓ ZIP 取得成功: {dest_path}")
                        return True
                    logger.warning(f"{label} ✗ ZIP 検証失敗（画像エントリ無し/破損）")
            except Exception as e:
                logger.warning(f"{label} ✗ 失敗: {get_error_message(e)}")
            finally:
                # 失敗した中途ファイルは残さない（成功時は上で return 済み）
                if dest_path.exists() and not zip_image_names(dest_path):
                    dest_path.unlink(missing_ok=True)
        logger.warning("✗ 全ての下載線路が失敗しました")
        return False

    def close(self):
        """ZIP 取得用セッションを閉じる（client 本体は HttpClient 側で閉じる）"""
        if self._dl_session is not None and self._dl_session is not getattr(
                self.client, "session", None):
            try:
                self._dl_session.close()
            except Exception:
                pass
            self._dl_session = None

    def _resolve_route_url(self, route: Dict) -> Optional[str]:
        """線路からダウンロード URL を解決（api 線路は WORKER_API に POST）"""
        if route.get("type") == "direct":
            return route.get("url")
        if route.get("type") == "api":
            resp = self._download_session().post(
                route["worker_api"],
                json={
                    "file_key": route.get("file_key", ""),
                    "file_name": route.get("file_name", ""),
                },
                headers={"Referer": f"{(self.base_url or '').rstrip('/')}/"},
                timeout=DOWNLOAD_TIMEOUT,
            )
            if resp.status_code != 200:
                logger.warning(f"WORKER_API が HTTP {resp.status_code} を返却")
                return None
            data = resp.json()
            if data.get("success") and data.get("url"):
                return data["url"]
            logger.warning(f"WORKER_API 応答が不正: {str(data)[:200]}")
            return None
        logger.warning(f"未知の線路タイプ: {route.get('type')}")
        return None

    def _stream_to_file(
        self,
        url: str,
        dest_path: Path,
        progress_cb: Optional[Callable[[int, int], None]] = None,
    ) -> bool:
        """URL から ZIP をストリーミング取得して dest_path に保存"""
        image_limiter.acquire()  # CDN 負荷配慮（単発 GET だが規約として通す）
        resp = self._download_session().get(
            url, stream=True, timeout=DOWNLOAD_TIMEOUT,
            headers={"Referer": f"{(self.base_url or '').rstrip('/')}/"},
        )
        try:
            if resp.status_code != 200:
                logger.warning(f"ZIP 取得 HTTP {resp.status_code}: {url}")
                return False
            total_bytes = int(resp.headers.get("content-length") or 0)
            downloaded = 0
            first = True
            with open(dest_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=CHUNK_SIZE):
                    if not chunk:
                        continue
                    if first:
                        # HTML エラーページ等を掴まされた場合を早期に弾く
                        if not chunk.startswith(b"PK"):
                            ctype = resp.headers.get("content-type", "")
                            logger.warning(
                                f"応答が ZIP ではありません（content-type={ctype}）: {url}")
                            return False
                        first = False
                    f.write(chunk)
                    downloaded += len(chunk)
                    if progress_cb:
                        progress_cb(downloaded, total_bytes)
            if first:
                logger.warning(f"応答が空でした: {url}")
                return False
            if total_bytes and downloaded < total_bytes:
                logger.warning(
                    f"ZIP が途中で切断されました（{downloaded}/{total_bytes} bytes）: {url}")
                return False
            return True
        finally:
            try:
                resp.close()
            except Exception:
                pass
