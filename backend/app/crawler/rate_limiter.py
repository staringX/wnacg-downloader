"""リクエストのレート制限（サイト負荷への配慮）

スレッド間で共有する「最小間隔」ベースのレート制限。並行数（ThreadPool）に関係なく、
リクエストの開始を min_interval 秒ずつ間引くことで、実効レートを 1/min_interval [req/s] に
頭打ちにする。並行はレイテンシ隠蔽のためだけに働く。

**漫画ダウンロード時のみ**適用する（収藏夹同期・検索などのスキャン動作は軽量なため非適用）:
- site_limiter : DL 時の view ページ取得（get_manga_images）に適用。
- image_limiter: DL 時の画像バイナリ取得（download_service.download_image, CDN）に適用。

間隔は設定（REQUEST_MIN_INTERVAL / IMAGE_REQUEST_MIN_INTERVAL、秒）で可変。0 で無制限。
"""
import threading
import time

from app.config import settings


class RateLimiter:
    """スレッドセーフな最小間隔レート制限器"""

    def __init__(self, min_interval: float):
        self.min_interval = max(0.0, float(min_interval))
        self._lock = threading.Lock()
        self._next_allowed = 0.0  # monotonic 時刻

    def acquire(self) -> None:
        """次のスロットまで待機する（必要な分だけ sleep）"""
        if self.min_interval <= 0:
            return
        with self._lock:
            now = time.monotonic()
            # 自分のスロットを確保（ロック内は計算のみ。sleep はロック外で行う）
            slot = max(now, self._next_allowed)
            self._next_allowed = slot + self.min_interval
            wait = slot - now
        if wait > 0:
            time.sleep(wait)

    def set_min_interval(self, min_interval: float) -> None:
        """間隔を動的に変更（テスト/設定反映用）"""
        with self._lock:
            self.min_interval = max(0.0, float(min_interval))


# プロセス共有のシングルトン（並行ダウンロード間でもレートを共有する）
site_limiter = RateLimiter(settings.request_min_interval)
image_limiter = RateLimiter(settings.image_request_min_interval)
