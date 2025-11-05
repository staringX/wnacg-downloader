import requests
from bs4 import BeautifulSoup
from typing import List, Optional, Dict
import time
import re
from datetime import datetime
from app.config import settings

# 可选的Selenium导入
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException, NoSuchElementException
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False
    print("警告: Selenium未安装，爬虫功能将不可用")


class MangaCrawler:
    def __init__(self):
        self.base_url: Optional[str] = None
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
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
        
        try:
            self.driver = webdriver.Chrome(options=chrome_options)
        except Exception as e:
            print(f"警告：无法初始化Chrome驱动: {e}")
            self.driver = None
    
    def get_available_url(self) -> Optional[str]:
        """从发布页获取可用的漫画网站地址"""
        try:
            response = self.session.get(settings.publish_page_url, timeout=10)
            response.encoding = 'utf-8'
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 查找所有链接
            links = soup.find_all('a', href=True)
            urls = []
            
            for link in links:
                href = link.get('href', '')
                text = link.get_text(strip=True)
                
                # 匹配网站地址模式（www.wn*.ru 或 www.wnacg*.cc等）
                if re.match(r'https?://www\.wn\d+\.ru', href) or \
                   re.match(r'https?://www\.wnacg\d+\.cc', href):
                    urls.append(href)
            
            # 尝试连接每个URL，返回第一个可用的
            for url in urls:
                try:
                    test_response = self.session.get(f"{url}/", timeout=5)
                    if test_response.status_code == 200:
                        return url
                except:
                    continue
            
            return None
        except Exception as e:
            print(f"获取网站地址失败: {e}")
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
            login_url = f"{self.base_url}/users-login.html"
            self.driver.get(login_url)
            time.sleep(2)
            
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
            if "users-login" not in current_url:
                # 获取cookies并设置到session
                cookies = self.driver.get_cookies()
                for cookie in cookies:
                    self.session.cookies.set(cookie['name'], cookie['value'])
                return True
            
            return False
        except Exception as e:
            print(f"登录失败: {e}")
            return False
    
    def get_collection(self) -> List[Dict]:
        """获取收藏夹中的所有漫画，按作者分类"""
        if not self.driver:
            return []
        
        try:
            # 导航到我的书架页面
            bookshelf_url = f"{self.base_url}/users-bookshelf.html"
            self.driver.get(bookshelf_url)
            time.sleep(3)
            
            mangas = []
            
            # 获取所有作者分类链接
            category_links = self.driver.find_elements(By.CSS_SELECTOR, "a[href*='bookshelf']")
            
            for link in category_links:
                category_text = link.text.strip()
                if category_text and category_text != "全部" and category_text != "管理分類":
                    # 点击分类链接
                    link.click()
                    time.sleep(2)
                    
                    # 解析当前分类下的漫画
                    manga_items = self.driver.find_elements(By.CSS_SELECTOR, "a[href*='photos-index']")
                    
                    for item in manga_items:
                        try:
                            title = item.text.strip()
                            manga_url = item.get_attribute('href')
                            
                            if title and manga_url:
                                # 获取页数信息
                                parent = item.find_element(By.XPATH, "./..")
                                page_info = parent.find_elements(By.XPATH, ".//*[contains(text(), '頁數')]")
                                page_count = None
                                
                                if page_info:
                                    page_text = page_info[0].text
                                    page_match = re.search(r'頁數[：:]\s*(\d+)', page_text)
                                    if page_match:
                                        page_count = int(page_match.group(1))
                                
                                mangas.append({
                                    'title': title,
                                    'author': category_text,
                                    'manga_url': manga_url,
                                    'page_count': page_count
                                })
                        except Exception as e:
                            print(f"解析漫画项失败: {e}")
                            continue
            
            return mangas
        except Exception as e:
            print(f"获取收藏夹失败: {e}")
            return []
    
    def get_manga_details(self, manga_url: str) -> Optional[Dict]:
        """获取漫画详情（页数、更新日期、封面等）"""
        if not self.driver:
            return None
        
        try:
            self.driver.get(manga_url)
            time.sleep(2)
            
            # 获取标题
            title_elem = self.driver.find_element(By.CSS_SELECTOR, "h2")
            title = title_elem.text.strip()
            
            # 获取页数
            page_info = self.driver.find_element(By.XPATH, "//*[contains(text(), '頁數')]")
            page_text = page_info.text
            page_match = re.search(r'頁數[：:]\s*(\d+)', page_text)
            page_count = int(page_match.group(1)) if page_match else None
            
            # 获取作者（从标签中提取）
            author = None
            tag_links = self.driver.find_elements(By.CSS_SELECTOR, "a[href*='tag']")
            for tag in tag_links:
                tag_text = tag.text.strip()
                # 通常第一个标签是作者
                if tag_text and not tag_text.startswith('['):
                    author = tag_text
                    break
            
            # 获取封面图片URL
            cover_img = self.driver.find_element(By.CSS_SELECTOR, "img[alt*='']")
            cover_url = cover_img.get_attribute('src')
            
            # 获取更新日期（从图片上传时间中提取）
            upload_info = self.driver.find_elements(By.XPATH, "//*[contains(text(), '上傳於')]")
            updated_at = None
            if upload_info:
                upload_text = upload_info[0].text
                date_match = re.search(r'上傳於(\d{4}-\d{2}-\d{2})', upload_text)
                if date_match:
                    date_str = date_match.group(1)
                    updated_at = datetime.strptime(date_str, '%Y-%m-%d')
            
            return {
                'title': title,
                'author': author,
                'manga_url': manga_url,
                'page_count': page_count,
                'updated_at': updated_at,
                'cover_image_url': cover_url
            }
        except Exception as e:
            print(f"获取漫画详情失败: {e}")
            return None
    
    def get_manga_images(self, manga_url: str) -> List[Dict]:
        """获取漫画的所有图片URL，按显示顺序"""
        if not self.driver:
            return []
        
        try:
            # 导航到漫画详情页
            self.driver.get(manga_url)
            time.sleep(2)
            
            # 点击"下拉閱讀"或直接访问列表页
            try:
                list_link = self.driver.find_element(By.XPATH, "//a[contains(text(), '下拉閱讀')]")
                list_url = list_link.get_attribute('href')
            except:
                # 如果没有找到，尝试构建列表页URL
                if '/photos-index' in manga_url:
                    list_url = manga_url.replace('/photos-index', '/photos-index') + '-list.html'
                else:
                    list_url = manga_url + '-list.html'
            
            self.driver.get(list_url)
            time.sleep(3)
            
            images = []
            
            # 获取所有图片链接（按页面上的顺序）
            # 图片链接通常在详情页的缩略图列表中
            img_links = self.driver.find_elements(By.CSS_SELECTOR, "a[href*='photos-view'], a[href*='photo']")
            
            # 如果没有找到，尝试从详情页获取
            if not img_links:
                self.driver.get(manga_url)
                time.sleep(2)
                img_links = self.driver.find_elements(By.CSS_SELECTOR, "a[href*='photos-view'], a[href*='photo']")
            
            for idx, link in enumerate(img_links, 1):
                try:
                    img_url = link.get_attribute('href')
                    if not img_url or 'photos-view' not in img_url:
                        # 尝试从图片元素获取
                        img_elem = link.find_element(By.CSS_SELECTOR, "img")
                        img_src = img_elem.get_attribute('src')
                        if img_src and 'photo' in img_src:
                            # 直接使用缩略图URL，可能需要替换为原图URL
                            # 这里需要根据实际网站结构调整
                            images.append({
                                'index': idx,
                                'url': img_src.replace('/thumb/', '/') if '/thumb/' in img_src else img_src,
                                'filename': f"{idx:04d}.jpg"
                            })
                        continue
                    
                    # 打开图片页面获取原图
                    self.driver.get(img_url)
                    time.sleep(1)
                    
                    # 查找原图
                    try:
                        img_elem = self.driver.find_element(By.CSS_SELECTOR, "img[src*='photo'], img[src*='image']")
                        original_url = img_elem.get_attribute('src')
                        
                        if original_url:
                            # 获取文件扩展名
                            ext = original_url.split('.')[-1].split('?')[0] if '.' in original_url else 'jpg'
                            images.append({
                                'index': idx,
                                'url': original_url,
                                'filename': f"{idx:04d}.{ext}"
                            })
                    except:
                        # 如果找不到，尝试使用URL中的图片
                        if 'photo' in img_url:
                            images.append({
                                'index': idx,
                                'url': img_url,
                                'filename': f"{idx:04d}.jpg"
                            })
                    
                    # 返回列表页
                    if idx < len(img_links):
                        self.driver.back()
                        time.sleep(0.5)
                except Exception as e:
                    print(f"获取图片 {idx} 失败: {e}")
                    continue
            
            return images
        except Exception as e:
            print(f"获取漫画图片失败: {e}")
            return []
    
    def close(self):
        """关闭浏览器"""
        if self.driver:
            self.driver.quit()
            self.driver = None
