"""HTTP クライアント基盤（requests + BeautifulSoup）

ドメイン解決・ログイン・ページ取得・文字コード判定・タイムアウト/リトライを担う軽量クライアント。
解析自体は app.crawler.parsers の純関数に委譲し、本クラスは「取得」に専念する。

設計方針:
- requests.Session を 1 つ保持し、Cookie を自動的に引き継ぐ（セッション維持）。
- ログイン仕様: POST /users-check_login.html（fields=normal/login_name/login_pass）。
- 取得は指数バックオフ付きリトライ・接続/読取タイムアウトを実装。
- テスト容易性のため session は注入可能（既定は新規 Session）。
"""
import threading
import time
from typing import Optional, Tuple

import requests
from bs4 import BeautifulSoup

from app.config import settings
from app.utils.logger import logger, get_error_message

# curl_cffi（Chrome の TLS/JA3 指紋を偽装）で Cloudflare のボット判定を回避する。
# 未導入環境では通常の requests に回退する（その場合 CF 保護下では 429/403 が増える）。
try:
    from curl_cffi import requests as curl_requests
    from curl_cffi.requests import RequestsError as _CurlRequestsError
    CURL_CFFI_AVAILABLE = True
    _CURL_EXCEPTIONS: Tuple[type, ...] = (_CurlRequestsError,)
except ImportError:  # pragma: no cover - 環境依存
    CURL_CFFI_AVAILABLE = False
    _CURL_EXCEPTIONS = ()

# リトライ対象とする一過性の例外（requests 系 + curl_cffi 系を横断的に扱う）
RETRYABLE_EXCEPTIONS: Tuple[type, ...] = (
    requests.ConnectionError, requests.Timeout, requests.HTTPError,
) + _CURL_EXCEPTIONS

# ネットワーク系例外の総称（requests でも curl_cffi でも捕捉できるようにする）
NETWORK_EXCEPTIONS: Tuple[type, ...] = (requests.RequestException,) + _CURL_EXCEPTIONS

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")


def build_impersonate_session(impersonate: Optional[str] = None):
    """サイト取得用セッションを生成する。

    curl_cffi が利用可能かつ impersonate 指定があれば Chrome 偽装セッションを返す
    （Cloudflare の TLS 指紋判定を回避）。無ければ通常の requests.Session に回退する。
    """
    if impersonate is None:
        impersonate = getattr(settings, "http_impersonate", "chrome")
    if CURL_CFFI_AVAILABLE and impersonate:
        try:
            return curl_requests.Session(impersonate=impersonate)
        except Exception as e:  # 偽装名が不正等 → requests に回退
            logger.warning(
                f"curl_cffi セッション生成に失敗（impersonate={impersonate!r}）: "
                f"{get_error_message(e)} → requests に回退")
    elif not CURL_CFFI_AVAILABLE and impersonate:
        logger.warning(
            "curl_cffi が未導入のため通常の requests で動作します"
            "（Cloudflare 保護下では 429/403 が発生しやすくなります）")
    return requests.Session()

# (接続タイムアウト, 読取タイムアウト) 秒
DEFAULT_TIMEOUT: Tuple[float, float] = (10.0, 30.0)
DEFAULT_MAX_RETRIES = 3
DEFAULT_BACKOFF = 0.5  # 指数バックオフ基準（秒）: 0.5, 1.0, 2.0, ...
# 429（Cloudflare のレート制限チャレンジ）は接続エラーより粘り強くリトライする。
# 実測では 429 の多くは数秒待てば解消するが、瞬間的な再試行では抜けられないため
# 専用の予算・待機下限を設ける（接続リトライの予算とは独立に消費する）。
DEFAULT_MAX_RETRIES_429 = 5
DEFAULT_MIN_WAIT_429 = 2.0  # 429 リトライ時の最小待機秒（CF の制限窓を跨ぐため）

def retry_after_seconds(resp, attempt: int, backoff: float) -> float:
    """429 応答の待機秒数を決める。Retry-After（秒数 or HTTP-date）を尊重し上限でクランプ。

    ヘッダが無い場合は指数バックオフ（backoff * 2^(attempt-1)）にフォールバックする。
    HttpClient と一発 GET ヘルパ（impersonated_get）の双方から共有する。
    """
    cap = getattr(settings, "retry_after_cap", 30.0)
    header = resp.headers.get("Retry-After")
    if header:
        header = header.strip()
        # 数値（秒）形式
        try:
            return max(0.0, min(float(header), cap))
        except ValueError:
            pass
        # HTTP-date 形式
        try:
            from email.utils import parsedate_to_datetime
            from datetime import datetime, timezone
            dt = parsedate_to_datetime(header)
            if dt is not None:
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                delta = (dt - datetime.now(timezone.utc)).total_seconds()
                return max(0.0, min(delta, cap))
        except (TypeError, ValueError):
            pass
    # フォールバック: 指数バックオフ（上限クランプ）
    return min(backoff * (2 ** (attempt - 1)), cap)


