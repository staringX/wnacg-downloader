"""爬虫基础类 - 整合所有功能模块"""
from app.crawler.browser import BrowserManager
from app.crawler.collection import CollectionCrawler
from app.crawler.manga_details import MangaDetailsCrawler
from app.crawler.search import SearchCrawler


class MangaCrawler:
    """漫画爬虫主类 - 整合所有爬虫功能"""
    
    def __init__(self):
        self.browser = BrowserManager()
        self.collection = CollectionCrawler(self.browser)
        self.details = MangaDetailsCrawler(self.browser)
        self.search = SearchCrawler(self.browser)
    
    @property
    def driver(self):
        """访问浏览器驱动"""
        return self.browser.driver
    
    @property
    def base_url(self):
        """访问基础URL"""
        return self.browser.base_url
    
    def get_available_url(self) -> str:
        """从发布页获取可用的漫画网站地址"""
        return self.browser.get_available_url()
    
    def login(self, username: str, password: str) -> bool:
        """登录网站"""
        return self.browser.login(username, password)
    
    def get_collection_stream(self):
        """获取收藏夹中的所有漫画（生成器版本）"""
        return self.collection.get_collection_stream()
    
    def get_manga_details(self, manga_url: str):
        """获取漫画详情（页数、更新日期、封面等）"""
        return self.details.get_manga_details(manga_url)
    
    def get_manga_images(self, manga_url: str):
        """获取漫画的所有图片URL，按显示顺序"""
        return self.details.get_manga_images(manga_url)
    
    def search_author_updates(self, author_name: str, since_date):
        """搜索作者并获取更新"""
        return self.search.search_author_updates(author_name, since_date)
    
    def close(self):
        """关闭浏览器"""
        self.browser.close()
