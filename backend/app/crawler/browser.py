"""浏览器管理和登录模块"""
import time
import os
from typing import Optional
from app.config import settings
from app.utils.logger import logger, get_error_message

# 可选的Selenium导入
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False
    logger.warning("Selenium未安装，爬虫功能将不可用")


class BrowserManager:
    """浏览器管理器 - 负责浏览器的初始化和登录"""
    
    def __init__(self):
        self.base_url: Optional[str] = None
        self.driver: Optional[webdriver.Chrome] = None
        self._init_driver()
    
    def _init_driver(self):
        """初始化Chrome浏览器驱动"""
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        # 在Docker环境中，chromedriver可能在/usr/local/bin/chromedriver或/usr/bin/chromedriver
        chromedriver_paths = [
            '/usr/local/bin/chromedriver',
            '/usr/bin/chromedriver',
            '/usr/bin/chromium-driver'
        ]
        
        # 检查是否使用Chromium（Docker环境）
        chromium_binary_paths = [
            '/usr/bin/chromium',
            '/usr/bin/chromium-browser'
        ]
        
        chromedriver_path = None
        for path in chromedriver_paths:
            if os.path.exists(path):
                chromedriver_path = path
                break
        
        # 如果找到Chromium，设置binary路径
        for chromium_path in chromium_binary_paths:
            if os.path.exists(chromium_path):
                chrome_options.binary_location = chromium_path
                break
        
        try:
            if chromedriver_path:
                service = Service(chromedriver_path)
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
            else:
                # 尝试自动检测
                self.driver = webdriver.Chrome(options=chrome_options)
        except Exception as e:
            logger.error(f"无法初始化Chrome驱动: {get_error_message(e)}")
            self.driver = None
    
    def get_available_url(self) -> Optional[str]:
        """从发布页获取可用的漫画网站地址（根据页面布局和元素结构查找）"""
        import requests
        from bs4 import BeautifulSoup
        
        try:
            response = requests.get(settings.publish_page_url, timeout=10)
            response.encoding = 'utf-8'
            soup = BeautifulSoup(response.text, 'html.parser')
            
            urls = []
            
            # 根据页面布局查找：在ul列表的li元素中查找target="_blank"的链接
            # 这些链接通常就是漫画网站地址
            ul_lists = soup.find_all('ul')
            
            for ul in ul_lists:
                # 查找ul中的所有li元素
                li_items = ul.find_all('li')
                
                for li in li_items:
                    # 在每个li中查找target="_blank"的链接（根据页面结构特征）
                    links = li.find_all('a', {'target': '_blank'}, href=True)
                    
                    for link in links:
                        href = link.get('href', '')
                        
                        # 排除发布页本身和chrome浏览器链接（根据URL特征）
                        if 'wn01.link' in href or 'google.cn' in href:
                            continue
                        
                        # 检查链接内部是否有i标签（页面结构特征）
                        # 漫画网站链接通常有i标签包裹文本
                        if link.find('i') and href.startswith('http'):
                            urls.append(href)
            
            # 如果上面的方法没找到，尝试备用方法：查找所有ul中li内的链接
            if not urls:
                for ul in ul_lists:
                    li_items = ul.find_all('li')
                    for li in li_items:
                        links = li.find_all('a', href=True)
                        for link in links:
                            href = link.get('href', '')
                            # 排除发布页和chrome链接
                            if 'wn01.link' in href or 'google.cn' in href:
                                continue
                            # 检查是否是http/https链接
                            if href.startswith('http'):
                                urls.append(href)
            
            # 尝试连接每个URL，返回第一个可用的
            for url in urls:
                try:
                    test_response = requests.get(f"{url}/", timeout=5)
                    if test_response.status_code == 200:
                        logger.info(f"找到可用的漫画网站地址: {url}")
                        return url
                except:
                    continue
            
            logger.warning("未找到可用的漫画网站地址")
            return None
        except Exception as e:
            logger.error(f"获取网站地址失败: {get_error_message(e)}")
            return None
    
    def login(self, username: str, password: str) -> bool:
        """登录网站"""
        if not self.base_url:
            self.base_url = self.get_available_url()
            if not self.base_url:
                return False
        
        if not self.driver:
            return False
        
        try:
            # 导航到登录页面
            base = self.base_url.rstrip('/')
            login_url = f"{base}/users-login.html"
            self.driver.get(login_url)
            time.sleep(3)
            
            # 查找并填写登录表单
            username_input = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.NAME, "login_name"))
            )
            password_input = self.driver.find_element(By.NAME, "login_pass")
            
            username_input.clear()
            username_input.send_keys(username)
            password_input.clear()
            password_input.send_keys(password)
            
            # 点击登录按钮
            login_button = self.driver.find_element(By.CSS_SELECTOR, "button, input[type='submit']")
            login_button.click()
            
            # 等待登录完成
            time.sleep(3)
            
            # 检查是否登录成功（查找用户名或退出登录链接）
            current_url = self.driver.current_url
            logger.info(f"登录后跳转到: {current_url}")
            
            # 等待页面加载完成
            time.sleep(2)
            
            # 检查页面是否包含登录成功的标志
            page_source = self.driver.page_source
            if "users-login" not in current_url or "我的空間" in page_source or username in page_source:
                logger.info("登录成功，已保存cookies")
                return True
            
            logger.warning("登录可能失败，仍在登录页面")
            return False
        except Exception as e:
            logger.error(f"登录失败: {get_error_message(e)}")
            return False
    
    def close(self):
        """关闭浏览器"""
        if self.driver:
            self.driver.quit()
            self.driver = None