def impersonated_get(
    url: str,
    *,
    headers: Optional[dict] = None,
    timeout: Tuple[float, float] = DEFAULT_TIMEOUT,
    max_retries: int = DEFAULT_MAX_RETRIES,
    max_retries_429: int = DEFAULT_MAX_RETRIES_429,
    min_wait_429: float = DEFAULT_MIN_WAIT_429,
    backoff: float = DEFAULT_BACKOFF,
    impersonate: Optional[str] = None,
):
    """セッション不要の一発 Chrome 偽装 GET（429/一過性エラーをリトライ）。

    画像バイト取得（download_service）のように Cookie を要さず、スレッド独立で使いたい
    経路向け。curl_cffi の一発 API（内部でハンドルを都度生成）を使うためスレッドセーフ。
    curl_cffi 未導入時は requests へ回退する。戻り値は Response（`.content`/`.status_code`）。
    """
    if impersonate is None:
        impersonate = getattr(settings, "http_impersonate", "chrome")
    use_curl = CURL_CFFI_AVAILABLE and bool(impersonate)

    def _do_get():
        if use_curl:
            return curl_requests.get(
                url, headers=headers, timeout=timeout, impersonate=impersonate)
        return requests.get(url, headers=headers, timeout=timeout)

    last_exc: Optional[Exception] = None
    last_429 = None
    err_attempt = 0
    r429_attempt = 0
    while True:
        try:
            resp = _do_get()
            if resp.status_code == 429:
                last_429 = resp
                r429_attempt += 1
                if r429_attempt >= max_retries_429:
                    break
                wait = max(retry_after_seconds(resp, r429_attempt, backoff),
                           min_wait_429)
                logger.warning(
                    f"画像GET 429 レート制限（{r429_attempt}/{max_retries_429}）"
                    f"{url} → {wait:.1f}s 待機して再試行")
                time.sleep(wait)
                continue
            if resp.status_code >= 500:
                raise requests.HTTPError(
                    f"server error {resp.status_code}", response=resp)
            return resp
        except RETRYABLE_EXCEPTIONS as e:
            last_exc = e
            err_attempt += 1
            if err_attempt >= max_retries:
                break
            wait = backoff * (2 ** (err_attempt - 1))
            logger.warning(
                f"画像GET 失敗（{err_attempt}/{max_retries}）{url}: "
                f"{get_error_message(e)} → {wait:.1f}s 後に再試行")
            time.sleep(wait)
    if last_429 is not None and last_exc is None:
        logger.error(f"画像GET 429 継続（レート制限が解消せず）{url}")
        return last_429
    raise last_exc if last_exc else RuntimeError(f"GET failed: {url}")


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
        max_retries_429: int = DEFAULT_MAX_RETRIES_429,
        min_wait_429: float = DEFAULT_MIN_WAIT_429,
    ):
        self.base_url: Optional[str] = base_url.rstrip("/") if base_url else None
        # 明示注入が無ければ Chrome 偽装セッション（curl_cffi）を使う（CF 対策）。
        self.session = session or build_impersonate_session()
        # curl_cffi は impersonate 済みの UA を持つため上書きしない。requests のみ既定 UA を補う。
        if not CURL_CFFI_AVAILABLE or isinstance(self.session, requests.Session):
            try:
                self.session.headers.setdefault("User-Agent", UA)
            except Exception:
                pass
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff = backoff
        self.max_retries_429 = max_retries_429
        self.min_wait_429 = min_wait_429

        # 適応的バックプレッシャー（429 カスケード防止）。429 を観測するたびに
        # _adaptive_delay を増やし、全 GET の直前にその秒数だけ待つことで実効レートを下げる。
        # 成功が続けば徐々に 0 へ戻す。スレッド間で共有するためロックで保護する。
        self._adaptive_step = getattr(settings, "adaptive_backpressure_step", 0.75)
        self._adaptive_max = getattr(settings, "adaptive_backpressure_max", 8.0)
        self._adaptive_recover = getattr(settings, "adaptive_backpressure_recover", 0.15)
        self._adaptive_delay = 0.0
        self._adaptive_lock = threading.Lock()

    # ------------------------------------------------------------------
    # 取得（リトライ/タイムアウト/文字コード）
    # ------------------------------------------------------------------
    def get(self, url: str, **kwargs) -> requests.Response:
        """GET（指数バックオフ付きリトライ・接続/読取タイムアウト）

        接続・読取・5xx・429（レート制限）を一過性とみなしてリトライ。
        429 の場合は Retry-After ヘッダを尊重し（無ければ指数バックオフ）待機してから再試行する。
        最終的に失敗した場合は例外を送出（429 が続いた場合は最後の 429 レスポンスを返す）。
        """
        kwargs.setdefault("timeout", self.timeout)
        last_exc: Optional[Exception] = None
        last_429: Optional[requests.Response] = None
        err_attempt = 0    # 接続/読取/5xx のリトライ回数
        r429_attempt = 0   # 429 のリトライ回数（独立予算）
        while True:
            self._apply_backpressure()  # 429 が続いている間は全 GET を自動減速
            try:
                resp = self.session.get(url, **kwargs)
                if resp.status_code == 429:
                    # レート制限（多くは CF の「Just a moment...」チャレンジ）。
                    # 接続エラーとは別予算で、待機下限を設けて粘り強く再試行する。
                    last_429 = resp
                    r429_attempt += 1
                    self._penalize_backpressure()  # 全体を減速して CF 窓の回復を促す
                    if r429_attempt >= self.max_retries_429:
                        break
                    wait = max(self._retry_after_seconds(resp, r429_attempt),
                               self.min_wait_429)
                    logger.warning(
                        f"GET 429 レート制限（{r429_attempt}/{self.max_retries_429}）"
                        f"{url} → {wait:.1f}s 待機して再試行")
                    time.sleep(wait)
                    continue
                if resp.status_code >= 500:
                    raise requests.HTTPError(
                        f"server error {resp.status_code}", response=resp)
                self._recover_backpressure()  # 成功時は追加遅延を徐々に戻す
                return resp
            except RETRYABLE_EXCEPTIONS as e:
                last_exc = e
                err_attempt += 1
                if err_attempt >= self.max_retries:
                    break
                wait = self.backoff * (2 ** (err_attempt - 1))
                logger.warning(
                    f"GET 失敗（{err_attempt}/{self.max_retries}）{url}: "
                    f"{get_error_message(e)} → {wait:.1f}s 後に再試行")
                time.sleep(wait)
        # 429 が最後まで解消しなかった場合は、例外ではなく 429 レスポンスを返す
        # （呼び出し側の診断ログで status/内容を出せるようにするため）
        if last_429 is not None and last_exc is None:
            logger.error(f"GET 429 継続（レート制限が解消せず）{url}")
            return last_429
        logger.error(f"GET 最終失敗 {url}: "
                     f"{get_error_message(last_exc) if last_exc else 'unknown'}")
        raise last_exc if last_exc else RuntimeError(f"GET failed: {url}")

    # ------------------------------------------------------------------
    # 適応的バックプレッシャー（429 カスケード防止）
    # ------------------------------------------------------------------
    def _apply_backpressure(self) -> None:
        """現在の追加遅延だけ待機する（429 未観測時は 0 なので何もしない）。"""
        with self._adaptive_lock:
            delay = self._adaptive_delay
        if delay > 0:
            time.sleep(delay)

    def _penalize_backpressure(self) -> None:
        """429 観測時に追加遅延を増やす（上限 _adaptive_max でクランプ）。"""
        if self._adaptive_step <= 0:
            return
        with self._adaptive_lock:
            self._adaptive_delay = min(
                self._adaptive_delay + self._adaptive_step, self._adaptive_max)
            new_delay = self._adaptive_delay
        logger.info(f"適応的バックプレッシャー: 追加遅延を {new_delay:.2f}s に引き上げ")

    def _recover_backpressure(self) -> None:
        """成功時に追加遅延を徐々に戻す（0 まで減衰）。"""
        if self._adaptive_recover <= 0:
            return
        with self._adaptive_lock:
            if self._adaptive_delay <= 0:
                return
            self._adaptive_delay = max(
                0.0, self._adaptive_delay - self._adaptive_recover)

    def _retry_after_seconds(self, resp, attempt: int) -> float:
        """429 応答の待機秒数を決める（module 関数 retry_after_seconds へ委譲）。"""
        return retry_after_seconds(resp, attempt, self.backoff)

    def get_page(self, url: str, **kwargs) -> requests.Response:
        """GET してエンコーディングを補正した Response を返す（診断用に status 等へアクセス可）"""
        resp = self.get(url, **kwargs)
        # サーバが charset を返さない場合があるため補正（R4）。curl_cffi は apparent_encoding を
        # 持たないため getattr で回退し、encoding が read-only な実装でも壊さないよう try で包む。
        enc = getattr(resp, "encoding", None)
        if not enc or str(enc).lower() == "iso-8859-1":
            fallback = getattr(resp, "apparent_encoding", None) or "utf-8"
            try:
                resp.encoding = fallback
            except (AttributeError, TypeError):
                pass
        return resp

    def get_html(self, url: str, **kwargs) -> str:
        """GET してエンコーディングを補正した HTML 文字列を返す（parsers 入力用）"""
        return self.get_page(url, **kwargs).text

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
                except NETWORK_EXCEPTIONS:
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
        except NETWORK_EXCEPTIONS as e:
            logger.error(f"登录请求失败: {get_error_message(e)}")
            return False

        # 書架ページに到達できればログイン成立（R1/R6）
        try:
            verify = self.get_page(f"{base}{SHELF_PATH}")
            body = verify.text
        except NETWORK_EXCEPTIONS as e:
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
