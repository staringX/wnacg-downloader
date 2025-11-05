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
            print(f"登录后跳转到: {current_url}")
            
            # 等待页面加载完成
            time.sleep(2)
            
            # 检查页面是否包含登录成功的标志
            page_source = self.driver.page_source
            if "users-login" not in current_url or "我的空間" in page_source or "lilifan456" in page_source:
                # 获取cookies并设置到session
                cookies = self.driver.get_cookies()
                for cookie in cookies:
                    self.session.cookies.set(cookie['name'], cookie['value'])
                print("登录成功，已保存cookies")
                return True
            
            print("登录可能失败，仍在登录页面")
            return False
        except Exception as e:
            print(f"登录失败: {e}")
            return False
    
    def get_collection(self) -> List[Dict]:
        """获取收藏夹中的所有漫画，按作者分类"""
        if not self.driver:
            return []
        
        try:
            mangas = []
            base = self.base_url.rstrip('/')
            
            # 正确的书架URL（通过Chrome DevTools MCP确认）
            bookshelf_url = f"{base}/users-users_fav.html"
            print(f"访问书架页面: {bookshelf_url}")
            self.driver.get(bookshelf_url)
            time.sleep(5)
            
            # 检查页面是否成功加载
            current_url = self.driver.current_url
            page_title = self.driver.title
            print(f"当前页面URL: {current_url}")
            print(f"页面标题: {page_title}")
            
            if "404" in page_title.lower() or "404" in self.driver.page_source[:1000].lower():
                print(f"书架页面返回404")
                return []
            
            # 查找分类链接（格式：users-users_fav-c-{id}.html）
            category_links = {}  # {author_name: link_url}
            all_links = self.driver.find_elements(By.CSS_SELECTOR, "a")
            
            for link in all_links:
                href = link.get_attribute('href') or ''
                text = link.text.strip()
                
                # 识别分类链接：users-users_fav-c-{id}.html
                if 'users-users_fav-c-' in href and text:
                    # 排除"全部"和"管理分類"
                    if text not in ["全部", "管理分類", "書架", "书架", "我的書架"]:
                        category_links[text] = href
                        print(f"找到分类: {text} -> {href}")
            
            print(f"共找到 {len(category_links)} 个作者分类")
            
            # 如果有分类，按分类获取漫画
            if category_links:
                for author, category_url in category_links.items():
                    print(f"\n处理作者分类: {author}")
                    
                    # 提取分类ID（从URL中）
                    # 格式：users-users_fav-c-{category_id}.html
                    category_id_match = re.search(r'users-users_fav-c-(\d+)\.html', category_url)
                    if not category_id_match:
                        print(f"  无法提取分类ID，跳过")
                        continue
                    
                    category_id = category_id_match.group(1)
                    page_num = 1
                    author_manga_count = 0
                    
                    # 从第一页开始
                    current_url = category_url
                    visited_urls = set()
                    
                    # 遍历所有分页
                    while True:
                        # 避免重复访问
                        if current_url in visited_urls:
                            print(f"  检测到重复URL，停止翻页")
                            break
                        
                        print(f"  访问第 {page_num} 页: {current_url}")
                        self.driver.get(current_url)
                        visited_urls.add(current_url)
                        time.sleep(2)
                        
                        # 查找该页面下的所有漫画链接
                        manga_links = self.driver.find_elements(By.CSS_SELECTOR, "a[href*='photos-index-aid-']")
                        page_manga_count = 0
                        
                        for manga_link in manga_links:
                            try:
                                manga_url = manga_link.get_attribute('href')
                                title = manga_link.text.strip()
                                
                                # 跳过空标题或重复链接
                                if not title or not manga_url:
                                    continue
                                
                                # 检查是否已添加（避免重复）
                                if any(m['manga_url'] == manga_url for m in mangas):
                                    continue
                                
                                # 尝试获取页数信息
                                page_count = None
                                try:
                                    parent = manga_link.find_element(By.XPATH, "./ancestor::*[contains(text(), '頁數')]")
                                    page_text = parent.text
                                    page_match = re.search(r'頁數[：:]\s*(\d+)', page_text)
                                    if page_match:
                                        page_count = int(page_match.group(1))
                                except:
                                    pass
                                
                                mangas.append({
                                    'title': title,
                                    'author': author,
                                    'manga_url': manga_url,
                                    'page_count': page_count
                                })
                                page_manga_count += 1
                                author_manga_count += 1
                            except Exception as e:
                                print(f"    处理漫画失败: {e}")
                                continue
                        
                        print(f"    第 {page_num} 页：找到 {page_manga_count} 个漫画")
                        
                        # 如果没有找到漫画，停止翻页
                        if page_manga_count == 0:
                            print(f"    第 {page_num} 页没有找到漫画，停止翻页")
                            break
                        
                        # 查找"下一页"或"后頁"链接
                        next_page_link = None
                        try:
                            # 方法1：通过文本查找（后頁>、下一頁等）
                            next_links = self.driver.find_elements(By.XPATH, "//a[contains(text(), '後頁') or contains(text(), '后页') or contains(text(), '下一頁') or contains(text(), '下一页')]")
                            if next_links:
                                next_page_link = next_links[0]
                                print(f"    找到下一页链接（文本匹配）")
                        except Exception as e:
                            print(f"    方法1查找下一页失败: {e}")
                        
                        if not next_page_link:
                            try:
                                # 方法2：查找包含 users-users_fav 和 category_id 且未访问的链接
                                all_page_links = self.driver.find_elements(By.CSS_SELECTOR, f"a[href*='users-users_fav'][href*='c-{category_id}']")
                                for link in all_page_links:
                                    href = link.get_attribute('href')
                                    if href and href not in visited_urls and '-page-' in href:
                                        next_page_link = link
                                        print(f"    找到下一页链接（URL模式匹配）")
                                        break
                            except Exception as e:
                                print(f"    方法2查找下一页失败: {e}")
                        
                        if not next_page_link:
                            print(f"    没有找到下一页链接，停止翻页")
                            break
                        
                        # 获取下一页 URL
                        current_url = next_page_link.get_attribute('href')
                        if not current_url:
                            print(f"    下一页链接无效，停止翻页")
                            break
                        
                        page_num += 1
                        
                        # 安全检查：最多翻100页
                        if page_num > 100:
                            print(f"    已达到最大页数限制(100页)，停止翻页")
                            break
                    
                    print(f"  {author} 总共获取 {author_manga_count} 个漫画")
            else:
                # 如果没有找到分类链接，直接从当前页面获取所有漫画
                print("未找到分类链接，从当前页面直接获取漫画...")
                manga_links = self.driver.find_elements(By.CSS_SELECTOR, "a[href*='photos-index-aid-']")
                print(f"找到 {len(manga_links)} 个漫画链接")
                
                for manga_link in manga_links:
                    try:
                        manga_url = manga_link.get_attribute('href')
                        title = manga_link.text.strip()
                        
                        if title and manga_url:
                            # 尝试从页面中提取作者信息
                            author = "未知"
                            try:
                                # 查找分类名称（通常在链接附近）
                                parent = manga_link.find_element(By.XPATH, "./ancestor::*[position()<=5]")
                                author_elem = parent.find_elements(By.XPATH, ".//*[contains(@href, 'users-users_fav-c-')]")
                                if author_elem:
                                    author = author_elem[0].text.strip() or "未知"
                            except:
                                pass
                            
                            # 获取页数
                            page_count = None
                            try:
                                parent = manga_link.find_element(By.XPATH, "./ancestor::*[contains(text(), '頁數')]")
                                page_text = parent.text
                                page_match = re.search(r'頁數[：:]\s*(\d+)', page_text)
                                if page_match:
                                    page_count = int(page_match.group(1))
                            except:
                                pass
                            
                            mangas.append({
                                'title': title,
                                'author': author,
                                'manga_url': manga_url,
                                'page_count': page_count
                            })
                    except Exception as e:
                        print(f"处理漫画失败: {e}")
                        continue
            
            print(f"\n总共获取到 {len(mangas)} 个漫画")
            return mangas
        except Exception as e:
            print(f"获取收藏夹失败: {e}")
            import traceback
            traceback.print_exc()
            return []


    def get_manga_details(self, manga_url: str) -> Optional[Dict]:
        """获取漫画详情（页数、更新日期、封面等）"""
        if not self.driver:
            return None
        
        try:
            self.driver.get(manga_url)
            time.sleep(3)
            
            # 获取标题
            title = None
            try:
                title_elem = self.driver.find_element(By.CSS_SELECTOR, "h2")
                title = title_elem.text.strip()
            except:
                pass
            
            # 获取页数 - 格式："頁數：20P"
            page_count = None
            try:
                page_elem = self.driver.find_element(By.XPATH, "//*[contains(text(), '頁數')]")
                page_text = page_elem.text  # 例如: "頁數：20P"
                # 提取数字部分
                page_match = re.search(r'頁數[：:]\s*(\d+)', page_text)
                if page_match:
                    page_count = int(page_match.group(1))
            except Exception as e:
                print(f"    获取页数失败: {e}")
            
            # 获取上传日期 - 从图片列表中的"上傳於2023-06-22"提取
            updated_at = None
            try:
                # 查找所有包含"上傳於"的元素
                upload_elems = self.driver.find_elements(By.XPATH, "//*[contains(text(), '上傳於')]")
                if upload_elems:
                    # 取第一个图片的上传日期作为漫画更新日期
                    upload_text = upload_elems[0].text  # 例如: "上傳於2023-06-22"
                    date_match = re.search(r'上傳於(\d{4}-\d{2}-\d{2})', upload_text)
                    if date_match:
                        date_str = date_match.group(1)
                        updated_at = datetime.strptime(date_str, '%Y-%m-%d')
            except Exception as e:
                print(f"    获取上传日期失败: {e}")
            
            # 获取封面图片URL - 取第一张图片的缩略图
            cover_url = None
            try:
                # 查找所有图片，通常第一张是封面
                images = self.driver.find_elements(By.CSS_SELECTOR, "img[src*='wnimg']")
                if images:
                    cover_url = images[0].get_attribute('src')
            except Exception as e:
                print(f"    获取封面失败: {e}")
            
            return {
                'title': title,
                'manga_url': manga_url,
                'page_count': page_count,
                'updated_at': updated_at,
                'cover_image_url': cover_url
            }
        except Exception as e:
            print(f"获取漫画详情失败: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def get_manga_images(self, manga_url: str) -> List[Dict]:
        """获取漫画的所有图片URL，按显示顺序
        
        流程：
        1. 遍历漫画详情页的所有分页，收集所有图片查看链接 (photos-view-id-xxxxx.html)
        2. 逐个访问这些链接，从每个页面提取原图 URL
        3. 不使用"下拉阅读"，因为它是懒加载，大漫画会导致部分图片未加载
        """
        if not self.driver:
            return []
        
        try:
            print(f"\n开始获取漫画图片: {manga_url}")
            
            # 第一步：收集所有图片查看链接
            view_urls = []
            page_num = 1
            
            # 从第一页开始
            current_url = manga_url
            visited_urls = set()
            
            while True:
                # 避免重复访问
                if current_url in visited_urls:
                    print(f"  检测到重复URL，停止扫描")
                    break
                
                print(f"  扫描第 {page_num} 页: {current_url}")
                self.driver.get(current_url)
                visited_urls.add(current_url)
                time.sleep(2)
                
                # 查找所有图片查看链接 (photos-view-id-xxxxx.html)
                view_links = self.driver.find_elements(By.CSS_SELECTOR, "a[href*='photos-view-id-']")
                
                if not view_links:
                    if page_num == 1:
                        print(f"    ✗ 第 1 页没有找到图片链接")
                    else:
                        print(f"    第 {page_num} 页没有更多图片，停止扫描")
                    break
                
                # 提取所有链接 URL
                page_view_urls = []
                for link in view_links:
                    url = link.get_attribute('href')
                    if url and 'photos-view-id-' in url and url not in view_urls:
                        page_view_urls.append(url)
                
                view_urls.extend(page_view_urls)
                print(f"    找到 {len(page_view_urls)} 个图片链接（总计: {len(view_urls)}）")
                
                # 查找"下一页"或"后頁"链接
                next_page_link = None
                try:
                    # 方法1：通过文本查找（后頁>、下一頁等）
                    next_links = self.driver.find_elements(By.XPATH, "//a[contains(text(), '後頁') or contains(text(), '后页') or contains(text(), '下一頁') or contains(text(), '下一页')]")
                    if next_links:
                        next_page_link = next_links[0]
                except:
                    pass
                
                if not next_page_link:
                    try:
                        # 方法2：查找包含 photos-index 且 page 数字更大的链接
                        all_page_links = self.driver.find_elements(By.CSS_SELECTOR, "a[href*='photos-index']")
                        for link in all_page_links:
                            href = link.get_attribute('href')
                            if href and href not in visited_urls and '-page-' in href:
                                next_page_link = link
                                break
                    except:
                        pass
                
                if not next_page_link:
                    print(f"    没有找到下一页链接，扫描完成")
                    break
                
                # 获取下一页 URL
                current_url = next_page_link.get_attribute('href')
                if not current_url:
                    print(f"    下一页链接无效，停止扫描")
                    break
                
                page_num += 1
                
                # 安全限制：最多 100 页
                if page_num > 100:
                    print(f"    达到最大页数限制 (100 页)")
                    break
            
            print(f"\n共收集到 {len(view_urls)} 个图片链接")
            
            if not view_urls:
                print("✗ 没有找到任何图片链接")
                return []
            
            # 第二步：逐个访问链接获取原图
            images = []
            
            for idx, view_url in enumerate(view_urls, 1):
                try:
                    print(f"  [{idx}/{len(view_urls)}] 获取原图...")
                    self.driver.get(view_url)
                    time.sleep(1.5)
                    
                    # 查找原图
                    # 原图特征：src 包含 wnimg，且路径为 /data/.../xxx.jpg (不含 /t/)
                    img_elems = self.driver.find_elements(By.CSS_SELECTOR, "img[src*='wnimg']")
                    original_url = None
                    
                    for img_elem in img_elems:
                        src = img_elem.get_attribute('src')
                        # 过滤掉缩略图 (包含 /t/) 和其他非原图
                        if src and '/data/' in src and '/t/' not in src:
                            original_url = src
                            break
                    
                    if original_url:
                        # 获取文件扩展名
                        ext = original_url.split('.')[-1].split('?')[0] if '.' in original_url else 'jpg'
                        images.append({
                            'index': idx,
                            'url': original_url,
                            'filename': f"{idx:04d}.{ext}"
                        })
                        print(f"    ✓ {original_url[:70]}...")
                    else:
                        print(f"    ✗ 未找到原图")
                        
                except Exception as e:
                    print(f"    ✗ 获取失败: {e}")
                    continue
            
            print(f"\n✓ 成功获取 {len(images)}/{len(view_urls)} 张原图")
            return images
            
        except Exception as e:
            print(f"获取漫画图片失败: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def close(self):
        """关闭浏览器"""
        if self.driver:
            self.driver.quit()
            self.driver = None
