"""収藏夹爬取モジュール（requests + BeautifulSoup）

HttpClient + parsers で収藏夹一覧をストリーム取得する。
yield する辞書の形（title/author/manga_url/page_count）と挙動（作者カテゴリ毎にページ送り・
グローバル重複排除・最大100ページ）を提供する。
"""
import re
from typing import Dict, Generator

from app.crawler import parsers
from app.utils.logger import logger, get_error_message

EXCLUDED_CATEGORY_NAMES = parsers.EXCLUDED_CATEGORY_NAMES


class CollectionCrawler:
    """収藏夹爬取器（requests 版）"""

    def __init__(self, client):
        self.client = client

    @property
    def base_url(self):
        return self.client.base_url

    def get_collection_stream(self) -> Generator[Dict, None, None]:
        """収藏夹の全漫画をストリーム取得（生成器）

        Yields: {'title', 'author', 'manga_url', 'page_count'}
        """
        base = self.base_url
        if not base:
            logger.error("base_url未设置，无法获取收藏夹")
            return
        base = base.rstrip("/")

        try:
            shelf_url = f"{base}/users-users_fav.html"
            logger.info(f"访问书架页面: {shelf_url}")
            shelf_html = self.client.get_html(shelf_url)

            categories = parsers.parse_favorite_categories(shelf_html)
            logger.info(f"共找到 {len(categories)} 个作者分类")

            seen_urls = set()  # グローバル重複排除
            total_count = 0

            if categories:
                for idx, (author, category_url) in enumerate(categories.items(), 1):
                    logger.info(f"[{idx}/{len(categories)}] 处理作者分类: {author}")
                    full_category_url = parsers._abs_url(category_url, base)
                    yield from self._stream_category(
                        author, full_category_url, base, seen_urls)
            else:
                # カテゴリが無い場合は書架ページ自体から取得（author 不明）
                logger.info("未找到分类链接，从书架页面直接获取漫画...")
                page = parsers.parse_collection_page(shelf_html, base)
                for m in page["mangas"]:
                    if m["manga_url"] in seen_urls:
                        continue
                    seen_urls.add(m["manga_url"])
                    total_count += 1
                    yield {
                        "title": m["title"],
                        "author": "未知",
                        "manga_url": m["manga_url"],
                        "page_count": m["page_count"],
                    }

            logger.info(f"✓ 收藏夹爬取完成，总共 {len(seen_urls)} 个漫画")
        except Exception as e:
            logger.error(f"获取收藏夹失败: {get_error_message(e)}")
            return

    def _stream_category(self, author, category_url, base, seen_urls):
        """単一作者カテゴリのページを順に辿って yield する"""
        category_id_match = re.search(r"users-users_fav-c-(\d+)\.html", category_url or "")
        category_id = category_id_match.group(1) if category_id_match else None

        current_url = category_url
        visited = set()
        page_num = 1
        author_count = 0

        # 冊数に固定上限は設けない。訪問済み URL 集合 + 「次ページ無しで終了」で必ず有限停止する。
        while current_url and current_url not in visited:
            visited.add(current_url)
            logger.info(f"  访问第 {page_num} 页: {current_url}")
            try:
                html = self.client.get_html(current_url)
            except Exception as e:
                logger.warning(f"    页面获取失败: {get_error_message(e)}")
                break

            page = parsers.parse_collection_page(html, base)
            page_count_yielded = 0
            for m in page["mangas"]:
                if m["manga_url"] in seen_urls:
                    continue
                seen_urls.add(m["manga_url"])
                author_count += 1
                page_count_yielded += 1
                yield {
                    "title": m["title"],
                    "author": author,
                    "manga_url": m["manga_url"],
                    "page_count": m["page_count"],
                }

            logger.info(f"    第 {page_num} 页：找到 {page_count_yielded} 个新漫画")
            if page_count_yielded == 0:
                break

            next_url = page["next_url"]
            # 次ページが同一カテゴリの -page- リンクであることを確認（従来ロジック踏襲）
            if next_url and category_id and not (
                    "users-users_fav" in next_url and "-page-" in next_url
                    and f"c-{category_id}" in next_url):
                next_url = None
            if not next_url or next_url in visited:
                break
            current_url = next_url
            page_num += 1

        logger.info(f"  {author} 总共获取 {author_count} 个漫画")
