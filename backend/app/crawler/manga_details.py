"""漫画详情・原図取得モジュール（requests + BeautifulSoup）

get_manga_details / get_manga_images を HttpClient + parsers で提供する。
parsers.parse_details は updated_at を 'YYYY-MM-DD' 文字列で返すため、
戻り値では datetime オブジェクトに変換する（DB 列・呼び出し側の契約に合わせる）。
原図取得は view ページを ThreadPool で並行 GET する。
"""
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Dict, List, Optional

from app.config import settings
from app.crawler import parsers
from app.crawler.rate_limiter import site_limiter
from app.utils.logger import logger, get_error_message


class MangaDetailsCrawler:
    """漫画详情爬取器（requests 版）"""

    def __init__(self, client):
        self.client = client

    @property
    def base_url(self):
        return self.client.base_url

    def get_manga_details(self, manga_url: str) -> Optional[Dict]:
        """漫画詳情を取得（页数・更新日・封面・分类・标签 等）

        戻り値の updated_at は datetime（または None）。
        """
        try:
            base = (self.base_url or "").rstrip("/")
            html = self.client.get_html(manga_url)
            data = parsers.parse_details(html, manga_url=manga_url, base=base)

            # parsers は updated_at を 'YYYY-MM-DD' 文字列で返す → datetime へ変換
            data["updated_at"] = _to_datetime(data.get("updated_at"))
            return data
        except Exception as e:
            logger.error(f"获取漫画详情失败: {get_error_message(e)}")
            return None

    def get_manga_images(self, manga_url: str) -> List[Dict]:
        """漫画の全画像 URL を表示順で取得（requests + ThreadPool・フェーズ3）

        手順:
        1. 詳細ページの全ページを辿り view リンク（photos-view-id-*）を表示順・重複排除で収集。
        2. 各 view ページを並行 GET し、原図 URL（/data/ 直下・非 /t/）を抽出。
        3. index 昇順で整列して返す。

        戻り値: [{'index', 'url', 'filename'}]。
        view ページは非ログインでも取得可能（フェーズ0 で実証）。
        """
        try:
            base = (self.base_url or "").rstrip("/")
            logger.info(f"开始获取漫画图片: {manga_url}")
            view_urls = self._collect_view_links(manga_url, base)
            logger.info(f"共收集到 {len(view_urls)} 个图片链接")
            if not view_urls:
                logger.warning("✗ 没有找到任何图片链接")
                return []

            thread_count = max(1, settings.image_fetch_threads)
            logger.info(
                f"开始使用 {thread_count} 个线程并发获取 {len(view_urls)} 个原图链接...")

            results: Dict[int, Dict] = {}
            with ThreadPoolExecutor(max_workers=thread_count) as executor:
                future_map = {
                    executor.submit(self._fetch_original, idx, url): idx
                    for idx, url in enumerate(view_urls, 1)
                }
                for future in as_completed(future_map):
                    try:
                        item = future.result()
                        if item:
                            results[item["index"]] = item
                    except Exception as e:
                        logger.error(f"获取原图任务异常: {get_error_message(e)}")

            images = [results[i] for i in sorted(results)]
            logger.info(f"✓ 成功获取 {len(images)}/{len(view_urls)} 张原图")
            return images
        except Exception as e:
            logger.error(f"获取漫画图片失败: {get_error_message(e)}")
            return []

    def _collect_view_links(self, manga_url: str, base: str) -> List[str]:
        """詳細ページの全分页から view リンクを表示順・重複排除で収集"""
        view_urls: List[str] = []
        seen = set()
        current_url = manga_url
        visited = set()
        page_num = 1

        # ページ数に固定上限は設けない（3000P 超の作品もあるため）。
        # 訪問済み URL 集合 + 「次ページリンクが無くなったら終了」で必ず有限停止する。
        while current_url and current_url not in visited:
            visited.add(current_url)
            logger.info(f"  扫描第 {page_num} 页: {current_url}")
            try:
                site_limiter.acquire()  # ダウンロード時のサイト負荷配慮（最小間隔）
                html = self.client.get_html(current_url)
            except Exception as e:
                logger.warning(f"    页面获取失败: {get_error_message(e)}")
                break

            links = parsers.parse_view_links(html, base)
            if not links:
                if page_num == 1:
                    logger.warning("    ✗ 第 1 页没有找到图片链接")
                break
            for url in links:
                if url not in seen:
                    seen.add(url)
                    view_urls.append(url)

            next_url = parsers.parse_next_page(html, base)
            # 同一作品の -page- 链接であることを確認（従来ロジック踏襲）
            if next_url and not ("photos-index" in next_url and "-page-" in next_url):
                next_url = None
            if not next_url or next_url in visited:
                break
            current_url = next_url
            page_num += 1

        return view_urls

    def _fetch_original(self, idx: int, view_url: str) -> Optional[Dict]:
        """単一 view ページから原図 URL を取得（スレッド関数）"""
        try:
            site_limiter.acquire()  # ダウンロード時のサイト負荷配慮（並行でもレート頭打ち）
            html = self.client.get_html(view_url)
            original_url = parsers.parse_original_image(html)
            if not original_url:
                logger.warning(f"    [{idx}] ✗ 未找到原图")
                return None
            ext = "jpg"
            if "." in original_url:
                ext = original_url.split(".")[-1].split("?")[0] or "jpg"
            return {"index": idx, "url": original_url, "filename": f"{idx:04d}.{ext}"}
        except Exception as e:
            logger.warning(f"    [{idx}] ✗ 获取失败: {get_error_message(e)}")
            return None


def _to_datetime(value) -> Optional[datetime]:
    """'YYYY-MM-DD' / 'YYYY-MM-DD HH:MM:SS' 文字列を datetime に変換"""
    if not value or isinstance(value, datetime):
        return value
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt)
        except (ValueError, TypeError):
            continue
    return None
