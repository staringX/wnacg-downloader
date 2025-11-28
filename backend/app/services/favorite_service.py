"""收藏服务 - 负责将漫画添加到网站收藏夹"""
import time
import re
from typing import Optional, Dict
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from app.crawler.base import MangaCrawler
from app.config import settings
from app.utils.logger import logger, get_error_message


class FavoriteService:
    """收藏服务类"""
    
    def __init__(self):
        self.crawler = MangaCrawler()
    
    def extract_manga_id(self, manga_url: str) -> Optional[str]:
        """从漫画URL中提取aid（漫画ID）
        
        Args:
            manga_url: 漫画URL，例如：https://www.wn05.ru/photos-index-aid-208661.html
            
        Returns:
            漫画ID（aid），例如：208661
        """
        try:
            # 从URL中提取aid：photos-index-aid-{aid}.html
            match = re.search(r'photos-index-aid-(\d+)\.html', manga_url)
            if match:
                return match.group(1)
            return None
        except Exception as e:
            logger.error(f"提取漫画ID失败: {get_error_message(e)}")
            return None
    
    def get_favorite_categories(self, manga_url: str) -> Dict[str, str]:
        """获取收藏分类列表（分类ID -> 分类名称的映射）
        
        Args:
            manga_url: 漫画URL
            
        Returns:
            字典，key为分类ID，value为分类名称（作者名）
        """
        if not self.crawler.driver:
            return {}
        
        try:
            manga_id = self.extract_manga_id(manga_url)
            if not manga_id:
                logger.error("无法提取漫画ID")
                return {}
            
            base = self.crawler.browser.base_url.rstrip('/')
            # 第一步：获取收藏表单
            add_fav_url = f"{base}/users-addfav-id-{manga_id}.html?ajax=true&_t={int(time.time() * 1000)}"
            
            self.crawler.driver.get(add_fav_url)
            time.sleep(2)
            
            # 检查是否需要登录
            if "users-login" in self.crawler.driver.current_url:
                logger.info("需要登录，先执行登录...")
                if not self.crawler.login(settings.manga_username, settings.manga_password):
                    logger.error("登录失败")
                    return {}
                # 登录后重新获取表单
                self.crawler.driver.get(add_fav_url)
                time.sleep(2)
            
            # 解析HTML，提取分类选项
            categories = {}
            try:
                # 查找select元素
                select = self.crawler.driver.find_element(By.CSS_SELECTOR, "select[name='favc_id']")
                options = select.find_elements(By.CSS_SELECTOR, "option")
                
                for option in options:
                    value = option.get_attribute('value')
                    text = option.text.strip()
                    # 跳过空值和"請選擇收藏分類"
                    if value and value != '' and text and text != "請選擇收藏分類":
                        categories[value] = text
                
                logger.info(f"获取到 {len(categories)} 个收藏分类")
            except Exception as e:
                logger.error(f"解析分类列表失败: {get_error_message(e)}")
                return {}
            
            return categories
            
        except Exception as e:
            logger.error(f"获取收藏分类失败: {get_error_message(e)}")
            return {}
    
    def find_category_id_by_author(self, manga_url: str, author: str) -> Optional[str]:
        """根据作者名查找对应的分类ID
        
        Args:
            manga_url: 漫画URL
            author: 作者名
            
        Returns:
            分类ID，如果找不到则返回None
        """
        categories = self.get_favorite_categories(manga_url)
        
        # 精确匹配
        for category_id, category_name in categories.items():
            if category_name == author:
                logger.info(f"找到作者分类: {author} -> {category_id}")
                return category_id
        
        # 模糊匹配（如果精确匹配失败）
        for category_id, category_name in categories.items():
            if author in category_name or category_name in author:
                logger.info(f"模糊匹配到作者分类: {author} -> {category_name} ({category_id})")
                return category_id
        
        logger.warning(f"未找到作者 '{author}' 对应的分类")
        return None
    
    def add_to_favorite(self, manga_url: str, author: str) -> bool:
        """将漫画添加到网站收藏夹（对应作者文件夹）
        
        Args:
            manga_url: 漫画URL
            author: 作者名（用于匹配分类）
            
        Returns:
            是否成功
        """
        if not self.crawler.driver:
            # 初始化浏览器
            if not self.crawler.browser.driver:
                logger.error("浏览器未初始化")
                return False
        
        try:
            # 确保已登录
            if not self.crawler.login(settings.manga_username, settings.manga_password):
                logger.error("登录失败")
                return False
            
            manga_id = self.extract_manga_id(manga_url)
            if not manga_id:
                logger.error("无法提取漫画ID")
                return False
            
            # 查找作者对应的分类ID
            category_id = self.find_category_id_by_author(manga_url, author)
            if not category_id:
                logger.error(f"未找到作者 '{author}' 对应的分类，无法收藏")
                return False
            
            base = self.crawler.browser.base_url.rstrip('/')
            
            # 根据MCP观察，收藏流程：
            # 1. GET /users-addfav-id-{aid}.html?ajax=true - 获取表单（确保登录状态）
            # 2. POST /users-save_fav-id-{aid}.html - 提交表单，请求体：favc_id={分类ID}
            
            # 第一步：先访问表单页面，确保登录状态有效
            add_fav_url = f"{base}/users-addfav-id-{manga_id}.html?ajax=true&_t={int(time.time() * 1000)}"
            self.crawler.driver.get(add_fav_url)
            time.sleep(1)
            
            # 检查是否需要登录
            if "users-login" in self.crawler.driver.current_url:
                logger.info("需要重新登录...")
                if not self.crawler.login(settings.manga_username, settings.manga_password):
                    logger.error("登录失败")
                    return False
                # 登录后重新获取表单
                self.crawler.driver.get(add_fav_url)
                time.sleep(1)
            
            # 第二步：提交收藏表单
            save_fav_url = f"{base}/users-save_fav-id-{manga_id}.html"
            
            try:
                import requests
                
                # 获取当前会话的cookies（从Selenium）
                cookies = {}
                for cookie in self.crawler.driver.get_cookies():
                    cookies[cookie['name']] = cookie['value']
                
                # 获取User-Agent
                user_agent = self.crawler.driver.execute_script("return navigator.userAgent;")
                
                # 发送POST请求
                headers = {
                    'User-Agent': user_agent,
                    'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                    'X-Requested-With': 'XMLHttpRequest',
                    'Referer': manga_url,
                    'Accept': 'application/json, text/javascript, */*; q=0.01',
                }
                
                data = {
                    'favc_id': category_id
                }
                
                response = requests.post(
                    save_fav_url,
                    headers=headers,
                    cookies=cookies,
                    data=data,
                    timeout=10
                )
                
                # 检查响应
                if response.status_code == 200:
                    # 检查响应内容是否包含成功提示
                    response_text = response.text
                    if "成功" in response_text or "已收藏" in response_text:
                        logger.info(f"✅ 成功收藏漫画到分类: {author} (ID: {category_id})")
                        return True
                    else:
                        logger.warning(f"收藏可能失败，响应: {response_text[:200]}")
                        # 即使没有明确成功提示，如果状态码是200，也认为可能成功
                        # 因为网站可能返回空响应或JSON
                        logger.info(f"✅ 收藏请求已发送（状态码200），假设成功: {author} (ID: {category_id})")
                        return True
                else:
                    logger.error(f"收藏失败，HTTP状态码: {response.status_code}")
                    return False
                    
            except Exception as e:
                logger.error(f"提交收藏请求失败: {get_error_message(e)}")
                return False
            
        except Exception as e:
            logger.error(f"收藏漫画失败: {get_error_message(e)}")
            return False
    
    def close(self):
        """关闭浏览器"""
        if self.crawler:
            self.crawler.close()

