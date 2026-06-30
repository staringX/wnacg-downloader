"""搜索功能モジュール（requests + BeautifulSoup 版・フェーズ2）

search_author_updates を HttpClient + parsers で提供する。
- 検索結果は時間降順。since_date より新しい作品のみ返し、古い作品に当たったら打ち切り。
- updated_at は datetime（parsers の文字列を変換）。
- 数字ページネーション（p=N）を parsers.parse_search_next_page で辿る。
"""
from datetime import datetime
from typing import Dict, List
from urllib.parse import quote

from app.crawler import parsers
from app.crawler.manga_details import _to_datetime
from app.utils.logger import logger, get_error_message


class SearchCrawler:
    """搜索爬取器（requests 版）"""

    def __init__(self, client):
        self.client = client

    @property
    def base_url(self):
        return self.client.base_url

    def search_author_updates(self, author_name: str,
                              since_date: datetime) -> List[Dict]:
        """作者を検索し since_date より新しい更新を返す"""
        base = self.base_url
        if not base:
            logger.error("base_url未设置，无法搜索作者更新")
            return []
        base = base.rstrip("/")

        try:
            encoded = quote(author_name)
            current_url = f"{base}/q/?q={encoded}&f=_all&s=create_time_DESC&syn=yes"
            logger.info(f"搜索作者: {author_name}, URL: {current_url}")

            visited = set()
            page_num = 1
            results: List[Dict] = []

            # 固定上限は設けない。訪問済み URL 集合 + since_date 打ち切り + 次ページ無しで必ず有限停止する。
            while current_url and current_url not in visited:
                visited.add(current_url)
                logger.info(f"  访问第 {page_num} 页: {current_url}")
                try:
                    html = self.client.get_html(current_url)
                except Exception as e:
                    logger.warning(f"    页面获取失败: {get_error_message(e)}")
                    break

                items = parsers.parse_search_page(html, base, author=author_name)
                if not items:
                    logger.info(f"    第 {page_num} 页没有找到漫画，停止翻页")
                    break

                should_stop = False
                for item in items:
                    dt = _to_datetime(item.get("updated_at"))
                    if dt is None:
                        continue
                    if dt > since_date:
                        results.append({
                            "title": item["title"],
                            "manga_url": item["manga_url"],
                            "updated_at": dt,
                            "page_count": item["page_count"],
                            "cover_image_url": item["cover_image_url"],
                            "author": author_name,
                        })
                    else:
                        # 時間降順のため、これ以降は更に古い → 打ち切り
                        logger.info(
                            f"    遇到早于截止日期的漫画（{dt} <= {since_date}），停止翻页")
                        should_stop = True
                        break
                if should_stop:
                    break

                next_url = parsers.parse_search_next_page(html, base, page_num)
                if not next_url or next_url in visited:
                    logger.info("    未找到下一页链接，停止翻页")
                    break
                current_url = next_url
                page_num += 1

            logger.info(f"  作者 {author_name} 共找到 {len(results)} 个新更新")
            return results
        except Exception as e:
            logger.error(f"搜索作者 {author_name} 失败: {get_error_message(e)}")
            return []
