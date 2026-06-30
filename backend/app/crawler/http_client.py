"""HTTP クライアント基盤（requests + BeautifulSoup）

ドメイン解決・ログイン・ページ取得・文字コード判定・タイムアウト/リトライを担う軽量クライアント。
解析自体は app.crawler.parsers の純関数に委譲し、本クラスは「取得」に専念する。

設計方針:
- requests.Session を 1 つ保持し、Cookie を自動的に引き継ぐ（セッション維持）。
- ログイン仕様: POST /users-check_login.html（fields=normal/login_name/login_pass）。
- 取得は指数バックオフ付きリトライ・接続/読取タイムアウトを実装。
- テスト容易性のため session は注入可能（既定は新規 Session）。
"""
import time
from typing import Optional, Tuple

import requests
from bs4 import BeautifulSoup

from app.config import settings
from app.utils.logger import logger, get_error_message

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

# (接続タイムアウト, 読取タイムアウト) 秒
DEFAULT_TIMEOUT: Tuple[float, float] = (10.0, 30.0)
DEFAULT_MAX_RETRIES = 3
DEFAULT_BACKOFF = 0.5  # 指数バックオフ基準（秒）: 0.5, 1.0, 2.0, ...

# ログイン仕様（フェーズ0 PoC / capture_golden.py で実証済み）
LOGIN_PATH = "/users-check_login.html"
LOGIN_FORM_PATH = "/users-login.html"
# ログイン済みマーカーが現れる検証用ページ（書架）
SHELF_PATH = "/users-users_fav.html"
SHELF_MARKER = "users-users_fav-c-"


