"""爬虫基础类 - 整合所有功能模块（requests + BeautifulSoup）

クロールは HttpClient + parsers に統一。公開 API（login/get_collection_stream/
get_manga_details/get_manga_images/search_author_updates/base_url/get_available_url/close）を提供する。
"""
from app.crawler.http_client import HttpClient
from app.crawler.collection import CollectionCrawler
from app.crawler.manga_details import MangaDetailsCrawler
from app.crawler.archive_download import ArchiveDownloadCrawler
from app.crawler.search import SearchCrawler


class MangaCrawler:
    """漫画爬虫主类 - 整合所有爬虫功能（requests ベース）"""

    def __init__(self):
        self.client = HttpClient()
        self.collection = CollectionCrawler(self.client)
        self.details = MangaDetailsCrawler(self.client)
        self.archive = ArchiveDownloadCrawler(self.client)
        self.search = SearchCrawler(self.client)

    @property
    def base_url(self):
        """访问基础URL"""
        return self.client.base_url

    def get_available_url(self) -> str:
        """从发布页获取可用的漫画网站地址"""
        return self.client.get_available_url()

    def login(self, username: str, password: str) -> bool:
        """登录网站"""
        return self.client.login(username, password)

    def get_collection_stream(self):
        """获取收藏夹中的所有漫画（生成器版本）"""
        return self.collection.get_collection_stream()

    def get_manga_details(self, manga_url: str):
        """获取漫画详情（页数、更新日期、封面等）"""
        return self.details.get_manga_details(manga_url)

    def get_manga_images(self, manga_url: str):
        """获取漫画的所有图片URL，按显示顺序"""
        return self.details.get_manga_images(manga_url)

    def get_download_routes(self, manga_url: str):
        """获取一括下载（ZIP）的可用线路列表"""
        return self.archive.get_download_routes(manga_url)

    def download_archive(self, routes, dest_path, progress_cb=None):
        """按线路顺序下载 ZIP（失败自动切换线路）"""
        return self.archive.download_archive(routes, dest_path, progress_cb)

    def search_author_updates(self, author_name: str, since_date):
        """搜索作者并获取更新"""
        return self.search.search_author_updates(author_name, since_date)

    def close(self):
        """关闭会话"""
        self.archive.close()
        self.client.close()
