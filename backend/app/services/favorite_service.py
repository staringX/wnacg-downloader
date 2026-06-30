"""收藏服务 - 负责将漫画添加到网站收藏夹

HttpClient のセッションで収藏フォーム取得・收藏 POST を完結する（Cookie 自動・
手動受け渡し撤廃）。解析は parsers.parse_addfav_form。

公開 API（get_favorite_categories / find_category_id_by_author / add_to_favorite / close）は不変。
"""
import time
import re
from typing import Optional, Dict

from app.crawler.base import MangaCrawler
from app.crawler import parsers
from app.config import settings
from app.utils.logger import logger, get_error_message


class FavoriteService:
    """收藏服务类"""

    def __init__(self):
        self.crawler = MangaCrawler()

    def extract_manga_id(self, manga_url: str) -> Optional[str]:
        """从漫画URL中提取aid（漫画ID），例: photos-index-aid-208661.html -> 208661"""
        try:
            match = re.search(r'photos-index-aid-(\d+)\.html', manga_url)
            return match.group(1) if match else None
        except Exception as e:
            logger.error(f"提取漫画ID失败: {get_error_message(e)}")
            return None

    @staticmethod
    def _addfav_url(base: str, manga_id: str) -> str:
        return (f"{base.rstrip('/')}/users-addfav-id-{manga_id}.html"
                f"?ajax=true&_t={int(time.time() * 1000)}")

    # ------------------------------------------------------------------
    # 分类取得
    # ------------------------------------------------------------------
    def get_favorite_categories(self, manga_url: str) -> Dict[str, str]:
        """获取收藏分类列表（分类ID -> 分类名称(作者名) 的映射）"""
        client = self.crawler.client
        manga_id = self.extract_manga_id(manga_url)
        if not manga_id:
            logger.error("无法提取漫画ID")
            return {}
        # セッション/ベース URL を確保
        if not client.base_url:
            if not self.crawler.login(settings.manga_username, settings.manga_password):
                logger.error("登录失败")
                return {}
        url = self._addfav_url(client.base_url, manga_id)
        try:
            html = client.get_html(url)
        except Exception as e:
            logger.error(f"获取收藏表单失败: {get_error_message(e)}")
            return {}
        categories = parsers.parse_addfav_form(html)
        # 空ならログイン切れの可能性 → 一度だけ再ログインして取り直す
        if not categories:
            if self.crawler.login(settings.manga_username, settings.manga_password):
                try:
                    categories = parsers.parse_addfav_form(client.get_html(url))
                except Exception as e:
                    logger.error(f"重试获取收藏表单失败: {get_error_message(e)}")
        logger.info(f"获取到 {len(categories)} 个收藏分类")
        return categories

    def find_category_id_by_author(self, manga_url: str, author: str) -> Optional[str]:
        """根据作者名查找对应的分类ID（精确→模糊匹配）"""
        categories = self.get_favorite_categories(manga_url)
        for category_id, category_name in categories.items():
            if category_name == author:
                logger.info(f"找到作者分类: {author} -> {category_id}")
                return category_id
        for category_id, category_name in categories.items():
            if author in category_name or category_name in author:
                logger.info(f"模糊匹配到作者分类: {author} -> {category_name} ({category_id})")
                return category_id
        logger.warning(f"未找到作者 '{author}' 对应的分类")
        return None

    # ------------------------------------------------------------------
    # 收藏登録
    # ------------------------------------------------------------------
    def add_to_favorite(self, manga_url: str, author: str) -> bool:
        """将漫画添加到网站收藏夹（对应作者文件夹）"""
        client = self.crawler.client
        try:
            if not self.crawler.login(settings.manga_username, settings.manga_password):
                logger.error("登录失败")
                return False
            manga_id = self.extract_manga_id(manga_url)
            if not manga_id:
                logger.error("无法提取漫画ID")
                return False
            category_id = self.find_category_id_by_author(manga_url, author)
            if not category_id:
                logger.error(f"未找到作者 '{author}' 对应的分类，无法收藏")
                return False

            base = client.base_url.rstrip('/')
            # フォームページに触れてセッション状態を確実にする（best-effort）
            try:
                client.get_html(self._addfav_url(base, manga_id))
            except Exception:
                pass

            save_fav_url = f"{base}/users-save_fav-id-{manga_id}.html"
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'X-Requested-With': 'XMLHttpRequest',
                'Referer': manga_url,
                'Accept': 'application/json, text/javascript, */*; q=0.01',
            }
            try:
                response = client.post(save_fav_url, data={'favc_id': category_id},
                                       headers=headers)
            except Exception as e:
                logger.error(f"提交收藏请求失败: {get_error_message(e)}")
                return False
            return self._interpret_save_response(response, author, category_id)
        except Exception as e:
            logger.error(f"收藏漫画失败: {get_error_message(e)}")
            return False

    @staticmethod
    def _interpret_save_response(response, author: str, category_id: str) -> bool:
        """收藏 POST のレスポンス判定（従来挙動踏襲: 200 なら成功とみなす）"""
        if response.status_code != 200:
            logger.error(f"收藏失败，HTTP状态码: {response.status_code}")
            return False
        text = response.text or ""
        if "成功" in text or "已收藏" in text:
            logger.info(f"✅ 成功收藏漫画到分类: {author} (ID: {category_id})")
        else:
            logger.info(f"✅ 收藏请求已发送（状态码200），假设成功: {author} (ID: {category_id})")
        return True

    def close(self):
        """关闭浏览器/会话"""
        if self.crawler:
            self.crawler.close()