class HttpClient:
    """requests ベースの取得クライアント"""

    def __init__(
        self,
        base_url: Optional[str] = None,
        session: Optional[requests.Session] = None,
        timeout: Tuple[float, float] = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
        backoff: float = DEFAULT_BACKOFF,
    ):
        self.base_url: Optional[str] = base_url.rstrip("/") if base_url else None
        self.session = session or requests.Session()
        self.session.headers.setdefault("User-Agent", UA)
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff = backoff

    # ------------------------------------------------------------------
    # 取得（リトライ/タイムアウト/文字コード）
    # ------------------------------------------------------------------
    def get(self, url: str, **kwargs) -> requests.Response:
        """GET（指数バックオフ付きリトライ・接続/読取タイムアウト）

        接続・読取・5xx を一過性とみなしてリトライ。最終的に失敗した場合は例外を送出。
        """
        kwargs.setdefault("timeout", self.timeout)
        last_exc: Optional[Exception] = None
        for attempt in range(1, self.max_retries + 1):
            try:
                resp = self.session.get(url, **kwargs)
                if resp.status_code >= 500:
                    raise requests.HTTPError(
                        f"server error {resp.status_code}", response=resp)
                return resp
            except (requests.ConnectionError, requests.Timeout,
                    requests.HTTPError) as e:
                last_exc = e
                if attempt >= self.max_retries:
                    break
                wait = self.backoff * (2 ** (attempt - 1))
                logger.warning(
                    f"GET 失敗（{attempt}/{self.max_retries}）{url}: "
                    f"{get_error_message(e)} → {wait:.1f}s 後に再試行")
                time.sleep(wait)
        logger.error(f"GET 最終失敗 {url}: "
                     f"{get_error_message(last_exc) if last_exc else 'unknown'}")
        raise last_exc if last_exc else RuntimeError(f"GET failed: {url}")

    def get_html(self, url: str, **kwargs) -> str:
        """GET してエンコーディングを補正した HTML 文字列を返す（parsers 入力用）"""
        resp = self.get(url, **kwargs)
        # サーバが charset を返さない場合があるため apparent_encoding で補正（R4）
        if not resp.encoding or resp.encoding.lower() == "iso-8859-1":
            resp.encoding = resp.apparent_encoding or "utf-8"
        return resp.text

    def get_soup(self, url: str, **kwargs) -> BeautifulSoup:
        """GET してエンコーディングを補正し BeautifulSoup を返す"""
        return BeautifulSoup(self.get_html(url, **kwargs), "html.parser")

    def post(self, url: str, **kwargs) -> requests.Response:
        """POST（単発・タイムアウト付き）。冪等性が無いため自動リトライはしない"""
        kwargs.setdefault("timeout", self.timeout)
        return self.session.post(url, **kwargs)

    # ------------------------------------------------------------------
    # ドメイン解決
    # ------------------------------------------------------------------
    def get_manual_url(self) -> Optional[str]:
        """DB に手動設定された漫画サイト URL を取得（best-effort）"""
        try:
            from app.database import SessionLocal
            from app.models import AppConfig
            db = SessionLocal()
            try:
                config = db.query(AppConfig).filter(
                    AppConfig.id == "singleton").first()
                if config and config.manual_manga_site_url:
                    logger.info(
                        f"使用手动设置的漫画网站链接: {config.manual_manga_site_url}")
                    return config.manual_manga_site_url
            finally:
                db.close()
        except Exception as e:
            logger.debug(f"获取手动设置的链接失败: {get_error_message(e)}")
        return None

    def get_available_url(self) -> Optional[str]:
        """利用可能な base_url を取得（手動設定優先、無ければ発布ページ解決）"""
        manual_url = self.get_manual_url()
        if manual_url:
            return manual_url.rstrip("/")
        logger.info("未找到手动设置的链接，从发布页获取...")
        return self._resolve_from_publish_page()

    def _resolve_from_publish_page(self) -> Optional[str]:
        """発布ページから疎通可能な漫画サイト URL を解決"""
        try:
            resp = self.session.get(settings.publish_page_url, timeout=self.timeout)
            resp.encoding = "utf-8"
            soup = BeautifulSoup(resp.text, "html.parser")
            urls = self._extract_candidate_urls(soup)
            for url in urls:
                try:
                    test = self.session.get(f"{url}/", timeout=self.timeout)
                    if test.status_code == 200:
                        logger.info(f"找到可用的漫画网站地址: {url}")
                        return url.rstrip("/")
                except requests.RequestException:
                    continue
            logger.warning("未找到可用的漫画网站地址")
            return None
        except Exception as e:
            logger.error(f"获取网站地址失败: {get_error_message(e)}")
            return None

    @staticmethod
    def _extract_candidate_urls(soup: BeautifulSoup) -> list:
        """発布ページのレイアウトから候補 URL を抽出"""
        urls: list = []
        ul_lists = soup.find_all("ul")
        for ul in ul_lists:
            for li in ul.find_all("li"):
                for link in li.find_all("a", {"target": "_blank"}, href=True):
                    href = link.get("href", "")
                    if "wn01.link" in href or "google.cn" in href:
                        continue
                    if link.find("i") and href.startswith("http"):
                        urls.append(href)
        # 備用: target 属性に依らず li 内の http リンクを拾う
        if not urls:
            for ul in ul_lists:
                for li in ul.find_all("li"):
                    for link in li.find_all("a", href=True):
                        href = link.get("href", "")
                        if "wn01.link" in href or "google.cn" in href:
                            continue
                        if href.startswith("http"):
                            urls.append(href)
        return urls

    # ------------------------------------------------------------------
    # ログイン
    # ------------------------------------------------------------------
    def login(self, username: str, password: str) -> bool:
        """ログイン。成功時 True（Cookie は self.session に保持される）"""
        if not self.base_url:
            self.base_url = self.get_available_url()
            if not self.base_url:
                logger.error("无法获取漫画网站地址（手动设置或发布页都失败）")
                return False

        base = self.base_url
        try:
            self.session.post(
                f"{base}{LOGIN_PATH}",
                data={"normal": "1", "login_name": username, "login_pass": password},
                timeout=self.timeout,
                headers={"Referer": f"{base}{LOGIN_FORM_PATH}"},
            )
        except requests.RequestException as e:
            logger.error(f"登录请求失败: {get_error_message(e)}")
            return False

        # 書架ページに到達できればログイン成立（R1/R6）
        try:
            verify = self.get(f"{base}{SHELF_PATH}")
            if not verify.encoding or verify.encoding.lower() == "iso-8859-1":
                verify.encoding = verify.apparent_encoding or "utf-8"
            body = verify.text
        except requests.RequestException as e:
            logger.error(f"登录校验请求失败: {get_error_message(e)}")
            return False

        logged_in = (SHELF_MARKER in body) or (username in body)
        if logged_in:
            logger.info("登录成功，会话已建立")
        else:
            logger.warning("登录失败，未到达书架页面")
        return logged_in

    def close(self):
        """セッションを閉じる"""
        self.session.close()
